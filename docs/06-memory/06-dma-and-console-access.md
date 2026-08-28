# DMA and Console Memory Access

## 1. Purpose

This document defines how the memory subsystem treats memory operations that originate outside normal CPU instruction execution.

This includes:

- DMA-initiated memory access
- console Examine memory access
- console Deposit memory access

The memory subsystem does not define DMA sequencing, DMA arbitration, console sequencing, or front-panel control behavior.

---

## 2. Access-Origin Boundary

The memory subsystem does not distinguish the origin of a valid memory operation.

From the memory subsystem perspective, all memory operations are defined by the same interface values:

- MFB
- AB
- MDB
- /RD
- /WR

If those interface values define a valid read or write operation, memory performs the corresponding operation regardless of whether the requester is the CPU, DMA logic, or console logic.

---

## 3. DMA Memory Access

During DMA memory access, the memory subsystem uses the same read/write protocol defined for all memory operations.

A valid DMA read requires:

- stable MFB
- stable AB
- /RD asserted
- /WR not asserted
- memory allowed to drive MDB

A valid DMA write requires:

- stable MFB
- stable AB
- /WR asserted
- /RD not asserted
- valid write data driven on MDB by a source outside memory

The memory subsystem does not define:

- DMA request timing
- DMA grant timing
- DMA arbitration
- DMA word count
- single-cycle versus multi-cycle DMA behavior
- DMA continuation rules
- DMA device-side address generation
- DMA device-side data buffering

Those behaviors are outside the memory subsystem boundary.

---

## 4. DMA Operation Meaning

A DMA read returns the word stored at:

M[{MFB, AB}]

A DMA write stores the value presented on MDB at:

M[{MFB, AB}]

DMA does not create a separate memory address space, separate memory data path, or separate memory semantics.

---

## 5. Console Examine Access

Console Examine is a memory read from the memory subsystem perspective.

During a valid console Examine memory access:

- memory observes MFB
- memory observes AB
- /RD is asserted
- /WR is not asserted
- memory drives MDB with the word stored at M[{MFB, AB}]

The memory subsystem does not define how the console operation selects the field or address.

---

## 6. Console Deposit Access

Console Deposit is a memory write from the memory subsystem perspective.

During a valid console Deposit memory access:

- memory observes MFB
- memory observes AB
- /WR is asserted
- /RD is not asserted
- memory observes the 12-bit value presented on MDB
- memory stores that value at M[{MFB, AB}]

The memory subsystem does not define how the console operation selects the field, address, or deposited value.

---

## 7. Origin-Independent Behavior

The same MFB, AB, /RD, /WR, and MDB values produce the same memory behavior regardless of access origin.

For a read:

- the selected word is determined only by MFB and AB
- the value driven by memory is determined only by the contents of M[{MFB, AB}]

For a write:

- the selected word is determined only by MFB and AB
- the stored value is determined only by MDB during the active write window

---

## 8. Invalid Conditions

The following conditions are invalid during DMA or console memory access:

- /RD and /WR asserted together
- unstable MFB during the active operation window
- unstable AB during the active operation window
- DMA or console write without valid MDB write data
- memory driving MDB during a write
- more than one source driving MDB
- DMA or console access attempting to bypass the memory interface
- DMA or console access modifying memory without /WR asserted

Invalid conditions are design errors.

---

## 9. Invariants

- DMA memory access uses the normal memory interface.
- Console memory access uses the normal memory interface.
- Memory does not distinguish CPU, DMA, or console origin.
- DMA does not define separate memory semantics.
- Console access does not define separate memory semantics.
- A DMA or console read returns one 12-bit word from M[{MFB, AB}].
- A DMA or console write stores one 12-bit word at M[{MFB, AB}].
- DMA sequencing is outside the memory subsystem boundary.
- Console sequencing is outside the memory subsystem boundary.
- Memory behavior is determined only by the memory interface signals.

---

## 10. Summary

DMA and console memory accesses are not special memory operations.

They use the same memory interface and the same read/write protocol as all other memory accesses. The requester determines how the interface signals are produced; the memory subsystem only responds to the valid read or write operation presented at its boundary.