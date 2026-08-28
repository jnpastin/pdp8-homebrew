# Memory

## 1. Purpose

This section defines the memory subsystem.

The memory subsystem is a bounded storage component that stores 12-bit words and responds to memory operations presented at the memory interface.

---

## 2. Scope

Section 6 defines:

- the logical memory model
- the memory subsystem interface
- read and write behavior
- memory timing requirements
- field interpretation at the memory boundary
- DMA and console access from the memory perspective
- implementation constraints for physical memory technology

Section 6 does not define:

- instruction semantics
- effective-address generation
- CPU register behavior
- micro-operation sequencing
- control-store behavior
- timing-generator behavior
- I/O device behavior
- DMA sequencing or arbitration
- physical backplane implementation

---

## 3. Model Summary

Memory is addressed through the memory-facing address term MEM_ADDR.

MEM_ADDR is local to Section 6 and is defined as:

MEM_ADDR = {MFB, AB}

Where:

- MFB provides the memory field value
- AB provides the 12-bit address value

MEM_ADDR describes what memory observes at its interface. It is not a replacement for EA and is not a general system-wide address term.

---

## 4. Interface Summary

The memory subsystem interface consists of:

- MFB
- AB
- MDB
- /RD
- /WR

Memory observes MFB and AB to select a word.

During a read, memory drives MDB.

During a write, memory observes MDB.

---

## 5. Technology Independence

The logical memory model is independent of physical memory technology.

The memory subsystem may be implemented using SRAM, MRAM, FRAM, nvSRAM, battery-backed SRAM, or another suitable technology, provided the implementation satisfies the memory-interface behavior defined in this section.

---

## 6. Contents

- [Memory Model](./01-memory-model.md)
- [Memory Interface](./02-memory-interface.md)
- [Read/Write Protocol](./03-read-write-protocol.md)
- [Memory Timing](./04-memory-timing.md)
- [Memory Field Selection](./05-memory-field-selection.md)
- [DMA & Console Access](./06-dma-and-console-access.md)
- [Implementation Constraints](./07-implementation-constraints.md)

---

## 7. Invariants

- Memory stores 12-bit words.
- Memory is addressed through MEM_ADDR.
- MEM_ADDR is defined only as {MFB, AB}.
- MEM_ADDR is local to Section 6.
- Memory does not interpret instruction bits.
- Memory does not choose field, address, data, or control sources.
- Memory drives MDB only during valid reads.
- Memory observes MDB during valid writes.
- Memory behavior is independent of access origin.
- Physical implementation must not change logical memory behavior.

---

## 8. Summary

Section 6 defines memory as a technology-independent storage subsystem.

It specifies how memory behaves when presented with a field, address, data, and read/write control. It does not define how the rest of the system produces those values.
