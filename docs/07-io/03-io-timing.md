# I/O Timing

## Purpose

This document defines external-IOT phase usage, TP commit rules, controller timing participation, and I/O wait behavior.

## Shared Timing Interface

TS and TP signals are exposed to external controllers through the I/O interface.

Controllers use the shared TP events directly. Dedicated I/O commit strobes are not defined.

All controller-local state changes caused by an IOT occur only at TP events.

## IOT Phase Allocation

### TS1: Selection and Decode

During TS1:

- `IOT_ACTIVE` is asserted
- IOA is valid
- IOP is valid
- controllers evaluate address match
- the selected controller decodes IOP
- no controller action commits at TP1

TS1 is the I/O selection and operation-decode phase.

### TS2 through TS4: Execution

The selected controller may request actions during TS2, TS3, or TS4, subject to the constraints in [External IOT Interface](./02-external-iot-interface.md).

A response asserted during TS2 commits at TP2. A response asserted during TS3 commits at TP3. A response asserted during TS4 commits at TP4.

## TP4 Sequencing Boundary

Device actions may commit at TP4 while CPU sequencing and interrupt decisions also commit at TP4.

Constraints:

- TP4 sequencing and interrupt decisions must depend only on state and inputs available at completion of TP3.
- A controller result committed at TP4 cannot affect the sequencing or interrupt decision committed at TP4.
- A controller may assert INT_REQ during TS4 when the assertion depends only on state available at completion of TP3.
- DB ownership must end before ownership changes for the following major state.

## I/O Wait

`IO_WAIT` extends an IOT setup interval for a slower selected controller.

Properties:

- `IO_WAIT` is distinct from RUN.
- MCLK continues while `IO_WAIT` is asserted.
- TCLK continues while `IO_WAIT` is asserted.
- `IO_WAIT` may inhibit TSTEP advancement only at non-TP setup TSTEPs.
- `IO_WAIT` is ignored when the current TSTEP is a TP position.
- A TP cannot be extended, repeated, or suppressed by `IO_WAIT`.
- The selected controller is contractually responsible for qualifying `IO_WAIT` with `IOT_ACTIVE` and address match.

## TSTEP Progression Requirement

TSTEP transition logic must:

- evaluate the pre-edge TSTEP value
- use mutually exclusive transition branches
- perform at most one TSTEP increment per TCLK rising edge
- hold the current non-TP TSTEP while `IO_WAIT` is asserted
- advance normally when `IO_WAIT` is deasserted
- advance through a TP position independently of `IO_WAIT`

## Stability During Wait

While a non-TP TSTEP is held by `IO_WAIT`, all signals required for the pending operation must remain stable, including:

- `IOT_ACTIVE`
- IOA
- IOP
- applicable controller response intent
- DB ownership and source selection when already active
- controller data required by the pending operation

## Synchronization Boundary

The physical implementation must synchronize `IO_WAIT` before it influences TSTEP progression. The controller contract must prevent asynchronous state changes or repeated commit events.

## Related Documents

- [Timing Architecture](../09-timing/02-timing-architecture.md)
- [External IOT Interface](./02-external-iot-interface.md)
- [Controller Contract](./04-controller-contract.md)
