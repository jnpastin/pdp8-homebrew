# Read/Write Protocol

## Purpose

This document defines memory read and write behavior at the memory subsystem boundary.

It describes what the memory subsystem does when a valid memory read or write operation is presented on the memory interface.

---

## Protocol Boundary

The memory subsystem responds to memory interface signals.

It does not define:

- how the operation was selected
- whether the operation originated from CPU, DMA, or console logic
- how MFB or AB were selected
- how write data was selected
- how read data is captured by the CPU
- how control signals are generated

Those behaviors are outside the memory subsystem boundary.

---

## Common Requirements

Every valid memory operation requires:

- a stable memory field on MFB
- a stable 12-bit address on AB
- a valid MEM_ADDR formed as {MFB, AB}
- exactly one active memory operation type:
  - read
  - write

/RD and /WR must not both be asserted for the same memory operation.

---

## Read Operation

A memory read is requested when /RD is asserted and /WR is not asserted.

During a valid read operation:

- memory observes MFB
- memory observes AB
- memory forms MEM_ADDR = {MFB, AB}
- memory selects the word stored at M[MEM_ADDR]
- memory drives the selected 12-bit word onto MDB

The value driven onto MDB is the memory subsystem output for the read operation.

---

## Read Data Validity

During a valid read operation, /RD defines the active read window.

While /RD is asserted:

- memory must drive MDB
- MFB must remain stable
- AB must remain stable
- MDB must represent the word selected by MEM_ADDR

When /RD is not asserted, memory must not drive MDB.

CPU-side or external capture of MDB is outside the scope of this document.

---

## Read Side Effects

A valid memory read does not modify the contents of memory.

If the physical memory technology performs internal actions during a read, those actions must not change the logical value returned by future reads except as explicitly defined by a valid write operation.

---

## Write Operation

A memory write is requested when /WR is asserted and /RD is not asserted.

During a valid write operation:

- memory observes MFB
- memory observes AB
- memory forms MEM_ADDR = {MFB, AB}
- memory observes the 12-bit value present on MDB
- memory stores that value at M[MEM_ADDR]

The value present on MDB is the memory subsystem input for the write operation.

---

## Write Data Validity

During a valid write operation, the source outside the memory subsystem must drive MDB with valid write data for the required write-data validity window.

The memory subsystem is responsible for storing the value presented on MDB at the selected MEM_ADDR.

The memory subsystem does not determine the source of the write data.

---

## Write Side Effects

A valid memory write modifies exactly one memory word:

M[MEM_ADDR]

No other memory word may be modified by the write operation.

---

## Idle Behavior

When neither /RD nor /WR is asserted:

- memory performs no read operation
- memory performs no write operation
- memory does not modify stored contents
- memory does not drive MDB

MFB and AB may contain values while memory is idle, but those values do not select a completed memory operation unless /RD or /WR is asserted as part of a valid memory operation.

---

## Operation Origin

The memory subsystem does not distinguish the origin of a valid memory operation.

A read or write operation has the same memory-subsystem meaning whether the operation originated from:

- normal CPU execution
- DMA
- console Examine or Deposit behavior
- another explicitly defined memory requester

The origin determines how the interface signals are produced. It does not change how memory interprets a valid read or write at the memory boundary.

---

## Invalid Protocol Conditions

The following protocol conditions are invalid:

- /RD and /WR asserted together
- /RD asserted without a valid MEM_ADDR
- /WR asserted without a valid MEM_ADDR
- /WR asserted without valid write data on MDB
- memory driving MDB during a write
- memory driving MDB while idle
- no valid MDB driver during a write
- more than one active MDB driver
- MFB changing during the required stability window
- AB changing during the required stability window
- MDB changing during the required write-data stability window

Invalid protocol conditions are design errors.

---

## Invariants

- /RD requests a memory read.
- /WR requests a memory write.
- /RD and /WR are mutually exclusive for valid memory operations.
- Reads use MEM_ADDR = {MFB, AB}.
- Writes use MEM_ADDR = {MFB, AB}.
- A valid read returns the word stored at M[MEM_ADDR].
- A valid write stores one 12-bit word at M[MEM_ADDR].
- A valid read does not logically modify memory contents.
- A valid write modifies exactly one selected memory word.
- Memory drives MDB only during valid reads.
- Memory observes MDB during valid writes.
- Memory does not determine operation origin.

---

## Summary

The memory read/write protocol is defined entirely at the memory interface.

A valid read uses {MFB, AB} to select a word and drives that word onto MDB. A valid write uses {MFB, AB} to select a word and stores the 12-bit value presented on MDB.