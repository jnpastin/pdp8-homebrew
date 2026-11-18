"""Front-panel inputs and console-command acceptance.

- Command acceptance: docs/04-control/10-control-input-definitions/04-external-inputs.md §4.1
- Console transaction: docs/09-timing/03-major-state-timing.md §8.2
- FP_CMD encoding: docs/04-control/08-control-store-organization.md §5.2

The simulator models one press as one accepted command: it is accepted only while RUN = 0 and no
transaction is in progress, latched for exactly one console transaction, and then cleared. Input
synchronization, debouncing, and re-arming are physical behavior below the TS level.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import encodings as E

COMMANDS = ("START", "CONTINUE", "CLEAR", "LOAD_ADDRESS", "EXAMINE", "DEPOSIT")


@dataclass
class FrontPanel:
    sr: int = 0            # FP_SR, switch register (12 bits)
    fp_if: int = 0         # FP_IF (3 bits)
    fp_df: int = 0         # FP_DF (3 bits)
    stop: bool = False     # FP_STOP
    single_step: bool = False
    single_instruction: bool = False
    latched: str | None = None  # the accepted console command, held for one transaction

    def fp_cmd(self) -> int:
        """CSO §5.2 priority encoder output; 0 when no command is latched."""
        return E.FP_CMD_CODES[self.latched]

    def command_asserted(self, name: str) -> int:
        """The latched accepted command as seen by control (EXT §4.1): at most one asserted."""
        return int(self.latched == name)
