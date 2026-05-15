# Hardware

## Purpose
This directory contains all hardware design artifacts, including schematics and PCB layouts.

---

## Structure

- `backplane` - System backplane design
- `cpu` - CPU subsystem
  - `alu` - Arithmetic and logic unit
  - `control` - Control logic
  - `registers` - Register implementation
- `memory` - Memory subsystem
- `io` - I/O devices
  - `serial` - Console interface
  - `ptr_ptp` - Paper tape devices
- `front_panel` - Operator interface hardware
- `common` - Shared components and libraries

---

## Guidelines
- Each module should include:
  - Schematic
  - PCB layout (if applicable)
  - Local README describing function and interfaces
- Do not place generated files (gerbers, exports) here

---

## Tooling
- KiCad (version to be defined)

---

## Status
Design in early stages; no finalized boards
