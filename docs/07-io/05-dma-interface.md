# DMA Interface

## Purpose

This document defines DMA ownership, memory-interface participation, transfer direction, and per-word timing.

## Architectural Model

DMA uses single-cycle transfer semantics.

The granted controller maintains:

- complete-operation memory field
- complete-operation memory address
- address progression
- remaining operation word count
- transfer direction
- controller-specific completion state

Each `MS = DMA` cycle transfers at most one memory word.

## DMA-Owned Interfaces

During a granted DMA operation, the controller supplies:

- `MFB[2:0]`
- `AB[11:0]`
- `RD` or `WR`
- `MDB[11:0]` during a write

During a DMA read, memory supplies MDB.

The CPU does not drive MFB, AB, MDB, RD, or WR during DMA ownership.

## Addressing

MFB and AB are treated as one DMA-selected memory address interface.

The granted controller supplies both values. MFB and AB must remain stable throughout the active RD or WR window.

## Direction

The granted controller asserts exactly one of RD or WR for a valid transfer.

### DMA Read

During a DMA read:

- controller drives MFB and AB
- controller asserts RD
- controller deasserts WR
- memory drives MDB
- controller captures MDB at TP2

### DMA Write

During a DMA write:

- controller drives MFB and AB
- controller asserts WR
- controller deasserts RD
- controller drives MDB
- memory stores MDB at TP2

## DMA Timing

### TS1 and TP1: Arbitration or Grant Continuation

If no controller-specific grant is active:

- the DMA arbiter evaluates pending requests during TS1
- it selects a winner
- the selected grant commits at TP1

If a controller-specific grant remains active for the current burst, TS1 preserves that grant and prepares the next transfer.

No memory transfer commits at TP1.

### TS2 and TP2: Memory Transfer

During TS2, the granted controller presents the complete memory operation.

At TP2:

- the memory transfer commits
- for a read, the controller captures MDB
- for a write, memory captures MDB

### TS3 and TP3: Count Update

At TP3:

- the controller updates its complete-operation address and remaining word count
- the DMA arbiter increments the active burst count.

These updates describe the word transferred at TP2.

### TS4 and TP4: Continuation Decision

During TS4, the DMA arbiter determines whether aggregate `DMA_REQ` remains asserted.

At TP4, CPU control commits:

```text
DMA_REQ = 1 -> MS_NEXT = DMA
DMA_REQ = 0 -> MS_NEXT = FETCH
```

The selected controller and arbiter prepare all grant-release and ownership-release decisions before TP4.

## DMA Wait Policy

No DMA wait signal is defined.

A controller should request DMA only when it can complete at least one memory transfer after grant. A controller unable to continue within an active burst releases the grant early and requests service again when ready.

## Related Documents

- [Memory Interface](../06-memory/02-memory-interface.md)
- [DMA and Console Memory Access](../06-memory/06-dma-and-console-access.md)
- [DMA Arbitration](./06-dma-arbitration.md)
- [Invalid Conditions](./07-invalid-conditions.md)
