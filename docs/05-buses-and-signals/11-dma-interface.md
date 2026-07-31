# 11 DMA Interface

## Purpose

This document defines the architectural interface used for Direct Memory Access (DMA) operations.

This document defines:

- DMA interface participants
- DMA request and grant behavior
- DMA participation in transport domains
- DMA memory read operations
- DMA memory write operations

This document does NOT define:

- DMA arbitration
- timing behavior
- ownership timing
- control signal semantics
- microarchitectural implementation

Bus semantics are defined in:

- [Bus Semantics](./06-bus-semantics.md)

Ownership is defined in:

- [Bus Ownership Matrix](./08-bus-ownership-matrix.md)

Memory arbitration is defined in Section 6.

---

## DMA Interface Participants

DMA operations involve:

- DMA Device
- CPU
- Memory
- AB
- MDB
- DMA_REQ
- DMA_GRANT

---

## DMA Request Model

A device requests DMA service by asserting DMA_REQ.

DMA_REQ indicates that the requesting device requires direct access to the memory interface.

DMA request behavior is defined by the control architecture.

---

## DMA Grant Model

DMA service is initiated by DMA_GRANT.

DMA_GRANT indicates that a requesting DMA device has been granted access to the memory interface.

Selection of the granted device is determined by memory arbitration.

This document does not define arbitration behavior.

---

## CPU Participation

DMA operations bypass the CPU datapath.

During DMA operation:

- the CPU is not an active participant in the DMA transfer
- DMA accesses memory without CPU data movement
- memory communication occurs directly between the DMA device and memory

CPU interaction with DMA is limited to DMA coordination.

---

## Domain Participation

DMA operations use:

- Address Domain (AB)
- Memory Data Domain (MDB)

Domain definitions are maintained in:

- [Domain Boundaries](./07-domain-boundaries.md)

DMA devices participate directly in the Memory Data Domain.

DMA operations do not require a DB-to-MDB domain crossing.

---

## DMA Memory Read Model

A DMA memory read transfers data from memory to a DMA device.

### Address Domain Participation

During a DMA memory read:

- The DMA device provides the memory address.

### Memory Data Domain Participation

During a DMA memory read:

- Memory is the MDB producer.
- The DMA device is the MDB consumer.

MDB transports the value read from memory.

### Control Participation

DMA_GRANT indicates that DMA memory access is authorized.

Control behavior is defined in Section 4.

---

## DMA Memory Write Model

A DMA memory write transfers data from a DMA device to memory.

### Address Domain Participation

During a DMA memory write:

- The DMA device provides the memory address.

### Memory Data Domain Participation

During a DMA memory write:

- The DMA device is the MDB producer.
- Memory is the MDB consumer.

MDB transports the value written to memory.

DMA devices participate directly in the MDB ownership model.

Authoritative ownership behavior is defined in:

- [Bus Ownership Matrix](./08-bus-ownership-matrix.md)
- [Microarchitectural Control Signals](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)

### Control Participation

DMA_GRANT indicates that DMA memory access is authorized.

Control behavior is defined elsewhere.

---

## Relationship to Memory Arbitration

Multiple DMA devices may request service simultaneously.

Selection of the DMA device granted memory access is determined by memory arbitration.

This document does not define arbitration behavior.

---

## Global Invariants

- DMA operations use AB.
- DMA operations use MDB.
- DMA devices participate directly in the Memory Data Domain.
- DMA operations do not require a DB-to-MDB domain crossing.
- Memory is the MDB producer during DMA memory reads.
- DMA devices are the MDB producer during DMA memory writes.
- DMA devices provide memory addresses during DMA operations.
- DMA_REQ requests DMA service.
- DMA_GRANT authorizes DMA service.
- Arbitration behavior is defined separately.

## Summary

DMA provides direct memory access between DMA devices and memory.

DMA operations use AB for address transport and MDB for data transport. DMA devices participate directly in the Memory Data Domain and exchange data with memory without CPU data movement.