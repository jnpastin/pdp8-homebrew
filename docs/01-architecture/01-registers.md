
## Register Model Specification

### Purpose
Defines all system state.

All stable values in the system must reside in registers.

---

### Architectural Registers
- PC: Program Counter (12-bit)
- AC: Accumulator (12-bit)
- L: Link (1-bit)
- MQ: Multiplier Quotient (12-bit)
- IF: Instruction Field (3-bit)
- DF: Data Field (3-bit)
- SR: Switch Register (12-bit)
- IE: Interrupt Enable (1-bit)

---

### Control-Visible State
- IR: Instruction Register
- MS: Major State

---

### Internal Registers
- MA: Memory Address
- MB: Memory Buffer
- EA: Effective Address

---

### EA Lifecycle

FETCH:
- EA formed from IR and PC context

DEFER:
- MA ← EA
- Memory read → MB
- EA ← MB

EXECUTE:
- EA used for operand access

---

### MA Rules
- MA is valid only during memory cycles
- MA must not be treated as persistent state

---

### MB Rules
- MB captures all memory data
- CPU must not use MDB directly

---

### Interrupt Representation
- /INT_REQ is an external signal
- IE is the only architectural interrupt state

---

### Constraints
- No hidden state
- All control decisions derive from registers + EXT

