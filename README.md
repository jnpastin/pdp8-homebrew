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
- `/firmware` - Microcode / ROM contents (if used)
- `/sim` - Simulation models and test programs
- `/tools` - Supporting utilities and scripts
- `/diagrams` - Block diagrams and timing diagrams
- `/specs` - Structured machine-readable specifications
- `/notes` - Working notes and exploration
- `/build` - Generated artifacts (gerbers, ROM images, etc.)

---

## Current Status
Early design phase:
- Architecture defined
- Documentation structure in place
- Microarchitecture and control logic in progress

---

## Design Philosophy
- Strict separation of ISA, microarchitecture, and implementation
- Prioritize correctness over performance
- Build for observability and incremental validation

---

## Getting Started
Start with:
- `/docs/00-overview`
- `/docs/01-architecture`
