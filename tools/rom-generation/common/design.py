"""The control design a ROM-generation run builds: the single selection point.

option2/plan.md (phase 2) keeps the v1 and v2 control designs side by side on the
`one-cycle-fetch` branch, built so that v1 can be removed before the merge. Every tool reads
its maintained-artifact directory, its build directory, and the `control_design_version` it
writes from `DESIGN`, which the `PDP8_DESIGN` environment variable selects (default `v1`).
The pipeline sets the variable for the tools it runs (`run_pipeline.py --design`).

A frozen design's artifacts are not regenerated from `docs/`: the documentation describes the
newest design, and a frozen design is packed from its maintained artifacts alone.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import PurePosixPath

ENVIRONMENT_VARIABLE = "PDP8_DESIGN"
DEFAULT = "v1"  # V1-ONLY: becomes the surviving design's name at cleanup


@dataclass(frozen=True)
class Design:
    name: str                    # the control_design_version written into artifacts
    maintained: PurePosixPath    # promoted artifacts, relative to the repository root
    build: PurePosixPath         # tool outputs, relative to the repository root
    frozen: bool                 # packed from maintained artifacts only; not regenerated
    # Control-store address formation outside EXECUTE (Control Store Organization §5.4.2,
    # §5.6): the IR-derived decode that drives the datapath slice's VARIANT, and the ones on
    # the sequencer slice's A2 and A1. None: VARIANT = 0, A2 = 0, A1 = 0 (v1).
    non_execute_variant: str | None = "IR_CLASS"
    sequencer_a2: str | None = "IR_NO_EXECUTE"
    sequencer_a1: str | None = "IR_OPR_HLT"
    # The state overlay group's low three bits pass through a 3-bit 2:1 multiplexer selected
    # by RUN: FP_CMD while halted, running-only signals while running (CSO §6.3).
    state_group_run_mux: bool = True
    # The datapath slice's device count (Control Store Organization §4.2, §8): its width in
    # bits must fit in this many 8-bit devices.
    datapath_devices: int = 5


DESIGNS = {
    # V1-ONLY: v1 keeps its original paths, so v1 output is unchanged by the selection.
    "v1": Design("v1", PurePosixPath("rom/microcode/v1"),
                 PurePosixPath("build/simulation_outputs/rom-generation"), frozen=True,
                 non_execute_variant=None, sequencer_a2=None, sequencer_a1=None,
                 state_group_run_mux=False, datapath_devices=6),
    "v2": Design("v2", PurePosixPath("rom/microcode/v2"),
                 PurePosixPath("build/simulation_outputs/rom-generation-v2"), frozen=False),
}


def select(name: str | None = None) -> Design:
    """The design named, or the one `PDP8_DESIGN` selects."""
    name = name or os.environ.get(ENVIRONMENT_VARIABLE) or DEFAULT
    try:
        return DESIGNS[name]
    except KeyError:
        raise SystemExit(f"{ENVIRONMENT_VARIABLE}={name!r} is not a control design "
                         f"(known: {', '.join(DESIGNS)})") from None


DESIGN = select()
