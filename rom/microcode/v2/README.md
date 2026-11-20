# Control Microcode Version 2 (branch `one-cycle-fetch`)

Version 2 is the option 2 control design: OPR and directly addressed JMP complete in FETCH, and JMP I completes in DEFER ([option2/spec.md](../../../option2/spec.md)). It is built as the documentation under `docs/` changes, slice by slice ([option2/plan.md](../../../option2/plan.md)).

It began as a copy of version 1 (phase 2.2), with `control_design_version` set to `v2` and the generator source paths renamed. `run_pipeline.py --dry-run --design v2` reproduced every artifact unchanged, and its packed images were byte-identical to version 1's.

Version 1 (`../v1/`) stays selectable while this branch is active. It is **frozen**: it is packed from its maintained artifacts and no longer regenerated from `docs/`, which now describe version 2. Selection: `PDP8_DESIGN` or `run_pipeline.py --design` (`tools/rom-generation/common/design.py`). Version 1 is removed before this branch merges (plan phase 10).

The rest of `../v1/README.md` (purpose, authority, contents) applies here unchanged.
