"""KL8E-compatible console controller, at the instruction level, for the reference model.

Source: docs/07-io/10-controllers/01-kl8e-uart.md (KL8E) §5-§26. Each IOT's effects are applied
in two parts, following the commit points the contract gives: effects at TP2 or TP3 are visible
to the interrupt-recognition decision at that instruction's completion; effects at TP4 (KIE,
TLS, TPC, and KRB's flag clear) are not, and are returned as a `late` action.

Output completion follows the same rule as the timing-state model (sim/io): an accepted character
completes after `output_delay` instruction boundaries.
"""

from __future__ import annotations

KEYBOARD, TELEPRINTER = 0o03, 0o04


class KL8E:
    def __init__(self, output_delay: int = 3):
        self.output_delay = output_delay
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

    def interrupt_request(self) -> bool:
        return bool(self.interrupt_enable and (self.keyboard_flag or self.teleprinter_flag))

    def at_boundary(self):
        if self.output_countdown is not None:
            self.output_countdown -= 1
            if self.output_countdown <= 0:
                self.output_countdown = None
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
            elif op == 5:                                  # KIE: enable <- AC[0] at TP4
                value = ref.ac & 1
                late = lambda: setattr(self, "interrupt_enable", value)
            elif op == 6:                                  # KRB: AC cleared, read; flag cleared at TP4
                ref.ac = self.keyboard_buffer
                late = lambda: setattr(self, "keyboard_flag", 0)
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
                    self.output_countdown = self.output_delay
                    if clear_flag:
                        self.teleprinter_flag = 0
                late = accept
            elif op == 5:                                  # TSK
                skip = bool(self.keyboard_flag or self.teleprinter_flag)
        return skip, late
