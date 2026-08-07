## Group 2 Execution

## Purpose
  
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

## Scope
  
Applies to instructions where:
- IR[11:9] = 111
- Group 2 bit pattern is selected (see [Group 2 ISA](../../02-isa/02-group-2.md))

## Execution Model
  
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

## Instruction Definition

### IR[11:9] = 111 (Group 2)

### Sub-group selection
  
- AND sub-group: IR[3] = 1 AND IR[0] = 0  
- OR sub-group:  IR[3] = 0 AND IR[0] = 0  

---

### TS1 — Skip Evaluation

Skip behavior is expressed as conditional execution of:
- PC_INC

#### AND Sub-group (IR[3] = 1)

Let the active predicate set P be:

- Include (AC ≥ 0) if IR[bit(SPA)] = 1
- Include (AC ≠ 0) if IR[bit(SNA)] = 1
- Include (L = 0)   if IR[bit(SZL)] = 1

Condition:

- if all predicates in P evaluate true: PC_INC
- an empty P is vacuously true, so it skips unconditionally (SKP = 7410)

Examples:

1. IR[bit(SPA)] = 1, IR[bit(SNA)] = 0, IR[bit(SZL)] = 0  
   P = { AC ≥ 0 }  
   - AC = 0000 → true → PC_INC  
   - AC < 0 → false → no skip  

2. IR[bit(SPA)] = 1, IR[bit(SNA)] = 1, IR[bit(SZL)] = 0  
   P = { AC ≥ 0, AC ≠ 0 }  
   - AC = 0001 → true ∧ true → PC_INC  
   - AC = 0000 → true ∧ false → no skip  
   - AC < 0 → false ∧ true → no skip  

3. IR[bit(SPA)] = 1, IR[bit(SNA)] = 1, IR[bit(SZL)] = 1  
   P = { AC ≥ 0, AC ≠ 0, L = 0 }  
   - AC = 0001, L = 0 → true ∧ true ∧ true → PC_INC  
   - AC = 0001, L = 1 → true ∧ true ∧ false → no skip  

---

#### OR Sub-group (IR[3] = 0)

Let the active predicate set P be:

- Include (AC < 0) if IR[bit(SMA)] = 1
- Include (AC = 0) if IR[bit(SZA)] = 1
- Include (L ≠ 0) if IR[bit(SNL)] = 1

Condition:

- if any predicate in P evaluates true: PC_INC

Examples:

1. IR[bit(SMA)] = 1, IR[bit(SZA)] = 0, IR[bit(SNL)] = 0  
   P = { AC < 0 }  
   - AC < 0 → true → PC_INC  
   - AC ≥ 0 → false → no skip  

2. IR[bit(SMA)] = 1, IR[bit(SZA)] = 1, IR[bit(SNL)] = 0  
   P = { AC < 0, AC = 0 }  
   - AC < 0 → true ∨ false → PC_INC  
   - AC = 0000 → false ∨ true → PC_INC  
   - AC > 0 → false ∨ false → no skip  

3. IR[bit(SMA)] = 0, IR[bit(SZA)] = 1, IR[bit(SNL)] = 1  
   P = { AC = 0, L ≠ 0 }  
   - AC = 0000 → true → PC_INC  
   - AC ≠ 0, L ≠ 0 → false ∨ true → PC_INC  
   - AC ≠ 0, L = 0 → false ∨ false → no skip  

---

Notes:
- Predicates are included only when their corresponding IR bit = 1
- Unset bits contribute no condition
- If P is empty: the AND sub-group skips unconditionally (vacuous truth); the OR sub-group does not skip
- Evaluation uses only register state; no intermediate state is created

---

### TS2 — AC Modification

- if IR[bit(CLA)] = 1: AC_CLEAR

---

### TS3 — Register and Control Operations

- if IR[bit(OSR)] = 1: AC_OR_SR

- if IR[bit(HLT)] = 1:
  - HLT is a meta-instruction
  - No datapath μop is performed
  - Behavior is implemented via control signals
  - No register state is modified
  - Control behavior is defined in [Control Model](../04-control/01-control-model.md)

---

### TS4

- (no μops)

---

## Composition Rules

### Skip Composition
- TS1 conditions are combined per sub-group definition
- Evaluation produces a single boolean result
- Result is realized as conditional PC_INC

### TS Ordering
- TS1 executes before TS2 and TS3
- PC_INC (if taken) occurs before subsequent operations

### Concurrency
- μops within a TS execute concurrently
- No ordering exists within a TS

### Register Conflicts
- No two μops may write the same register in the same TS

---

## Notes
- All behavior is expressed using IR bit selection, μops, and conditions
- No symbolic instruction interpretation is used
- Skip behavior is realized solely via PC_INC
- HLT is a control-layer effect and does not correspond to a datapath μop
- No persistent flag state is introduced
