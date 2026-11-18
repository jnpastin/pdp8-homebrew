"""What a controller sees and drives at the external-IOT interface during one TS.

Sources: docs/07-io/02-external-iot-interface.md, 03-io-timing.md, 04-controller-contract.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BusView:
    """The CPU-side signals during a TS (or a console transaction, `console=True`)."""
    iot_active: int          # IOT_ACTIVE
    ioa: int | None          # IOA[5:0]
    iop: int | None          # IOP[2:0]
    ts: int                  # current TS (1-4); 1 during a console transaction
    console: bool = False


@dataclass
class Response:
    """A controller's response inputs for the TS (levels as asserted: 1 = asserted)."""
    io_read_req: int = 0
    io_write_req: int = 0
    io_skip_req: int = 0
    io_clear_ac_req: int = 0
    db: int | None = None     # the value the controller drives on DB, if any
    int_req: bool = False     # the controller's interrupt contribution
