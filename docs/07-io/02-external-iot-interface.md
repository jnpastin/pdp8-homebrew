# External IOT Interface

## Purpose

This document defines external-IOT selection, response qualification, DB transfer behavior, AC behavior, and skip behavior.

## Selection

A controller is selected when all of the following are true:

```text
IOT_ACTIVE = 1
IOA[5:0] = CONTROLLER_ADDRESS
```

Only the selected controller may interpret IOP as an active operation.

## Phase-Specific Responses

Controller responses are phase-specific.

A response asserted during a TS requests exactly one action at the following TP. A controller must assert a response again during a later TS if another action is required at a later TP.

Responses must not persist across phases unless the controller intentionally requests an action in each phase.

## I/O Read

`IO_READ_REQ` requests a device-to-CPU transfer.

Qualification requires:

- the controller is selected
- IOP identifies a read operation
- the controller has valid data available for the current phase
- `IO_WRITE_REQ` is not asserted

During the active TS:

- the selected controller drives DB
- CPU control asserts `DB_READ`
- DB remains valid for the required setup and hold interval

At the following TP:

```text
AC <- AC OR DB
```

The read occurs through `DB_READ_TO_AC`. No direct DB transfer to another CPU register is defined.

## I/O Write

`IO_WRITE_REQ` requests a CPU-to-device transfer.

Qualification requires:

- the controller is selected
- IOP identifies a write operation
- the controller can accept data during the current phase
- `IO_READ_REQ` is not asserted

During the active TS:

- CPU control asserts `DB_WRITE`
- the CPU drives AC onto DB
- DB remains valid for the required setup and hold interval

At the following TP, the selected controller captures DB.

## AC Clear

`IO_CLEAR_AC_REQ` requests AC clear at the following TP.

Rules:

- Clear and read must not commit at the same TP because both write AC.
- Clear and write may commit at the same TP.
- For a same-TP write and clear, the device captures the pre-TP AC value from DB and AC clears at that TP.
- An earlier clear followed by a later read produces clear-then-OR behavior.
- AC clear is permitted at TP2, TP3, or TP4 when the selected controller defines that operation.

## Skip

`IO_SKIP_REQ` is valid only during TS4 and causes `PC_INC` at TP4.

Qualification requires:

- the controller is selected
- IOP identifies the controller's skip operation
- the controller's registered skip condition is true.

Valid same-TP combinations include:

- skip alone
- skip and read
- skip and write
- skip and clear
- skip, write, and clear

Skip, read, and clear together are invalid because read and clear both write AC.

The controller never modifies PC directly.

## Same-TP Semantics

CPU and controller actions committed at the same TP use pre-TP state and commit simultaneously.

A result committed at a TP must not affect another decision or action committed at that same TP.

## Inactive Controllers

A controller that is not selected must:

- ignore IOP
- deassert all controller response signals
- not drive DB
- not capture DB
- not modify controller state because of the IOT
- not assert IO_WAIT because of the IOT

## Related Documents

- [I/O Architecture](./01-io-architecture.md)
- [I/O Timing](./03-io-timing.md)
- [Controller Contract](./04-controller-contract.md)
- [Invalid Conditions](./07-invalid-conditions.md)
