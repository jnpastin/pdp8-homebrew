"""KL8E-compatible console controller, at the instruction level, for the reference model.

Source: docs/07-io/10-controllers/01-kl8e-uart.md (KL8E) §5-§26. Each IOT's effects are applied
in two parts, following the commit points the contract gives: effects at TP2 or TP3 are visible
to the interrupt-recognition decision at that instruction's completion; effects at TP4 (only TPC's
character) are not, and are returned as a `late` action. KIE, TLS, and KRB commit at TP3 (review C10).

Output completion follows the same rule as the timing-state model (sim/io): an accepted character
completes after `output_delay` instruction boundaries or, with a baud rate, at the simulated time
its flag is due (the reference model keeps the same major-state clock).
"""

from __future__ import annotations

KEYBOARD, TELEPRINTER = 0o03, 0o04

def frame_bits(baud):
    """Bits per Teletype character: 11 at 110 baud (two stop bits), 10 above."""
    return 11 if baud <= 110 else 10


class KL8E:
    def __init__(self, output_delay: int = 3, baud: int | None = None, flag_bits: float = 9.25):
        self.output_delay = output_delay
        self.baud = baud
        self.flag_bits = flag_bits
        self.line_free_at = 0
        self.printed: list[int] = []
        self.initialize()

    @classmethod
    def from_state(cls, state: dict) -> KL8E:
        device = cls(state["output_delay"])
        for key, value in state.items():
            setattr(device, key, value)
        return device

    def initialize(self):
        """KL8E §8."""
        self.keyboard_buffer = 0
        self.keyboard_flag = 0
        self.transmit_buffer = 0
        self.teleprinter_flag = 0
        self.interrupt_enable = 1
        self.output_countdown = None
        self.output_due = None

    def interrupt_request(self) -> bool:
        return bool(self.interrupt_enable and (self.keyboard_flag or self.teleprinter_flag))

    def at_boundary(self, now_ns: int = 0):
        if self.output_countdown is None:
            return
        if self.baud is None:
            self.output_countdown -= 1
            done = self.output_countdown <= 0
        else:
            if self.output_due is None:
                start = max(now_ns, self.line_free_at)
                bit = 1_000_000_000 / self.baud
                self.output_due = start + round(self.flag_bits * bit)
                self.line_free_at = start + round(frame_bits(self.baud) * bit)
            done = now_ns >= self.output_due
        if done:
            self.output_countdown = self.output_due = None
            self.teleprinter_flag = 1
            self.printed.append(self.transmit_buffer)

    def selects(self, device: int) -> bool:
        return device in (KEYBOARD, TELEPRINTER)

    def iot(self, ref, device: int, op: int):
        """Execute an IOT addressed to this controller. Returns (skip, late)."""
        skip, late = False, None
        if device == KEYBOARD:
            if op == 0:                                    # KCF
                self.keyboard_flag = 0
            elif op == 1:                                  # KSF
                skip = bool(self.keyboard_flag)
            elif op == 2:                                  # KCC
                ref.ac = 0
                self.keyboard_flag = 0
            elif op == 4:                                  # KRS
                ref.ac |= self.keyboard_buffer
            elif op == 5:                                  # KIE: enable <- AC[0] at TP3
                self.interrupt_enable = ref.ac & 1
            elif op == 6:                                  # KRB: AC cleared, read; flag cleared at TP3
                ref.ac = self.keyboard_buffer
                self.keyboard_flag = 0
        else:
            if op == 0:                                    # TFL
                self.teleprinter_flag = 1
            elif op == 1:                                  # TSF
                skip = bool(self.teleprinter_flag)
            elif op == 2:                                  # TCF
                self.teleprinter_flag = 0
            elif op in (4, 6) and self.output_countdown is None:   # TPC, TLS (accepted only if idle)
                char = ref.ac & 0o377

                def accept(clear_flag=(op == 6)):
                    self.transmit_buffer = char
                    self.output_countdown = self.output_delay if self.baud is None else 0
                    if clear_flag:
                        self.teleprinter_flag = 0
                if op == 6:                                # TLS: at TP3
                    accept()
                else:                                      # TPC: at TP4
                    late = accept
            elif op == 5:                                  # TSK (§23): the interrupt condition
                skip = self.interrupt_request()
        return skip, late
