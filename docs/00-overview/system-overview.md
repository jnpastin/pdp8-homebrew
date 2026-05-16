# System Overview

Status: work in progress

## Objective

The goal of this project is to design and build a homebrew computer using discrete logic that is compatible with the PDP-8/e architecture.

Primary target:
- Run OS/8 and associated PDP-8 software

---

## Key Features

- 12-bit architecture
- PDP-8/e instruction set compatibility
- SRAM-based memory system
- Modular PCB-based hardware design
- Backplane-based expansion
- Front panel modeled after PDP-8/I for observability

---

## Compatibility Goals

The system aims to achieve:

### Required
- Correct execution of PDP-8 instructions
- Compatible instruction encodings
- Functional support for OS/8

### Not Required (initially)
- Full DEC hardware replication
- Timesharing support (UF not implemented initially)
- Data break (DMA)

---

## System Components (Planned)

- CPU (may span multiple boards)
- Memory subsystem (SRAM)
- I/O subsystem (serial console, paper tape)
- Front panel interface
- Backplane interconnect

---

## Current Status

Completed:
- Repository and documentation structure
- Initial architecture definition
- Register set identified
- High-level bus structure outlined
- Timing architecture defined (TCLK / TSTEP / TP / TS model)
- Major state model defined (FETCH, DEFER, EXECUTE, INTERRUPT)

In progress:
- Control signal definition
- Interrupt and skip models
- Bus and register refinement

Not yet defined:
- Microarchitecture (cycle-by-cycle behavior)
- Control implementation
- I/O device behavior

---

## Known Gaps

The following areas must be defined before hardware design begins:

- Complete microoperation specification
- Control signal mapping to instruction execution
- Timing pulse and state definitions
- I/O instruction behavior and device interaction

---

## Risks

- Control complexity may increase significantly depending on implementation choice
- Subtle behavioral mismatches (skip, interrupt, indirect addressing) may break OS/8
- Timing design may become complex at higher clock rates

---

## Notes

This document describes intent and direction, not final design decisions.

Many implementation details are intentionally deferred until the behavioral model is fully specified.
