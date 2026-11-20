# PDP-8 Homebrew Handoff: One-Cycle OPR and JMP (Option 2)

Branch: `one-cycle-fetch`. This branch evaluates and, if the user approves, implements a change to the major-state structure: OPR and directly addressed JMP complete in FETCH, and JMP I completes in DEFER. The machine's cycle counts then match the PDP-8/E's for everything except IOT.

`main` carries the simulator's phase 3 work and its own handoff. Read that one (`git show main:handoff.md`) for the simulator's structure, status, and phase 3 plan.

**The branch is disposable.** The user may decide not to adopt option 2. Then the branch is deleted and work resumes on `main`. `main` is expected to stay mostly still meanwhile; rebase onto it before any merge.

## 1. Where Things Stand (2026-11-19)

| Phase ([option2/plan.md](option2/plan.md)) | Status |
|---|---|
| 0: baseline and feasibility | **Done.** Option 2 meets D2AB PRG0's timing only with 8/E-like state lengths (the ISZ + JMP loop at 3.75 to 3.85 µs; IOT cost irrelevant). Plan phase 0 has the results. |
| Checkpoint 0 | **Decided:** option 2; decision 3a (8/E fast/slow lengths); OPR split by group (slices C1 to C3); state-length slice D before OPR. |
| 1: specification | **Drafted, awaiting the user's review:** [option2/spec.md](option2/spec.md) and [option2/timing.md](option2/timing.md). |
| Checkpoint 1 | **Open:** the user approves the spec and the decisions in section 3, or stops the branch. |
| 2: behavior-neutral groundwork | **Done:** steps 2.1 to 2.7, every suite green under both designs (section 2). |
| 3 onward (slices A, B, D, C1 to C3) | Not started. Slice A needs checkpoint 1. |

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
| 1 | OPR controls hardwired from IR, enabled by one `OPR_PASS` select | Yes (DEC does this) |
| 2 | FETCH TS3's control word: `VARIANT = IR_CLASS` outside EXECUTE (2a) or mapping ROM from MDB (2b) | 2a |
| 3' | TS-length mechanism: a small timing ROM with speed modes; TSTEP 50 ns or 25 ns | Timing ROM; decide the TSTEP before designing the timing generator |
| 4 | Skip and interrupt at the same FETCH TP4 | No special case (same programmer-visible result as DEC) |
| 6 | `RUN` multiplexer on overlay group 1's low bits, to carry `SKIP` | Yes |
| 7 | `INSTR_END` decoded by gates from the sequencer word | Gates |
| 8 | Logic families | ACT/F on the paths in timing.md §6; **the control-store address path must be ACT** |
| 9 | **PC as a synchronous counter** (or a dedicated incrementer) | **Yes. Without it FETCH needs 25 steps; 3a exactly (24/28) is unreachable, and the fallback (25/26) has no slack.** |
| 10 | Drive AB from MA whenever the CPU owns the bus | Yes, if the memory-board design allows |
| 11 | Register `MS_EFF_IS_EXECUTE` and overlay zero-detect conditions at the preceding TP | Yes |

Notes for the review:
- **Decision 9 is invisible to the timing-state simulator.** `PC_INC` already loads PC "through a dedicated increment path" (MCS `PC_INC`). It changes the docs' hardware description and timing, not the simulated behavior, so it does not block slices A to C.
- **Datasheet gaps:** the SRAM's tOE is assumed (30 ns); the Mouser-hosted datasheet would not download. The backplane and ribbon crossing allowance (5 ns each) is an estimate.

## 4. Next Steps

1. **The user reviews** spec.md and timing.md and decides section 3. Until then, do not change `docs/`, `rom/microcode/v2/` (except through the pipeline), or the simulator's v2 behavior.
2. After approval: **slice A** (plan phase 3): IR loaded at TP2, PC increment in FETCH TS1, EA page from MA. v2 only; v1 frozen. Follow the slice pattern in the plan: docs, interactively; tools; the user runs the pipeline and promotes; simulator; verify.
3. After slice A diverges, `sim/cpu/tests/test_design.py::ImageTests` (v1 = v2 images) must be removed; its docstring says so.

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
- Stop and record in this handoff anything that needs the user's decision. Commit and push progress.

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
