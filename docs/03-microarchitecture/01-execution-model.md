## Execution Model

### Purpose

Defines how processor behavior is expressed and evaluated over time using the state model.

This document establishes the formal abstraction used to describe execution and binds behavior to the TS/TP timing structure.

---

## Terminology and Scope

### Microstate (μstate)

The complete execution context is:

    μstate = (MS, TS)

Where:
- MS defines the instruction-level phase
- TS defines the ordering position within the phase

Constraints:
- μstate is the only execution state variable controlling sequencing

---

### TS / TP Execution Model

Execution is defined by two distinct roles:

    TS: evaluation window
    TP: commit event

For each TSn:
- evaluation occurs during TSn
- results are committed at TPn

Constraints:
- TS defines ordering
- TP performs no computation
- TP only captures results

---

## Micro-Operation Definition

A micro-operation (μop) is a single, atomic state update:

    target <- function(sources)

Properties:
- evaluated during a TS
- result must be stable by TPn
- committed exactly once at TPn
- no conflicts with other μops in the same TS

---

## Execution Representation

All execution must be expressed as:

    During TSn:
        evaluate function(sources)

    At TPn:
        target <- evaluated_result

Constraints:
- all state updates occur only at TP
- no implicit or hidden behavior is permitted

---

## Ordering Semantics

Execution ordering is defined exclusively by TS.

Rules:
- TSn completes before TSn+1 begins
- μops in different TS execute in TS order
- all μops within a TS are evaluated concurrently
- all results within a TS are committed simultaneously at TPn

Constraint:
- no ordering exists within a single TS

---

## Source Domains

μops may use only the following sources:

- Architectural registers
- Control-visible registers (IR, MS)
- Internal registers
- Derived FLAGS (functions of register state)
- EXT inputs

Constraints:
- all sources must be stable during the TS in which they are used
- FLAGS are derived only from registers
- EXT must be stable prior to TP

---

## Stability Requirements

### Inputs

All sources used by a μop must be stable for the entire TS during evaluation.

### Outputs

All evaluated results must be stable before the TP that commits them.

### Boundary Behavior

Values are not assumed to remain stable across TS boundaries.

Implications:
- values stable in TSn may change in TSn+1
- if stability across TS boundaries is required, it must be enforced via registers

---

## Micro-Operations vs Control

### Micro-Operations

Define required state transitions:

    AC <- AC + MB
    PC <- PC + 1

### Control Signals

Define how the system implements those transitions.

### Relationship

    μop
        -> required datapath behavior
        -> control signals

Constraint:
- μops define behavior
- control implements behavior

---

## Determinism and Repeatability

Execution must satisfy:

    Given:
        μstate, registers, IR, FLAGS, EXT

    The resulting state at TP is:
        unique
        repeatable

Implications:
- identical inputs must always produce identical outputs
- no nondeterministic behavior is permitted

---

## State Transition Constraints

Execution decisions may depend only on:

- register state
- IR
- FLAGS
- EXT

Must NOT depend on:
- transient datapath signals
- control signals
- intermediate combinational values

---

## Relationship to State Model

This model operates over [00-state-model](./00-state-model.md):

- TS defines evaluation ordering
- TP defines state commit
- MS defines execution phase

Constraints:
- TS progression is independent of execution
- MS transitions occur only at TP4

---

## Summary

Execution is defined as:

- ordered by TS
- evaluated during TS
- committed at TP
- expressed as μops
- operating only on defined source domains

Micro-operations define behavior.
Control signals implement that behavior.
