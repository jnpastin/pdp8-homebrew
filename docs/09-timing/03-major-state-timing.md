
## Major State Timing

### Purpose
Defines timing behavior of each Major State using TS/TP model.

### Core Model
- TS = setup/stabilization window
- TP = state transition event

All state changes occur exclusively at TP.

---

## FETCH

### TS1 — Address Setup
- MA_SRC = PC (PC selected as MA input)

### TP1
- MA loaded from PC

### TS2 — Memory Access
- MA drives AB
- RD asserted
- Memory drives MDB

### TP2
- MB loaded from MDB

### TS3 — Instruction Preparation
- MB stable

### TP3
- IR loaded from MB

### TS4 — Finalization

### TP4
- PC increment
- MS transition decision

---

## DEFER

### TS1 — Address Setup
- MA_SRC = EA_ADDR (pointer location selected as MA input)

### TP1
- MA loaded from EA_ADDR

### TS2 — Memory Access
- MA drives AB
- MFB_SRC = IF (pointer located in the IF domain)
- RD asserted
- Memory drives MDB (pointer value)

### TP2
- MB loaded from MDB

### TS3 — Autoindex (conditional)
- if EA_ADDR is within autoindex range: MB incremented

### TP3
- MB updated with incremented value (autoindex only)

### TS4 — Resolution
- MB drives the resolved address
- if autoindex: WR asserted, MFB_SRC = IF, incremented value written back to the pointer location

### TP4
- EA_ADDR loaded from MB (final resolved effective address)
- MS transition to EXECUTE

---

## EXECUTE
- Instruction-dependent behavior
- Uses full TS1–TS4 structure

### TP4
- Interrupt condition evaluated
- Transition to INTERRUPT or FETCH

---

## INTERRUPT
- Sequence defined by control

### TS1–TS4
- Save PC
- Load vector

### TP4
- Return to FETCH
