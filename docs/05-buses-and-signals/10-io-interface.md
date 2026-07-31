# 10 I/O Interface

## Purpose

This document defines the architectural interface used for I/O communication.

This document defines:

- I/O interface participants
- I/O address participation
- I/O data domain participation
- I/O read operations
- I/O write operations

This document does NOT define:

- timing behavior
- ownership behavior
- control signal semantics
- microarchitectural implementation
- DMA-specific I/O operations

Bus semantics are defined in:

- [Bus Semantics](./06-bus-semantics.md)

Ownership is defined in:

- [Bus Ownership Matrix](./08-bus-ownership-matrix.md)

DMA-specific behavior is defined in:

- [DMA Interface](./11-dma-interface.md)

---

## I/O Interface Participants

I/O communication involves:

- CPU
- I/O Device
- IOA
- DB
- DB_READ
- DB_WRITE

## I/O Address Interface

The I/O Address Interface identifies the target I/O device associated with an I/O operation.

This interface is represented by:

- IOA

IOA definitions are maintained in:

- [Class B - Control](./02-class-b-control.md)

## I/O Data Domain

The I/O Data Domain provides the data associated with an I/O operation.

This domain is represented by:

- DB

Defined in:

- [Class A - Buses](./01-class-a-buses.md)

## Control Interface

I/O operations are identified by:

- DB_READ
- DB_WRITE

Control behavior is defined in Section 4.

---

## I/O Read Model

An I/O read transfers data from an I/O device to the CPU.

### I/O Address Participation

During an I/O read:

- The CPU provides the device address on IOA.

### I/O Data Domain Participation

During an I/O read:

- The I/O device is the DB producer.
- The CPU is the DB consumer.

DB transports the value provided by the selected I/O device.

### Control Participation

DB_READ identifies the operation as an I/O read.

Control behavior and timing are defined elsewhere.

---

## I/O Write Model

An I/O write transfers data from the CPU to an I/O device.

### I/O Address Participation

During an I/O write:

- The CPU provides the device address on IOA.

### I/O Data Domain Participation

During an I/O write:

- The CPU is the DB producer.
- The I/O device is the DB consumer.

DB transports the value written to the selected I/O device.

The value presented to DB is determined by the active operation.

Authoritative source-selection behavior is defined in Section 4.

### Control Participation

DB_WRITE identifies the operation as an I/O write.

Control behavior and timing are defined elsewhere.

---

## Domain Participation

I/O operations use:

- I/O Address Interface (IOA)
- I/O Data Domain (DB)

Domain definitions and isolation requirements are defined in:

- [Domain Boundaries](./07-domain-boundaries.md)

---

## Global Invariants

- IOA participates in all I/O operations.
- DB participates in all I/O operations.
- The CPU provides the I/O address for normal I/O operations.
- I/O devices are the DB producer during I/O reads.
- The CPU is the DB producer during I/O writes.
- DB_READ identifies I/O read operations.
- DB_WRITE identifies I/O write operations.
- Domain definitions, ownership behavior, timing behavior, and control semantics are defined elsewhere.

## Summary

The I/O interface uses IOA for device selection and DB for data transport.

During I/O reads, the selected I/O device produces DB data and the CPU consumes it. During I/O writes, the CPU produces DB data and the selected I/O device consumes it. Control, timing, ownership, and DMA-specific behavior remain defined by their respective architectural documents.