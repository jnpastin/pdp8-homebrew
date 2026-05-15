# PDP-8/e Compatible Discrete Logic Computer
## Agent Handoff Document

Status: work in progress (updated)

---

# 1. Project Summary

## Objective
Design and build a discrete-logic computer compatible with the PDP-8/e architecture.

Primary goal:
- Run OS/8 and standard PDP-8 software (PAL-8, BASIC, diagnostics)

## Constraints
- Discrete logic only (no microcontrollers)
- SRAM-based memory (no core memory)
- Modular PCB system with backplane
- Strong observability and debug capability

## Compatibility Target
- Bit-accurate instruction encoding
- Correct instruction behavior
- Sufficient fidelity for OS/8

---

# 2. Repository Structure (Implemented)

Top-level directories now exist:
- /docs - Design documentation (authoritative)
- /hardware - KiCad schematics and PCB designs
- /firmware - Microcode / ROM content
- /sim - Simulation and validation
- /tools - Supporting utilities
- /diagrams - Visual documentation
- /specs - Machine-readable definitions
- /notes - Working exploration
- /build - Generated artifacts

Each directory includes README stubs.

---

# 3. Architectural Model (Current)

## Core
- 12-bit word
- PDP-8 instruction set

## Memory
- 4K words per field
- 8 fields (32K total)
- IF (Instruction Field)
- DF (Data Field)
- No UF initially

## Registers

Programmer-visible:
- PC, AC, MQ, Link, SR

Memory path:
- MA, MR, MB, IR

Field registers:
- IF, DF

Control state:
- Major State (FETCH/DEFER/EXECUTE/INTERRUPT)
- Timing state (not finalized)
- IE, INT_REQ, INT_DELAY
- SKIP_PENDING

## Memory Data Flow
Memory → MR → MB → internal data bus

---

# 4. Behavioral Requirements

## Instruction Set
- MRI, OPR groups, IOT
- Exact bit encoding required
- Correct handling of indirect, auto-index, and page addressing

## Interrupts
- Recognized at instruction boundaries
- IE-controlled
- CIF introduces delay
- Entry: store PC, jump to location 1

## Skip Logic
- Latched SKIP_PENDING model
- Evaluated during execute
- Applied during next PC increment

---

# 5. Bus Model (Preliminary)

- AB[0:11] - Address bus
- DB[0:11] - Internal data bus
- MDB - Memory data bus
- DEV[0:5] - I/O device select

I/O data path is not finalized.

---

# 6. Timing Model (Concept Only)

- High-frequency master clock (experimental upper bound ~20 MHz)
- Timing pulses (TP) derived from clock
- Major states built from multiple TP steps (~28)

Not yet defined:
- Exact TP count
- State transitions
- Control timing relationships

---

# 7. Front Panel

Target: PDP-8/I style

Features:
- Examine/Deposit
- Load Address
- Run/Stop
- Multi-level single-step (cycle, timing, major, instruction)

Implementation deferred.

---

# 8. I/O Plan

Initial:
- UART console (KL8E-like)
- Paper tape (PTR/PTP)

Future:
- Disk
- Printer
- Modem
- Video (possible)

IOT behavior not fully specified.

---

# 9. Physical Design

- Backplane-based architecture
- Multi-board CPU expected
- Per-module debug LEDs

Electrical details not defined.

---

# 10. Completed Work

- Repository structure created
- High-level architecture defined
- Register set established
- Interrupt model outlined
- Skip model defined
- Documentation framework written

---

# 11. Work in Progress

- Control signal definitions
- Bus refinement
- Timing model definition

---

# 12. Not Yet Defined (Critical)

- Microarchitecture (cycle-level execution)
- Control implementation (hardwired vs microcoded)
- Full timing specification
- I/O device behavior
- Fielding instruction details (CIF/CDF timing and edge cases)

---

# 13. Key Risks

- Control logic complexity
- Incorrect skip or interrupt edge behavior
- Timing interactions between MR/MB and execution
- IOT semantics mismatch with OS/8 expectations

---

# 14. Immediate Next Steps

1. Define register model formally
2. Define instruction encoding document
3. Complete interrupt + skip specs
4. Define execution (microoperations)
5. Define timing model

---

# 15. Guidance for Next Contributor

Do not:
- Begin schematic capture
- Define control signals prematurely
- Mix ISA and implementation

Do:
- Formalize behavior first
- Define cycle-level execution
- Resolve all edge cases

---

# 16. Status Summary

The project has transitioned from conceptual planning to structured specification development.

The foundation is in place, but the design is not yet ready for hardware implementation.

Primary focus now: complete behavioral and microarchitectural specifications.
