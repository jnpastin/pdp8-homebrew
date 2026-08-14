# Controller Contract

## Purpose

This document defines the obligations common to all external I/O controllers.

## Address Configuration

Each controller must provide one active configured IOA address.

The architectural behavior does not depend on how that address is physically configured.

A DEC-compatible controller must default to the corresponding DEC device address when one is defined. Alternate addresses are permitted but may require software changes.

## Selection Qualification

Every controller action caused by an external IOT must be qualified by:

```text
IOT_ACTIVE
AND address match
AND decoded IOP behavior
AND assigned phase
```

A controller must not act on incidental IOA, IOP, TS, or TP values outside a selected external IOT.

## Response Qualification

The controller may assert:

- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`
- `IO_WAIT`

Each assertion must satisfy the definitions in [External IOT Interface](./02-external-iot-interface.md) and [I/O Timing](./03-io-timing.md).

## DB Ownership

For a read:

- only the selected controller drives DB
- the controller supplies valid data before the commit TP
- the controller releases DB after the required hold interval

For a write:

- the controller does not drive DB
- the controller captures the CPU-driven DB value at the commit TP

A controller must never drive DB while unselected.

## Controller-Local State

Controller-local state changes:

- are defined by the controller's IOT instruction set
- occur only at TP events
- are qualified by selection and decoded operation
- use pre-TP state
- commit simultaneously with CPU actions at the same TP
- do not depend on a result committed at the same TP

## Skip Condition

A controller requesting skip during TS4 must base `IO_SKIP_REQ` on the skip condition captured at TP3.

The controller may update or clear the underlying flag at TP4 while the CPU uses the TP3-captured condition for the TP4 skip decision.

## I/O Wait

A controller may assert `IO_WAIT` only:

- while selected
- while `IOT_ACTIVE` is asserted
- during a non-TP setup TSTEP
- when additional setup time is required before the next TP

The controller must deassert `IO_WAIT` when the pending operation is ready to proceed.

## DMA-Capable Controllers

A DMA-capable controller additionally must:

- use exactly one configured DMA priority channel
- assert only the corresponding request line
- recognize a grant only when `DMA_GRANT` is asserted and `DMA_GRANT_ID` matches its configured priority
- drive DMA-owned interfaces only while granted
- maintain its complete-operation address and remaining word count
- keep its request asserted while additional service remains pending
- tolerate grant termination at the configured arbiter burst boundary
- resume through normal re-arbitration

## Physical Implementation Boundary

The following are outside this architectural contract:

- address configuration technology
- DMA priority configuration technology
- burst-limit configuration technology
- electrical driver selection
- connector assignment
- controller-local counter widths
