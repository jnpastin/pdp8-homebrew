import random
import unittest

import _paths  # noqa: F401
import pack_control_store as P  # the packer: used only as an independent cross-check
from pdp8_cpu import address as A
from pdp8_cpu import encodings as E
from pdp8_cpu.errors import SpecViolation


class CodeTests(unittest.TestCase):
    def test_ms_eff(self):
        self.assertEqual(A.ms_eff(E.EXECUTE, 1), E.EXECUTE)
        self.assertEqual(A.ms_eff(E.EXECUTE, 0), E.HALTED)
        self.assertEqual(A.ms_eff_is_execute(E.EXECUTE), 1)
        self.assertEqual(A.ms_eff_is_execute(E.HALTED), 0)

    def test_ts_code(self):
        self.assertEqual([A.ts_code(t) for t in (1, 2, 3, 4)], [0, 1, 2, 3])
        with self.assertRaises(SpecViolation):
            A.ts_code(5)

    def test_execute_selection(self):
        mapr = (1 << 7) | (3 << 5) | 0o25
        self.assertEqual(A.execute_selection(1, mapr, 0), (0o25, 3, 1))
        self.assertEqual(A.execute_selection(0, mapr, 1), (0, 1, 1))
        with self.assertRaises(SpecViolation):
            A.execute_selection(1, None, 0)

    def test_seq_ovl(self):
        self.assertEqual(A.seq_ovl_bits(0, 6, 1, 1, 1), [0, 1, 1])        # FP_CMD = 6 while halted
        self.assertEqual(A.seq_ovl_bits(1, 0, 1, 0, 1), [1, 0, 1])        # IRV, SS, SI while running

    def test_undefined_bits_expand(self):
        addr, undef = A.datapath_address(E.FETCH, 0, 0, [0, None, 0, 0, None])
        self.assertEqual(undef, [1, 4])
        self.assertEqual(sorted(A.expand(addr, undef)), [0, 2, 16, 18])


class PackerCrossCheck(unittest.TestCase):
    """The simulator forms addresses independently; they must agree with the packer's."""

    def test_mapping_addresses(self):
        rng = random.Random(1)
        for _ in range(500):
            ir, ts = rng.randrange(4096), rng.randrange(1, 5)
            self.assertEqual(A.mapping_address(ir, ts), P.mapping_address(ir, ts))

    def test_datapath_addresses(self):
        rng = random.Random(2)
        for _ in range(500):
            mseff = rng.choice([0, 1, 2, 3, 4, 7])
            ts, variant, ovl = rng.randrange(1, 5), rng.randrange(32), rng.randrange(32)
            bits = [(ovl >> k) & 1 for k in range(5)]
            ours, undef = A.datapath_address(mseff, A.ts_code(ts), variant, bits)
            self.assertEqual(undef, [])
            self.assertEqual(ours, P.datapath_address(mseff, ts, variant, ovl))

    def test_sequencer_addresses(self):
        rng = random.Random(3)
        cmds = ["FP_START", "FP_CONTINUE", "FP_CLEAR", "FP_LOAD_ADDRESS", "FP_EXAMINE", "FP_DEPOSIT"]
        for _ in range(500):
            halted = rng.random() < 0.3
            mseff = 7 if halted else rng.choice([0, 1, 2, 3, 4])
            ts = 1 if halted else rng.randrange(1, 5)
            values = {k: str(rng.randrange(2)) for k in
                      ("HLT_REQ", "FP_STOP", "/DMA_REQ", "FP_SINGLE_INSTRUCTION", "FP_SINGLE_STEP",
                       "INTERRUPT_REQUEST_VALID")}
            cmd = rng.choice([None] + cmds) if halted else None
            for c in cmds:
                values[c] = "1" if c == cmd else "0"
            ir_seq = rng.randrange(2)
            fp_cmd = E.FP_CMD_CODES[cmd.removeprefix("FP_") if cmd else None]
            seq_ovl = A.seq_ovl_bits(0 if halted else 1, fp_cmd, int(values["FP_SINGLE_INSTRUCTION"]),
                                     int(values["FP_SINGLE_STEP"]), int(values["INTERRUPT_REQUEST_VALID"]))
            ours, _ = A.sequencer_address(mseff, A.ts_code(ts), int(values["HLT_REQ"]),
                                          int(values["FP_STOP"]), seq_ovl, int(values["/DMA_REQ"]), ir_seq)
            theirs = P.sequencer_address(mseff, ts, values, halted, str(ir_seq))
            self.assertEqual(ours, theirs, (mseff, ts, values, cmd, ir_seq))


if __name__ == "__main__":
    unittest.main()
