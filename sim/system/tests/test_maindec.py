"""Milestone M3: DEC MAINDEC-8E diagnostics, loaded through the console and run in lock-step.

Each program is operated as its write-up directs (sim/test_programs/*/…-d.pdf, §4.3). A pass is
a return to the program's restart point with no error halt; the simulator and the reference
model must agree on every instruction.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

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


if __name__ == "__main__":
    unittest.main()
