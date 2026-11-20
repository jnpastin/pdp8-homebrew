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


DESIGNS = {
    # V1-ONLY: v1 keeps its original paths, so v1 output is unchanged by the selection.
    "v1": Design("v1", PurePosixPath("rom/microcode/v1"),
                 PurePosixPath("build/simulation_outputs/rom-generation"), frozen=True),
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
