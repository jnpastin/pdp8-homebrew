# Memory Invalid Conditions

## 1. Purpose

This document identifies architectural memory conditions that are design errors.

---

## 2. MEM_ADDR, Addressing, and Field-Selection Violations

The following are invalid:

- MEM_ADDR defined as anything other than {MFB, AB}
- MEM_ADDR treated as an architectural or CPU-visible register
- MEM_ADDR used as a replacement for EA
- MEM_ADDR used as a general system-wide address term
- memory inspecting the source or history of MFB or AB
- memory interpreting instruction bits
- memory choosing its own field, address, data, or control source
- memory generating control decisions
- MFB interpreted by memory as IF, DF, or any other CPU register
- memory inspecting IF or DF directly
- memory distinguishing whether MFB or AB originated from instruction fetch, direct addressing, indirect addressing, data-field selection, DMA, or console access

---

## 3. Read/Write Protocol and Bus-Ownership Violations

The following are invalid:

- /RD and /WR asserted at the same time
- /RD asserted without a valid MEM_ADDR
- /WR asserted without a valid MEM_ADDR
- /WR asserted without valid write data present on MDB
- memory driving MDB during a write
- memory driving MDB while idle (neither /RD nor /WR asserted)
- no valid MDB driver during a write
- more than one active MDB driver on MDB
- a valid read logically modifying stored memory contents
- a valid read returning a value other than the word stored at M[MEM_ADDR]
- a valid write modifying any memory word other than the single selected M[MEM_ADDR]
- a completed memory operation with neither /RD nor /WR asserted
- memory behavior varying based on whether an operation originated from the CPU, DMA, or console logic

---

## 4. Timing and Stability Violations

The following are invalid:

- MFB changing while /RD or /WR is asserted
- AB changing while /RD or /WR is asserted
- MDB write data changing during the active write-data stability window
- memory failing to hold MDB stable for the required setup/hold interval around the commit TP during a read
- the MDB source failing to hold write data stable for the required setup/hold interval around the commit TP during a write
- a combined read/write memory operation
- changes on MFB or AB alone, without /RD or /WR asserted, causing memory behavior

---

## 5. DMA and Console Access Violations

The following are invalid:

- DMA or console memory access bypassing the memory interface
- DMA or console access modifying memory contents without /WR asserted
- DMA access defining a separate memory address space, data path, or semantics distinct from CPU-initiated access
- a console Examine or Deposit access producing memory behavior different from an equivalent CPU-initiated access presenting the same MFB, AB, /RD, /WR, and MDB values

---

## 6. Physical Implementation (Memory Technology) Violations

The following are invalid:

- memory technology not hidden behind the memory subsystem interface
- physical memory technology changing the logical width of a memory word
- physical memory technology changing the interpretation of MEM_ADDR
- physical address decoding (device-select, chip-select, bank-select, or similar) changing the logical meaning of MEM_ADDR
- a MEM_ADDR value mapping to more than one logical memory word, or not mapping to exactly one
- unused physical bits affecting logical memory behavior
- physical implementation changing valid read behavior or valid write behavior as defined elsewhere in Section 6
- physical implementation changing the boundary between memory behavior and CPU/control behavior
- memory device access time not fitting within the active read window
- memory device write timing not fitting within the active write window
- technology-specific timing parameters changing the logical memory behavior
- physical read-related internal actions changing the logical value returned by a later read, except through a valid write
- write-endurance, wear-leveling, block-management, or erase-cycle mechanisms changing the logical definition of a memory write
- volatility or nonvolatility affecting memory behavior while the system is powered and operating normally
- a design assuming specific memory contents after power-up without an explicit definition elsewhere

---

## 7. Validation Boundary

These conditions are architectural design errors.

The architecture does not require centralized runtime validation of memory-subsystem compliance. Optional diagnostics may detect violations, but diagnostic behavior must not participate in normal control, timing, ownership, or sequencing.

---

## 8. Related Documents

- [Memory Model](./01-memory-model.md)
- [Memory Interface](./02-memory-interface.md)
- [Read/Write Protocol](./03-read-write-protocol.md)
- [Memory Timing](./04-memory-timing.md)
- [Memory Field Selection](./05-memory-field-selection.md)
- [DMA & Console Access](./06-dma-and-console-access.md)
- [Implementation Constraints](./07-implementation-constraints.md)
