# Full Documentation Review (2026-11-22)

Proposals for the user's approval. **Only D1 has been applied. Everything else here is a proposal.** This is a branch working file: resolve it before `option2/` is removed.

Scope: all 104 files that were under `docs/` at the time, read in full, in the working tree that has groups A to E, R1 (less one held line), R2, and R3 applied. Diagram images were not reviewed. Outside `docs/`, only what was needed to check a finding.

How sure each finding is:
- **Tested**: reproduced with the simulator or tools.
- **DEC**: checked against a DEC manual.
- **Secondary**: checked against a non-DEC source.
- **Read**: follows from the documents' own text, by reading.

Approve by ID. D items are design questions. A items are accuracy fixes. H items are readability fixes.

---

## Q. The held 08 rule

**Applied 2026-11-22** as proposed below.

**Current:** "interrupt recognition at a TP that applies a pending instruction-field change" is illegal.

**It is wrong (DEC, Tested).** KM8-E Theory of Operation:
- §2.9.2: IF is loaded from the instruction buffer at TP4, "so that memory is not disturbed".
- §2.10.3: that TP4 is FETCH's for a direct JMP or JMS and DEFER's for an indirect one, "to ensure that there is no address mixup during the current memory cycle".
- §2.10.1: INT INHIBIT is "negated at TP3 whenever a JMP or JMS instruction occurs", which "prevents any memory field from being lost during a program interrupt".

So on the 8/E, the TP that applies the field change *is* the TP4 at which a JMP's interrupt is recognized. The inhibit is already off, because it cleared one TP earlier.

Here, for `CIF 2` then an auto-indexed `JMP I` with a request pending (simulator):

| TP | What commits | II after | CIFP after | IF after |
|---|---|---|---|---|
| DEFER TP3 | II clears | 0 | 1 | 0 |
| DEFER TP4 | pointer written in field 0; IF and PC load; INTERRUPT selected from II = 0 | 0 | 0 | 2 |
| INTERRUPT TP2 | IB saves IF = 2; IF clears | 0 | 0 | 0 |
| INTERRUPT TP3 | 0500, the JMP target, written to field 0 address 0000 | 0 | 0 | 0 |

The decision doesn't need the new IF. It needs only II = 0 before the TP. INTERRUPT reads IF afterward.

The v1 rule named "the same EXECUTE TP4". It could never fire, because v1 applied the field at EXECUTE TP1. Generalizing it to "a TP" in slice B made it forbid correct behavior.

**Proposed replacement (two bullets):**
- interrupt recognition at a TP4 when `II` was set before that TP
- interrupt entry after a JMP or JMS with a pending field change saving the old instruction field in `IB`

---

## D. Defects and decisions

| ID | Evidence | Problem | Recommendation |
|---|---|---|---|
| D1 | Tested | MTS §5.2.5 excluded an AC clear at TS3 with a pending write, so DMAN lost its clear, its TP3 capture and its buffer read. DMAN §23.4 also made a response depend on DB in the same TS, which breaks the TP(n-1) invariant. | **Applied 2026-11-22, approved as revised:** only a pending read excludes the clear; DMAN always requests the read and answers from the function registered at TP3. Regression test: `sim/cpu/tests/test_external_iot_write_clear.py` (needs the user's promotion). |
| D2 | Tested | MTS §5.2.7 declares AC clear with skip at TS4 impossible. 07-io/02 §7 lists "skip and clear" and "skip, write, and clear" as valid. The ROM does neither. | **Applied 2026-11-22:** AC_CLEAR loads `AC_SRC` = ZERO (code 5, reserved since decision 13), so it no longer uses the ALU, and the skip exclusion is gone. Three phase-9 assertions updated; skip-and-clear tests added. |
| D3 | Secondary | RK8E §9, §26.4 to §26.6 and §30.3 increment the current address *before* each transfer, so the bootstrap loads from 0001. SIMH transfers at the address, then increments, and boots OS/8 that way. If SIMH is right, OS/8 won't boot as written (not run: there is no RK8E simulator model here). | **Applied 2026-11-23:** transfer at the Current Address, then increment at TP3; the bootstrap loads from 0000. Confirmed by DEC: PDP-8/E Small Computer Handbook (1973), RK8-E "Current Address Register" (p. 6-70), "incremented after each memory transfer"; agrees with SIMH. The RK8 maintenance manual the user supplied is the older RK08 and was not used. |
| D4 | Read | Controllers may act on `/INITIALIZE` only at a TP, but no TP occurs during the power-on reset, so controllers are never initialized at power-on. | **Applied 2026-11-22 (option A):** the power-on reset loads CLEAR into the console latch and ends with that transaction; controllers and the arbiter initialize at its TPC, and CLEAR's micro-operations clear AC, L, IE. Matches the 8/E, whose power-up INITIALIZE is the CLEAR key's signal (HMM1 §3.16). The simulator powers on the same way; test added. |
| D5 | Read | CSO §8.1 never releases the EEPROM outputs after the copy. Both the EEPROM and the SRAM would drive every control-word bit. | **Applied 2026-11-23:** CSO §8.1, EEPROM `/OE` and SRAM `/OE` from `LOADING` in opposite senses, the SRAM enabled one TCLK later by a second flip-flop; the reset ends after it. Docs only. |
| D6 | Read | The commit edge is ambiguous. TP is the whole last step and "only the TP rising edge is significant" (commit at the start of step N), but TS changes "on the next clock edge", and timing.md budgets all N steps. The difference is one 50 ns step, equal to the smallest margin. | **Applied with C5.** |
| D7 | Read | Timing §11.3's "about 104 ns", and timing.md's main tables, assume decision 11, which was rejected. The figure is about 126 ns (24 ns margin to `CW_VALID`, not 46). | **Closed 2026-11-23:** recomputed by the C5 timing budget; the 104 ns figure is gone from the docs. |
| D8 | Read | Control Addressing, Constraints, Control Word and 04 Invalid Conditions forbid things v2 has: IR bits into the pass unit, RUN-selected overlays, gate-decoded `INSTR_END`, the timing ROM, the stored SKIP. They also call the decoded `/DMA_GRANT` invalid. | **Applied 2026-11-23:** Control Model §8.4 lists the realizations outside the control word; Control Addressing, Control Constraints and 04 Invalid Conditions refer to it (overlay selection now includes RUN; `/DMA_GRANT` from the `MS_EFF` decode). |
| D9 | Read | MCS §2.7, §3.5, §6.1, §6.12 and §12.2 require a valid value in every field every cycle, with "no don't care states". Control Word §5.6's bit sharing, which the packer uses, relies on the opposite. | **Applied 2026-11-23:** MCS §2.7, §3.3, §3.5, ALU_A_SRC, §6.12 and §12.2 require a valid value only where Value Required When holds (Control Word §5.6). |
| D10 | Read | Direct control §3.4.2 assigns nothing while a HLT is in IR outside FETCH TS3 (or STOP at completion), so `HLT_REQ_NEXT` comes from the default, which §3.4 forbids. | **Applied 2026-11-23:** §3.4.2 excludes exactly the two capture contexts; ROM images identical. |
| D11 | DEC | A direct JMP loads IF at FETCH TP3, and a JMS at EXECUTE TP1. The KM8-E loads both at the preceding state's TP4 (Q). Only II at TP3 matches. Not programmer-visible. Docs and spec §3.1 claim the field timing is DEC's. 08/03 §12 also cites its KM8-E quotation as §2.9, and it is §2.10.1. | **Applied 2026-11-22 (option A):** a direct JMP loads IF and clears CIFP at FETCH TP4, matching KM8-E §2.10.3 and JMP I; JMS keeps EXECUTE TP1, documented in 08/03 §12 (matching it needs JMS in `IR_CLASS`). Citation fixed to §2.10.1. Test added. |
| D12 | Read | 06-memory/02 and 07-io/05 say memory captures at the TP. 06-memory/04 and timing §11.3 say it stores when `/WR` ends, one step earlier. | **Applied with C5:** `WR_VALID` removed; memory writes within the first step of a two-step TP. |

---

## C. Constraint audit (2026-11-22)

The invariant: in TSn, everything is derived from values committed by TP(n-1). It was checked, with the other stated timing, stability and ownership constraints, against these:

- read in full for the audit: the three controller contracts; the IOT interface, I/O timing, controller, DMA and arbitration contracts; IOT, DMA, console and interrupt execution; sequencing; major-state timing and timing architecture; four memory documents; external inputs; the interface direct control
- checked by searches and the earlier full read only: everything else
- the packed control store, for what each strobe's address depends on

Clean results:

- All 4096 instruction words, in four state patterns each (16,384 runs, no devices attached): the simulator detected no violation. It models no propagation delay, so this says nothing about C1 and C2.
- External IOT, with D1 promoted in scratch: all 240 legal schedules without skip plus clear are correct. The 60 with skip plus clear at TP4 are all wrong (D2). The 132 illegal read-plus-clear schedules were not judged.
- DMAN was the only controller response that depended on DB.

### Violations

| ID | Evidence | Constraint | Violation | Recommendation |
|---|---|---|---|---|
| C1 | Read, packing | Timing §11.2: an immediate-effect signal never depends on an input that can change during a TS | `/DB_READ` and `/DB_WRITE` share their SRAM address with the controller responses in IOT TS3 and TS4, and with `/INT_REQ` in TS4. `/INITIALIZE` shares the sequencer's address with STOP, the mode switches, `/DMA_REQ` and the interrupt request. An address change can glitch each strobe. (Includes what was called D13.) | **DB strobes applied** with C5. The rest, correction 2, applied with C5. Proven equivalent to the packed ROM in 35,462 cycles; no `/RD` or MDB drive in any IOT EXECUTE, including after IOTs, at Single Step halts, and before DMA. |
| C2 | Read | External Inputs §2, Sequencing §9: inputs are stable for the whole TS | STOP and the two mode switches have no defined capture point, `/INT_REQ` has only "must be synchronized", and FP_SR is not defined as an input. A change within T_CS of a TP can commit a wrong sequencer word: RUN, HLT_REQ or MS. | **Applied 2026-11-22:** panel input register (STOP, the mode switches, FP_SR, FP_IF, FP_DF) captured at every TP, and at command acceptance while halted; FP_SR defined as an input; `/INT_REQ` treated like `/DMA_REQ`, no synchronizer. **`/IO_WAIT` removed (option A)**; the fallback if hardware needs it (B: a slow-TS3 request registered at TP2 and read by the timing ROM) is recorded in I/O Timing §5. FP_SR's control-use classification (`value`, like FP_IF) is left for the user's review. |
| C3 | Tested | The arbiter decides in TS3 from values committed by TP2 | The docs update the controller's word count at TP3 and don't say when the request drops. A request derived from that count is still asserted when the arbiter decides, so the finished controller stays selected and can be granted a cycle with nothing to transfer. The arbiter's tests work because their master drops the request at TP2, a rule the docs don't state. | **Applied 2026-11-22:** the request changes at the TP2 that completes the transfer (Controller Contract §9.2, DMA Interface §6.3 and §6.5, RK8E §26.2, DMA Arbitration §11). Docs only: the simulator's master already did this. |
| C4 | Tested | A selected controller must transfer; DMA Execution §5 says a state with no selection exits | A suspended burst keeps a canceled controller selected. With no selection, burst-enable never clears, so a new request keeps the CPU in DMA, contrary to §5. | **Applied 2026-11-22:** DMA Arbitration §13.3. TP1 drops a held selection with no request, without arbitrating; TP3 with no selection clears burst-enabled. Arbiter model fixed, two tests added. |
| C5 | Read | Memory Timing §4, §5: AB is stable while a strobe is asserted | DMA controllers release `/RD` and `/WR` at TP4, but update the address at TP3. DMA Interface §5 gives the strobes no window. | **Applied 2026-11-22**, after a full readability pass: two ranks; a two-step TP where memory can be written; slow 6/8/7/7; DB strobes decoded with `DB_VALID`; decision 11a; memory limits that admit MRAM; strong pull-ups; the SRQ qualifier; ACT or F on timed paths. Needs one promotion (control-word schema, line references only). Correction 2 (`/INITIALIZE` decoded; `/RD` and the MDB drive gated off in an IOT's EXECUTE) applied too, after the user's question about `/RD` was answered. |
| C6 | Read | Sequencing §7, Controller Contract §5: one defined result per TP | A device event setting a flag and an IOT clearing it at the same TP have no precedence (KL8E, PC8E, RK8E Done). An event can be lost. | **Applied 2026-11-23:** Controller Contract §5.1, the event wins (`FLAG_next = EVENT OR (FLAG AND NOT CLEAR)`), except `/INITIALIZE` and an aborting IOT (DCLC). Each flag's clear list in KL8E, PC8E and RK8E points to it. Docs only. |
| C7 | Read | RK8E §15: DCLD while busy is refused | §18.2.3 starts the recalibration unconditionally. | **Applied 2026-11-23:** §18.2.3 refuses DCLD while busy, as §15 says. Matches SIMH (`RKX_CLD` sets `RKS_BUSY` when `rk_busy`); DEC's handbook (1973, p. 6-72) is silent on busy. |
| C8 | Read | Registers: CIFP = 1 holds II set | START clears II and leaves CIFP. (Harmless: IE is also clear, and ION and RTF set II again.) | **Applied 2026-11-23:** exception stated in Registers (CIFP, II) and Interrupt Enable and Inhibit; behavior kept, matching the KM8-E (next JMP or JMS applies the field). |
| C9 | Read | External Inputs §2: inputs don't bypass control or load registers | GTF takes INT REQ, and OSR takes FP_SR, straight into AC. | **Applied 2026-11-23** with C2: External Inputs §2 says an input reaches a register only as data selected by a control-word micro-operation. Docs only; not parsed. |

Already listed: D2 (skip plus clear), D4 (initialization without a TP), D6 (which edge commits), D8, D9 and A1.9 (rules that forbid SKIP and other v2 logic), A2.29 (a PC8E action during TS3).

D6 was first argued here from the `WR_VALID` wording, toward a commit at the end of step N. That was wrong: see D6.

### Found during the C5 discussion

| ID | Evidence | Constraint | Violation | Recommendation |
|---|---|---|---|---|
| C11 | Tested | Console Execution §3: a halted Single Step resumes exactly where it stopped | EXAMINE and DEPOSIT overwrite EA_ADDR, so CONTINUE from a DEFER or EXECUTE halt can finish at the wrong address. | **Applied 2026-11-22:** EXAMINE and DEPOSIT load MS with FETCH (Sequencing §3.2.12), as START does; a held DMA selection continues at the next DMA entry. Matches HMM1 §3.8.2. Tests added. |
| C12 | Secondary | RK8E §15 and §18.2.3: DCLD clears only Control Done, and the controller is busy until recalibration completes | DEC (Small Computer Handbook 1973, p. 6-72) says DCLD clears the Status Register; SIMH's DCLR clears status before every function, even a refused one. In SIMH a seek or recalibrate does not make the controller busy: it sets Done when started, and again on completion if Command Register bit 4 (set Done on seek done, DEC p. 6-70) is set; DEC's status has a separate head-in-motion bit (p. 6-71). | **Applied 2026-11-23:** DCLR clears status before every function; seek-only and DCLD set Done at start, leave the controller free, and use `STATUS[10]` (Head In Motion), with Done again on completion when `COMMAND[7]`. DEC handbook pp. 6-72 to 6-74; DCLD as a seek follows SIMH. |

### A consequence of the invariant, for decision

| ID | Evidence | Behavior | Recommendation |
|---|---|---|---|
| C10 | Tested | KRB, TLS, and KIE disabling clear their request at TP4, where interrupt recognition still sees the pre-TP4 value. After `ION; KRB` the interrupt is taken with no device requesting. KCC and TCF, which clear by TP3, don't do this. RRB, PLS, DLDC and DCLS have the same shape by reading. CAF is special-cased for exactly this (08/02 §6). | **Applied 2026-11-23:** KRB, TLS, KIE, RRB, PLS, DLDC and DCLR (DCLS, DCLC, DCLD) request in TS2 and commit at TP3; Controller Contract §9.1 and §9.2 require any interrupt or DMA-request clear by TP3 (CAF excepted). Both KL8E models changed; four system tests and the unit harness updated. No ROM change. |

---

## A1. Wrong because of this branch

**Applied 2026-11-23**, all 36 (A1.35 in part: its §9.3 went with `/IO_WAIT`). A1.36's reason is the one in `spec.md`. ROM images identical.

### Architecture, ISA, overview
| ID | Where | Now | Fix |
|---|---|---|---|
| A1.1 | registers, IF | Changes only where JMP or JMS applies a field | Add interrupt entry (clear) and LOAD ADDRESS |
| A1.2 | registers, PC | After TP1, modified only by skip, JMP, JMS | Add interrupt entry and the console operations |
| A1.3 | registers, CIFP | While set, II is held set | Except between DEFER TP3 and TP4 of a JMP I |
| A1.4 | registers, MB | MB can't be bypassed; the only staging point | Except IR's load from MDB |
| A1.5 | ea-generation §4, §5; addressing §4.2 | Page from PC | The instruction's address (held in MA) |
| A1.6 | system-overview §4.1 | All behavior is ROM entries | Except the pass unit's stage selection |
| A1.7 | encoding-model §7 | Titled "Execute Timing States" | "Operation Ordering" |

### Microarchitecture
| ID | Where | Now | Fix |
|---|---|---|---|
| A1.8 | micro-operations §2 | No μop may load MDB into anything but MB | Add `MDB_TO_IR` |
| A1.9 | micro-operations §3; sequencing §4, §11, §12; execution-model §6 | Stored condition results are prohibited | Allow `SKIP`, the one stored decision |
| A1.10 | sequencing §8.1 | All instruction definitions assume EXECUTE | Only MRI (not JMP) and IOT |
| A1.11 | fetch-defer §5 | Two PC-increment bullets (left by R1) | Delete the first |
| A1.12 | group1-execution §4 | Stage B sentence repeats the table (left by R2) | Delete it |
| A1.13 | group2-execution §6 | The halt is consumed "after" the skip increment | "concurrently with" |

### Control
| ID | Where | Now | Fix |
|---|---|---|---|
| A1.14 | control-addressing §2.1 | Fixed values in states without a variant | `IR_CLASS` supplies the variant there |
| A1.15 | control-addressing §5.3 | OPR bits reach the address through an overlay | They reach only the pass unit; HLT reaches A1 |
| A1.16 | control-model §5.1, §9 | IR stable for the instruction; only IR, MS and registers persist | Valid from FETCH TP2; add SKIP and MAPR |
| A1.17 | input index §7 | Its own rule makes 15 OPR inputs "specification gaps" (Tested: analyzer report) | List them, path "OPR pass unit" |
| A1.18 | flags, CIFP | II_CLEAR selected only when CIFP = 0 | In FETCH TS1; a JMP or JMS clears II with CIFP = 1 |
| A1.19 | flags, ACN, ACZ, LZ | Drive PC_INC | Drive `OPR_SKIP_REQ` |
| A1.20 | IR-derived, IR_CLASS | Consumers omit FETCH TS4 | Add it |
| A1.21 | IR-derived, GROUP2 | Consumed by IR_NO_EXECUTE | It isn't; delete |
| A1.22 | IR-derived, IR_ADDR, IR_ZERO_PAGE | Consumers omit IR_ADDR_TO_PC | Add it |
| A1.23 | derived flags | AUTO_INDEX_REQUIRED's users omit the timing ROM | Add it |
| A1.24 | MCS §6.6, §7.11, §8.3 | Only MB may take MDB | Add IR |
| A1.25 | MCS §7.3.3 | `EA_FORMED = f(IR, PC, IR.P)` | `f(IR, MA[11:7])` |
| A1.26 | MCS AC_SRC | ALU is the source of all logical AC loads | Or the pass unit |
| A1.27 | MCS §8.6, §9.7 | Register input domains omit the pass unit and SKIP path | Add both |
| A1.28 | MCS §9.2.1, §9.4 | Lists omit the new PC loads | Complete them |
| A1.29 | output index | INSTR_END under Memory Interface | A DMA Interface heading (parsed: test it) |

### Buses, interrupts, timing
| ID | Where | Now | Fix |
|---|---|---|---|
| A1.30 | signal-classes §4.3; class B §6.5.4; 05/11 §2; io-architecture §10 | INSTR_END absent, so it would not reach the backplane | Add it as a CPU-to-arbiter signal |
| A1.31 | interrupt-entry §14, §15 | JMP execution is in MRI Execution | Fetch & Defer |
| A1.32 | skip-model §15 | Group 2 performs "later" AC operations | At the same TP3 |
| A1.33 | terminology §6.2 | MS is independent of timing | MS selects the TS lengths |
| A1.34 | timing-architecture §9.2 | TP count per cycle changes | It is always four |
| A1.35 | timing-architecture §9.3, §10 | Step skipping and shift-enable wording | Delete (counter design) |
| A1.36 | docs generally | IOT keeping EXECUTE, unlike the 8/E, is recorded only in option2 | State it in IOT Execution §3 |

---

## A2. Wrong before this branch

**Applied 2026-11-23**, except A2.28 (fixed by C12) and the first half of A2.22 (fixed by C5). ROM images identical. A2.24's write ownership is prose beside the parsed read block (the extractor reads one block per label).

| ID | Where | Now | Fix |
|---|---|---|---|
| A2.1 | addressing §9.2 | The pointer is read in DF | Read in IF; its value is used in DF (or IF for JMP, JMS) |
| A2.2 | addressing §11 | Off-page targets are within DF | Or IF, for JMP and JMS |
| A2.3 | registers, DIF | Written by CDF | CIF |
| A2.4 | registers, MA; dataflow §2; 05/09 §3, §4, §6 | MA is the only memory address source | PC also, for EXAMINE and DEPOSIT |
| A2.5 | registers, HLT_REQ, IE | Stable within a major state or instruction | They change at TP2 and TP3 |
| A2.6 | registers, MQ | Multiply/divide microcode writes it | No EAE; delete |
| A2.7 | registers, MS; state-model §5.1, §11; execution-model §11 | Changes only at TP4 | Also START at TPC, and power-on |
| A2.8 | architecture README §4 | Interrupts need only IE and a request | And II clear, at instruction completion |
| A2.9 | micro-operations §2 | MB is undefined after one TS | DEFER uses it two TSs later; state the real lifetime |
| A2.10 | micro-operations, MEM_* | Address is "specified by MA" | MA or PC |
| A2.11 | iot-execution §11 | CPU μops only for reads | Also write, clear, and skip |
| A2.12 | interrupt-execution §2 | Entry depends on IE and the request | And II; link the recognition doc |
| A2.13 | console §5 | Every console operation loads MA and EA_ADDR | EXAMINE and DEPOSIT only |
| A2.14 | control-model §5.2 | Examples IR_IS_ISZ, SMA_enable | Use signals that exist |
| A2.15 | control-word §8.3 | State always updates; no hold | MS holds when MS_LOAD = 0 |
| A2.16 | derived flags §1, §3 | Inputs are only IR fields and flags | And `/INT_REQ` |
| A2.17 | flags §2 | TP indexes off by one | TP(n−1) latches; changes after TP(n) |
| A2.18 | external inputs, /DMA_REQ | Consumed by /DMA_GRANT | It isn't; delete |
| A2.19 | MCS §7.2, §7.4, §9.3, §11.9 | CONST_1, Control path, MEM_WR | None exist; use the real names |
| A2.20 | MCS §9.4, §6.5, §8.2 | IDB_SRC selecting requires IDB_DRIVE | A select always holds a code; delete |
| A2.21 | MCS §11.11, §12.7 | No transitions within a TS | Stable after T_CS (§11.2) |
| A2.22 | ACS §1, §4.9 | All from the control word; INITIALIZE equation omits power-on | Correct both |
| A2.23 | direct control §3.3.8 | Single Step states omit DMA | Add it |
| A2.24 | interface control §5.4 | DMA ownership describes only a read | Add the write case |
| A2.25 | signal-classes §3.3, §6.3 | A[11:0], D[11:0]; no CLEAR or field switches | AB, DB; add them |
| A2.26 | io invalid conditions §4 | INITIALIZE lasts one TSTEP | One TS or console transaction |
| A2.27 | dma-arbitration §11 | DMA_ENABLE clears at TP3 | The retained burst-enabled state does |
| A2.28 | RK8E §12 against §11.3 | Seek sets Done always, or only when enabled | Only when enabled |
| A2.29 | PC8E §15 | The request is accepted during TS3 and at TP3 | At TP3 |
| A2.30 | MTS §5.1 | EXECUTE TP4 goes to INTERRUPT or FETCH | Or DMA |
| A2.31 | system-overview §5, §6; overview README §3; principles §3 | Memory, I/O and bus structure undefined | Update the status |
| A2.32 | iot.md §3 | SGT missing from the device 0 table | Add 6006 |
| A2.33 | encoding-model §4.1 | JMS omits where execution continues | "continue at Y+1" |
| A2.34 | opr README §3, §4 | Every bit is an independent operation | Except group and subgroup selectors |

---

## H. Human readability

**Mechanical items applied 2026-11-23:** H5, H8 to H15, H19 to H25. H16 dropped: §3.3.6 and §3.4.6 differ. H1, H2, H4, H6, H17 and H18 applied the same day; H3 skipped by the user (the DEC source key stays in `option2/spec.md` and the handoff, see O2).

| ID | Where | Problem | Fix |
|---|---|---|---|
| H1 | docs/README | No reading order, no status, four empty sections look finished | A reading path, and mark 10 to 13 as empty |
| H2 | 03 README | No list of its documents, no instruction-path overview | Add both |
| H3 | whole set | KK8-E, KM8-E, M8330 and MM1 are cited but never identified; the key is in option2 | A DEC references appendix |
| H4 | abbreviations | Many used names absent (DMA_ENABLE, EAI, IDB, TPC); §2's 2-to-4-letter rule is untrue | Complete it, and relax the rule |
| H5 | whole set | EA_fld, EA_field, EA_FIELD; MS_next, MS_NEXT; μstate, ustate | One spelling each |
| H6 | registers | Field-change timing repeated five times | Link the table in 08/03 §12 |
| H7 | registers, AC writers | One bullet holds three groups and three links | One bullet per group |
| H8 | iot.md §3.1 | A flags-word bit named "IR" collides with the register | Label it INT REQ, noting DEC's name |
| H9 | group 1 ISA | Table out of order; NOP is unnumbered between sections | Order the rows; move NOP |
| H10 | group 3 ISA | Leading spaces; SWP explained twice | Remove both |
| H11 | ea-generation §3, §6, §7 | "a EA_ADDR"; `EA_ADDR = EA_ADDR`; wrong cross-reference | Fix |
| H12 | ISA README | Describes PC_INC; omits 04-iot | Semantics only; add the link |
| H13 | execution-model §12.5 | Unlinked, incomplete document list | Link all |
| H14 | console §1 | "Section 4", "Section 10" (which is empty) | Link by name |
| H15 | 05 documents | "Section 4" means both a chapter and a local section | Link by name |
| H16 | direct control | §3.3.6 and §3.4.6 are identical | Keep one as prose (parsed: test it) |
| H17 | MCS §6 to §12 | The same exclusivity rules stated four to six times, with drift | State each once |
| H18 | constraints, invalid conditions | The "Constraint:" format hides the few rules that matter | A summary at the top of each |
| H19 | IR-derived | Empty consumer list; "switch multiplier quotient"; IR_WRITES_IF values say CIF only | Fix |
| H20 | IR-derived §2.4 | No Group 3 | Add it |
| H21 | signal-conventions | Stray ")", unreadable overbar, §8.4 at the wrong level | Fix |
| H22 | 08/03 §9, §13, §14 | List without a lead-in; FETCH-time title; wrong heading level | Fix |
| H23 | ownership-matrix §4.1; RK8E §26.3 | Stray punctuation | Fix |
| H24 | timing terminology §3.5 | A long parenthetical inside the input table | Move below the table |
| H25 | timing-architecture §5.1 | A paragraph carries the rationale, DEC, and the D2AB arithmetic | Three bullets |

---

## P. OPR pass unit: proposed `docs/03-microarchitecture/07-opr/00-pass-unit.md`

**Applied 2026-11-23**, corrected before adding: the MQ output applies CLA itself (it is not independent of the stages), stage E's RAR-with-RAL case, the full input path, the SKIP output, HLT outside the unit, and a CLA MQL example. Linked from the OPR README only; the parsed group files are unchanged.

The structure, inputs, outputs, and per-group behavior are microarchitecture, because they decide results: the stage order, what the skip logic sees, and SWP's simultaneous loads. Gates, parts, packages, and delays are electrical implementation and stay out. The group documents would keep their `OPR Pass` headings, which the extractor needs, and only their group-specific tables. The file name is outside the extractor's source list.

### Draft text

> # OPR Pass Unit
>
> ## 1. Purpose
>
> Defines the combinational unit that performs the register operations of every OPR instruction in one pass. Circuit realization and propagation delay belong to the implementation documents.
>
> ## 2. Structure
>
> ```text
>                  AC                                      L
>                  |                                       |
>                  +-------> skip logic <------------------+
>                  |             |                         |
>                  |             v                         |
>                  |           SKIP                        |
>                  |                                       |
>                  +-------> MQ output logic --> MQ        |
>                  |         (also reads MQ)               |
>                  v                                       v
>            A: clear AC                              A: clear L
>            (CLA or MQL)                               (CLL)
>                  |                                       |
>                  v                                       |
>            B: OR FP_SR (OSR)                             |
>               OR MQ    (MQA)                             |
>                  |                                       |
>                  v                                       v
>            C: complement AC                         C: complement L
>                  (CMA)                                 (CML)
>                  |                                       |
>                  v                                       v
>            D: 13-bit increment of L and AC together (IAC)
>                  |                                       |
>                  v                                       v
>            E: 13-bit rotate, or BSW of AC with L unchanged
>                  |                                       |
>                  v                                       v
>              AC input                                 L input
> ```
>
> The skip logic is beside the unit, not a stage of it. It and the MQ output read the registers directly, so neither sees a stage's result.
>
> ## 3. Interfaces
>
> | Input | Used by |
> |---|---|
> | AC | stage A, MQ output, skip logic |
> | L | stage A, skip logic |
> | MQ | stage B, MQ output |
> | FP_SR | stage B |
> | IR decodes | the selection of every stage |
>
> | Output | Loads | Selected by | When |
> |---|---|---|---|
> | AC result | AC | `OPR_PASS` | FETCH TP3, every OPR |
> | L result | L | `OPR_PASS` | FETCH TP3, every OPR |
> | MQ result | MQ | `OPR_PASS_TO_MQ` | FETCH TP3, Group 3 |
>
> ## 4. Effect on Each Group
>
> | Part | Group 1 | Group 2 | Group 3 |
> |---|---|---|---|
> | A, AC | CLA | CLA | CLA or MQL |
> | A, L | CLL | passes L | passes L |
> | B | passes | OSR | MQA |
> | C | CMA, CML | passes | passes |
> | D | IAC | passes | passes |
> | E | rotates, BSW | passes | passes |
> | MQ output | not loaded | not loaded | MQL: AC, or 0 with CLA. Otherwise MQ |
> | Skip logic | not loaded | loads SKIP | not loaded |
>
> ## 5. Examples
>
> | Instruction | Before | Through the unit | After TP3 |
> |---|---|---|---|
> | CMA IAC (7041) | AC = 1354 | C gives 6423, D gives 6424 | AC = 6424 |
> | CLA IAC (7201) | AC = 7070 | A gives 0000, D gives 0001 | AC = 0001 |
> | CLA SZA (7640) | AC = 0000 | skip logic sees 0000; A gives 0000 | SKIP = 1, AC = 0000 |
> | CLA OSR (7604) | AC = 7070, FP_SR = 0123 | A gives 0000, B gives 0123 | AC = 0123 |
> | SWP (7521) | AC = 1111, MQ = 2222 | A clears the AC path, B gives 2222, MQ output gives 1111 | AC = 2222, MQ = 1111 |
>
> ## 6. Invariants
>
> - The unit holds no state.
> - Every input is the value held before TP3. All outputs commit together at TP3.
> - IR bits select what each stage does. The control store selects only whether the results load.
> - A stage that is not selected passes its input unchanged.

---

## O. Needed before `option2/` is removed

| ID | Item |
|---|---|
| O1 | Five links from `docs/` to `option2/timing.md`: CSO §8.1 and §10, terminology §3.5, timing architecture §5.1 and §11.3 (with D6 and D7) |
| O2 | The DEC source key (H3), the IOT deliberate difference (A1.36), and the reasons for decisions 9 to 12 |
| O3 | References in code and READMEs: `rom/microcode/v2/README.md`, `tools/rom-generation/README.md` and `common/design.py`, `sim/cpu` design module and tests, `sim/io` `dma.py`, `sim/run_all_tests.py`, `sim/system` D2AB test |
| O4 | `option2/diagrams.md`: finish the diagram updates, or move the open list |
| O5 | This file |
| O6 | Schema cleanup: remove stale information from the schema objects (inventory in `option2/plan.md`, phase 10) |
