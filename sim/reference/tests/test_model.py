"""The reference model alone, against values derived by hand from docs/02-isa and docs/08.

These are the expectations of the M1 suite (sim/system/tests/test_instructions.py), checked here
against the reference model, so a mistake in the model and a mistake in the simulator cannot hide
one another.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_reference import Reference, ReferenceError, disassemble

HLT, NOP = 0o7402, 0o7000


def ref_with(blocks, pc=0o200, field=0, data_field=None):
    r = Reference()
    for (f, a), words in blocks.items():
        for k, w in enumerate(words):
            r.memory[f][a + k] = w
    r.pc, r.if_, r.df = pc, field, field if data_field is None else data_field
    return r


def run(r, max_steps=1000, int_req=False):
    r.int_req = int_req
    for _ in range(max_steps):
        if r.step().halted:
            return r
    raise AssertionError("did not halt")


class MemoryReference(unittest.TestCase):
    def test_and_tad_dca(self):
        r = run(ref_with({(0, 0o200): [0o7300, 0o1250, 0o1251, 0o3252, 0o1253, 0o0254, HLT],
                          (0, 0o250): [0o3777, 0o0001, 0o1111, 0o7070, 0o0770]}))
        self.assertEqual((r.memory[0][0o252], r.ac, r.l), (0o4000, 0o0070, 0))

    def test_isz_and_skip(self):
        r = run(ref_with({(0, 0o200): [0o2210, 0o2211, HLT, HLT], (0, 0o210): [0o0005, 0o7777]}))
        self.assertEqual((r.memory[0][0o210], r.memory[0][0o211], r.pc), (6, 0, 0o204))

    def test_current_page_uses_the_instructions_page(self):
        r = run(ref_with({(0, 0o377): [0o1376], (0, 0o376): [0o0055], (0, 0o576): [0o0077],
                          (0, 0o400): [HLT]}, pc=0o377))
        self.assertEqual(r.ac, 0o0055)

    def test_autoindex(self):
        r = run(ref_with({(0, 0o200): [0o7300, 0o1410, 0o1410, 0o3410, HLT],
                          (0, 0o010): [0o0277], (0, 0o300): [0o0005, 0o0006]}))
        self.assertEqual((r.memory[0][0o010], r.memory[0][0o302]), (0o0302, 0o0013))

    def test_jms_indirect_after_cif_stores_in_new_field(self):
        r = run(ref_with({(0, 0o200): [0o6212, 0o4620, HLT], (0, 0o220): [0o0400],
                          (1, 0o400): [0, 0o7001, HLT]}))
        self.assertEqual((r.memory[1][0o400], r.memory[0][0o400], r.if_, r.pc), (0o202, None, 1, 0o403))

    def test_indirect_operand_uses_df(self):
        r = run(ref_with({(0, 0o200): [0o7300, 0o6211, 0o1620, HLT], (0, 0o220): [0o0500],
                          (1, 0o500): [0o0777]}))
        self.assertEqual((r.df, r.ac), (1, 0o0777))


class Operate(unittest.TestCase):
    def one(self, ir, ac, link, mq=0o5252, sr=0o1234):
        r = ref_with({(0, 0o200): [ir, HLT, HLT]})
        r.ac, r.l, r.mq, r.sr = ac, link, mq, sr
        return run(r)

    def test_group1(self):
        self.assertEqual((self.one(0o7041, 0o0005, 0).ac,), (0o7773,))       # CIA
        r = self.one(0o7012, 0o0003, 0)                                       # RTR
        self.assertEqual((r.ac, r.l), (0o4000, 1))
        r = self.one(0o7014, 0o3456, 1)                                       # RAR RAL: no rotate
        self.assertEqual((r.ac, r.l), (0o3456, 1))
        self.assertEqual(self.one(0o7002, 0o1234, 0).ac, 0o3412)              # BSW

    def test_group2(self):
        self.assertEqual(self.one(0o7604, 0o7777, 0).ac, 0o1234)              # LAS = CLA OSR
        self.assertEqual(self.one(0o7410, 0, 0).pc, 0o203)                    # SKP
        self.assertEqual(self.one(0o7450, 0, 0).pc, 0o202)                    # SNA, AC = 0

    def test_group3(self):
        r = self.one(0o7721, 0o1111, 0, mq=0o2222)                            # CLA SWP
        self.assertEqual((r.ac, r.mq), (0o2222, 0))


class ProcessorAndMemoryExtensionIots(unittest.TestCase):
    def test_gtf(self):
        r = run(ref_with({(1, 0o200): [0o7120, 0o6231, 0o6001, 0o6004, HLT]}, field=1))
        self.assertEqual(r.ac, 0o4213)

    def test_rtf(self):
        r = run(ref_with({(0, 0o200): [0o7300, 0o1210, 0o6005, 0o5611], (0, 0o210): [0o4013, 0o0300],
                          (1, 0o300): [HLT]}))
        self.assertEqual((r.l, r.df, r.if_, r.ie, r.pc), (1, 3, 1, 1, 0o301))

    def test_rib_before_any_interrupt_is_refused(self):
        r = ref_with({(0, 0o200): [0o6234, HLT]})
        with self.assertRaises(ReferenceError):
            run(r)

    def test_undefined_memory_is_refused(self):
        with self.assertRaises(ReferenceError):
            run(ref_with({(0, 0o200): [0o1300, HLT]}))


class Interrupts(unittest.TestCase):
    def test_ion_delay_and_entry(self):
        r = run(ref_with({(3, 0o200): [0o6251, 0o6001, NOP, HLT], (0, 0o001): [HLT]}, field=3),
                int_req=True)
        self.assertEqual((r.memory[0][0], r.ib, r.if_, r.df, r.pc), (0o203, 0o35, 0, 0, 0o002))

    def test_cif_window(self):
        r = run(ref_with({(0, 0o200): [0o6001, 0o6212, 0o5300], (1, 0o300): [NOP, HLT],
                          (0, 0o001): [HLT]}), int_req=True)
        self.assertEqual((r.memory[0][0], r.ib), (0o301, 0o10))

    def test_no_interrupt_at_caf_completion(self):
        r = run(ref_with({(0, 0o200): [0o6001, 0o6007, HLT]}), int_req=True)
        self.assertEqual((r.pc, r.memory[0][0]), (0o203, None))


class Disassembly(unittest.TestCase):
    def test_names(self):
        cases = {0o1620: "TAD I 020", 0o5200: "JMP 000", 0o7300: "CLA CLL", 0o7041: "CMA IAC",
                 0o7410: "SKP", 0o7721: "CLA SWP", 0o7621: "CLA MQL", 0o6212: "CIF 10", 0o6233: "CDF 30 CIF 30",
                 0o6244: "RMF", 0o6046: "IOT 6046", 0o6007: "CAF"}
        for ir, text in cases.items():
            self.assertEqual(disassemble(ir), text, f"{ir:04o}")


if __name__ == "__main__":
    unittest.main()
