"""The CPU: control-store lookup, datapath evaluation, and commit, one TS or console transaction at a time.

Step granularity is one timing state, committing at its TP (handoff §5; MCS §7). The control word
for TS n is combinational and valid during TS n; there is no pipeline register
(docs/04-control/08-control-store-organization.md, CSO §5.4.3). TSTEP-level timing (T_CS,
CW_VALID, DB_VALID, /WR_PULSE) is below this granularity and not modelled.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import address as A
from . import derived as D
from . import design as DS
from . import encodings as E
from .console import COMMANDS, FrontPanel
from .datapath import evaluate
from .errors import SimError, SpecGap, SpecViolation
from .images import ControlStore
from .inputs import Conditions, ExternalInputs, ir_decodes
from .logic import bits, t_and
from .sequencer import next_ts, sequencer_loads
from .state import CpuState


@dataclass(frozen=True)
class IotBus:
    """The external-IOT interface signals presented to controllers during a TS (docs/07-io)."""
    iot_active: int
    ioa: int | None
    iop: int | None
    ts: int
    console: bool = False


@dataclass
class TraceRecord:
    kind: str                 # "TS" (main sequence) or "TPC" (console transaction)
    ms: int
    ts: int
    run: int
    ir: int | None
    pc: int | None
    command: str | None
    dp_addresses: list
    seq_addresses: list
    datapath: dict            # decoded datapath fields (first candidate address)
    sequencer: dict           # decoded sequencer fields
    loads: dict = field(default_factory=dict)
    mem_read: tuple | None = None
    mem_write: tuple | None = None
    strobes: dict = field(default_factory=dict)


# Simulated duration of each major state, in ns: the PDP-8/E's 1.2 µs memory cycle by default. The
# documentation does not yet fix this machine's cycle time (TSTEP counts are an open item); time is
# simulated only so that controllers can model real-time behavior such as Teletype character times.
# The design's per-TS table (design.py) is the source; this is its per-state view.
DEFAULT_TIMING = DS.select("v1").state_ns()  # V1-ONLY: the v1 time base, for callers that name it


class Cpu:
    def __init__(self, store: ControlStore, memory, panel: FrontPanel | None = None,
                 ext: ExternalInputs | None = None, trace=None, devices=(), dma=None, timing=None, ts_ns=None):
        """ext: test stimulus for the external inputs (for example /INT_REQ); controllers in
        `devices` contribute their own responses each TS. A controller provides present(bus),
        commit(bus, tp, db_write, initialize), initialize(), and optionally at_boundary().

        dma: the DMA arbiter (docs/07-io/06-dma-arbitration.md), which supplies aggregate
        /DMA_REQ and, while /DMA_GRANT is asserted, the selected controller's memory transfer:
        aggregate_n(in_last_state, in_dma, ts), operation(), and
        commit(tp, in_last_state, in_dma, initialize, transferred), where in_last_state is true in
        the instruction's last major state (design.is_last_state; v1: EXECUTE).

        timing: the simulated duration of each major state in ns, overriding the design's; that
        state's whole duration is then charged at its TP4.
        ts_ns: the duration of each timing state, per major state (default: the design's table,
        design.py). `elapsed_ns` advances by each TS's duration at its main-sequence TP, so at an
        instruction boundary it has the sum of the major states run; it is passed to
        `at_boundary(now_ns)`."""
        self.store = store
        self.memory = memory
        self.panel = panel or FrontPanel()
        self.ext = ext or ExternalInputs()
        self.devices = list(devices)
        self.dma = dma
        self.design = getattr(store, "design", None) or DS.select()
        table = dict(ts_ns or self.design.ts_ns)
        if timing:
            table.update(DS.ts_table_from_states(timing))
        self.ts_ns = table
        self.elapsed_ns = 0
        self.st = CpuState()
        self.trace = trace          # optional callable(TraceRecord)
        self.last_record: TraceRecord | None = None

    def last_state(self, ms: int, ir) -> bool:
        """Whether major state `ms`, running `ir`, ends the instruction (design.is_last_state)."""
        return DS.is_last_state(self.design, E.MS_NAMES.get(ms, ms), ir)

    def boundary_kind(self, record) -> str | None:
        """For the TS just committed: "instruction", "interrupt" (entry), or "dma" (one cycle) if
        its TP4 ended one of these, else None."""
        if record.kind != "TS" or record.ts != 4:
            return None
        if record.ms == E.INTERRUPT:
            return "interrupt"
        if record.ms == E.DMA:
            return "dma"
        return "instruction" if self.last_state(record.ms, record.ir) else None

    @property
    def timing(self) -> dict:
        """The duration of each major state, in ns: the sum of its timing states."""
        return {ms: sum(t) for ms, t in self.ts_ns.items()}

    # -- lifecycle ---------------------------------------------------------------------------

    def power_on(self):
        """Timing Terminology §3.4. The console latch holds no command; /INITIALIZE is asserted,
        so each controller is in its initialized state when the reset ends."""
        self.st.power_on()
        self.panel.latched = None
        for device in self.devices:
            device.initialize()
        if self.dma is not None:
            self.dma.initialize()

    @property
    def running(self) -> bool:
        return self.st["RUN"] == 1

    def step_ts(self) -> TraceRecord | None:
        """Execute one main-sequence TS and its TP. Returns None while halted."""
        if not self.running:
            return None
        return self._cycle(console=False)

    def press(self, command: str) -> bool:
        """Press a console-command key. Accepted only while halted (EXT §4.1); an accepted
        command runs as one console transaction committing at TPC (MST §8.2)."""
        if command not in COMMANDS:
            raise ValueError(f"unknown console command {command}")
        if self.running:
            return False
        if self.st.ts != 1:
            raise SpecViolation(f"halted with TS{self.st.ts}; TSEQ is held at TS1 while halted", "MST §8.1")
        self.panel.latched = command
        try:
            self._cycle(console=True)
        finally:
            self.panel.latched = None
        return True

    # -- one TS or console transaction -----------------------------------------------------

    def _signal(self, cond, name):
        if name == "FP_CMD":
            return self.panel.fp_cmd()
        return cond.get(name)

    def _bus(self, console: bool) -> IotBus:
        """ACS §4.6-§4.8: IOA and IOP from IR; IOT_ACTIVE = MS_EFF_IS_EXECUTE AND IR_IS_EXTERNAL_IOT."""
        st = self.st
        is_exec = A.ms_eff_is_execute(A.ms_eff(st["MS"], st["RUN"]))
        active = t_and(is_exec, ir_decodes(st["IR"])["IR_IS_EXTERNAL_IOT"])
        return IotBus(int(active == 1), bits(st["IR"], 8, 3), bits(st["IR"], 2, 0), st.ts, console)

    def _external_inputs(self, bus: IotBus) -> ExternalInputs:
        """The test stimulus combined with every controller's responses for this TS."""
        ext = object.__new__(ExternalInputs)          # a copy of the test stimulus (faster than replace())
        ext.__dict__.update(self.ext.__dict__)
        if self.dma is not None:                      # ARB §7: the arbiter's aggregate /DMA_REQ
            st = self.st
            ext.dma_req_n &= self.dma.aggregate_n(self.last_state(st["MS"], st["IR"]), st["MS"] == E.DMA,
                                                  st.ts)
        for device in self.devices:
            r = device.present(bus)
            ext.io_read_req |= r.io_read_req
            ext.io_write_req |= r.io_write_req
            ext.io_skip_req |= r.io_skip_req
            ext.io_clear_ac_req |= r.io_clear_ac_req
            if r.db is not None:
                if ext.db_input is not None:
                    raise SpecViolation("two controllers drive DB", "ACS §4.3")
                ext.db_input = r.db
            if r.int_req:
                ext.int_req_n = 0                 # /INT_REQ is the wired OR of the requests
        return ext

    def _cycle(self, console: bool) -> TraceRecord:
        st = self.st
        bus = self._bus(console)
        ext = self._external_inputs(bus)
        cond = Conditions(st, ext, self.panel)
        run, ms, ts = st["RUN"], st["MS"], st.ts
        context = {"MS": E.MS_NAMES.get(ms, ms), "TS": ts, "RUN": run, "IR": st["IR"], "PC": st["PC"],
                   "command": self.panel.latched}
        try:
            mseff = A.ms_eff(ms, run)
            is_exec = A.ms_eff_is_execute(mseff)
            D.check_derived(run, ms, mseff, is_exec, cond.get("IR_IS_EXTERNAL_IOT"))

            design = self.design
            non_exec_variant = cond.get(design.non_execute_variant) if design.non_execute_variant else 0
            variant, sel, ir_seq = A.execute_selection(is_exec, st["MAPR"], cond.get("IR_INDIRECT"),
                                                       non_exec_variant)
            a2 = cond.get(design.sequencer_a2) if design.sequencer_a2 else 0
            a1 = cond.get(design.sequencer_a1) if design.sequencer_a1 else 0
            group = self.store.overlay_group(sel, run)
            ovl = A.overlay_bits(group, lambda s: self._signal(cond, s))
            tsc = A.ts_code(ts)
            dp_base, dp_undef = A.datapath_address(mseff, tsc, variant, ovl)
            seq_ovl = A.seq_ovl_bits(run, self.panel.fp_cmd(), int(self.panel.single_instruction),
                                     int(self.panel.single_step), cond.get("INTERRUPT_REQUEST_VALID"))
            seq_base, seq_undef = A.sequencer_address(mseff, tsc, st["HLT_REQ"], int(self.panel.stop),
                                                      seq_ovl, ext.dma_req_n, ir_seq, a2, a1)
            context.update(dp_addr=dp_base, seq_addr=seq_base)

            dp_addrs = A.expand(dp_base, dp_undef)
            effects, dp_fields = self._datapath_effects(dp_addrs, dp_undef, group, cond, mseff, ext)
            dma_read, dma_write, dma_value = self._dma_transfer(mseff, ts, console)
            seq_addrs = A.expand(seq_base, seq_undef)
            seq = self._sequencer_word(seq_addrs, seq_undef)

            D.check_initialize(seq["/INITIALIZE"], D.initialize_asserted(
                cond.get("IR_IS_CAF"), ms, ts, run, self.panel.command_asserted("CLEAR")))
            seq_loads = sequencer_loads(seq, main_sequence=not console, ts=ts)

            # Timing Terminology §3.5: the timing ROM's context, from pre-TP state: the major
            # state, or the slow DEFER when AUTO_INDEX_REQUIRED = 1.
            timing_context = E.MS_NAMES.get(ms, ms)
            if (timing_context == "DEFER" and DS.DEFER_AUTOINDEX in self.ts_ns
                    and cond.get("AUTO_INDEX_REQUIRED") == 1):
                timing_context = DS.DEFER_AUTOINDEX
            mapr_next = None
            if not console:  # CSO §5.4.1: MAPR loads at every main-sequence TP, never at TPC
                m_addr = A.mapping_address(st["IR"], ts)
                mapr_next = None if m_addr is None else self.store.mapping_entry(m_addr)
        except SimError as e:
            raise e.with_context(**context) from e

        # Commit: every load uses values computed from the pre-TP state (MCS §7.5, §11.5).
        overlap = effects.loads.keys() & seq_loads.keys()
        if overlap:
            raise SpecViolation(f"datapath and sequencer both load {sorted(overlap)}", "CSO §4", context)
        for name, value in {**effects.loads, **seq_loads}.items():
            st[name] = value
        if effects.mem_write:
            self.memory.write(*effects.mem_write)
        if dma_write:
            self.memory.write(*dma_write)
        if not console:
            st["MAPR"] = mapr_next
            st.ts = next_ts(ts, st["RUN"])
        initialize = seq["/INITIALIZE"] == 0       # ACS §4.9: controllers initialize at this TP
        for device in self.devices:
            device.commit(bus, "C" if console else ts, effects.db_write, initialize)
        if self.dma is not None:
            self.dma.commit("C" if console else ts, self.last_state(ms, context["IR"]), ms == E.DMA,
                            initialize, dma_value)
        if not console:                              # this TS's duration (design.py)
            self.elapsed_ns += self.ts_ns[timing_context][ts - 1]
        if not console and ts == 4 and (ms == E.INTERRUPT or self.last_state(ms, context["IR"])):
            for device in self.devices:              # an instruction boundary (see KL8E model)
                getattr(device, "at_boundary", lambda now_ns: None)(self.elapsed_ns)

        record = TraceRecord("TPC" if console else "TS", ms, ts, run, context["IR"], context["PC"],
                             self.panel.latched, dp_addrs, seq_addrs, dp_fields, seq,
                             dict(effects.loads, **seq_loads), effects.mem_read or dma_read,
                             effects.mem_write or dma_write, effects.strobes)
        self.last_record = record
        if self.trace:
            self.trace(record)
        return record

    def _dma_transfer(self, mseff, ts, console):
        """DMA §6.3, MEM §3: with /DMA_GRANT asserted (MS_EFF = DMA), the controller the arbiter
        selected presents one memory operation during TS2, and it commits at TP2. Returns
        (read address, write, value transferred), each None when there is none."""
        if console or ts != 2 or mseff != E.DMA or self.dma is None:
            return None, None, None
        op = self.dma.operation()
        if op is None:
            return None, None, None                  # DMX §5: no controller selected, no transfer
        if op[0] == "read":
            _, f, a = op
            return (f, a), None, self.memory.read(f, a)
        _, f, a, value = op
        return None, (f, a, value), value

    def _datapath_effects(self, addresses, undefined, group, cond, mseff, ext):
        """Evaluate the word at every candidate address; their effects must agree."""
        results = []
        for addr in addresses:
            fields = self.store.decode_datapath(addr)
            results.append((addr, fields, evaluate(fields, self.st, ext, self.panel,
                                                   self.memory, cond, mseff, self.design)))
        keys = {fx.key() for _, _, fx in results}
        if len(keys) > 1:
            names = [self._dp_bit_name(p, group) for p in undefined]
            raise SpecGap(f"the datapath word's effect depends on undefined input(s) {names}",
                          "CSO §9: no reachable word may depend on an input it cannot rely on",
                          {"addresses": [f"{a:05o}" for a, _, _ in results]})
        _, fields, effects = results[0]
        return effects, fields

    def _sequencer_word(self, addresses, undefined):
        if len(addresses) == 1:
            return self.store.decode_sequencer(addresses[0])
        words = {tuple(sorted(self.store.decode_sequencer(a).items())) for a in addresses}
        if len(words) > 1:
            names = [{9: "HLT_REQ", 8: "FP_STOP", 7: "SEQ_OVL[2]", 6: "SEQ_OVL[1]", 5: "SEQ_OVL[0]",
                      4: "/DMA_REQ", 3: "IR_SEQ", 2: "A2", 1: "A1"}.get(p, f"A{p}")
                     for p in undefined]
            raise SpecGap(f"the sequencer word depends on undefined input(s) {names}", "CSO §9")
        return dict(words.pop())

    @staticmethod
    def _dp_bit_name(position, group):
        if position >= 5:
            return f"A{position}"
        for bit, signal, width in group:
            if bit <= position < bit + width:
                return signal if width == 1 else f"{signal}[{position - bit}]"
        return f"DP_OVL[{position}]"
