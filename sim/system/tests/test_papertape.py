"""The BIN paper-tape loader, checked against every MAINDEC tape, its octal dump, and its listing."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system.machine import Machine, load_store
from pdp8_system.papertape import (
    TapeError,
    load_tape,
    octal_dump_bytes,
    parse_bin,
    read_tape,
)

PROGRAMS = Path(__file__).resolve().parents[2] / "test_programs"


def tapes():
    for d in sorted(p for p in PROGRAMS.iterdir() if p.is_dir()):
        yield d.name, next(d.glob("*-pb"))


class TapeFormat(unittest.TestCase):
    def test_every_tape_parses_with_a_valid_checksum(self):
        for name, path in tapes():
            with self.subTest(tape=name):
                tape = read_tape(path)
                self.assertTrue(tape.checksum_ok, f"{tape.checksum:04o} vs {tape.computed:04o}")
                self.assertGreater(len(tape.words), 0)

    def test_every_tape_matches_its_octal_dump(self):
        for name, path in tapes():
            od = path.with_name(path.name + ".od")
            with self.subTest(tape=name):
                self.assertEqual(octal_dump_bytes(od), path.read_bytes())

    def test_d0ab_decodes_as_its_listing(self):
        # MAINDEC-8E-D0AB listing page 1-68: the bell routine at 5307-5314.
        words = {a: v for f, a, v in read_tape(PROGRAMS / "maindec-8e-d0ab" / "maindec-8E-d0ab-pb").words}
        self.assertEqual([words[a] for a in range(0o5307, 0o5315)],
                         [0o1120, 0o6046, 0o6041, 0o5311, 0o6042, 0o5147])

    def test_format_rules(self):
        # leader, field 1, origin 0200, data 1234 5670, checksum, trailer; a rubout pair is skipped.
        frames = [0o200, 0o200, 0o310, 0o102, 0o000, 0o377, 0o055, 0o377, 0o012, 0o034, 0o056, 0o070]
        total = (0o102 + 0o000 + 0o012 + 0o034 + 0o056 + 0o070) & 0o7777
        frames += [(total >> 6) & 0o77, total & 0o77, 0o200]
        tape = parse_bin(bytes(frames))
        self.assertEqual(tape.words, [(1, 0o200, 0o1234), (1, 0o201, 0o5670)])
        self.assertTrue(tape.checksum_ok)

    def test_bad_checksum_is_refused(self):
        frames = bytes([0o200, 0o102, 0o000, 0o012, 0o034, 0o000, 0o001, 0o200])
        tape = parse_bin(frames)
        self.assertFalse(tape.checksum_ok)
        with self.assertRaises(TapeError):
            load_tape(Machine(load_store()), tape)


class LoadingThroughTheConsole(unittest.TestCase):
    def test_load_deposits_every_word(self):
        m = Machine(load_store())
        tape = read_tape(PROGRAMS / "maindec-8e-d0db" / "maindec-8E-d0db-pb")
        self.assertEqual(load_tape(m, tape), len(tape.words))
        for f, a, v in tape.words:
            self.assertEqual(m.memory.read(f, a), v)
        self.assertEqual(len(m.memory.write_log), len(tape.words))   # one DEPOSIT per word


if __name__ == "__main__":
    unittest.main()
