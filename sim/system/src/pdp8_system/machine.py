"""A machine: the CPU, its memory and front panel, and operator-level console helpers.

Every helper goes through the console microcode: it sets the front-panel switches and presses a
key, exactly as an operator would (docs/03-microarchitecture/09-console-execution.md).
"""

from __future__ import annotations

import random

from pdp8_cpu import encodings
from pdp8_cpu.cpu import Cpu, TraceRecord
from pdp8_cpu.errors import ImageError, SimError
from pdp8_cpu.design import select as select_design
from pdp8_cpu.images import ControlStore
from pdp8_io import KL8E, DmaArbiter, DmaTestMaster
from pdp8_memory import Memory

__all__ = ["KL8E", "DmaArbiter", "DmaTestMaster", "Machine", "SimError", "TraceRecord", "load_store"]

_STORE_CACHE: dict = {}


def load_store(image_dir=None, packing=None, schema=None, design: str | None = None) -> ControlStore:
    """Load and validate a control design's store once per (images, packing) pair.

    design: "v1" or "v2" (pdp8_cpu/design.py; default: PDP8_DESIGN, else v1). The other arguments
    override that design's paths."""
    d = select_design(design)
    image_dir, packing, schema = image_dir or d.image_dir, packing or d.packing, schema or d.schema
    key = (d.name, str(image_dir), str(packing))
    if key not in _STORE_CACHE:
        problems = encodings.check_against_schema(schema)
        if problems:
            raise ImageError("field encodings disagree with the control-word schema: " + "; ".join(problems))
        _STORE_CACHE[key] = ControlStore.load(image_dir, packing, d)
    return _STORE_CACHE[key]


class Machine:
    def __init__(self, store: ControlStore | None = None, keep_trace: bool = False, devices=(), dma=None):
        """devices: I/O controllers attached to the external-IOT interface (for example KL8E()).
        dma: a DmaArbiter for DMA-capable controllers (each also listed in `devices`)."""
        self.memory = Memory()
        self.trace: list[TraceRecord] = []
        self.devices = list(devices)
        self.dma = dma
        self.cpu = Cpu(store or load_store(), self.memory,
                       trace=self.trace.append if keep_trace else None, devices=self.devices, dma=dma)
        self.cpu.power_on()

    @property
    def panel(self):
        return self.cpu.panel

    @property
    def state(self):
        return self.cpu.st

    def core_residue(self, seed: int):
        """Give every memory word an arbitrary, defined value, standing in for what core memory
        retained from earlier use. Core keeps its contents through power-on and CLEAR, so a
        program that does not clear memory sees whatever was left there (MAINDEC-8E-D0BB's
        autoindex test ANDs location 7777, which it never loads, into a zero AC, for example).
        The values come from `seed`; a program that does not depend on leftover contents gives
        the same result for every seed. Memory of a machine created without this stays
        UNDEFINED, so unit tests still catch accidental reads.

        The interrupt save field IB gets an arbitrary value too: nothing initializes it before the
        first interrupt entry (Register Model IB; on the PDP-8/E the save field is loaded only at
        interrupt entry), and GTF reports it. MAINDEC-8E-D0BB executes GTF before any interrupt and
        masks those bits off."""
        rng = random.Random(seed)
        for f in range(8):
            self.memory.preload(f, 0, [rng.randrange(4096) for _ in range(4096)])
        self.state["IB"] = rng.randrange(0o100)

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
