"""DEC MAINDEC-8E diagnostics: how each is operated, and how its result is judged.

Every entry follows the program's write-up (sim/test_programs/<directory>/…-d.pdf, sections 4 to
8). A run loads the tape through the console, operates the switches as the write-up directs,
and runs, normally in lock-step with the reference model. The result is judged as the operator
would: any halt is an error halt (the write-ups list them), and any Teletype output other than
the program's documented pass markers and start-up characters is an error printout.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pdp8_cpu import encodings as E

from .lockstep import Lockstep, disassemble
from .machine import KL8E, Machine, load_store
from .papertape import load_tape, read_tape

PROGRAMS = Path(__file__).resolve().parents[3] / "test_programs"
JUMP_TO_SELF_LIMIT = 10_000           # consecutive self-jumps that count as an error loop
BEL, NUL, RUBOUT, CR, LF = 0o207, 0o000, 0o377, 0o215, 0o212
NEWLINE = frozenset({CR, LF})
# Lines D1FB and D1BC type after setup, reporting the memory they found and will test.
STACK_INFO = (r"\d STACKS IN THIS SYSTEM", r"STACKS SEL'D ARE( \d)* ?", r"PROG WILL (NOT )?RELOCATE")


@dataclass(frozen=True)
class Diagnostic:
    directory: str
    title: str
    switches: int = 0                  # SR for CLEAR and CONTINUE (write-up §4.1, §4.3)
    deposits: tuple = ()               # (address, value) set up before starting (§4.3, §5)
    markers: frozenset = frozenset()   # characters that mark a completed pass (§8)
    ignored: frozenset = frozenset()   # start-up characters and the line breaks around markers
    continue_halts: frozenset = frozenset()  # PC after a documented halt, after which CONTINUE
    continue_switches: int | None = None  # SR set before CONTINUE at a documented halt
    preamble: bool = False             # text before the first documented halt (a banner) is not judged
    info_lines: tuple = ()             # regexes for whole lines of information, not errors
    jump_to_self_errors: bool = False  # a JMP to its own address that keeps looping is an error (§6)
    printout_halts: bool = False       # every error printout is followed by a halt (§6), so the
                                       # halt alone is the error; other text is not judged


DIAGNOSTICS = {
    "d0ab": Diagnostic("maindec-8e-d0ab", "Instruction Test 1", switches=0o7777,
                       markers=frozenset({BEL}), continue_halts=frozenset({0o0147})),
    "d0bb": Diagnostic("maindec-8e-d0bb", "Instruction Test 2", markers=frozenset({BEL})),
    # §5.1 fast test (SR03 = 1): ARG2 starts at the value in 0170 instead of 0000. The end-of-test
    # typeout is not documented; observed, it is CR LF and the test's name ("SIMAD" after 737,358
    # instructions with 0170 = 7777). Every error message ends in a halt (§6.1), so only halts count.
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
    # No write-up in the archive: started at 0200 with SR = 0 and judged by halts until its output
    # is known.
    "d1aa": Diagnostic("maindec-8e-d1aa", "MM8-E 4K Memory Checkerboard", printout_halts=True),
    # §7.1: "EC" after every 96 loops, before each relocation; §6.1: errors print "A xxxx C yyyy"
    # and halt (SR0 = 0). The "C" is counted, so an "A" or a digit is error text.
    "d1ec": Diagnostic("maindec-8e-d1ec", "Memory Address Test", markers=frozenset({ord("C") | 0o200}),
                       ignored=NEWLINE | {ord("E") | 0o200}),
    # §4.3.2, time share disabled (no time-share hardware): SR0 = 1 (memory extension only) and
    # SR9-11 = 7 extended fields; a halt at 3651 confirms time share is disabled, then CONTINUE.
    # §4.3: a bell after every pass. §6.1: errors are halts or jumps to self.
    "d1ha": Diagnostic("maindec-8e-d1ha", "Memory Extension and Time Share Control Test", switches=0o4007,
                       markers=frozenset({BEL}), continue_halts=frozenset({0o3651, 0o3652}),
                       jump_to_self_errors=True),
    # §4.1: start at 0200 (IF = DF = 0); it types a banner and "SETUP SR & CONT" and halts (at
    # 2634); then SR06-08 = 0 and SR09-11 = 7 select stacks 0-7, and CONTINUE. It reports the stacks
    # it found and selected (STACK_INFO; observed "8 STACKS IN THIS SYSTEM") and tests in silence.
    # §7: a "5" about every five minutes of real run time (about 100 million instructions), so a
    # run is judged by its errors. §5: error typeouts ("PR LOC ADDR GOOD BAD TEST", "RELOCATION
    # ERROR") and the program continues.
    "d1fb": Diagnostic("maindec-8e-d1fb", "Extended Memory Address Test", markers=frozenset({ord("5") | 0o200}),
                       ignored=NEWLINE, continue_halts=frozenset({0o2635}), continue_switches=0o0007,
                       preamble=True, info_lines=STACK_INFO),
    # No write-up; the archive's note: SR09-11 = the number of fields to check, a "5" after each
    # pass. Same start-up as D1FB (banner, "SETUP SR & CONT", halt at 2632, STACK_INFO).
    "d1bc": Diagnostic("maindec-8e-d1bc", "KM8-E Extended Memory Checkerboard", markers=frozenset({ord("5") | 0o200}),
                       ignored=NEWLINE, continue_halts=frozenset({0o2633}), continue_switches=0o0007,
                       preamble=True, info_lines=STACK_INFO),
}


@dataclass
class Outcome:
    name: str
    steps: int = 0
    markers: int = 0
    printed: list = field(default_factory=list)
    halt: str | None = None            # description of an error halt or jump to self
    continued: int = 0                 # documented halts continued from
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
    pending = []                               # an incomplete line, for info_lines judging
    self_jumps = 0
    while outcome.steps < max_steps:
        halted, pc, ir = stepper.step()
        outcome.steps += 1
        if d.jump_to_self_errors and ir is not None and ir >> 9 == 0o5 and m.state["PC"] == pc:
            self_jumps += 1
            if self_jumps >= JUMP_TO_SELF_LIMIT:
                outcome.halt = f"jump to self at {pc:04o} {disassemble(ir)}, AC = {m.state['AC']:04o}"
                break
        else:
            self_jumps = 0
        if not (d.preamble and outcome.continued == 0):
            new = kl.printed[seen:]
            if d.info_lines:                       # judge whole lines, so information lines pass
                pending += new
                while LF in pending:
                    i = pending.index(LF)
                    _judge_line(d, pending[:i + 1], outcome)
                    pending = pending[i + 1:]
            else:
                markers, errors = classify(d, new)
                outcome.markers += markers
                outcome.error_text += errors
        seen = len(kl.printed)
        if halted:
            if m.state["PC"] in d.continue_halts:
                outcome.continued += 1
                if d.continue_switches is not None:
                    m.panel.sr = d.continue_switches
                m.cont()
                continue
            outcome.halt = f"at {pc:04o} {disassemble(ir)}, AC = {m.state['AC']:04o}"
            break
        if outcome.error_text or (stop_after_markers and outcome.markers >= stop_after_markers):
            break
        if progress and outcome.steps % 100_000 == 0:
            progress(outcome)
    if pending:
        _judge_line(d, pending, outcome)
    outcome.printed = list(kl.printed)
    return outcome


def _judge_line(d: Diagnostic, line, outcome: Outcome):
    body = "".join(chr(c & 0o177) for c in line if c not in NEWLINE)
    if any(re.fullmatch(p, body) for p in d.info_lines):
        return
    markers, errors = classify(d, line)
    outcome.markers += markers
    outcome.error_text += errors


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
