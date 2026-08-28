# Dataflow and Bus Model

Buses are defined and described in more detail [here](../05-buses-and-signals/01-class-a-buses.md).

## Core Principle
All data movement follows:

Bus → Register → Consumer

---

## Address Path

MA → AB → Memory
- MA is the authoritative CPU address register
- AB is an architectural bus driven by MA during normal CPU operation
- During DMA, an external device drives AB instead of MA
- Memory is addressed via AB

---

## Memory Data Path
MDB → MB → CPU

- MDB is transient
- MB stores stable value

---

## System Data Bus
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

## Constraints
- Buses are not storage
- Registers are the only stable sources
- No component may rely on bus state

---

## Timing Relationship
- TS: stabilization
- TP: capture

