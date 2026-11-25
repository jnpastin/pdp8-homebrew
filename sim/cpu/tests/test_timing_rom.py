"""The timing ROM image (Timing Terminology §3.5) as the simulator reads it.

- docs/09-timing/01-terminology.md §3.5: address and data layout
- docs/09-timing/02-timing-architecture.md §5.1: the TS lengths, which design.py's MODE_0 table
  also records; the image and the table must agree
"""

import unittest

import _paths  # noqa: F401
from pdp8_cpu import design as DS
from pdp8_cpu import images as I
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory


class TimingRomTests(unittest.TestCase):
    def setUp(self):
        self.design = DS.select("v2")
        if not self.design.timing_image.exists():
            self.skipTest("no timing ROM image: run tools/rom-generation/pipeline")

    def test_image_matches_the_documented_mode_0_table(self):
        self.assertEqual(I.timing_rom_ts_ns(self.design.timing_image), DS.MODE_0)

    def test_mode_1_is_uniform_slow(self):
        table = I.timing_rom_ts_ns(self.design.timing_image, mode=1)
        self.assertEqual(set(table.values()), {DS.SLOW})

    def test_the_cpu_uses_the_image(self):
        store = ControlStore.load(design=self.design)
        self.assertEqual(store.ts_ns, DS.MODE_0)
        cpu = Cpu(store, Memory())
        self.assertEqual(cpu.ts_ns, DS.MODE_0)


if __name__ == "__main__":
    unittest.main()
