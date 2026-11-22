"""Slice D (option2/plan.md phase 5): v2 instruction durations, TIMING_MODE 0.

docs/09-timing/02-timing-architecture.md §5.1: fast states (FETCH, DEFER with
AUTO_INDEX_REQUIRED = 0) 5/8/6/5 TSTEPs = 1.2 us; slow states (DEFER with
AUTO_INDEX_REQUIRED = 1, EXECUTE, INTERRUPT, DMA) 6/8/7/7 = 1.4 us; TSTEP 50 ns.
"""

import unittest

import _paths  # noqa: F401
from pdp8_cpu import design as D
from test_jmp_slice_b import HLT, JMP_300, JMP_I_10, JMP_I_50, machine

TAD_50, TAD_I_50, TAD_I_10, ISZ_50 = 0o1050, 0o1450, 0o1410, 0o2050


def first_instruction_ns(program):
    """Elapsed time at the first instruction boundary after START (TS by TS)."""
    cpu = machine(program)
    while True:
        r = cpu.step_ts()
        if cpu.boundary_kind(r) is not None:
            return cpu.elapsed_ns


class V2Durations(unittest.TestCase):
    def test_table(self):
        d = D.select("v2")
        self.assertEqual(d.ts_ns["FETCH"], (250, 400, 300, 250))      # 5/8/6/5 TSTEPs
        self.assertEqual(d.ts_ns["EXECUTE"], (300, 400, 350, 350))    # 6/8/7/7 TSTEPs
        self.assertEqual(d.state_ns()["DEFER"], 1200)
        for slow in (D.DEFER_AUTOINDEX, "EXECUTE", "INTERRUPT", "DMA"):
            self.assertEqual(d.state_ns()[slow], 1400, slow)

    def test_mri_is_2_6_us(self):
        self.assertEqual(first_instruction_ns({0o200: TAD_50, 0o50: 1}), 2600)

    def test_direct_jmp_is_one_fast_cycle(self):
        self.assertEqual(first_instruction_ns({0o200: JMP_300, 0o300: HLT}), 1200)

    def test_jmp_i_is_two_fast_cycles(self):
        self.assertEqual(first_instruction_ns({0o200: JMP_I_50, 0o50: 0o400, 0o400: HLT}), 2400)

    def test_autoindex_defer_is_slow(self):
        self.assertEqual(first_instruction_ns({0o200: JMP_I_10, 0o10: 0o477, 0o500: HLT}), 2600)
        self.assertEqual(first_instruction_ns({0o200: TAD_I_10, 0o10: 0o477}), 1200 + 1400 + 1400)

    def test_indirect_mri(self):
        self.assertEqual(first_instruction_ns({0o200: TAD_I_50, 0o50: 0o400}), 1200 + 1200 + 1400)

    def test_isz_jmp_loop_is_3_8_us(self):
        # The D2AB delay loop (ISZ + JMP back): 2 x 1.2 + 1.4 = 3.8 us, the PDP-8/E figure.
        cpu = machine({0o200: ISZ_50, 0o201: 0o5200, 0o50: 0o7770})
        boundaries = []
        while len(boundaries) < 5:
            r = cpu.step_ts()
            if cpu.boundary_kind(r) is not None:
                boundaries.append(cpu.elapsed_ns)
        self.assertEqual(boundaries[4] - boundaries[2], 3800)          # one ISZ + JMP iteration


if __name__ == "__main__":
    unittest.main()
