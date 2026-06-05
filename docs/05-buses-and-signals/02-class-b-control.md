
## Class B — Global Control Signals

### Purpose
Defines system-wide control signals that coordinate behavior across modules on the backplane.

### Properties
- Single-bit (except IOA)
- Visible to all modules
- May be single-driver, wired-OR, or daisy-chain

---

### Memory Control
#### RD (Read)
- Asserted by CPU
- Memory drives MDB when RD = 1
- MDB must be valid before TP that loads MB

#### WR (Write)
- Asserted by CPU
- CPU drives MDB from MB when WR = 1
- Memory captures MDB

Constraints:
- RD and WR are mutually exclusive

---

### Interrupt System
#### /INT_REQ
- Wired-OR, active-low
- Asserted by devices only

#### INT_ACK Chain
- INT_ACK_IN / INT_ACK_OUT
- CPU injects acknowledge into chain
- First requesting device consumes it

Invariants:
- Only one device responds per cycle
- Priority determined by position

---

### I/O Selection
#### IOA[5:0]
- Driven only by CPU
- Stable during IOT operations
- Devices decode combinationally

Idle state:
- All ones

---

### Data Break (DMA)
#### DB_REQ
- Wired-OR request signal

#### DB_GRANT Chain
- Daisy-chained arbitration

#### Transfer Signals
- DB_ADDR_EN
- DB_DATA_EN
- DB_READ
- DB_WRITE

Rules:
- CPU releases AB and MDB when DB_GRANT asserted
- Only one DMA device active at a time

---

### Global Invariants
- Only one driver per bus at a time
- Control signals originate from CPU
- Devices assert requests only (/INT_REQ, /DB_REQ)
