"""Tests for the timing ROM generator."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import generate_timing_rom as G  # noqa: E402

ROOT = Path(__file__).resolve().parents[4]

CSO = "`MS` uses five of its eight codes (`FETCH = 0`, `DEFER = 1`, `EXECUTE = 2`, `INTERRUPT = 3`, `DMA = 4`)."

ARCH = """## 5. Timing

### 5.1 Structure

| Context | Mode 0 (optimized) | Mode 1 (uniform slow) |
|---|---|---|
| FETCH; DEFER with `AUTO_INDEX_REQUIRED = 0` | **5/8/6/5 = 24 (1.20 µs)** | 6/8/7/7 = 28 (1.40 µs) |
| DEFER with `AUTO_INDEX_REQUIRED = 1`; EXECUTE; INTERRUPT; DMA | **6/8/7/7 = 28 (1.40 µs)** | 6/8/7/7 = 28 (1.40 µs) |

| Context | TSs with a two-step TP | Writer |
|---|---|---|
| DEFER with `AUTO_INDEX_REQUIRED = 1` | TS4 | auto-index write-back |
| EXECUTE, whatever the instruction | TS3, TS4 | DCA |
| INTERRUPT | TS3 | return address |
| DMA | TS2 | controller |
| Console transaction | TP_FP | DEPOSIT |

### 5.2 Function
"""


def byte(image, state_code, ts, auto_index=0, mode=0):
    return image[G.address(state_code, ts, auto_index, mode)]


class LayoutTests(unittest.TestCase):
    def test_address_and_data_layout(self):
        self.assertEqual(G.address(2, 3, 1, 1), 0b010_10_1_01)
        self.assertEqual(G.encode(7, 2), 0x0D)          # EXECUTE TS3: setup 5, two-step TP
        self.assertEqual(G.encode(8, 1), 0x07)
        self.assertEqual(G.decode(0x0D), (7, 2))


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.image, self.entries, self.diagnostics = G.build(ARCH, CSO)

    def test_no_diagnostics(self):
        self.assertEqual(self.diagnostics, [])

    def test_documented_entries(self):
        execute = [byte(self.image, 2, ts) for ts in (1, 2, 3, 4)]
        self.assertEqual(execute, [0x05, 0x07, 0x0D, 0x0D])
        self.assertEqual([byte(self.image, 0, ts) for ts in (1, 2, 3, 4)], [0x04, 0x07, 0x05, 0x04])
        self.assertEqual([byte(self.image, 4, ts) for ts in (1, 2, 3, 4)], [0x05, 0x0E, 0x06, 0x06])

    def test_auto_index_changes_only_defer(self):
        self.assertEqual([byte(self.image, 1, ts, 1) for ts in (1, 2, 3, 4)], [0x05, 0x07, 0x06, 0x0D])
        self.assertEqual([byte(self.image, 1, ts, 0) for ts in (1, 2, 3, 4)], [0x04, 0x07, 0x05, 0x04])
        for code in (0, 2, 3, 4):
            for ts in (1, 2, 3, 4):
                self.assertEqual(byte(self.image, code, ts, 0), byte(self.image, code, ts, 1))

    def test_reserved_modes_repeat_mode_1(self):
        for code in range(5):
            for ts in (1, 2, 3, 4):
                for mode in (2, 3):
                    self.assertEqual(byte(self.image, code, ts, 0, mode), byte(self.image, code, ts, 0, 1))

    def test_unused_major_states_are_slow_with_one_step_tps(self):
        for code in (5, 6, 7):
            for mode in range(4):
                self.assertEqual([byte(self.image, code, ts, 0, mode) for ts in (1, 2, 3, 4)],
                                 [0x05, 0x07, 0x06, 0x06])

    def test_upper_address_bits_are_zero(self):
        self.assertTrue(all(v == 0 for v in self.image[256:]))


class DiagnosticTests(unittest.TestCase):
    def codes(self, arch, cso=CSO):
        return [d.code for d in G.build(arch, cso)[2]]

    def test_stated_total_must_match(self):
        self.assertIn("TOTAL_MISMATCH", self.codes(ARCH.replace("5/8/6/5 = 24", "5/8/6/5 = 25")))

    def test_unknown_context(self):
        self.assertIn("UNKNOWN_CONTEXT", self.codes(ARCH.replace("; DMA |", "; DMB |")))

    def test_missing_major_state(self):
        codes = self.codes(ARCH.replace("; DMA |", " |").replace("| DMA | TS2 | controller |\n", ""))
        self.assertIn("MISSING_LENGTHS", codes)

    def test_missing_section(self):
        self.assertEqual(self.codes("## Nothing\n"), ["MISSING_SECTION"])

    def test_missing_ms_code(self):
        self.assertIn("MISSING_MS_CODE", self.codes(ARCH, CSO.replace("`DMA = 4`", "")))


class RepositoryTests(unittest.TestCase):
    def test_documentation_builds_the_image(self):
        arch = (ROOT / G.TIMING_ARCHITECTURE).read_text(encoding="utf-8")
        cso = (ROOT / G.CONTROL_STORE_ORGANIZATION).read_text(encoding="utf-8")
        image, _, diagnostics = G.build(arch, cso)
        self.assertEqual(diagnostics, [])
        # Timing Architecture §5.1: an ISZ + JMP loop, 2 FETCH + 1 EXECUTE, is 76 TSTEPs in mode 0.
        total = lambda code: sum(G.decode(byte(image, code, ts))[0] for ts in (1, 2, 3, 4))
        self.assertEqual(2 * total(0) + total(2), 76)


if __name__ == "__main__":
    unittest.main()
