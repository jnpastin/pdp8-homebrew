# Plan: One-Cycle OPR and JMP (Option 2), Incremental

Branch `one-cycle-fetch`. Phases 0 to 9 are done; phase 10 is not started. The phase texts below are the plan as made, corrected where they would mislead.

## How this differs from handoff §7

The handoff's plan goes one layer at a time: all docs, then all tools, then the simulator, then verification. Nothing runs end to end until the last stage. This plan makes three changes:

1. **Check feasibility first (phase 0, done).** Before any hardware work, measure which cycle counts and state lengths make D2AB PRG0 pass.
2. **Build in vertical slices.** Each slice is a coherent v2 design that runs: docs, tools, pipeline, simulator, verification. Every slice ends with v1 and v2 both green and lock-step passing. The cost is that the same docs get touched more than once. The benefit is that a bug shows up in the slice that caused it.
3. **Do behavior-neutral groundwork first (phase 2).** Design selection, a per-(MS, TS) time base, and an abstract instruction-boundary hook go in with bit-identical images and identical `elapsed_ns`. Later slices then change behavior and nothing else.

## Phase 0: Baseline and feasibility check (done 2026-11-19)

### Baseline (macOS, CPython 3.14.8; PyPy 3.12 / 8.0.1 from Homebrew)

| Check | Result |
|---|---|
| `run_pipeline.py --dry-run` | SUCCEEDED, every generator unchanged, no pending promotion |
| `sim/cpu`, `sim/memory`, `sim/reference`, `sim/io` | 50, 3, 18, 29 tests OK |
| `sim/system` | 76 tests OK (358 s under CPython) |
| Branch against `main` | up to date (`main` = `7419a67`, already in the branch) |

### Feasibility experiment

Scripts: `option2/experiments/d2ab_timing.py`, `sweep.py`, and `split.py` (run from the repository root: `pypy3.12 option2/experiments/d2ab_timing.py . [model ...]`). The repeatable form is `sim/system/tests/test_d2ab_timing.py` (phase 2.7). It loads D2AB through the simulator's console exactly as `maindec.prepare` does, builds the reference model with `reference_from`, and runs the reference model alone. The KL8E is at 110 baud with `flag_bits` = 9.25, and the built-in per-instruction time charge is replaced by a cost table. Each run takes 11 to 17 s under PyPy.

| Cost model | Result |
|---|---|
| Today: every state 1.2 µs, all instructions FETCH + EXECUTE | halt **2607** at 31.9 M instructions. This reproduces the simulator's result, which validates the harness |
| Option 2, every state 1.2 µs | halt **2614** |
| Option 2, FETCH and DEFER 1.2, EXECUTE and autoindex DEFER 1.4; IOT 2.4 µs | **PASS**: end halt at 0300 after 47.1 M instructions; routines 4 and 5 pass |
| Same, IOT 2.6 µs | **PASS** |
| Same, IOT 1.2 µs | **PASS** |
| Option 1 (8/E: OPR, IOT, and JMP 1.2 µs) | **PASS** |

**Routine 4.** It sends a character, waits about 9 bit times with ISZ/JMP delay loops, and halts at **2607** if the printer flag is already set. It then waits a little longer and halts at **2614** if the flag is still clear. The loop is ISZ + JMP. In instruction counts before the halt, MRI and direct JMP make up 99%; there are only about 61 K IOTs. The program accepts the flag at 9 to 9.55 bit times after TLS (`sim/io/src/pdp8_io/kl8e.py` docstring).

**State-length sweeps** (option-2 cycle counts):

| FETCH and DEFER 1.2 µs, EXECUTE = | 1.20 | 1.25 | 1.30 | **1.35** | **1.40** | **1.45** | 1.50 | 1.55+ |
|---|---|---|---|---|---|---|---|---|
| Result | 2614 | 2614 | 2652 | **PASS** | **PASS** | **PASS** | 2650 | 2607 |

| Every state = | 1.200 | 1.225 | **1.250** | **1.275** | 1.300 | 1.325+ |
|---|---|---|---|---|---|---|
| Result | 2614 | 2652 | **PASS** | **PASS** | 2650 | 2607 |

Halts 2650 and 2652 come from a later routine (5) whose window lies on either side.

### Findings

1. **Option 2 is sufficient.** IOT's extra cycle does not matter for D2AB PRG0: every IOT cost from 1.2 to 2.6 µs passes.
2. **The cycle counts alone are not enough; the state lengths matter.** The ISZ + JMP loop must take 3.75 to 3.85 µs, against the 8/E's 3.8 µs. That is a window of about ±1.3%. At a flat 1.2 µs per state the loop takes 3.6 µs, which is too fast (halt 2614), just as today's 4.8 µs is too slow (halt 2607).
3. So **decision 3 is required, not optional.** It has two workable forms:
   - **(3a) 8/E durations:** fast FETCH and DEFER at 1.2 µs, slow EXECUTE and autoindex DEFER at 1.4 µs. This needs the TS-length table, matches DEC per instruction class, and has DEC precedent (KK8-E fast and slow cycles).
   - **(3b) One uniform major-state length of about 1.267 µs** (3.8 / 3). It needs no table, just a different TSTEP count. ISZ + JMP matches exactly, but other mixes do not: OPR runs 6% slow, and a lone MRI runs 2.6% fast.
   - Recommendation: **(3a)**. It is what DEC did, and it is the only one of the two that matches timing for all instruction mixes.
4. The ±1.3% window means the hardware's TS lengths must be accurate. The phase 1 spec must show that the TSTEP clock and counts can produce the chosen lengths.
5. **Only the sum matters for D2AB.** With FETCH = DEFER = F and EXECUTE = X, every split with 2F + X = 3.75 to 3.80 µs passes:
   - F 1.25 / X 1.30 passes.
   - F 1.30 / X 1.20 passes.
   - F 1.225 / X 1.35 passes.
   - F 1.25 / X 1.25 passes.
   
   The acceptance test therefore fixes the total, not the split. This is the fallback if FETCH cannot reach 1.2 µs (section "Timing budget" below).
6. **Caveat:** where the window falls depends on the KL8E model's `flag_bits` = 9.25, which is the middle of D2AB's accepted range, not a measured KL8-E value. The experiment models no interrupt or DMA timing; PRG0 uses neither.

**Checkpoint 0 (decided 2026-11-19):** option 2, decision **3a**. Slice D is required, and OPR is split by group (slices C1 to C3).

### Timing budget: the control-store settle time

Source: `diagrams/timing/cpu-timing/source/cpu-timing-overview.json` shows a 20 MHz clock (TSTEP = 50 ns) with TS1, TS2, TS3, TS4 = 6, 9, 7, 6 steps. That is **28 steps = 1.40 µs for every major state today**, already the 8/E slow cycle. (The simulator's 1.2 µs default is a placeholder.) Every TS starts with `T_CS` (Timing Terminology §5.5): address formation, one 28C256 slice-ROM access, and the overlay, before `CW_VALID`. That is four ROM settles per major state.

Working assumption, to be replaced with datasheet figures in phase 1: `T_CS` ≈ 200 ns (a 150 ns 28C256 plus about 50 ns of register, selection, and overlay logic). Then today's state is 800 ns of ROM settle and 600 ns of datapath action (TS action windows of about 100, 250, 150, and 100 ns).

What 3a asks:

| | FETCH | EXECUTE | ISZ + JMP (2F + X) |
|---|---|---|---|
| Today | 28 steps | 28 | 84 steps = 4.2 µs (option-2 counts, too slow) |
| 3a, 8/E durations | **24** | 28 | 76 = 3.8 µs |
| 3a fallback, same total | 25 | 26 | 76 = 3.8 µs |
| 3a fallback, same total | 26 | 24 | 76 = 3.8 µs |

- Whatever the split, the three states of the loop must fit in **76 steps against today's 84**, with 12 ROM settles inside. This constraint comes from D2AB, not from option 1 or 2. Option 1 would not relax it, because the loop has no IOT.
- **FETCH at 24 steps** leaves about 400 ns of action after four 200 ns settles: TS1 (`MA ← PC`, PC increment), TS2 (memory read), TS3 (OPR pass or JMP PC load or EA formation), and TS4 (skip increment, sequencing). FETCH TS3 is the hardest, because the class decode (decision 2a) sits in front of the ROM access and the OPR pass follows it. A sketch is TS1 5, TS2 7, TS3 7, TS4 5 steps, with no slack.

Levers, in order of preference:
1. **Per-(MS, TS) lengths** (the TS-length table). Today's 6/9/7/6 is sized for the worst case of any state; for example, TS2's 9 steps cover an EXECUTE write-back, but FETCH TS2 only reads. Each TS gets `T_CS` plus its own action and no more.
2. **The FETCH/EXECUTE split** (finding 5): set F from FETCH's critical path, then X = 3.8 µs − 2F. The cost is per-class fidelity (OPR at 1.25 to 1.3 µs instead of 1.2), which no current test detects.
3. **A faster logic family** (AC, ACT, or F) in the `T_CS` and FETCH TS3 paths. The ROM's 150 ns stays fixed; everything around it shrinks.
4. **A finer TSTEP** (for example 40 MHz, 25 ns) to place each TP more exactly. It does not speed up the ROM.
5. Last resort: **hardwire FETCH TS1 and TS2 controls**, which are the same for every instruction, so those TSs do not wait for a ROM access (as DEC's 8/E does throughout). This departs further from "the control store drives everything"; use it only if the phase 1 estimate shows 76 steps cannot be reached otherwise.

Phase 1 must produce a per-(MS, TS) step table with a datasheet-based critical path for each TS. It must show 2F + X = 76 steps (±1) and say how close F gets to 24. **If 76 steps cannot be reached, D2AB routines 4 and 5 cannot pass on this control-store architecture under either option, and the branch stops there.**

## Phase 1: Architecture specification (review gate)

As in handoff §7.1: one document covering the new FETCH TS1 to TS4, JMP I in DEFER, the OPR pass datapath with IR-driven controls, SKIP, IR at TP2, PC and EA sources, the instruction-boundary rule and end-of-instruction signal, the TS-length table, and decisions 1 to 5 with DEC citations. It also needs a critical-path estimate for FETCH TS3 (and TS2 if decision 2b is chosen) with real part numbers.

Additions this plan needs:
- **Final control-word and address-budget layout, decided up front.** That means the 7th datapath EEPROM (yes or no), the mapping ROM's `A0` table select, the sequencer's class input, and the TS-length table's inputs. With the layout fixed, the slices fill in fields instead of repacking each time.
- **Slice boundaries**: what each intermediate v2 contains, so every slice is a consistent design and not a half-built machine.
- **TS lengths:** the per-(MS, TS) step table and critical paths described in "Timing budget" (phase 0), meeting 2F + X = 76 steps.
- **Phase 0's results** as an appendix.

**Status: done; approved 2026-11-20.** [spec.md](spec.md) and [timing.md](timing.md). The decisions are recorded in spec.md §11.

**Checkpoint 1: the user approves, or the work stops.**

### v1 and v2 side by side, built to be removed

v1 and v2 both work on this branch, but v1 support is set up so it can be deleted cleanly before the merge:

- **Docs: one set, which becomes v2.** v1's docs are on `main`. The v1 artifacts in `rom/microcode/v1/` become frozen inputs: `run_pipeline.py --design v1` runs only the packer on them and never regenerates them from `docs/`. A `main` worktree confirms the frozen v1 artifacts match what `main` generates.
- **One selection point.** A single `design` setting (pipeline `--design`, simulator `design=`), resolved in one module per package into a `Design` record. The record holds the artifact and image paths, the per-(MS, TS) time table, the reference model's cycle costs, and the instruction-boundary rule. Code reads the record and does not test `design == "v1"`.
- **Where v1 and v2 genuinely differ, keep the code separate.** For example, IR loading and FETCH sequencing go in separate small functions selected by the `Design` record. Every v1-only line carries a `# V1-ONLY` marker, and every v1-only test is either marked `V1-ONLY` too or kept in its own `*_v1.py` file.
- **Cleanup before merge (phase 10):** delete `rom/microcode/v1/`, the v1 `Design` records, everything marked `V1-ONLY`, and the selector. Then rename v2 to whatever name is chosen, at which point the remaining suites must pass unchanged. Grepping for `V1-ONLY` must return nothing.

`main` is expected to stay mostly still while this branch is active. The branch is disposable: if the result is not wanted, it is deleted and work resumes on `main`. Rebase onto `main` before merging.

## Phase 2: Behavior-neutral groundwork

Each step is a small patch, and each ends with all suites green and nothing observable changed.

| Step | Change | Verification |
|---|---|---|
| 2.1 | `Design` record and selector in the pipeline and in each tool (replacing hard-coded `rom/microcode/v1` paths and `CONTROL_DESIGN_VERSION`); per-design build directories; pipeline `--design` | Tool tests; `--dry-run --design v1` output matches the baseline |
| 2.2 | `rom/microcode/v2/` created as a copy of v1 (`control_design_version: v2`); v1 switched to frozen inputs (packer only) | v1 and v2 images **byte-identical** to each other and to `main`'s |
| 2.3 | Simulator `design=` selector (image directory, schema, packing; default v1) | Existing suites pass; a new test loads both designs |
| 2.4 | Simulator time base: replace the fixed 1.2 µs per major state with a per-(MS, TS) duration table held in `Design`, uniform for now | `elapsed_ns` identical on all lock-step tests and the MAINDEC regression |
| 2.5 | Abstract "instruction boundary" in CPU, lock-step, `DmaArbiter` re-enable, HLT/STOP/Single Instruction, `maindec._SimStepper`, and controllers' `at_boundary`. For now it is defined as EXECUTE or INTERRUPT TP4 in both designs | All suites identical; DMA random episodes identical |
| 2.6 | Reference model: cycle costs per instruction class from `Design`, replacing the fixed charge at `model.py:111` (today's values) | Lock-step elapsed-time agreement unchanged |
| 2.7 | Test runner that runs every suite under both designs; phase 0's D2AB timing check as a reference-model-only test that can be given a design | Both green; v1 reproduces the halt at 2607 |

**Checkpoint 2:** v1 and v2 identical, every suite green under both, and `elapsed_ns` unchanged. The user commits.

**Status (2026-11-19):** steps 2.1 to 2.7 implemented.
- The tools select through `tools/rom-generation/common/design.py`, and the simulator through `sim/cpu/src/pdp8_cpu/design.py`. Both read `PDP8_DESIGN`.
- `sim/run_all_tests.py` runs every suite per design.
- The step 2.2 check against `main`'s images was made by packing the unchanged v1 artifacts with the patched packer; v1 artifacts are untouched in git.
- Results are recorded in `handoff.md`.

## Slice pattern (phases 3 to 8)

Every slice goes through the same steps:
1. **Docs** (v2 only): propose each affected file and apply it once the user agrees (dependency order: 01, 03, 04, 08, 09, 07-io/06). Run a pipeline dry run for v2 after each file.
2. **Tools**: extractor, generator, and packer changes, each with tool tests. v1 still packs from its frozen artifacts.
3. **Pipeline**: the user runs it for v2 and promotes. Check the packing report against the phase 1 budget.
4. **Simulator**: v2 code paths selected by the `Design` record, with unit tests.
5. **Verify**: the v1 full suite unchanged. For v2: the full suite, lock-step random episodes (including DMA), and the MAINDEC regression under PyPy with two seeds.
6. **Checkpoint**: report results, give the user the list of diagrams affected, and the user commits.

## Phase 3, slice A: FETCH restructure with no cycle-count change

- `IR ← MDB` at TP2 (replaces `MB_TO_IR` at TP3); PC increment in FETCH TS1; EA page from MA.
- Every instruction still goes to EXECUTE, so the reference model's cycle counts are unchanged and lock-step stays strict.
- **Why first:** it exercises the new IR and PC paths with no sequencing change. Any failure is in the datapath.
- **Tests:** a new unit test for IR and MAPR at TP2 (MAPR still holds the previous instruction's entry, which is the problem decision 2 addresses). Regression for gaps A to N. All MAINDECs.

## Phase 4, slice B: direct JMP in FETCH, JMP I completes in DEFER

- Instruction-class decode (decision 2a), the sequencer's class input, and `PC ← EA` at FETCH TP3.
- Field change, `CIFP_CLEAR`, and `II_CLEAR` at FETCH TP3 for direct JMP. For JMP I, `II_CLEAR` at DEFER TP3, and the other two at DEFER TP4. JMP's EXECUTE is removed.
- The instruction boundary moves to FETCH TP4 or DEFER TP4 for JMP. The reference model's costs become JMP = 1 and JMP I = 2.
- **Why before OPR:** it introduces the new boundary rule with the fewest new datapath parts, so boundary bugs and datapath bugs stay separate.
- **Targeted tests:** interrupt recognized after a direct JMP and after JMP I; gap L (CIF then JMP) both ways; ION then JMP (one-instruction delay); autoindex JMP I; a DMA request at a FETCH-TP4 boundary; Single Step and Single Instruction over JMP; HLT and STOP during a JMP loop. Full lock-step and MAINDECs.

## Phase 5, slice D: state lengths (moved ahead of OPR)

Phase 0 showed that D2AB's timing depends on the ISZ + JMP loop and the EXECUTE length, not on OPR. After slices A and B, plus this slice, routine 4's loop has its final timing, so the acceptance test can run before the largest slice.

- Per decision 3: the TS-length table (3a) or the uniform length (3b) in the timing generator. This also closes main's open TSTEP item.
- v2's values go into the simulator's per-(MS, TS) table from 2.4, and the reference model gets matching per-state durations.
- **Acceptance:** D2AB PRG0 including routines 4 and 5, in lock-step, both seeds. (OPR's cost does not affect the loop.)
- **Tests:** the timing table against the packing and timing-constraint artifacts; elapsed-time agreement in lock-step; the phase 0 reference-only check at the edges of the window.

## Phases 6 to 8, slices C1 to C3: OPR in FETCH, one group at a time

The FETCH TS3 class decode distinguishes the groups by IR bits 3 and 11 (PDP-8 numbering, bit 0 most significant; group 1: bit 3 = 0; group 2: bit 3 = 1 and bit 11 = 0; group 3: bit 3 = 1 and bit 11 = 1). A group not yet moved keeps FETCH and EXECUTE, so every intermediate design is complete. The reference model's cycle costs change per group. Each slice gets its own exhaustive test against the reference model over a set of AC, L, MQ, and SR edge values.

### Phase 6, slice C1: group 1 (the pass unit)

- The OPR pass unit: zero gating (CLA, CLL), true/complement (CMA, CML), carry-in (IAC), and the shift/rotate/BSW multiplexer, hardwired from IR (decision 1). `ALU_OP` re-encoded or given a mode field.
- **Why first:** groups 2 and 3 reuse its zero gating and add OR inputs to it (OSR; MQA).
- **Exhaustive test:** all 256 group 1 encodings (7000 to 7377) × edge values. RAR and RAL together are excluded as undocumented, per the rules.
- **Targeted tests:** 7041-style combinations (CIA), BSW, RTL and RTR carry through L, IAC overflow into L. A timing note: FETCH TS3's critical path is now real, so check it against the phase 1 estimate.

### Phase 7, slice C2: group 2

- The SKIP register (loaded at TP3, so CLA in the same pass cannot disturb the decision), skip-sense logic, the PC increment at FETCH TS4, CLA and OSR through the pass unit, and HLT at FETCH TP4.
- Skip and interrupt at the same TP4 per decision 4.
- **Exhaustive test:** all 256 group 2 encodings (7400 to 7777 with bit 11 = 0) × edge values, including SR.
- **Targeted tests:** skip with an interrupt recognized at the same TP4 (decision 4); SMA/SZA with CLA; SKP; OSR with CLA; HLT then CONTINUE; HLT with Single Step and Single Instruction.

### Phase 8, slice C3: group 3

- The MQ OR input to the pass unit (MQA), MQL, and SWP's two paths loaded at the same TP3.
- **Exhaustive test:** all 256 group 3 encodings (odd 7401 to 7777) × edge values for AC, L, and MQ. EAE-only bits behave as documented in `docs/02-isa/03-group-3.md`.
- **Targeted tests:** SWP, CLA with MQA, MQL with MQA (ACL-style combinations).
- After this slice, cycle counts match option 2 for every instruction. D2AB PRG0 is rerun.

## Phase 9: Full verification

- All suites under CPython for v1 and v2. MAINDEC regression and full passes of the long programs (D0*, D1*) under PyPy. D2AB PRG0 end to end.
- Packing and budget review against phase 1. Final diagram list for the user. Update `handoff.md`.
- **Checkpoint 7 (user decision):** merge, and whether to plan option 1 (IOT in FETCH) later.

## Phase 10: v1 cleanup before merge

- Remove `rom/microcode/v1/`, the v1 `Design` records, every `V1-ONLY` line and test, and the selector. Rename v2 as the user decides.
- **Verification:** `grep -r V1-ONLY` returns nothing; the full v2 suite and the MAINDEC regression pass unchanged; a pipeline dry run succeeds.
- **Schema cleanup** (user, 2026-11-22): remove stale information from the maintained schema objects. Fix the docs or generators and regenerate; the user promotes. Found so far:
  - **Description:** both schema generators hard-code "for version 1 CPU control", so the v2 schemas say it.
  - **Stage:** four maintained artifacts say `generation_stage: candidate-generation`.
  - **`control_uses`:** carried forward from the previous schema and never re-derived. The 11 OPR stage-select inputs still say `predicate`, though only the pass unit uses them. `SKIP`, `ISZ_SKIP_REQ` and `OPR_SKIP_REQ` have none (the pipeline's three warnings). Review the other classifications with no direct reference; some are legitimate through derivations.
  - **Reserved values:** in eight output fields and `IR_CLASS`. Keep real spare codes, and remove leftovers of retired ones.
  - **Unselected micro-operations:** no case selects `IOT_TRANSFER_CAPTURE` or `IOT_TRANSFER_CLEAR`. Establish whether they are stale or realized by direct control.
  - **Text copied from docs:** stale consumers and constraints (docs-review A1 and A2; `IR_IS_IOT` has no consumer).
  - **Verification:** every removed item explained; ROM images byte-identical; the three warnings gone.
- Rebase onto `main`.
- **Checkpoint 10:** the user merges into `main`.

## Cross-cutting rules

- v1 stays green at every checkpoint.
- No pipeline promotion is answered on the user's behalf; use `--dry-run` only.
- Every DEC claim in docs and spec cites the KK8-E, M8330, maintenance manual, or KM8-E document (handoff §4).
- The ISA semantics do not change, so the reference model's instruction behavior is never edited; only its cycle costs and durations are.
