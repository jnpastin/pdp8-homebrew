# OPR Execution

## 1. Purpose
  
Defines execution behavior for Operate Instructions (OPR).

OPR instructions differ from other instruction classes in that behavior is determined directly by individual IR bits rather than a single opcode field.

---

## 2. Execution Context
  
Execution follows the general model defined in:

- [Execution Model](../01-execution-model.md)
- [Instruction Encoding Model](../../02-isa/00-encoding-model.md)

This directory defines only OPR-specific execution behavior.

---

## 3. OPR Model
  
OPR instructions are identified by:

- IR[11:9] = 111  

Within this class, individual bits of IR directly select operations.

Properties:

- Each bit represents an independent operation
- Multiple operations may be combined in a single instruction
- μops are selected directly from IR bit values
- No intermediate decoding into symbolic instructions is performed

---

## 4. Group Structure
  
OPR instructions are divided into groups based on IR bit patterns.

Execution behavior is defined in:

- [Group 1](./01-group1-execution.md)
- [Group 2](./02-group2-execution.md)
- [Group 3](./03-group3-execution.md)

Each group defines:

- Valid bit combinations
- μop selection rules
- TS assignment of operations

---

## 5. Constraints
  
- All behavior must be expressed as μops
- Multiple μops may be active within the same TS
- No μop conflicts are permitted
- All operations are derived directly from IR bits

---

## 6. Summary
  
OPR execution is defined as:

- direct mapping from IR bits to μop selection
- composition of multiple operations within a single instruction
- TS-ordered execution with TP-committed state updates