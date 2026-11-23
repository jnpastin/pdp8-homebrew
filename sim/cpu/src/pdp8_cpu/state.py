"""CPU register state.

Registers and widths: docs/01-architecture/01-registers.md. A register holds an int, or None when
UNDEFINED. Power-on: docs/09-timing/01-terminology.md §3.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import encodings as E

REGISTER_WIDTHS = {
    # architectural
    "AC": 12, "L": 1, "MQ": 12, "PC": 12, "IF": 3, "DF": 3, "IE": 1,
    # control-visible
    "CIFP": 1, "HLT_REQ": 1, "II": 1, "IR": 12, "MS": 3, "RUN": 1, "SKIP": 1,
    # internal
    "DIF": 3, "EA_ADDR": 12, "IB": 6, "IOT_TRANSFER": 2, "MA": 12, "MAPR": 8, "MB": 12,
}


@dataclass
class CpuState:
    regs: dict = field(default_factory=lambda: {name: None for name in REGISTER_WIDTHS})
    ts: int = 1  # current timing state, 1..4

    def __getitem__(self, name):
        return self.regs[name]

    def __setitem__(self, name, value):
        if name not in REGISTER_WIDTHS:
            raise KeyError(name)
        if value is not None:
            value &= (1 << REGISTER_WIDTHS[name]) - 1
        self.regs[name] = value

    def snapshot(self) -> dict:
        return dict(self.regs, TS=self.ts)

    def power_on(self):
        """Timing Terminology §3.4, during the reset: TSEQ at TS1; RUN = 0, MS = FETCH,
        HLT_REQ = 0, IOT_TRANSFER = NONE; all else undefined. AC, L, and IE are cleared by the CLEAR
        transaction that ends the reset (Cpu.power_on)."""
        for name in REGISTER_WIDTHS:
            self.regs[name] = None
        self.ts = 1
        self["RUN"] = 0
        self["MS"] = E.FETCH
        self["HLT_REQ"] = 0
        self["IOT_TRANSFER"] = E.IOT_NONE
