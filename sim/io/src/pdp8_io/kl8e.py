"""KL8E-compatible console controller at the timing-state level.

Source: docs/07-io/10-controllers/01-kl8e-uart.md (KL8E): device addresses 03 (keyboard) and 04
(teleprinter); each IOT's request and commit points are those of KL8E §11-§24.

Output completion is outside the controller contract (KL8E §17.4). This model completes an
accepted character after `output_delay` instruction boundaries, counted by `at_boundary()`, which
the simulator calls after the TP4 of each EXECUTE or INTERRUPT major state. Counting boundaries
rather than time lets the instruction-level reference model complete it at the same instruction.

Keyboard input arrives through `type_character()`.
"""

from __future__ import annotations

from .bus import BusView, Response

KEYBOARD, TELEPRINTER = 0o03, 0o04


class KL8E:
    def __init__(self, output_delay: int = 3):
        self.output_delay = output_delay
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
        self._transfer = None             # "read" or "write" accepted for the TS after TP2/TP3
        self._asserted = Response()

    def state(self) -> dict:
        return {k: getattr(self, k) for k in ("keyboard_buffer", "keyboard_flag", "transmit_buffer",
                                              "teleprinter_flag", "interrupt_enable", "output_countdown",
                                              "output_delay")}

    def interrupt_request(self) -> bool:
        """KL8E §7: INTERRUPT_ENABLE AND (KEYBOARD_FLAG OR TELEPRINTER_FLAG)."""
        return bool(self.interrupt_enable and (self.keyboard_flag or self.teleprinter_flag))

    def type_character(self, char: int):
        """A character arrives (synchronized; KL8E §25). Ignored while the previous one is pending."""
        if not self.keyboard_flag:
            self.keyboard_buffer = char & 0o377
            self.keyboard_flag = 1

    def at_boundary(self):
        if self.output_countdown is not None:
            self.output_countdown -= 1
            if self.output_countdown <= 0:
                self.output_countdown = None
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
                elif op in (4, 6):                               # KRS, KRB
                    if op == 6 and ts == 2:
                        r.io_clear_ac_req = 1
                    if ts == 3:
                        r.io_read_req = 1
                elif op == 5 and ts == 3:                        # KIE
                    r.io_write_req = 1
            else:
                if op == 1 and ts == 4:                          # TSF
                    r.io_skip_req = self.teleprinter_flag
                elif op == 5 and ts == 4:                        # TSK
                    r.io_skip_req = int(bool(self.keyboard_flag or self.teleprinter_flag))
                elif op in (4, 6) and ts == 3 and self.output_countdown is None:   # TPC, TLS
                    r.io_write_req = 1
            if ts == 4 and self._transfer == "read":
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
        if tp == 3:
            self._transfer = ("read" if asserted.io_read_req else "write" if asserted.io_write_req else None)
        if device == KEYBOARD:
            if op in (0, 2) and tp == 2:                         # KCF, KCC
                self.keyboard_flag = 0
            elif op == 5 and tp == 4 and self._transfer == "write":   # KIE
                self.interrupt_enable = db_write & 1
            elif op == 6 and tp == 4 and self._transfer == "read":    # KRB
                self.keyboard_flag = 0
        else:
            if op == 0 and tp == 2:                              # TFL
                self.teleprinter_flag = 1
            elif op == 2 and tp == 3:                            # TCF
                self.teleprinter_flag = 0
            elif op in (4, 6) and tp == 4 and self._transfer == "write":   # TPC, TLS
                self.transmit_buffer = db_write & 0o377
                self.output_countdown = self.output_delay
                if op == 6:
                    self.teleprinter_flag = 0
        if tp == 4:
            self._transfer = None
