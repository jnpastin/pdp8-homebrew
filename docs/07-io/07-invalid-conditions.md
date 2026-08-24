# I/O Invalid Conditions

## Purpose

This document identifies architectural I/O and DMA conditions that are design errors.

## External IOT Invalid Conditions

The following are invalid:

- duplicate active IOA addresses
- more than one controller responding to the same external IOT
- a nonselected controller asserting a response
- a nonselected controller changing local state because of the IOT
- a response asserted outside `IOT_ACTIVE`
- simultaneous `IO_READ_REQ` and `IO_WRITE_REQ`
- more than one DB producer
- CPU driving DB during an I/O read
- a controller driving DB during an I/O write
- an I/O read without valid controller data
- an I/O write without valid CPU data
- read and AC clear committing at the same TP
- a phase-specific response unintentionally causing actions at multiple TPs
- a TP action depending on a result committed at that same TP
- `IO_SKIP_REQ` based on unregistered or unstable controller state
- `IO_WAIT` asserted by a nonselected controller
- `IO_WAIT` suppressing, extending, or repeating a TP
- more than one TSTEP increment on one TCLK rising edge

## DMA Invalid Conditions

The following are invalid:

- duplicate active DMA priority channels
- more than one controller accepting the same grant
- a controller driving DMA-owned interfaces without a matching active grant
- CPU and DMA controller driving the same interface concurrently
- RD and WR asserted together
- MFB changing during an active DMA memory operation
- AB changing during an active DMA memory operation
- no valid MDB producer during a DMA write
- more than one MDB producer
- memory driving MDB during a DMA write
- a DMA controller driving MDB during a DMA read
- grant identity changing during an active grant
- preemption of an active grant
- grant withdrawal before RD and WR are inactive and bus ownership is released
- arbiter burst count changing outside TP3
- controller operation state changing outside TP
- a controller exceeding the arbiter-enforced burst boundary
- CPU ownership resuming before DMA ownership ends
- a controller configured with DMA priority 15
- a controller accepting DMA ownership while DMA_GRANT_ID is 15
- a controller accepting DMA ownership while DMA_GRANT is deasserted
- a controller driving DMA-owned interfaces when DMA_GRANT_ID does not match its configured priority
- DMA_GRANT_ID containing a value other than 15 when no controller is selected
- a configured DMA burst limit of zero
- a controller asserting DMA_REQ[n] without being prepared to complete the next DMA word transfer
- a selected controller failing to complete exactly one DMA word transfer at TP2
- DMA address, remaining-word-count, or burst-count state updating at TP3 without a corresponding transfer completed at TP2
- a selected controller releasing before completing the current TP2 transfer
- a controller attempting to delay, suppress, repeat, or extend a DMA TP

## Validation Boundary

These conditions are architectural design errors.

The architecture does not require centralized runtime validation of controller compliance. Optional diagnostics may detect violations, but diagnostic behavior must not participate in normal control, timing, ownership, or sequencing.

## Related Documents

- [External IOT Interface](./02-external-iot-interface.md)
- [I/O Timing](./03-io-timing.md)
- [Controller Contract](./04-controller-contract.md)
- [DMA Interface](./05-dma-interface.md)
- [DMA Arbitration](./06-dma-arbitration.md)
