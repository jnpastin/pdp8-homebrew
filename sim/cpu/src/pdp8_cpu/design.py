"""The control design the simulator runs: the single selection point (option2/plan.md, phase 2).

The branch `one-cycle-fetch` keeps the v1 and v2 control designs side by side, built so that v1
can be removed before the merge. A `Design` names everything that differs between them:

- the packed images, the packing description, and the control-word schema;
- `ts_ns`: the simulated duration of each timing state, per timing context, in ns: each major
  state, and `DEFER_AUTOINDEX`, a DEFER with AUTO_INDEX_REQUIRED = 1, which the timing ROM
  gives the slow lengths (docs/09-timing/02-timing-architecture.md §5.1; 01-terminology.md
  §3.5). `elapsed_ns` advances by the duration of each TS at its TP.
- `boundary_rule`: which major state is an instruction's last, so that its TP4 is the
  instruction boundary (`is_last_state`; option2/spec.md §6.1).
- `ir_source`: IR's wired load input, "MDB" (v2: IR loads at FETCH TP2 with MB) or "MB" (v1:
  IR <- MB at FETCH TP3). docs/01-architecture/01-registers.md, IR.
- `ea_page`: the register whose bits 11:7 give the current page in EA formation, "MA" (v2: the
  instruction's address, because PC has already advanced at FETCH TP1) or "PC" (v1).
  docs/03-microarchitecture/02-micro-operations.md, IR_ADDR_TO_EA_ADDR.
- `non_execute_variant`, `sequencer_a2`: the IR decodes on the datapath slice's VARIANT and the
  sequencer slice's A2 outside EXECUTE (v2: IR_CLASS and IR_NO_EXECUTE; v1: none, so 0).
  docs/04-control/08-control-store-organization.md §5.4.2, §5.6.

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
DEFER_AUTOINDEX = "DEFER_AUTOINDEX"     # timing context: a DEFER with AUTO_INDEX_REQUIRED = 1
TIMING_CONTEXTS = MAJOR_STATES + (DEFER_AUTOINDEX,)

# Every timing state 300 ns, 1.2 us per major state: the placeholder time base used since phase 2
# of the simulator. The per-state totals are what devices and the reference model see.
UNIFORM_1200 = {ms: (300, 300, 300, 300) for ms in TIMING_CONTEXTS}  # V1-ONLY

# Timing Architecture §5.1, TIMING_MODE 0 (optimized), TSTEP = 50 ns: fast 5/8/6/5 TSTEPs
# (1.2 us) for FETCH and non-autoindex DEFER; slow 6/9/7/6 (1.4 us) for every other state.
FAST = (250, 400, 300, 250)
SLOW = (300, 450, 350, 300)
MODE_0 = {"FETCH": FAST, "DEFER": FAST, DEFER_AUTOINDEX: SLOW, "EXECUTE": SLOW,
          "INTERRUPT": SLOW, "DMA": SLOW}


@dataclass(frozen=True)
class Design:
    name: str
    build: Path                       # the ROM-generation build directory for this design
    schema: Path                      # the maintained control-word schema
    ts_ns: dict = field(default_factory=lambda: dict(MODE_0))
    boundary_rule: str = "instr_end"  # see is_last_state
    ir_source: str = "MDB"            # IR's load input (slice A)
    ea_page: str = "MA"               # EA formation's page source (slice A)
    non_execute_variant: str | None = "IR_CLASS"      # slice B
    sequencer_a2: str | None = "IR_NO_EXECUTE"        # slice B
    opr_pass: bool = True             # AC_SRC 7 and L_OP 1 select the OPR pass unit (slice C1)

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
                 ts_ns=dict(UNIFORM_1200),
                 ir_source="MB", ea_page="PC", boundary_rule="execute",
                 non_execute_variant=None, sequencer_a2=None,
                 opr_pass=False),                                     # V1-ONLY
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
    - "execute": every instruction ends in EXECUTE (v1).
    - "instr_end": INSTR_END (docs/04-control/20-control-output-definitions/
      02-architectural-control-signals.md §4.10): EXECUTE, or FETCH when IR_NO_EXECUTE and not
      IR_INDIRECT (a direct JMP), or DEFER when IR_NO_EXECUTE (a JMP I) (v2).
    """
    if design.boundary_rule == "execute":  # V1-ONLY
        return ms == "EXECUTE"
    if design.boundary_rule == "instr_end":
        if ms == "EXECUTE":
            return True
        if ms not in ("FETCH", "DEFER"):
            return False
        no_execute, indirect = _completion_decodes(ir)
        if no_execute is None:
            return False
        return bool(no_execute) and (ms == "DEFER" or not indirect)
    raise ValueError(f"unknown boundary rule {design.boundary_rule!r}")


def _completion_decodes(ir):
    """(IR_NO_EXECUTE, IR_INDIRECT) of `ir`, from the simulator's IR decodes."""
    from .inputs import ir_decodes        # inputs does not import design
    d = ir_decodes(ir)
    return d["IR_NO_EXECUTE"], d["IR_INDIRECT"]


def major_states(design: Design, ir: int) -> tuple:
    """The major states instruction `ir` runs, in order, under `design`'s boundary rule: the
    instruction-level cycle count the reference model charges (option2/plan.md phase 2.6)."""
    indirect = ir >> 9 <= 0o5 and (ir >> 8) & 1        # an indirect MRI, JMP and JMS included
    if design.boundary_rule == "execute":  # V1-ONLY
        return ("FETCH", "DEFER", "EXECUTE") if indirect else ("FETCH", "EXECUTE")
    if design.boundary_rule == "instr_end":
        no_execute, _ = _completion_decodes(ir)
        if no_execute:                                  # JMP: completes in FETCH or DEFER
            return ("FETCH", "DEFER") if indirect else ("FETCH",)
        return ("FETCH", "DEFER", "EXECUTE") if indirect else ("FETCH", "EXECUTE")
    raise ValueError(f"unknown boundary rule {design.boundary_rule!r}")


def ts_table_from_states(state_ns: dict) -> dict:
    """A per-TS table from per-major-state durations (each state's time charged at its TP4),
    for callers that give only a duration per major state."""
    return {ms: (0, 0, 0, ns) for ms, ns in state_ns.items()}
