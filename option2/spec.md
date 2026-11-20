# Option 2 Architecture Specification: One-Cycle OPR and Direct JMP

Status: **draft for the user's review** (phase 1 of [plan.md](plan.md)). Nothing in `docs/`, `rom/`, `tools/`, or `sim/` changes on the strength of this document until the user approves it. Section 11 lists the decisions that need approval.

Companion documents: [timing.md](timing.md) (per-TS critical paths and the TS-length table) and [plan.md](plan.md) (phases, slices, phase 0 results).

DEC sources (handoff §4), cited as:
- **KK8-E**: KK8-E Central Processor Theory of Operation
- **M8330**: M8330 Timing Generator Theory of Operation
- **MM1**: PDP-8/E, 8/F, 8/M Maintenance Manual Volume 1, Processor (Sep 1973)
- **KM8-E**: KM8-E Memory Extension Theory of Operation

Quotations are those recorded in the handoff (§4). Page numbers are to be added when the scans are next opened.

---

## 1. Scope

| Instruction | v1 (today) | v2 (option 2) | PDP-8/E |
|---|---|---|---|
| OPR, groups 1, 2, 3 | FETCH, EXECUTE | **FETCH** | FETCH |
| JMP, direct | FETCH, EXECUTE | **FETCH** | FETCH |
| JMP I | FETCH, DEFER, EXECUTE | **FETCH, DEFER** | FETCH, DEFER |
| AND, TAD, ISZ, DCA, JMS (direct or indirect) | FETCH, (DEFER), EXECUTE | unchanged | same |
| IOT | FETCH, EXECUTE | **unchanged** | FETCH |

DEC: "A one-cycle instruction can be an OPR microinstruction, an IOT instruction, or a directly addressed JMP instruction." "A two-cycle instruction involving the DEFER state can only be a JMP." (KK8-E.)

**Deliberate difference from DEC: IOT keeps EXECUTE.** `docs/07-io`, the controller contracts, and the KL8E, PC8E, and RK8E models stay untouched. Phase 0 showed that D2AB's timing does not depend on IOT cost ([plan.md](plan.md), phase 0).

**Unchanged:**
- The ISA semantics (`docs/02-isa`), and so the reference model's instruction behavior.
- The interrupt entry sequence (INTERRUPT state).
- DMA cycles.
- The console transactions.
- IOT execution.

## 2. Instruction Classes

A new combinational **class decode** on the live IR produces `IR_CLASS[2:0]`:

| `IR_CLASS` | Class | IR condition (DEC bit numbers, bit 0 most significant) | Ends in |
|---|---|---|---|
| 0 | MRI other than JMP, IOT | opcode 0 to 4, or opcode 6 | EXECUTE |
| 1 | JMP direct | opcode 5, bit 3 = 0 | FETCH |
| 2 | JMP indirect | opcode 5, bit 3 = 1 | DEFER |
| 3 | OPR group 1 | opcode 7, bit 3 = 0 | FETCH |
| 4 | OPR group 2 | opcode 7, bit 3 = 1, bit 11 = 0 | FETCH |
| 5 | OPR group 3 without MQL | opcode 7, bit 3 = 1, bit 11 = 1, bit 7 = 0 | FETCH |
| 6 | OPR group 3 with MQL (MQL, SWP, and their combinations) | opcode 7, bit 3 = 1, bit 11 = 1, bit 7 = 1 | FETCH |

Code 7 is spare. Class 6 exists only so that the control store can assert `MQ_LOAD` for MQL; every other OPR function is selected by IR bits in the pass unit (section 4.1).

Two further predecodes, from the same gates, feed the sequencer (section 6.2):
- `IR_ONE_STATE = class 1, 3, 4, 5, or 6`, meaning the instruction ends at FETCH TP4.
- `IR_OPR_HLT`, the group 2 HLT bit, which v1 already decodes, but through `MAPR`.

During phases 6 to 8 (slices C1 to C3), a group that has not yet moved is decoded as class 0. It keeps EXECUTE, so each intermediate design is complete.

Realization: a 3-to-8 decoder on the opcode, plus about two levels of gates. It sits in the FETCH TS3 control-store address path (section 5.2 and [timing.md](timing.md) §4).

## 3. Major-State Sequences

### 3.1 FETCH

v1 FETCH: TS1 `MA ← PC`; TS2 memory read into MB; TS3 `IR ← MB`; TS4 PC increment, EA formation, next state.

v2 FETCH, IR loaded at TP2, as DEC does:

| TS | All classes | OPR (3, 4, 5) | JMP direct (1) | Other (0, 2) |
|---|---|---|---|---|
| TS1 | `MA ← PC`, PC increment (both from the pre-TP1 PC); `II_CLEAR` if `CIFP = 0` (as v1) | | | |
| TS2 | memory read: `MB ← MDB` **and `IR ← MDB`** at TP2 | | | |
| TS3 | | OPR pass: AC, L, MQ at TP3; group 2 skip sense into **SKIP** at TP3; group 2 HLT captured (`HLT_REQ_NEXT`) | `PC ← EA_FORMED` (page from **MA**); if `CIFP`: `DIF_TO_IF`, `CIFP_CLEAR`; `II_CLEAR`, all at TP3 | `EA_ADDR ← EA_FORMED` (page from MA) at TP3 |
| TS4 | | if `SKIP`: PC increment. **Instruction boundary** | **Instruction boundary** | next state: DEFER if `IR_INDIRECT` or class 2, else EXECUTE |

- **PC increment moves from TS4 to TS1.** In v2, IR is not loaded until TP2, so EA formation in TS3 can no longer take the page from PC, which has already advanced. It takes it from MA, which holds the instruction's address from TP1 until the next MA load. This matches DEC: "PC, plus 1 if SKIP, into CPMA at TP4" (KK8-E), with the instruction's address held in the memory address register.
- **Direct JMP:** "the PC is modified during TS3" (KK8-E); the next cycle is FETCH. The field change and the clearing of `II` at TP3 follow KM8-E: INT INHIBIT is "negated at TP3 whenever a JMP or JMS instruction occurs". This is the rule gap L already applies on `main`.
- **OPR:** "OPR in FETCH TS3, one pass, loaded at TP3" (KK8-E; section 4.1).
- **IR and MB both load from MDB at TP2.** MB still loads, so nothing that reads MB changes.

### 3.2 DEFER

| TS | MRI (class 0) | JMP I (class 2) |
|---|---|---|
| TS1 | `MA ← EA_ADDR` | same |
| TS2 | read the pointer: `MB ← MDB` | same |
| TS3 | autoindex: `MB ← MB + 1` | autoindex as for MRI; **`DIF_TO_IF` if `CIFP`; `CIFP_CLEAR`; `II_CLEAR`** at TP3 |
| TS4 | autoindex write-back; `EA_ADDR ← MB`; next state EXECUTE | autoindex write-back; **`PC ← MB`**; **instruction boundary** |

- JMP I's field change and `II_CLEAR` stay at TP3 of the instruction's last state, so an interrupt is recognized at the JMP I's end (gap L, KM8-E).
- `PC ← MB` waits for TP4 because autoindexing changes MB at TP3.
- DEC: "JMP I: next cycle DEFER, which completes it" (KK8-E). Autoindexed DEFER is a slow cycle on the 8/E (section 8).

### 3.3 EXECUTE

- Entered only by class 0: MRIs other than JMP, and IOT.
- The EXECUTE words for OPR and JMP are removed. Every other EXECUTE word is unchanged, including CAF, so its `/INITIALIZE` and "no interrupt at CAF's completion" are unchanged.

### 3.4 INTERRUPT, DMA, and console

Their sequences are unchanged. Only where they are entered from changes (section 6).

## 4. Datapath Changes

### 4.1 OPR pass unit

One combinational pass from the current AC, L, MQ, and SR to new AC and L values, controlled **directly by IR bits** (decision 1). The KK8-E describes the same structure:
- AC onto the DATA bus, with CLA implemented by not gating AC, which gives zeros;
- the data control gate passing true or complement (CMA);
- the adder's register input = 0 and carry-in = IAC;
- then a 74151 adder-output multiplexer for no shift, left, right, twice, or BSW.

The four-step group 1 order (CLA/CLL; CMA/CML; IAC; rotates or BSW) is the order in which the stages compose, and all four happen in one pass ("Because each instruction takes one memory cycle … 7001 can be combined with 7040 to give 7041").

| Stage | Group 1 | Group 2 | Group 3 |
|---|---|---|---|
| A: zero gating of AC (12) and L (1) | CLA, CLL | CLA | CLA, MQL |
| B: OR inputs | — | OSR: OR SR | MQA: OR MQ |
| C: true/complement of AC and L | CMA, CML | — | — |
| D: increment (carry-in into a 13-bit incrementer; the carry out of AC bit 0 complements L) | IAC | — | — |
| E: rotate/BSW multiplexer on the 13-bit L·AC ring | RAR, RAL, RTR, RTL, BSW | — | — |

- **The stage controls are gated from IR, qualified by the class.** For example, CLA = IR bit 4 AND class ∈ {3, 4, 5}; complement = IR bit 6 AND class 3. With the pass not selected, AC and L do not load, so the gating has no effect.
- **The control store selects the pass with field codes, not a new bit** (section 5.1): `AC_SRC` = 7 (reserved in v1) loads AC from the pass unit, and `L_OP` = 1 (COMP in v1, used only by OPR's `L_COMP`) loads L from it, in FETCH TS3. "`OPR_PASS`" in this document means that pair of codes. MQ loads for MQL and SWP use the existing `MQ_LOAD` / `MQ_SRC = AC` path, also at TP3. The control store learns of MQL from class 6 (section 2; decided 2026-11-20), which fits the 3-bit class code and the 5-bit `VARIANT` with no new bits. MQL also clears AC (stage A gates AC to zero when MQL is set). SWP therefore exchanges in one TP, "two paths loaded at the same TP3" (KK8-E).
- **RAR and RAL together** (and RTR with RTL) are treated as no rotate. DEC's behavior there is undocumented and is not replicated (main's handoff rules).
- **Realization:**
  - stage A: 4 × quad AND;
  - stage B: 3 × quad OR;
  - stage C: 4 × quad XOR;
  - stage D: 13-bit incrementer, 3 × 4-bit adder with B = 0, carry-in = IAC, or a dedicated incrementer;
  - stage E: 7 × dual 4:1 multiplexer.
  
  Roughly 21 to 25 packages; delays in [timing.md](timing.md) §5.
- **The ALU's rotate, BSW, NOT, and CLEAR operations become unused in v2** once OPR leaves EXECUTE. `MQ_CLEAR` (console) and `AC_CLEAR` (IOT, console) still use CLEAR. Whether to delete the others is a packing choice for slice C3 (section 7).

### 4.2 SKIP register

A 1-bit register. It loads at FETCH TP3 of a group 2 OPR with the skip-sense result (SMA/SZA/SNL, or SPA/SNA/SZL), computed from the **pre-TP3** AC and L. It is needed because CLA may clear AC at the same TP3 at which the skip decision is made. The KK8-E's SKIP flip-flop works the same way: combinational skip logic sets SKIP at TP3. `SKIP` reaches the control store as an overlay condition in FETCH TS4 (section 5.3).

### 4.3 IR source

IR loads from MDB at FETCH TP2, wired to the same source as MB's MDB input. `MB_TO_IR` at TP3 is removed.

### 4.4 PC sources

- **PC increment at FETCH TS1:** `PC_INC` through the ALU (`ALU_A_SRC = PC`, `ALU_OP = INC`), as v1 does at TS4.
- **New PC source `EA_FORMED`** for direct JMP at FETCH TP3. `EA_ADDR` loads at the same TP3, so the IDB path through the `EA_ADDR` register cannot be used. `PC_SRC` widens from 1 to 2 bits: 0 IDB, 1 constant 0001, 2 `EA_FORMED`.
- JMP I: `PC ← MB` through the IDB (`IDB_SRC = MB`, `PC_SRC = IDB`) at DEFER TP4.

### 4.5 EA formation

The page bits come from **MA** instead of PC (section 3.1). The unit stays combinational: `EA_FORMED = IR[7] ? MA[11:7]·IR[6:0] : 0·IR[6:0]` (page zero or current page).

## 5. Control-Store Changes

### 5.1 Datapath control word

| Change | Field | Width effect |
|---|---|---|
| OPR pass select | `AC_SRC` = 7 (reserved) and `L_OP` = 1 (freed COMP code) | 0 |
| SKIP load | new `SKIP_LOAD` | +1 |
| `ALU_OP`: OR, NOT, ROR, ROL, RTR, RTL, BSW used only by OPR | 4 → 2 bits (ADD, AND, INC, CLEAR) | −2, after slice C3 |
| `ALU_B_SRC`: MQ and FP_SR used only by OPR | 2 → 1 bit (NONE, MB) | −1, after slice C3 |
| PC source `EA_FORMED` | `PC_SRC` 1 → 2 bits | 0: it already sits in a 2-bit shared group (`IOT_TRANSFER_VAL`, `L_OP`, `MB_SRC`, `PC_SRC`) |
| IR from MDB | `IR_LOAD` unchanged, source wired | 0 |

v1 uses 44 of 48 datapath bits. v2 needs **45 of 48 until slice C3, then about 42 of 48** once the OPR-only ALU encodings are removed (section 7). **No seventh datapath EEPROM is needed.** The packer confirms the sharing (phase 3 onward).

### 5.2 Address formation outside EXECUTE (decision 2a)

v1: outside EXECUTE, `VARIANT = 0`, `DP_OVL_SEL = 1` (the state group), and `IR_SEQ = IR_INDIRECT`.

v2:
- **`VARIANT[2:0] = IR_CLASS` and `VARIANT[4:3] = 0` whenever `MS_EFF_IS_EXECUTE = 0`.** The five AND gates of CSO §5.4.2 become a 5-bit 2:1 multiplexer: `MAPR[4:0]` in EXECUTE, `00·IR_CLASS` otherwise.
- The class decode reads the live IR, which is valid from TP2 on. It is used only in FETCH TS3 and TS4 and in DEFER.
- **FETCH TS1 and TS2 still see a `VARIANT`, from the previous instruction's IR.** Their datapath words must therefore be the same for every class: the packer must verify it, and the tools must generate them as class-independent. The same applies while halted (`MS_EFF = 7`), where the console words must not depend on the stale IR class.
- **`MAPR` is unchanged.**
  - It still captures at every TP1 to TP4, and EXECUTE still uses it.
  - Its lookahead entry for EXECUTE TS1, captured at FETCH TP4 or DEFER TP4, is correct, because IR is loaded at TP2. The mapping ROM has all of TS3 and TS4 with the new IR.
  - CSO §5.4.3's argument changes only in its first bullet: "IR is loaded only at FETCH TP2".
- **The mapping ROM's `A0` stays wired 0.** The handoff (§6.2) proposed using it to select a FETCH table; with the class decode it is not needed.

The rejected alternative, **decision 2b**, addresses the mapping ROM from MDB during FETCH TS2. It puts a second EEPROM access in series with the memory read inside TS2 ([timing.md](timing.md) §4.2) and is not recommended.

### 5.3 Overlay group 1 (state group)

v1's state group is `{CIFP, AUTO_INDEX_REQUIRED, FP_CMD[2:0]}`, and all five bits are used. v2 needs `SKIP` in FETCH TS4. `FP_CMD` matters only while halted, so group 1's low three bits get a 3-bit 2:1 multiplexer selected by `RUN`, exactly as `SEQ_OVL` already has (CSO §5.6):

| `RUN` | `DP_OVL[4]` | `DP_OVL[3]` | `DP_OVL[2]` | `DP_OVL[1]` | `DP_OVL[0]` |
|---|---|---|---|---|---|
| 0 | `CIFP` | `AUTO_INDEX_REQUIRED` | `FP_CMD[2]` | `FP_CMD[1]` | `FP_CMD[0]` |
| 1 | `CIFP` | `AUTO_INDEX_REQUIRED` | `SKIP` | 0 | 0 |

This is address formation: it selects which inputs reach the address. It adds one multiplexer delay to the overlay path, in parallel with the class decode ([timing.md](timing.md) §4).

### 5.4 Sequencer slice

The sequencer address has three spare bits (CSO §5.6: `A2..A0 = 0`). v2 uses two of them:

| Bit | v2 input | Source | Used |
|---|---|---|---|
| A3 `IR_SEQ` | unchanged: `MAPR[7]` in EXECUTE, `IR_INDIRECT` otherwise | | FETCH TS4: DEFER or EXECUTE |
| A2 | `IR_ONE_STATE` (FETCH) / `IR_IS_JMP` (DEFER), live predecode | class decode | FETCH TP4 and DEFER TP4: does the instruction end here? |
| A1 | `IR_OPR_HLT`, live predecode | class decode and IR bit 10 | FETCH TS3: HLT capture (v1 did this in EXECUTE TS3 through `MAPR[7]`) |

Sequencer next-state decisions:
- **FETCH TP4:**
  - if `IR_ONE_STATE`: the instruction-boundary rule (section 6.1);
  - else if `IR_INDIRECT` or JMP I: DEFER;
  - else: EXECUTE.
- **DEFER TP4:**
  - if `IR_IS_JMP`: the instruction-boundary rule;
  - else: EXECUTE.
- **EXECUTE TP4:** the instruction-boundary rule, as v1.

The `IR_SEQ` meaning of `MAPR[7]` in EXECUTE TS3 (`IR_OPR_HLT`) is no longer needed, since OPR never reaches EXECUTE. The mapping ROM's sequencer decode keeps only `IR_IS_CAF` in TS4.

### 5.5 Address-budget summary

| Resource | v1 | v2 |
|---|---|---|
| Datapath control word | 44 / 48 bits | 45 / 48, then about 42 after slice C3 |
| Datapath address | 15 / 15 | 15 / 15 (same fields; `VARIANT` takes 3 class bits outside EXECUTE) |
| Datapath variants used outside EXECUTE | 1 | 7 (the classes) |
| Mapping ROM address | IR 12 + TS 2 + `A0` = 0 | unchanged |
| Mapping ROM output | 8 / 8 | 8 / 8 (sequencer decode bit used in TS4 only) |
| Sequencer address | 12 of 15 used | 14 of 15 |
| Sequencer output | 7 / 8 bits | **8 / 8**: the spare carries `INSTR_END` (decision 7, section 6.1) |
| Overlay | 4 groups × 5 | unchanged, plus a 3-bit `RUN` multiplexer on group 1 |

## 6. Sequencing and Interrupts

### 6.1 Instruction boundary

An instruction ends at the TP4 of its last major state: FETCH (classes 1, 3, 4, 5), DEFER (class 2), or EXECUTE (class 0). At that TP4, exactly as at v1's EXECUTE TP4:
- Interrupt recognition, inhibited by `II` and by the pending field change, as v1.
- DMA entry (`/DMA_REQ`), and the DMA arbiter's "at least one instruction between bursts" re-enable (ARB §12).
- HLT (group 2, captured at FETCH TP3, halting at FETCH TP4); STOP; Single Instruction.
- Controllers' `at_boundary` time base (simulator).

`INSTR_END` is defined for hardware outside the sequencer (the DMA arbiter's re-enable). **It is a sequencer output (decision 7)**, the last spare bit of the sequencer word, asserted in the TS4 words that end an instruction. It is TP-qualified: its consumers sample it at TP4. Its meaning is
```
INSTR_END = TS4 AND MS ∈ {FETCH, DEFER, EXECUTE} AND NOT (MS_LOAD AND MS_NEXT ∈ {DEFER, EXECUTE})
```
and the packer can verify every sequencer word against that expression. The control store decides it, as it decides every other sequencing output, instead of gates re-deriving it from the sequencer word.

**ION's one-instruction delay still works.** ION sets `II`, and the next instruction's FETCH TS1 clears it if `CIFP = 0`, so recognition is still inhibited at ION's own end.

### 6.2 Skip and interrupt at the same TP4 (decision 4)

DEC: "If an interrupt is honored at the same TP4 as a skip, the increment is not made in TS4; it is made during TS2 of the forced JMS" (KK8-E). That is a consequence of the 8/E loading CPMA, not PC, at TP4.

In this design the skip increment is a PC load at FETCH TP4. The INTERRUPT state then stores PC (`PC_TO_MB` at INTERRUPT TS1), which is already incremented. The programmer-visible result, return address = skip target, is identical to DEC's. **Recommendation: no special case.** Increment at FETCH TP4 whenever `SKIP`, whether or not an interrupt is recognized there. A targeted test covers it (slice C2).

### 6.3 Single Step

Single Step halts after each major state, so it shows one state for OPR and direct JMP and two for JMP I. This is the user-visible consequence.

## 7. Removed or Repurposed v1 Elements (v2 only)

- The EXECUTE cases for OPR groups 1 to 3 and JMP.
- `MB_TO_IR` and the FETCH TS4 `IR_ADDR_TO_EA_ADDR`; EA formation moves to TS3.
- FETCH TS4's PC increment (moved to TS1; TS4 keeps a conditional increment).
- ALU operations no longer needed (ROR, ROL, RTR, RTL, BSW, NOT) can be dropped or kept. Recommendation: keep the ALU encoding until slice C3 has passed, then decide on cleanup.

## 8. Timing (decision 3a): summary

Full analysis: [timing.md](timing.md).

- Phase 0 fixed the target: the ISZ + JMP loop must take 3.75 to 3.85 µs, that is, 2·FETCH + EXECUTE ≈ 76 TSTEPs at 50 ns.
- **3a** gives FETCH and non-autoindex DEFER fast lengths, and EXECUTE and autoindex DEFER slow lengths, as the 8/E's fast and slow cycles do. DEC: "FETCH and non-autoindex DEFER are fast; EXECUTE and autoindex DEFER are slow"; MRIs are "one fast FETCH (1.2 µs) and one slow EXECUTE (1.4 µs)" (KK8-E, M8330, MM1).
- **The TS-length table:**
  - a small timing ROM indexed by the next state and TS, a class bit (autoindex DEFER), and a 2-bit speed-mode input;
  - its output is a TSTEP terminal count, loaded at each TP for the following TS;
  - the speed mode gives at least three modes: optimized, uniform slow (today's 28 steps per state), and single-step debug.
  
  DEC precedent for a selectable speed: the 8/E's slow-cycle jumper (M8330).
- At reduced TCLK during hardware bring-up, time-based tests (D2AB routines 4 and 5) are not expected to pass. Every other test is clock-independent.
- **The console transaction timer** (Major State Timing §8: "the transaction duration equals the TS2 duration") uses the slow TS2 length.
- **External-IOT EXECUTE** keeps slow-cycle lengths, and `/IO_WAIT` still stretches it. The controller contracts are unchanged.

Result of the per-TS analysis ([timing.md](timing.md) revision 2, §4), with the SRAM-shadowed control store (decision 12) and ACT on the control-store address path: the minimum lengths are about FETCH 15 and ISZ EXECUTE 16 steps at 50 ns, with the PC still incremented through the ALU. The proposed lengths are **FETCH and plain DEFER 5/8/6/5 = 24, EXECUTE and autoindex DEFER 6/9/7/6 = 28 (3a exactly; the slow states keep today's lengths)**, with at least 50 ns of margin in every TS. Any main-memory part with an access time up to about 165 ns fits ([timing.md](timing.md) §4.4).

## 9. Impacts

As handoff §6, with these resolutions:
- §6.1 hardware: OPR pass unit (section 4.1), SKIP, IR source, `EA_FORMED` PC source, EA page from MA, the class decode, the group 1 `RUN` multiplexer, the timing ROM.
- §6.2 control store: 45 / 48 datapath bits (about 42 after slice C3); mapping ROM `A0` not needed; sequencer A2 and A1 used.
- §6.3 sequencing: section 6.
- §6.4 documentation and §6.5 simulator: as handoff, in the slice order of [plan.md](plan.md).

**Diagrams the user will need to update** (never edited by Claude):
- Datapath: the OPR pass unit; the IR input from MDB; the PC source multiplexer (`EA_FORMED`); the EA unit's page source (MA); the SKIP register.
- Control-store address formation: the `VARIANT` multiplexer with the class decode; the group 1 `RUN` multiplexer; the sequencer A2 and A1 inputs.
- Timing: `cpu-timing-overview` per-state TS lengths; the timing ROM and TSTEP terminal-count logic.

## 10. Verification

Per [plan.md](plan.md):
- v1 kept selectable and green throughout.
- Lock-step against the unchanged reference model, with reference cycle costs per design.
- An exhaustive OPR test per group.
- Targeted boundary tests per slice.
- The MAINDEC regression under PyPy.
- D2AB PRG0 routines 4 and 5 as the timing acceptance test (slice D).

## 11. Decisions for the User

| # | Decision | Recommendation | Status |
|---|---|---|---|
| 1 | OPR controls hardwired from IR bits, enabled by `OPR_PASS` (the `AC_SRC` and `L_OP` codes, section 5.1) | Yes (DEC does this; microcoding needs about 2^8 group 1 combinations). **Amend `docs/00-overview/00-design-principles.md` §3.1** ("no hardwired control logic") in slice C1: the control store decides when the pass acts; IR bits select its function | **decided 2026-11-20** |
| 2 | How FETCH TS3 gets its control word | **2a**: `VARIANT = IR_CLASS` outside EXECUTE (section 5.2) | **decided 2026-11-20** |
| 3 | Variable TS lengths | 3a | decided 2026-11-19 |
| 3' | TS-length mechanism: timing ROM with speed modes (section 8); TSTEP 50 ns, or finer | Timing ROM (shadowed in SRAM), **50 ns**: 3a's lengths are whole 50 ns steps ([timing.md](timing.md) §4.3) | **decided 2026-11-20** (timing.md rev. 2) |
| 4 | Skip and interrupt at the same TP4 | No special case (section 6.2) | **decided 2026-11-20** |
| 5 | v1 alongside v2 | Side by side, removable before merge | decided 2026-11-19 |
| 6 | Overlay: `RUN` multiplexer on state-group bits 2 to 0 for `SKIP` (section 5.3) | Yes | **decided 2026-11-20** |
| 7 | `INSTR_END`: gates from the sequencer word, or the spare sequencer output (section 6.1) | **Spare sequencer output** | **decided 2026-11-20** |
| 8 | Logic family per path | Mixed: ACT or F on the critical paths named in [timing.md](timing.md) §6. **The control-store address path must stay ACT**: with HCT there, the SRAM's gain is lost (timing.md §7.2) | **decided 2026-11-20** (timing.md rev. 2) |
| 9 | PC as a synchronous counter (or a dedicated incrementer) instead of incrementing through the ALU | **No** (revised with decision 12): FETCH has 103 ns of margin with the ALU increment, which is what DEC's 8/E does (timing.md §4.3) | **decided 2026-11-20** (timing.md rev. 2) |
| 10 | Drive AB from MA whenever the CPU owns the bus (not only while `/RD` or `/WR`), so the address leads `/RD` | **No** (revised with decision 12): the read already has 110 ns of margin | **decided 2026-11-20** (timing.md rev. 2) |
| 11 | Register `MS_EFF_IS_EXECUTE` and the overlay's combinational conditions (zero detects) at the preceding TP | **Not required** (revised with decision 12): without it every TS still fits, with at least 50 ns of margin (timing.md §4.3, conclusion 5) | **decided 2026-11-20** (timing.md rev. 2) |
| 12 | Control store shadowed in fast SRAM: the EEPROMs are copied into SRAM at power-on reset, and the machine runs from the SRAM | Yes | **decided 2026-11-20** (with option 2) |

### 11.1 Decision 12: SRAM-shadowed control store

Decided 2026-11-20: option 2 **and** an SRAM shadow, for per-class fidelity (option 2) and timing slack (SRAM).

- Every control-store EEPROM (mapping, datapath slices, sequencer, and the timing ROM) gets a 5 V 32K × 8 SRAM of 10 to 15 ns. `T_CW` falls from about 202 ns to about 65 ns, so 3a's 24/28 steps gain large slack.
- **Copy:** at power-on reset only, from a supply supervisor. A 15-bit copy counter drives every SRAM's address through tri-state buffers (about 7 ns in the address path), the EEPROM outputs drive the SRAM data pins, and all devices copy in parallel (about 7 ms).
- **Never at `/INITIALIZE`:** CAF and front-panel CLEAR assert it while running from the control store.
- **Write protection:**
  - only the `LOADING` flip-flop and the copy strobe reach the SRAM `/WE`, which has a pull-up;
  - no control-word field and no bus reaches it, and the control store is not in the memory address space;
  - while `LOADING`, TSEQ is held in reset, `CW_VALID` is low, and `/INITIALIZE` is asserted, so no partial control word acts;
  - the EEPROMs' `/WE` is tied high.
- **Optional:** a front-panel RELOAD accepted only while `RUN = 0` (as every console command), and a verify pass with a fault lamp.
- **DEC precedent:** the KL10's microcode was loaded into control RAM by its front-end PDP-11 at boot; the VAX-11/780 loaded writable-control-store patches from its console floppy. The PDP-8/E itself is hardwired, so there is no 8-family precedent.
- **Effect on other decisions** ([timing.md](timing.md) revision 2): decisions 9 (counter PC), 10 (early AB), and 11 (registered conditions) are no longer needed for 3a; decision 3' can be 50 ns; decision 8's "the control-store address path must be ACT" still holds, because HCT there would cancel the SRAM's gain.
