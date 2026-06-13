# Control Store Design

## Purpose

Defines how control behavior is implemented using a ROM-based control store.

This document specifies:
- how the control store address is constructed
- how inputs are reduced and encoded
- how the control word is structured

This document does not define:
- control signal semantics (see [Control Constraints](../04-control/03-control-constraints.md))
- micro-operations (see [Micro-Operations](../03-microarchitecture/02-micro-operations.md))

---

## 1. Control Store Model

Control is implemented as a ROM lookup:

CONTROL_WORD = ROM[CTRL_ADDR]

Where:
- CTRL_ADDR is a reduced encoding of processor state
- CONTROL_WORD is the complete set of control outputs

---

## 2. Control Word

### Definition

The ROM output defines the full control word.

It must include:
- all architectural control signals
- all microarchitectural control signals
- MS_next (next major state)

No additional decoding or interpretation is permitted after ROM output.

---

### Width

Control word width is equal to the number of control signals.

Properties:
- width is not constrained to multiples of 8
- unused bits are permitted

---

### Physical Implementation

The control word is implemented using multiple ROM devices in parallel.

Example:
- required width: 36 bits  
- implementation: 5 × 8-bit EEPROMs (40 bits total)

All devices share:
- identical address lines (CTRL_ADDR)
- independent output bit groups

---

## 3. Control Store Address

### Definition

CTRL_ADDR is derived from a reduced encoding of:

(MS, TS, IR, FLAGS, EXT)

The address must uniquely identify control behavior.

---

## 3A. Control Address Definition

### Conceptual Form

CTRL_ADDR = PACK(
    MS,
    TS,
    INST_FIELDS,
    COND_FIELDS,
    EXT_FIELDS
)

Where:

- MS defines the current major state
- TS defines the current time state
- INST_FIELDS are instruction-derived fields
- COND_FIELDS are derived decision conditions
- EXT_FIELDS are external inputs

---

### MS (Major State)

Encodes the current execution phase.

Properties:
- always included
- determines high-level control flow

Defined in:  
[Control Model](../04-control/01-control-model.md)

---

### TS (Time State)

Encodes the intra-state step.

Properties:
- always included
- defines sequencing within MS

Defined in:  
[Control Model](../04-control/01-control-model.md)

---

### INST_FIELDS (Instruction-Derived Fields)

Encodes only the portions of IR that affect control behavior.

Requirements:
- full IR must not be included
- only control-relevant subsets allowed

Examples:
- opcode
- indirect bit
- selected OPR bits

Constraint:
- inclusion is context-dependent

Related:  
[Control Constraints](../04-control/03-control-constraints.md#9-control-store-address-constraints)

---

### COND_FIELDS (Derived Conditions)

Encodes evaluated predicates, not raw register values.

Examples:
- AC == 0
- AC negative
- LINK == 0

Rules:
- include only conditions that influence control
- do not include full register contents
- may encode multiple conditions into compact fields

Key principle:

> CTRL_ADDR encodes decisions, not state

Related:  
[Control Constraints](../04-control/03-control-constraints.md#9-control-store-address-constraints)

---

### EXT_FIELDS (External Inputs)

Encodes signals external to the CPU.

Examples:
- interrupt pending
- DMA request pending

Properties:
- must be stable before TP
- must not include internal signals

Defined in:  
[Control Constraints](../04-control/03-control-constraints.md#8-external-inputs-ext)

---

## 4. Address Construction Rules

### Inclusion Rule

A field may be included in CTRL_ADDR only if:
- it affects control output

---

### Exclusion Rule

A field must not be included if:
- it does not affect control behavior in the current context

Unused combinations are handled by:
- duplicating ROM entries

---

### Reduction Requirement

Inputs must be reduced prior to inclusion:

| Source | Requirement |
|--------|------------|
| IR     | include only required bits |
| FLAGS  | convert to predicates |
| EXT    | include only decision-relevant signals |

---

## 5. Context Sensitivity

Field usage varies by execution context.

Examples:

### FETCH
- INST_FIELDS excluded
- COND_FIELDS excluded

### DEFER
- include indirect bit
- may include address classification

### EXECUTE
- include opcode or instruction class
- include required conditions

Implication:
- multiple CTRL_ADDR values may map to identical CONTROL_WORD outputs

---

## 6. Sparse Encoding

### Principle

The control store may contain redundant entries.

Purpose:
- reduce predecode complexity
- simplify address generation

Example:
- FETCH ignores IR  
→ all IR values map to identical control words

---

## 7. Predecode

Predecode logic will be used to reduce address width.

Examples:
- instruction class decode
- OPR group identification
- address classification

Properties:
- combinational logic
- feeds CTRL_ADDR inputs

Constraint:
- must preserve determinism and stability

---

## 8. MS_next Encoding

MS_next is part of CONTROL_WORD.

Properties:
- determined during TS4
- committed at TP4

Constraint:
- MS may only change through this mechanism

See:  
[Control Constraints](../04-control/03-control-constraints.md)

---

## 9. Determinism Guarantee

The mapping:

CTRL_ADDR → CONTROL_WORD

must satisfy:

- each valid execution state maps to exactly one control word
- identical behaviors may share entries
- conflicting outputs are not permitted

---

## 10. Implementation Summary

The control system consists of:

1. Input signals  
   - MS, TS, reduced IR, COND_FIELDS, EXT

2. Address generation logic  
   - reduces inputs to CTRL_ADDR

3. Control store (ROM)  
   - addressed by CTRL_ADDR

4. Output  
   - complete control word drives system

No additional control interpretation is permitted after ROM.

---

## Related Documents

- [Control Model](../04-control/01-control-model.md)  
- [Control Constraints](../04-control/03-control-constraints.md)  
- [Micro-Operations](../03-microarchitecture/02-micro-operations.md)
