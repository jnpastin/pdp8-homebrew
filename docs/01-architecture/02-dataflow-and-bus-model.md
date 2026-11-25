# Dataflow and Bus Model

## 1. Purpose

Describes, at the architectural level, how data moves between the buses, the registers, and memory. The buses themselves are defined in [Class A Buses](../05-buses-and-signals/01-class-a-buses.md).

---

## 2. Core Principle
All data movement follows:

Bus → Register → Consumer

---

## 3. Address Path

MA → AB → Memory
- MA is the authoritative CPU address register
- AB is an architectural bus driven by MA during normal CPU operation, and by PC for the EXAMINE and DEPOSIT console operations
- During DMA, an external device drives AB instead of MA
- Memory is addressed via AB

---

## 4. Memory Data Path
MDB → MB → CPU

- MDB is transient
- MB stores stable value
- Exception: during instruction fetch IR also loads directly from MDB (`MDB → IR`), at FETCH TP2, in parallel with MB

---

## 5. System Data Bus
DB → Register → Consumer

- DB values must be captured
  - CPU captures into AC
  - I/O devices capture into a register within the device's controller
- No direct consumption

DB → AC → CPU

- DB is transient
- AC stores stable value

All CPU ingestion of DB must occur via AC.

Constraints:
- No arbitrary register may consume DB directly
- DB must be captured into AC before any use by the CPU datapath
- This mirrors the MDB → MB → CPU model

---

## 6. Constraints
- Buses are not storage
- Registers are the only stable sources
- No component may rely on bus state: a register may capture a bus at a TP, as IR captures MDB, but nothing holds a value on a bus

---

## 7. Timing Relationship
- TS: values settle from state committed at the previous TP
- TP: the capture rank loads at its rising edge, and the output rank publishes at its falling edge ([Timing Architecture §7.6](../09-timing/02-timing-architecture.md#76-rule-6--two-ranks))

