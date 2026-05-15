# Design Principles

Status: work in progress

## Core Principles

### 1. Correctness Over Performance
The system must behave correctly according to PDP-8/e semantics before any effort is made to optimize performance.

---

### 2. Separation of Concerns

The design must clearly separate:

- Instruction Set Architecture (ISA)
  - What software observes

- Microarchitecture
  - How instructions are executed

- Implementation
  - How the system is physically built

These layers must not be conflated.

---

### 3. Incremental Development

The system should be built and validated in stages:

- Minimal CPU
- Basic instruction execution
- Console I/O
- Interrupt support
- OS/8 compatibility

---

### 4. Observability and Debuggability

The system must support detailed inspection of internal state.

Examples:
- Front panel indicators
- Timing state visibility
- Bus observation
- Single-step execution modes

---

### 5. Modularity

The system will be divided into independent modules:

- CPU subcomponents (ALU, control, registers)
- Memory
- I/O devices
- Backplane

Each module should have clearly defined interfaces.

---

### 6. Conservative Electrical Assumptions

Design decisions should account for:

- Signal integrity
- Propagation delays
- Fan-out limits

Clock targets are progressive, not fixed.

---

### 7. Faithful Behavior, Not Exact Replica

The system aims to reproduce observed PDP-8 behavior, not exact internal implementation.

Examples:
- Memory implemented with SRAM instead of core
- Control logic may differ from DEC hardware
- Front panel may be logically equivalent but not electrically identical

---

## Non-Goals

- Exact reproduction of PDP-8 hardware schematics
- Maximum performance at the expense of clarity
- Early optimization before behavior is fully defined

---

## Open Decisions

The following architectural decisions remain unresolved:

- Control strategy (hardwired vs microcoded)
- Timing model implementation
- I/O bus structure
- Backplane electrical characteristics

---

## Notes

These principles are intended to guide decisions as the project evolves.

They should be revisited periodically as the design matures.