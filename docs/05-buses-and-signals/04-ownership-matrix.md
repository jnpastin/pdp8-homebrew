# 04 Ownership Matrix

## Purpose

This document defines signal ownership for all system buses and related control signals.

Ownership specifies:
- Which entity may drive a signal
- Under what conditions it may be driven
- When all other entities must be in High-Z

Bus validity and timing rules are defined separately in:
- 03-bus-semantics.md

---

## Global Control Ownership Model

The CPU is the sole driver of all system control signals and performs all bus arbitration.

All control signals, including RD, WR, DB_GRANT, DB_READ, DB_WRITE, and IOA, originate from the CPU.
Devices do not drive control signals and do not initiate bus operations.

Devices may assert request signals (/INT_REQ, /DB_REQ), but the CPU determines when these requests are serviced.
External request signals (/INT_REQ, /DB_REQ) are provided to the CPU as inputs and are used in control decisions, but are not driven by the CPU.

As a result:
- Bus ownership is centrally controlled by the CPU
- All arbitration decisions are made within the CPU
- Bus transitions occur only at CPU-defined boundaries

---

# 1. Address Bus (AB)

## Drivers

- CPU
- DMA device (when granted)

## Ownership Rules

CPU drives AB when:
```
DB_GRANT == 0
```

DMA drives AB when:
```
DB_GRANT == 1 AND DB_ADDR_EN == 1
```

## High-Z Condition

AB is High-Z when:
```
DB_GRANT == 1 AND DB_ADDR_EN == 0
```

## Invariants

- CPU must not drive AB when DB_GRANT == 1
- DMA must not drive AB unless DB_ADDR_EN == 1
- At most one driver may be active at any time

---

# 2. Memory Data Bus (MDB)

## Drivers

- Memory
- CPU
- DMA device

## Ownership Rules

Memory drives MDB when:
```
RD == 1 OR (DB_GRANT == 1 AND DB_READ == 1)
```

CPU drives MDB when:
```
WR == 1 AND DB_GRANT == 0
```

DMA drives MDB when:
```
DB_GRANT == 1 AND DB_WRITE == 1 AND DB_DATA_EN == 1
```

## High-Z Condition

MDB is High-Z when no driver condition is true.

## Invariants

- Only one driver may be active at any time
- CPU must not drive MDB when DB_GRANT == 1
- Memory must not drive MDB during write operations
- DMA must explicitly assert DB_DATA_EN to drive MDB

---

# 3. System Data Bus (DB) and IOA

## IOA Ownership

### Drivers

- CPU only

### Rules

```
CPU continuously drives IOA
```

- Devices must never drive IOA
- IOA is never tri-stated

### IOA Idle Value

```
IOA = 111111 (all ones) outside IOT operations
```

### Reserved Address

```
111111 is reserved and must not be assigned to any device
```

---

## DB Ownership

### Drivers

- CPU
- One selected device

### CPU drives DB when

```
IOT AND WRITE_PHASE
```

### Device drives DB when

```
IOT AND READ_PHASE AND (IOA == device_address)
```

### High-Z Condition

DB is High-Z when no driver condition is true.

---

## IOA-DB Coupling Invariants

- Only CPU may drive IOA
- IOA determines device selection
- At most one device may match IOA
- A device may drive DB only if selected by IOA
- Multiple matching devices results in contention (illegal)

---

# Summary

This document establishes:

- CPU-centric control and arbitration
- Explicit ownership rules for AB, MDB, and DB
- Safe tri-state behavior for shared buses
- IOA as a single-driver selection mechanism

These rules guarantee:

- No bus contention
- Deterministic ownership transitions
- Clear separation between control and data transport
