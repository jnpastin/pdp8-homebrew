import unittest

import _paths  # noqa: F401
from _paths import blank_fields
from pdp8_cpu import derived as D
from pdp8_cpu import design as DS
from pdp8_cpu import encodings as E
from pdp8_cpu.console import FrontPanel
from pdp8_cpu.datapath import alu, evaluate
from pdp8_cpu.errors import SpecGap, SpecViolation
from pdp8_cpu.inputs import Conditions, ExternalInputs, ir_decodes
from pdp8_cpu.state import CpuState
from pdp8_memory import Memory


class AluTests(unittest.TestCase):
    """MCS §7.3.1."""

    def test_add_carry_complements_link(self):
        self.assertEqual(alu(E.ADD, 0o7777, 0o0001, 0), (0, 1))
        self.assertEqual(alu(E.ADD, 0o7777, 0o0001, 1), (0, 0))
        self.assertEqual(alu(E.ADD, 0o0003, 0o0004, 1), (0o0007, 1))

    def test_inc(self):
        self.assertEqual(alu(E.INC, 0o7777, None, 0), (0, 1))
        self.assertEqual(alu(E.INC, 0o0176, None, 0), (0o0177, 0))

    def test_logic(self):
        self.assertEqual(alu(E.AND, 0o7070, 0o0770, 1), (0o0070, 1))
        self.assertEqual(alu(E.CLEAR, None, None, 1), (0, 1))

    def test_logic_of_the_v1_alu(self):  # V1-ONLY
        self.assertEqual(alu(E.OR, 0o7000, 0o0007, 0), (0o7007, 0))
        self.assertEqual(alu(E.NOT, 0o7070, None, 0), (0o0707, 0))
        self.assertEqual(alu(E.BSW, 0o1234, None, 0), (0o3412, 0))

    def test_rotates_are_a_13_bit_ring(self):  # V1-ONLY
        self.assertEqual(alu(E.ROR, 0o0001, None, 1), (0o4000, 1))   # RAR: L -> AC11, AC0 -> L
        self.assertEqual(alu(E.ROL, 0o4000, None, 1), (0o0001, 1))   # RAL
        self.assertEqual(alu(E.RTR, 0o0003, None, 0), (0o4000, 1))   # RTR: two places right
        self.assertEqual(alu(E.RTL, 0o6000, None, 0), (0o0001, 1))   # RTL: two places left

    def test_undefined_propagates(self):
        self.assertEqual(alu(E.ADD, None, 1, 0), (None, None))
        self.assertEqual(alu(E.AND, None, 1, 0), (None, 0))


class InputTests(unittest.TestCase):
    """docs/04-control/10-control-input-definitions/."""

    def test_iot_classes(self):
        caf, ion, tls, cdf = ir_decodes(0o6007), ir_decodes(0o6001), ir_decodes(0o6046), ir_decodes(0o6211)
        self.assertEqual((caf["IR_IS_CAF"], caf["IR_IS_EXTERNAL_IOT"]), (1, 0))
        self.assertEqual((ion["IR_IS_CAF"], ion["IR_IS_EXTERNAL_IOT"]), (0, 0))
        self.assertEqual(tls["IR_IS_EXTERNAL_IOT"], 1)
        self.assertEqual((cdf["IR_IS_MEMEXT_IOT"], cdf["IR_IS_EXTERNAL_IOT"], cdf["IR_WRITES_DF"]), (1, 0, 1))

    def test_mri_fields(self):
        d = ir_decodes(0o1777)  # TAD I, current page, offset 177
        self.assertEqual((d["IR_IS_MRI"], d["IR_INDIRECT"], d["IR_ZERO_PAGE"], d["IR_ADDR"]), (1, 1, 0, 0o177))
        d = ir_decodes(0o1577)  # TAD I, zero page, offset 177
        self.assertEqual((d["IR_INDIRECT"], d["IR_ZERO_PAGE"]), (1, 1))
        self.assertEqual(ir_decodes(0o7402)["IR_INDIRECT"], 0)  # OPR bit 8 is not an indirect bit

    def test_undefined_ir(self):
        d = ir_decodes(None)
        self.assertIsNone(d["IR_INDIRECT"])
        self.assertIsNone(d["IR_IS_CAF"])

    def _skip(self, ir, ac, link):
        st = CpuState()
        st["IR"], st["AC"], st["L"] = ir, ac, link
        return Conditions(st, ExternalInputs(), FrontPanel()).get("SKIP_TAKEN")

    def test_skip_taken(self):
        self.assertEqual(self._skip(0o7500, 0o4000, 0), 1)   # SMA, AC negative
        self.assertEqual(self._skip(0o7500, 0o0001, 0), 0)
        self.assertEqual(self._skip(0o7510, 0o0001, 0), 1)   # SPA, AC positive
        self.assertEqual(self._skip(0o7410, 0o0000, 0), 1)   # SKP
        self.assertEqual(self._skip(0o7420, 0o0000, 1), 1)   # SNL, L = 1
        self.assertEqual(self._skip(0o7430, 0o0000, 1), 0)   # SZL, L = 1
        self.assertEqual(self._skip(0o7440, 0o0000, 0), 1)   # SZA
        self.assertEqual(self._skip(0o7450, 0o0000, 0), 0)   # SNA, AC = 0
        self.assertEqual(self._skip(0o7001, 0o0000, 0), 0)   # not group 2

    def test_interrupt_request_valid(self):
        st = CpuState()
        st["IE"], st["II"] = 0, None
        self.assertEqual(Conditions(st, ExternalInputs(int_req_n=0), FrontPanel()).get("INTERRUPT_REQUEST_VALID"), 0)
        st["IE"], st["II"] = 1, 0
        self.assertEqual(Conditions(st, ExternalInputs(int_req_n=0), FrontPanel()).get("INTERRUPT_REQUEST_VALID"), 1)


class DatapathTests(unittest.TestCase):
    def setUp(self):
        self.st = CpuState()
        self.st.power_on()
        self.st["MA"], self.st["PC"], self.st["IF"], self.st["DF"], self.st["MB"] = 0o100, 0o200, 0, 0, 0o1234
        self.mem = Memory()
        self.panel = FrontPanel()
        self.ext = ExternalInputs()

    def run_word(self, design=None, **fields):
        """Evaluate one word; `design` names the wiring (default: PDP8_DESIGN)."""
        cond = Conditions(self.st, self.ext, self.panel)
        return evaluate(blank_fields(**fields), self.st, self.ext, self.panel, self.mem, cond, E.FETCH,
                        DS.select(design))

    def test_memory_read_into_mb(self):
        self.mem.preload(0, 0o100, [0o4321])
        fx = self.run_word(**{"/RD": 0, "MB_LOAD": 1, "MB_SRC": 1})
        self.assertEqual(fx.loads, {"MB": 0o4321})
        self.assertEqual(fx.mem_read, (0, 0o100))

    def test_memory_write_from_mb(self):
        fx = self.run_word(**{"/WR": 0, "MDB_SRC": 1})
        self.assertEqual(fx.mem_write, (0, 0o100, 0o1234))

    def test_read_and_write_together(self):
        with self.assertRaises(SpecViolation):
            self.run_word(**{"/RD": 0, "/WR": 0, "MDB_SRC": 1})

    def test_cpu_drives_mdb_during_read(self):
        with self.assertRaises(SpecViolation):
            self.run_word(**{"/RD": 0, "MB_LOAD": 1, "MB_SRC": 1, "MDB_SRC": 1})

    def test_write_without_cpu_driver(self):
        with self.assertRaises(SpecViolation):
            self.run_word(**{"/WR": 0, "MDB_SRC": 0})

    def test_idb_not_driven(self):
        with self.assertRaises(SpecViolation):
            self.run_word(AC_LOAD=1, AC_SRC=0, IDB_DRIVE=0)

    def test_reserved_select_only_matters_when_used(self):
        self.run_word(MA_LOAD=0, MA_SRC=3)                # not consumed: no effect (Control Word §5.6)
        with self.assertRaises(SpecViolation):
            self.run_word(MA_LOAD=1, MA_SRC=3)            # MA_SRC 3 is reserved in both designs

    def test_pc_inc_rules(self):
        add, inc = (E.alu_code(DS.select().name, op) for op in (E.ADD, E.INC))
        fx = self.run_word(PC_INC=1, ALU_OP=inc, ALU_A_SRC=2)
        self.assertEqual(fx.loads, {"PC": 0o201})
        with self.assertRaises(SpecViolation):
            self.run_word(PC_INC=1, ALU_OP=add, ALU_A_SRC=2)
        with self.assertRaises(SpecViolation):
            self.run_word(PC_INC=1, PC_LOAD=1, ALU_OP=inc, ALU_A_SRC=2)

    def test_binary_alu_needs_operand(self):
        with self.assertRaises(SpecViolation):
            self.run_word(AC_LOAD=1, AC_SRC=0, IDB_DRIVE=1, IDB_SRC=7, ALU_OP=E.alu_code(DS.select().name, E.ADD),
                          ALU_B_SRC=0)

    def test_ea_formation_page_from_ma(self):
        # v2: the page is MA[11:7], the instruction's address; PC has already advanced at FETCH TP1
        # (02-micro-operations.md IR_ADDR_TO_EA_ADDR). An instruction at the last word of a page
        # shows the difference: PC is on the next page.
        self.st["IR"], self.st["MA"], self.st["PC"] = 0o1300, 0o4777, 0o5000   # TAD, current page, offset 100
        fx = self.run_word("v2", EA_ADDR_LOAD=1, EA_ADDR_SRC=1)
        self.assertEqual(fx.loads["EA_ADDR"], 0o4700)
        self.st["IR"] = 0o1177                               # zero page
        fx = self.run_word("v2", EA_ADDR_LOAD=1, EA_ADDR_SRC=1)
        self.assertEqual(fx.loads["EA_ADDR"], 0o0177)

    def test_ea_formation_page_from_pc(self):  # V1-ONLY
        self.st["IR"], self.st["PC"] = 0o1377, 0o4777        # TAD, current page, offset 177
        fx = self.run_word("v1", EA_ADDR_LOAD=1, EA_ADDR_SRC=1)
        self.assertEqual(fx.loads["EA_ADDR"], 0o4777)
        self.st["IR"] = 0o1177                               # zero page
        fx = self.run_word("v1", EA_ADDR_LOAD=1, EA_ADDR_SRC=1)
        self.assertEqual(fx.loads["EA_ADDR"], 0o0177)

    def test_ir_loads_from_mdb_with_mb(self):
        # v2 MDB_TO_IR with MEM_READ_TO_MB: IR and MB load the same word at the same TP, one read.
        self.mem.preload(0, 0o100, [0o4321])
        fx = self.run_word("v2", **{"/RD": 0, "MB_LOAD": 1, "MB_SRC": 1, "IR_LOAD": 1})
        self.assertEqual(fx.loads, {"MB": 0o4321, "IR": 0o4321})
        self.assertEqual(fx.mem_read, (0, 0o100))

    def test_ir_load_needs_a_read(self):
        # v2 MCS IR_LOAD: requires a memory read in the same TS (IR's input is MDB).
        with self.assertRaises(SpecViolation):
            self.run_word("v2", IR_LOAD=1)

    def test_ir_loads_from_mb(self):  # V1-ONLY
        fx = self.run_word("v1", IR_LOAD=1)
        self.assertEqual(fx.loads, {"IR": 0o1234})

    def test_field_merges(self):
        self.st["AC"], self.st["IF"], self.st["DF"], self.st["IB"] = 0o0001, 5, 3, 0o72
        self.assertEqual(self.run_word(AC_LOAD=1, AC_SRC=2).loads["AC"], 0o0051)
        self.assertEqual(self.run_word(AC_LOAD=1, AC_SRC=3).loads["AC"], 0o0031)
        self.assertEqual(self.run_word(AC_LOAD=1, AC_SRC=4).loads["AC"], 0o0073)


class DerivedTests(unittest.TestCase):
    """CSO §5.1 against the direct-control definitions (DCI §5.2, §5.3, §7.2, §7.3)."""

    def test_running_contexts_agree(self):
        for ms in (E.FETCH, E.DEFER, E.EXECUTE, E.INTERRUPT, E.DMA):
            for ext_iot in (0, 1):
                D.check_derived(1, ms, ms, int(ms == E.EXECUTE), ext_iot)

    def test_halted_in_fetch_agrees(self):
        D.check_derived(0, E.FETCH, E.HALTED, 0, 1)

    def test_halted_in_dma(self):
        # DCI §5.3: /DMA_GRANT is deasserted while halted, including while MS = DMA holds a burst.
        self.assertEqual(D.check_derived(0, E.DMA, E.HALTED, 0, 0), (1, 0))

    def test_halted_in_execute_with_external_iot(self):
        # DCI §7.3: IOT_ACTIVE = 0 while halted, even with an external IOT in IR.
        self.assertEqual(D.check_derived(0, E.EXECUTE, E.HALTED, 0, 1), (1, 0))

    def test_disagreement_is_reported_as_a_spec_gap(self):
        # A decode that disagrees with the direct-control definitions is a SpecGap.
        original = D.dma_grant_n
        D.dma_grant_n = lambda mseff: 0
        try:
            with self.assertRaises(SpecGap):
                D.check_derived(1, E.FETCH, E.FETCH, 0, 0)
        finally:
            D.dma_grant_n = original

    def test_initialize_condition(self):
        self.assertEqual(D.initialize_asserted(1, E.EXECUTE, 4, 1, 0), 1)
        self.assertEqual(D.initialize_asserted(1, E.EXECUTE, 3, 1, 0), 0)
        self.assertEqual(D.initialize_asserted(None, E.FETCH, 1, 0, 1), 1)
        D.check_initialize(0, 1)
        with self.assertRaises(SpecViolation):
            D.check_initialize(1, 1)


if __name__ == "__main__":
    unittest.main()
