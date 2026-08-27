# DMA Interface

## Purpose

This document defines the architectural signals used for DMA communication among DMA-capable controllers, the external DMA arbiter, CPU control, and memory.

DMA arbitration and transfer sequencing are defined in:

- [DMA Arbitration](../07-io/06-dma-arbitration.md)
- [DMA Interface Timing](../07-io/05-dma-interface.md)

## Participants

DMA operations involve:

- CPU control
- external DMA arbiter
- one granted DMA controller
- memory

The DMA arbiter observes:

- `MS[2:0]`
- shared TS signals
- shared TP signals

The arbiter uses this timing context to update its internal arbitration state. Observing `MS` does not authorize bus ownership or permit a controller to drive DMA-owned interfaces.

## Request Interface

DMA-capable controllers request service through /DMA_REQ[14:0].  
The request interface provides 15 configurable DMA priority-channel request lines.  
Each DMA-capable controller asserts exactly one configured request line.  
Valid configured DMA priorities are 0 through 14.  
DMA priority 15 is reserved as the no-controller-selected encoding and has no corresponding /DMA_REQ line.

The DMA arbiter produces the combinational `DMA_ENABLE` qualification output.

Separate combinational aggregation logic derives the aggregate CPU-facing request:

```text
/DMA_REQ =
    NOT (
        DMA_ENABLE
        AND
        ANY_CONTROLLER_REQUEST_ASSERTED
    )
```

The aggregate request identifies only that DMA service is eligible and pending. It does not identify an individual controller.

/DMA_REQ[n], DMA_ENABLE, and aggregate /DMA_REQ must settle before the TP at which CPU control samples aggregate /DMA_REQ.

## CPU Authorization

CPU control asserts /DMA_GRANT.  
/DMA_GRANT indicates that the CPU is in MS = DMA and has released CPU ownership of the memory interface.  
/DMA_GRANT does not identify the selected DMA controller.  
/DMA_GRANT is produced by the CPU and is observed by the DMA arbiter and DMA-capable controllers.

## Controller Selection

The DMA arbiter presents DMA_GRANT_ID[3:0].

DMA_GRANT_ID values have the following meanings:

- 0 through 14: selected DMA priority channel
- 15: no controller selected

A DMA-capable controller accepts ownership only when:

```text
/DMA_GRANT = 0
AND
DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

A controller DMA priority must be in the range 0 through 14.  
No /DMA_REQ line exists for priority 15.  
No controller accepts ownership while DMA_GRANT_ID is 15.  
Exactly one controller may accept a valid controller selection.

## Transport Participation

The granted DMA controller supplies:

- `MFB[2:0]`
- `AB[11:0]`
- /RD or /WR
- `MDB[11:0]` for a DMA write to memory

Memory supplies MDB for a DMA read from memory.

## Memory Read

A DMA memory read transfers data from memory to the granted controller.

The granted controller:

- drives MFB
- drives AB
- asserts /RD
- deasserts /WR
- does not drive MDB

Memory drives MDB.

The granted controller captures MDB at TP2.

## Memory Write

A DMA memory write transfers data from the granted controller to memory.

The granted controller:

- drives MFB
- drives AB
- asserts /WR
- deasserts /RD
- drives MDB

Memory captures MDB at TP2.

## Ownership

During DMA ownership:

- CPU control does not drive MFB, AB, MDB, /RD, or /WR.
- Only the granted controller may drive DMA-owned controller outputs.
- Memory is the sole MDB producer during a DMA read.
- The granted controller is the sole MDB producer during a DMA write.
- CPU and DMA ownership must not overlap.

## Arbitration Boundary

The CPU does not select among DMA-capable controllers.

Memory does not arbitrate among DMA-capable controllers.

Requester selection, fixed priority, bounded bursts, grant identity, CPU fairness, and re-arbitration are defined in [DMA Arbitration](../07-io/06-dma-arbitration.md).

## Related Documents

- [Bus Ownership Matrix](./08-ownership-matrix.md)
- [Domain Boundaries](./07-domain-boundaries.md)
- [Memory Interface](../06-memory/02-memory-interface.md)
- [DMA Interface](../07-io/05-dma-interface.md)
- [DMA Arbitration](../07-io/06-dma-arbitration.md)