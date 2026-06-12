
## Dataflow and Bus Model

Buses are defined and described in more detail [here](https://github.com/jnpastin/pdp8-homebrew/blob/arch/docs/05-buses-and-signals/01-class-a-buses.md).

### Core Principle
All data movement follows:

Bus → Register → Consumer

---

### Address Path
AB → MA → Memory

- AB is transient
- MA is authoritative
- Memory must use MA exclusively

---

### Memory Data Path
MDB → MB → CPU

- MDB is transient
- MB stores stable value

---

### System Data Bus
DB → Register → Consumer

- DB values must be captured
  - CPU captures into AC
  - I/O devices capture into a register within the device's controller
- No direct consumption

---

### Constraints
- Buses are not storage
- Registers are the only stable sources
- No component may rely on bus state

---

### Timing Relationship
- TS: stabilization
- TP: capture

