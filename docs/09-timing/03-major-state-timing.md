# Major State Timing

## 1. Purpose
Defines timing behavior of each Major State using TS/TP model.

---

## 2. Core Model
- TS = setup/stabilization window
- TP = state transition event

All state changes occur exclusively at TP: captured at its leading edge, visible as it ends, when TS changes.

---

## 3. FETCH

### 3.1 TS1 — Address Setup
- MA_SRC = PC (PC selected as MA input)
- ALU forms PC + 1

### 3.2 TP1
- MA loaded from PC; PC loaded with PC + 1 (MA receives the pre-increment PC)

### 3.3 TS2 — Memory Access
- MA drives AB
- /RD asserted
- Memory drives MDB

### 3.4 TP2
- MB loaded from MDB; IR loaded from MDB

### 3.5 TS3 — Address Formation
- EA formation from IR[6:0] and the page of MA
- OPR: the pass unit and, for Group 2, the skip decision

### 3.6 TP3
- EA_ADDR loaded
- Direct JMP: PC loaded with the formed address; with a field change pending, II clears
- OPR: AC and L loaded from the pass unit; Group 2 also loads SKIP and captures HLT; Group 3 also loads MQ

### 3.7 TS4 — Finalization
- Group 2 OPR with SKIP set: ALU forms PC + 1

### 3.8 TP4
- Group 2 OPR with SKIP set: PC loaded with PC + 1
- Direct JMP: a pending instruction field is applied (IF loaded, CIFP cleared)
- MS transition decision; a direct JMP or an OPR completes here

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

### 4.5 TS3 — Auto-Index (conditional)
- if EA_ADDR is within auto-index range: MB incremented

### 4.6 TP3
- MB updated with incremented value (auto-index only)

### 4.7 TS4 — Resolution
- MB drives the resolved address
- if auto-index: /WR asserted, MFB_SRC = IF, incremented value written back to the pointer location

### 4.8 TP4
- EA_ADDR loaded from MB (final resolved effective address)
- JMP I: PC loaded from MB, a pending instruction field applied, and the instruction completes
- Otherwise: MS transition to EXECUTE

---

## 5. EXECUTE
- Instruction-dependent behavior
- Uses full TS1–TS4 structure

### 5.1 TP4
- Interrupt condition evaluated
- Transition to INTERRUPT, DMA, or FETCH

---

### 5.2 EXECUTE: External IOT

Applicable context:

```text
MS = EXECUTE
IR_IS_EXTERNAL_IOT = 1
```

#### 5.2.1 TS1

- `IOT_ACTIVE` is asserted.
- `IOA` and `IOP` are valid.
- Controllers evaluate address match.
- The selected controller decodes IOP.
- TS1 is selection and decode only; the selected controller requests no transfer, AC clear, or skip:
  - `IO_READ_REQ != 1 AND IO_WRITE_REQ != 1 IF TS = 1`
  - `IO_CLEAR_AC_REQ != 1 AND IO_SKIP_REQ != 1 IF TS = 1`

#### 5.2.2 TP1

- No external-IOT action commits.

#### 5.2.3 TS2

- The selected controller may assert `IO_READ_REQ` or `IO_WRITE_REQ` for a transfer during TS3.
- The selected controller may assert `IO_CLEAR_AC_REQ` for an operation assigned to TP2.
- `IO_SKIP_REQ` is valid only during TS4:
  - `IO_SKIP_REQ != 1 IF TS = 2`

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
- The selected controller may assert `IO_CLEAR_AC_REQ` only when no read transfer is pending, because a read cannot use an AC cleared at the same TP. A pending write uses the AC committed at TP2:
  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1`
- `IO_SKIP_REQ` is valid only during TS4:
  - `IO_SKIP_REQ != 1 IF TS = 3`

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
- The selected controller may assert `IO_CLEAR_AC_REQ` only when no read transfer is pending, because a read and a clear both load AC. A clear may commit with a skip, because the clear does not use the ALU:
  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1`
- The selected controller may assert `IO_SKIP_REQ` from stable registered controller state.
- No read or write request is made during TS4, because its transfer would fall outside the major state; `IOT_TRANSFER` clears to `NONE` at TP4:
  - `IO_READ_REQ != 1 AND IO_WRITE_REQ != 1 IF TS = 4`
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
- Sequence defined in [Interrupt Execution §4](../03-microarchitecture/08-interrupt-execution.md#4-execution-sequence)

### 6.1 TS1–TS4
- TP1: MB ← PC, MA ← 0000
- TP2: IB ← IF and DF; IF, DF, and DIF cleared; CIFP cleared
- TP3: M[0:0000] ← MB (the return address)
- TP4: PC ← 0001, IE cleared

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

The granted controller, in this TS only:

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

- the previously selected controller has driven none of MFB, AB, MDB, /RD, and /WR since it released them at the end of TS2
- the arbiter sets DMA_GRANT_ID to 15
- CPU ownership resumes during the following FETCH TS1

Aggregate `/DMA_REQ` remains deasserted throughout the intervening FETCH, optional DEFER, and EXECUTE major states (EXECUTE is omitted for a JMP or an OPR) while `DMA_ENABLE = 0`.

During the TS4 that completes the instruction, in which [`INSTR_END`](../04-control/20-control-output-definitions/02-architectural-control-signals.md#410-instruction-end-instr_end) is asserted:

- controllers establish `/DMA_REQ[n]`
- the arbiter asserts combinational `DMA_ENABLE`
- separate combinational aggregation logic continuously derives aggregate `/DMA_REQ`
- `/DMA_REQ[n]`, `DMA_ENABLE`, and aggregate `/DMA_REQ` are stable at least `T_CS` before TP4, the TP that accepts it ([External Inputs §2](../04-control/10-control-input-definitions/04-external-inputs.md#2-timing-model))

At that TP4, CPU control samples aggregate `/DMA_REQ` for the major-state transition decision.

The transition decision uses the aggregate value established during TS4. No value committed at TP4 affects that same TP4 decision.

### 7.9 Halt Between DMA Cycles

Single Step may commit `RUN ← 0` at DMA TP4. When the burst continues, `MS` holds `DMA` while halted (section 8.1):

- `/DMA_GRANT` is deasserted while `RUN = 0`
- the selected controller holds its request and prepared transfer
- the arbiter holds `DMA_GRANT_ID`, burst-enabled state, and burst count
- no DMA transfer occurs while halted
- CONTINUE resumes at DMA TS1 with the same selection, unless an EXAMINE or DEPOSIT made FETCH the held state

See [DMA Execution §4](../03-microarchitecture/10-dma-execution.md#4-halting-between-dma-cycles).

---

## 8. Halted State and Console Transactions

### 8.1 Main Timing While Halted

A transition to the halted state commits only at TP4.

When TP4 commits `RUN ← 0`:

- TSEQ completes that TP4
- TSEQ stops at the first TSTEP of TS1
- MS holds the value committed at that TP4

While `RUN = 0`:

- TSEQ does not advance
- no main-sequence TP occurs
- MS and TS are held
- front-panel interaction does not modify TSEQ, MS, or TS, except that START, EXAMINE, and DEPOSIT load MS with FETCH

When a console TP commits `RUN ← 1`, TSEQ resumes at the first TSTEP of TS1:

```text
START     → FETCH TS1
CONTINUE  → TS1 of the held MS (FETCH after an EXAMINE or DEPOSIT)
```

### 8.2 Console Transaction

A console transaction executes one accepted console command while `RUN = 0`.

Sequence:

```text
accepted command latched
    →
console transaction timer runs for 7 setup TSTEPs
    →
TP_FP (two TSTEPs)
    →
latched command cleared as TP_FP ends
```

Properties:

- The console transaction is the single TS-equivalent evaluation window for the command.
- The latched command is stable from the start of the transaction through TP_FP.
- The control word is evaluated from the latched command for the whole transaction.
- The transaction lasts 9 TSTEPs, with a two-step TP_FP ([Timing Architecture §5.1](./02-timing-architecture.md#51-structure)). That allows 7 steps of setup, as in the longest main-sequence read, and the same write pulse and hold as a main-sequence write.
- A console memory read drives AB and MFB for the whole transaction, and MB captures MDB at TP_FP, matching TS2 and TP2.
- A console memory write commits at TP_FP, matching TP2.
- TP_FP commits every control-word result that a main-sequence TP commits, including `RUN_NEXT`, `HLT_REQ_NEXT`, and, when `MS_LOAD = 1`, `MS_NEXT`.
- Only one console transaction is in progress at a time.
- The console transaction timer never runs while `RUN = 1`.

Command acceptance is defined in [External Inputs §4.1](../04-control/10-control-input-definitions/04-external-inputs.md#41-console-command-acceptance).

---

## 9. State Invariants

These conditions hold in every reachable state, because of how the sequencing above commits state. Control need not define behavior for a state that violates one. The ROM-generation tools use them to exclude unreachable states; they are not requirements on any input.

Each invariant is written `REQUIREMENT IF CONDITION`: whenever the condition holds, so does the requirement.

### 9.1 DEFER Follows an Indirect MRI

DEFER is entered only from FETCH TP4 when `IR_INDIRECT = 1`, and IR is loaded only at FETCH TP2. IR therefore stays indirect throughout DEFER, including while halted in DEFER by Single Step:

- `IR_INDIRECT = 1 IF MS = DEFER`

### 9.2 Pending External-IOT Transfer

`IOT_TRANSFER` leaves `NONE` only by a request accepted at external-IOT TP2 or TP3 (sections 5.2.3 and 5.2.5), and returns to `NONE` no later than TP4 (section 5.2.8). A transfer is therefore pending only during external-IOT TS3 or TS4:

- `IOT_READ_PENDING = 0 AND IOT_WRITE_PENDING = 0 IF NOT (MS = EXECUTE AND IR_IS_EXTERNAL_IOT = 1 AND (TS = 3 OR TS = 4))`

`IOT_TRANSFER` records one direction, so at most one pending flag is set:

- `IOT_WRITE_PENDING = 0 IF IOT_READ_PENDING = 1`

### 9.3 An IR_NO_EXECUTE Instruction Never Reaches EXECUTE

EXECUTE is entered only from FETCH TP4 or DEFER TP4 when `IR_NO_EXECUTE = 0` ([Sequencing and Internal Direct Control §3.2.2, §3.2.4](../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#322-fetch-transition-without-indirection)), and IR is loaded only at FETCH TP2. IR therefore never holds a JMP or an OPR in EXECUTE, including while halted in EXECUTE by Single Step:

- `IR_NO_EXECUTE = 0 IF MS = EXECUTE`
