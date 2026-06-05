
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
- PC drives AB

### TP1
- MA loaded from AB

### TS2 — Memory Access
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
### TS1
- MA valid
- Memory read in progress

### TP1
- MB loaded

### TS2
- Effective address computed

### TP2
- EA updated

### TS3
- Address staging

### TP3
- MA loaded with EA

### TS4

### TP4
- Transition to EXECUTE

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
