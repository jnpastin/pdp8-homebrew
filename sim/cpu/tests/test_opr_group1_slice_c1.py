"""Slice C1 (option2/plan.md phase 6), run on the packed v2 images: OPR Group 1 completes in FETCH
through the OPR pass unit.

- docs/03-microarchitecture/07-opr/01-group1-execution.md §3, §4 (the pass and its stages)
- docs/02-isa/01-group-1.md (the semantics, notes 1 to 4), which the reference model implements
- docs/09-timing/02-timing-architecture.md §5.1 (a FETCH is 1.2 µs)
"""

import itertools
import sys
import unittest
from pathlib import Path

import _paths  # noqa: F401

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reference" / "src"))
from pdp8_cpu import design as D
from pdp8_cpu import encodings as E
from pdp8_reference import Reference
from test_jmp_slice_b import HLT, machine, run, states

GROUP1 = range(0o7000, 0o7400)                     # all 256 Group 1 encodings
AC_EDGES = (0o0000, 0o0001, 0o3777, 0o4000, 0o5252, 0o2525, 0o7776, 0o7777, 0o1354, 0o0077)


def run_opr(ir, ac, link):
    """Execute `ir` at 0200 (HLT at 0201) with AC and L preset; return (AC, L, states)."""
    cpu = machine({0o200: ir, 0o201: HLT})
    cpu.st["AC"], cpu.st["L"] = ac, link          # START cleared them; set before the first TS
    records = run(cpu)
    return cpu.st["AC"], cpu.st["L"], states(records)


def reference(ir, ac, link):
    ref = Reference()
    ref.ac, ref.l = ac, link
    ref._group1(ir)
    return ref.ac, ref.l


class ExhaustiveGroup1(unittest.TestCase):
    def test_every_encoding_and_edge_value_agrees_with_the_reference(self):
        mismatches = []
        for ir, ac, link in itertools.product(GROUP1, AC_EDGES, (0, 1)):
            got_ac, got_l, path = run_opr(ir, ac, link)
            want = reference(ir, ac, link)
            if (got_ac, got_l) != want or path[:2] != ["FETCH", "FETCH"]:
                mismatches.append(f"{ir:04o} AC={ac:04o} L={link}: got {got_ac:04o}/{got_l} "
                                  f"via {path[:2]}, reference {want[0]:04o}/{want[1]}")
        self.assertEqual(mismatches[:10], [], f"{len(mismatches)} mismatches")


class Targeted(unittest.TestCase):
    def check(self, ir, ac, link, want_ac, want_l):
        got_ac, got_l, path = run_opr(ir, ac, link)
        self.assertEqual((got_ac, got_l), (want_ac, want_l), f"{ir:04o}")
        self.assertEqual(path[:2], ["FETCH", "FETCH"])            # completes in FETCH

    def test_cia_complements_then_increments(self):
        self.check(0o7041, 0o1354, 0, 0o6424, 0)                   # Group 1 ISA §2 example

    def test_iac_overflow_complements_link(self):
        self.check(0o7001, 0o7777, 0, 0o0000, 1)
        self.check(0o7001, 0o7777, 1, 0o0000, 0)

    def test_bsw(self):
        self.check(0o7002, 0o1234, 1, 0o3412, 1)

    def test_rotates_carry_through_link(self):
        self.check(0o7010, 0o0001, 0, 0o0000, 1)                   # RAR: AC bit 11 (LSB) into L
        self.check(0o7004, 0o4000, 0, 0o0000, 1)                   # RAL: AC bit 0 (MSB) into L
        self.check(0o7012, 0o0001, 0, 0o4000, 0)                   # RTR: through L into AC
        self.check(0o7006, 0o4000, 0, 0o0001, 0)                   # RTL

    def test_rar_with_ral_neither_rotates_nor_swaps(self):
        self.check(0o7017, 0o1234, 0, 0o1235, 0)                   # IAC still acts (note 4)
        self.check(0o7016, 0o1234, 1, 0o1234, 1)                   # BSW ignored too

    def test_cla_iac_is_one(self):
        self.check(0o7201, 0o5555, 1, 0o0001, 1)

    def test_group1_costs_one_fetch(self):
        d = D.select("v2")
        self.assertEqual(D.major_states(d, 0o7041), ("FETCH",))
        cpu = machine({0o200: 0o7041, 0o201: HLT})
        while True:
            r = cpu.step_ts()
            if cpu.boundary_kind(r) is not None:
                break
        self.assertEqual((r.ms, r.ts, cpu.elapsed_ns), (E.FETCH, 4, 1200))


if __name__ == "__main__":
    unittest.main()
