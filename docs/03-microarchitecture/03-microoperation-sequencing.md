# Micro-Operation Sequencing

## 1. Purpose

Defines how μops are selected, evaluated, and committed over time.

This document establishes the rules governing:
- assignment of μops to TS
- conditional execution
- visibility of register state
- interaction with control decisions

This document does not define individual instructions or μops.

---

## 2. Execution Cycle Model

Execution proceeds in discrete steps defined by TS and TP.

For each TSn:

    During TSn:
        - control evaluates conditions using stable state
        - control selects a set of active μops

    At TPn:
        - all selected μops commit simultaneously

---

## 3. μop Selection

For each TSn:

    Active_μops(TSn) = f(MS, TS, IR, FLAGS, EXT)

Where:
- MS defines the major state (FETCH, DEFER, EXECUTE, INTERRUPT, DMA)
- TS defines the current time step
- IR provides instruction encoding
- FLAGS are derived from register state
- EXT represents external inputs

Constraints:
- selection must be deterministic
- selection must depend only on stable inputs

---

## 4. Conditional Execution

Conditions are not μops.

Rules:
- conditions are evaluated during TSn using register state
- conditions do not produce stored values, except a Group 2 OPR's skip decision in `SKIP` (see below)
- conditions are used only to select μops

Example form:

    if (condition):
        include μop in Active_μops(TSn)

Else:
    μop is not executed


The one exception is `SKIP`: a Group 2 OPR's skip decision is loaded into `SKIP` at FETCH TP3 (`OPR_SKIP_REQ_TO_SKIP`) and used at FETCH TP4, because CLA may clear AC at the same TP3 ([Skip Model §12](../08-interrupts-and-skip/05-skip-model.md#12-skip-state)).

---

## 5. Concurrency Model

Within a single TSn:

- all μops are evaluated concurrently
- all μops observe the same input state
- no μop may depend on another μop in the same TSn

Constraint:

    No ordering exists within a TSn

---

### 5.1 Bus Domain Exclusivity

μops that consume external bus domains must not conflict.

Specifically:
- MEM_READ_TO_MB (MDB domain) and DB_READ_TO_AC (DB domain)
  must not be active in the same TS

Rationale:
- Each requires exclusive validity assumptions about its source bus
- Simultaneous use would violate determinism and bus isolation

---

## 6. Register Visibility

Register values follow strict timing rules.

For any TSn:

- reads observe values committed at TP(n-1)
- writes become visible only after TPn

Everything in TSn, including its TP, derives only from state committed by TP(n-1). A write is captured at the leading edge of TPn and becomes visible as TPn ends ([Timing Architecture §7.6](../09-timing/02-timing-architecture.md#76-rule-6--two-ranks)). Apart from TP itself, no edge or level that arises during a TS commits or selects anything.

Implications:

- all μops in TSn operate on the same stable inputs
- results of TSn are not visible until TPn completes

---

## 7. State Update Rules

At TPn:

- all active μops commit simultaneously
- no partial updates occur
- all target registers update atomically

Constraint:

    Each register may be targeted by at most one μop per TSn

If violated:
- behavior is undefined (design error)

---

## 8. Major State Interaction

MS is updated separately from μops.

Rules:

- MS_NEXT is determined during TS4 by control logic
- MS is updated at TP4

Constraint:

- MS updates are not μops
- μops must not directly modify MS


### 8.1 EXECUTE Phase Invariants

The EXECUTE definitions, for the memory reference instructions other than JMP and for the IOTs, assume:

- MS = EXECUTE
- EA_ADDR is the fully resolved effective address and is stored in the EA register
- All indirect addressing and autoindex effects have completed
- IR is stable and valid for the duration of execution

---


## 9. External Inputs (EXT)

External inputs influence execution only through control decisions.

Rules:

- EXT may be used during TS to evaluate conditions and determine μop selection
- EXT reaches a register only as data selected by a control-word micro-operation, never by itself ([External Inputs §2](../04-control/10-control-input-definitions/04-external-inputs.md#2-timing-model))
- EXT does not trigger or initiate state changes at TP
- any effect of EXT must be realized only through control-selected μops

Constraints:

- EXT must be stable for the duration of the TS in which it is evaluated ([External Inputs §2](../04-control/10-control-input-definitions/04-external-inputs.md#2-timing-model))
- EXT must not introduce implicit or asynchronous state changes


---

## 10. Determinism Requirement

Execution must satisfy:

    Given identical:
        MS, TS, register state, IR, FLAGS, EXT

    Active_μops(TSn) is identical
    Resulting state at TPn is identical

Implications:

- behavior is fully deterministic
- no hidden or implicit inputs exist

---

## 11. Prohibited Behavior

The following are explicitly disallowed:

- μop-to-μop dependency within a TSn
- multiple μops writing the same register in a TSn
- use of transient datapath signals as inputs
- storing intermediate condition results in registers, other than `SKIP` (section 4)
- modifying MS via μops

---

## 12. Summary

Execution is defined as:

- control selects μops each TSn
- μops execute concurrently
- results commit at TPn
- conditions influence selection, not state

This model ensures:
- deterministic behavior
- strict separation of control and datapath
- absence of implicit ordering or hidden state