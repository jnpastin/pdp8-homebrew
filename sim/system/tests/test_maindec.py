"""Milestone M3: DEC MAINDEC-8E diagnostics, loaded through the console and run in lock-step.

Each program is operated as its write-up directs (sim/test_programs/*/…-d.pdf, §4.3). D0AB and
D0BB pass by returning to their restart points with no error halt. The random and specialized
tests (D0CC-D0JC) take 1 to 4 million instructions per pass, so the regression runs are bounded:
a fixed number of instructions with no error halt and no error printout, under two core
residues. The simulator and the reference model must agree on every instruction.
test_maindec_full_passes.py runs them to complete passes (opt-in).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system import maindec
from pdp8_system.lockstep import Lockstep, disassemble
from pdp8_system.machine import KL8E, Machine, load_store
from pdp8_system.papertape import load_tape, read_tape

PROGRAMS = Path(__file__).resolve().parents[2] / "test_programs"


def loaded(name, devices=(), seed=1):
    m = Machine(load_store(), devices=devices)
    m.core_residue(seed)        # leftover core contents (see Machine.core_residue)
    load_tape(m, read_tape(next((PROGRAMS / name).glob("*-pb"))))
    return m


def run_passes(test, m, restart, passes, max_steps=20_000):
    """Lock-step until `passes` returns to `restart`; fail on any halt."""
    ls = Lockstep(m)
    seen = 0
    while seen < passes:
        expected, _ = ls.step()
        if expected.halted:
            test.fail(f"error halt at {expected.field:o}:{expected.pc:04o} {disassemble(expected.ir)}, "
                      f"AC = {m.state['AC']:04o}, step {ls.steps}")
        if expected.kind == "instruction" and m.state["PC"] == restart and expected.pc != restart - 1:
            seen += 1
        test.assertLess(ls.steps, max_steps * passes, "no pass completed")
    return ls


class InstructionTest1(unittest.TestCase):
    """MAINDEC-8E-D0AB: operate, TAD, rotates, BSW, MQ, AND. No device is needed before the bell."""

    def test_two_passes(self):
        m = loaded("maindec-8e-d0ab")
        # §4.3: SR = 200, LOAD ADDRESS; SR = 7777, CLEAR, CONTINUE; halts with MA = 147 and AC = 0.
        m.panel.sr = 0o200
        m.cpu.press("LOAD_ADDRESS")
        m.panel.sr = 0o7777
        m.clear()
        m.cont()
        Lockstep(m).run(100)
        self.assertEqual((m.state["PC"], m.state["AC"]), (0o0147, 0))
        # §4.3 step 5: CONTINUE; the program runs until stopped or an error halts it.
        m.cont()
        run_passes(self, m, restart=0o0147, passes=2)


class InstructionTest2(unittest.TestCase):
    """MAINDEC-8E-D0BB: DCA, indirect, autoindex, processor IOTs, interrupts (via the KL8E)."""

    def start(self, kl, counter=None, seed=1):
        m = loaded("maindec-8e-d0bb", devices=[kl], seed=seed)
        if counter is not None:
            m.deposit_block(0o3747, [counter])          # the pass counter the bell routine tests
        # §4.3: SR = 200, LOAD ADDRESS; CLEAR, CONTINUE.
        m.panel.sr = 0o200
        m.cpu.press("LOAD_ADDRESS")
        m.clear()
        m.cont()
        return m

    def test_two_passes(self):
        # Two different core residues: the result must not depend on leftover memory contents.
        for seed in (1, 2):
            with self.subTest(seed=seed):
                kl = KL8E()
                m = self.start(kl, seed=seed)
                run_passes(self, m, restart=0o0200, passes=2)
                self.assertEqual(kl.printed, [])

    def test_bell(self):
        # One pass short of 1550 (octal 3016): the first pass rings the bell (TLS 0207, wait on TSF)
        # and resets the counter; the second pass counts 1.
        kl = KL8E()
        m = self.start(kl, counter=0o3015)
        run_passes(self, m, restart=0o0200, passes=2)
        self.assertEqual((kl.printed, m.memory.read(0, 0o3747)), ([0o207], 1))



class PassCriteria(unittest.TestCase):
    """maindec.classify: the end-of-pass text observed from each program, and error text."""

    def chars(self, s):
        return [ord(c) | 0o200 for c in s]

    def test_markers_and_line_breaks(self):
        D, nl = maindec.DIAGNOSTICS, [maindec.CR, maindec.LF]
        self.assertEqual(maindec.classify(D["d0db"], nl + self.chars("A") + nl + self.chars("A")), (2, []))
        self.assertEqual(maindec.classify(D["d0eb"], nl + self.chars("T")), (1, []))
        self.assertEqual(maindec.classify(D["d0gc"], [maindec.BEL]), (1, []))

    def test_error_text(self):
        D = maindec.DIAGNOSTICS
        self.assertEqual(maindec.classify(D["d0gc"], self.chars("E")), (0, self.chars("E")))
        self.assertEqual(maindec.classify(D["d0jc"], [maindec.RUBOUT] + self.chars("F")),
                         (0, self.chars("F")))

    def test_end_of_pass_names(self):
        # D0FC, D0HC, D0JC write-ups §9, as printed by full passes (start-up character included).
        D, nl = maindec.DIAGNOSTICS, [maindec.CR, maindec.LF]
        for name, start, printed in (("d0fc", [], self.chars("FC") + [maindec.RUBOUT]),
                                     ("d0hc", [maindec.NUL], self.chars("HC")),
                                     ("d0jc", [maindec.RUBOUT], self.chars("JC"))):
            with self.subTest(program=name):
                self.assertEqual(maindec.classify(D[name], start + (nl + printed) * 2), (2, []))

    def test_error_printouts_are_not_passes(self):
        # The examples of error printouts in the same write-ups (§6.2).
        D, nl = maindec.DIAGNOSTICS, [maindec.CR, maindec.LF]
        for name, lines in (("d0fc", ("F 3003 T 5470", "0 3705 F 4777 R 5000 S")),
                            ("d0fc", ("F 3003 T 5470", "0 3705 F 4777 R 5020  NS")),
                            ("d0hc", ("F 4252 TO 7020", "Z = 7000")),
                            ("d0jc", ("F 5236 TO 6354", "(TO) = 7402", "(4354) = 5237")),
                            ("d0jc", ("F 5236 TO 6354", "(TO) = 7237", "(6354) = 7237"))):
            with self.subTest(program=name, lines=lines):
                markers, errors = maindec.classify(D[name], [c for line in lines for c in nl + self.chars(line)])
                self.assertEqual(markers, 0)
                self.assertTrue(errors)

    def test_information_lines(self):
        d, out = maindec.DIAGNOSTICS["d1fb"], maindec.Outcome("d1fb")
        nl = [maindec.CR, maindec.LF]
        for line in ("8 STACKS IN THIS SYSTEM", "STACKS SEL'D ARE 7 6 5 4 3 2 1 0 ", "PROG WILL RELOCATE"):
            maindec._judge_line(d, self.chars(line) + nl, out)
        self.assertEqual((out.markers, out.error_text), (0, []))
        maindec._judge_line(d, nl + self.chars("5"), out)
        self.assertEqual((out.markers, out.error_text), (1, []))
        maindec._judge_line(d, self.chars("RELOCATION ERROR AT LOCATION 12345") + nl, out)
        self.assertTrue(out.error_text)

    def test_unfinished_lines_judged_early(self):
        # maindec.run judges an unfinished line after QUIET_LINE_STEPS without output only if it
        # holds nothing but markers and line breaks: D1FB's and D1BC's "5", but never the start
        # of an information line, which may contain a "5".
        d, nl = maindec.DIAGNOSTICS["d1bc"], [maindec.CR, maindec.LF]
        self.assertTrue(maindec.only_markers(d, self.chars("5")))
        self.assertTrue(maindec.only_markers(d, nl + self.chars("5")))
        for partial in ("5 STACKS", "STACKS SEL'D ARE 7 6 5", "8", ""):
            with self.subTest(partial=partial):
                self.assertFalse(maindec.only_markers(d, self.chars(partial)))
        self.assertFalse(maindec.only_markers(d, nl))

    def test_halt_only_programs_do_not_judge_text(self):
        self.assertEqual(maindec.classify(maindec.DIAGNOSTICS["d0cc"], self.chars("PASS")), (0, []))


class RandomAndSpecializedTests(unittest.TestCase):
    """MAINDEC-8E-D0CC to D0JC: bounded lock-step runs, under two core residues."""

    STEPS = 25_000

    def test_programs(self):
        for name in ("d0cc", "d0db", "d0eb", "d0fc", "d0gc", "d0hc", "d0ib", "d0jc"):
            for seed in (1, 2):
                with self.subTest(program=name, seed=seed):
                    outcome = maindec.run(name, self.STEPS, seed=seed)
                    self.assertTrue(outcome.passed, outcome.summary())
                    self.assertEqual(outcome.steps, self.STEPS, outcome.summary())



class MemoryTests(unittest.TestCase):
    """Phase 2: MAINDEC-8E-D1AA (4K checkerboard), D1EC (memory address test), D1HA (memory
    extension control, time share disabled), D1FB (extended memory address test), and D1BC
    (extended memory checkerboard), bounded lock-step runs under two core residues. Their passes
    run to millions of instructions, so no run reaches a pass marker; D1HA, D1FB, and D1BC each
    take their documented start-up halt and continue."""

    STEPS = 25_000

    def test_programs(self):
        for name in ("d1aa", "d1ec", "d1ha", "d1fb", "d1bc"):
            for seed in (1, 2):
                with self.subTest(program=name, seed=seed):
                    outcome = maindec.run(name, self.STEPS, seed=seed)
                    self.assertTrue(outcome.passed, outcome.summary())
                    self.assertEqual(outcome.steps, self.STEPS, outcome.summary())
                    if maindec.DIAGNOSTICS[name].continue_halts:
                        self.assertEqual(outcome.continued, 1, outcome.summary())


if __name__ == "__main__":
    unittest.main()
