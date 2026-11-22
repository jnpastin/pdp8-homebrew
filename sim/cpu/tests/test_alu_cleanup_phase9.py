"""Phase 9 ALU cleanup (option2/spec.md decision 13), v2: the OPR-only ALU codes are gone.

- MCS ALU_OP (2 bits: ADD, AND, INC, CLEAR), ALU_B_SRC (1 bit: NONE, MB); AC_SRC 5, reserved by
  decision 13, is ZERO since review item D2
- MCS §7.3.1 (the operations that remain)
- CSO §7.2 (44 datapath bits)
"""

import unittest

import _paths  # noqa: F401
from _paths import blank_fields
from pdp8_cpu import design as DS
from pdp8_cpu import encodings as E
from pdp8_cpu.console import FrontPanel
from pdp8_cpu.datapath import evaluate
from pdp8_cpu.errors import SpecViolation
from pdp8_cpu.images import ControlStore
from pdp8_cpu.inputs import Conditions, ExternalInputs
from pdp8_cpu.state import CpuState
from pdp8_memory import Memory


class Encodings(unittest.TestCase):
    def test_field_definitions(self):
        f = E.datapath_fields("v2")
        self.assertEqual((f["ALU_OP"].width, f["ALU_OP"].values),
                         (2, {0: "ADD", 1: "AND", 2: "INC", 3: "CLEAR"}))
        self.assertEqual((f["ALU_B_SRC"].width, f["ALU_B_SRC"].values), (1, {0: "NONE", 1: "MB"}))
        self.assertEqual(f["AC_SRC"].values[5], "ZERO")

    def test_packed_width(self):
        store = ControlStore.load(design=DS.select("v2"))
        self.assertEqual(store.packing["summary"]["datapath_bits"], 44)


class Datapath(unittest.TestCase):
    def setUp(self):
        self.st = CpuState()
        self.st.power_on()
        self.st["AC"], self.st["L"], self.st["MB"], self.st["MQ"] = 0o7070, 1, 0o1770, 0o2525
        self.st["MA"], self.st["PC"], self.st["IF"], self.st["DF"] = 0o100, 0o200, 0, 0
        self.panel, self.ext = FrontPanel(), ExternalInputs()

    def run_word(self, **fields):
        cond = Conditions(self.st, self.ext, self.panel)
        return evaluate(blank_fields(**fields), self.st, self.ext, self.panel, Memory(), cond, E.FETCH,
                        DS.select("v2"))

    def through_alu(self, op, b_src):
        loads = self.run_word(AC_LOAD=1, AC_SRC=0, L_LOAD=1, L_OP=2, IDB_DRIVE=1, IDB_SRC=7,
                              ALU_A_SRC=0, ALU_B_SRC=b_src, ALU_OP=op).loads
        return loads["AC"], loads["L"]

    def test_each_code_selects_its_operation(self):
        self.assertEqual(self.through_alu(0, 1), (0o1060, 0))     # ADD: the carry complements L
        self.assertEqual(self.through_alu(1, 1), (0o1070, 1))     # AND
        self.assertEqual(self.through_alu(2, 0), (0o7071, 1))     # INC
        self.assertEqual(self.through_alu(3, 0), (0o0000, 1))     # CLEAR

    def test_removed_b_sources_are_rejected(self):
        for b_src in (2, 3):                                      # v1's MQ and FP_SR
            with self.assertRaises(SpecViolation):
                self.through_alu(0, b_src)

    def test_removed_operations_are_rejected(self):
        for op in range(4, 0o20):
            with self.assertRaises(SpecViolation):
                self.through_alu(op, 0)

    def test_ac_src_5_loads_zero_without_the_alu(self):
        loads = self.run_word(AC_LOAD=1, AC_SRC=5, PC_INC=1, ALU_A_SRC=2, ALU_OP=2).loads
        self.assertEqual((loads["AC"], loads["PC"]), (0, 0o201))


if __name__ == "__main__":
    unittest.main()
