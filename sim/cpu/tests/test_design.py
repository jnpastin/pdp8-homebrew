"""Control-design selection (pdp8_cpu/design.py; option2/plan.md phase 2) and the per-TS time base."""

import os
import unittest
from unittest import mock

import _paths  # noqa: F401
from pdp8_cpu import design as D
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory


class SelectionTests(unittest.TestCase):
    def test_default_is_v1(self):  # V1-ONLY
        with mock.patch.dict(os.environ, clear=True):
            self.assertEqual(D.select().name, "v1")

    def test_environment_and_name(self):
        with mock.patch.dict(os.environ, {D.ENVIRONMENT_VARIABLE: "v2"}):
            self.assertEqual(D.select().name, "v2")
            self.assertEqual(D.select("v1").name, "v1")
        with self.assertRaises(ValueError):
            D.select("v9")

    def test_designs_use_their_own_outputs(self):
        v1, v2 = D.select("v1"), D.select("v2")
        self.assertNotEqual(v1.image_dir, v2.image_dir)
        self.assertNotEqual(v1.schema, v2.schema)
        self.assertTrue(v2.image_dir.as_posix().endswith("rom-generation-v2/control-store-packer/images"))


class TimeBaseTests(unittest.TestCase):
    def test_state_duration_is_sum_of_ts(self):
        d = D.select("v1")
        for ms, ts in d.ts_ns.items():
            self.assertEqual(len(ts), 4)
            self.assertEqual(d.state_ns()[ms], sum(ts))
        self.assertEqual(d.state_ns()["FETCH"], 1200)   # the time base used since sim phase 2

    def test_elapsed_advances_per_ts_and_totals_per_state(self):
        store = ControlStore.load(design=D.select("v1"))
        table = {ms: (100, 200, 300, 600) for ms in D.MAJOR_STATES}
        cpu = Cpu(store, Memory(), ts_ns=table)
        cpu.power_on()
        self.assertEqual(cpu.timing["EXECUTE"], 1200)
        cpu.memory.write(0, 0o200, 0o7000)        # NOP
        cpu.memory.write(0, 0o201, 0o7402)        # HLT
        cpu.panel.sr = 0o200
        cpu.press("LOAD_ADDRESS")
        cpu.press("START")
        seen = []
        for _ in range(4):                        # FETCH TS1..TS4 of the NOP
            cpu.step_ts()
            seen.append(cpu.elapsed_ns)
        self.assertEqual(seen, [100, 300, 600, 1200])

    def test_per_state_timing_override_charges_at_tp4(self):
        store = ControlStore.load(design=D.select("v1"))
        cpu = Cpu(store, Memory(), timing={"FETCH": 1000})
        self.assertEqual(cpu.ts_ns["FETCH"], (0, 0, 0, 1000))
        self.assertEqual(cpu.timing["EXECUTE"], 1200)


class BoundaryRuleTests(unittest.TestCase):
    def test_execute_rule(self):
        d = D.select("v1")
        self.assertTrue(D.is_last_state(d, "EXECUTE", 0o7000))
        for ms in ("FETCH", "DEFER", "INTERRUPT", "DMA"):
            self.assertFalse(D.is_last_state(d, ms, 0o5000))

    def test_major_states_execute_rule(self):
        d = D.select("v1")
        self.assertEqual(D.major_states(d, 0o1000), ("FETCH", "EXECUTE"))           # TAD
        self.assertEqual(D.major_states(d, 0o1400), ("FETCH", "DEFER", "EXECUTE"))  # TAD I
        self.assertEqual(D.major_states(d, 0o5400), ("FETCH", "DEFER", "EXECUTE"))  # JMP I
        self.assertEqual(D.major_states(d, 0o7400), ("FETCH", "EXECUTE"))           # group 2 OPR
        self.assertEqual(D.major_states(d, 0o6400), ("FETCH", "EXECUTE"))           # IOT, bit 3 set

    def test_unknown_rule_rejected(self):
        d = D.Design("x", D.REPO_ROOT, D.REPO_ROOT, boundary_rule="nonsense")
        with self.assertRaises(ValueError):
            D.is_last_state(d, "EXECUTE", 0)
        with self.assertRaises(ValueError):
            D.major_states(d, 0)

    def test_boundary_kind(self):
        store = ControlStore.load(design=D.select("v1"))
        cpu = Cpu(store, Memory())
        cpu.power_on()
        cpu.memory.write(0, 0o200, 0o7000)        # NOP
        cpu.panel.sr = 0o200
        cpu.press("LOAD_ADDRESS")
        cpu.press("START")
        kinds = [cpu.boundary_kind(cpu.step_ts()) for _ in range(8)]
        self.assertEqual(kinds, [None] * 7 + ["instruction"])    # FETCH TS1-4, EXECUTE TS1-4


if __name__ == "__main__":
    unittest.main()
