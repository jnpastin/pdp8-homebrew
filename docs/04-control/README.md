## 04 Control

Status: draft

### Purpose

Defines the **control signal space** and control word structure.

Control bridges:
- microarchitecture execution (see ../03-microarchitecture/README.md)
- datapath behavior

---

## Scope

Includes:
- control signal definitions
- control word composition
- mapping from control outputs to datapath effects

Excludes:
- instruction semantics (see ../02-isa/README.md)
- execution timing (see ../09-timing/README.md)

---

## Control Model

Control is a function of:

MS, TS, IR bits, FLAGS

See:
- ../03-microarchitecture/README.md

---

## Outputs

Control signals include:
- register load enables
- ALU operations
- bus selection
- memory control
- MS\_next

---

## Control Word

Each control word defines:

- operations enabled during TS
- state changes committed at TP
- next major state

---

## Constraint

All control must be representable as:

CONTROL = f(MS, TS, IR bits, FLAGS)

No external sequencing logic is permitted.
