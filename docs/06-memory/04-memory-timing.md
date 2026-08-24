# Memory Timing

## Purpose

This document defines the timing contract at the memory subsystem boundary.

It describes when memory interface signals must be stable and how /RD and /WR define active memory operation windows.

## Timing Boundary

The memory subsystem does not generate timing states or timing pulses.

The timing system determines when memory interface signals are asserted, sampled, or deasserted. The memory subsystem only observes the resulting memory interface signals.

## Active Read Window

/RD defines the active read window.

During a valid read operation, while /RD is asserted:

- MFB must remain stable
- AB must remain stable
- memory must drive MDB
- MDB must represent the word selected by MEM_ADDR

When /RD is not asserted, memory must not drive MDB.

## Active Write Window

/WR defines the active write window.

During a valid write operation, while /WR is asserted:

- MFB must remain stable
- AB must remain stable
- MDB must contain valid write data
- memory must observe MDB as the value to be stored at MEM_ADDR

When /WR is not asserted, memory must not perform a write.

## Address Stability

MFB and AB together define MEM_ADDR.

For any valid read or write operation, MFB and AB must remain stable for the entire active operation window.

If MFB or AB changes while /RD or /WR is asserted, the memory operation is invalid.

## Read Data Stability

During a valid read operation, memory must drive MDB with the value stored at M[MEM_ADDR] while /RD is asserted and MEM_ADDR remains stable.

Memory is not required to preserve MDB after /RD is deasserted.

## Write Data Stability

During a valid write operation, MDB must contain the value to be stored while /WR is asserted.

The memory subsystem stores the value presented on MDB at the selected MEM_ADDR.

If MDB changes during the active write window, the write operation is invalid unless explicitly defined elsewhere.

## Mutual Exclusion

/RD and /WR must not be asserted at the same time.

A memory operation is either:

- a read
- a write
- idle

No combined read/write memory operation is defined.

## Idle Timing

When /RD and /WR are both deasserted:

- memory performs no read
- memory performs no write
- memory must not drive MDB
- changes on MFB or AB do not by themselves cause memory behavior

## Technology Timing Requirements

The selected physical memory technology must satisfy the timing contract defined by this section.

Technology-specific timing parameters, such as access time, output enable delay, write pulse width, setup time, and hold time, are implementation constraints. They must be chosen so that the logical memory behavior remains valid at the system timing rate.

## Invariants

- /RD defines the active read window.
- /WR defines the active write window.
- MFB must remain stable during an active memory operation.
- AB must remain stable during an active memory operation.
- MDB must be valid during an active write window.
- Memory drives MDB only during an active read window.
- Memory does not drive MDB when /RD is deasserted.
- /RD and /WR must not be asserted together.
- Timing implementation details must not change the logical memory model.

## Summary

Memory timing is defined at the memory interface.

/RD controls when memory drives read data. /WR controls when memory stores write data. MFB and AB must remain stable for the active operation window, and MDB direction is determined by whether the operation is a read or a write.