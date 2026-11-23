"""KL8E-compatible console controller at the timing-state level.

Source: docs/07-io/10-controllers/01-kl8e-uart.md (KL8E): device addresses 03 (keyboard) and 04
(teleprinter); each IOT's request and commit points are those of KL8E §11-§24.

Output completion is outside the controller contract (KL8E §17.4). Without a baud rate, this model
completes an accepted character after `output_delay` instruction boundaries. With `baud`, it
models the Teletype line in simulated time (`now_ns`, from the major-state clock): a character
starts when the line is free, its flag sets `flag_bits` bit times after the start, and the line
stays busy for the whole frame (11 bits at 110 baud, 10 above). The default of 9.25 bit times lies
in the window MAINDEC-8E-D2AB accepts for a PDP-8/E KL8-E (no earlier than 9, no later than 9.55
bit times after TLS), and back-to-back characters complete one frame apart, as D2AB expects.

`at_boundary(now_ns)` is called after the TP4 of each EXECUTE or INTERRUPT major state, so the
instruction-level reference model completes a character at the same instruction.

Keyboard input arrives through `type_character()`.
"""

from __future__ import annotations

from .bus import BusView, Response

KEYBOARD, TELEPRINTER = 0o03, 0o04

def frame_bits(baud):
    """Bits per Teletype character: 11 at 110 baud (two stop bits), 10 above."""
    return 11 if baud <= 110 else 10


class KL8E:
    def __init__(self, output_delay: int = 3, baud: int | None = None, flag_bits: float = 9.25):
        self.output_delay = output_delay
        self.baud = baud
        self.flag_bits = flag_bits
        self.line_free_at = 0             # simulated time the line finishes the last frame
        self.printed: list[int] = []
        self.initialize()

    # -- state ---------------------------------------------------------------------------------

    def initialize(self):
        """KL8E §8: registers 000, flags clear, shared interrupt enable set, operations cancelled."""
        self.keyboard_buffer = 0
        self.keyboard_flag = 0
        self.transmit_buffer = 0
        self.teleprinter_flag = 0
        self.interrupt_enable = 1
        self.output_countdown = None      # boundaries until the accepted character completes
                                          # (0 while pending, with a baud rate)
        self.output_due = None            # with a baud rate: the time its flag sets
        self._transfer = None             # "read" or "write" accepted for the TS after TP2/TP3
        self._asserted = Response()

    def state(self) -> dict:
        return {k: getattr(self, k) for k in ("keyboard_buffer", "keyboard_flag", "transmit_buffer",
                                              "teleprinter_flag", "interrupt_enable", "output_countdown",
                                              "output_delay", "baud", "flag_bits", "output_due",
                                              "line_free_at")}

    def interrupt_request(self) -> bool:
        """KL8E §7: INTERRUPT_ENABLE AND (KEYBOARD_FLAG OR TELEPRINTER_FLAG)."""
        return bool(self.interrupt_enable and (self.keyboard_flag or self.teleprinter_flag))

    def type_character(self, char: int):
        """A character arrives (synchronized; KL8E §25). Ignored while the previous one is pending."""
        if not self.keyboard_flag:
            self.keyboard_buffer = char & 0o377
            self.keyboard_flag = 1

    def at_boundary(self, now_ns: int = 0):
        if self.output_countdown is None:
            return
        if self.baud is None:
            self.output_countdown -= 1
            done = self.output_countdown <= 0
        else:
            if self.output_due is None:              # accepted at this boundary: start when free
                start = max(now_ns, self.line_free_at)
                bit = 1_000_000_000 / self.baud
                self.output_due = start + round(self.flag_bits * bit)
                self.line_free_at = start + round(frame_bits(self.baud) * bit)
            done = now_ns >= self.output_due
        if done:
            self.output_countdown = self.output_due = None
            self.teleprinter_flag = 1
            self.printed.append(self.transmit_buffer)

    # -- interface -------------------------------------------------------------------------------

    def _selected(self, bus: BusView):
        if bus.console or not bus.iot_active or bus.ioa not in (KEYBOARD, TELEPRINTER):
            return None
        return bus.ioa, bus.iop

    def present(self, bus: BusView) -> Response:
        """The response inputs for this TS, from registered state."""
        r = Response(int_req=self.interrupt_request())
        sel = self._selected(bus)
        if sel is not None:
            device, op = sel
            ts = bus.ts
            if device == KEYBOARD:
                if op == 1 and ts == 4:                          # KSF
                    r.io_skip_req = self.keyboard_flag
                elif op == 2 and ts == 2:                        # KCC
                    r.io_clear_ac_req = 1
                elif op == 4 and ts == 3:                        # KRS: read in TS4
                    r.io_read_req = 1
                elif op == 6 and ts == 2:                        # KRB: clear at TP2, read in TS3 (C10)
                    r.io_clear_ac_req = 1
                    r.io_read_req = 1
                elif op == 5 and ts == 2:                        # KIE: write in TS3 (C10)
                    r.io_write_req = 1
            else:
                if op == 1 and ts == 4:                          # TSF
                    r.io_skip_req = self.teleprinter_flag
                elif op == 5 and ts == 4:                        # TSK (§23): the interrupt condition
                    r.io_skip_req = int(self.interrupt_request())
                elif self.output_countdown is None and ((op == 4 and ts == 3) or (op == 6 and ts == 2)):
                    r.io_write_req = 1                           # TPC: write in TS4; TLS: in TS3 (C10)
            if self._transfer == ("read", ts):
                r.db = self.keyboard_buffer
        self._asserted = r
        return r

    def commit(self, bus: BusView, tp, db_write, initialize: bool):
        """Commit at TP1-TP4 (`tp` = 1..4) or the console TP (`tp` = "C")."""
        if initialize:                                           # KL8E §8: overrides everything else
            self.initialize()
            return
        sel = self._selected(bus)
        if sel is None:
            self._transfer = None
            return
        device, op = sel
        asserted = self._asserted
        done = self._transfer[0] if self._transfer is not None and self._transfer[1] == tp else None
        if device == KEYBOARD:
            if op in (0, 2) and tp == 2:                         # KCF, KCC
                self.keyboard_flag = 0
            elif op == 5 and done == "write":                    # KIE, at TP3
                self.interrupt_enable = db_write & 1
            elif op == 6 and done == "read":                     # KRB, at TP3
                self.keyboard_flag = 0
        else:
            if op == 0 and tp == 2:                              # TFL
                self.teleprinter_flag = 1
            elif op == 2 and tp == 3:                            # TCF
                self.teleprinter_flag = 0
            elif op in (4, 6) and done == "write":               # TPC at TP4, TLS at TP3
                self.transmit_buffer = db_write & 0o377
                self.output_countdown = self.output_delay if self.baud is None else 0
                if op == 6:
                    self.teleprinter_flag = 0
        # A request accepted at TP2 or TP3 transfers in the following TS (MST §5.2).
        if tp in (2, 3) and (asserted.io_read_req or asserted.io_write_req):
            self._transfer = ("read" if asserted.io_read_req else "write", tp + 1)
        elif done is not None or tp == 4:
            self._transfer = None
