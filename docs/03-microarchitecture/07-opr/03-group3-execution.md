## Group 3 Execution

## Purpose
  
Defines execution behavior for OPR Group 3 instructions.  
This document specifies:
- IR bit to μop mapping
- TS assignment of μops
- composition constraints  

Instruction semantics and encoding details are defined in:
- [Group 3 ISA](../../02-isa/03-group-3.md)  

Execution behavior follows:
- [Execution Model](../01-execution-model.md)

## Scope
  
Applies to instructions where:
- IR[11:9] = 111
- Group 3 bit pattern is selected (see [Group 3 ISA](../../02-isa/03-group-3.md))

## Execution Model
  
Group 3 instructions are composed of:
- optional state modification operations across TS1–TS2

Properties:
- Each IR bit independently enables a μop
- Multiple μops may be selected in a single instruction
- μops execute concurrently within a TS
- μops across TS execute in TS order  

All μop selection is derived directly from IR bits.

## Instruction Definition

### IR[11:9] = 111 (Group 3)

---

### TS1 — AC Modification

- if IR[bit(CLA)] = 1: AC_CLEAR

---

### TS2 — Register Transfer and Logical Operations

- if IR[bit(MQA)] = 1: AC_OR_MQ
- if IR[bit(MQL)] = 1: AC_TO_MQ_AND_CLEAR_AC
- if IR[bit(MQA)] = 1 AND IR[bit(MQL)] = 1: AC_MQ_SWAP

---

### TS3

- (no μops)

---

### TS4

- (no μops)

---

## Composition Rules

### TS Ordering
- TS1 executes before TS2
- Effects of TS1 are visible to TS2

### Concurrency
- μops within a TS execute concurrently
- No ordering exists within a TS

### Register Conflicts
- No two μops may write the same register in the same TS

### Group 3 Constraints
- When IR[bit(MQA)] and IR[bit(MQL)] are both 1, the combination selects AC_MQ_SWAP (the SWP instruction), which exchanges AC and MQ as a single operation
- TS2 must resolve to at most one μop
- This mirrors the Group 1 rotate/BSW decode, where two otherwise-conflicting bits select a single combined operation

---

## Notes
- All behavior is expressed using IR bit selection and μops
- No symbolic instruction interpretation is used
- No memory or I/O interaction occurs
- No control-level operations are defined in this group
- No persistent flag state is introduced