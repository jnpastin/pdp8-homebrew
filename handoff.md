# Handoff: `one-cycle-fetch`, Validation and Merge Readiness

**Your job:** help the user make this branch functional, clean, and ready to merge into `main`. The design work is done. What remains is to validate it, make the documents consistent and readable, clean up the tooling and generated artifacts, follow the user's diagram updates, and prepare the merge.

Read this whole file first, then [docs/00-overview/97-documentation-conventions.md](docs/00-overview/97-documentation-conventions.md), before touching anything.

---

## 1. What the Branch Is

A PDP-8/E-compatible homebrew CPU, documented in `docs/`, with a microcoded control store generated from those documents (`tools/rom-generation/`) and a simulator (`sim/`) that runs the generated images.

This branch, "option 2", changes the major-state structure so that cycle counts match the PDP-8/E:

- every OPR and a direct JMP complete in FETCH; a JMP I completes in DEFER
- the MRIs other than JMP, and every IOT, complete in EXECUTE. IOT keeping EXECUTE is a deliberate difference from DEC, stated in IOT Execution §3

It also replaced the timing model and settled a long design review. Two control designs coexist:

- **v1**, the original, is frozen: `rom/microcode/v1/` is packed but never regenerated. It stays green until plan phase 10 removes it. v1-only code and tests are marked `# V1-ONLY`.
- **v2** is the design the docs describe. It is selected by `PDP8_DESIGN=v2` or `--design v2`.

`option2/` holds the working records: `plan.md`, `spec.md`, `timing.md`, `docs-review.md`, `diagrams.md`, `timing-budget.md`, and `experiments/`. **It is removed before the merge**, so `docs/` must stand alone.

### 1.1 State at handoff (2026-11-23)

- Branch HEAD `9598dad`. Its last commit added [docs/03-microarchitecture/07-opr/00-pass-unit.md](docs/03-microarchitecture/07-opr/00-pass-unit.md), linked from the OPR README, and the two tools in `option2/experiments/` (section 5.3).
- Every review item in `option2/docs-review.md` is applied or closed, except section O (moves out of `option2/`) and H3 (a DEC references appendix, which the user declined).
- Plan phases 0 to 9 are done. **Phase 10 (v1 removal, schema cleanup, pipeline reporting, rebase) has not started.**
- No diagram source has changed on the branch (`git diff main -- diagrams` is empty). The user is updating them now.

### 1.2 Baselines to reproduce

| Check | Expected |
|---|---|
| `run_pipeline.py --dry-run --design v2` | every stage unchanged, nothing pending |
| `run_pipeline.py --dry-run --design v1` | packer only, succeeds |
| packed v2 images | 43 datapath bits in 6 devices; 7-bit sequencer slice; 105,411 address checks |
| `sim/run_all_tests.py --quick` | all suites pass |
| system suite (PyPy), each design | 83 tests, OK, 2 skipped (the long D2AB timing test and the opt-in MAINDEC full passes) |
| `option2/experiments/timing_budget.py` | 2,737 checks, 0 failing |
| `option2/experiments/check_links.py` | 1,923 links, 0 bad |
| pipeline warnings | 4 `CONTROL_USES_UNRESOLVED` (SKIP, ISZ_SKIP_REQ, OPR_SKIP_REQ, IR_IS_SRQ), known; phase 10 removes them |

---

## 2. Design Decisions That Govern Validation

These are the user's decisions. **Do not re-open them**; check the documents and the code against them. Each is recorded in the docs at the place named.

### 2.1 Timing (Timing Terminology and Timing Architecture)

- **The invariant:** everything a TSn uses derives from state committed by TP(n−1). Nothing selects or commits during a TS, and a controller's response never depends on DB in the same TS.
- **Nothing visible changes during TP.** Each register that holds machine state has two ranks: r1 captures at TP's rising edge; r2 publishes at TP's falling edge, together with the TS change. Only r2 reads r1. The one decode between ranks is `MS_EFF_IS_EXECUTE` (decision 11a).
- **One TP clock** from one flip-flop. TSn is a synchronous enable. Never gate a clock from TP and TS.
- **TCLK 20 MHz.** TS lengths: fast 5/8/6/5, slow 6/8/7/7, console transaction 9. TP is two TSTEPs only where memory can be written (DEFER with auto-index TS4, EXECUTE TS3 and TS4, INTERRUPT TS3, DMA TS2, TP_FP); `/WR_PULSE` is its first step.
- DB strobes are decoded from `IOT_TRANSFER` within `DB_VALID`. `/RD` and the CPU's MDB drive are gated off in an IOT's EXECUTE. `/INITIALIZE` is decoded.
- `/IO_WAIT` is removed. Its fallback, if hardware ever needs one, is recorded in I/O Timing §5.
- **Rejected; never propose again:** trailing-edge capture; bus-hold latches with single-rank registers; both ranks on one edge; r2 before r1; a 28-bit memory capture register; mid-TS validity windows such as `WR_VALID`.

### 2.2 Control and datapath

- The control store is EEPROM shadowed in SRAM, copied during the power-on reset. The output enables follow `LOADING`, with a one-TCLK gap (CSO §8.1).
- Control Model §8.4 lists the only realizations outside the control word: predecode gates, the OPR pass unit, registered `MAPR`/`MS_EFF_IS_EXECUTE`/`SKIP`, RUN-selected overlays, decoded outputs, the timing ROM.
- `SKIP` is the one stored decision: a Group 2 OPR's skip, from FETCH TP3 to TP4.
- `AC_CLEAR` uses `AC_SRC` = 5 (ZERO), not the ALU, so an IOT can skip and clear at one TP. v1's code 5 means MQ.
- A field needs a valid value only where its Value Required When holds (Control Word §5.6; packer bit sharing).
- A direct JMP loads IF at FETCH TP4 and a JMP I at DEFER TP4, both as on the KM8-E. A JMS loads IF at EXECUTE TP1, a documented one-TP difference.

### 2.3 Console, inputs, power-on

- The panel input register (STOP, SS, SI, FP_SR, FP_IF, FP_DF) captures at every TP, and at command acceptance while halted. `/INT_REQ` has no extra synchronizer (External Inputs §2).
- EXAMINE and DEPOSIT load FETCH as the held major state, as START does. CONTINUE then starts a new instruction, matching the PDP-8/E.
- The power-on reset ends by running one console CLEAR transaction, so controllers initialize at a console TP (`TP_FP`).

### 2.4 I/O and DMA

- An IOT that clears its controller's interrupt condition or enable, or a DMA request, commits the clear by TP3. CAF is the exception (Controller Contract §9.1, §9.2).
- A device event wins over an IOT clear at the same TP. `/INITIALIZE` and an aborting IOT (DCLC) are the exceptions (Controller Contract §5.1).
- A DMA request reflects the transfer at the TP2 that completes it. A held selection with no request is dropped at TP1. TP3 with no selection clears burst-enable (DMA Arbitration §11, §13.3).
- RK8E, confirmed against DEC's Small Computer Handbook (1973), pp. 6-70 to 6-74:
  - it transfers at the Current Address, then increments, so the bootstrap loads from 0000;
  - DCLR clears status first;
  - a seek or recalibration sets Done when it starts and leaves the controller free, with Done again on completion if `COMMAND[7]`.

---

## 3. Work to Do

Do these in order. **Report findings to the user and wait for approval before changing anything.** For each fix:
1. Propose it.
2. Apply it to a scratch copy and verify it there.
3. Apply it to the repo.
4. Let the user promote and commit.

### 3.1 Validate the work

Re-run every baseline in section 1.2. Then check the three representations against each other:

- **docs and generated artifacts:** run the pipeline in a scratch copy. Every maintained artifact under `rom/microcode/v2/` must equal a fresh generation, and every content field must say what the docs say.
- **artifacts and the simulator:** the simulator interprets the packed images. Its hand-written datapath (`sim/cpu/src/pdp8_cpu/datapath.py`) and controllers (`sim/io`, `sim/reference`) must implement what the docs say, including everything in section 2.
- **simulator and DEC:** the MAINDEC regressions and lock-step tests are the evidence. The D2AB timing test runs only with `PDP8_LONG_TESTS=1` under PyPy.

### 3.2 Documents: up to date and consistent

The review fixed what it found, but the branch changed a lot in two days. Read **every document in `docs/` in full**, for two kinds of reader:

- **Human:** accurate, consistent with the other documents, and readable. Watch for stale statements about the old timing (one-step TP everywhere, `WR_VALID`, `/IO_WAIT`, 6/9/7/6), about JMP or OPR in EXECUTE, and about "MS changes only at TP4". Check that each term has one spelling and that every cross-reference is right.
- **Machine:** the pipeline parses parts of `docs/`. The conventions document lists what it reads and the traps. A prose edit in a parsed document can change the ROM silently, and a dry run does not show it. After any docs change, diff every artifact's content, not only the images (section 5.3).

Also check that `docs/` never links into `option2/`. It doesn't today; keep it that way.

### 3.3 Constraints, invariants, and rules

Sweep the docs, the control words, and the simulator for violations of the rules in section 2 and of those stated in Control Constraints, the invalid-conditions documents, and Timing Architecture §7. In particular:

- anything a TS uses that is not committed by the previous TP;
- anything that changes during TP;
- a register with two sources at one TP, or a bus with two drivers;
- a decision made outside the control store that is not in Control Model §8.4.

The equivalence analyzer's report (`build/simulation_outputs/rom-generation-v2/control-word-equivalence-analyzer/analysis-report.txt`) lists each input's significance. Every `unreferenced` input must appear in the control input index §7.

### 3.4 The generation pipeline

- Run every tool's tests. Read each extractor and generator against the conventions document, looking for silent parsing assumptions. Known ones:
  - **one block per label:** a second code block after "External ownership:" is not parsed;
  - **binary value ranges:** a range such as `0000-7777` must be written in binary, one digit per bit;
  - **reviewed `control_uses`:** a new input gets no `control_uses` until someone reviews it and writes it into the maintained schema.
- **Reformat the pipeline's output** (plan phase 10, "Pipeline change reports"). A stage whose candidate differs from the maintained artifact only in source line references must be reported apart from one with a content change, in the stage summary and in the `CHANGED_*` diagnostics. `option2/experiments/json_content_diff.py` shows the comparison rule.
- **Schema cleanup** (plan phase 10): the stale descriptions, stage names, `control_uses`, reserved values, unselected micro-operations, and copied text listed there. The ROM images must stay byte-identical, and the three warnings must go.

### 3.5 Diagrams

The user updates the diagrams; **you never edit them.** As each one changes, read its source file, never a rendering, and validate it in full against the docs. Section 6 gives notes on what each probably needs. They are context only, written before some of the latest changes: verify every point against the current docs. Keep `option2/diagrams.md` current until it is removed.

### 3.6 Before the merge

- **Section O of the review:**
  - O1: no `docs/` links into `option2/` remain. Re-check at the end.
  - O2: the user declined a DEC references appendix (H3), so the source key stays in `option2/spec.md` and in section 7 below. Ask the user where it should live after `option2/` goes, along with the reasons for decisions 9 to 12.
  - O3: `option2` is still referenced in `rom/microcode/v2/README.md`, `tools/rom-generation/README.md`, `tools/rom-generation/common/design.py`, `sim/cpu/src/pdp8_cpu/design.py`, `sim/io/src/pdp8_io/dma.py`, `sim/run_all_tests.py`, `sim/system/tests/test_d2ab_timing.py`, and eight `sim/cpu/tests` files.
  - O4 to O6: the diagram list, the review file, and the schema cleanup.
- **Move what must survive** out of `option2/`. `experiments/timing_budget.py` and its report belong with the timing docs or tools; ask the user.
- **Plan phase 10:** remove v1 (`rom/microcode/v1/`, the v1 `Design` records, every `V1-ONLY`, the selector), then rebase onto `main`. The user merges.

---

## 4. Rules (the user's)

- **Never commit or push unless the user says to.** Stop after each piece of work so the user can check and commit. Commits go on `one-cycle-fetch`. End a commit message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Never promote in the repo.** Run `--dry-run` there; the user promotes. You may promote in scratch copies.
- **Never edit diagrams.** Read their source files; never infer content from a rendered image.
- **Propose, then apply after approval,** one item at a time unless the user groups them.
- **Match DEC.** For each design option, give the DEC precedent, and keep documented fact separate from inference. Cite the DEC document for every claim about DEC behavior.
- v1 stays green until phase 10.
- No subagents unless the user asks.
- Never send personal or project details to outside services.
- Downloaded files are untrusted: put each in its own new directory, and read it with `python -I`.
- bitsavers refuses automated fetches; don't retry it. deramp.com has the DEC scans with OCR text.
- **Never quote a timing margin without running** `option2/experiments/timing_budget.py`. Hand-picked paths were wrong repeatedly.
- `docs/` must read well for people and parse correctly for tools. When the two conflict, ask.

---

## 5. How to Work Here

### 5.1 Environment (Windows)

- Git Bash for shell work; PowerShell for `System.Drawing`. `cd` persists only inside the repository; use absolute paths.
- PyPy is at `~/Downloads/pypy3.12-v8.0.1-win64/pypy3.12-v8.0.1-win64/pypy3.12.exe`. Use it for the system suite, which runs about 1 minute per design.
- `python -I` ignores `PYTHONIOENCODING`, so add `-X utf8`.
- Long heredocs in Bash can fail to parse; write long scripts to a file. A comment line such as `# ... encoding: 7401` is taken by Python as a source-encoding declaration.
- Writing files can strip trailing double spaces, which are Markdown line breaks used in many docs. Edit scripts must match line ends with optional trailing spaces.

### 5.2 Commands

```text
python tools/rom-generation/pipeline/src/run_pipeline.py --dry-run --design v2
python tools/rom-generation/pipeline/src/run_pipeline.py --dry-run --design v1
python sim/run_all_tests.py --quick
cd sim/system/tests; PDP8_DESIGN=v2 <pypy> -m unittest discover -p "test_*.py"   # and v1
cd sim/system/tests; PDP8_FULL_PASSES=short PDP8_DESIGN=v2 <pypy> -m unittest test_maindec_full_passes   # all: 2 to 3 hours
python -I -X utf8 option2/experiments/timing_budget.py
python -I option2/experiments/check_links.py
```

`build/` is not committed. A fresh checkout needs `run_pipeline.py --dry-run` for both designs, or `run_all_tests.py --build`, before the simulator can load images.

### 5.3 Testing a change in scratch

1. Copy the tracked and untracked files: `git ls-files -co --exclude-standard | tar -cf - -T - | tar -xf - -C <scratch>`.
2. Make it a git repo, and promote there until nothing changes. That can take two or three runs.
3. Snapshot `rom/microcode/v2` and the packed images.
4. Apply your edit, then promote again until nothing changes.
5. Compare each artifact with `option2/experiments/json_content_diff.py` and the images with `diff -rq`.
6. Run the suites and the link check.
7. Apply the resulting `git diff` to the repo with `git apply`, then confirm that each file matches the scratch copy.

If the repo has an unpromoted change, promote it in scratch *before* applying yours, so the diff shows only your change.

---

## 6. Diagram Notes (context only: validate against the docs)

Element ids and full detail are in `option2/diagrams.md`. Its "Final list" predates the timing work, and still shows 6/9/7/6; the notes below supersede it.

| Diagram source | Probably needs |
|---|---|
| `microarchitecture/cpu-architecture/CPU_Architecture.xml` | MDB → IR, with IR no longer loaded from the IDB. MA → EA_ADDR as the page source. The formed address → PC. An `INSTR_END` output to the DMA arbiter. The OPR pass unit (inputs AC, L, MQ, FP_SR; outputs AC, L, MQ). The `SKIP` register. Remove FP_SR → ALU B, MQ → ALU B, and MQ → AC. The AC zero input (`AC_SRC` = 5) and the panel input register, only if the diagram shows that level. |
| `control/ms_next-flowchart.xml` | FETCH goes to the instruction-completion decision for a direct JMP or any OPR; DEFER does for a JMP I. If console paths are drawn: START, EXAMINE, and DEPOSIT load FETCH; power-on ends with CLEAR. |
| `control/control-store-mapping.xml` | The wired 0 into the 5-bit variant MUX becomes `00·IR_CLASS`. |
| `control/control-store-organization.xml` | Sequencer slice inputs `IR_NO_EXECUTE` (A2) and `IR_OPR_HLT` (A1). The datapath slice is 43 bits. Optionally, the EEPROM-to-SRAM shadow with `LOADING`-driven output enables. |
| `control/control-store-overlay.xml` | The RUN multiplexer on the group 1 low bits. Group 3's DP_OVL[4] (old `SKIP_TAKEN`) and DP_OVL[3] become wired 0; `ISZ_SKIP_REQUIRED` becomes `ISZ_SKIP_REQ` on DP_OVL[2]; `IF_CHANGE_PENDING` is removed (docs review C4.4). `/INT_REQ` qualified by the SRQ decode. |
| `control/control-store-address-formation.xml` | `MS_EFF_IS_EXECUTE` is a registered bit (decision 11a), not a comparator on `MS_EFF`. Read the source to see what it shows. |
| `timing/cpu-timing-overview.json` | Fast 5/8/6/5 and slow 6/8/7/7, two-step TPs where memory can be written, console 9. |
| `io/io_timing.json` | EXECUTE 6/8/7/7, TP3 and TP4 two steps. The DB strobes and DB open 100 ns into the transfer TS. A transfer is in TS3 (requested in TS2) or TS4 (requested in TS3). |
| `io/io_wait_timing.json` | Obsolete: `/IO_WAIT` is removed and no document links it. Delete it or keep it as history; the user decides. |
| `io/io_subsystem.xml` | Remove "IO_WAIT" from the response label (cell `ld4gAUsl70I4UcyXSL3b-61`). |
| `io/dma_timing.json` | DMA 6/8/7/7, TP2 two steps, `/WR_PULSE` over its first step. The controller drives only in TS2. |
| `memory/memory_timing/source/memory_timing.png` | This is WaveDrom text with a `.png` name; rename it `.json`. Show a write TS with a two-step TP and `/WR_PULSE`. |
| `isa/addressing-model.xml` | Not yet checked since A1.5. The docs now take the current page from the instruction's own address (IA). If the diagram says PC, it needs the same change. |
| `architecture/High-Level-Architecture.xml`, `architecture/class-a-buses.xml` | No change found. Re-check against the bus docs (AB and DB names; `INSTR_END` on the CPU-to-arbiter interface). |

No diagram exists for the timing ROM, TSEQ, the two register ranks, or the shadow copy. Whether to draw them is the user's call.

---

## 7. DEC Sources

Cited in the docs and in `option2/spec.md`:
- **KK8-E:** Central Processor Theory of Operation
- **M8330:** Timing Generator Theory of Operation
- **KM8-E:** Memory Extension Theory of Operation
- **Maintenance manual:** PDP-8/E, 8/F, 8/M Maintenance Manual Volume 1, Processor (Sep 1973)
- **MAINDEC-8E-D1HA, -D2AB:** diagnostics

The first four are scans on deramp.com with an OCR text layer. The user has two more on their Desktop: the *PDP-8/E Small Computer Handbook* (1973), whose RK8-E chapter is on pp. 6-67 to 6-74, and an RK8 (RK08, not RK8-E) maintenance manual. Both are scans with no text layer. To read them, extract the CCITT page images into TIFFs and convert them with `System.Drawing`. SIMH's `PDP8/pdp8_rk.c` (open-simh) is a secondary source.

Key facts already used:
- One-cycle instructions are OPR, IOT, and direct JMP; DEFER-only two-cycle is JMP I.
- OPR runs in FETCH TS3, in one pass, loaded at TP3.
- The 8/E does an IOT within FETCH: transfer at TP3 (BUS STROBE), interrupt sampled at TP3 (INT STROBE).
- The KM8-E clears its interrupt inhibit at TP3 of a JMP or JMS, and loads IF at the TP4 before the target.
- CONT after EXAM or DEP causes a FETCH.
- Power-up INITIALIZE is the CLEAR key's signal.
