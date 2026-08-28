# I/O Interface

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

- [Bus Ownership Matrix](./08-ownership-matrix.md)

DMA-specific behavior is defined in:

- [DMA Interface](./11-dma-interface.md)

---

## I/O Interface Participants

External IOT communication involves:

- CPU
- selected I/O controller
- `IOT_ACTIVE`
- `IOA[5:0]`
- `IOP[2:0]`
- DB
- `/DB_READ`
- `/DB_WRITE`
- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`
- `/IO_WAIT`
- shared TS signals
- shared TP signals

---

## I/O Selection Interface

`IOA[5:0]` identifies the target external controller.

`IOP[2:0]` identifies the controller-defined operation.

IOA and IOP are distinct interfaces and remain stable throughout external-IOT EXECUTE.

IOA and IOP are meaningful to controllers only while `IOT_ACTIVE` is asserted.

### Controller Response Interface

The selected controller may assert:

- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`
- `/IO_WAIT`

Controller responses request CPU behavior. They do not directly modify CPU state.

`IO_CLEAR_AC_REQ` and `IO_SKIP_REQ` request CPU state changes at the immediately following TP.

`IO_READ_REQ` and `IO_WRITE_REQ` request a DB transfer during the following phase. CPU control accepts the request at the TP following the request phase and asserts `/DB_READ` or `/DB_WRITE` during the next TS.

Responses must satisfy the timing and combination constraints defined in the [External IOT Interface](../07-io/02-external-iot-interface.md).

---

## I/O Read Model

An I/O read transfers data from the selected controller to the CPU.

During the request phase:

- the CPU provides `IOA` and `IOP`
- the selected controller asserts `IO_READ_REQ`
- CPU control accepts the request at the following TP
- the selected controller does not drive DB because of the pending read

During the following transfer phase:

- CPU control asserts `/DB_READ`
- the selected controller is the DB producer
- the CPU is the DB consumer
- the selected controller drives valid data onto DB

At the following TP:

```text
AC <- AC OR DB
```

The transfer commits through `DB_READ_TO_AC`.

---

## I/O Write Model

An I/O write transfers data from the CPU to the selected controller.

During the request phase:

- the CPU provides `IOA` and `IOP`
- the selected controller asserts `IO_WRITE_REQ`
- CPU control accepts the request at the following TP

During the following transfer phase:

- CPU control asserts `/DB_WRITE`
- the CPU is the DB producer
- the selected controller is the DB consumer
- the CPU drives AC onto DB

At the following TP, the selected controller captures DB.

### Global Invariants

- `IOA` and `IOP` are distinct controller-facing fields.
- `IOA` and `IOP` are meaningful only while `IOT_ACTIVE` is asserted.
- Controller responses are phase-specific.
- Only the address-matched controller may respond.
- `/DB_READ` and `/DB_WRITE` are CPU control outputs describing the active DB transfer.
- `IO_READ_REQ` and `IO_WRITE_REQ` are mutually exclusive.
- `IO_READ_REQ` and `IO_WRITE_REQ` are accepted at the TP following their request phase.
- `/DB_READ` and `/DB_WRITE` are asserted during the subsequent transfer phase.
- The associated DB transfer commits at the TP following the transfer phase.
- Only one source may drive DB.
- Controller response signals do not directly modify CPU state.
- All CPU and controller state changes occur only at TP.
- I/O wait behavior is defined in [I/O Timing](../07-io/03-io-timing.md).

---

## Summary

The I/O interface uses IOA for device selection and DB for data transport.

During I/O reads, the selected I/O device produces DB data and the CPU consumes it. During I/O writes, the CPU produces DB data and the selected I/O device consumes it. Control, timing, ownership, and DMA-specific behavior remain defined by their respective architectural documents.