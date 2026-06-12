
## Control Model

### Purpose
Defines how all system behavior is generated from machine state.

Control is the only mechanism that produces behavior in the system.

---

### Definition

CONTROL = f(MS, TS, IR, FLAGS, EXT)

Where:
- MS: Major State
- TS: Time State
- IR: Instruction Register bits
- FLAGS: architectural state (defined incrementally)
- EXT: external inputs

Control is implemented exclusively using a ROM-based mapping.

---

### Evaluation Model

During TS:
- Control outputs are stable
- Datapath is configured

At TP:
- All state changes occur
- Registers latch values
- MS ← MS_next

Constraint:
- No state change occurs outside TP

---

### External Inputs (EXT)

EXT includes only externally sourced signals:
- /INT_REQ (interrupt request)
- /DB_REQ (DMA request)

Constraints:
- Must be stable before TP
- Must not include datapath values
- Must not include control outputs

---

### Control Domains

#### Architectural Control
Defines externally visible behavior:
- RD, WR
- IOA[5:0]
- DB_* signals

#### Microarchitectural Control
Defines internal datapath behavior:
- Register loads
- ALU operations
- Bus selection

---

### Interrupt Rule

Interrupts are recognized only at TP4 of EXECUTE when:

IE = 1 AND /INT_REQ = 0

Constraints:
- No interrupt during FETCH or DEFER
- Instruction always executes once fetched

---

### Completeness Constraint

For every (MS, TS):
- All control outputs must be defined
- No implicit behavior allowed

---

### Determinism

The mapping must be:

(MS, TS, IR, FLAGS, EXT) → exactly one control word

No undefined states are permitted
