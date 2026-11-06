# Group 2 Execution

## 1. Purpose
  
Defines execution behavior for OPR Group 2 instructions.  
This document specifies:
- IR bit to μop mapping
- TS assignment of μops
- condition evaluation rules
- composition constraints  

Instruction semantics and encoding details are defined in:
- [Group 2 ISA](../../02-isa/02-group-2.md)  

Execution behavior follows:
- [Execution Model](../01-execution-model.md)

---

## 2. Scope
  
Applies when:

```text
IR_IS_OPR = 1
IR_OPR_GROUP2 = 1
```

---

## 3. Execution Model
  
Group 2 instructions are composed of:
- conditional skip operations (TS1)
- optional state modification operations (TS2–TS3)

Properties:
- Skip conditions are evaluated during TS1
- Skip results are realized as conditional PC_INC
- Sub-group selection defines condition composition:
  - AND sub-group: all enabled conditions must be true
  - OR sub-group: any enabled condition must be true
- CLA and OSR are datapath operations
- HLT is a control-level operation (see TS3)
- μops execute concurrently within a TS  

All μop selection and condition evaluation are derived directly from IR bits.

---

## 4. Instruction Definition

### 4.1 IR[11:9] = 111 (Group 2)

### 4.2 Sub-group selection
  
- AND sub-group: IR[3] = 1 AND IR[0] = 0  
- OR sub-group:  IR[3] = 0 AND IR[0] = 0  

---

### 4.3 TS1 — Skip Evaluation

Conditional μops:

```text
SKIP_TAKEN = 1 -> PC_INC
```

The composition of the Group 2 skip predicates, including AND-subgroup vacuous truth and OR-subgroup behavior, is defined by `SKIP_TAKEN` in the control-input definitions [found here](../../04-control/10-control-input-definitions/03-derived-flags.md#skip_taken).

The Group 2 ISA defines the instruction-bit meanings and subgroup encodings.

---

### 4.4 TS2 — AC Modification

- if IR[bit(CLA)] = 1: AC_CLEAR

---

### 4.5 TS3 — Register and Control Operations

- if IR[bit(OSR)] = 1: AC_OR_FP_SR

- if IR[bit(HLT)] = 1:
  - HLT is a meta-instruction
  - No datapath μop is performed
  - Behavior is implemented via control signals
  - No register state is modified
  - Control behavior is defined in [Control Model](../../04-control/01-control-model.md)

---

### 4.6 TS4

- (no μops)

---

## 5. Composition Rules

### 5.1 Skip Composition
- TS1 conditions are combined per sub-group definition
- Evaluation produces a single boolean result
- Result is realized as conditional PC_INC

### 5.2 TS Ordering
- TS1 executes before TS2 and TS3
- PC_INC (if taken) occurs before subsequent operations

### 5.3 Concurrency
- μops within a TS execute concurrently
- No ordering exists within a TS

### 5.4 Register Conflicts
- No two μops may write the same register in the same TS

---

## 6. Notes
- All behavior is expressed using IR bit selection, μops, and conditions
- No symbolic instruction interpretation is used
- Skip behavior is realized solely via PC_INC
- HLT is a control-layer effect and does not correspond to a datapath μop
- No persistent flag state is introduced
