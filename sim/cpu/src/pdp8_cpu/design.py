"""The control design the simulator runs: the single selection point (option2/plan.md, phase 2).

The branch `one-cycle-fetch` keeps the v1 and v2 control designs side by side, built so that v1
can be removed before the merge. A `Design` names everything that differs between them:

- the packed images, the packing description, and the control-word schema;
- `ts_ns`: the simulated duration of each timing state, per major state, in ns. `elapsed_ns`
  advances by the duration of each TS at its TP (docs/09-timing; option2/timing.md).
- `boundary_rule`: which major state is an instruction's last, so that its TP4 is the
  instruction boundary (`is_last_state`; option2/spec.md §6.1).
- `ir_source`: IR's wired load input, "MDB" (v2: IR loads at FETCH TP2 with MB) or "MB" (v1:
  IR <- MB at FETCH TP3). docs/01-architecture/01-registers.md, IR.
- `ea_page`: the register whose bits 11:7 give the current page in EA formation, "MA" (v2: the
  instruction's address, because PC has already advanced at FETCH TP1) or "PC" (v1).
  docs/03-microarchitecture/02-micro-operations.md, IR_ADDR_TO_EA_ADDR.

`PDP8_DESIGN` selects the design (default v1), as for the ROM-generation tools
(tools/rom-generation/common/design.py).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ENVIRONMENT_VARIABLE = "PDP8_DESIGN"
DEFAULT = "v1"  # V1-ONLY: becomes the surviving design's name at cleanup

MAJOR_STATES = ("FETCH", "DEFER", "EXECUTE", "INTERRUPT", "DMA")

# Every timing state 300 ns, 1.2 us per major state: the placeholder time base used since phase 2
# of the simulator. The per-state totals are what devices and the reference model see.
UNIFORM_1200 = {ms: (300, 300, 300, 300) for ms in MAJOR_STATES}


@dataclass(frozen=True)
class Design:
    name: str
    build: Path                       # the ROM-generation build directory for this design
    schema: Path                      # the maintained control-word schema
    ts_ns: dict = field(default_factory=lambda: dict(UNIFORM_1200))
    boundary_rule: str = "execute"    # see is_last_state
    ir_source: str = "MDB"            # IR's load input (slice A)
    ea_page: str = "MA"               # EA formation's page source (slice A)

    @property
    def image_dir(self) -> Path:
        return self.build / "control-store-packer" / "images"

    @property
    def packing(self) -> Path:
        return self.build / "control-store-packer" / "control-store-packing.json"

    def state_ns(self) -> dict:
        """The duration of each major state: the sum of its timing states."""
        return {ms: sum(t) for ms, t in self.ts_ns.items()}


_ROM_BUILD = REPO_ROOT / "build" / "simulation_outputs"

DESIGNS = {
    # V1-ONLY
    "v1": Design("v1", _ROM_BUILD / "rom-generation",
                 REPO_ROOT / "rom" / "microcode" / "v1" / "control-word-schema.json",
                 ir_source="MB", ea_page="PC"),                       # V1-ONLY
    "v2": Design("v2", _ROM_BUILD / "rom-generation-v2",
                 REPO_ROOT / "rom" / "microcode" / "v2" / "control-word-schema.json"),
}


def select(name: str | None = None) -> Design:
    """The design named, or the one `PDP8_DESIGN` selects."""
    name = name or os.environ.get(ENVIRONMENT_VARIABLE) or DEFAULT
    try:
        return DESIGNS[name]
    except KeyError:
        raise ValueError(f"{ENVIRONMENT_VARIABLE}={name!r} is not a control design "
                         f"(known: {', '.join(DESIGNS)})") from None


def is_last_state(design: Design, ms: str, ir) -> bool:
    """Whether major state `ms` (a name), running instruction `ir`, is that instruction's last,
    so that its TP4 is an instruction boundary: interrupt recognition, DMA entry and the DMA
    arbiter's re-enable, halts, and controllers' `at_boundary` (option2/spec.md §6.1).

    Rules:
    - "execute": every instruction ends in EXECUTE (v1; v2 until slice B).
    """
    if design.boundary_rule == "execute":
        return ms == "EXECUTE"
    raise ValueError(f"unknown boundary rule {design.boundary_rule!r}")


def major_states(design: Design, ir: int) -> tuple:
    """The major states instruction `ir` runs, in order, under `design`'s boundary rule: the
    instruction-level cycle count the reference model charges (option2/plan.md phase 2.6)."""
    indirect = ir >> 9 <= 0o5 and (ir >> 8) & 1        # an indirect MRI, JMP and JMS included
    if design.boundary_rule == "execute":
        return ("FETCH", "DEFER", "EXECUTE") if indirect else ("FETCH", "EXECUTE")
    raise ValueError(f"unknown boundary rule {design.boundary_rule!r}")


def ts_table_from_states(state_ns: dict) -> dict:
    """A per-TS table from per-major-state durations (each state's time charged at its TP4),
    for callers that give only a duration per major state."""
    return {ms: (0, 0, 0, ns) for ms, ns in state_ns.items()}
