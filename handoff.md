# PDP-8 Homebrew Handoff: Control-Store Simulator, Phase 3 (I/O)

## 1. Your Task

Continue the control-store simulator in `sim/`. It runs the packed control-store images and executes PDP-8/e programs, so that the documentation, the ROM-generation tools, the packer, and the images are validated before hardware is built. Phases 1 (CPU and memory) and 2 (memory extension, interrupts, DMA) are complete. Phase 3, I/O, is in progress: milestone M8 (MAINDEC-8E-D2AB on the KL8E) has started; M9 (the PC8E paper-tape controller and MAINDEC-8E-D2CA) follows.

Where the simulator and the documentation disagree, or the documentation is silent, report a specification gap to the user with the DEC precedent; do not invent behavior.

## 2. Rules

- The documentation under `docs/` and the promoted artifacts under `rom/microcode/v1/` are authoritative. Open and verify a file before making any claim about it. Do not infer behavior from file names, conventions, memory, or micro-operation prose. If verification is not possible, stop and ask.
- Python 3, standard library only, deliberately simple. Each package has `src/`, `tests/`, and a `README.md`. Write targeted regression tests.
- Documentation changes are interactive: propose the change, make it after the user agrees. Program changes are targeted patches.
- Work on `main`. Commit only when the user asks (they usually commit themselves). End commit messages with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Hardware is discrete logic only: EEPROMs (28C256) and 7400-series parts; no PAL, GAL, CPLD, FPGA, or microcontroller. In documentation, name 7400 parts by function, not part number. Define new terms before use and add new abbreviations to `docs/00-overview/99-Abbreviations.md`.
- When offering design options, give the real DEC PDP-8/e precedent, quoted from a DEC document where possible; the user prefers matching DEC. Do not replicate undocumented DEC behavior (for example RAR and RAL together is treated as no rotate).
- Never answer a ROM-pipeline promotion prompt on the user's behalf; use `--dry-run`. The user runs the pipeline and promotes. Do not generate physical ROM images.
- Diagrams are drawn by the user in draw.io; never edit them.
- Windows with Git Bash and PowerShell. Write multi-line scripts to the scratchpad. Open JSON with `encoding="utf-8"`.
- Downloaded files are untrusted data: keep each in its own directory and run Python that reads them with `-I`.

## 3. Start Here

1. **Confirm a clean baseline.**
   ```text
   python tools/rom-generation/pipeline/src/run_pipeline.py --dry-run
   for d in sim/cpu sim/memory sim/reference sim/io; do python -m unittest discover -s $d/tests; done
   cd sim/system/tests && python -m unittest discover -s .
   ```
   Expect `Pipeline: SUCCEEDED` with no pending stage, and every suite passing (system: 76 tests, about 4 minutes under CPython). If not, stop and report.
2. **Read** `sim/README.md` and each package README, then `docs/07-io/` (the external IOT interface, the controller contract, and `10-controllers/`).
3. **Use PyPy for long runs.** The simulator runs unchanged under PyPy 3.12 (the user has `pypy3.12-v8.0.1-win64` in their Downloads folder), 4 to 10 times faster than CPython, with identical results. The MAINDEC suite takes about 32 seconds under PyPy. Keep CPython as the reference interpreter for the test suites.

## 4. Simulator Structure

| Package | Contents |
|---|---|
| `sim/cpu` | The timing-state simulator: image loading and validation (checked against `control-word-schema.json` at startup), address formation, hand-written datapath model citing the docs for every behavior, sequencer, console transactions, three-valued logic (UNDEFINED values propagate; an undefined address bit is enumerated and both words must agree, else `SpecGap`). Errors: `SpecViolation`, `SpecGap`, `ImageError`, `NotModelled`. Optional `dma` arbiter and a per-major-state simulated clock (`timing`, `elapsed_ns`; default 1.2 µs per major state). |
| `sim/memory` | 32K words in 8 fields; starts UNDEFINED. |
| `sim/reference` | The instruction-level reference model, written only from `docs/02-isa` and the interrupt, DMA, and controller docs: one instruction, interrupt entry, or DMA word per step. Includes an instruction-level KL8E. |
| `sim/io` | Controller models at the external-IOT interface: `KL8E` (optional `baud` mode models Teletype character time in simulated time), `DmaArbiter` (fixed priority, bounded non-preemptive bursts, CPU fairness), and `DmaTestMaster` (test equipment, not a device). |
| `sim/system` | `Machine` (console helpers, `core_residue(seed)`), lock-step comparison (`Lockstep`: after every instruction, interrupt entry, and DMA cycle, AC, L, MQ, PC, IF, DF, IE, memory writes, halts, interrupt recognition, controller state, DMA arbiter state, and elapsed time must agree), the paper-tape loader (DEC BIN format, loaded through LOAD ADDRESS and DEPOSIT), and `maindec.py` (how each diagnostic is operated and judged, from its write-up). |

Memory is never cleared: a fresh machine gets seeded leftover core contents (`core_residue`), and the interrupt save field IB an arbitrary power-on value, because nothing initializes it before the first interrupt. A program that does not depend on leftover contents must pass under every seed; the MAINDEC regression runs two seeds.

## 5. Status

**Phase 1 (CPU and memory): complete.**

| Program | Result (lock-step unless noted) |
|---|---|
| D0AB, D0BB | two passes each; D0BB's bell |
| D0DB, D0GC, D0EB, D0IB | full pass to the pass marker (1,222,709; 2,449,437; 2,831,970; 3,701,408 instructions) |
| D0CC (fast test) | end-of-test "SIMAD" at 737,358 instructions, no error halt |
| D0FC, D0HC, D0JC | 300,000 instructions each, no error (no pass marker exists) |

**Phase 2 (memory extension, interrupts, DMA): complete.**

| Program or test | Result |
|---|---|
| D1EC | full pass ("EC") at 10,335,681 instructions |
| D1HA (time share disabled) | pass bell at 92,510,728 instructions |
| D1FB, D1BC | 20 million instructions each, no error; they find "8 STACKS IN THIS SYSTEM" |
| D1AA | 20 million instructions sim-only, no output, no error (no write-up) |
| M7 DMA | `test_dma.py`: bursts, fairness, priority, interrupt precedence, CAF, halts, random episodes with two masters (about 2,000 DMA cycles agreeing) |

DEC has no CPU-level data-break MAINDEC; real DMA validation is the RK8E diagnostics and the DECX8 RK8 exerciser modules in phase 4.

**Phase 3 (I/O): in progress.** See section 6.

**Specification gaps found and fixed** (each has a regression test): A to K before and during phase 1 (see git history from `1adbb5a`); L, interrupt recognized at the end of the JMP or JMS that applies a pending field change (KM8-E §2.9: INT INHIBIT negated at TP3 of JMP/JMS); M, GTF bits 5:0 report the save field IB, bit 8 reads 0 (D1HA requires it); N, KL8E TSK skips on the interrupt condition, `INTERRUPT_ENABLE AND (keyboard flag OR teleprinter flag)` (DEC's SPI is the same operation under a later mnemonic). Also `ALU_B_SRC` was reduced to 2 bits.

## 6. Next: Phase 3

### 6.1 M8: MAINDEC-8E-D2AB (Teletype KL8 Data Control Test) on the KL8E

The write-up is `sim/test_programs/maindec-8e-d2ab/maindec-8E-d2ab-d-d.pdf` (scanned; §4 is the procedure, §5.1 normal halts, §6.1 error halts, §7 tapes and test equipment). Device selection (§4.1): deposit 0020 = 0000 (ASR33), 0021 = 0304 (keyboard 03, printer 04), 0022 = 0110 (110 baud). Each program PRGn starts at 0200 with SR = n, halts at 0236 for options (SR = 0 normal), and ends at the program end halt at 0300 (§5.1); with SR0 = 1 it halts at 0324 after each routine with the routine number in AC. Any other halt is an error (§6.1 lists them). `maindec.py` has `d2ab-prg0`, using `KL8E(baud=110)`.

The agreed approach (user decision): **test equipment around an unchanged KL8E model**, injecting inputs at instruction boundaries so the reference model's KL8E receives identical inputs (as `DmaTestMaster` does). Build:

- a **loop-back jumper**: characters completed on output are presented to keyboard input (PRG1, "EIA output to EIA input");
- a **tape reader** feeding the keyboard input at the reader's character rate (PRG2, PRG3, PRG10: the binary count pattern test tape, which PRG12 punches; §7.2 describes it);
- a **punch-to-reader loop** with a short delay (PRG5, PRG7: "very little slack between punch and reader");
- **scripted keystrokes** (PRG6 keyboard test, PRG11 printer exerciser, which ask the operator to type);
- **output capture** compared with the expected text or pattern (PRG4 printer test, PRG5, PRG12).

A live interactive terminal console comes later, sharing the same input and output interface.

Current PRG0 result (sim-only, 110 baud): routines 0 to 3 pass (routine 3 prints 200 characters); **routine 4 halts at 2607**, "printer flag set prior to 9 bit times". D2AB times characters with instruction delay loops calibrated to PDP-8/E instruction timing, and this machine's instruction timing differs from the 8/E's. This is an open item for the user (section 7); until it is resolved, run PRG0 with routines 4 and 5 deselected (SR1 = 1 selects one routine by number in SR6-11) and report it rather than changing the timing model.

### 6.2 M9: the PC8E and MAINDEC-8E-D2CA

- Write the PC8E model from `docs/07-io/10-controllers/02-pc8e-paper-tape.md` (device 01 reader: RPE, RSF, RRB, RFC; device 02 punch: PCE, PSF, PCF, PPC, PLS), its reference-model counterpart, unit tests in `sim/io/tests` (as for the KL8E), and a reader-tape input and punch capture.
- D2CA has no write-up in the archive (`sim/test_programs/maindec-8e-d2ca/` has only the tape). The user has not yet decided whether to reverse-engineer its operation from the program or attempt it best-effort; ask before starting.
- Optionally, KL8E and PC8E together with interrupts on, serviced by one interrupt routine.

### 6.3 Then phase 4

OS/8 on the RK8E (`docs/07-io/10-controllers/03-rk8e-storage.md`), with the RK8E diagnostics and the DECX8 RK8 modules as the DEC validation, including DMA.

## 7. Known Open Items

Raise these with the user; do not resolve them alone.

- **Instruction timing versus the PDP-8/E** (D2AB PRG0 routine 4, above). The user is evaluating it separately.
- **TSTEP counts** and window positions for `CW_VALID` and `WR_VALID` are not yet set; the I/O timing diagrams wait on them.
- **Datapath diagrams** that show a control-supplied input on the IF, MA, or PC source multiplexers must show the hardwired constants instead.
- **Physical image format** is undefined (`tools/rom-generation/README.md` §13).
- **Single Step inside a DMA burst** (DMA Execution §4) is not yet tested.
- **KEY CONTROL and INT INHIBIT:** on the KM8-E, console loads (KEY CONTROL) also set INT INHIBIT (Theory of Operation §2.9); check the console docs when the front panel is worked on.
- **Scan-reading helpers** used to read the MAINDEC write-ups (a CCITT G4 page decoder and an OCR-text-layer extractor) lived in a session scratchpad, not the repository. Recreate them, or ask the user whether to add them under `tools/`.
- `docs/10-front-panel` to `docs/13-implementation-plan`, `docs/appendices`, and `hardware/` are stubs.

## 8. Reference Material

- MAINDEC tapes and write-ups: `sim/test_programs/` (provenance and SHA-256 in its README); archive at deramp.com (`mfe_archive/011-Digital Equipment Corporation/01 DEC PDP-8 Family Software/03 MAINDEC Maintenance progams/`).
- DEC hardware manuals used for gaps L to N: KM8-E Memory Extension Theory of Operation, KK8-E Central Processor Theory of Operation, M8330 Timing Generator Theory of Operation, PDP-8/E Maintenance Manual Volume 1 (Sep 1973), all on deramp.com under `02 PDP-8e/`. Their scans carry an OCR text layer.
- SIMH (`PDP8/pdp8_cpu.c`, `pdp8_tt.c`) is an occasional independent cross-check of the reference model, not an authority.
