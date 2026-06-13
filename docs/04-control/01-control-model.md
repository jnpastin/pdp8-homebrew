# Control Model

## Purpose

Defines the conceptual model of control in the system.

This document establishes:
- how control decisions are formed
- how control is implemented using a control store
- how instruction and processor state are represented for control purposes

This document is descriptive and architectural.

Formal rules and requirements are defined in:  
[Control Constraints](../04-control/03-control-constraints.md)

---

## 1. Control as a Function

Control is defined as a deterministic function:

CONTROL = f(MS, TS, INST, FLAGS, EXT)

Where:

- MS: Major State
- TS: Time State
- INST: instruction-derived signals
- FLAGS: derived condition signals
- EXT: external inputs

This function produces the complete control word.

---

## 2. ROM-Based Implementation

Control is implemented using a control store:

```
CONTROL_WORD = ROM[CTRL_ADDR]
```

Where:

```
CTRL_ADDR = PACK(MS, TS, INST, FLAGS, EXT)
```

The ROM output defines:
- all architectural control signals
- all microarchitectural control signals
- MS_next (next major state)

No additional decoding or interpretation occurs after the control store.

Further details:  
[Control Store Design](../04-control/02-control-store.md)

---

## 3. Control State

Control operates over two orthogonal state dimensions.

---

### 3.1 Major State (MS)

Defines the high-level execution phase.

Examples include:
- FETCH
- DEFER
- EXECUTE
- INTERRUPT

Properties:
- persists across multiple TS
- changes only at defined transition points

---

### 3.2 Time State (TS)

Defines sequencing within a major state.

Properties:
- finite sequence per MS
- advances deterministically
- resets on MS transition

---

## 4. Instruction Representation (INST)

Control does not operate on raw instruction fields directly.

Instead, the instruction register (IR) is transformed into a set of
instruction-derived signals (INST).

---

### 4.1 Instruction Predecode

Instruction predecode is a combinational transformation:

```
IR → INST
```

INST signals represent only the control-relevant properties of the instruction.

Examples:

- instruction class:
  - IS_MRI
  - IS_OPR
  - IS_IOT

- operation identification:
  - IS_ISZ
  - IS_AND

- condition enables:
  - SPA_enable
  - SNA_enable

---

### 4.2 Properties of INST Signals

INST signals:

- are derived combinationally from IR
- are stable for the duration of the instruction
- represent minimal, control-relevant information

They replace the need to include opcode or full IR in CTRL_ADDR.

---

### 4.3 Design Principle

Instruction information used by control must be expressed as:

> control-relevant predicates, not raw encoded state

---

## 5. Condition Representation (FLAGS)

FLAGS consists of derived predicates based on processor state.

These are not raw register values.

They influence control selection but do not directly drive the datapath.

---

### 5.1 Definition

FLAGS are boolean predicates derived from processor state.

They are evaluated combinationally and do not represent stored state.

---

### 5.2 Properties

- Type: single-bit (per flag)
- Domain: control input (not control output)
- Polarity: active-high (true when condition holds)
- Timing:
  - derived from state captured at TP
  - stable during TS
- Storage:
  - none (purely combinational)
- Usage:
  - consumed by control during CTRL_ADDR formation

---

### 5.3 Constraints

- FLAGS must be derived only from stable register state
- FLAGS must not depend on transient datapath signals
- FLAGS must not be stored or latched
- FLAGS must be minimal and non-redundant

---

### 5.4 Usage

FLAGS contribute to control address formation:

- [Control Store](../04-control/02-control-store.md)

---

### 5.5 Scope

FLAGS are not:

- control signals  
- datapath signals  
- part of the control word  

They are inputs to control selection only.

---

### 5.6 Design Principle

Control decisions are based on:

> reduced condition signals, not full register contents

---

### 5.7 Defined FLAGS

#### AC_zero

Description:
True when the accumulator is zero.

Expression:
AC == 0

Source:
AC register

---

#### AC_negative

Description:
True when the accumulator is negative.

Expression:
AC[MSB] == 1

Source:
AC register

---

#### L_zero

Description:
True when the Link register is zero.

Expression:
L == 0

Source:
L register

---

#### L_set

Description:
True when the Link register is one.

Expression:
L == 1

Source:
L register

---

#### MB_zero

Description:
True when the Memory Buffer is zero.

Expression:
MB == 0

Source:
MB register

---

## 6. External Inputs (EXT)

EXT represents signals external to the CPU.

Examples:
- interrupt request
- DMA request

Properties:
- originate outside the CPU
- influence control decisions
- must be stable prior to TP

Defined in:  
[Control Constraints](../04-control/03-control-constraints.md#8-external-inputs-ext)

---

## 7. Control Structure

For reasoning purposes, control can be viewed as three conceptual components:

1. Predecode and Reduction  
2. Address Generation  
3. Control Store  

---

### 7.1 Conceptual Roles

- Predecode and Reduction  
  - produces INST and FLAGS signals

- Address Generation  
  - combines MS, TS, INST, FLAGS, EXT into CTRL_ADDR

- Control Store  
  - maps CTRL_ADDR to CONTROL_WORD

---

### 7.2 Implementation Note

This partitioning is conceptual only.

In the actual system:

- all components operate concurrently as combinational logic
- there is no sequential staging between them
- signals propagate continuously during TS

The system behaves as a single combinational network:

```
IR → INST
Registers → FLAGS
(MDB_input, DB_input) → datapath sources
(MS, TS, INST, FLAGS, EXT) → CTRL_ADDR
CTRL_ADDR → ROM → CONTROL_WORD
```

---

### 7.3 Timing Model

- At TPₙ₋₁:
  - state is latched

- During TSₙ:
  - all combinational logic evaluates continuously

- By TPₙ:
  - CONTROL_WORD must be stable

- At TPₙ:
  - all state updates occur simultaneously

Correct operation requires that all propagation delays are bounded such that:

> CONTROL_WORD is stable before TP

---

## 8. Persistence of Information

Control state does not persist across TS.

However, required information persists via:

- IR (instruction register)
- MS (major state register)
- architectural registers

INST and FLAGS signals remain stable because their source values are stable.

No additional latching is required for instruction decode.

---

## 9. Design Principles

The control model follows these principles.

---

### 9.1 Decision-Based Encoding

CTRL_ADDR encodes:

- control-relevant decisions

Not:

- full processor state

---

### 9.2 Minimality

Only include information required to determine control outputs.

---

### 9.3 Separation of Concerns

- decode determines instruction properties
- control store determines system behavior

---

### 9.4 Determinism

Each input combination produces exactly one control word.

---

## 10. Summary

Control is implemented as a ROM-based mapping from reduced processor state to a complete control word.

Key transformations:

```
IR → INST
Registers → FLAGS
(MS, TS, INST, FLAGS, EXT) → CTRL_ADDR
CTRL_ADDR → CONTROL_WORD
```

This structure provides:
- compact address encoding
- efficient hardware implementation
- clear separation between decision logic and execution