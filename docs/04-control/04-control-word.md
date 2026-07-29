# Control Word

## Purpose

Defines the structure and role of the control word (CONTROL_WORD).

This document establishes:
- what the control word represents
- how it is partitioned
- how it relates to control behavior

This document defines structure only.

Signal definitions are provided in:
- [Microarchitectural Control Signals](20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Architectural Control Signals](20-control-output-definitions/02-architectural-control-signals.md)
- [Sequencing Control Signals](20-control-output-definitions/03-sequencing-control-signals.md)

Control address formation is defined in:
- [Control Addressing](02-control-addressing.md)

Constraints are defined in:
- [Control Constraints](03-control-constraints.md)

---

## 1. Control Word Definition

The control word is the output of the control store:

```
CONTROL_WORD = ROM[CTRL_ADDR]
```

Where:

- CTRL_ADDR is defined in [Control Addressing](02-control-addressing.md)
- CONTROL_WORD defines all control outputs for a cycle

Constraint:
- CONTROL_WORD must fully determine system behavior for the current cycle.
- No additional decoding or interpretation is permitted after ROM lookup.

---

## 2. Role of the Control Word

The control word represents the result of a control decision.

Control flow:

```
(MS, TS, IR_FIELDS, FLAGS, EXT)
→ CTRL_ADDR
→ CONTROL_WORD
→ system behavior
```

Interpretation:

- input domains define the condition space
- CTRL_ADDR selects a control case
- CONTROL_WORD defines the outcome of that case

Constraint:
- CONTROL_WORD encodes outcomes, not conditions.

---

## 3. Control Word Partitioning

The control word is partitioned into categories of signals.

These categories reflect functional roles, not encoding structure.

---

### 3.1 Microarchitectural Control Signals

Control internal datapath behavior.

Defined in:
- [Microarchitectural Control Signals](20-control-output-definitions/01-microarchitectural-control-signals.md)

---

### 3.2 Architectural Control Signals

Control architecturally visible state updates.

Defined in:
- [Architectural Control Signals](20-control-output-definitions/02-architectural-control-signals.md)

---

### 3.3 Sequencing Control Signals

Control progression of execution.

Defined in:
- [Sequencing Control Signals](20-control-output-definitions/03-sequencing-control-signals.md)

---

## 4. Physical Implementation Considerations

The control word is physically implemented using ROM devices.

Typical ROM devices provide fixed-width outputs (commonly 8 bits per device).

---

### 4.1 Width Composition

A complete CONTROL_WORD may be assembled from multiple ROM devices operating in parallel.

Example:

```
ROM0 → bits [7:0]
ROM1 → bits [15:8]
ROM2 → bits [23:16]
...
```

Constraint:
- All ROM outputs together must form the complete CONTROL_WORD.
- All bits must be aligned and stable within the timing window.

---

### 4.2 Arbitrary Control Word Width

Constraint:
- CONTROL_WORD width is not required to be a multiple of 8 bits.
- The logical width is defined by control requirements, not device boundaries.

Implication:
- Unused bits in ROM devices are allowed.
- Partial device utilization is permitted.

---

### 4.3 Unused Bits

Constraint:
- Unused bits within CONTROL_WORD are permitted.
- Unused bits must not influence system behavior.

Constraint:
- Behavior must not depend on unspecified or uninitialized bits.

---

### 4.4 Extensibility

Constraint:
- CONTROL_WORD must be extensible.

Future expansion may require:
- additional control fields
- increased word width
- new signal categories

Example:
- adding Extended Arithmetic Element (EAE) control signals

Constraint:
- new fields must be added without altering existing control semantics.
- existing CONTROL_WORD encodings must remain valid unless explicitly revised.

---

### 4.5 Device Independence

Constraint:
- CONTROL_WORD structure must be independent of physical ROM organization.

Implication:
- logical field definition must not depend on:
  - device width
  - number of devices
  - specific hardware layout

---

## 5. Structural Requirements

### 5.1 Completeness

Constraint:
- CONTROL_WORD must include all signals required to:
  - fully define datapath behavior
  - fully define architectural state updates
  - fully define sequencing behavior

---

### 5.2 Explicitness

Constraint:
- All control effects must be explicitly encoded in CONTROL_WORD.
- No implicit behavior is permitted.

---

### 5.3 Non-Redundancy

Constraint:
- Signals within CONTROL_WORD must not be redundant.
- No duplicated control information is permitted.

---

### 5.4 Exclusivity

Constraint:
- Each control function must be represented by a single, well-defined signal or encoding.
- Overlapping control definitions are prohibited.

---

## 6. Control Signal Application

### 6.1 Signal Assertion

Each field in CONTROL_WORD directly drives control signals.

Constraint:
- CONTROL_WORD bits must directly correspond to control signals or encoded control fields.

---

### 6.2 Combinational Effect During TS

Constraint:
- CONTROL_WORD defines enables, selections, and operations during TS.
- Datapath behavior within TS must be combinational.

---

### 6.3 State Update at TP

Constraint:
- State updates occur only at TP.
- CONTROL_WORD must be stable before TP.

---

### 6.4 No Implicit Behavior

Constraint:
- No operation may occur without explicit CONTROL_WORD signals.

---

## 7. Control Signal Interpretation Model

Control signals are interpreted according to their functional role.

Control signals fall into three categories:

---

### 7.1 Enable Signals

Enable signals control whether an operation occurs.

Examples:
- register load signals
- memory and I/O controls

Behavior:
- inactive (0): no operation occurs
- active (1): operation occurs

Constraint:
- Operations must only occur when explicitly enabled.

---

### 7.2 Select Signals

Select signals define parameters of an operation.

Examples:
- DB_src
- AB_src
- ALU_op

Behavior:
- must always contain a valid encoding
- are interpreted only when associated operations are enabled

Constraint:
- Select signals must not use invalid or undefined encodings.
- If the associated operation is not enabled, select signals must have no effect on system behavior.

---

### 7.3 State-Output Signals

State-output signals define next-state values.

Examples:
- MS_NEXT
- RUN_NEXT
- HLT_REQ_NEXT

Behavior:
- must be explicitly defined for every CONTROL_WORD
- are applied unconditionally at the state update point (TP)

Constraint:
- No "noop" encoding is permitted.
- State must always update to the value specified by CONTROL_WORD, even if unchanged.

---

### 7.4 Interaction of Signal Types

Operations are defined by combinations of enable and select signals.

Model:

```
if ENABLE == 1:
    apply operation using SELECT parameters
else:
    no operation occurs
```

Constraint:
- Select signals must not cause effects unless the corresponding operation is enabled.

---

### 7.5 Inactive Behavior

Constraint:
- All control signals must be assigned a defined value in every CONTROL_WORD.
- Signals that are not active in a given cycle must:
  - be set to a valid encoding
  - have no effect on system behavior

---

### 7.6 Deterministic Interpretation

Constraint:
- Interpretation of CONTROL_WORD must be fully deterministic.
- No signal may have context-dependent or implicit meaning outside the rules defined above.

---

## 8. Sequencing Responsibility

Constraint:
- CONTROL_WORD must define all sequencing state outputs.
  - MS_NEXT
  - RUN_NEXT
  - HLT_REQ_NEXT
- Control flow must be determined entirely by CONTROL_WORD.

---

## 9. Isolation from Addressing

Constraint:
- CONTROL_WORD must not influence CTRL_ADDR formation.
- No feedback from CONTROL_WORD to control inputs is permitted.

---

## 10. Timing Relationship

Constraint:
- CONTROL_WORD must be stable during TS.
- CONTROL_WORD must be valid before TP.

---

## 11. External Arbitration and Signal Masking

External arbitration mechanisms (e.g., DMA) may override the physical application of control signals.

Constraint:
- CONTROL_WORD defines intended behavior for the current cycle.
- External mechanisms may suppress the physical effect of control signals without modifying CONTROL_WORD.

---

### 11.1 Bus Signal Masking

When external bus ownership is active:

Constraint:
- CPU-generated bus signals must be masked:
  - RD
  - WR
  - IOA
  - address bus drivers
  - data bus drivers

Constraint:
- Masking must force signals to an inactive or high-impedance state.

---

### 11.2 Non-Persistence of Control Signals

Constraint:
- CONTROL_WORD signals are cycle-local and must not persist across cycles.
- No control signal may be “restored” after suppression.

Constraint:
- After DMA or other arbitration, CONTROL_WORD must be recomputed and applied normally.

---

### 11.3 Separation of Intent and Effect

Constraint:
- CONTROL_WORD represents intent.
- Physical signals represent effect.

Constraint:
- External arbitration may suppress effect but must not alter control intent.

---

## 12. Design Principles

### 12.1 Outcome Encoding

Constraint:
- CONTROL_WORD encodes outcomes only.

---

### 12.2 Centralization

Constraint:
- All control behavior must originate from CONTROL_WORD.

---

### 12.3 Layer Separation

Constraint:
- CONTROL_WORD must not perform:
  - instruction decoding
  - condition evaluation
  - address formation

---

## 13. Summary

Definition:

```
CONTROL_WORD = ROM[CTRL_ADDR]
```

Execution model:

```
CONTROL_WORD → control signals → datapath evaluation (TS) → state update (TP)
```

Constraint:
- CONTROL_WORD must fully define system behavior with no implicit dependencies.