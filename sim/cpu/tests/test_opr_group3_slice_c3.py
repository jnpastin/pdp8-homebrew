"""Slice C3 (option2/plan.md phase 8), run on the packed v2 images: OPR Group 3 completes in FETCH.

- docs/03-microarchitecture/07-opr/03-group3-execution.md §3, §4 (CLA and MQL zero AC, MQA ORs MQ;
  MQ loads from the pass unit's MQ output, which is MQ itself without MQL)
- docs/03-microarchitecture/04-fetch-defer.md §3.3 (OPR_PASS and OPR_PASS_TO_MQ at FETCH TP3)
- docs/02-isa/03-group-3.md (the semantics), which the reference model implements
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

GROUP3 = range(0o7401, 0o10000, 2)                     # all 256 Group 3 encodings
AC_EDGES = (0o0000, 0o0001, 0o3777, 0o4000, 0o5252, 0o2525, 0o7776, 0o7777, 0o1354, 0o0077)
MQ_EDGES = (0o0000, 0o7777, 0o2525, 0o1234)
MQA, MQL, SWP, CLA = 0o7501, 0o7421, 0o7521, 0o7601
CLA_MQA, CLA_MQL, CLA_SWP = 0o7701, 0o7621, 0o7721
EAE_BITS = 0o056                                      # IR bits 5, 3, 2, 1: SCA and EAE op code


def one_instruction(ir, ac, link, mq):
    """Run `ir` at 0200 for one FETCH (four TSs) with AC, L, and MQ preset."""
    cpu = machine({0o200: ir, 0o201: HLT})
    cpu.st["AC"], cpu.st["L"], cpu.st["MQ"] = ac, link, mq
    return cpu, [cpu.step_ts() for _ in range(4)]


def reference(ir, ac, link, mq):
    ref = Reference()
    ref.ac, ref.l, ref.mq = ac, link, mq
    ref._group3(ir)
    return ref.ac, ref.l, ref.mq


class ExhaustiveGroup3(unittest.TestCase):
    def test_every_encoding_and_edge_value_agrees_with_the_reference(self):
        mismatches = []
        for ir, ac, link, mq in itertools.product(GROUP3, AC_EDGES, (0, 1), MQ_EDGES):
            cpu, records = one_instruction(ir, ac, link, mq)
            st = cpu.st
            got = (st["AC"], st["L"], st["MQ"])
            want = reference(ir, ac, link, mq)
            in_fetch = (all(r.ms == E.FETCH for r in records) and (st["MS"], st.ts) == (E.FETCH, 1)
                        and st["PC"] == 0o201)
            if got != want or not in_fetch:
                mismatches.append(f"{ir:04o} AC={ac:04o} L={link} MQ={mq:04o}: got {got}, "
                                  f"reference {want}, completed in FETCH {in_fetch}")
        self.assertEqual(mismatches[:10], [], f"{len(mismatches)} mismatches")


class Targeted(unittest.TestCase):
    def check(self, ir, ac, mq, want_ac, want_mq):
        cpu, records = one_instruction(ir, ac, 0, mq)
        self.assertEqual((cpu.st["AC"], cpu.st["MQ"]), (want_ac, want_mq), f"{ir:04o}")
        return records

    def test_swp_exchanges_in_one_tp(self):
        records = self.check(SWP, 0o1111, 0o2222, 0o2222, 0o1111)
        tp3 = records[2].loads
        self.assertEqual((tp3["AC"], tp3["MQ"]), (0o2222, 0o1111))  # both loads at FETCH TP3

    def test_cla_acts_before_the_mq_operation(self):
        self.check(CLA_SWP, 0o1111, 0o2222, 0o2222, 0o0000)
        self.check(CLA_MQL, 0o1111, 0o2222, 0o0000, 0o0000)
        self.check(CLA_MQA, 0o1111, 0o2222, 0o2222, 0o2222)

    def test_mql_and_mqa(self):
        self.check(MQL, 0o1111, 0o2222, 0o0000, 0o1111)
        self.check(MQA, 0o1111, 0o2222, 0o3333, 0o2222)
        self.check(CLA, 0o1111, 0o2222, 0o0000, 0o2222)

    def test_mq_reloads_unchanged_without_mql(self):
        records = self.check(MQA, 0o0101, 0o0707, 0o0707, 0o0707)
        self.assertEqual(records[2].loads["MQ"], 0o0707)           # MQ loads every Group 3 OPR

    def test_eae_bits_select_nothing(self):
        for ir in (MQA, MQL, SWP, CLA, CLA_SWP):
            a = one_instruction(ir, 0o1234, 1, 0o4321)[0].st
            b = one_instruction(ir | EAE_BITS, 0o1234, 1, 0o4321)[0].st
            self.assertEqual((a["AC"], a["L"], a["MQ"]), (b["AC"], b["L"], b["MQ"]), f"{ir:04o}")

    def test_link_is_unchanged(self):
        for ir, link in itertools.product((SWP, CLA_MQL, MQA), (0, 1)):
            cpu, _ = one_instruction(ir, 0o7777, link, 0o7777)
            self.assertEqual(cpu.st["L"], link)

    def test_group3_costs_one_fetch(self):
        d = D.select("v2")
        self.assertEqual(D.major_states(d, SWP), ("FETCH",))
        cpu, records = one_instruction(SWP, 0, 0, 0)
        self.assertEqual(cpu.boundary_kind(records[3]), "instruction")
        self.assertEqual(cpu.elapsed_ns, 1200)

    def test_interrupt_after_swp(self):
        cpu = machine({0o200: SWP, 0o1: HLT})
        cpu.st["IE"], cpu.ext.int_req_n = 1, 0
        cpu.st["AC"], cpu.st["MQ"] = 0o0005, 0o0006
        records = run(cpu)
        self.assertEqual(states(records)[:2], ["FETCH", "INTERRUPT"])
        self.assertEqual((cpu.memory.read(0, 0), cpu.st["AC"], cpu.st["MQ"]), (0o201, 0o0006, 0o0005))


if __name__ == "__main__":
    unittest.main()
