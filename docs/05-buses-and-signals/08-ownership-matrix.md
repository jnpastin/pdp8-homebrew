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

- DB_SRC

**Purpose**

Selects the source permitted to drive DB.

Permissible source selections are defined in the control architecture.

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

## Relationship to DMA

This document defines ownership during normal operation.

DMA may modify ownership behavior for one or more transport mechanisms.

DMA-specific ownership behavior is defined in:

- [DMA Interface](./11-dma-interface.md)

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
