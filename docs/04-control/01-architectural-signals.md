# Architectural Control Signals

## Index
- [RD](#rd)
- [WR](#wr)

---

## RD

### Definition
Initiates memory read.

### Values
0, 1

### Constraints
- RD and WR mutually exclusive
- MDB carries memory data
- Data becomes valid in MB for CPU

### Preconditions
- MA must contain valid data
- MA must be stable for entire read phase

---

## WR

### Definition
Initiates memory write.

### Values
0, 1

### Constraints
- RD and WR mutually exclusive
- Write data defined by MB
- MDB transports MB contents

### Preconditions
- MB must contain valid data
- MA must contain valid data
- MDB must reflect MB during write cycle

