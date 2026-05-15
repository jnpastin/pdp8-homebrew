# Documentation

## Purpose
This directory contains all human-readable design documentation for the system.

It serves as the authoritative source for:
- System behavior
- Architecture
- Design constraints

---

## Structure

- `00-overview` - High-level system overview and goals
- `01-architecture` - Programmer-visible machine model
- `02-isa` - Instruction set architecture
- `03-microarchitecture` - Execution model and microoperations
- `04-control` - Control signals and state behavior
- `05-buses-and-signals` - Bus definitions and signal lists
- `06-memory` - Memory architecture and access model
- `07-io` - I/O system definition
- `08-interrupts-and-skip` - Interrupt and skip behavior
- `09-timing` - Clocking and timing model
- `10-front-panel` - Operator interface definition
- `11-backplane-and-physical` - Hardware structure
- `12-verification` - Testing and validation
- `13-implementation-plan` - Build phases and roadmap
- `appendices` - Supporting material

---

## Rules
- Documents here define behavior, not implementation details
- Do not embed schematic-specific assumptions
- Changes should maintain consistency across sections
