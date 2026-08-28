# Memory Interface

## 1. Purpose

This document defines the architectural interface used for memory communication.

This document defines:

- memory interface participants
- address-domain participation
- memory-data-domain participation
- memory read operations
- memory write operations

This document does NOT define:

- timing behavior
- ownership behavior
- control signal semantics
- microarchitectural implementation
- DMA-specific memory operations

Bus semantics are defined in:

- [Bus Semantics](./06-bus-semantics.md)

Ownership is defined in:

- [Bus Ownership Matrix](./08-ownership-matrix.md)

DMA-specific behavior is defined in:

- [DMA Interface](./11-dma-interface.md)

---

## 2. Memory Interface Participants

Memory communication involves:

- CPU
- Memory
- AB
- MDB
- /RD
- /WR

### 2.1 Address Domain

The Address Domain provides the address associated with a memory operation.

This domain is represented by:

- AB

### 2.2 Memory Data Domain

The Memory Data Domain provides the data associated with a memory operation.

This domain is represented by:

- MDB

### 2.3 Control Interface

Memory operations are identified by:

- /RD
- /WR

Control behavior is defined in:

- [Control Model](../04-control/01-control-model.md)
- [Architectural Control Signals](../04-control/20-control-output-definitions/02-architectural-control-signals.md)

---

## 3. Memory Read Model

A memory read transfers data from memory to the CPU.

### 3.1 Address Domain Participation

During a memory read:
- The CPU drives AB from MA.
- The CPU drives MFB from EA_FIELD (IF or DF per MFB_SRC).
- AB and MFB together carry the physical address to memory.

### 3.2 Memory Data Domain Participation

During a memory read:

- Memory is the MDB producer.
- The CPU is the MDB consumer.

MDB transports the value read from memory.

### 3.3 Control Participation

/RD identifies the operation as a memory read.

Control behavior and timing are defined elsewhere.

---

## 4. Memory Write Model

A memory write transfers data from the CPU to memory.

### 4.1 Address Domain Participation

During a memory write:
- The CPU drives AB from MA.
- The CPU drives MFB from EA_FIELD (IF or DF per MFB_SRC).
- AB and MFB together carry the physical address to memory.

### 4.2 Memory Data Domain Participation

During a memory write:

- The CPU is the MDB producer.
- Memory is the MDB consumer.

MDB transports the value written to memory.

The value presented to MDB is determined by the active operation.

Possible sources include:

- MB
- FP_SR

Authoritative source-selection behavior is defined in:

- [Control Model](../04-control/01-control-model.md)
- [Microarchitectural Control Signals](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)

### 4.3 Control Participation

/WR identifies the operation as a memory write.

Control behavior and timing are defined elsewhere.

---

## 5. Domain Participation

Memory operations use:

- Address Domain (AB)
- Memory Data Domain (MDB)

Domain definitions and isolation requirements are defined in:

- [Domain Boundaries](./07-domain-boundaries.md)

---

## 6. Global Invariants
- AB participates in all memory operations.
- MFB participates in all memory operations.
- MDB participates in all memory operations.
- Memory is the MDB producer during memory reads.
- The CPU is the MDB producer during memory writes.
- During normal memory operations, the CPU drives AB from MA and MFB from EA_FIELD.
- During DMA, an external device drives AB and MFB; the CPU drives neither.
- AB and MFB together form the physical memory address: {MFB, AB} = {F[2:0], A[11:0]}.
- /RD identifies memory read operations.
- /WR identifies memory write operations.
- Domain definitions, ownership behavior, timing behavior, and control semantics are defined elsewhere.

---

## 7. Summary

The memory interface uses AB for address transport and MDB for data transport.

During memory reads, memory produces MDB data and the CPU consumes it. During memory writes, the CPU produces MDB data and memory consumes it. Control, timing, ownership, and DMA-specific behavior remain defined by their respective architectural documents.