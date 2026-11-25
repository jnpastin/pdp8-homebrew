"""The DMA arbiter, and a DMA bus master for tests.

Sources: docs/07-io/05-dma-interface.md (DMA), 06-dma-arbitration.md (ARB), and
docs/03-microarchitecture/10-dma-execution.md (DMX).

The arbiter is a system component outside the CPU (ARB §2). The CPU gives it the major-state
and timing context (ARB §3) and reads only the aggregate /DMA_REQ it derives (ARB §7). The
selected controller drives the memory interface while /DMA_GRANT is asserted (DMA §3); the
simulator's CPU performs that memory cycle on the controller's behalf at DMA TP2.

A DMA controller provides:

- `dma_priority`: its priority channel, 0 (highest) to 14 (ARB §6)
- `dma_request()`: its /DMA_REQ[n] line, asserted only while its next transfer is prepared (DMA §7)
- `dma_operation()`: the prepared transfer, ("read", field, address) or ("write", field, address, value)
- `dma_transferred(value)`: TP2, the word transferred (the value read, for a read)
- `dma_advance()`: TP3, the controller's address and word count update (DMA §6.4)
- `initialize()`: /INITIALIZE (ARB §13.2)
"""

from __future__ import annotations

NO_CONTROLLER = 15            # ARB §8: DMA_GRANT_ID with no controller selected


class DmaArbiter:
    """ARB §4-§13: fixed priority, non-preemptive bounded bursts, CPU fairness."""

    def __init__(self, controllers=(), burst_limits: dict | None = None, default_burst_limit: int = 4):
        self.controllers = list(controllers)
        self.burst_limits = dict(burst_limits or {})
        self.default_burst_limit = default_burst_limit
        priorities = [c.dma_priority for c in self.controllers]
        if len(set(priorities)) != len(priorities) or not all(0 <= p <= 14 for p in priorities):
            raise ValueError(f"DMA priorities must be distinct and 0-14 (ARB §6): {priorities}")
        if any(limit < 1 for limit in self.burst_limits.values()) or default_burst_limit < 1:
            raise ValueError("a burst limit of zero is invalid (ARB §11.1)")
        self.initialize()

    def initialize(self):
        """ARB §13.2: DMA_GRANT_ID = 15, burst-enabled state and burst count cleared."""
        self.grant_id = NO_CONTROLLER
        self.burst_enabled = False
        self.burst_count = 0
        self._terminating = False

    def state(self) -> dict:
        return {"grant_id": self.grant_id, "burst_enabled": self.burst_enabled,
                "burst_count": self.burst_count}

    def burst_limit(self, priority: int) -> int:
        return self.burst_limits.get(priority, self.default_burst_limit)

    def selected(self):
        return next((c for c in self.controllers if c.dma_priority == self.grant_id), None)

    # -- combinational outputs -----------------------------------------------------------------

    def dma_enable(self, in_last_state: bool, in_dma: bool, ts: int) -> bool:
        """ARB §5: 1 in a TS4 in which INSTR_END is asserted; the retained burst-enabled state in
        DMA; otherwise 0.

        `in_last_state`: the CPU is in an instruction's last major state, so that its TS4 asserts
        INSTR_END (docs/04-control/20-control-output-definitions/02-architectural-control-signals.md
        §4.10): EXECUTE, FETCH of a direct JMP or an OPR, or DEFER of a JMP I. In v1, EXECUTE only."""
        if in_last_state and ts == 4:
            return True
        if in_dma:
            return self.burst_enabled
        return False

    def aggregate_n(self, in_last_state: bool, in_dma: bool, ts: int) -> int:
        """ARB §7: /DMA_REQ = NOT (DMA_ENABLE AND any /DMA_REQ[n] asserted)."""
        requested = any(c.dma_request() for c in self.controllers)
        return 0 if self.dma_enable(in_last_state, in_dma, ts) and requested else 1

    def operation(self):
        """DMA §6.3: the transfer the selected controller presents during DMA TS2, or None."""
        c = self.selected()
        return None if c is None else c.dma_operation()

    # -- TP commits ------------------------------------------------------------------------------

    def commit(self, tp, in_last_state: bool, in_dma: bool, initialize: bool, transferred=None):
        """Commit at a main-sequence TP (`tp` = 1..4) or the console TP (`tp` = "C").

        `transferred` is the value of the word transferred at DMA TP2 (None for none)."""
        if initialize:                                   # ARB §13.2, at the TP ending /INITIALIZE
            self.initialize()
            return
        if tp == "C":                                    # ARB §13.1: console TPs change nothing
            return
        if in_dma:
            c = self.selected()
            if tp == 1 and c is None:                    # DMA §6.2: arbitrate when none selected
                requesting = sorted(x.dma_priority for x in self.controllers if x.dma_request())
                if requesting:
                    self.grant_id = requesting[0]        # ARB §9: lowest-numbered request wins
            elif tp == 1 and not c.dma_request():        # ARB §13.3: drop a held selection, no request
                self.grant_id = NO_CONTROLLER
                self.burst_count = 0
            elif tp == 3 and c is None:                  # ARB §13.3: no selection ends the burst
                self.burst_enabled = False
            elif tp == 2 and c is not None:              # DMA §6.3: exactly one word transfers
                c.dma_transferred(transferred)
            elif tp == 3 and c is not None:              # DMA §6.4, ARB §11
                still_requesting = c.dma_request()       # pre-TP3: after the TP2 transfer
                c.dma_advance()
                self.burst_count += 1
                if not still_requesting or self.burst_count >= self.burst_limit(c.dma_priority):
                    self.burst_enabled = False           # ARB §12: the burst terminates
                    self._terminating = True
            elif tp == 4 and self._terminating:          # ARB §13: release at DMA TP4
                self.grant_id = NO_CONTROLLER
                self.burst_count = 0
                self._terminating = False
        elif in_last_state and tp == 4:                  # ARB §4, §14: reenable at INSTR_END TP4
            self.burst_enabled = True


class DmaTestMaster:
    """A DMA bus master for tests, not a device model: it performs a queue of prepared single-word
    transfers, following the DMA controller contract (DMA §5-§7). It requests only while its next
    transfer is prepared, completes exactly one word per selection at TP2, advances at TP3, and
    has no IOTs or interrupt. Transfers are queued by `load()`, or at an instruction boundary by
    `schedule` ({boundary number: [operations]}), so two copies stay identical."""

    def __init__(self, dma_priority: int = 0, schedule: dict | None = None):
        self.dma_priority = dma_priority
        self.schedule = {k: list(v) for k, v in (schedule or {}).items()}
        self.queue: list = []
        self.read_values: list = []
        self.boundaries = 0
        self.done = False             # the head transfer has completed at TP2, not yet advanced

    def initialize(self):
        """ARB §13.2: the request deasserts; queued transfers are canceled."""
        self.queue = []
        self.done = False

    def state(self) -> dict:
        return {"dma_priority": self.dma_priority, "queue": list(self.queue),
                "read_values": list(self.read_values), "boundaries": self.boundaries, "done": self.done}

    def load(self, operations):
        for op in operations:
            if op[0] not in ("read", "write") or len(op) != (3 if op[0] == "read" else 4):
                raise ValueError(f"not a DMA operation: {op}")
        self.queue.extend(tuple(op) for op in operations)

    # -- the DMA controller interface ------------------------------------------------------------

    def dma_request(self) -> bool:
        """/DMA_REQ[n]: asserted while another transfer is prepared (DMA §7). After the TP2
        transfer of the last word, it deasserts before the TP3 update (ARB §11)."""
        return len(self.queue) - (1 if self.done else 0) > 0

    def dma_operation(self):
        if not self.queue or self.done:
            raise RuntimeError("selected with no prepared transfer (DMA §6.2)")
        return self.queue[0]

    def dma_transferred(self, value):
        if self.queue[0][0] == "read":
            self.read_values.append(value)
        self.done = True

    def dma_advance(self):
        if self.done:
            self.queue.pop(0)
            self.done = False

    # -- the rest of the controller interface (no IOTs, no interrupt) ---------------------------

    def present(self, bus):
        from .bus import Response
        return Response()

    def commit(self, bus, tp, db_write, initialize: bool):
        if initialize:
            self.initialize()

    def at_boundary(self, now_ns: int = 0):
        self.boundaries += 1
        self.load(self.schedule.get(self.boundaries, ()))

    def interrupt_request(self) -> bool:
        return False

    def selects(self, device: int) -> bool:
        return False
