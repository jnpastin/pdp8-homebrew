"""The cross-checks of the logic realized outside the control store (ACS §3.2).

- docs/04-control/20-control-output-definitions/02-architectural-control-signals.md §3.2: /DB_READ
  and /DB_WRITE are decoded from IOT_TRANSFER (v1's control word also has fields for them,
  which must agree); /RD and the CPU's MDB drive are gated off by MS_EFF_IS_EXECUTE AND
  IR_IS_IOT.
"""

import unittest

import _paths  # noqa: F401
from pdp8_cpu import derived as D
from pdp8_cpu import encodings as E
from pdp8_cpu.errors import SpecViolation


class DbStrobeTests(unittest.TestCase):
    def test_agreeing_words_pass(self):
        D.check_db_strobes(1, 1, E.IOT_NONE)
        D.check_db_strobes(0, 1, E.IOT_READ)
        D.check_db_strobes(1, 0, E.IOT_WRITE)

    def test_undefined_transfer_is_not_judged(self):
        D.check_db_strobes(0, 0, None)

    def test_disagreeing_words_are_violations(self):
        for fields, transfer in (((0, 1), E.IOT_NONE), ((1, 1), E.IOT_READ),
                                 ((0, 1), E.IOT_WRITE), ((1, 1), E.IOT_WRITE)):
            with self.subTest(fields=fields, transfer=transfer):
                with self.assertRaises(SpecViolation):
                    D.check_db_strobes(*fields, transfer)


class IotGateTests(unittest.TestCase):
    def test_read_or_drive_in_iot_execute_is_a_violation(self):
        for rd, mdb in ((True, False), (False, True)):
            with self.subTest(rd=rd, mdb=mdb):
                with self.assertRaises(SpecViolation):
                    D.check_iot_gate(1, 1, rd, mdb)

    def test_the_gate_acts_only_in_an_iots_execute(self):
        D.check_iot_gate(0, 1, True, True)       # FETCH of an IOT: read normally
        D.check_iot_gate(1, 0, True, True)       # EXECUTE of an MRI
        D.check_iot_gate(1, 1, False, False)     # an IOT's EXECUTE with no memory operation


if __name__ == "__main__":
    unittest.main()
