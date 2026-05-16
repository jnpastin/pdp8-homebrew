# Hardware

## Purpose
This directory will contain all hardware design artifacts, including schematics and PCB layouts.

---

## Status
Not yet started. Directory structure will be defined when hardware design begins.

Top-level module directories are placeholders:

- `backplane/` - System backplane
- `cpu/` - CPU subsystem
- `memory/` - Memory subsystem
- `io/` - I/O devices
- `front_panel/` - Operator interface
- `common/` - Shared components and footprint libraries

Internal structure for each module is TBD.

---

## Guidelines (when work begins)
- Each module should include a schematic and a local README describing function and interfaces
- PCB layouts go in the relevant module directory
- Generated files (gerbers, exports) go in `/build/gerbers`, not here

---

## Tooling
- KiCad (version to be confirmed before design begins)
