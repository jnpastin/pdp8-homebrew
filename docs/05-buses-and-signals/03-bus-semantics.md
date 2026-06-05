# 03 Bus Semantics

## Purpose

This document defines the semantic behavior of system buses, including validity, consumption rules,
and the relationship between signal ownership, control signals, and timing.

This document complements signal definitions and ownership by specifying when bus values are
meaningful and when devices may act on them.

---

## 1. Scope and Separation of Concerns

This document defines:
- Bus value validity
- Device consumption rules
- Relationship to control signals
- Relationship to timing (TP)

This document does NOT define:
- Signal ownership (defined in ownership document)
- Electrical drive behavior

---

## 2. Ownership vs Validity

Two independent concepts must be distinguished:

### Ownership

Defines:
- Which entity is permitted to drive the bus

Ownership is governed by:
- DB_GRANT
- DB_ADDR_EN
- Control state

### Validity

Defines:
- Whether the current value on the bus is meaningful for use

Key invariant:

```
Ownership != Validity
```

- Ownership is necessary but not sufficient for validity
- A bus may be owned and driven yet still be invalid

---

## 3. Architectural Validity

Architectural validity determines when other modules (memory, I/O devices)
may act on the value of a bus.

### Rule

A bus is architecturally valid only when a defined operation requires it.

For address and memory data buses:

```
Valid operations include:
  RD
  WR
  DB_READ
  DB_WRITE
```

### Negative Definition

```
A bus is considered invalid unless a defined operation is active.
```

---

## 4. Microarchitectural Validity

Microarchitectural validity determines when internal CPU registers sample bus values.

### Rule

```
Bus values are latched only at defined timing pulses (TP)
```

### Requirement

```
Bus values must be stable prior to the TP at which they are latched
```

### Notes

- Microarchitectural validity is independent of architectural validity
- A bus may be architecturally invalid yet still be sampled internally

---

## 5. Bus Invalidity (Negative Logic)

### Core Rule

```
Buses are invalid by default
```

They become valid only when explicitly used by a defined operation.

### Implications

- The presence of a driver does not guarantee validity
- Absence of a valid operation guarantees invalidity

---

## 6. Transition Behavior

During ownership transitions:

- Bus drivers may be disabled
- The bus may enter High-Z state
- Weak pull-ups may define a default value

### Constraint

```
Bus values during transition must be treated as invalid
```

---

## 7. Device Consumption Rules

Devices must follow the rule:

```
Do not act on bus values unless a valid operation is active
```

### For memory and DMA

```
Use bus values only when:
  RD or WR or DB_READ or DB_WRITE is asserted
```

### For other devices

- Do not infer meaning from bus values alone
- Use control signals to determine when to act

---

## 8. Global Invariants

- Ownership defines who may drive a bus
- Validity defines when the bus value is meaningful
- Ownership does not imply validity
- Validity is defined by control signals
- Microarchitectural timing (TP) defines when values are sampled, not when they are meaningful
- Buses must be treated as invalid outside of defined operations
- External request signals (/INT_REQ, /DB_REQ) are not part of architectural state
- These signals influence control behavior but do not define bus validity

---

## Summary

This document establishes a clear separation between:
- Electrical ownership
- Logical validity
- Timing-based sampling

These distinctions ensure:
- Correct device behavior
- Safe handling of transition states
- Clear reasoning about bus usage across the system
