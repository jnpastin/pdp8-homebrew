# Addressing Modes and Effective Address Model

## 1. Scope

This section applies only to Memory Reference Instructions (MRI).

MRI instructions and their encoding are defined in the [encoding model](./00-encoding-model.md) document.

The addressing concepts in this document do not apply to:

- IOT instructions
- OPR instructions

---

## 2. Address Representation

### 2.1 Logical Address

All MRI addressing operates on a 12-bit logical address within a field.

### 2.2 Extended Address Notation

EA_addr is a phase-dependent working value that becomes the final operand address before EXECUTE.  It contains all of the information that the system requires in order to address the entire memory system.


Final effective address is defined as:

    EA_logical = (EA_fld, EA_addr)

For clarity across fields, this specification uses a 5-digit octal notation:

FXXXX

Where:

- F = field (octal, 0–7)
- XXXX = 12-bit address within the field

Example:

10354

Means:

- Field = 1
- Address = 0354

This notation is used when referring to effective addresses (EA).

---

## 3. MRI Addressing Fields

MRI format (see [encoding doc](./00-encoding-model.md)) includes:

- I bit: indirect flag
- P bit: zero/current page select
- 7-bit offset

These bits define how the initial address is formed.

---

## 4. Addressing Domains

### 4.1 Zero Page

- Selected when P = 0
- Base address = 0000
- Final logical address = 0000 || offset

Properties:

- Exists independently in every field
- Used for:
  - Global access
  - Pointer storage
  - Auto-index registers (0010–0017)

---

### 4.2 Current Page

- Selected when P = 1
- Base address = PC[11:7]
- Final logical address = PC[11:7] || offset

Properties:

- Defined relative to the instruction being executed
- Therefore tied to IF

---

## 5. Instruction Field (IF)

IF determines:

- The field used for:
  - Instruction fetch
  - Current page formation
  - Direct memory access (I = 0)
  - The initial address calculation for all MRI instructions

Key property:

IF defines the execution context and is always used to form the base address.

---

## 6. Data Field (DF)

DF determines:

- The field used for:
  - Indirect pointer resolution
  - Final operand access when indirection is used

---

## 7. IF vs DF: Correct Architectural Rule

The actual field rule is:

- IF is used to compute the initial address
- DF is used only when indirection occurs (I = 1)

This creates a strict distinction:

Operation phase              | Field used
-----------------------------|-----------
Instruction fetch           | IF        
Current page resolution     | IF        
Direct access (I = 0)       | IF        
Indirect pointer fetch      | DF        
Final indirect operand      | DF        

---

## 8. Direct Addressing (I = 0)

When the indirect bit is clear:

1. Address is formed using IF, P, and offset
2. This becomes the final EA
3. Memory access occurs in IF

Key constraint:

Direct addressing never uses DF.

---

## 9. Indirect Addressing (I = 1)

Indirect addressing is a two-stage process.

### 9.1 Stage 1: Pointer Location

- The base address is formed exactly like direct addressing
- This uses IF, P, and offset

This address identifies a pointer location in the field defined by IF.

### 9.2 Stage 2: Pointer Resolution

- The value stored at the pointer location is read as a 12-bit address
- This read occurs in DF context

The resulting value becomes the final EA.

Key property:

Indirect addressing always starts in IF and resolves into DF.

---

## 10. Example: Cross-Field Indirection

Instruction:

`TAD I myVAL`

Assume:

- IF = 0
- DF = 1

Memory:

Field 0:
  myVAL -> 0354

Field 1:
  0354 -> data

Execution:

1. Locate myVAL using IF
2. Read pointer value 0354
3. Interpret as 10354 via DF
4. Use value at 10354

---

## 11. Off-Page Indirection

The pointer value obtained during indirection:

- Is a full 12-bit address
- Is not constrained to the originating page

This allows arbitrary addressing within DF.

---

## 12. Pointer Model

Indirect addressing assumes:

A memory location in the current (or zero) page holds a pointer to the target address.

This pointer:

- Is always located using IF
- Is always resolved using DF

---

## 13. Auto-Index Registers (0010–0017)

Locations:

0010–0017 (octal)

Defined per field.

### 13.1 Behavior

Auto-indexing applies only when:

- I = 1
- Address in 0010–0017

### 13.2 Operation

1. Pointer location identified via IF
2. If in range, increment value
3. Write back incremented value
4. Use as pointer
5. Interpret result in DF

### 13.3 Distinction

- I = 0: normal memory
- I = 1: auto-increment behavior

---

## 14. Summary Invariants

- MRI-only behavior
- IF defines instruction context and direct access
- DF is used only after indirection begins
- Indirection is a field transition mechanism
- Auto-indexing applies only with I = 1
- Final EA expressed as FXXXX

---

## 15. Transition to EA Generation

This section defines conceptual rules.

EA generation algorithm is defined separately.
