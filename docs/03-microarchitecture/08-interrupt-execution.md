# INTERRUPT Execution

## 1. Purpose
  
Defines execution behavior for the INTERRUPT major state.  
This document specifies:
- μop sequences assigned to TS
- register state transitions required for interrupt entry  

Interrupt semantics and programmer-visible behavior are defined in:
- [Interrupts and Skip](../08-interrupts-and-skip/README.md)

Execution behavior follows:
- [Execution Model](./01-execution-model.md)

---

## 2. Scope
  
Applies when:
- MS = INTERRUPT  

Entry into INTERRUPT is determined by control based on:
- interrupt enable state (IE)
- interrupt request signals  

Control conditions governing entry are defined in:
- [Control Model](../04-control/01-control-model.md)

---

## 3. Execution Model
  
INTERRUPT execution is similar to, but not equivalent to:

- JMS 0000  

Shared behavior:
- M[0000] ← PC  
- PC ← 0001  

Additional behavior (not present in JMS):
- IE ← 0  
- IF ← 0   
- DF ← 0   
- DIF ← 0
- CIFP ← 0

Properties:
- No IR decoding occurs during this state
- All datapath and register behavior is expressed via μops
- No device state is modified during interrupt entry
- Execution is completed within TS1–TS4  

---

## 4. Execution Sequence

### 4.1 TS1 — PC Capture and Address Formation

- PC_TO_MB
- MA_CLEAR

Description:
- Captures the current PC value into MB for subsequent storage
- Sets MA to 0000

---

### 4.2 TS2 — Field Save and Field Clear

- IF_DF_TO_IB
- IF_CLEAR
- DF_CLEAR
- DIF_CLEAR
- CIFP_CLEAR

Description:
- Saves the current IF and DF into IB
- Forces instruction and data fields to 0, so the TS3 write addresses field 0
- Clears `DIF` and `CIFP` so the ISR starts with no pending deferred instruction-field change

IB captures the values IF and DF held before TP2, so the save and the clear commit at the same TP ([Microarchitectural Control Signals §11.5](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#115-pre-ts-state-visibility)). All field state changes together, as on the PDP-8/e, where the memory extension saves and clears the fields before the return address is stored.

---

### 4.3 TS3 — Save Return Address

- MEM_WRITE_FROM_MB

Description:
- Writes MB (saved PC) to memory location 0000 of field 0 (MA = 0000, IF = 0)

---

### 4.4 TS4 — Control Transfer

- PC_SET_1
- IE_CLEAR

Description:
- Loads PC with address 0001
- Clears interrupt enable state

---

## 5. Invariants

- PC is saved exactly once to memory location 0000 of field 0
- Memory write occurs before PC is modified
- PC is updated only after the original value is preserved
- IF and DF are saved into IB at the same TP at which they are cleared, from their values before that TP
- IF = 0 throughout the TS3 write
- IE is cleared during interrupt entry
- IF and DF are cleared during interrupt entry
- DIF and CIFP are cleared during interrupt entry, so no field change is pending in the ISR
- No IR-dependent behavior occurs during this state
- No device interrupt state is modified during this state

---

## 6. Execution Boundary Guarantee
  
Upon completion of INTERRUPT:
- M[0:0000] contains the return address
- IB[5:3] = saved IF, IB[2:0] = saved DF
- PC = 0001
- IE = 0
- IF = 0 and DF = 0
- DIF = 0 
- CIFP = 0

---

## 7. Notes

- INTERRUPT execution performs the same memory and control transfer as `JMS 0000`, with additional register updates (IE, IF, DF, DIF, CIFP)
- Entry point is fixed at address 0001; no vector lookup is performed
- Return from interrupt is performed via:
  - JMP I 0000 (defined in ISA)
- No stack or automatic context save mechanism is provided

### 7.1 Device Interaction

- Interrupting devices are **not acknowledged** during INTERRUPT execution
- No global interrupt acknowledge (IRQ_ACK) mechanism exists
- Device interrupt requests remain asserted until cleared

### 7.2 Software Responsibility

- The interrupt service routine must:
  - identify the interrupting device via IOT skip instructions
  - service the device via IOT operations
  - clear the device interrupt condition as part of that service
  - preserve and restore any required register state (AC, L, MQ)

- Interrupt enable state (IE) is modified by IOT instructions (e.g., ION, IOF), defined in:
  - [IOT Execution](./06-iot-execution.md)

### 7.3 Interrupt Model

- Interrupt request is the logical OR of device requests
- Device priority and dispatch are determined by software
- Nested interrupts require explicit re-enabling via ION