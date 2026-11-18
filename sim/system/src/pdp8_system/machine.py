"""A machine: the CPU, its memory and front panel, and operator-level console helpers.

Every helper goes through the console microcode: it sets the front-panel switches and presses a
key, exactly as an operator would (docs/03-microarchitecture/09-console-execution.md).
"""

from __future__ import annotations

from pdp8_cpu import encodings
from pdp8_cpu.cpu import Cpu, TraceRecord
from pdp8_cpu.errors import ImageError, SimError
from pdp8_cpu.images import (
    DEFAULT_IMAGE_DIR,
    DEFAULT_PACKING,
    DEFAULT_SCHEMA,
    ControlStore,
)
from pdp8_memory import Memory

__all__ = ["Machine", "SimError", "TraceRecord", "load_store"]

_STORE_CACHE: dict = {}


def load_store(image_dir=DEFAULT_IMAGE_DIR, packing=DEFAULT_PACKING, schema=DEFAULT_SCHEMA) -> ControlStore:
    """Load and validate the control store once per (images, packing) pair."""
    key = (str(image_dir), str(packing))
    if key not in _STORE_CACHE:
        problems = encodings.check_against_schema(schema)
        if problems:
            raise ImageError("field encodings disagree with the control-word schema: " + "; ".join(problems))
        _STORE_CACHE[key] = ControlStore.load(image_dir, packing)
    return _STORE_CACHE[key]


class Machine:
    def __init__(self, store: ControlStore | None = None, keep_trace: bool = False):
        self.memory = Memory()
        self.trace: list[TraceRecord] = []
        self.cpu = Cpu(store or load_store(), self.memory,
                       trace=self.trace.append if keep_trace else None)
        self.cpu.power_on()

    @property
    def panel(self):
        return self.cpu.panel

    @property
    def state(self):
        return self.cpu.st

    # -- console helpers -------------------------------------------------------------------

    def load_address(self, address: int, instruction_field: int = 0, data_field: int = 0) -> bool:
        self.panel.sr, self.panel.fp_if, self.panel.fp_df = address, instruction_field, data_field
        return self.cpu.press("LOAD_ADDRESS")

    def deposit(self, value: int) -> bool:
        self.panel.sr = value
        return self.cpu.press("DEPOSIT")

    def deposit_block(self, address: int, values, instruction_field: int = 0) -> None:
        self.load_address(address, instruction_field)
        for value in values:
            self.deposit(value)

    def examine(self):
        self.cpu.press("EXAMINE")
        return self.state["MB"]

    def start(self) -> bool:
        return self.cpu.press("START")

    def cont(self) -> bool:
        return self.cpu.press("CONTINUE")

    def clear(self) -> bool:
        return self.cpu.press("CLEAR")

    # -- running ---------------------------------------------------------------------------

    def run(self, max_ts: int = 1_000_000) -> int:
        """Step until the processor halts; return the number of TS executed."""
        n = 0
        while self.cpu.running:
            if n >= max_ts:
                raise RuntimeError(f"still running after {max_ts} timing states")
            self.cpu.step_ts()
            n += 1
        return n
