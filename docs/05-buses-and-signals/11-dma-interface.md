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

## Request Interface

DMA-capable controllers request service through:

```text
DMA_REQ[15:0]
```

Each DMA-capable controller asserts exactly one configured priority-channel request.

The DMA arbiter produces the aggregate CPU-facing request:

```text
DMA_REQ
```

The aggregate request identifies only that DMA service is pending. It does not identify an individual controller.

## CPU Authorization

CPU control asserts the CPU-facing signal:

```text
DMA_GRANT
```

`DMA_GRANT` indicates that the CPU is in `MS = DMA` and has released CPU ownership of the memory interface.

CPU-facing `DMA_GRANT` does not identify the selected DMA controller.

## Controller Selection

The DMA arbiter presents:

```text
DMA_GRANT_ID[3:0]
```

A DMA-capable controller accepts ownership only when:

```text
DMA_GRANT
AND
(DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY)
```

Exactly one controller may accept an active grant.

## Transport Participation

The granted DMA controller supplies:

- `MFB[2:0]`
- `AB[11:0]`
- RD or WR
- `MDB[11:0]` for a DMA write to memory

Memory supplies MDB for a DMA read from memory.

## Memory Read

A DMA memory read transfers data from memory to the granted controller.

The granted controller:

- drives MFB
- drives AB
- asserts RD
- deasserts WR
- does not drive MDB

Memory drives MDB.

The granted controller captures MDB at TP2.

## Memory Write

A DMA memory write transfers data from the granted controller to memory.

The granted controller:

- drives MFB
- drives AB
- asserts WR
- deasserts RD
- drives MDB

Memory captures MDB at TP2.

## Ownership

During DMA ownership:

- CPU control does not drive MFB, AB, MDB, RD, or WR.
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