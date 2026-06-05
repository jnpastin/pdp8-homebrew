
## Microarchitecture

Reference Diagram:
[High-Level Architecture Diagram](../../diagrams/architecture/High-Level-Architecture/export/High-Level-Architecture.png)

### Purpose

Defines how ISA behavior is executed over time using the system’s timing and control model.

This layer specifies:
- Execution ordering
- Operation composition
- Mapping from ISA semantics to control behavior

It describes how behavior occurs, not what the behavior is.

---

### Scope

Includes:
- Execution over microstates (MS, TS)
- Ordering of operations within an instruction
- Composition rules for OPR instructions
- Interaction between control outputs and datapath behavior

Excludes:
- Instruction semantics ([../02-isa/README.md](../02-isa/README.md))
- Control signal definitions ([../04-control/README.md](../04-control/README.md))
- Timing signal definitions ([../09-timing/README.md](../09-timing/README.md))

---

### Execution Model

ustate = (MS, TS)

- MS: Major State
- TS: Time State

Behavior is evaluated during TS and committed at TP.
All state changes occur only at TP.

---

### Relationship to Control

Control defines the mechanism that produces behavior.

See:
- [../04-control/00-control-model.md](../04-control/00-control-model.md)

Microarchitecture defines how ISA behavior maps to sequences of control actions.

---

### Relationship to Timing

Timing defines when events occur.

See:
- [../09-timing/README.md](../09-timing/README.md)

Microarchitecture binds control behavior to timing structure.

---

### OPR Execution Model

OPR instructions are composable bitfields.

- Each bit represents an operation
- Each operation is assigned to a TS
- Enabled operations in a TS execute in parallel

Ordering is determined only by TS.

---

### Design Constraints

- Behavior must be expressible as:
  (MS, TS, IR, FLAGS, EXT) → CONTROL
- No implicit sequencing logic
- No hidden state

---

### Summary

Microarchitecture defines structured execution as microstate sequences driven by control.
