"""Lock-step comparison of the control-store simulator with the instruction-level reference model.

The two run side by side. After every instruction, and after every interrupt entry, they must
agree on AC, L, MQ, PC, IF, DF, IE, the memory words written, whether the processor halted, and
whether an interrupt was recognized at that boundary. The first difference raises `Divergence`,
naming the instruction and, for each differing register, the major state and TS at which the
simulator committed it.

Attached controllers are compared too: each simulator controller has an instruction-level
counterpart in the reference model, and their programmer-visible state must agree at every
boundary.

A boundary in the simulator is the TP4 of an EXECUTE or INTERRUPT major state. DMA, Single Step,
and Single Instruction are outside the comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pdp8_cpu import encodings as E
from pdp8_reference import KL8E as ReferenceKL8E
from pdp8_reference import Reference, ReferenceError, disassemble

from .machine import Machine

__all__ = ["Divergence", "Lockstep", "Reference", "ReferenceError", "disassemble", "reference_from"]

COMPARED = ("AC", "L", "MQ", "PC", "IF", "DF", "IE")


class Divergence(Exception):
    pass


@dataclass
class Boundary:
    kind: str                       # "instruction" or "interrupt"
    records: list = field(default_factory=list)
    writes: list = field(default_factory=list)
    halted: bool = False
    interrupt_next: bool = False


def reference_from(machine: Machine) -> Reference:
    """A reference model holding the machine's current programmer-visible state and memory."""
    st = machine.state
    ref = Reference()
    ref.ac, ref.l, ref.mq, ref.pc = st["AC"], st["L"], st["MQ"], st["PC"]
    ref.if_, ref.df, ref.ie = st["IF"], st["DF"], st["IE"]
    ref.ib = st["IB"]
    ref.staged_if = st["DIF"] if st["CIFP"] == 1 else None
    ref.sr = machine.panel.sr
    ref.memory = [list(words) for words in machine.memory.words]
    ref.interrupt_pending = st["MS"] == E.INTERRUPT
    ref.devices = [_reference_device(d) for d in machine.devices]
    return ref


def _reference_device(device):
    if type(device).__name__ == "KL8E":
        return ReferenceKL8E.from_state(device.state())
    raise Divergence(f"no reference model for controller {type(device).__name__}")


class Lockstep:
    def __init__(self, machine: Machine, reference: Reference | None = None, int_req=None):
        """int_req: optional callable(step_number) -> bool giving the interrupt request for each step."""
        self.m = machine
        self.ref = reference or reference_from(machine)
        self.int_req = int_req or (lambda n: False)
        self.steps = 0
        self._records: list = []
        machine.cpu.trace = self._records.append

    def _sim_boundary(self, max_ts: int) -> Boundary:
        self._records.clear()
        cpu = self.m.cpu
        for _ in range(max_ts):
            record = cpu.step_ts()
            if record is None:
                raise Divergence("the simulator is halted mid-instruction")
            if record.kind == "TS" and record.ts == 4 and record.ms in (E.EXECUTE, E.INTERRUPT):
                b = Boundary("interrupt" if record.ms == E.INTERRUPT else "instruction",
                             list(self._records))
                b.writes = [r.mem_write for r in b.records if r.mem_write]
                b.halted = self.m.state["RUN"] == 0
                b.interrupt_next = self.m.state["MS"] == E.INTERRUPT
                return b
            if record.ms == E.DMA:
                raise Divergence("DMA is outside the lock-step comparison")
        raise Divergence(f"no instruction boundary within {max_ts} timing states")

    def step(self, max_ts: int = 64):
        """Run one instruction (or interrupt entry) on both models and compare them."""
        request = bool(self.int_req(self.steps))
        self.m.cpu.ext.int_req_n = 0 if request else 1
        self.ref.int_req = request
        self.ref.sr = self.m.panel.sr
        expected = self.ref.step()
        got = self._sim_boundary(max_ts)
        self.steps += 1
        self._compare(expected, got)
        return expected, got

    def run(self, max_steps: int, stop_at_halt: bool = True) -> int:
        for _ in range(max_steps):
            expected, _ = self.step()
            if expected.halted and stop_at_halt:
                break
            if expected.halted:
                self.m.cont()
        return self.steps

    # -- comparison --------------------------------------------------------------------------

    def _compare(self, expected, got: Boundary):
        st, ref = self.m.state, self.ref
        problems = []
        if expected.kind != got.kind:
            problems.append(f"step kind: simulator {got.kind}, reference {expected.kind}")
        for name in COMPARED:
            mine = st[name]
            theirs = getattr(ref, "if_" if name == "IF" else name.lower())
            if mine != theirs:
                problems.append(f"{name}: simulator {_o(mine)}, reference {_o(theirs)}"
                                f" ({self._last_commit(got, name)})")
        if got.writes != expected.writes:
            problems.append(f"memory writes: simulator {_writes(got.writes)}, reference {_writes(expected.writes)}")
        for sim_dev, ref_dev in zip(self.m.devices, ref.devices):
            mine, theirs = sim_dev.state(), {k: getattr(ref_dev, k) for k in sim_dev.state()}
            if mine != theirs:
                diff = {k: (mine[k], theirs[k]) for k in mine if mine[k] != theirs[k]}
                problems.append(f"{type(sim_dev).__name__}: simulator/reference {diff}")
        if got.halted != expected.halted:
            problems.append(f"halted: simulator {got.halted}, reference {expected.halted}")
        if got.interrupt_next != expected.interrupt_next:
            problems.append(f"interrupt recognized: simulator {got.interrupt_next}, reference {expected.interrupt_next}")
        if problems:
            what = ("interrupt entry" if expected.kind == "interrupt" else
                    f"{expected.field:o}:{expected.pc:04o} {expected.ir:04o} {disassemble(expected.ir)}")
            raise Divergence(f"step {self.steps}, {what}: " + "; ".join(problems))

    @staticmethod
    def _last_commit(got: Boundary, name):
        for r in reversed(got.records):
            if name in r.loads:
                return f"last committed at {E.MS_NAMES.get(r.ms, r.ms)} TP{r.ts}"
        return "not loaded during this step"


def _o(v):
    return "UNDEFINED" if v is None else f"{v:o}"


def _writes(ws):
    return "[" + ", ".join(f"{f:o}:{a:04o}=" + ("UNDEFINED" if v is None else f"{v:04o}") for f, a, v in ws) + "]"
