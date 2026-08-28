# Memory Field Selection

## 1. Purpose

This document defines how the memory subsystem interprets the memory field presented on MFB.

The memory subsystem does not choose the memory field. It only observes the field value presented at the memory interface.

---

## 2. Field Boundary

MFB provides the memory field value used by the memory subsystem.

The memory subsystem treats MFB as part of MEM_ADDR:

MEM_ADDR = {MFB, AB}

MFB is not interpreted as IF, DF, or any other CPU register by the memory subsystem. It is only the field value currently presented to memory.

---

## 3. Field Selection Responsibility

The rules that determine which value appears on MFB are outside the memory subsystem boundary.

The memory subsystem does not determine whether MFB came from:

- instruction fetch context
- direct addressing
- indirect addressing
- data field selection
- DMA access
- console access
- any other defined memory requester

From the memory subsystem perspective, all valid memory operations use the MFB value already present at the memory interface.

---

## 4. Relationship to IF and DF

IF and DF are CPU-side field registers.

The memory subsystem does not inspect IF or DF directly.

When a memory operation occurs, memory observes only MFB. If MFB was derived from IF, DF, or another source, that selection has already occurred before memory interprets the operation.

---

## 5. Fielded Memory Space

MFB selects the memory field.

AB selects the 12-bit address within that field.

Together, MFB and AB select one 12-bit memory word:

M[{MFB, AB}]

Equivalently:

M[MEM_ADDR]

---

## 6. Field Stability

During any valid memory operation, MFB must remain stable for the active operation window.

If MFB changes while /RD or /WR is asserted, the memory operation is invalid.

---

## 7. Field Origin Independence

The memory subsystem treats the same MFB value identically regardless of operation origin.

A memory access with the same MFB and AB selects the same memory word whether the operation originated from:

- CPU instruction execution
- DMA
- console Examine or Deposit behavior
- another explicitly defined memory requester

Operation origin does not change memory field interpretation.

---

## 8. Invariants

- MFB is the memory field input to the memory subsystem.
- Memory does not choose the value on MFB.
- Memory does not inspect IF or DF directly.
- Memory does not distinguish the source of MFB.
- MFB forms the high-order portion of MEM_ADDR.
- AB forms the 12-bit address portion of MEM_ADDR.
- MEM_ADDR is defined as {MFB, AB}.
- MFB must remain stable during an active memory operation.

---

## 9. Summary

The memory subsystem interprets MFB only as the field portion of MEM_ADDR.

Field-selection rules belong outside Section 6. Memory sees only the selected field value presented on MFB and combines it with AB to select a 12-bit memory word.