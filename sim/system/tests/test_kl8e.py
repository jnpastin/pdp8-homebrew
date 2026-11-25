"""The KL8E controller through the external-IOT microcode, compared in lock-step with the
reference model's instruction-level KL8E (docs/07-io/10-controllers/01-kl8e-uart.md)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system.lockstep import Lockstep
from pdp8_system.machine import KL8E, Machine, load_store

HLT, NOP = 0o7402, 0o7000


def run(blocks, kl=None, steps=200, typed=None):
    kl = kl or KL8E()
    m = Machine(load_store(), devices=[kl])                 # power-on initializes the controller
    for (f, a), words in blocks.items():
        m.deposit_block(a, words, instruction_field=f)
    m.load_address(0o200)
    m.start()                                               # START initializes the controller
    if typed is not None:
        kl.type_character(typed)                            # so the key arrives after START
    Lockstep(m).run(steps)
    return m, kl


class Teleprinter(unittest.TestCase):
    def test_tfl_tsf_tcf(self):
        # TFL; TSF (skips); HLT; TCF; TSF (no skip); IAC; HLT
        m, kl = run({(0, 0o200): [0o6040, 0o6041, HLT, 0o6042, 0o6041, 0o7001, HLT]})
        self.assertEqual((m.state["AC"], m.state["PC"], kl.teleprinter_flag), (1, 0o207, 0))

    def test_tls_prints_and_the_flag_sets_on_completion(self):
        # TAD char; TLS; TSF; JMP .-1; HLT
        m, kl = run({(0, 0o200): [0o1210, 0o6046, 0o6041, 0o5202, HLT], (0, 0o210): [0o0301]})
        self.assertEqual((kl.printed, kl.teleprinter_flag, m.state["PC"]), ([0o301], 1, 0o205))

    def test_tsk(self):
        m, _ = run({(0, 0o200): [0o6045, HLT, 0o6040, 0o6045, HLT, HLT]})
        self.assertEqual(m.state["PC"], 0o202)          # no flag: no skip
        m, _ = run({(0, 0o200): [0o6040, 0o6045, HLT, HLT]})
        self.assertEqual(m.state["PC"], 0o204)


class Keyboard(unittest.TestCase):
    def test_ksf_krb_kcc(self):
        kl = KL8E()
        # KSF (skips); HLT; KRB; DCA 220; KCC with AC set; HLT
        m, _ = run({(0, 0o200): [0o6031, HLT, 0o6036, 0o3220, 0o7040, 0o6032, HLT]}, kl, typed=0o315)
        self.assertEqual(m.memory.read(0, 0o220), 0o315)
        self.assertEqual((m.state["AC"], kl.keyboard_flag), (0, 0))

    def test_krs_does_not_clear_the_flag(self):
        kl = KL8E()
        m, _ = run({(0, 0o200): [0o7240, 0o6034, HLT]}, kl, typed=0o101)   # STA; KRS: OR into AC
        self.assertEqual((m.state["AC"], kl.keyboard_flag), (0o7777, 1))


class Interrupts(unittest.TestCase):
    def test_enabled_after_initialization(self):
        # KL8E §8 (gap G): CLEAR or power-on leaves the interrupt enable set. TFL; ION; NOP -> interrupt.
        m, _ = run({(0, 0o200): [0o6040, 0o6001, NOP, HLT], (0, 0o001): [HLT]})
        self.assertEqual((m.memory.read(0, 0), m.state["PC"]), (0o203, 0o002))

    def test_kie_disables(self):
        # CLA; KIE (AC[0] = 0); TFL; ION; NOP; HLT -> no interrupt
        m, kl = run({(0, 0o200): [0o7200, 0o6035, 0o6040, 0o6001, NOP, HLT], (0, 0o001): [HLT]})
        self.assertEqual((kl.interrupt_enable, m.state["PC"]), (0, 0o206))

    def test_kie_enabling_counts_at_its_own_completion(self):
        # KL8E §15 (review C10): KIE commits at TP3, so an enabling KIE allows the interrupt at its
        # own completion: CLA; KIE (off); TFL; ION; NOP; IAC; KIE (on) -> return address 0207.
        m, _ = run({(0, 0o200): [0o7200, 0o6035, 0o6040, 0o6001, NOP, 0o7001, 0o6035, NOP, HLT],
                     (0, 0o001): [HLT]})
        self.assertEqual(m.memory.read(0, 0), 0o207)

    def test_kie_disabling_counts_at_its_own_completion(self):
        # Review C10: CLA; TFL; ION; KIE (off); HLT. The KIE is the first eligible completion, and
        # its TP3 disable is seen there, so no interrupt is taken.
        m, kl = run({(0, 0o200): [0o7200, 0o6040, 0o6001, 0o6035, HLT], (0, 0o001): [HLT]})
        self.assertEqual((kl.interrupt_enable, m.state["PC"]), (0, 0o205))

    def test_ion_krb_takes_no_interrupt(self):
        # Review C10: the keyboard flag is the only request; KRB clears it at TP3, so the decision
        # at KRB's TP4 sees no request.
        m, kl = run({(0, 0o200): [0o6001, 0o6036, HLT], (0, 0o001): [HLT]}, typed=0o301)
        self.assertEqual((m.state["AC"], kl.keyboard_flag, m.state["PC"]), (0o301, 0, 0o203))

    def test_ion_tls_takes_no_interrupt(self):
        # Review C10: TFL; ION; TLS. TLS clears the teleprinter flag at TP3, so its completion
        # takes no interrupt; the flag sets again when the character completes.
        m, kl = run({(0, 0o200): [0o6040, 0o6001, 0o6046, HLT], (0, 0o001): [HLT]})
        self.assertEqual(m.state["PC"], 0o204)

    def test_caf_initializes_the_controller(self):
        kl = KL8E()
        run({(0, 0o200): [0o7200, 0o6035, 0o6040, 0o6007, HLT]}, kl)
        self.assertEqual((kl.teleprinter_flag, kl.interrupt_enable), (0, 1))


if __name__ == "__main__":
    unittest.main()
