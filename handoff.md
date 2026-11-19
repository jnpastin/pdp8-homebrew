# PDP-8 Homebrew Handoff: One-Cycle OPR and JMP (Option 2)

Branch: `one-cycle-fetch`. This branch evaluates, and if the user approves, implements a change to the major-state structure so that the machine's cycle counts match the PDP-8/E's for everything except IOT. `main` carries the simulator's phase 3 work and its own handoff; read that one (`git show main:handoff.md`) for the simulator's structure, status, and phase 3 plan, which are not repeated here except where this change affects them.

## 1. Your Task

1. Write an architecture specification for option 2 (section 5) for the user's review. No documentation, microcode, tool, or simulator changes until the user approves it.
2. After approval, implement it in stages (section 7), keeping microcode v1 working throughout and adding the new design as microcode v2.

The user has not yet decided to adopt the change. They want the implications understood first; this branch is where that is worked out.

## 2. Rules

The rules of `main`'s handoff apply, with these differences:

- Work on the branch `one-cycle-fetch`, not `main`. Merge from `main` when it moves on; do not merge into `main` without the user's instruction.
- Keep `rom/microcode/v1/` and everything that consumes it working. Put the new design in `rom/microcode/v2/`, and make the pipeline and simulator able to select either.
- Every claim about DEC behavior cites a DEC document (section 4 lists them). The user prefers matching DEC; where this design deliberately does not (IOT), say so.

## 3. The Problem

On the PDP-8/E, OPR, IOT, and directly addressed JMP complete in FETCH; only memory-reference instructions (and JMP I, through DEFER) take a second cycle. In this design every instruction runs FETCH and EXECUTE. Timing-dependent software therefore runs slower than on an 8/E at the same cycle time: an `ISZ; JMP` delay loop takes 4 major states here against 3.8 µs (1.2 + 1.4 + 1.2) on the 8/E, about 26% slower.

Concrete consequence: MAINDEC-8E-D2AB PRG0 routine 4 halts at 2607, "printer flag set prior to 9 bit times". Its character-timing window is about 6%, measured with instruction loops calibrated to 8/E timing. (Routines 0 to 3 pass; see `main`'s handoff §6.1.)

## 4. DEC Facts (verified)

Sources, all on deramp.com under `011-Digital Equipment Corporation/02 PDP-8e/`: KK8-E Central Processor Theory of Operation; M8330 Timing Generator Theory of Operation; PDP-8/E, 8/F, 8/M Maintenance Manual Volume 1, Processor (Sep 1973); KM8-E Memory Extension Theory of Operation. The scans carry an OCR text layer. The Small Computer Handbook (8/E, 8/F, 8/M) is scanned on a mirror that blocks automated downloads; the maintenance manual's flow diagrams cover the same material.

- **Cycles.** "A one-cycle instruction can be an OPR microinstruction, an IOT instruction, or a directly addressed JMP instruction." "A two-cycle instruction involving the DEFER state can only be a JMP." MRIs: one fast FETCH (1.2 µs) and one slow EXECUTE (1.4 µs), 2.6 µs.
- **Fast and slow cycles** come from core memory's destructive read and write-back: the slow cycle lengthens TS2 by 200 ns so modified data can reach the write half. FETCH and non-autoindex DEFER are fast; EXECUTE and autoindex DEFER are slow.
- **OPR in FETCH TS3, one pass, loaded at TP3.** AC onto the DATA bus (CLA by not gating AC, so zeros), the data control gate true or complement (CMA), the adder's register-in = 0 and carry-in = IAC, then a 74151 adder-output multiplexer for no shift, left, right, twice, BSW; AC and L load at TP3. The handbook's four-step group 1 order (CLA/CLL; CMA/CML; IAC; rotates or BSW) is the composition order, implemented by this gating in one pass ("Because each instruction takes one memory cycle … 7001 can be combined with 7040 to give 7041"). Group 2: combinational skip logic sets a SKIP flip-flop at TP3; CLA and OSR in the same pass. Group 3: MQA is an OR in the data-line multiplexer; SWP uses two paths loaded at the same TP3.
- **FETCH TS4.** Interrupt check first (INT IN PROG forces JMS into IR, selects EXECUTE, loads 0 into CPMA); otherwise PC, plus 1 if SKIP, into CPMA at TP4. If an interrupt is honored at the same TP4 as a skip, the increment is not made in TS4; it is made during TS2 of the forced JMS.
- **Direct JMP:** "the PC is modified during TS3"; next cycle FETCH. JMP I: next cycle DEFER, which completes it.
- **IOT in FETCH TS3** with I/O PAUSE, C lines, and BUS STROBE at TP3; slow or multi-transfer peripherals stall TS3 with NOT LAST TRANSFER. (Option 2 does not adopt this; IOT keeps EXECUTE.)
- **KM8-E:** INT INHIBIT is "negated at TP3 whenever a JMP or JMS instruction occurs" (already matched by gap L on `main`).

## 5. Option 2: Scope

| Instruction | Today | Option 2 | PDP-8/E |
|---|---|---|---|
| OPR (groups 1, 2, 3) | FETCH, EXECUTE | **FETCH only** | FETCH only |
| JMP (direct) | FETCH, EXECUTE | **FETCH only** | FETCH only |
| JMP I | FETCH, DEFER, EXECUTE | **FETCH, DEFER** | FETCH, DEFER |
| AND, TAD, ISZ, DCA, JMS (direct / indirect) | FETCH, (DEFER), EXECUTE | unchanged | same |
| IOT (all) | FETCH, EXECUTE | **unchanged**: keeps EXECUTE and today's external IOT contract | FETCH only |

IOT stays in EXECUTE so that `docs/07-io`, the controller contracts, and the KL8E, PC8E, and RK8E models are untouched. Consequence: IOTs cost one major state more than on the 8/E, so flag-polling loops (`TSF; JMP .-1`) run about 30% slower than an 8/E's; ISZ/JMP delay loops match exactly. Moving IOT into FETCH is a possible later stage (option 1), not part of this branch.

### 5.1 New FETCH (IR loaded at TP2, as DEC does)

| TS | All instructions | OPR | Direct JMP | MRI, JMP I, IOT |
|---|---|---|---|---|
| TS1 | `MA ← PC`; PC increment (both from the pre-TP PC) | | | |
| TS2 | memory read: `MB ← MDB` and **`IR ← MDB`** at TP2 | | | |
| TS3 | | single OPR pass; AC, L, MQ at TP3; group 2 skip into **SKIP** at TP3 | `PC ← EA` (page from **MA**, the instruction address); pending field change, `CIFP` and `II` clear, at TP3 | EA formation |
| TS4 | | PC increment if SKIP; instruction ends | instruction ends | next state DEFER or EXECUTE |

At the end of an OPR or direct JMP, FETCH TP4 is an **instruction boundary**: interrupt recognition, DMA entry, HLT, STOP, and Single Instruction, all currently tied to EXECUTE TP4, also apply there. JMP I's boundary is DEFER TP4.

### 5.2 Decisions the user must make (in the specification)

1. **OPR controls hardwired from IR bits** (as DEC), enabled by a control-word field. Microcoding is not feasible: group 1 alone has about 2^8 combinations and VARIANT is 5 bits. This adds IR-to-datapath decode gates, a change from "the control store drives everything".
2. **How FETCH TS3 gets its control word.** `MAPR` is loaded from the mapping ROM, which is addressed by IR; at TP2 IR and MAPR load together, so MAPR would hold the old instruction's entry. Either (a) a small instruction-class decode from IR drives `VARIANT` in FETCH TS3 (a few gates in the TS3 critical path), or (b) the mapping ROM is addressed from MDB during FETCH TS2 through a 12-bit 2:1 multiplexer (memory access plus an EEPROM access inside TS2; viable only with a longer TS2). Recommendation: (a).
3. **Variable TS lengths.** A TSTEP-count table indexed by registered state (`MS_EFF`, `TS`, possibly an instruction-class bit), as the 8/E's fast and slow cycles vary TS2. This resolves the open TSTEP item. Lengths can be set to each path's critical delay, or to the 8/E's durations for timing compatibility. With SRAM there is no destructive read, so fast/slow has no memory reason; any 8/E-like durations are a deliberate compatibility choice (DEC precedent for a switch: the 8/E's slow-cycle jumper).
4. **Skip and interrupt at the same FETCH TP4.** Match DEC (suppress the TS4 increment and apply it during interrupt entry), or define it differently.
5. **Microcode v2 alongside v1** (recommended) and whether the simulator keeps both selectable permanently.

## 6. Impacts

### 6.1 Datapath hardware

- OPR pass unit: zero gating on the A input (about 4 × quad AND, 13 bits with L), true/complement stage (about 4 × quad XOR), the adder's carry-in (exists), a 13-bit shift/rotate/BSW multiplexer (about 7 × dual 4-to-1 or 13 × 8-to-1 multiplexers; may replace the rotate ALU operations). Roughly 20 to 30 packages. `ALU_OP` changes from one operation per TS to a composed pass (re-encode, or add mode fields).
- SKIP register (1 bit, loaded at TP3), because CLA may clear AC at the same TP3 the skip decision uses.
- `IR ← MDB` at TP2 (new IR source, replacing `MB_TO_IR` at TP3).
- PC increment in FETCH TS1; EA page from MA; new PC source for the direct JMP address; MQ OR and SR paths into the pass.
- The FETCH TS3 class decode (decision 2a).
- Variable TS lengths in the timing generator (decision 3): a loadable TSTEP terminal count and its table.

### 6.2 Control store, microcode, packing

Address budgets (Control Store Organization §5; packing report): datapath slice 15 bits = `MS_EFF` 3 + `TS_CODE` 2 + `VARIANT` 5 + `DP_OVL` 5, full, but FETCH's VARIANT and overlay space is unused today and can be used without new bits; EXECUTE's busiest TS (TS2, 26 variants) loses no variants under option 2 except JMP's and OPR's. Mapping ROM: IR 12 + `TS_CODE` 2 + `A0` (wired 0, the only spare); FETCH TS4 entries would collide with EXECUTE TS4 entries for the same IR and TS, so `A0` selects the table (last spare used); its 8 output bits stay full. Sequencer: three spare bits (A2..A0); FETCH TP4 needs an instruction-class input besides `IR_INDIRECT` (one spare). Datapath width: 44 of 48 bits used; new fields (OPR-pass enable, SKIP load, IR source, JMP PC source, possibly an end-of-instruction output) may need a seventh datapath EEPROM.

- FETCH TS3 and TS4, and DEFER for JMP I, become instruction-dependent: address formation, `MAPR` rules, `MS_EFF_IS_EXECUTE` gating, overlay groups.
- Sequencer next-state decisions at FETCH TP4 and DEFER TP4 (FETCH, DEFER, EXECUTE, INTERRUPT, DMA, halt).
- Pipeline tools: the execution-definition extractor and generator (EXECUTE-centric cases), the symbolic generator, the equivalence analyzer, and the packer (address map, FETCH variants, verification) all change; all artifacts regenerate as v2.

### 6.3 Sequencing and interrupts

- Instruction boundary at the TP4 of the last major state: FETCH (OPR, direct JMP), DEFER (JMP I), EXECUTE (MRIs, IOT). Move interrupt recognition, DMA entry and the arbiter's `DMA_ENABLE` ("EXECUTE TS4" becomes the TS4 of an instruction's last state; the arbiter needs an end-of-instruction signal), HLT, STOP, Single Instruction, and the controllers' `at_boundary`.
- Direct JMP applies `DIF_TO_IF`, `CIFP_CLEAR`, and `II_CLEAR` at FETCH TP3 (consistent with gap L and KM8-E §2.9). ION's one-instruction delay still works (FETCH TS1 clears II).
- JMP I completes in DEFER, including autoindex and the field change; JMP's EXECUTE is removed.
- Group 2 HLT halts at FETCH TP4. CAF stays in EXECUTE (it is an IOT), so its `/INITIALIZE` and "no interrupt at CAF's completion" are unchanged.
- Skip and interrupt at the same TP4 (decision 4).
- Single Step (halt per major state) sees fewer states for OPR and JMP.

### 6.4 Documentation

- `03-microarchitecture`: state model, micro-operations (new; ALU re-encoding), sequencing, FETCH/DEFER (rewrite), MRI (JMP leaves EXECUTE; JMP I in DEFER), OPR groups 1 to 3 (rewrite as single pass), interrupt, console, and DMA execution.
- `04-control`: control model, addressing, control word, datapath mapping, invalid conditions, control-store organization, control inputs and outputs, direct-control definitions.
- `01-architecture` (registers: SKIP, IR source; dataflow), `08-interrupts` (boundary), `09-timing` (TS-length table, major-state timing), `07-io/06-dma-arbitration` (re-enable context only), `99-Abbreviations`.
- `02-isa`: semantics unchanged; cycle-count notes only. `docs/07-io` controller contracts: unchanged.
- The user's datapath and timing diagrams need the OPR pass unit, the IR path, and the FETCH sequence (list them for the user; never edit them).

### 6.5 Simulator and verification

- CPU: address formation, datapath (OPR pass, SKIP, IR at TP2, PC sources), sequencing, derived signals; the time base becomes per (MS, TS).
- Lock-step: boundaries at FETCH, DEFER, and EXECUTE TP4. Reference model: semantics unchanged, cycle counting and timing per (MS, TS).
- DMA arbiter: the re-enable context. I/O models: unchanged.
- Tests: most CPU unit tests that build OPR or JMP EXECUTE words change. All MAINDECs re-verified (cheap under PyPy), including D2AB PRG0 routines 4 and 5, the acceptance test for the timing goal.

## 7. Plan

1. **Specification (review gate).** One document: the new FETCH TS1 to TS4 and DEFER for JMP I; the OPR pass datapath and its IR-driven controls; SKIP; IR at TP2; PC and EA sources; the instruction-boundary rule and end-of-instruction signal; the TS-length table; decisions 1 to 5 with DEC precedent; a critical-path estimate for FETCH TS3 (class decode, slice EEPROM access, OPR pass) and FETCH TS2 with real part numbers. Stop for the user's decision.
2. **Microcode v2 scaffolding.** `rom/microcode/v2/`, pipeline and simulator able to select v1 or v2; v1 stays green.
3. **Documentation**, in dependency order (01, 03, 04, 08, 09, then 07-io/06), each area proposed and applied interactively, with a pipeline dry run after each; keep a diagram list for the user.
4. **Tools:** extractor and generator support for FETCH and DEFER cases; packer address map and FETCH variants; verification; tool tests.
5. **Pipeline run and promotion of v2** (the user). Check packing, control-word width, and address budgets.
6. **Simulator:** v2 address formation and datapath, lock-step boundaries, reference cycle counting, per-(MS, TS) time base, DMA arbiter context; unit tests.
7. **Re-verification:** all suites; lock-step random episodes (including DMA); the MAINDEC regression; full passes of the long programs under PyPy; D2AB PRG0 including routines 4 and 5.

## 8. Risks

- **Hardware timing**, which the simulator (timing-state level) cannot see: the FETCH TS3 path, and TS2 if decision 2b is chosen. Needs a static timing estimate before committing.
- **New-boundary corner cases** (skip with interrupt at FETCH TP4, CIF and II around a direct JMP, DMA re-enable, Single Step), any not exercised by a MAINDEC.
- **Tooling restructure bugs** in the extractor and generator; limited by the packer's address-by-address verification and the tools' tests.
- **Documentation consistency** across about 30 files, plus the diagrams.
- Mitigations: the ISA semantics, and so the reference model and the lock-step oracle, do not change; every fixed gap (A to N) has a regression test; v1 stays intact for comparison; the work is staged and each stage is verified before the next.
