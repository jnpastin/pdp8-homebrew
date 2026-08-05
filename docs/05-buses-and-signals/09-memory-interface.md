# 09 Memory Interface

## Purpose

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

## Memory Interface Participants

Memory communication involves:

- CPU
- Memory
- AB
- MDB
- RD
- WR

### Address Domain

The Address Domain provides the address associated with a memory operation.

This domain is represented by:

- AB

### Memory Data Domain

The Memory Data Domain provides the data associated with a memory operation.

This domain is represented by:

- MDB

### Control Interface

Memory operations are identified by:

- RD
- WR

Control behavior is defined in:

- [Control Model](../04-control/01-control-model.md)
- [Architectural Control Signals](../04-control/20-control-output-definitions/02-architectural-control-signals.md)

---

## Memory Read Model

A memory read transfers data from memory to the CPU.

### Address Domain Participation

During a memory read:
- The CPU drives AB from MA.
- AB carries the address to memory.

### Memory Data Domain Participation

During a memory read:

- Memory is the MDB producer.
- The CPU is the MDB consumer.

MDB transports the value read from memory.

### Control Participation

RD identifies the operation as a memory read.

Control behavior and timing are defined elsewhere.

---

## Memory Write Model

A memory write transfers data from the CPU to memory.

### Address Domain Participation

During a memory read:
- The CPU drives AB from MA.
- AB carries the address to memory.

### Memory Data Domain Participation

During a memory write:

- The CPU is the MDB producer.
- Memory is the MDB consumer.

MDB transports the value written to memory.

The value presented to MDB is determined by the active operation.

Possible sources include:

- MB
- SR

Authoritative source-selection behavior is defined in:

- [Control Model](../04-control/01-control-model.md)
- [Microarchitectural Control Signals](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)

### Control Participation

WR identifies the operation as a memory write.

Control behavior and timing are defined elsewhere.

---

## Domain Participation

Memory operations use:

- Address Domain (AB)
- Memory Data Domain (MDB)

Domain definitions and isolation requirements are defined in:

- [Domain Boundaries](./07-domain-boundaries.md)

---

## Global Invariants
- AB participates in all memory operations.
- MDB participates in all memory operations.
- Memory is the MDB producer during memory reads.
- The CPU is the MDB producer during memory writes.
- During normal memory operations, the CPU drives AB from MA.
- During DMA, an external device drives AB; the CPU does not drive AB.
- RD identifies memory read operations.
- WR identifies memory write operations.
- Domain definitions, ownership behavior, timing behavior, and control semantics are defined elsewhere.

## Summary

The memory interface uses AB for address transport and MDB for data transport.

During memory reads, memory produces MDB data and the CPU consumes it. During memory writes, the CPU produces MDB data and memory consumes it. Control, timing, ownership, and DMA-specific behavior remain defined by their respective architectural documents.