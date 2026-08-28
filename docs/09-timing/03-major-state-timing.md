# Major State Timing

## 1. Purpose
Defines timing behavior of each Major State using TS/TP model.

---

## 2. Core Model
- TS = setup/stabilization window
- TP = state transition event

All state changes occur exclusively at TP.

---

## 3. FETCH

### 3.1 TS1 — Address Setup
- MA_SRC = PC (PC selected as MA input)

### 3.2 TP1
- MA loaded from PC

### 3.3 TS2 — Memory Access
- MA drives AB
- /RD asserted
- Memory drives MDB

### 3.4 TP2
- MB loaded from MDB

### 3.5 TS3 — Instruction Preparation
- MB stable

### 3.6 TP3
- IR loaded from MB

### 3.7 TS4 — Finalization

### 3.8 TP4
- PC increment
- MS transition decision

---

## 4. DEFER

### 4.1 TS1 — Address Setup
- MA_SRC = EA_ADDR (pointer location selected as MA input)

### 4.2 TP1
- MA loaded from EA_ADDR

### 4.3 TS2 — Memory Access
- MA drives AB
- MFB_SRC = IF (pointer located in the IF domain)
- /RD asserted
- Memory drives MDB (pointer value)

### 4.4 TP2
- MB loaded from MDB

### 4.5 TS3 — Autoindex (conditional)
- if EA_ADDR is within autoindex range: MB incremented

### 4.6 TP3
- MB updated with incremented value (autoindex only)

### 4.7 TS4 — Resolution
- MB drives the resolved address
- if autoindex: /WR asserted, MFB_SRC = IF, incremented value written back to the pointer location

### 4.8 TP4
- EA_ADDR loaded from MB (final resolved effective address)
- MS transition to EXECUTE

---

## 5. EXECUTE
- Instruction-dependent behavior
- Uses full TS1–TS4 structure

### 5.1 TP4
- Interrupt condition evaluated
- Transition to INTERRUPT or FETCH

---

### 5.2 EXECUTE: External IOT

#### 5.2.1 TS1

- `IOT_ACTIVE` is asserted.
- `IOA` and `IOP` are valid.
- Controllers evaluate address match.
- The selected controller decodes IOP.
- `/IO_WAIT` may hold an eligible non-TP setup TSTEP.

#### 5.2.2 TP1

- No external-IOT action commits.

#### 5.2.3 TS2

- The selected controller may assert `IO_READ_REQ` or `IO_WRITE_REQ` for a transfer during TS3.
- The selected controller may assert `IO_CLEAR_AC_REQ` for an operation assigned to TP2.
- The selected controller may assert `/IO_WAIT` during an eligible non-TP setup TSTEP.

#### 5.2.4 TP2

- CPU control records an accepted read or write direction in `IOT_TRANSFER`.
- An accepted `IO_CLEAR_AC_REQ` clears AC.
- Controller-local actions assigned to TP2 commit.

Acceptance of `IO_READ_REQ` or `IO_WRITE_REQ` at TP2 does not transfer DB data at TP2.

#### 5.2.5 TS3

- `IOT_READ_PENDING` causes CPU control to assert `/DB_READ`.
- `IOT_WRITE_PENDING` causes CPU control to assert `/DB_WRITE`.
- During `/DB_READ`, the selected controller drives valid data onto DB.
- During `/DB_WRITE`, the CPU drives AC onto DB.
- The selected controller may assert `IO_READ_REQ` or `IO_WRITE_REQ` for a transfer during TS4.
- The selected controller may assert `IO_CLEAR_AC_REQ` when it does not conflict with the active transfer.
- The selected controller may assert `/IO_WAIT` during an eligible non-TP setup TSTEP.

#### 5.2.6 TP3

- A pending read commits `DB_READ_TO_AC`.
- The selected controller captures DB for a pending write.
- An accepted `IO_CLEAR_AC_REQ` clears AC.
- Controller-local actions assigned to TP3 commit.
- A newly accepted read or write request replaces the completed `IOT_TRANSFER`.
- If no new request is accepted, a completed `IOT_TRANSFER` clears to `NONE`.

Acceptance of a new request at TP3 does not affect the transfer committing at TP3.

#### 5.2.7 TS4

- `IOT_READ_PENDING` causes CPU control to assert `/DB_READ`.
- `IOT_WRITE_PENDING` causes CPU control to assert `/DB_WRITE`.
- During `/DB_READ`, the selected controller drives valid data onto DB.
- During `/DB_WRITE`, the CPU drives AC onto DB.
- The selected controller may assert `IO_CLEAR_AC_REQ` only when no read transfer is pending.
- The selected controller may assert `IO_SKIP_REQ` from stable registered controller state.
- `/IO_WAIT` may hold an eligible non-TP setup TSTEP.
- TP4 device actions and CPU sequencing decisions use pre-TP4 inputs.

#### 5.2.8 TP4

- A pending read commits `DB_READ_TO_AC`.
- The selected controller captures DB for a pending write.
- An accepted `IO_CLEAR_AC_REQ` clears AC.
- An accepted `IO_SKIP_REQ` increments PC.
- `IOT_TRANSFER` clears to `NONE`.
- Controller-local actions assigned to TP4 commit.
- Interrupt and sequencing decisions commit simultaneously.

No result committed at a TP may affect another action or decision committed at that same TP.

---

## 6. INTERRUPT
- Sequence defined by control

### 6.1 TS1–TS4
- Save PC
- Load vector

### 6.2 TP4
- Return to FETCH

---

## 7. DMA

Each DMA major-state cycle with a valid controller selection transfers exactly one memory word at TP2.

### 7.1 TS1

If no controller is selected:

- the external DMA arbiter evaluates pending request channels
- the lowest-numbered pending requester is selected
- the selected DMA_GRANT_ID commits at TP1

If a burst continues:

- the active grant remains selected;
- arbitration is not repeated.

### 7.2 TP1

- A new DMA_GRANT_ID commits when arbitration was required.
- No memory transfer commits.

### 7.3 TS2

The granted controller:

- drives MFB;
- drives AB;
- asserts /RD or /WR;
- drives MDB for a DMA write.

For a DMA read, memory drives MDB.

### 7.4 TP2

- One DMA memory transfer commits.
- For a read, the granted controller captures MDB.
- For a write, memory captures MDB.

### 7.5 TS3

- Completion of the TP2 transfer is available to the granted controller and DMA arbiter.

### 7.6 TP3

- The controller updates its complete-operation address.
- The controller updates its remaining operation word count.
- The DMA arbiter increments the active burst count.

### 7.7 TS4

The DMA arbiter determines whether DMA service continues.

- If the current burst continues, aggregate `/DMA_REQ` remains asserted.
- If the current burst ends, aggregate `/DMA_REQ` is deasserted.
- Pending controller request lines may remain asserted after a burst ends.

### 7.8 TP4

```text
/DMA_REQ = 0 -> MS_NEXT = DMA
/DMA_REQ = 1 -> MS_NEXT = FETCH
```

At a terminating TP4:

- the previously selected controller releases MFB, AB, MDB, /RD, and /WR
- the arbiter sets DMA_GRANT_ID to 15
- CPU ownership resumes during the following FETCH TS1

Aggregate `/DMA_REQ` remains deasserted throughout the intervening FETCH, optional DEFER, and EXECUTE major states while `DMA_ENABLE = 0`.

During EXECUTE TS4:

- controllers establish `/DMA_REQ[n]`
- the arbiter asserts combinational `DMA_ENABLE`
- separate combinational aggregation logic continuously derives aggregate `/DMA_REQ`
- `/DMA_REQ[n]`, `DMA_ENABLE`, and aggregate `/DMA_REQ` settle before TP4

At EXECUTE TP4, CPU control samples aggregate `/DMA_REQ` for the major-state transition decision.

The transition decision uses the aggregate value established during TS4. No value committed at TP4 affects that same TP4 decision.
