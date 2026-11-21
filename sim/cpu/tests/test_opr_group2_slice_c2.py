"""Slice C2 (option2/plan.md phase 7), run on the packed v2 images: OPR Group 2 completes in FETCH.

- docs/03-microarchitecture/07-opr/02-group2-execution.md (CLA and OSR through the pass unit; the
  skip decision into SKIP at FETCH TP3; HLT_REQ at FETCH TP3)
- docs/03-microarchitecture/04-fetch-defer.md §3.3, §3.4 (PC_INC at FETCH TP4 when SKIP = 1)
- docs/08-interrupts-and-skip/05-skip-model.md §12, §14 (a skip and an interrupt at the same TP4:
  the interrupt saves the incremented PC; decision 4)
- docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md §3.4.4,
  §3.4.6 (the HLT request is consumed at the instruction's completion, FETCH TP4)
- docs/02-isa/02-group-2.md (the semantics), which the reference model implements
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
from pdp8_reference.model import StepResult
from test_jmp_slice_b import HLT, machine, run, states

GROUP2 = [ir for ir in range(0o7400, 0o10000) if not ir & 1]   # all 256 Group 2 encodings
AC_EDGES = (0o0000, 0o0001, 0o3777, 0o4000, 0o5252, 0o2525, 0o7776, 0o7777, 0o1354, 0o0077)
SR_EDGES = (0o0000, 0o7777, 0o5252)
SKP, SMA_CLA, SZA_CLA, CLA_OSR, OSR = 0o7410, 0o7700, 0o7640, 0o7604, 0o7404
SNA_HLT, CLA_IAC, ION = 0o7452, 0o7201, 0o6001


def one_instruction(ir, ac, link, sr):
    """Run `ir` at 0200 for one FETCH (four TSs) with AC, L, and SR preset. Returns the CPU and the
    four records."""
    cpu = machine({0o200: ir})
    cpu.st["AC"], cpu.st["L"] = ac, link
    cpu.panel.sr = sr
    return cpu, [cpu.step_ts() for _ in range(4)]


def reference(ir, ac, link, sr):
    ref = Reference()
    ref.ac, ref.l, ref.sr, ref.pc = ac, link, sr, 0o201       # PC already advanced past 0200
    result = StepResult("instruction", 0o200, 0, ir)
    ref._group2(ir, result)
    return ref.ac, ref.l, ref.pc, result.halted


class ExhaustiveGroup2(unittest.TestCase):
    def test_every_encoding_and_edge_value_agrees_with_the_reference(self):
        mismatches = []
        for ir, ac, link, sr in itertools.product(GROUP2, AC_EDGES, (0, 1), SR_EDGES):
            cpu, records = one_instruction(ir, ac, link, sr)
            st = cpu.st
            got = (st["AC"], st["L"], st["PC"], st["RUN"] == 0)
            want = reference(ir, ac, link, sr)
            in_fetch = all(r.ms == E.FETCH for r in records) and (st["MS"], st.ts) == (E.FETCH, 1)
            if got != want or not in_fetch or st["HLT_REQ"] != 0:
                mismatches.append(f"{ir:04o} AC={ac:04o} L={link} SR={sr:04o}: got {got}, "
                                  f"reference {want}, completed in FETCH {in_fetch}")
        self.assertEqual(mismatches[:10], [], f"{len(mismatches)} mismatches")


class Targeted(unittest.TestCase):
    def check(self, ir, ac, link, sr, want_ac, want_pc):
        cpu, _ = one_instruction(ir, ac, link, sr)
        self.assertEqual((cpu.st["AC"], cpu.st["PC"]), (want_ac, want_pc), f"{ir:04o}")
        return cpu

    def test_skip_decision_uses_ac_before_cla(self):
        self.check(SMA_CLA, 0o4000, 0, 0, 0o0000, 0o202)       # negative: skips, then cleared
        self.check(SMA_CLA, 0o0001, 0, 0, 0o0000, 0o201)       # positive: no skip, cleared
        self.check(SZA_CLA, 0o0000, 0, 0, 0o0000, 0o202)
        self.check(SZA_CLA, 0o0005, 0, 0, 0o0000, 0o201)

    def test_skp_always_skips(self):
        for ac, link in itertools.product((0, 0o4000, 0o7777), (0, 1)):
            self.check(SKP, ac, link, 0, ac, 0o202)

    def test_osr_ors_the_switch_register(self):
        self.check(OSR, 0o0707, 0, 0o1010, 0o1717, 0o201)
        self.check(CLA_OSR, 0o0707, 0, 0o1010, 0o1010, 0o201)  # CLA before OSR: AC <- SR

    def test_tp_by_tp(self):
        # SKIP loads at TP3 with the decision; AC loads from the pass unit at TP3; PC increments
        # at TP4; HLT_REQ is set at TP3 and consumed at TP4.
        cpu, records = one_instruction(SNA_HLT, 0o0003, 0, 0)
        tp3, tp4 = records[2].loads, records[3].loads
        self.assertEqual((tp3["SKIP"], tp3["AC"], tp3["HLT_REQ"]), (1, 0o0003, 1))
        self.assertEqual((tp4["PC"], tp4["HLT_REQ"], tp4["RUN"]), (0o202, 0, 0))
        self.assertNotIn("SKIP", tp4)

    def test_no_skip_leaves_pc(self):
        cpu, records = one_instruction(SNA_HLT, 0o0000, 0, 0)
        self.assertEqual(records[2].loads["SKIP"], 0)
        self.assertNotIn("PC", records[3].loads)
        self.assertEqual((cpu.st["PC"], cpu.st["RUN"]), (0o201, 0))

    def test_group2_costs_one_fetch(self):
        d = D.select("v2")
        self.assertEqual(D.major_states(d, SKP), ("FETCH",))
        cpu, records = one_instruction(SKP, 0, 0, 0)
        self.assertTrue(cpu.boundary_kind(records[3]) == "instruction")
        self.assertEqual(cpu.elapsed_ns, 1200)


class SkipAndInterruptAtTheSameTp4(unittest.TestCase):
    def test_interrupt_saves_the_skip_target(self):
        # Decision 4 (spec §6.2): the increment commits at FETCH TP4 with the recognition; the
        # INTERRUPT state saves the incremented PC, the same return address DEC's 8/E saves.
        cpu = machine({0o200: SKP, 0o1: HLT})
        cpu.st["IE"], cpu.ext.int_req_n = 1, 0
        records = run(cpu)
        self.assertEqual(states(records)[:3], ["FETCH", "INTERRUPT", "FETCH"])
        self.assertEqual(cpu.memory.read(0, 0), 0o202)

    def test_interrupt_after_a_skip_not_taken(self):
        cpu = machine({0o200: SMA_CLA, 0o1: HLT})
        cpu.st["IE"], cpu.ext.int_req_n = 1, 0
        cpu.st["AC"] = 0o0001
        records = run(cpu)
        self.assertEqual(states(records)[:2], ["FETCH", "INTERRUPT"])
        self.assertEqual(cpu.memory.read(0, 0), 0o201)

    def test_ion_then_skp(self):
        # ION's own completion is inhibited; the SKP after it is the first eligible boundary.
        cpu = machine({0o200: ION, 0o201: SKP, 0o1: HLT})
        cpu.ext.int_req_n = 0
        records = run(cpu)
        self.assertEqual(states(records)[:4], ["FETCH", "EXECUTE", "FETCH", "INTERRUPT"])
        self.assertEqual(cpu.memory.read(0, 0), 0o203)

    def test_dma_entered_at_skip_completion(self):
        cpu = machine({0o200: SKP, 0o202: HLT})
        cpu.ext.dma_req_n = 0
        for _ in range(4):
            r = cpu.step_ts()
        self.assertEqual((r.ms, r.ts), (E.FETCH, 4))
        self.assertEqual((cpu.st["MS"], cpu.st["PC"]), (E.DMA, 0o202))


class Halts(unittest.TestCase):
    def test_hlt_halts_at_fetch_tp4(self):
        cpu = machine({0o200: HLT})
        records = run(cpu)
        self.assertEqual(len(records), 4)
        self.assertEqual((cpu.st["RUN"], cpu.st["MS"], cpu.st["PC"], cpu.st["HLT_REQ"]),
                         (0, E.FETCH, 0o201, 0))

    def test_hlt_then_continue(self):
        cpu = machine({0o200: HLT, 0o201: CLA_IAC, 0o202: HLT})
        run(cpu)
        self.assertEqual(cpu.st["PC"], 0o201)
        cpu.press("CONTINUE")
        records = run(cpu)
        self.assertEqual(states(records), ["FETCH", "FETCH"])     # CLA IAC, then HLT
        self.assertEqual((cpu.st["AC"], cpu.st["PC"], cpu.st["RUN"]), (0o0001, 0o203, 0))

    def test_hlt_with_single_step(self):
        # Single Step halts after the FETCH, which is also the instruction's completion, so the
        # HLT request is consumed there and CONTINUE runs the next instruction normally.
        cpu = machine({0o200: HLT, 0o201: CLA_IAC, 0o202: HLT})
        cpu.panel.single_step = True
        records = run(cpu)
        self.assertEqual(len(records), 4)
        self.assertEqual((cpu.st["RUN"], cpu.st["PC"], cpu.st["HLT_REQ"]), (0, 0o201, 0))
        cpu.press("CONTINUE")
        run(cpu)
        self.assertEqual((cpu.st["AC"], cpu.st["PC"], cpu.st["HLT_REQ"]), (0o0001, 0o202, 0))

    def test_hlt_with_single_instruction(self):
        cpu = machine({0o200: HLT, 0o201: CLA_IAC, 0o202: HLT})
        cpu.panel.single_instruction = True
        records = run(cpu)
        self.assertEqual(len(records), 4)
        self.assertEqual((cpu.st["RUN"], cpu.st["PC"], cpu.st["HLT_REQ"]), (0, 0o201, 0))
        cpu.press("CONTINUE")
        run(cpu)
        self.assertEqual((cpu.st["AC"], cpu.st["PC"], cpu.st["HLT_REQ"]), (0o0001, 0o202, 0))

    def test_skip_then_halt(self):
        cpu = machine({0o200: SNA_HLT})
        cpu.st["AC"] = 0o0007
        run(cpu)
        self.assertEqual((cpu.st["PC"], cpu.st["RUN"]), (0o202, 0))


if __name__ == "__main__":
    unittest.main()
