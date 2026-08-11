## Group 1 Execution

## Purpose
  
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

## Scope
  
Applies to instructions where:

- IR[11:9] = 111  
- Group 1 bit pattern is selected (see [Group 1 ISA](../../02-isa/01-group-1.md))

---

## Execution Model
  
Group 1 instructions are defined as a set of independent operations selected directly by IR bits.

Properties:

- Each IR bit enables one or more μops  
- Multiple μops may be selected in a single instruction  
- μops are assigned to TS  
- μops execute concurrently within a TS  

All μop selection is derived directly from IR bits.

---

## Instruction Definition

### IR[11:9] = 111 (Group 1)

TS1:
- if IR[bit(CLA)] = 1: AC_CLEAR  
- if IR[bit(CLL)] = 1: L_CLEAR  

TS2:
- if IR[bit(CMA)] = 1: AC_COMP  
- if IR[bit(CML)] = 1: L_COMP  

TS3:
- if IR[bit(IAC)] = 1: AC_INC  

TS4:
- if IR[bit(RAR)] = 1 AND IR[bit(BSW)] = 0: AC_RAR  
- if IR[bit(RAL)] = 1 AND IR[bit(BSW)] = 0: AC_RAL  
- if IR[bit(RAR)] = 1 AND IR[bit(BSW)] = 1: AC_RTR  
- if IR[bit(RAL)] = 1 AND IR[bit(BSW)] = 1: AC_RTL  
- if IR[bit(RAR)] = 0 AND IR[bit(RAL)] = 0 AND IR[bit(BSW)] = 1: AC_BSW  

---

## Composition Rules
  
- μops in different TS execute in TS order  
- μops in the same TS execute concurrently  
- no ordering exists within a TS  

Constraints:

- IR[bit(RAR)] and IR[bit(RAL)] must not both be 1  
- TS4 must resolve to at most one μop  
- no two μops may write the same register in the same TS  

---

## Notes
  
- All behavior is expressed strictly in μops  
- No symbolic instruction interpretation is used  
- All μop selection is derived directly from IR bits  