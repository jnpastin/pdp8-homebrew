"""DEC MAINDEC-8E diagnostics: how each is operated, and how its result is judged.

Every entry follows the program's write-up (sim/test_programs/<directory>/…-d.pdf, sections 4 to
8). A run loads the tape through the console, operates the switches as the write-up directs,
and runs, normally in lock-step with the reference model. The result is judged as the operator
would: any halt is an error halt (the write-ups list them), and any Teletype output other than
the program's documented pass markers and start-up characters is an error printout.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pdp8_cpu import encodings as E

from .lockstep import Lockstep, disassemble
from .machine import KL8E, Machine, load_store
from .papertape import load_tape, read_tape

PROGRAMS = Path(__file__).resolve().parents[3] / "test_programs"
BEL, NUL, RUBOUT, CR, LF = 0o207, 0o000, 0o377, 0o215, 0o212
NEWLINE = frozenset({CR, LF})


@dataclass(frozen=True)
class Diagnostic:
    directory: str
    title: str
    switches: int = 0                  # SR for CLEAR and CONTINUE (write-up §4.1, §4.3)
    deposits: tuple = ()               # (address, value) set up before starting (§4.3, §5)
    markers: frozenset = frozenset()   # characters that mark a completed pass (§8)
    ignored: frozenset = frozenset()   # start-up characters and the line breaks around markers
    initial_halt: int | None = None    # PC of a documented start-up halt, after which CONTINUE
    printout_halts: bool = False       # every error printout is followed by a halt (§6), so the
                                       # halt alone is the error; other text is not judged


DIAGNOSTICS = {
    "d0ab": Diagnostic("maindec-8e-d0ab", "Instruction Test 1", switches=0o7777,
                       markers=frozenset({BEL}), initial_halt=0o0147),
    "d0bb": Diagnostic("maindec-8e-d0bb", "Instruction Test 2", markers=frozenset({BEL})),
    # §5.1 fast test (SR03 = 1): ARG2 starts at the value in 0170 instead of 0000. The end-of-test
    # typeout is not documented; every error message ends in a halt (§6.1).
    "d0cc": Diagnostic("maindec-8e-d0cc", "Adder Test", switches=0o0400, deposits=((0o0170, 0o7777),),
                       printout_halts=True),
    # §8: CR LF "A" after each 4096 tests (observed every 1.16-1.23 million instructions).
    "d0db": Diagnostic("maindec-8e-d0db", "Random AND Test", markers=frozenset({ord("A") | 0o200}),
                       ignored=NEWLINE),
    # §8: CR LF "T" after each 4096 tests (observed every 2.84 million instructions).
    "d0eb": Diagnostic("maindec-8e-d0eb", "Random TAD Test", markers=frozenset({ord("T") | 0o200}),
                       ignored=NEWLINE),
    "d0fc": Diagnostic("maindec-8e-d0fc", "Random ISZ Test"),
    # Not in the write-up: a bell after each pass (observed every 2.43 million instructions). The
    # "E" of §6.1 ends an error printout, so it is error text.
    "d0gc": Diagnostic("maindec-8e-d0gc", "Random DCA Test", markers=frozenset({BEL})),
    "d0hc": Diagnostic("maindec-8e-d0hc", "Random JMP Test", ignored=frozenset({NUL})),
    # §8.1: a bell every 3456 loops (observed first at 3,701,408 instructions).
    "d0ib": Diagnostic("maindec-8e-d0ib", "Basic JMP-JMS Test", markers=frozenset({BEL})),
    "d0jc": Diagnostic("maindec-8e-d0jc", "Random JMP-JMS Test", ignored=frozenset({RUBOUT})),
}


@dataclass
class Outcome:
    name: str
    steps: int = 0
    markers: int = 0
    printed: list = field(default_factory=list)
    halt: str | None = None            # description of an error halt
    error_text: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.halt is None and not self.error_text

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        detail = (f"halt {self.halt}" if self.halt else
                  f"error printout {text(self.error_text)!r}" if self.error_text else "")
        return (f"{self.name}: {status} after {self.steps} instructions, {self.markers} pass markers"
                + (f"; {detail}" if detail else "") + f"; printed {text(self.printed)[:120]!r}")


def text(chars) -> str:
    out = []
    for c in chars:
        c &= 0o177
        out.append(chr(c) if 32 <= c < 127 else {10: "\\n", 13: "\\r", 7: "<BEL>", 0: "<NUL>"}.get(c, f"<{c:o}>"))
    return "".join(out)


def classify(d: Diagnostic, chars) -> tuple[int, list]:
    """Split printed characters into a count of pass markers and a list of error text."""
    markers, errors = 0, []
    for c in chars:
        if c in d.markers:
            markers += 1
        elif c not in d.ignored and not d.printout_halts:
            errors.append(c)
    return markers, errors


def prepare(name: str, seed: int = 1) -> tuple[Machine, KL8E]:
    """A machine with the program loaded and started as its write-up directs."""
    d = DIAGNOSTICS[name]
    kl = KL8E()
    m = Machine(load_store(), devices=[kl])
    m.core_residue(seed)
    load_tape(m, read_tape(next((PROGRAMS / d.directory).glob("*-pb"))))
    for address, value in d.deposits:
        m.deposit_block(address, [value])
    m.panel.sr = 0o0200
    m.cpu.press("LOAD_ADDRESS")
    m.panel.sr = d.switches
    m.clear()
    m.cont()
    return m, kl


def run(name: str, max_steps: int, seed: int = 1, lockstep: bool = True, stop_after_markers: int | None = None,
        progress=None) -> Outcome:
    """Run until `max_steps` instructions, an error, or `stop_after_markers` pass markers."""
    d = DIAGNOSTICS[name]
    m, kl = prepare(name, seed)
    outcome = Outcome(name)
    stepper = _LockstepStepper(m) if lockstep else _SimStepper(m)
    seen = 0
    while outcome.steps < max_steps:
        halted, pc, ir = stepper.step()
        outcome.steps += 1
        markers, errors = classify(d, kl.printed[seen:])
        outcome.markers += markers
        outcome.error_text += errors
        seen = len(kl.printed)
        if halted:
            if d.initial_halt is not None and m.state["PC"] == d.initial_halt and outcome.steps < 100:
                m.cont()
                continue
            outcome.halt = f"at {pc:04o} {disassemble(ir)}, AC = {m.state['AC']:04o}"
            break
        if outcome.error_text or (stop_after_markers and outcome.markers >= stop_after_markers):
            break
        if progress and outcome.steps % 100_000 == 0:
            progress(outcome)
    outcome.printed = list(kl.printed)
    return outcome


class _LockstepStepper:
    def __init__(self, m):
        self.ls = Lockstep(m)

    def step(self):
        expected, _ = self.ls.step()
        return expected.halted, expected.pc, expected.ir


class _SimStepper:
    """The simulator alone: faster, and the program's own checks still apply."""

    def __init__(self, m):
        self.m = m

    def step(self, max_ts: int = 64):
        cpu, st = self.m.cpu, self.m.state
        pc = st["PC"]                              # the next instruction's address
        for _ in range(max_ts):
            ms = st["MS"]
            ir = st["IR"]
            record = cpu.step_ts()
            if record is None:
                raise RuntimeError("the simulator is halted mid-instruction")
            if record.kind == "TS" and record.ts == 4 and record.ms in (E.EXECUTE, E.INTERRUPT):
                return st["RUN"] == 0, pc, (ir if ms == E.EXECUTE else None)
        raise RuntimeError(f"no instruction boundary within {max_ts} timing states")
