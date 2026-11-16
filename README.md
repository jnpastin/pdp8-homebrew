# PDP-8/e Compatible Discrete Logic Computer

## Overview
This repository contains the design, documentation, and implementation artifacts for a homebrew computer compatible with the PDP-8/e architecture, implemented using discrete logic.

The primary goal is to achieve software compatibility sufficient to run OS/8 and associated toolchains.

---

## Objectives
- PDP-8/e instruction set compatibility
- OS/8 support
- Discrete logic implementation (no microcontrollers)
- Modular PCB-based system with backplane
- Strong observability and debugging support

---

## Repository Structure

- `/docs` - Design documentation and specifications
- `/hardware` - KiCad schematics and PCB designs
- `/rom` - ROM and microcode content
- `/sim` - Simulation models and test programs
- `/tools` - Supporting utilities and scripts
- `/diagrams` - Block diagrams and timing diagrams
- `/specs` - Structured machine-readable specifications
- `/notes` - Working notes and exploration
- `/build` - Generated artifacts (gerbers, ROM images, etc.)

---

## Current Status
Active design phase.

Defined:
- Architecture, register model, and ISA (`docs/01`, `docs/02`)
- Microarchitecture: major states, micro-operations, and execution of every instruction class, interrupts, front-panel operations, and DMA (`docs/03`)
- Control: control inputs and outputs, control word, control addressing, and control store organization (`docs/04`)
- Buses and signals, memory, I/O and DMA interfaces, interrupts and skip, and timing (`docs/05` to `docs/09`)

Implemented:
- ROM-generation toolchain: extracts the control specifications from the documentation, generates and validates symbolic control words, and packs them into verified logical control-store images (`tools/rom-generation`, `rom/microcode/v1`)

Not yet started:
- Simulation against the packed control store (`sim/`)
- Physical ROM image format
- Front panel, backplane and physical design, verification plan, and implementation plan (`docs/10` to `docs/13`)
- Hardware design (`hardware/`)

---

## Design Philosophy
- Strict separation of ISA, microarchitecture, and implementation
- Prioritize correctness over performance
- Build for observability and incremental validation

---

## Getting Started
Start with:
- `/docs/00-overview`
