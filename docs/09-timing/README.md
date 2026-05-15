# Timing Documentation

## Purpose

This section defines the timing model of the system.

It provides the authoritative specification for:
- Clocking
- Sequencing of execution
- Event ordering

Timing is responsible for defining **when operations occur**, but not:
- what operations occur (see ISA / microarchitecture)
- how operations are implemented (see control / hardware)

---

## Structure

- `01-terminology.md`  
  Defines all timing-related terms and signals.

- `02-timing-architecture.md`  
  Defines the timing model, sequencing, and execution rules.

- `03-major-state-timing.md` 
  Defines timing behavior for each major state (FETCH, DEFER, etc).

- `04-instruction-timing.md` *(future)*  
  Defines instruction-specific timing behavior.

- `05-memory-timing.md` *(future)*  
  Defines memory interface timing.

- `06-io-timing.md` *(future)*  
  Defines I/O device interaction timing.

- `07-timing-constraints.md` *(future)*  
  Captures real hardware constraints

---

## Key Principles

- Timing defines **when**, not **what**
- All state changes are event-driven
- All behavior must be deterministic
- Timing must be independent of implementation details
