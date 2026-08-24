
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
- /RD asserted
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
- /RD asserted
- Memory drives MDB (pointer value)

### TP2
- MB loaded from MDB

### TS3 — Autoindex (conditional)
- if EA_ADDR is within autoindex range: MB incremented

### TP3
- MB updated with incremented value (autoindex only)

### TS4 — Resolution
- MB drives the resolved address
- if autoindex: /WR asserted, MFB_SRC = IF, incremented value written back to the pointer location

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

### EXECUTE: External IOT

#### TS1

- `IOT_ACTIVE` is asserted.
- IOA is valid.
- IOP is valid.
- Controllers evaluate address match.
- The selected controller decodes IOP.
- `/IO_WAIT` may hold an eligible non-TP setup TSTEP.

#### TP1

- No external-IOT action commits.

#### TS2 and TS3

- The selected controller may assert phase-specific read, write, or clear responses.
- `/IO_WAIT` may hold eligible non-TP setup TSTEPs.
- A response asserted during the TS commits at the following TP.

#### TS4

- The selected controller may assert phase-specific read, write, clear, or skip responses.
- The selected controller may assert `IO_SKIP_REQ` from stable registered controller state.
- A separate TP3-captured skip condition is not required..
- TP4 sequencing and interrupt inputs must be stable before TP4.

#### TP4

- Requested device and CPU actions commit.
- `IO_SKIP_REQ` increments PC when asserted.
- Interrupt and sequencing decisions use only pre-TP4 inputs.
- No TP4 result affects another decision committed at TP4.

---

## INTERRUPT
- Sequence defined by control

### TS1–TS4
- Save PC
- Load vector

### TP4
- Return to FETCH

---

### DMA

Each DMA major-state cycle with a valid controller selection transfers exactly one memory word at TP2.

#### TS1

If no controller is selected:

- the external DMA arbiter evaluates pending request channels
- the lowest-numbered pending requester is selected
- the selected DMA_GRANT_ID commits at TP1

If a burst continues:

- the active grant remains selected;
- arbitration is not repeated.

#### TP1

- A new DMA_GRANT_ID commits when arbitration was required.
- No memory transfer commits.

#### TS2

The granted controller:

- drives MFB;
- drives AB;
- asserts /RD or /WR;
- drives MDB for a DMA write.

For a DMA read, memory drives MDB.

#### TP2

- One DMA memory transfer commits.
- For a read, the granted controller captures MDB.
- For a write, memory captures MDB.

#### TS3

- Completion of the TP2 transfer is available to the granted controller and DMA arbiter.

#### TP3

- The controller updates its complete-operation address.
- The controller updates its remaining operation word count.
- The DMA arbiter increments the active burst count.

#### TS4

The DMA arbiter determines whether DMA service continues.

- If the current burst continues, aggregate `/DMA_REQ` remains asserted.
- If the current burst ends, aggregate `/DMA_REQ` is deasserted.
- Pending controller request lines may remain asserted after a burst ends.

#### TP4

```text
/DMA_REQ = 0 -> MS_NEXT = DMA
/DMA_REQ = 1 -> MS_NEXT = FETCH
```

At a terminating TP4:

- the previously selected controller releases MFB, AB, MDB, /RD, and /WR
- the arbiter sets DMA_GRANT_ID to 15
- CPU ownership resumes during the following FETCH TS1

Aggregate `/DMA_REQ` may be reasserted after entry to FETCH because DMA entry is not evaluated again until the following instruction's EXECUTE TP4.
