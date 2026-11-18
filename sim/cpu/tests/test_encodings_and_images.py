import copy
import unittest

import _paths  # noqa: F401
from pdp8_cpu import address as A
from pdp8_cpu import encodings as E
from pdp8_cpu.errors import ImageError
from pdp8_cpu.images import DEFAULT_SCHEMA, ControlStore

_STORE = None


def store():
    global _STORE
    if _STORE is None:
        _STORE = ControlStore.load()
    return _STORE


class EncodingTests(unittest.TestCase):
    def test_encodings_match_schema(self):
        self.assertEqual(E.check_against_schema(DEFAULT_SCHEMA), [])

    def test_reserved_detection(self):
        self.assertTrue(E.DATAPATH_FIELDS["AC_SRC"].is_reserved(7))
        self.assertFalse(E.DATAPATH_FIELDS["AC_SRC"].is_reserved(6))
        self.assertTrue(E.DATAPATH_FIELDS["ALU_OP"].is_reserved(0o13))
        self.assertTrue(E.DATAPATH_FIELDS["IOT_TRANSFER_VAL"].is_reserved(3))
        self.assertTrue(E.SEQUENCER_FIELDS["MS_NEXT"].is_reserved(5))


class ImageTests(unittest.TestCase):
    def test_layout_covers_every_datapath_field_once(self):
        names = [n for slot in store().datapath_layout for n in slot.fields]
        self.assertEqual(sorted(names), sorted(E.DATAPATH_FIELDS))

    def test_packing_that_disagrees_with_docs_is_rejected(self):
        s = store()
        packing = copy.deepcopy(s.packing)
        packing["non_execute_overlay_group"] = 0
        with self.assertRaises(ImageError):
            ControlStore(s.mapping, s.datapath, s.sequencer, packing)
        packing = copy.deepcopy(s.packing)
        packing["mapping_rom"]["fields"]["IR_SEQ"] = [6, 1]
        with self.assertRaises(ImageError):
            ControlStore(s.mapping, s.datapath, s.sequencer, packing)

    def test_fetch_ts1_word(self):
        # Fetch & Defer §3.1: PC_TO_MA; II_CLEAR only when CIFP = 0.
        s = store()
        cifp_bit = next(b for b, sig, _ in s.overlay_groups[1] if sig == "CIFP")
        for cifp in (0, 1):
            ovl = [0] * 5
            ovl[cifp_bit] = cifp
            addr, undef = A.datapath_address(E.FETCH, A.ts_code(1), 0, ovl)
            self.assertEqual(undef, [])
            f = s.decode_datapath(addr)
            self.assertEqual((f["MA_LOAD"], f["MA_SRC"]), (1, 0))
            self.assertEqual(f["II_LOAD"], 1 - cifp)
            if not cifp:
                self.assertEqual(f["II_VAL"], 0)


if __name__ == "__main__":
    unittest.main()
