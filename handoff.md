# PDP-8 Homebrew Handoff: One-Cycle OPR and JMP (Option 2)

Branch: `one-cycle-fetch`. This branch evaluates and, if the user approves, implements a change to the major-state structure: OPR and directly addressed JMP complete in FETCH, and JMP I completes in DEFER. The machine's cycle counts then match the PDP-8/E's for everything except IOT.

`main` carries the simulator's phase 3 work and its own handoff. Read that one (`git show main:handoff.md`) for the simulator's structure, status, and phase 3 plan.

**The branch is disposable.** The user may decide not to adopt option 2. Then the branch is deleted and work resumes on `main`. `main` is expected to stay mostly still meanwhile; rebase onto it before any merge.

## 1. Where Things Stand (2026-11-20)

| Phase ([option2/plan.md](option2/plan.md)) | Status |
|---|---|
| 0: baseline and feasibility | **Done.** Option 2 meets D2AB PRG0's timing only with 8/E-like state lengths (the ISZ + JMP loop at 3.75 to 3.85 µs; IOT cost irrelevant). Plan phase 0 has the results. |
| Checkpoint 0 | **Decided:** option 2; decision 3a (8/E fast/slow lengths); OPR split by group (slices C1 to C3); state-length slice D before OPR. |
| 1: specification | **Done:** every decision in [option2/spec.md](option2/spec.md) §11 decided (2026-11-20); [option2/timing.md](option2/timing.md) revision 2 reviewed. |
| Checkpoints 1 and 2 | **Approved** by the user (2026-11-20). |
| 2: behavior-neutral groundwork | **Done:** steps 2.1 to 2.7, every suite green under both designs (section 2). |
| 3: slice A | **Done** (section 1.2; committed `7758162`). |
| 4: slice B | **Done, awaiting the user's check and commit** (section 1.3). |
| 5 onward (slices D, C1 to C3) | Not started. |

### 1.2 Slice A (phase 3), 2026-11-20

IR loads from MDB at FETCH TP2 (`MDB_TO_IR`, replacing `MB_TO_IR`); PC increments at FETCH TP1; EA formation moves to FETCH TS3 with the page from MA; FETCH TS4 only sequences.

- **Docs** (v2): `01-registers.md`, `02-dataflow-and-bus-model.md`, `02-micro-operations.md`, `04-fetch-defer.md`, `01-microarchitectural-control-signals.md` (`IR_LOAD`, `EA_ADDR_SRC` purpose, a stale `MB_TO_IR` entry removed from §9.4), `08-control-store-organization.md` §5.4.2 and §5.4.3, `02-ir-derived-fields.md` (`IR_INDIRECT`), `09-timing/03-major-state-timing.md` §3 and §9.1, and **direct-control §4.2.1 → §4.3.1: the instruction fetch drives AB from MA, not PC** (found by the simulator: with PC incremented at TP1, `AB_SRC = PC` fetched the next word).
- **Tools:** no change needed. The user promoted the v2 pipeline twice (the second for the direct-control fix).
- **Simulator:** `Design.ir_source` (MDB; v1 MB) and `Design.ea_page` (MA; v1 PC), used by `datapath.py`; v1 values marked `V1-ONLY`. Tests: datapath IR-from-MDB and EA-page tests, `sim/cpu/tests/test_fetch_slice_a.py` (end-of-page MRI, FETCH TP by TP, MAPR at TP2), `ImageTests` removed. Two Windows-only test bugs fixed (path separators in `test_design.py` and the pipeline's `test_run_pipeline.py`; both failed at HEAD).
- **Verified (Windows, CPython 3.14; PyPy 3.12):** tools 17 suites OK; sim/cpu 71, memory 3, reference 18, io 29, system 77 (1 skipped) OK under v1 and v2; MAINDEC suite (seeds 1 and 2) under PyPy OK for both; D2AB timing test OK for both (halt at 2607 until slice D).
- **Diagrams:** the running list is [option2/diagrams.md](option2/diagrams.md), read from the diagram sources. Slice A: CPU_Architecture.xml A1 (add MDB → IR; IR–IDB becomes IR → IDB only) and A2 (add MA → EA_ADDR).

### 1.3 Slice B (phase 4), 2026-11-20

Direct JMP completes in FETCH (`IR_ADDR_TO_PC` at TP3, field change and `II_CLEAR` at TP3); JMP I completes in DEFER (`MB_TO_PC` at TP4; `II_CLEAR` at DEFER TP3, `DIF_TO_IF` and `CIFP_CLEAR` at DEFER TP4). JMP is removed from EXECUTE.

- **Decisions made during the slice:** sequencer A2 = one predecode `IR_NO_EXECUTE` (with A3 = `IR_INDIRECT`), not a state-dependent input; new μops `IR_ADDR_TO_PC`, `MB_TO_PC`; **decision 7 revised**: `INSTR_END` is a gate decode of registered `MS_EFF`, TS, `IR_NO_EXECUTE`, `IR_INDIRECT` (a sequencer output would loop through the DMA arbiter's `/DMA_REQ` into the sequencer address); boundary contexts written out in full in each direct control (§3.1.1 defines instruction completion).
- **Found by lock-step:** JMP I's field change at DEFER TP3 made the autoindex write-back in DEFER TS4 use the new field (`MFB_SRC = IF`). Fixed by applying the field and clearing `CIFP` at DEFER TP4; `II` still clears at TP3, so gap L holds.
- **Docs:** 01 registers; 03 state model, fetch-defer, MRI execution (JMP removed), μops, console, DMA execution; 04 IR-derived fields (`{…}` concatenation notation, `IR_CLASS`, `IR_NO_EXECUTE`), control outputs (`PC_SRC` 2 bits, `INSTR_END` in ACS §4.10), CSO §3 to §9 (class `VARIANT`, A2, packing 46 bits), direct-control §3.1.1 to §3.4; 08 interrupts ("instruction-completion TP4"); 09 timing (§9.3 invariant: a JMP never reaches EXECUTE); 07-io DMA arbitration (`INSTR_END`); 00 signal conventions.
- **Tools:** `common/predicates.py` concatenation (tests); `common/design.py` per-design `non_execute_variant`, `sequencer_a2` (v1: none); packer: class `VARIANT` outside EXECUTE, A2, class-independence check outside FETCH TS3/TS4 and DEFER, `INSTR_END` agreement check; packer fixture now sequences FETCH/DEFER realistically; 5 new packer tests. **v1 packer output byte-identical.** Reviewed decisions set by the user: `INSTR_END` role `derived`; `IR_CLASS`, `IR_NO_EXECUTE` `control_uses` `["predicate"]`.
- **Simulator:** `IR_CLASS`, `IR_NO_EXECUTE` decodes; `VARIANT = 00·IR_CLASS` outside EXECUTE (undefined IR gives three undefined class bits, high bits wired 0); A2; `PC_SRC` = 2; per-design field definitions (`encodings.datapath_fields`); packing cross-check of the two decodes; boundary rule `instr_end` (= `INSTR_END`) driving the DMA arbiter, `at_boundary`, lock-step, and reference costs (JMP 1 state, JMP I 2). Tests: `sim/cpu/tests/test_jmp_slice_b.py` (17: paths, autoindex JMP I, interrupt after JMP and JMP I, CIF then JMP with and without interrupt, CIF then autoindex JMP I, ION then JMP, DMA at FETCH TP4, Single Instruction and Single Step, STOP in a JMP loop, costs).
- **Verified (Windows, CPython 3.14; PyPy 3.12):** tools 17 suites OK; sim/cpu 88, memory 3, reference 18, io 29, system 77 (1 skipped) OK under v1 and v2; MAINDEC suite (seeds 1 and 2) under PyPy OK for both; D2AB timing: v1 halt 2607, **v2 halt 2614** (too fast at the placeholder 1.2 µs states, as phase 0 predicted; expectation updated until slice D).
- **Diagrams:** `option2/diagrams.md` B1 to B7 (MS_NEXT flowchart, mapping, organization, CPU architecture).
- **STOP at an instruction-completion TS4 (closed 2026-11-20):** with `HLT_REQ = 0` and `FP_STOP = 1` there, no context assigns `HLT_REQ_NEXT` (default 0), so STOP is captured at the next TP. The user accepts this: STOP is a human key press, held far longer than a TS. Same as v1.

### 1.1 Commits on this branch

1. The design-selection tools change and `rom/microcode/v2` (phase 2.1, 2.2).
2. The option 2 plan, spec, timing analysis, phase 0 experiment scripts, and this handoff.
3. The simulator design selection, the per-TS time base, the instruction-boundary rule, reference cycle sequences, the test runner, and the D2AB timing test (phase 2.3 to 2.7).

## 2. Phase 2 Results

| Step | What | Verified |
|---|---|---|
| 2.1 | `tools/rom-generation/common/design.py`: the single selection point. `PDP8_DESIGN` or `run_pipeline.py --design`. Every tool takes its maintained and build paths and its `control_design_version` from it. v1 keeps its original paths. | All 17 tool suites pass. Pipeline tests cover `--design` and the frozen design. |
| 2.2 | `rom/microcode/v2/` = v1 with the version and two generator source paths renamed. v1 is **frozen**: `run_pipeline.py --dry-run` (v1) runs only the packer. | `--dry-run --design v2`: every generator "unchanged". v1 and v2 images **byte-identical**; packing descriptions identical except the version. |
| 2.3 | `sim/cpu/src/pdp8_cpu/design.py`: `Design` (image directory, packing, schema, `ts_ns`, `boundary_rule`). `ControlStore.load(design=...)`, `load_store(design=...)`, `PDP8_DESIGN`. | `sim/cpu/tests/test_design.py` |
| 2.4 | `elapsed_ns` advances by each TS's duration at its TP (`Cpu.ts_ns`). v1 is 300 ns per TS, so 1.2 µs per state as before. `timing=` (per state) still works, charged at TP4. | Per-TS and override tests; lock-step elapsed-time agreement in the system suite. |
| 2.5 | One rule for "the instruction's last major state" (`design.is_last_state`, `Cpu.last_state`, `Cpu.boundary_kind`), used by the DMA arbiter context (parameter renamed `in_last_state`), `at_boundary`, lock-step, and `maindec._SimStepper`. Rule `"execute"` for both designs until slice B. | Boundary tests; system suite. |
| 2.6 | The reference model charges `instruction_states(ir)`; lock-step sets it from `design.major_states`. | Reference suite; lock-step. |
| 2.7 | `sim/run_all_tests.py` (`--design`, `--quick`, `--build`, `--no-tools`). `sim/system/tests/test_d2ab_timing.py` (`PDP8_LONG_TESTS=1`): the reference model alone runs D2AB PRG0 with the design's cycle counts; v1 and v2 expect the halt at 2607 until slice D. | v1 timing test passes under PyPy in 21 s (halt at 2607 reproduced). |

**Full-suite results (CPython 3.14, macOS), checkpoint 2 criteria met:**

| Suite | v1 | v2 |
|---|---|---|
| ROM-generation tools (17 suites, design-independent) | OK | OK |
| `sim/cpu` | 61 OK | 61 OK |
| `sim/memory`, `sim/reference`, `sim/io` | 3, 18, 29 OK | 3, 18, 29 OK |
| `sim/system` | 77 OK, 1 skipped (D2AB timing; 930 s) | 77 OK, 1 skipped (618 s) |
| D2AB timing, PyPy, `PDP8_LONG_TESTS=1` | OK: halt at 2607 (21 s) | OK: halt at 2607 (45 s) |

Lock-step elapsed-time agreement held throughout, so `elapsed_ns` at every boundary is unchanged. **Checkpoint 2 needs only the user's review of the commits.**

## 3. Decisions the User Needs to Make (checkpoint 1)

From [option2/spec.md](option2/spec.md) §11, each with a recommendation there:

| # | Decision | Recommendation |
|---|---|---|
| 1 | OPR controls hardwired from IR, enabled by `OPR_PASS` (spare `AC_SRC` and `L_OP` codes) | Yes; amend design principle §3.1 in slice C1 — **decided 2026-11-20** |
| 2 | FETCH TS3's control word: `VARIANT = IR_CLASS` outside EXECUTE (2a) or mapping ROM from MDB (2b) | 2a — **decided 2026-11-20** |
| 3' | TS-length mechanism: a small timing ROM with speed modes; TSTEP 50 ns or 25 ns | Timing ROM, **50 ns** (timing.md rev. 2) — **decided 2026-11-20** |
| 4 | Skip and interrupt at the same FETCH TP4 | No special case (same programmer-visible result as DEC) — **decided 2026-11-20** |
| 6 | `RUN` multiplexer on overlay group 1's low bits, to carry `SKIP` | Yes — **decided 2026-11-20** |
| 7 | `INSTR_END`: gates or the spare sequencer output | Gates on registered state — **decided 2026-11-20, revised the same day** (a sequencer output would loop through the DMA arbiter's `/DMA_REQ`; spec §6.1) |
| 8 | Logic families | ACT/F on the paths in timing.md §6; **the control-store address path must stay ACT** (HCT there cancels the SRAM's gain) — **decided 2026-11-20** |
| 9 | PC as a synchronous counter (or a dedicated incrementer) | **No** since decision 12: FETCH has 103 ns of margin with the ALU increment (as the 8/E) — **decided 2026-11-20** |
| 10 | Drive AB from MA whenever the CPU owns the bus | **No** since decision 12: the read has 110 ns of margin — **decided 2026-11-20** |
| 11 | Register `MS_EFF_IS_EXECUTE` and overlay zero-detect conditions at the preceding TP | **Not required** since decision 12 — **decided 2026-11-20** |
| 12 | **SRAM-shadowed control store** | **Decided 2026-11-20: yes, with option 2** (spec §11.1) |

### 3.1 Session of 2026-11-20 (Windows host)

The user reviewed the spec with questions and decided **option 2 + SRAM shadow** (decision 12, spec §11.1).

Phase 0 rerun on this host (PyPy 3.12, scratch script, not committed):
- v1 today: halt at 2607; option 2 with 3a lengths: PASS. Both match the macOS runs exactly.
- **v1 cycle counts with uniform states** pass only at 0.937 to 0.962 µs per state (0.925: halt 2652; 0.975: halt 2650). v1 + SRAM at 19 × 50 ns would also have passed D2AB, but with per-class errors (OPR and JMP +58%, MRI −27% against the 8/E). The user chose option 2 for per-class fidelity.

Points raised in the review that the spec does not yet cover (resolve before or during checkpoint 1):
1. **Group 3 MQL has no control input.** **Decided 2026-11-20: class 6 = group 3 with MQL** (fits, no new bits; spec §2). The spec loads MQ through `MQ_LOAD`, but `IR_CLASS` 5 does not distinguish MQL. Options: a sixth class (6 = group 3 with MQL), or gate `MQ_LOAD` from the IR bit like the rest of the pass unit.
2. **Decided 2026-11-20: `OPR_PASS` is spare codes, not a new bit.** It can be a spare `AC_SRC` code (7) and the freed `L_OP` COMP code. With OR, NOT, and the rotates gone from `ALU_OP` (4 → 2 bits) and MQ and FP_SR gone from `ALU_B_SRC` (2 → 1 bit), the datapath word shrinks to about 42 of 48 bits instead of growing to 46.
3. **Decided 2026-11-20: `EA_FORMED` at TP3.** Direct JMP's PC source: `EA_FORMED` at TP3 (spec, DEC's TS3) or `PC ← EA_ADDR` through the IDB at TP4 (no new PC source, no `PC_SRC` widening; not programmer-visible).
4. **Decided 2026-11-20, then revised: `INSTR_END` is a gate decode of registered state** (decision 7; spec §6.1).
5. **Decided 2026-11-20 (with decision 1), applied in slice C1. Design principle:** the OPR pass unit (IR bits gating the datapath) departs from `00-design-principles.md` §3.1 ("no hardwired control logic"); amend the principle explicitly.
6. **`02-group2-execution.md`** says "No persistent flag state is introduced"; the SKIP register changes that. `SKIP_TAKEN` keeps its inputs and becomes SKIP's D input; group 3's `SKIP_TAKEN` overlay bit is freed.
7. **timing.md revision 2 done** (2026-11-20, awaiting review): control-store SRAM AS7C256C-15PCN (PDIP; the B part is discontinued); `T_CW` 81 ns; proposed lengths FETCH/plain DEFER 5/8/6/5 = 24, EXECUTE/autoindex DEFER 6/9/7/6 = 28 (3a exactly), at least 50 ns margin per TS. Main memory left unchosen (the user's instruction): any part up to about 165 ns access fits (timing.md §4.4).

Notes for the review:
- **Decision 9 is invisible to the timing-state simulator.** `PC_INC` already loads PC "through a dedicated increment path" (MCS `PC_INC`). It changes the docs' hardware description and timing, not the simulated behavior, so it does not block slices A to C.
- **Datasheet gaps:** the SRAM's tOE is assumed (30 ns); the Mouser-hosted datasheet would not download. The backplane and ribbon crossing allowance (5 ns each) is an estimate.

## 4. Next Steps

1. **The user checks and commits slice B** (section 1.3).
2. **Slice D** (plan phase 5): the TS-length table (decision 3a, timing.md rev. 2: FETCH and plain DEFER 5/8/6/5, EXECUTE and autoindex DEFER 6/9/7/6 at 50 ns) in the docs and the simulator's per-TS time base; acceptance is D2AB PRG0 routines 4 and 5 passing. Also decide where the SRAM shadow (decision 12) enters the hardware docs.
3. (Done) **Slice B** (plan phase 4): direct JMP completes in FETCH (`PC ← EA_FORMED` at TP3, field change and `II_CLEAR` at TP3), JMP I completes in DEFER; the class decode (decision 2a), `IR_ONE_STATE` and `IR_IS_JMP` sequencer inputs, and the boundary rule moving to FETCH TP4 / DEFER TP4 for JMP. Same slice pattern: docs interactively (searching every doc directory, including `04-control/30-direct-control-definitions`, for each affected register and TS), tools, the user runs the pipeline, simulator, verify. Add each slice's diagram changes to `option2/diagrams.md` from the diagram sources.

## 5. Resuming on Another Machine

`build/` is not committed, so the images must be packed first:

```text
git checkout one-cycle-fetch
python tools/rom-generation/pipeline/src/run_pipeline.py --dry-run              # v1 (frozen: packer)
python tools/rom-generation/pipeline/src/run_pipeline.py --dry-run --design v2  # v2 (every stage)
python sim/run_all_tests.py --quick       # tools and unit suites, both designs
python sim/run_all_tests.py --no-tools    # adds the system suite (about 6 min per design, CPython)
PDP8_LONG_TESTS=1 pypy3 -m unittest discover -s sim/system/tests -p "test_d2ab_timing.py"
```

Or `python sim/run_all_tests.py --build` to pack both designs first.

Expected:
- every suite OK under both designs;
- pipeline SUCCEEDED for both, with nothing pending;
- system suite 76 tests, plus the skipped D2AB timing test;
- the D2AB timing test passes, with v1 halting at 2607.

The phase 0 scripts are in `option2/experiments/`. `main`'s handoff describes the Windows setup (Git Bash, PyPy in Downloads). This session ran on macOS with Homebrew `pypy3.12`.

## 6. Rules

The rules of `main`'s handoff apply, with these differences:
- Work on `one-cycle-fetch`, not `main`. Do not merge into `main` without the user's instruction.
- Keep v1 working beside v2 (`PDP8_DESIGN`), built to be removed: mark v1-only code and tests `# V1-ONLY`. Plan phase 10 removes them before the merge.
- `docs/` describe v2 from slice A on. v1 is frozen: it is packed from `rom/microcode/v1/` and never regenerated.
- Every claim about DEC behavior cites a DEC document (section 7). Where this design deliberately differs (IOT keeps EXECUTE), say so.
- Stop and record in this handoff anything that needs the user's decision. **Do not commit or push unless the user says to; stop after each phase so the user can check and commit** (user instruction, 2026-11-20).

## 7. DEC Facts (verified)

Sources, all on deramp.com under `011-Digital Equipment Corporation/02 PDP-8e/`:
- KK8-E Central Processor Theory of Operation;
- M8330 Timing Generator Theory of Operation;
- PDP-8/E, 8/F, 8/M Maintenance Manual Volume 1, Processor (Sep 1973);
- KM8-E Memory Extension Theory of Operation.

The scans carry an OCR text layer. The Small Computer Handbook (8/E, 8/F, 8/M) is scanned on a mirror that blocks automated downloads; the maintenance manual's flow diagrams cover the same material.

- **Cycles.** "A one-cycle instruction can be an OPR microinstruction, an IOT instruction, or a directly addressed JMP instruction." "A two-cycle instruction involving the DEFER state can only be a JMP." MRIs take one fast FETCH (1.2 µs) and one slow EXECUTE (1.4 µs), 2.6 µs in all.
- **Fast and slow cycles** come from core memory's destructive read and write-back: the slow cycle lengthens TS2 by 200 ns so modified data can reach the write half. FETCH and non-autoindex DEFER are fast; EXECUTE and autoindex DEFER are slow.
- **OPR runs in FETCH TS3, in one pass, loaded at TP3:**
  - AC goes onto the DATA bus. CLA works by not gating AC, which gives zeros.
  - The data control gate passes true or complement (CMA).
  - The adder's register input is 0, and its carry-in is IAC.
  - A 74151 adder-output multiplexer then selects no shift, left, right, twice, or BSW.
  - AC and L load at TP3.
  
  The handbook's four-step group 1 order (CLA/CLL; CMA/CML; IAC; rotates or BSW) is the order in which these stages compose, and all four happen in the one pass ("Because each instruction takes one memory cycle … 7001 can be combined with 7040 to give 7041").
  
  Group 2: combinational skip logic sets a SKIP flip-flop at TP3; CLA and OSR happen in the same pass. Group 3: MQA is an OR in the data-line multiplexer; SWP uses two paths loaded at the same TP3.
- **FETCH TS4.** The interrupt check comes first: INT IN PROG forces JMS into IR, selects EXECUTE, and loads 0 into CPMA. Otherwise PC, plus 1 if SKIP, goes into CPMA at TP4. If an interrupt is honored at the same TP4 as a skip, the increment is not made in TS4; it is made during TS2 of the forced JMS.
- **Direct JMP:** "the PC is modified during TS3"; the next cycle is FETCH. JMP I: the next cycle is DEFER, which completes it.
- **IOT** runs in FETCH TS3, with I/O PAUSE, C lines, and BUS STROBE at TP3. Slow or multi-transfer peripherals stall TS3 with NOT LAST TRANSFER. Option 2 does not adopt this; IOT keeps EXECUTE.
- **KM8-E:** INT INHIBIT is "negated at TP3 whenever a JMP or JMS instruction occurs" (already matched by gap L on `main`).

## 8. Risks

- **Hardware timing,** which the timing-state simulator cannot see. option2/timing.md estimates 1 to 2 steps of slack with decision 9 and none without it. Verify on the first boards with the uniform-slow mode as a fallback.
- **New-boundary corner cases:**
  - skip with interrupt at FETCH TP4;
  - CIF and II around a direct JMP;
  - DMA re-enable;
  - Single Step.
  
  Each slice has targeted tests for these.
- **Tooling restructure** in the extractor and generator. The packer's address-by-address verification and the tool tests limit the risk.
- **Documentation consistency** across about 30 files, plus the user's diagrams (spec §9 lists them).
