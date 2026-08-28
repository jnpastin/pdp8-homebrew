# Implementation Constraints

## Purpose

This document defines implementation constraints for the physical memory technology used by the memory subsystem.

It does not select a specific memory technology or memory part.

---

## Implementation Boundary

The memory subsystem may be implemented using any suitable physical memory technology, provided that the implementation satisfies the logical memory behavior defined by Section 6.

Acceptable implementation technologies may include:

- SRAM
- MRAM
- FRAM
- nvSRAM
- battery-backed SRAM
- another technology that satisfies the same interface behavior

The selected technology must be hidden behind the memory subsystem interface.

---

## Required Interface Behavior

The implementation must behave as random-access read/write memory at the memory interface.

For every valid memory read:

- the implementation must use MEM_ADDR to select one stored word
- the implementation must drive the selected 12-bit word onto MDB while /RD is asserted
- the implementation must not logically modify memory contents

For every valid memory write:

- the implementation must use MEM_ADDR to select one stored word
- the implementation must store the 12-bit value presented on MDB while /WR is asserted
- the implementation must modify exactly one selected memory word

---

## Logical Word Width

The memory subsystem stores 12-bit words.

The physical implementation may use memory devices with a different native width, provided that the memory subsystem presents the required 12-bit logical behavior.

Examples:

- multiple narrower devices may be combined to form one 12-bit word
- wider devices may be partially used
- unused physical bits must not affect logical memory behavior

The logical memory word remains 12 bits regardless of physical device width.

---

## Address Mapping

The implementation must map each MEM_ADDR value to exactly one logical 12-bit memory word.

The physical implementation may decode MEM_ADDR into device-select, chip-select, bank-select, or internal address signals, but those physical signals must not change the logical meaning of MEM_ADDR.

MEM_ADDR remains:

MEM_ADDR = {MFB, AB}

---

## Timing Compliance

The selected memory technology must satisfy the memory timing contract.

The implementation must ensure that:

- read data is valid on MDB while /RD is asserted
- write data is captured from MDB while /WR is asserted
- MFB and AB stability requirements are met
- the memory device access time fits within the active read window
- the memory device write requirements fit within the active write window

Technology-specific timing parameters are implementation constraints.

These may include:

- access time
- output enable delay
- output disable delay
- write pulse width
- address setup time
- address hold time
- data setup time
- data hold time

These implementation details must not change the logical memory behavior.

---

## Read Side Effects

Some physical memory technologies may perform internal actions during a read.

If a technology performs internal read-related actions, those actions must preserve the logical value stored at the selected MEM_ADDR.

A valid read must not logically change the value returned by later reads unless a valid write occurs.

---

## Write Endurance

If the selected memory technology has finite write endurance, the implementation must account for that limitation.

Write endurance limits are implementation constraints. They must not change the logical definition of a memory write.

Section 6 does not define wear leveling, block management, erase cycles, or write avoidance mechanisms.

If such mechanisms are required by the selected technology, they must preserve the Section 6 memory interface behavior.

---

## Volatility and Retention

The logical memory model does not require memory contents to persist across power loss.

If the selected implementation is nonvolatile, battery-backed, or otherwise retains contents across power loss, that retention is an implementation property unless explicitly defined as a system requirement elsewhere.

Volatility or nonvolatility must not affect memory behavior while the system is powered and operating normally.

---

## Power-Up Contents

Section 6 does not define memory contents after power-up.

Unless explicitly defined elsewhere, memory contents after power-up are unspecified.

A memory implementation may power up with retained contents, cleared contents, random contents, or technology-defined contents, provided that normal read/write behavior is valid after the memory subsystem is ready.

---

## Physical Device Details

The following are implementation details and are not defined by this document:

- specific memory part numbers
- package type
- voltage level
- board layout
- backplane connector pinout
- chip-select logic implementation
- device count
- memory board organization
- mechanical placement
- removable or replaceable module design

These details may be documented in physical or implementation sections if needed.

---

## Invariants

- The logical memory word width is 12 bits.
- MEM_ADDR selects one logical memory word.
- Physical memory width must not change logical word width.
- Physical address decoding must not change the meaning of MEM_ADDR.
- Read timing must satisfy the active read window.
- Write timing must satisfy the active write window.
- Physical read side effects must preserve logical memory contents.
- Volatility or nonvolatility must not change normal read/write behavior.
- Power-up contents are unspecified unless explicitly defined elsewhere.
- Specific memory part selection is outside the logical memory model.

---

## Summary

The memory implementation may use any suitable technology that satisfies the Section 6 memory contract.

The physical memory technology must present the required logical behavior: 12-bit random-access reads and writes selected by MEM_ADDR, with timing compatible with /RD, /WR, MFB, AB, and MDB.