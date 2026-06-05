# Control Constraints Model

## Purpose

Defines global system constraints and invariants governing all control behavior.

---

## Ownership

Defines which component drives a bus.

Example:
```
RD = 1 → Memory drives MDB
WR = 1 → CPU drives MDB
```

---

## Electrical Validity

A bus is electrically valid when exactly one device is driving it.

---

## Semantic Validity (Consumer-Relative)

Validity is defined relative to a consumer.

Example:
```
During WR:
  MDB is not valid for CPU consumption
  Write data is defined by MB
```

---

## Core Invariant

```
Bus driven ≠ safe to consume
```

---

## Dataflow Model

```
CPU → MDB → MB → Memory
Memory → MDB → MB → CPU
```

---

## Consumption Rule

No component consumes a bus directly.

All consumption occurs via registers.

---

## Precondition Constraint

Defines required prior state.

Example:
```
WR requires MB to contain valid data
```
