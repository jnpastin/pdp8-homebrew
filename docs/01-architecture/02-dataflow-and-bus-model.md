
## Dataflow and Bus Model

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

