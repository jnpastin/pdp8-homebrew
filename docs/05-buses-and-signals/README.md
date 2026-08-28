# Buses and Signals

## 1. Purpose
Defines the system's signal classification, bus definitions, bus semantics, domain boundaries, ownership, and the architectural memory, I/O, and DMA interfaces.

---

## 2. Scope
Includes:
- Signal classification (Classes A-E)
- Class A bus definitions (AB, DB, MDB, MFB)
- Class B-E signal organization
- Bus semantics, domain boundaries, and ownership
- Memory, I/O, and DMA interface participation models

Excludes:
- Control signal semantics ([../04-control/README.md](../04-control/README.md))
- Timing behavior ([../09-timing/README.md](../09-timing/README.md))
- Register definitions ([../01-architecture/01-registers.md](../01-architecture/01-registers.md))

---

## 3. Model Summary
- Signals are partitioned into five classes with distinct visibility, placement, and electrical rules.
- Class A buses provide address and data transport; ownership is control-selected and mutually exclusive.
- Transport domains (AB, MDB, DB, IDB) are isolated; crossings are explicit and control-defined.
- Memory, I/O, and DMA interfaces are defined in terms of domain participation, not control mechanism.

---

## 4. Related Documents
- [00-signal-classes.md](./00-signal-classes.md)
- [01-class-a-buses.md](./01-class-a-buses.md)
- [02-class-b-control.md](./02-class-b-control.md)
- [03-class-c-timing.md](./03-class-c-timing.md)
- [04-class-d-front-panel.md](./04-class-d-front-panel.md)
- [05-class-e-internal.md](./05-class-e-internal.md)
- [06-bus-semantics.md](./06-bus-semantics.md)
- [07-domain-boundaries.md](./07-domain-boundaries.md)
- [08-ownership-matrix.md](./08-ownership-matrix.md)
- [09-memory-interface.md](./09-memory-interface.md)
- [10-io-interface.md](./10-io-interface.md)
- [11-dma-interface.md](./11-dma-interface.md)