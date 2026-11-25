"""The KL8E controller model on its own, driven at the external-IOT interface with no CPU.

Each test checks a rule of docs/07-io/10-controllers/01-kl8e-uart.md (KL8E §n). The CPU side is
played by `iot()`: for TS1-TS4 it presents the bus, collects the controller's response, and
commits the TP. A read or write accepted at TP2 or TP3 transfers in the following TS (MST §5.2),
and for a write the harness drives AC on DB in that TS, as CPU control does.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_io.bus import BusView
from pdp8_io.kl8e import KEYBOARD, KL8E, TELEPRINTER


class Iot:
    """The controller's responses over one IOT."""

    def __init__(self, responses):
        self.responses = responses

    clear_ac = property(lambda self: self.responses[1].io_clear_ac_req)     # TS2
    read = property(lambda self: int(any(r.io_read_req for r in self.responses[1:3])))    # TS2 or TS3
    write = property(lambda self: int(any(r.io_write_req for r in self.responses[1:3])))  # TS2 or TS3
    skip = property(lambda self: self.responses[3].io_skip_req)             # TS4
    db = property(lambda self: next((r.db for r in self.responses if r.db is not None), None))

    def silent(self):
        return all((r.io_read_req, r.io_write_req, r.io_skip_req, r.io_clear_ac_req, r.db)
                   == (0, 0, 0, 0, None) for r in self.responses)


def iot(kl, device, op, ac=0, iot_active=1, console=False, arrive=None, initialize_at=None):
    """`arrive`: (TP, character), a keyboard character that arrives at that TP.
    `initialize_at`: a TP at which /INITIALIZE is asserted."""
    responses, write_ts = [], None
    for ts in (1, 2, 3, 4):
        bus = BusView(iot_active, device, op, ts, console)
        r = kl.present(bus)
        responses.append(r)
        if arrive is not None and arrive[0] == ts:
            kl.arrive_at_next_tp(arrive[1])
        kl.commit(bus, ts, ac if ts == write_ts else None, ts == initialize_at)
        if ts in (2, 3) and r.io_write_req:
            write_ts = ts + 1
    return Iot(responses)


def boundaries(kl, n):
    for _ in range(n):
        kl.at_boundary()


class Initialization(unittest.TestCase):
    def test_initialized_state(self):
        # §8: registers 000, both flags clear, shared interrupt enable set, no contribution.
        kl = KL8E()
        self.assertEqual((kl.keyboard_buffer, kl.keyboard_flag, kl.transmit_buffer, kl.teleprinter_flag,
                          kl.interrupt_enable), (0, 0, 0, 0, 1))
        self.assertFalse(kl.interrupt_request())

    def test_initialize_cancels_output_and_overrides_the_iot(self):
        # §8: /INITIALIZE cancels an operation not yet complete; no other action commits at that TP.
        kl = KL8E()
        iot(kl, TELEPRINTER, 6, ac=0o101)                        # TLS: output pending
        kl.type_character(0o301)
        bus = BusView(1, TELEPRINTER, 0, 2)                      # a TFL, whose TP2 would set the flag
        kl.present(bus)
        kl.commit(bus, 2, None, True)
        boundaries(kl, 10)
        self.assertEqual((kl.keyboard_flag, kl.teleprinter_flag, kl.printed), (0, 0, []))
        self.assertEqual(kl.interrupt_enable, 1)


class Keyboard(unittest.TestCase):
    def setUp(self):
        self.kl = KL8E()
        self.kl.type_character(0o301)

    def test_ksf_skips_only_on_the_flag(self):
        # §12: IO_SKIP_REQ during TS4 when the keyboard flag is set; no state change.
        self.assertEqual(iot(self.kl, KEYBOARD, 1).skip, 1)
        self.assertEqual(self.kl.keyboard_flag, 1)
        self.assertEqual(iot(KL8E(), KEYBOARD, 1).skip, 0)

    def test_kcf_clears_the_flag_only(self):
        # §11: flag cleared at TP2; no AC clear, no transfer.
        r = iot(self.kl, KEYBOARD, 0)
        self.assertEqual((r.clear_ac, r.read, r.db, self.kl.keyboard_flag), (0, 0, None, 0))

    def test_kcc_clears_ac_and_the_flag(self):
        # §13: IO_CLEAR_AC_REQ during TS2; flag cleared at TP2; the receive register is not read.
        r = iot(self.kl, KEYBOARD, 2)
        self.assertEqual((r.clear_ac, r.read, r.db, self.kl.keyboard_flag), (1, 0, None, 0))

    def test_krs_reads_without_clearing(self):
        # §14 and §9.2: read request in TS3, the character on DB in TS4; KRS does not clear the flag.
        r = iot(self.kl, KEYBOARD, 4)
        self.assertEqual((r.clear_ac, r.read, r.db, self.kl.keyboard_flag), (0, 1, 0o301, 1))

    def test_krb_clears_ac_reads_and_consumes(self):
        # §16 (review C10): AC cleared at TP2, read in TS3, character consumed (flag cleared) at TP3.
        r = iot(self.kl, KEYBOARD, 6)
        self.assertEqual((r.clear_ac, r.read, r.db, self.kl.keyboard_flag), (1, 1, 0o301, 0))

    def test_pending_character_is_not_replaced(self):
        # §9.3: the visible character is not replaced while the keyboard flag is set.
        self.kl.type_character(0o302)
        self.assertEqual(iot(self.kl, KEYBOARD, 6).db, 0o301)
        self.kl.type_character(0o302)
        self.assertEqual(iot(self.kl, KEYBOARD, 6).db, 0o302)


class EventAndClearAtOneTp(unittest.TestCase):
    """§9.2 and Controller Contract §5.1: FLAG_next = EVENT OR (FLAG AND NOT CLEAR)."""

    def test_arrival_without_an_iot_is_visible_after_its_tp(self):
        kl = KL8E()
        kl.arrive_at_next_tp(0o301)
        self.assertEqual(kl.keyboard_flag, 0)                    # not visible before the TP
        iot(kl, 0o10, 0)                                         # some other device's IOT
        self.assertEqual((kl.keyboard_flag, kl.keyboard_buffer), (1, 0o301))

    def test_kcf_and_kcc_at_the_arrival_tp_leave_the_flag_set(self):
        for op in (0, 2):                                        # KCF, KCC: clear at TP2
            with self.subTest(op=op):
                kl = KL8E()
                r = iot(kl, KEYBOARD, op, arrive=(2, 0o301))
                self.assertEqual((kl.keyboard_flag, kl.keyboard_buffer), (1, 0o301))
                self.assertTrue(kl.interrupt_request())
                self.assertEqual(r.db, None)

    def test_kcf_after_the_arrival_tp_clears_it(self):
        kl = KL8E()
        iot(kl, KEYBOARD, 0, arrive=(1, 0o301))                  # visible at TP1, cleared at TP2
        self.assertEqual(kl.keyboard_flag, 0)

    def test_arrival_while_the_flag_is_set_is_rejected(self):
        # §9.3: KRB consumes 301 at TP3; 302, arriving at that TP, met a set flag.
        kl = KL8E()
        kl.type_character(0o301)
        r = iot(kl, KEYBOARD, 6, arrive=(3, 0o302))
        self.assertEqual((r.db, kl.keyboard_flag, kl.keyboard_buffer), (0o301, 0, 0o301))

    def test_initialize_at_the_arrival_tp_cancels_it(self):
        # Controller Contract §5.1: /INITIALIZE wins over the event (§8).
        kl = KL8E()
        iot(kl, KEYBOARD, 0, arrive=(4, 0o301), initialize_at=4)
        self.assertEqual((kl.keyboard_flag, kl.keyboard_buffer), (0, 0))


class Teleprinter(unittest.TestCase):
    def setUp(self):
        self.kl = KL8E()

    def test_tfl_tsf_tcf(self):
        # §19 sets the flag at TP2, §20 skips on it in TS4, §21 clears it at TP3.
        self.assertEqual(iot(self.kl, TELEPRINTER, 1).skip, 0)
        iot(self.kl, TELEPRINTER, 0)
        self.assertEqual(iot(self.kl, TELEPRINTER, 1).skip, 1)
        iot(self.kl, TELEPRINTER, 2)
        self.assertEqual((self.kl.teleprinter_flag, iot(self.kl, TELEPRINTER, 1).skip), (0, 0))

    def test_tsk_skips_on_the_interrupt_condition(self):
        # §23: skip when the interrupt enable is set and either flag is set; no state change.
        self.assertEqual(iot(self.kl, TELEPRINTER, 5).skip, 0)
        self.kl.type_character(0o301)
        self.assertEqual(iot(self.kl, TELEPRINTER, 5).skip, 1)
        iot(self.kl, KEYBOARD, 0)
        iot(self.kl, TELEPRINTER, 0)
        self.assertEqual(iot(self.kl, TELEPRINTER, 5).skip, 1)
        self.assertEqual((self.kl.keyboard_flag, self.kl.teleprinter_flag), (0, 1))
        iot(self.kl, KEYBOARD, 5, ac=0)                            # KIE: interrupt enable clear
        self.assertEqual(iot(self.kl, TELEPRINTER, 5).skip, 0)     # a flag alone does not skip

    def test_tls_accepts_clears_the_flag_and_completes_later(self):
        # §24: write request in TS3, DB[7:0] loaded and the flag cleared at TP4. §17.4: the flag
        # sets only when output completes (here after output_delay boundaries), not on acceptance.
        iot(self.kl, TELEPRINTER, 0)                              # flag set beforehand
        r = iot(self.kl, TELEPRINTER, 6, ac=0o7301)
        self.assertEqual((r.write, self.kl.transmit_buffer, self.kl.teleprinter_flag), (1, 0o301, 0))
        boundaries(self.kl, self.kl.output_delay - 1)
        self.assertEqual((self.kl.teleprinter_flag, self.kl.printed), (0, []))
        boundaries(self.kl, 1)
        self.assertEqual((self.kl.teleprinter_flag, self.kl.printed), (1, [0o301]))

    def test_tpc_does_not_clear_the_flag(self):
        # §22: TPC accepts the character without clearing the teleprinter flag.
        iot(self.kl, TELEPRINTER, 0)
        r = iot(self.kl, TELEPRINTER, 4, ac=0o0215)
        self.assertEqual((r.write, self.kl.transmit_buffer, self.kl.teleprinter_flag), (1, 0o215, 1))
        boundaries(self.kl, self.kl.output_delay)
        self.assertEqual(self.kl.printed, [0o215])

    def test_busy_output_discards_the_new_character(self):
        # §17.3 and §24: while a character is pending, no write request, the new character is
        # discarded, the active operation is unchanged, and the flag is not cleared.
        iot(self.kl, TELEPRINTER, 6, ac=0o301)
        iot(self.kl, TELEPRINTER, 0)                              # TFL sets the flag meanwhile
        r = iot(self.kl, TELEPRINTER, 6, ac=0o302)
        self.assertEqual((r.write, self.kl.transmit_buffer, self.kl.teleprinter_flag), (0, 0o301, 1))
        boundaries(self.kl, self.kl.output_delay)
        self.assertEqual(self.kl.printed, [0o301])


class Interrupts(unittest.TestCase):
    def test_contribution_is_enable_and_either_flag(self):
        # §7 and §26: INTERRUPT_ENABLE AND (KEYBOARD_FLAG OR TELEPRINTER_FLAG), in every response.
        kl = KL8E()
        self.assertFalse(iot(kl, 0o10, 0).responses[0].int_req)
        kl.type_character(0o301)
        self.assertTrue(iot(kl, 0o10, 0).responses[0].int_req)    # reported while not selected
        iot(kl, KEYBOARD, 4)                                      # KRS alone does not remove it
        self.assertTrue(kl.interrupt_request())
        iot(kl, KEYBOARD, 0)
        iot(kl, TELEPRINTER, 0)                                   # the other flag keeps it asserted
        self.assertTrue(kl.interrupt_request())
        iot(kl, TELEPRINTER, 2)
        self.assertFalse(kl.interrupt_request())

    def test_kie_loads_ac0_only(self):
        # §15 and §7: write request in TS3; the enable loads from DB bit 0 at TP4; other bits ignored.
        kl = KL8E()
        kl.type_character(0o301)
        r = iot(kl, KEYBOARD, 5, ac=0o7776)
        self.assertEqual((r.write, kl.interrupt_enable, kl.interrupt_request()), (1, 0, False))
        iot(kl, KEYBOARD, 5, ac=0o0001)
        self.assertEqual((kl.interrupt_enable, kl.interrupt_request()), (1, True))


class Selection(unittest.TestCase):
    def loaded(self):
        kl = KL8E()
        kl.type_character(0o301)
        iot(kl, TELEPRINTER, 0)
        return kl

    def test_unsupported_operations_are_ignored(self):
        # §27: 6033, 6037, 6043, 6047 produce no response and no state change.
        for device, op in ((KEYBOARD, 3), (KEYBOARD, 7), (TELEPRINTER, 3), (TELEPRINTER, 7)):
            with self.subTest(iot=f"6{device:02o}{op}"):
                kl = self.loaded()
                before = kl.state()
                self.assertTrue(iot(kl, device, op, ac=0o7777).silent())
                self.assertEqual(kl.state(), before)

    def test_responds_only_to_its_addresses_during_an_iot(self):
        # §4: devices 03 and 04 only; nothing when IOT_ACTIVE is negated or during a console
        # transaction.
        for kwargs in ({"device": 0o05}, {"device": KEYBOARD, "iot_active": 0},
                       {"device": KEYBOARD, "console": True}):
            with self.subTest(**kwargs):
                kl = self.loaded()
                before = kl.state()
                self.assertTrue(iot(kl, op=6, **kwargs).silent())
                self.assertEqual(kl.state(), before)


if __name__ == "__main__":
    unittest.main()
