# Control Addressing

## 1. Purpose

Defines the formation of the control address (CTRL_ADDR) used to access the control store.

This document establishes:
- how control inputs are combined into CTRL_ADDR
- what information is permitted in the control address
- structural and encoding constraints governing address formation

This document defines structure and constraints only.

For the control model, see:
- [Control Model](./01-control-model.md)

For constraints and formal rules, see:
- [Control Constraints](./03-control-constraints.md)

---

## 2. Control Address Definition

The control system is implemented as a mapping:

```
CONTROL_WORD = ROM[CTRL_ADDR]
```

Where:

- CTRL_ADDR is the control address
- CONTROL_WORD is the complete control output for a cycle

CTRL_ADDR fully determines the control word.

Constraint:
- Every control decision must be encoded in CTRL_ADDR.
- No additional decoding or interpretation is permitted after ROM lookup.

---

## 3. Control Address Function

CTRL_ADDR is defined as a deterministic function:

```
CTRL_ADDR = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

Where:

- MS: Major State
- TS: Timing State
- IR_FIELDS: instruction-derived fields
- FLAGS: derived condition signals
- EXT: external inputs

Constraint:
- CTRL_ADDR must depend only on these inputs.
- No other signals may influence control address formation.

---

### 3.1 Predecode and Input Reduction

Control inputs must be reduced before address formation.

The reduction process is:

```
IR → IR_FIELDS
Registers → FLAGS
```

Where:

- IR_FIELDS represent instruction-decoding results
- FLAGS represent derived condition predicates

This stage is commonly referred to as **predecode**.

Properties:
- purely combinational
- operates only on IR or stable register state
- produces control-relevant signals

Constraint:
- Predecode must not depend on TS or MS.
- Predecode must not encode control behavior.
- Predecode must not include timing or sequencing semantics.

Constraint:
- All instruction-dependent information used in CTRL_ADDR must be expressed through IR_FIELDS.
- All condition-dependent behavior must be expressed through FLAGS.

---

### 3.2 Control Decisions as Address Selection

Control logic is conceptually described using conditional statements, but is implemented as address selection.

Example conceptual form:

```
if (TS == 4 and IR_FIELDS.indirect == 1)
    MS_next = DEFER
endif
```

This is not implemented as runtime conditional logic.

Instead:

```
(MS, TS=4, IR_FIELDS.indirect=1, FLAGS, EXT)
→ CTRL_ADDR
→ CONTROL_WORD { MS_next = DEFER, ... }
```

Interpretation:

- conditions (TS, IR_FIELDS, FLAGS, EXT)  
  → determine CTRL_ADDR  

- CTRL_ADDR  
  → selects a precomputed CONTROL_WORD  

- CONTROL_WORD  
  → defines outcomes (e.g., MS_next, control signals)

Constraint:
- All conditional behavior must be represented through CTRL_ADDR selection.
- No control decisions may be computed outside the control store.

---

### 3.3 Role Separation

The control process is strictly divided:

- inputs define the condition space:
  - MS, TS, IR_FIELDS, FLAGS, EXT

- CTRL_ADDR selects the case

- CONTROL_WORD defines:
  - control signals
  - sequencing decisions (including MS_next)

Constraint:
- CTRL_ADDR encodes which decision applies.
- CONTROL_WORD encodes the result of that decision.

---

### 3.4 Valid and Invalid Conditions

Valid example:

```
if (TS == 3 and FLAGS.AC_zero == 1)
```

Because:
- TS is a valid input domain
- FLAGS is a valid reduced domain

Invalid example:

```
if (AC == 0)
```

Because:
- raw register state is not permitted
- must first be reduced:

```
AC → FLAGS.AC_zero
```

Constraint:
- All conditions must be expressed only in terms of MS, TS, IR_FIELDS, FLAGS, EXT.

---

## 4. Address Composition

CTRL_ADDR is formed by combining contributions from each input domain.

Formally:

```
CTRL_ADDR = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

For implementation purposes, this function may be expressed as an encoding operation:

```
CTRL_ADDR = PACK(MS, TS, IR_FIELDS, FLAGS, EXT)
```

Where:

- PACK is the structural encoding realization of the control function f
- PACK defines how input domains are mapped into an address representation suitable for ROM indexing

Constraint:
- PACK is not a separate transformation stage.
- PACK ≡ f and must produce identical results for all input combinations.

---

### 4.1 Properties of PACK

PACK represents a deterministic encoding of control inputs.

Properties:
- encodes all input domains into CTRL_ADDR
- produces a unique address for each distinct control decision
- is consistent across all system states

Constraint:
- PACK must encode control-relevant decisions only.
- PACK must not encode full machine state.

---

### 4.2 Separation from Input Reduction

PACK operates only on already-reduced inputs.

Upstream transformations:

```
IR → IR_FIELDS
Registers → FLAGS
```

PACK operates strictly after these reductions:

```
(MS, TS, IR_FIELDS, FLAGS, EXT) → CTRL_ADDR
```

Constraint:
- PACK must not perform instruction decoding.
- PACK must not evaluate conditions.
- PACK must not derive new signals.

---

### 4.3 Prohibited Behavior

PACK must not introduce or replicate control logic.

The following are prohibited within PACK:

- decoding raw IR bits
- evaluating register values
- generating FLAGS internally
- interpreting datapath signals
- introducing new conditional logic

Constraint:
- All control decisions must be fully resolved in the input domains prior to PACK.

---

### 4.4 Encoding Nature

PACK is an encoding mechanism, not a decision mechanism.

Interpretation:

- input domains define the condition space
- PACK encodes that condition space into an address
- CONTROL_WORD encodes the result of that condition

Relationship:

```
decision inputs → PACK → CTRL_ADDR → CONTROL_WORD → outcomes
```

Constraint:
- PACK must not encode outcomes.
- All outcomes (including sequencing decisions such as MS_next) must exist only in CONTROL_WORD.

---

## 5. Input Contributions

Each input domain contributes to CTRL_ADDR in a strictly defined manner.

---

### 5.1 Major State Contribution (MS)

MS selects the high-level execution phase.

Properties:
- partitions control space into major operational regions
- defines the primary control context

Constraint:
- MS must not encode datapath or register state.

---

### 5.2 Timing State Contribution (TS)

TS defines sequencing within a major state.

Properties:
- selects the step within a control sequence
- determines progression through micro-operations

Constraint:
- TS must encode position only, not behavior.

---

### 5.3 Instruction-Derived Contribution (IR_FIELDS)

IR_FIELDS contribute instruction-dependent control decisions.

Properties:
- derived exclusively from IR
- represent decoded instruction properties
- stable for the duration of an instruction

Constraint:
- Only IR_FIELDS may carry instruction-dependent information into CTRL_ADDR.
- Raw IR bits must not be included in CTRL_ADDR.
- IR_FIELDS must represent decisions, not encoded instruction state.

For definitions, see:
- [IR Derived Field Definitions](10-control-input-definitions/02-ir-derived-fields.md)

---

### 5.4 Condition Contribution (FLAGS)

FLAGS provide conditional control inputs.

Properties:
- derived from stable register state
- represent boolean predicates
- evaluated combinationally

Constraint:
- FLAGS must not depend on transient datapath signals.
- Only FLAGS may represent conditional state in CTRL_ADDR.

For definitions, see:
- [Primitive Flag Definitions](10-control-input-definitions/01-flags.md)
- [Derived Flag Definitions](10-control-input-definitions/03-derived-flags.md)

---

### 5.5 External Input Contribution (EXT)

EXT provides external control influences.

Properties:
- originate outside the CPU
- may affect control flow

Constraint:
- EXT must be stable during control evaluation.
- EXT must not introduce non-determinism.

---

## 6. Encoding Constraints

CTRL_ADDR encoding must satisfy the following constraints.

---

### 6.1 Decision-Based Encoding

CTRL_ADDR encodes control decisions, not full system state.

Constraint:
- Only information required to select a control word may be encoded.
- Redundant or unused information must not be included.

---

### 6.2 Prohibited Information

The following must not be encoded in CTRL_ADDR:

- raw IR contents
- full instruction encoding
- register values
- datapath signals
- transient combinational outputs

Constraint:
- All information must be reduced to IR_FIELDS, FLAGS, MS, TS, or EXT.

---

### 6.3 Domain Separation

Each input domain must remain independent.

Constraint:
- No domain may implicitly encode another.
- Address encoding must not merge unrelated domains.

---

### 6.4 Determinism

CTRL_ADDR must be a strictly deterministic function.

Constraint:
- identical inputs must always produce identical CTRL_ADDR values.
- no implicit conditions or hidden dependencies are allowed.

---

## 7. Structural Properties

### 7.1 Completeness

All valid input combinations must map to a defined control word.

Constraint:
- no reachable address may be undefined.

---

### 7.2 Sparsity

Unused addresses are permitted.

Properties:
- not all address combinations must be used
- unused combinations must not affect correctness

---

### 7.3 Non-Aliasing

Different control decisions must not collide unless explicitly intended.

Constraint:
- distinct control behaviors must map to distinct addresses.

---

## 8. Address Space Evolution

This section defines how CTRL_ADDR must evolve when the control system is extended.

---

### 8.1 Output Extension Without Address Change

New control signals may be added without modifying CTRL_ADDR when no new control decisions are introduced.

Examples:
- adding new datapath capabilities
- extending CONTROL_WORD with additional fields
- adding optional control features that depend only on existing inputs

Behavior:

```
(MS, TS, IR_FIELDS, FLAGS, EXT)
→ same CTRL_ADDR
→ extended CONTROL_WORD
```

Constraint:
- CTRL_ADDR must not change if the input decision space is unchanged.

Constraint:
- New CONTROL_WORD bits must default to values that preserve existing behavior.

---

### 8.2 Input Domain Extension

If new control decisions are introduced, CTRL_ADDR must be extended.

Examples:
- new IR_FIELDS signals
- new FLAGS
- new external condition inputs

Behavior:

```
Old:
CTRL_ADDR = f(MS, TS, IR_FIELDS, FLAGS, EXT)

New:
CTRL_ADDR = f(MS, TS, IR_FIELDS', FLAGS', EXT)
```

Where:
- IR_FIELDS' or FLAGS' includes additional signals

Constraint:
- CTRL_ADDR must be extended or re-encoded to represent the expanded input domain.

Constraint:
- No two distinct input conditions may map to the same CTRL_ADDR unless explicitly intended.

---

### 8.3 Address Extension Mechanism

Extension is performed by incorporating new input signals into the encoding.

Conceptually:

```
Old:
CTRL_ADDR = PACK(MS, TS, IR_FIELDS, FLAGS, EXT)

New:
CTRL_ADDR = PACK(MS, TS, IR_FIELDS, FLAGS, EXT, NEW_INPUTS)
```

Constraint:
- New inputs must be incorporated without violating existing encoding guarantees.
- Existing input mappings must remain stable unless intentionally revised.

---

### 8.4 Backward Compatibility

When extending CTRL_ADDR:

Constraint:
- Existing input combinations must preserve their original control behavior.

Mechanism:

- new input signals must define a default value representing legacy behavior
- extended address space must map legacy conditions to existing CONTROL_WORD entries

Constraint:
- Behavior for existing instructions and states must remain unchanged unless explicitly modified.

---

### 8.5 Prohibited Alternatives

The following are prohibited when extending control:

- partial decoding outside CTRL_ADDR
- secondary decision logic after ROM lookup
- implicit interpretation of CONTROL_WORD fields
- introduction of control behavior not defined by CTRL_ADDR

Constraint:
- All new decisions must be reflected in CTRL_ADDR formation.

---

### 8.6 Relationship to CONTROL_WORD

See:
- [Control Word](./04-control-word.md)

Constraint:
- Extending CONTROL_WORD and extending CTRL_ADDR are independent operations.

Rule:

- adding outputs → extend CONTROL_WORD
- adding decision inputs → extend CTRL_ADDR

Constraint:
- CONTROL_WORD must not compensate for missing address distinctions.

---

## 9. Timing Model

CTRL_ADDR is evaluated during each timing state.

Behavior:

- at TP(n-1):
  - state inputs (MS, IR, registers) are latched

- during TS(n):
  - IR_FIELDS and FLAGS are evaluated
  - CTRL_ADDR is formed

- before TP(n):
  - CTRL_ADDR must be stable

Constraint:
- CTRL_ADDR must settle within the evaluation window of TS.

---

## 10. Design Principles

### 10.1 Reduction Before Encoding

All state must be reduced to control-relevant forms prior to address formation.

---

### 10.2 Explicit Control Decisions

All control behavior must be explicitly represented in CTRL_ADDR.

Constraint:
- no implicit or inferred behavior is permitted.

---

### 10.3 Separation of Concerns

- IR decoding → IR_FIELDS
- condition evaluation → FLAGS
- control selection → CTRL_ADDR

Constraint:
- no cross-layer behavior is allowed.

---

### 10.4 Isolation from Datapath

Control addressing must not depend on datapath implementation.

Constraint:
- datapath signals must not influence CTRL_ADDR.

---

## 11. Summary

Control addressing maps reduced system state to a control store index.

Core definition:

```
CTRL_ADDR = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

Transformation pipeline:

```
IR → IR_FIELDS
Registers → FLAGS
(MS, TS, IR_FIELDS, FLAGS, EXT) → CTRL_ADDR
CTRL_ADDR → CONTROL_WORD
```

This ensures:

- deterministic control selection
- explicit decision encoding
- strict separation between state and control behavior