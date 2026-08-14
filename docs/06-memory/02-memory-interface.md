# Memory Interface

## Purpose

This document defines the memory subsystem interface.

The memory interface is the boundary between the memory subsystem and the rest of the system. Memory observes address, field, control, and write-data signals at this boundary, and drives read data when a valid read operation is requested.

## Interface Signals

The memory subsystem interface consists of:

- MFB
- AB
- MDB
- RD
- WR

These signals define the complete memory-facing interface for normal memory operations.

## Signal Roles

### MFB

MFB provides the memory field value.

From the memory subsystem perspective, MFB is an input.

Memory does not determine the source of MFB. Memory only observes the field value presented on MFB during a memory operation.

### AB

AB provides the 12-bit address value within the selected memory field.

From the memory subsystem perspective, AB is an input.

Memory does not determine the source of AB. Memory only observes the address value presented on AB during a memory operation.

### MDB

MDB is the memory data bus.

MDB is bidirectional from the memory subsystem perspective:

- during a read, memory drives MDB
- during a write, memory observes MDB
- when memory is not driving read data, memory must not drive MDB

Only one source may drive MDB during any valid memory operation.

### RD

RD requests a memory read.

From the memory subsystem perspective, RD is an input.

When RD is asserted as part of a valid read operation, memory uses MEM_ADDR to select a word and drives the selected 12-bit value onto MDB.

RD does not define CPU-side capture behavior. It only defines the memory-side read request.

### WR

WR requests a memory write.

From the memory subsystem perspective, WR is an input.

When WR is asserted as part of a valid write operation, memory uses MEM_ADDR to select a word and stores the 12-bit value presented on MDB.

WR does not define the source of write data. It only defines the memory-side write request.

## Memory Address Formation

The memory subsystem forms its memory selection value from MFB and AB.

MEM_ADDR = {MFB, AB}

MFB and AB must be valid and stable for the duration required by the active memory operation.

The memory subsystem does not inspect the source or history of either signal.

## Read Direction

During a valid read operation:

- MFB is observed by memory
- AB is observed by memory
- RD is asserted
- WR is not asserted
- memory drives MDB with the selected 12-bit word

Memory is the MDB driver during the read data phase.

## Write Direction

During a valid write operation:

- MFB is observed by memory
- AB is observed by memory
- WR is asserted
- RD is not asserted
- MDB is driven by a source outside the memory subsystem
- memory stores the 12-bit value present on MDB

Memory is not the MDB driver during a write.

## Idle Behavior

When no valid memory operation is active:

- memory does not modify stored contents
- memory does not drive MDB
- memory does not interpret MFB or AB as a completed memory operation

MFB and AB may have values while memory is idle, but those values do not cause memory behavior without an active memory operation.

## Source Independence

The memory subsystem does not distinguish between CPU-initiated, DMA-initiated, or console-initiated memory operations.

From the memory subsystem perspective, a valid operation is defined only by the memory interface signals:

- MEM_ADDR
- RD or WR
- MDB direction and data validity

The origin of the operation is outside the memory subsystem boundary.

## Invalid Interface Conditions

The following conditions are invalid unless explicitly defined elsewhere:

- RD and WR asserted at the same time
- RD asserted while memory is not allowed to drive MDB
- WR asserted without valid write data on MDB
- more than one source driving MDB
- no source driving MDB during a write
- unstable MFB during an active memory operation
- unstable AB during an active memory operation
- memory driving MDB during a write
- memory driving MDB while no read operation is active

Invalid interface conditions are design errors.

## Invariants

- MFB is an input to memory.
- AB is an input to memory.
- RD is an input to memory.
- WR is an input to memory.
- MDB is driven by memory only during reads.
- MDB is observed by memory during writes.
- Memory uses MEM_ADDR = {MFB, AB} to select a word.
- Memory does not choose the source of MFB, AB, MDB, RD, or WR.
- Memory does not distinguish CPU, DMA, or console access origins.
- Memory behavior occurs only through the defined memory interface.

## Summary

The memory interface consists of MFB, AB, MDB, RD, and WR.

Memory observes MFB and AB to form MEM_ADDR. On reads, memory drives MDB with the selected word. On writes, memory observes MDB and stores the presented word. The memory subsystem does not decide where the interface values came from.