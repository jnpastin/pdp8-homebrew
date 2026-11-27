import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_memory import Memory


class MemoryTests(unittest.TestCase):
    def test_starts_undefined(self):
        self.assertIsNone(Memory().read(7, 0o7777))

    def test_write_changes_one_word_and_counts(self):
        m = Memory()
        m.write(3, 0o0100, 0o17777)          # masked to 12 bits
        self.assertEqual(m.read(3, 0o0100), 0o7777)
        self.assertIsNone(m.read(3, 0o0101))
        self.assertIsNone(m.read(2, 0o0100))
        self.assertEqual(m.write_count, 1)

    def test_range(self):
        with self.assertRaises(ValueError):
            Memory().read(8, 0)
        with self.assertRaises(ValueError):
            Memory().write(0, 0o10000, 0)


if __name__ == "__main__":
    unittest.main()
