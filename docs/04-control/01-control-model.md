# Control Model

## 1. Purpose

Defines the conceptual model of control in the system.

This document establishes:
- how control decisions are formed
- how processor state is represented for control purposes
- how inputs to the control system are defined

This document defines control inputs and conceptual behavior only.

For control address construction, see:
- [Control Addressing](./02-control-addressing.md)

For constraints and formal rules, see:
- [Control Constraints](./03-control-constraints.md)

For definitions of control input signals, see:
- [Primitive Flags](./10-control-input-definitions/01-flags.md)
- [IR Derived Fields](./10-control-input-definitions/02-ir-derived-fields.md)
- [Derived Flags](./10-control-input-definitions/03-derived-flags.md)
- [External Inputs](./10-control-input-definitions/04-external-inputs.md)

---

## 2. Control as a Function

Control is defined as a deterministic function:

```
CONTROL = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

Where:

- MS: Major State  
- TS: Timing State  
- IR_FIELDS: instruction-derived fields from IR  
- FLAGS: internal derived condition signals  
- EXT: external inputs  

This function selects a control word that determines system behavior.

---

## 3. Control Inputs

Control depends only on explicitly defined input domains.

### 3.1 Input Domains

Control inputs are partitioned into:

- execution state:
  - MS (Major State)
  - TS (Timing State)

- instruction state:
  - IR (Instruction Register)
  - IR-derived fields (IR_FIELDS)

- derived conditions:
  - FLAGS

- external inputs:
  - EXT

Each domain is distinct and must not overlap in definition or implementation.

---

## 4. Control State

Control operates over two orthogonal state dimensions.

### 4.1 Major State (MS)

Defines the high-level execution phase.

Examples:
- FETCH
- DEFER
- EXECUTE
- INTERRUPT
- DMA

Properties:
- persists across multiple TS
- changes only at defined transition points
- determines high-level control flow

---

### 4.2 Timing State (TS)

Defines sequencing within a major state.

Properties:
- finite sequence per MS
- advances deterministically
- resets on MS transition
- defines the evaluation step within an instruction

---

## 5. Instruction Representation

Control does not operate directly on raw instruction encoding.

Instead, the Instruction Register (IR) is reduced to control-relevant fields.

---

### 5.1 Instruction Register (IR)

IR holds the current instruction.

Properties:
- loaded during instruction fetch, at FETCH TP2
- stable from then until the next instruction's FETCH TP2
- source for instruction-derived fields

---

### 5.2 IR-Derived Fields (IR_FIELDS)

IR is transformed via combinational logic:

```
IR → IR_FIELDS
```

IR_FIELDS retain only the information required for control decisions.

Examples:

- instruction class:
  - IR_IS_MRI
  - IR_IS_OPR
  - IR_IS_IOT

- operation identification:
  - IR_MRI_OPCODE (which memory reference instruction)
  - IR_IS_EXTERNAL_IOT

- control-relevant bits:
  - indirect bit

- OPR Group 1 examples:
  - IR_OPR_CLA (clear accumulator)
  - IR_OPR_CLL (clear link)
  - IR_OPR_CMA (complement accumulator)

- OPR Group 2 examples:
  - IR_OPR_SMA (skip on minus accumulator)
  - IR_OPR_SZA (skip on zero accumulator)
  - IR_OPR_SNL (skip on non-zero link)

---

### 5.3 Properties of IR_FIELDS

IR_FIELDS:

- are derived combinationally from IR
- are stable for the duration of the instruction
- represent only control-relevant information
- must be reduced (not full IR)

---

### 5.4 Design Principle

Instruction information used by control must be expressed as:

```
control-relevant fields, not raw encoded state
```

---

## 6. Condition Representation (FLAGS)

FLAGS are internal, derived condition signals used as inputs to control.

They are not architecturally visible and do not correspond to a stored
flags register.

---

### 6.1 Definition

FLAGS are boolean predicates derived from register state.

They are:
- not stored
- not architecturally observable

A FLAG may be either:

- a direct reflection of a one-bit state register
- a combinational predicate derived from one or more registers

FLAGS do not imply the existence of a stored aggregate flags register.

---

### 6.2 Properties

- Type: single-bit (per flag)
- Domain: control input
- Polarity: active-high
- Timing:
  - derived from state captured at TP
  - stable during TS
- Storage: none

---

### 6.3 Constraints

- must be derived only from stable register state
- must not depend on transient datapath signals
- must not be latched or stored
- must be minimal and non-redundant

---

### 6.4 Definition Source

Complete definitions of all FLAGS are provided in:

- [Primitive Flags](./10-control-input-definitions/01-flags.md)
- [Derived Flags](./10-control-input-definitions/03-derived-flags.md)

---

## 7. External Inputs (EXT)

EXT represents signals originating outside the CPU.

Examples:
- Front panel request
- Interrupt request
- DMA request

Properties:
- originate outside the CPU
- influence control decisions
- must be stable before TP

Defined in:
- [External Inputs](./10-control-input-definitions/04-external-inputs.md)

---

## 8. Control Structure

Control can be understood as three conceptual operations:

- input reduction
- address formation
- control selection

---

### 8.1 Conceptual Roles

- input reduction:
  - produces IR_FIELDS and FLAGS

- address formation:
  - combines MS, TS, IR_FIELDS, FLAGS, EXT into CTRL_ADDR

- control selection:
  - maps CTRL_ADDR to a control word

---

### 8.2 Implementation Model

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

### 8.3 Timing Model

- At TP(n-1):
  - state is latched

- During TS(n):
  - all combinational logic evaluates

- By TP(n):
  - CONTROL_WORD must be stable

- At TP(n):
  - all state updates occur simultaneously

### 8.4 Realizations Outside the Control Word

Some control is realized outside the control store, as gates, registers, or a small ROM. Each entry below is permitted, and the general rules that forbid decisions, IR bits, or stored state outside the control store do not apply to it.

| Realization | What it is | Defined in |
|---|---|---|
| Predecode gates | `IR_CLASS`, `IR_INDIRECT`, `IR_NO_EXECUTE`, and `IR_OPR_HLT`, from IR | [IR-Derived Fields](./10-control-input-definitions/02-ir-derived-fields.md) |
| OPR pass unit | IR bits used directly as datapath stage selects, qualified by `IR_CLASS` | [OPR Execution](../03-microarchitecture/07-opr/README.md) |
| Registered control state | `MAPR`, `MS_EFF_IS_EXECUTE`, and `SKIP` | [Control Store Organization §5](./08-control-store-organization.md), [Registers](../01-architecture/01-registers.md) |
| RUN-selected overlays | `SEQ_OVL`, and the state group forced while halted | [Control Store Organization §5.6 and §6](./08-control-store-organization.md) |
| Decoded outputs | `/DMA_GRANT`, `IOT_ACTIVE`, `/DB_READ`, `/DB_WRITE`, `/INITIALIZE`, and `INSTR_END` | [Architectural Control Signals](./20-control-output-definitions/02-architectural-control-signals.md) |
| Timing ROM | the length of each TS and the width of its TP | [Timing Terminology §3.5](../09-timing/01-terminology.md#35-timing-rom) |

Each realization:

- is a function only of state committed by the previous TP, or of a static jumper
- is specified in its own definition
- makes no decision that the control store also makes
- is verified by the control-store packer wherever it affects the control word ([Control Store Organization §9](./08-control-store-organization.md#9-verification))

---

## 9. Persistence of Information

Control state does not persist across TS.

Required information persists via:

- IR
- MS
- architectural registers
- the registered control state `SKIP` and `MAPR` ([Control Model §8.4](#84-realizations-outside-the-control-word))

IR_FIELDS and FLAGS remain stable because their sources are stable.

---

## 10. Design Principles

### 10.1 Decision-Based Representation

Control inputs represent decisions, not full state.

---

### 10.2 Minimality

Only information required to determine control behavior is included.

---

### 10.3 Separation of Concerns

- IR decoding determines instruction properties
- FLAGS represent conditions
- control selects behavior based on reduced inputs

---

### 10.4 Determinism

Each input combination produces exactly one control outcome.

---

## 11. Summary

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