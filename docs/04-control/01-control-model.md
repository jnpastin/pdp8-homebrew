# Control Model

## Purpose

Defines the conceptual model of control in the system.

This document establishes:
- how control decisions are formed
- how processor state is represented for control purposes
- how inputs to the control system are defined

This document defines control inputs and conceptual behavior only.

For control address construction, see:
- [Control Addressing](../04-control/02-control-addressing.md)

For constraints and formal rules, see:
- [Control Constraints](../04-control/03-control-constraints.md)

For definitions of control input signals, see:
- [Derived Flags](../04-control/10-control-input-definitions/01-derived-flags.md)
- [IR Derived Fields](../04-control/10-control-input-definitions/02-ir-derived-fields.md)

---

## 1. Control as a Function

Control is defined as a deterministic function:

```
CONTROL = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

Where:

- MS: Major State  
- TS: Time State  
- IR_FIELDS: instruction-derived fields from IR  
- FLAGS: internal derived condition signals  
- EXT: external inputs  

This function selects a control word that determines system behavior.

---

## 2. Control Inputs

Control depends only on explicitly defined input domains.

### 2.1 Input Domains

Control inputs are partitioned into:

- execution state:
  - MS (Major State)
  - TS (Time State)

- instruction state:
  - IR (Instruction Register)
  - IR-derived fields (IR_FIELDS)

- derived conditions:
  - FLAGS

- external inputs:
  - EXT

Each domain is distinct and must not overlap in definition or implementation.

---

## 3. Control State

Control operates over two orthogonal state dimensions.

### 3.1 Major State (MS)

Defines the high-level execution phase.

Examples:
- FETCH
- DEFER
- EXECUTE
- INTERRUPT

Properties:
- persists across multiple TS
- changes only at defined transition points
- determines high-level control flow

---

### 3.2 Time State (TS)

Defines sequencing within a major state.

Properties:
- finite sequence per MS
- advances deterministically
- resets on MS transition
- defines the evaluation step within an instruction

---

## 4. Instruction Representation

Control does not operate directly on raw instruction encoding.

Instead, the Instruction Register (IR) is reduced to control-relevant fields.

---

### 4.1 Instruction Register (IR)

IR holds the current instruction.

Properties:
- loaded during instruction fetch
- stable for the duration of the instruction
- source for instruction-derived fields

---

### 4.2 IR-Derived Fields (IR_FIELDS)

IR is transformed via combinational logic:

```
IR → IR_FIELDS
```

IR_FIELDS retain only the information required for control decisions.

Examples:

- instruction class:
  - IS_MRI
  - IS_OPR
  - IS_IOT

- operation identification:
  - IS_ISZ
  - IS_AND

- control-relevant bits:
  - indirect bit

- OPR Group 1 examples:
  - CLA (clear accumulator)
  - CLL (clear link)
  - CMA (complement accumulator)

- OPR Group 2 examples:
  - SMA_enable (skip on minus accumulator)
  - SZA_enable (skip on zero accumulator)
  - SNL_enable (skip on non-zero link)

---

### 4.3 Properties of IR_FIELDS

IR_FIELDS:

- are derived combinationally from IR
- are stable for the duration of the instruction
- represent only control-relevant information
- must be reduced (not full IR)

---

### 4.4 Design Principle

Instruction information used by control must be expressed as:

```
control-relevant fields, not raw encoded state
```

---

## 5. Condition Representation (FLAGS)

FLAGS are internal, derived condition signals used as inputs to control.

They are not architecturally visible and do not correspond to a stored
flags register.

---

### 5.1 Definition

FLAGS are boolean predicates derived from register state.

They are:
- combinational
- not stored
- not architecturally observable

---

### 5.2 Properties

- Type: single-bit (per flag)
- Domain: control input
- Polarity: active-high
- Timing:
  - derived from state captured at TP
  - stable during TS
- Storage: none

---

### 5.3 Constraints

- must be derived only from stable register state
- must not depend on transient datapath signals
- must not be latched or stored
- must be minimal and non-redundant

---

### 5.4 Definition Source

Complete definitions of all FLAGS are provided in:

- [Derived Flags](../04-control/10-control-input-definitions/01-derived-flags.md)

---

## 6. External Inputs (EXT)

EXT represents signals originating outside the CPU.

Examples:
- interrupt request
- DMA request

Properties:
- originate outside the CPU
- influence control decisions
- must be stable before TP

Defined in:
- [External Inputs](../04-control/03-control-constraints.md#8-external-inputs-ext)

---

## 7. Control Structure

Control can be understood as three conceptual operations:

- input reduction
- address formation
- control selection

---

### 7.1 Conceptual Roles

- input reduction:
  - produces IR_FIELDS and FLAGS

- address formation:
  - combines MS, TS, IR_FIELDS, FLAGS, EXT into CTRL_ADDR

- control selection:
  - maps CTRL_ADDR to a control word

---

### 7.2 Implementation Model

These roles are conceptual only.

In implementation:

- all logic is combinational
- signals propagate continuously during TS
- no staged sequencing exists between components

Behavior:

```
IR → IR_FIELDS
Registers → FLAGS
(MS, TS, IR_FIELDS, FLAGS, EXT) → CTRL_ADDR
CTRL_ADDR → CONTROL_WORD
```

---

### 7.3 Timing Model

- At TP(n-1):
  - state is latched

- During TS(n):
  - all combinational logic evaluates

- By TP(n):
  - CONTROL_WORD must be stable

- At TP(n):
  - all state updates occur simultaneously

---

## 8. Persistence of Information

Control state does not persist across TS.

Required information persists via:

- IR
- MS
- architectural registers

IR_FIELDS and FLAGS remain stable because their sources are stable.

---

## 9. Design Principles

### 9.1 Decision-Based Representation

Control inputs represent decisions, not full state.

---

### 9.2 Minimality

Only information required to determine control behavior is included.

---

### 9.3 Separation of Concerns

- IR decoding determines instruction properties
- FLAGS represent conditions
- control selects behavior based on reduced inputs

---

### 9.4 Determinism

Each input combination produces exactly one control outcome.

---

## 10. Summary

Control is a mapping from reduced machine state to control behavior.

Key transformations:

```
IR → IR_FIELDS
Registers → FLAGS
(MS, TS, IR_FIELDS, FLAGS, EXT) → control selection
```

This model provides:

- deterministic behavior
- minimal encoding
- clear separation between state, decisions, and execution