# Simulation

## Purpose
Contains simulation models, test programs, and validation tools.

---

## Structure

- `cpu` - CPU-level simulations
- `memory` - Memory behavior tests
- `system` - Full system simulations
- `test_programs` - PDP-8 binaries for validation

---

## Relationship to `/specs`
`/specs` contains the machine-readable definitions that simulation validates against (instruction encodings, control signal tables, timing state definitions). Simulation results provide evidence that those specifications are correct and complete.

---

## Goals
- Validate instruction behavior
- Verify edge cases (skip, interrupt, indirect)
- Compare results with reference emulator (e.g., SIMH)

---

## Notes
Simulation may be partial and evolve alongside hardware
