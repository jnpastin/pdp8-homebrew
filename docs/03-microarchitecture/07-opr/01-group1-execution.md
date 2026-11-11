# Group 1 Execution

## 1. Purpose
  
Defines execution behavior for OPR Group 1 instructions.

This document specifies:
- IR bit to μop mapping
- TS assignment of μops
- composition constraints

Instruction semantics and encoding details are defined in:

- [Group 1 ISA](../../02-isa/01-group-1.md)

Execution behavior follows:

- [Execution Model](../01-execution-model.md)

---

## 2. Scope
  
Applies when:

```text
IR_IS_OPR = 1
IR_OPR_GROUP1 = 1
```

---

## 3. Execution Model
  
Group 1 instructions are defined as a set of independent operations selected directly by IR bits.

Properties:

- Each IR bit enables one or more μops  
- Multiple μops may be selected in a single instruction  
- μops are assigned to TS  
- μops execute concurrently within a TS  

All μop selection is derived directly from IR bits.

---

## 4. Instruction Definition

### 4.1 IR[11:9] = 111 (Group 1)

TS1:
- if IR_OPR_CLA = 1: AC_CLEAR  
- if IR_OPR_CLL = 1: L_CLEAR  

TS2:
- if IR_OPR_CMA = 1: AC_COMP  
- if IR_OPR_CML = 1: L_COMP  

TS3:
- if IR_OPR_IAC = 1: AC_INC  

TS4:
- if IR_OPR_RAR = 1 AND IR_OPR_RAL = 0 AND IR_OPR_BSW = 0: AC_RAR  
- if IR_OPR_RAL = 1 AND IR_OPR_RAR = 0 AND IR_OPR_BSW = 0: AC_RAL  
- if IR_OPR_RAR = 1 AND IR_OPR_RAL = 0 AND IR_OPR_BSW = 1: AC_RTR  
- if IR_OPR_RAL = 1 AND IR_OPR_RAR = 0 AND IR_OPR_BSW = 1: AC_RTL  
- if IR_OPR_RAR = 0 AND IR_OPR_RAL = 0 AND IR_OPR_BSW = 1: AC_BSW  

---

## 5. Composition Rules
  
- μops in different TS execute in TS order  
- μops in the same TS execute concurrently  
- no ordering exists within a TS  

Constraints:

- IR_OPR_RAR and IR_OPR_RAL must not both be 1  
- TS4 must resolve to at most one μop  
- no two μops may write the same register in the same TS  

---

## 6. Notes
  
- All behavior is expressed strictly in μops  
- No symbolic instruction interpretation is used  
- All μop selection is derived directly from IR bits  