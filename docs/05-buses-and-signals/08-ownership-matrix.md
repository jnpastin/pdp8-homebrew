# 08 Bus Ownership Matrix

## Purpose

This document defines ownership of system transport mechanisms during normal operation.

Ownership determines which source is permitted to drive a transport mechanism.

This document defines:

- ownership structure
- ownership selection mechanisms
- ownership scope

This document does NOT define:

- ownership timing
- ownership transfer behavior
- bus validity
- control behavior
- DMA ownership behavior

Bus semantics are defined in:

- [Bus Semantics](./06-bus-semantics.md)

DMA-specific ownership behavior is defined in:

- [DMA Interface](./11-dma-interface.md)

---

## Ownership Model

Ownership determines which source is permitted to drive a transport mechanism.

Ownership is controlled through source-selection signals defined by the control architecture.

This document identifies the ownership mechanism for each transport mechanism.

Permissible ownership selections are defined in Section 4.

---

### Ownership Activation

Source-selection signals identify the source eligible to drive a transport mechanism.

A selected source drives a transport mechanism only when the corresponding drive-enable condition is asserted.

Ownership therefore depends on both source selection and source enable conditions.

Authoritative definitions are maintained in Section 4.

---

## Ownership Matrix

### Address Bus (AB)

**Ownership Control**

- AB_SRC

**Purpose**

Selects the source permitted to drive AB.

Permissible source selections are defined in the control architecture.

---

### Data Bus (DB)

**Ownership Control**

- /DB_WRITE

**Purpose**

Determines when the CPU drives DB. The CPU drives DB (source AC) only when /DB_WRITE is asserted; otherwise the selected I/O device drives DB, or DB is idle (High-Z). Unlike the other buses, DB has no source-select signal because the CPU has a single DB source (AC).
---

### Internal Data Bus (IDB)

**Ownership Control**

- IDB_SRC

**Purpose**

Selects the source permitted to drive IDB.

Permissible source selections are defined in the control architecture.

---

### Memory Data Bus (MDB)

**Ownership Control**

- MDB_SRC

**Purpose**

Selects the source permitted to drive MDB.

Permissible source selections are defined in the control architecture.

---

### Memory Field Bus (MFB)

**Ownership Control**

- MFB_SRC

**Purpose**

Selects the source permitted to drive MFB.

Permissible source selections are defined in the control architecture.

---

## Relationship to Control

Ownership selection is performed by the control system.

This document defines ownership structure only.

Ownership selection values, constraints, and operational behavior are defined in Section 4.

---

### DMA Ownership

During MS = DMA, CPU control releases normal ownership of:

- MFB
- AB
- MDB
- /RD
- /WR

/DMA_GRANT indicates that the CPU has released these interfaces.  
The external DMA arbiter selects one controller through DMA_GRANT_ID[3:0].  
DMA_GRANT_ID values 0 through 14 identify valid controller priority channels.  
DMA_GRANT_ID value 15 indicates that no controller is selected.

A controller owns the DMA interfaces only when:

```text
/DMA_GRANT = 0
AND
DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

The selected controller owns:

- MFB
- AB
- /RD
- /WR
- MDB during DMA writes

Memory owns MDB during DMA reads.

Ownership rules:

- A controller DMA priority must be in the range 0 through 14.
- No /DMA_REQ line exists for priority 15.
- No controller may drive a DMA-owned interface unless /DMA_GRANT is asserted and DMA_GRANT_ID matches its configured priority.
- No controller may drive a DMA-owned interface while DMA_GRANT_ID is 15.
- CPU and DMA ownership must not overlap.
- DMA_GRANT_ID remains stable throughout an active controller selection.
- An active controller selection is non-preemptive.
- DMA controller ownership ends at TP4 before CPU ownership resumes in the following FETCH TS1.
- Memory is the sole MDB producer during a DMA read.
- The selected controller is the sole MDB producer during a DMA write.

Detailed DMA interface behavior is defined in [DMA Interface](../07-io/05-dma-interface.md).  
Arbitration and selection behavior are defined in [DMA Arbitration](../07-io/06-dma-arbitration.md).)

---

## Global Invariants

- Ownership determines which source may drive a transport mechanism.
- Ownership does not imply validity.
- Every transport mechanism has a defined ownership control.
- Ownership selection is determined by the control architecture.
- Permissible ownership selections are defined in Section 4.
- DMA ownership behavior is defined separately.

---

## Summary

Ownership defines which source is permitted to drive a transport mechanism.

This document identifies the ownership control associated with each transport mechanism. Ownership behavior, selection values, and operational constraints are defined by the control architecture.
