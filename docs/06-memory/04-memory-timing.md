# Memory Timing

## 1. Purpose

This document defines the timing contract at the memory subsystem boundary.

It describes when memory interface signals must be stable and how /RD and /WR define active memory operation windows.

---

## 2. Timing Boundary

The memory subsystem does not generate timing states or timing pulses.

The timing system determines when memory interface signals are asserted, sampled, or deasserted. The memory subsystem only observes the resulting memory interface signals.

---

## 3. Active Read Window

/RD defines the active read window.

During a valid read operation, while /RD is asserted:

- MFB must remain stable
- AB must remain stable
- memory must drive MDB
- MDB must represent the word selected by MEM_ADDR

When /RD is not asserted, memory must not drive MDB.

---

## 4. Active Write Window

/WR requests a write. [`/WR_PULSE`](../09-timing/01-terminology.md#57-write-pulse-wr_pulse), the first step of a two-step TP, is the active write window:

```text
write enable = (/WR = 0) AND (/WR_PULSE = 0)
```

MFB, AB, MDB, and /WR are stable from before the leading edge of TP through the end of TP ([Timing Architecture §7.6](../09-timing/02-timing-architecture.md#76-rule-6--two-ranks)). Therefore:

- the write depends only on values committed by the previous TP
- gating /WR with the pulse cannot glitch, and a change on /WR outside the pulse has no effect
- address and data are held for the second step of TP after the write ends

The write commits at that TP. When /WR is not asserted during the pulse, memory must not perform a write.

---

## 5. Address Stability

MFB and AB together define MEM_ADDR.

For any valid read or write operation, MFB and AB must remain stable for the entire active operation window.

If MFB or AB changes while /RD is asserted, or during a write pulse with /WR asserted, the memory operation is invalid.

---

## 6. Read Data Stability

During a valid read operation, memory must drive MDB with the value stored at M[MEM_ADDR] while /RD is asserted and MEM_ADDR remains stable.

Memory is not required to preserve MDB after /RD is deasserted.

---

## 7. Write Data Stability

During a valid write operation, MDB must contain the value to be stored from before the leading edge of TP through the end of TP.

The memory subsystem stores the value presented on MDB at the selected MEM_ADDR.

If MDB changes during the active write window, the write operation is invalid unless explicitly defined elsewhere.

---

## 8. Mutual Exclusion

/RD and /WR must not be asserted at the same time.

A memory operation is either:

- a read
- a write
- idle

No combined read/write memory operation is defined.

---

## 9. Idle Timing

When /RD and /WR are both deasserted:

- memory performs no read
- memory performs no write
- memory must not drive MDB
- changes on MFB or AB do not by themselves cause memory behavior

---

## 10. Technology Timing Requirements

The selected physical memory technology must satisfy the timing contract defined by this section.

Technology-specific timing parameters, such as access time, output enable delay, write pulse width, setup time, and hold time, are implementation constraints. They must be chosen so that the logical memory behavior remains valid at the system timing rate.

Memory is an asynchronous part with separate write-enable timing. The interface admits any device, volatile or persistent, within these limits:

| Parameter | Device may require at most |
|---|---:|
| Write pulse | 15 ns |
| Address valid to end of write | 18 ns |
| Data valid to end of write | 10 ns |
| Address hold after write | 12 ns |
| Data hold after write | 0 ns |
| Address access | 35 ns |
| Output-enable access | 15 ns |

A 3.3 V device needs level translation, and any persistent device needs write protection while power rises and falls.

---

## 11. Invariants

- /RD defines the active read window.
- /WR selects a write; /WR_PULSE is the active write window.
- MFB must remain stable during an active memory operation.
- AB must remain stable during an active memory operation.
- MDB must be valid during an active write window.
- Memory drives MDB only during an active read window.
- Memory does not drive MDB when /RD is deasserted.
- /RD and /WR must not be asserted together.
- Timing implementation details must not change the logical memory model.

---

## 12. Summary

Memory timing is defined at the memory interface.

/RD controls when memory drives read data. /WR selects whether memory stores write data at a TP, and /WR_PULSE times the write. MFB and AB must remain stable for the active operation window, and MDB direction is determined by whether the operation is a read or a write.