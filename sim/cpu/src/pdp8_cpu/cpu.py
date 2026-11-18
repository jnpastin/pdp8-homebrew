"""The CPU: control-store lookup, datapath evaluation, and commit, one TS or console transaction at a time.

Step granularity is one timing state, committing at its TP (handoff §5; MCS §7). The control word
for TS n is combinational and valid during TS n; there is no pipeline register
(docs/04-control/08-control-store-organization.md, CSO §5.4.3). TSTEP-level timing (T_CS,
CW_VALID, WR_VALID, /IO_WAIT) is below this granularity and not modelled.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from . import address as A
from . import derived as D
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


class Cpu:
    def __init__(self, store: ControlStore, memory, panel: FrontPanel | None = None,
                 ext: ExternalInputs | None = None, trace=None, devices=()):
        """ext: test stimulus for the external inputs (for example /INT_REQ); controllers in
        `devices` contribute their own responses each TS. A controller provides present(bus),
        commit(bus, tp, db_write, initialize), initialize(), and optionally at_boundary()."""
        self.store = store
        self.memory = memory
        self.panel = panel or FrontPanel()
        self.ext = ext or ExternalInputs()
        self.devices = list(devices)
        self.st = CpuState()
        self.trace = trace          # optional callable(TraceRecord)
        self.last_record: TraceRecord | None = None

    # -- lifecycle ---------------------------------------------------------------------------

    def power_on(self):
        """Timing Terminology §3.4. The console latch holds no command; /INITIALIZE is asserted,
        so each controller is in its initialized state when the reset ends."""
        self.st.power_on()
        self.panel.latched = None
        for device in self.devices:
            device.initialize()

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
        ext = replace(self.ext)
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

            variant, sel, ir_seq = A.execute_selection(is_exec, st["MAPR"], cond.get("IR_INDIRECT"))
            group = self.store.overlay_groups[sel]
            ovl = A.overlay_bits(group, lambda s: self._signal(cond, s))
            tsc = A.ts_code(ts)
            dp_base, dp_undef = A.datapath_address(mseff, tsc, variant, ovl)
            seq_ovl = A.seq_ovl_bits(run, self.panel.fp_cmd(), int(self.panel.single_instruction),
                                     int(self.panel.single_step), cond.get("INTERRUPT_REQUEST_VALID"))
            seq_base, seq_undef = A.sequencer_address(mseff, tsc, st["HLT_REQ"], int(self.panel.stop),
                                                      seq_ovl, ext.dma_req_n, ir_seq)
            context.update(dp_addr=dp_base, seq_addr=seq_base)

            dp_addrs = A.expand(dp_base, dp_undef)
            effects, dp_fields = self._datapath_effects(dp_addrs, dp_undef, group, cond, mseff, ext)
            seq_addrs = A.expand(seq_base, seq_undef)
            seq = self._sequencer_word(seq_addrs, seq_undef)

            D.check_initialize(seq["/INITIALIZE"], D.initialize_asserted(
                cond.get("IR_IS_CAF"), ms, ts, run, self.panel.command_asserted("CLEAR")))
            seq_loads = sequencer_loads(seq, main_sequence=not console, ts=ts)

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
        if not console:
            st["MAPR"] = mapr_next
            st.ts = next_ts(ts, st["RUN"])
        initialize = seq["/INITIALIZE"] == 0       # ACS §4.9: controllers initialize at this TP
        for device in self.devices:
            device.commit(bus, "C" if console else ts, effects.db_write, initialize)
        if not console and ts == 4 and ms in (E.EXECUTE, E.INTERRUPT):
            for device in self.devices:              # an instruction boundary (see KL8E model)
                getattr(device, "at_boundary", lambda: None)()

        record = TraceRecord("TPC" if console else "TS", ms, ts, run, context["IR"], context["PC"],
                             self.panel.latched, dp_addrs, seq_addrs, dp_fields, seq,
                             dict(effects.loads, **seq_loads), effects.mem_read, effects.mem_write,
                             effects.strobes)
        self.last_record = record
        if self.trace:
            self.trace(record)
        return record

    def _datapath_effects(self, addresses, undefined, group, cond, mseff, ext):
        """Evaluate the word at every candidate address; their effects must agree."""
        results = []
        for addr in addresses:
            fields = self.store.decode_datapath(addr)
            results.append((addr, fields, evaluate(fields, self.st, ext, self.panel,
                                                   self.memory, cond, mseff)))
        keys = {fx.key() for _, _, fx in results}
        if len(keys) > 1:
            names = [self._dp_bit_name(p, group) for p in undefined]
            raise SpecGap(f"the datapath word's effect depends on undefined input(s) {names}",
                          "CSO §9: no reachable word may depend on an input it cannot rely on",
                          {"addresses": [f"{a:05o}" for a, _, _ in results]})
        _, fields, effects = results[0]
        return effects, fields

    def _sequencer_word(self, addresses, undefined):
        words = {tuple(sorted(self.store.decode_sequencer(a).items())) for a in addresses}
        if len(words) > 1:
            names = [{9: "HLT_REQ", 8: "FP_STOP", 7: "SEQ_OVL[2]", 6: "SEQ_OVL[1]", 5: "SEQ_OVL[0]",
                      4: "/DMA_REQ", 3: "IR_SEQ"}.get(p, f"A{p}") for p in undefined]
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
