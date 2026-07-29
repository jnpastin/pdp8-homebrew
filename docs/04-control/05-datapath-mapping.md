# Datapath Mapping

## Purpose

Defines how CONTROL_WORD produces datapath and system behavior.

This document establishes:
- how control signals affect datapath elements
- how combinations of signals produce operations
- how correctness and completeness are validated

This document does not define signals or control logic.

Signal definitions are provided in:
- [Microarchitectural Control Signals](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Architectural Control Signals](../04-control/20-control-output-definitions/02-architectural-control-signals.md)
- [Sequencing Control Signals](../04-control/20-control-output-definitions/03-sequencing-control-signals.md)

Control behavior is defined in:
- [Control Word](04-control-word.md)

Constraints are defined in:
- [Control Constraints](03-control-constraints.md)

---

## 1. Mapping Definition

System behavior is derived from CONTROL_WORD:

```
CONTROL_WORD → control signals → (external masking) → datapath behavior → state update
```

Constraint:
- Every control signal must produce a defined effect on the system.

The system includes:
- datapath behavior
- architectural state changes
- sequencing behavior

---

## 2. Control-Centric Execution Model

Each CONTROL_WORD defines a complete set of signals.

Behavior is determined by:

- which signals are active
- how signals interact

Constraint:
- CONTROL_WORD must fully determine system behavior for the cycle.
- No implicit or external behavior is permitted.

---

## 3. Signal Role Application

Control signals are interpreted according to their roles as defined in:
- [Control Word](04-control-word.md)

---

### 3.1 Enable Signals

Constraint:
- Operations occur only when enable signals are asserted.

If an enable signal is inactive:
- no operation occurs
- associated select signals have no effect

---

### 3.2 Select Signals

Constraint:
- Select signals must always have valid encodings.
- Select signals are only meaningful when associated operations are enabled.

Constraint:
- Select signals must not produce behavior without an active consumer.

---

### 3.3 State-Output Signals

Constraint:
- State-output signals (e.g., MS_NEXT, RUN_NEXT, HLT_REQ_NEXT) are always applied.
- No conditional or suppressed updates are permitted.

---

## 4. Datapath Interaction

Datapath behavior is produced by interactions of signals.

Examples of interactions:

- register update:
  - enable: register load
  - select: data source (DB_src)

- ALU operation:
  - select: ALU_op
  - inputs: operand selection
  - result consumed by register load

- memory operation:
  - enable: RD / WR
  - address source: AB_src
  - data source: DB_src

Constraint:
- All interactions must be fully defined by CONTROL_WORD.
- No implicit data movement is permitted.

---

## 5. Conditional Relevance

Not all signals are relevant in all cycles.

Constraint:
- All signals must be defined in CONTROL_WORD.
- Signals that are not enabled or not consumed in a given cycle must have no effect.

Constraint:
- Irrelevant signals must not influence system behavior.

---

## 6. Timing Behavior

Defined in:
- [Control Model](01-control-model.md)

Behavior:

- during TS:
  - CONTROL_WORD is applied
  - datapath evaluates combinationally

- at TP:
  - state updates occur

Constraint:
- All datapath results must be determined before TP.
- All state updates must occur only at TP.

---

## 7. Completeness Validation

### 7.1 Signal Definition

Constraint:
- Every control signal must have a defined semantic effect.

---

### 7.2 Control Word Coverage

Constraint:
- Every CONTROL_WORD must define all control fields.

Constraint:
- No field may be left undefined.

---

### 7.3 Behavior Completeness

Constraint:
- All required datapath operations must be realizable via CONTROL_WORD.

Constraint:
- No operation may rely on implicit behavior.

---

## 8. Non-Redundancy

Constraint:
- No control signal may exist without a defined purpose.

Constraint:
- No two signals may produce identical effects unless explicitly intended.

---

## 9. Verification Model

Verification proceeds per CONTROL_WORD:

1. Identify asserted enable signals  
2. Identify relevant select signals  
3. Determine resulting datapath interactions  
4. Confirm resulting state updates  

Constraint:
- This process must be deterministic and complete.

---

## 10. Design Principles

### 10.1 Explicit Behavior

All behavior must be explicitly driven by control signals.

---

### 10.2 No Implicit Data Movement

Constraint:
- Data movement must occur only when explicitly enabled.

---

### 10.3 Separation from Control Logic

Constraint:
- Datapath mapping must not introduce new control decisions.
- All decisions must originate from CONTROL_WORD.

---

## 11. External Bus Arbitration (DMA)

External arbitration mechanisms may temporarily override CPU control of shared resources.

---

### 11.1 Bus Ownership

Constraint:
- At any time, exactly one agent may drive shared buses.

Constraint:
- When DMA is active:
  - CPU must not drive address bus
  - CPU must not drive data bus
  - CPU must not assert RD, WR, or IOA

---

### 11.2 Signal Masking

Constraint:
- CPU bus signals must be gated as:

```
CPU_signal = CONTROL_signal AND NOT DMA_HOLD
```

Constraint:
- Masking must not alter CONTROL_WORD interpretation.

---

### 11.3 Execution Suspension

Constraint:
- DMA must suspend datapath progression by:
  - inhibiting register writes
  - inhibiting MS, RUN, HLT_REQ updates
  - inhibiting TS advancement

Constraint:
- No datapath state may change while DMA is active.

---

### 11.4 Resumption

Constraint:
- After DMA completes, execution resumes with:
  - unchanged MS
  - unchanged TS
  - recomputed CONTROL_WORD

Constraint:
- No control signals are restored from prior cycles.

---

## 12. Summary

Datapath mapping defines how control signals are realized.

Core transformation:

```
CONTROL_WORD → signals → datapath → state update
```

Constraint:
- This mapping must be complete, explicit, and deterministic.
``