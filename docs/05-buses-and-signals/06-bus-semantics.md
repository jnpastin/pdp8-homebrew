# Bus Semantics

## Purpose

This document defines the semantic behavior of shared system buses.

This document defines:

- the relationship between ownership and validity
- bus validity concepts
- electrical bus invariants
- bus consumption rules
- domain awareness

This document does NOT define:

- bus ownership rules
- bus arbitration mechanisms
- operation-specific behavior
- timing definitions
- physical implementation details

Ownership is defined in:

- [Bus Ownership Matrix](./08-ownership-matrix.md)

Operation semantics are defined in:

- [Control Constraints](../04-control/03-control-constraints.md)
- [Architectural Control Signals](../04-control/20-control-output-definitions/02-architectural-control-signals.md)

---

## Ownership and Validity

Ownership and validity are distinct concepts.

### Ownership

Ownership determines which entity is permitted to drive a bus.

Ownership rules are defined in:

- [Bus Ownership Matrix](./08-ownership-matrix.md)

This document does not define ownership behavior.

### Bus Validity

Bus validity is determined by defined system operations.

A bus value is considered valid only when a defined operation requires that value to be produced, consumed, or interpreted.

Bus semantics does not independently define validity conditions.

Validity is derived from:

- control behavior
- operation definitions
- control constraints

Consumers must treat bus values as invalid unless a defined operation specifies otherwise.

---

## Electrical Semantics

### Driver Exclusivity

At most one device may actively drive a shared bus at any time.

Bus contention is prohibited.

### Inactive Driver Behavior

A device that is not actively driving a shared bus must present a high-impedance (High-Z) output state.

Inactive devices must not influence bus values.

### Undriven Bus State

Shared buses shall have a defined value when no active driver is present.

The mechanism used to establish this value is implementation-dependent.

Consumers must not infer operation semantics from this value.

---

## Consumer Semantics

### No Implied Meaning

The presence of a value on a bus does not imply that an operation is occurring.

Consumers must not infer operational meaning from bus values alone.

### Operation-Defined Interpretation

Bus values are interpreted only within the context of defined operations.

Control definitions and operation specifications are authoritative.

Consumers shall act only when required by the operation currently being performed.

### No Implied Data Transfer

The presence of a bus value does not imply:

- data consumption
- data production
- register updates
- memory activity
- I/O activity

Such behavior must be explicitly defined by the corresponding operation.

---

## Domain Awareness

The system contains multiple independent data domains.

Domain definitions, isolation requirements, and domain-crossing rules are defined in:

- [Domain Boundaries](./07-domain-boundaries.md)

Bus semantics do not define domain membership or crossing behavior.

---

## Global Invariants

- Ownership and validity are independent concepts.
- Ownership does not imply validity.
- Bus validity is determined by defined operations.
- At most one device may actively drive a shared bus at a time.
- Inactive bus drivers must enter a High-Z state.
- Shared buses must have a defined undriven state.
- Consumers must not infer meaning from bus values alone.
- Consumers shall act only within the context of defined operations.
- Domain boundaries remain independent unless explicitly crossed through defined mechanisms.

---

## Summary

Bus semantics define how shared bus values are interpreted and consumed throughout the system.

Ownership controls who may drive a bus. Validity determines when a bus value is meaningful. Operation definitions remain the authoritative source for determining when bus values may be produced, consumed, or interpreted.
