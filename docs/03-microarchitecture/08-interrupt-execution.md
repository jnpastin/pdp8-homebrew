## INTERRUPT Execution

## Purpose
  
Defines execution behavior for the INTERRUPT major state.  
This document specifies:
- μop sequences assigned to TS
- register state transitions required for interrupt entry  

Interrupt semantics and programmer-visible behavior are defined in:
- [Interrupts and Skip](../08-interrupts-and-skip/README.md)

Execution behavior follows:
- [Execution Model](./01-execution-model.md)

## Scope
  
Applies when:
- MS = INTERRUPT  

Entry into INTERRUPT is determined by control based on:
- interrupt enable state (IE)
- interrupt request signals  

Control conditions governing entry are defined in:
- [Control Model](../04-control/01-control-model.md)

## Execution Model
  
INTERRUPT execution is similar to, but not equivalent to:

- JMS 0000  

Shared behavior:
- M[0000] ← PC  
- PC ← 0001  

Additional behavior (not present in JMS):
- IE ← 0  
- IF ← 0 (if present)  
- DF ← 0 (if present)  

Properties:
- No IR decoding occurs during this state
- All datapath and register behavior is expressed via μops
- No device state is modified during interrupt entry
- Execution is completed within TS1–TS4  

---

## INTERRUPT Execution

### TS1 — PC Capture
  
- PC_TO_MB  

Description:
- Captures the current PC value into MB for subsequent storage  

---

### TS2 — Address Formation
  
- MA_CLEAR  
- IF_DF_TO_IB

Description:
- Sets MA to 0000  
- Saves the current IF and DF into IB

---

### TS3 — Save Return Address
  
- MEM_WRITE_FROM_MB  

Description:
- Writes MB (saved PC) to memory location MA (0000)  

---

### TS4 — Control Transfer and State Update
  
- PC_SET_1  
- IE_CLEAR  
- IF_CLEAR (if present)  
- DF_CLEAR (if present)  

Description:
- Loads PC with address 0001  
- Clears interrupt enable state  
- Forces instruction and data fields to 0 (if implemented)  

---

## Invariants

- PC is saved exactly once to memory location 0000
- Memory write occurs before PC is modified
- PC is updated only after the original value is preserved
- IF and DF are saved into IB before they are cleared
- IE is cleared during interrupt entry
- IF and DF are cleared during interrupt entry (if present)
- No IR-dependent behavior occurs during this state
- No device interrupt state is modified during this state

---

## Execution Boundary Guarantee
  
Upon completion of INTERRUPT:
- M[0000] contains the return address
- IB[5:3] = saved IF, IB[2:0] = saved DF
- PC = 0001
- IE = 0
- IF = 0 and DF = 0 (if implemented)

---

## Notes

- INTERRUPT execution performs the same memory and control transfer as `JMS 0000`, with additional register updates (IE, IF, DF)
- Entry point is fixed at address 0001; no vector lookup is performed
- Return from interrupt is performed via:
  - JMP I 0000 (defined in ISA)
- No stack or automatic context save mechanism is provided

### Device Interaction

- Interrupting devices are **not acknowledged** during INTERRUPT execution
- No global interrupt acknowledge (IRQ_ACK) mechanism exists
- Device interrupt requests remain asserted until cleared

### Software Responsibility

- The interrupt service routine must:
  - identify the interrupting device via IOT skip instructions
  - service the device via IOT operations
  - clear the device interrupt condition as part of that service
  - preserve and restore any required register state (AC, L, MQ)

- Interrupt enable state (IE) is modified by IOT instructions (e.g., ION, IOF), defined in:
  - [IOT Execution](./06-iot-execution.md)

### Interrupt Model

- Interrupt request is the logical OR of device requests
- Device priority and dispatch are determined by software
- Nested interrupts require explicit re-enabling via ION