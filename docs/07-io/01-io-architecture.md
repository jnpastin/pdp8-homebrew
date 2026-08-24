# I/O Architecture

## Purpose

This document defines the architectural participants, interfaces, and boundaries of the I/O subsystem.

## Architectural Participants

The I/O subsystem includes:

- CPU
- external I/O controllers
- DMA-capable controllers
- DMA arbiter
- memory subsystem

## External IOT Interface

External IOT execution uses:

- `IOT_ACTIVE`
- `IOA[5:0]`
- `IOP[2:0]`
- `DB[11:0]`
- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`
- `IO_WAIT`
- shared TS and TP timing signals

![I/O Subsystem Diagram](../../diagrams/io/io_subsystem/export/io_subsystem.png)

## Device Addressing

`IOA[5:0]` is the six-bit architectural device address.

Properties:

- Each external controller has one active configured address for each device interface it implements.
- Address assignment is independent of physical backplane position.
- A controller compatible with a DEC device defaults to the corresponding DEC device address when one is defined.
- A compatible controller may be configured to use another nonreserved address.
- A custom controller may use an arbitrary nonreserved address.
- The address configuration mechanism belongs to the physical implementation.
- Two installed controllers must not use the same active address.

A nondefault address may require corresponding software or handler changes. Address configurability does not alter the required operation semantics of a controller claiming compatibility with a DEC device.

## I/O Operation Field

`IOP[2:0]` carries `IR[2:0]` unchanged during an external IOT.

Properties:

- IOP is distinct from IOA.
- IOP semantics belong to the selected controller.
- A DEC-compatible controller reproduces the operation encoding and combined-operation behavior of the emulated controller.
- A custom controller may interpret IOP as independent function bits, an encoded operation, or a documented mixture.
- The conventional status, state-change, and transfer pattern is guidance rather than a system-wide requirement.

## External IOT Validity

`IOT_ACTIVE` identifies execution of an external IOT.

Controllers must interpret IOA, IOP, controller response signals, and IOT timing behavior only while `IOT_ACTIVE` is asserted.

IOA and IOP are not required to be cleared outside an external IOT.

## CPU-Visible Controller Responses

The selected controller may request the following CPU-visible actions:

- `IO_READ_REQ`: device-to-CPU DB transfer
- `IO_WRITE_REQ`: CPU-to-device DB transfer
- `IO_SKIP_REQ`: increment PC
- `IO_CLEAR_AC_REQ`: clear AC

Controller-local state changes do not require a separate CPU response signal. They are defined by the controller and committed at the assigned TP.

## DMA Boundary

DMA arbitration is external to CPU control.

The CPU observes only the aggregate DMA request. The external DMA arbiter selects a controller and manages controller-facing grant identity, burst limits, and re-arbitration.

During DMA, the granted controller directly participates in the memory interface and supplies the operation-specific memory-facing signals defined in [DMA Interface](./05-dma-interface.md).

## Related Documents

- [External IOT Interface](./02-external-iot-interface.md)
- [I/O Timing](./03-io-timing.md)
- [Controller Contract](./04-controller-contract.md)
- [DMA Interface](./05-dma-interface.md)
- [DMA Arbitration](./06-dma-arbitration.md)
