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
- Every OPR completes in FETCH and never enters EXECUTE
- The control store selects the pass by instruction group; IR bits select the operations inside the [OPR pass unit](./01-group1-execution.md#4-opr-pass)
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
- Pass-unit stages and the bits that select them
- What acts at FETCH TP3, and at FETCH TP4

---

## 5. Constraints
  
- Register loads must be expressed as μops; IR bits select the operations composed within a pass
- Multiple μops may be active within the same TS
- No μop conflicts are permitted
- All operations are derived directly from IR bits

---

## 6. Summary
  
OPR execution is defined as:

- one pass through the OPR pass unit, loaded at FETCH TP3
- composition of multiple operations within a single instruction
- completion at FETCH TP4, where a taken Group 2 skip increments PC