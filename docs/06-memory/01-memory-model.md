# Memory Model

## 1. Purpose

This document defines the logical memory model from the perspective of the memory subsystem.

Memory is modeled as storage for 12-bit words. Each word is selected by the field and address values presented at the memory interface.

---

## 2. Scope Boundary

Section 6 defines memory behavior at the memory subsystem boundary.

It does not define how the CPU, ISA, microarchitecture, or control system produce the field, address, data, or read/write controls presented to memory.

---

## 3. Logical Memory Structure

Memory stores 12-bit words.

A memory word is selected by:

- a memory field value
- a 12-bit address value

The memory subsystem observes those values at its interface and uses them to select a stored word.

---

## 4. Memory Address Terminology

Within Section 6, the term MEM_ADDR refers only to the address as observed by the memory subsystem.

MEM_ADDR is defined as:

MEM_ADDR = {MFB, AB}

Where:

- MFB provides the memory field value
- AB provides the 12-bit address value

MEM_ADDR is a memory-subsystem term.

It is not:

- an architectural register
- a CPU-visible register
- a replacement for EA
- a general system-wide address term

EA remains the architectural and ISA-level effective-address concept.

From the memory subsystem perspective, MEM_ADDR is how memory observes an already-selected effective address at the memory interface.

---

## 5. Relationship to EA

EA describes how an effective address is produced.

MEM_ADDR describes the field and address values that memory sees after field and address selection have already occurred.

The distinction is:

- EA belongs to the architectural and ISA addressing model.
- MEM_ADDR belongs only to the Section 6 memory-subsystem model.
- EA may involve instruction context, IF, DF, direct addressing, indirect addressing, and auto-index behavior.
- MEM_ADDR contains none of that history.
- MEM_ADDR is only {MFB, AB} at the memory boundary.

---

## 6. Word Selection

For any valid memory operation, the selected memory word is:

M[MEM_ADDR]

Equivalently:

M[{MFB, AB}]

The memory subsystem uses MEM_ADDR only as a selection value. It does not inspect the source or history of MFB or AB.

---

## 7. Read Model

During a valid memory read:

- memory observes MEM_ADDR
- memory selects the word stored at M[MEM_ADDR]
- memory provides that 12-bit word on the memory data interface

CPU-side capture of the returned value is defined outside this document.

---

## 8. Write Model

During a valid memory write:

- memory observes MEM_ADDR
- memory observes the 12-bit write data on the memory data interface
- memory stores that value at M[MEM_ADDR]

The source of the write data is defined outside this document.

---

## 9. Technology Independence

The logical memory model is independent of physical memory technology.

The memory subsystem may be implemented using SRAM, MRAM, FRAM, nvSRAM, battery-backed SRAM, or another suitable technology, provided the implementation satisfies the Section 6 memory-interface behavior.

Physical memory technology must not change:

- the width of a memory word
- the interpretation of MEM_ADDR
- valid read behavior
- valid write behavior
- the boundary between memory behavior and CPU/control behavior

Specific part selection, packaging, board layout, and backplane implementation are outside the scope of this document.

---

## 10. Invariants

- Memory stores 12-bit words.
- Memory is addressed through MEM_ADDR.
- MEM_ADDR is defined only as {MFB, AB}.
- MEM_ADDR is local to Section 6.
- MEM_ADDR does not replace EA.
- A valid read returns one 12-bit word from the selected MEM_ADDR.
- A valid write stores one 12-bit word at the selected MEM_ADDR.
- Memory does not interpret instruction bits.
- Memory does not choose field, address, or data sources.
- Memory does not generate control decisions.

---

## 11. Summary

The memory subsystem is a bounded storage component.

It observes MFB, AB, data, and read/write control at its interface. It uses {MFB, AB} as MEM_ADDR to select a 12-bit memory word for read or write operations.