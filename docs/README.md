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

### 1. Separation of Concerns
Each section represents a distinct abstraction layer:

- ISA defines observable behavior
- Architecture defines the machine model
- Microarchitecture defines execution structure
- Control defines signal behavior
- Timing defines ordering of events
- Physical documents define implementation

Layers must not be conflated.

---

### 2. Single Source of Truth
Each concept is defined in exactly one location.

- Definitions must not be duplicated
