# Documentation Consistency Review (2026-11-24)

A complete review of `docs/` for design consistency across all documents, for human readability, and for correct parsing. Requested by the user after the branch's changes. Findings only: **nothing here has been applied.** Fixes are proposed after the whole review, grouped by kind. This is a branch working file, removed with `option2/`.

## 1. Scope and Method

All 106 files under `docs/` (32,342 lines), at HEAD `9598dad` plus the uncommitted changes of 2026-11-23 (F1 to F6, G1, G2, G4, G5).

1. **Mechanical sweep** (scripted, repeatable): links, anchors, link text against target headings, prose section references, document structure, section READMEs against their directories, the abbreviation dictionary, one spelling per term, stale terms, readability flags.
2. **Parsed documents**: the traps of Documentation Conventions §5 and §6, and coverage: every item a reader sees in a parsed region appears in its artifact, and nothing else does. Whether the extractors read each item correctly is checked in the ROM-generation phase.
3. **Full read** of every file, recorded in section 2: each fact against its owning document, consistency, readability (Conventions §3), and DEC citations.
4. **Design fact table** (section 5): every place each cross-cutting fact is stated, side by side.

Finding IDs: `M` mechanical, `P` parsing, `C` design consistency (two documents disagree), `A` accuracy (wrong against the design or DEC), `H` human readability, `S` structure. Each gives file and line, what is wrong, the evidence, and a proposed fix.

How sure each finding is: **Tested** (reproduced with tools), **DEC** (checked against a DEC manual), **Read** (follows from the documents' own text).

## 2. Coverage

Parsed: read by a ROM-generation extractor (taken from the artifacts' source references). Read: date read in full.

| File | Lines | Parsed | Read | Findings |
|---|---|---|---|---|
| `00-overview/00-design-principles.md` | 121 |  | 2026-11-24 | S0.2,C0.1,H0.2,H0.3 |
| `00-overview/01-system-overview.md` | 111 |  | 2026-11-24 | S0.3,H0.4,C0.2,H0.5 |
| `00-overview/97-documentation-conventions.md` | 209 |  | 2026-11-24 | H0.6 |
| `00-overview/98-signal-conventions.md` | 193 |  | 2026-11-24 | C0.3,H0.7,H0.8,H0.9 |
| `00-overview/99-Abbreviations.md` | 459 |  | 2026-11-24 | M5,M6,H0.10,H0.11 |
| `00-overview/README.md` | 29 |  | 2026-11-24 | H0.1 |
| `01-architecture/01-registers.md` | 656 |  | 2026-11-24 | A1.1-A1.6,C1.1,H1.5-H1.8 |
| `01-architecture/02-dataflow-and-bus-model.md` | 63 |  | 2026-11-24 | S1.1,H1.3,H1.4 |
| `01-architecture/README.md` | 36 |  | 2026-11-24 | H1.1,H1.2 |
| `02-isa/00-encoding-model.md` | 143 |  | 2026-11-24 | S2.1,S2.2,H2.4-H2.6 |
| `02-isa/01-group-1.md` | 56 | yes | 2026-11-24 | S2.4,A2.1,H2.7 |
| `02-isa/02-group-2.md` | 73 | yes | 2026-11-24 | S2.4 |
| `02-isa/03-group-3.md` | 37 | yes | 2026-11-24 | S2.4,A2.1 |
| `02-isa/04-iot.md` | 242 |  | 2026-11-24 | S2.3,A2.2,H2.8 |
| `02-isa/05-addressing-model.md` | 282 |  | 2026-11-24 | S2.5,A2.3,H2.9 |
| `02-isa/06-ea-generation.md` | 177 |  | 2026-11-24 | S2.6,C2.1,H2.1,H2.10 |
| `02-isa/README.md` | 48 |  | 2026-11-24 | H2.2,H2.3 |
| `03-microarchitecture/00-state-model.md` | 212 |  | 2026-11-24 | C3.1-C3.3,H3.2 |
| `03-microarchitecture/01-execution-model.md` | 328 |  | 2026-11-24 | C3.1-C3.3 |
| `03-microarchitecture/02-micro-operations.md` | 1323 | yes | 2026-11-24 | A3.1,C3.4,H3.3,P4 |
| `03-microarchitecture/03-microoperation-sequencing.md` | 223 |  | 2026-11-24 | C3.1,H3.1 |
| `03-microarchitecture/04-fetch-defer.md` | 247 | yes | 2026-11-24 | A3.2 |
| `03-microarchitecture/05-mri-execution.md` | 148 | yes | 2026-11-24 | C3.5,H3.4,M1 |
| `03-microarchitecture/06-iot-execution.md` | 444 | yes | 2026-11-24 | C3.6,H3.5,H3.6 |
| `03-microarchitecture/07-opr/00-pass-unit.md` | 96 |  | 2026-11-24 | C3.8 |
| `03-microarchitecture/07-opr/01-group1-execution.md` | 100 | yes | 2026-11-24 | C3.8,A3.5,H3.8 |
| `03-microarchitecture/07-opr/02-group2-execution.md` | 93 | yes | 2026-11-24 | A3.5 |
| `03-microarchitecture/07-opr/03-group3-execution.md` | 84 | yes | 2026-11-24 | A3.5 |
| `03-microarchitecture/07-opr/README.md` | 75 |  | 2026-11-24 | - |
| `03-microarchitecture/08-interrupt-execution.md` | 166 | yes | 2026-11-24 | A3.3 |
| `03-microarchitecture/09-console-execution.md` | 592 | yes | 2026-11-24 | C3.7,A3.4,H3.7 |
| `03-microarchitecture/10-dma-execution.md` | 111 | yes | 2026-11-24 | - |
| `03-microarchitecture/README.md` | 134 |  | 2026-11-24 | S3.1,C3.3 |
| `04-control/01-control-model.md` | 398 |  | 2026-11-24 | C4.1,C4.7,H4.1 |
| `04-control/02-control-addressing.md` | 718 |  | 2026-11-24 | C4.1,C4.7,H4.2 |
| `04-control/03-control-constraints.md` | 734 |  | 2026-11-24 | C4.1,C4.5,M1 |
| `04-control/04-control-word.md` | 497 |  | 2026-11-24 | C4.1,C4.2,M3 |
| `04-control/05-datapath-mapping.md` | 298 |  | 2026-11-24 | C4.2,H4.1,H4.6 |
| `04-control/06-invalid-conditions.md` | 259 |  | 2026-11-24 | C4.1,C4.2,C4.5,C4.6 |
| `04-control/07-direct-control-model.md` | 553 |  | 2026-11-24 | C4.1,H4.7,H4.8 |
| `04-control/08-control-store-organization.md` | 454 |  | 2026-11-24 | C4.1,C4.3,H4.3-H4.5,A4.1 |
| `04-control/10-control-input-definitions/00-index.md` | 211 | yes | 2026-11-24 | - |
| `04-control/10-control-input-definitions/01-flags.md` | 305 | yes | 2026-11-24 | H4.9 |
| `04-control/10-control-input-definitions/02-ir-derived-fields.md` | 1400 | yes | 2026-11-24 | C4.3,H4.9,H4.10,P1 |
| `04-control/10-control-input-definitions/03-derived-flags.md` | 248 | yes | 2026-11-24 | C4.4,H4.10 |
| `04-control/10-control-input-definitions/04-external-inputs.md` | 571 | yes | 2026-11-24 | C4.7,H4.8,P1 |
| `04-control/20-control-output-definitions/00-index.md` | 137 | yes | 2026-11-24 | H4.15 |
| `04-control/20-control-output-definitions/01-microarchitectural-control-signals.md` | 3183 | yes | 2026-11-24 | C4.6,C4.8,A4.3-A4.5,A4.7,H4.11-H4.13 |
| `04-control/20-control-output-definitions/02-architectural-control-signals.md` | 667 | yes | 2026-11-24 | C4.1,C4.2,C4.5,C3.6,A4.2 |
| `04-control/20-control-output-definitions/03-sequencing-control-signals.md` | 407 | yes | 2026-11-24 | C4.9,C4.10 |
| `04-control/30-direct-control-definitions/00-index.md` | 220 |  | 2026-11-24 | C4.8,C4.10 |
| `04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md` | 2217 | yes | 2026-11-24 | C4.8,A4.7,H4.14,P2,M3 |
| `04-control/30-direct-control-definitions/02-interface-and-ownership-control.md` | 998 | yes | 2026-11-24 | C4.1,A4.2,A4.6,H4.16,P2 |
| `04-control/README.md` | 58 |  | 2026-11-24 | - |
| `05-buses-and-signals/00-signal-classes.md` | 258 |  | 2026-11-24 | C5.1,C5.2,M3 |
| `05-buses-and-signals/01-class-a-buses.md` | 188 |  | 2026-11-24 | H5.3 |
| `05-buses-and-signals/02-class-b-control.md` | 253 |  | 2026-11-24 | C4.7 |
| `05-buses-and-signals/03-class-c-timing.md` | 153 |  | 2026-11-24 | - |
| `05-buses-and-signals/04-class-d-front-panel.md` | 124 |  | 2026-11-24 | - |
| `05-buses-and-signals/05-class-e-internal.md` | 167 |  | 2026-11-24 | - |
| `05-buses-and-signals/06-bus-semantics.md` | 150 |  | 2026-11-24 | - |
| `05-buses-and-signals/07-domain-boundaries.md` | 154 |  | 2026-11-24 | C5.3 |
| `05-buses-and-signals/08-ownership-matrix.md` | 202 |  | 2026-11-24 | - |
| `05-buses-and-signals/09-memory-interface.md` | 178 |  | 2026-11-24 | C5.3,H5.1,H5.2 |
| `05-buses-and-signals/10-io-interface.md` | 163 |  | 2026-11-24 | A5.1,C3.6 |
| `05-buses-and-signals/11-dma-interface.md` | 160 |  | 2026-11-24 | H5.1,C4.7 |
| `05-buses-and-signals/README.md` | 43 |  | 2026-11-24 | H5.4 |
| `06-memory/01-memory-model.md` | 151 |  | 2026-11-24 | - |
| `06-memory/02-memory-interface.md` | 190 |  | 2026-11-24 | H6.1,H6.3 |
| `06-memory/03-read-write-protocol.md` | 189 |  | 2026-11-24 | - |
| `06-memory/04-memory-timing.md` | 145 |  | 2026-11-24 | H6.2 |
| `06-memory/05-memory-field-selection.md` | 107 |  | 2026-11-24 | - |
| `06-memory/06-dma-and-console-access.md` | 167 |  | 2026-11-24 | C6.1 |
| `06-memory/07-implementation-constraints.md` | 183 |  | 2026-11-24 | - |
| `06-memory/08-invalid-conditions.md` | 110 |  | 2026-11-24 | - |
| `06-memory/README.md` | 112 |  | 2026-11-24 | C6.1 |
| `07-io/01-io-architecture.md` | 154 |  | 2026-11-24 | - |
| `07-io/02-external-iot-interface.md` | 144 |  | 2026-11-24 | - |
| `07-io/03-io-timing.md` | 227 |  | 2026-11-24 | C4.7,A7.3 |
| `07-io/04-controller-contract.md` | 310 |  | 2026-11-24 | C4.7 |
| `07-io/05-dma-interface.md` | 181 |  | 2026-11-24 | C7.1,C4.7 |
| `07-io/06-dma-arbitration.md` | 381 |  | 2026-11-24 | C4.7 |
| `07-io/07-invalid-conditions.md` | 103 |  | 2026-11-24 | H7.2 |
| `07-io/08-device-address-map.md` | 56 |  | 2026-11-24 | H7.3 |
| `07-io/10-controllers/01-kl8e-uart.md` | 691 |  | 2026-11-24 | A7.3 |
| `07-io/10-controllers/02-pc8e-paper-tape.md` | 654 |  | 2026-11-24 | A7.3,H7.5 |
| `07-io/10-controllers/03-rk8e-storage.md` | 1274 |  | 2026-11-24 | A7.1,A7.3,H7.1,H7.4 |
| `07-io/10-controllers/README.md` | 74 |  | 2026-11-24 | M3 |
| `07-io/README.md` | 85 |  | 2026-11-24 | A7.2,H7.4 |
| `08-interrupts-and-skip/01-interrupt-model.md` | 203 |  | 2026-11-24 | C8.1 |
| `08-interrupts-and-skip/02-interrupt-recognition-and-sequencing.md` | 200 |  | 2026-11-24 | C8.1,A8.1,H8.1 |
| `08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md` | 304 |  | 2026-11-24 | C8.2,A8.1,H8.2 |
| `08-interrupts-and-skip/04-interrupt-entry-and-return.md` | 323 |  | 2026-11-24 | H8.2 |
| `08-interrupts-and-skip/05-skip-model.md` | 336 |  | 2026-11-24 | A8.1 |
| `08-interrupts-and-skip/06-invalid-conditions.md` | 70 |  | 2026-11-24 | - |
| `08-interrupts-and-skip/README.md` | 96 |  | 2026-11-24 | C8.1 |
| `09-timing/01-terminology.md` | 296 |  | 2026-11-24 | M9,A9.3,H9.2 |
| `09-timing/02-timing-architecture.md` | 347 |  | 2026-11-24 | C4.7,A9.3,H9.1 |
| `09-timing/03-major-state-timing.md` | 376 | yes | 2026-11-24 | A9.1,A9.2,H9.3 |
| `09-timing/README.md` | 27 |  | 2026-11-24 | H9.2 |
| `10-front-panel/README.md` | 3 |  | 2026-11-24 | S9.1 |
| `11-backplane-and-physical/README.md` | 3 |  | 2026-11-24 | S9.1 |
| `12-verification/README.md` | 3 |  | 2026-11-24 | S9.1 |
| `13-implementation-plan/README.md` | 3 |  | 2026-11-24 | S9.1 |
| `appendices/README.md` | 3 |  | 2026-11-24 | S9.1 |
| `README.md` | 67 |  | 2026-11-24 | S0.1 |

## 3. Mechanical Sweep

Scripts (kept in the session scratch area, to be moved with the other experiments if wanted): `sweep_links.py`, `sweep_structure.py`, `sweep_terms.py`, `sweep_stale.py`. Every hit below was read; the IDs are the ones that need a change.

**Clean (Tested):**
- All 1,822 links resolve, with their anchors. No link from `docs/` into `option2/` (O1).
- Every link whose text names a section number points to a heading with that number.
- No numbered heading is out of sequence or duplicated.
- "MS changes only at TP4, or at a console TPC" (State Model §3 and §11, Execution Model, Timing Terminology §3.5) is current: in the v2 control words, `MS_LOAD = 1` occurs only at TP4 of FETCH, DEFER, EXECUTE, INTERRUPT, and DMA, and in console transactions.
- No `WR_VALID`, `/IO_WAIT`, 6/9/7/6, one-step TP, `MB_TO_IR`, `AC_MQ_SWAP`, `SKIP_TAKEN`, or `ISZ_SKIP_REQUIRED` remains. RTR, RTL, ROR, ROL hits are the OPR mnemonics, correctly in the pass unit.

**M1. Link text names documents by other titles (Read).** 18 links, and the same names in prose:
- "Fetch & Defer" (21 uses in 10 files) for *FETCH and DEFER Execution*.
- "Sequencing and Internal Control" (9 links) for *Sequencing and Internal Direct Control*.
- "MCS" (`04-control/03-control-constraints.md:23`) for *Microarchitectural Control Signals*; no other document uses the short form.
- Fix: name each document by its title. Some of these lines are in parsed documents; see section 4.

**M2. Missing Purpose sections (Read).** Documentation Conventions §2.3 requires a numbered Purpose section. Missing in: `00-overview/00-design-principles.md`, `00-overview/01-system-overview.md`, `01-architecture/02-dataflow-and-bus-model.md`, `02-isa/01-group-1.md`, `02-group-2.md`, `03-group-3.md`, `05-addressing-model.md`, `06-ea-generation.md`, and the five placeholder READMEs (10 to 13, appendices). The three ISA group documents are parsed (box diagrams), so a new section above them changes recorded line numbers only.

**M3. Heading levels that disagree with their numbers (Read).**
- `04-control/04-control-word.md:445`: "12.4 No External Control Masking" is level 4.
- `05-buses-and-signals/00-signal-classes.md:102`: "4.3.4 System Control" is level 5.
- `07-io/10-controllers/README.md:41`: "4. Interrupt-Service Documentation" is level 3.
- `04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md:1714-1775`: §4.5.5.1 to §4.5.5.4 are level 4, the same level as their parent §4.5.5. Parsed document: see section 4 before changing.

**M4. Top-level README omits five sections (Read).** `docs/README.md` §2 names 10 to 13 and appendices in plain text, without links. They are placeholders ("Status: draft"). Fix: link them, or say they are empty.

**M5. Abbreviation Dictionary gaps (Read).** Documentation Conventions §3.2 requires definition before use. Used but not defined:
- signals and buses: `DMA_ENABLE` (51 uses), `DMA_GRANT_ID` (18), `IDB` (78 bare plus code-styled), `ALU` (70), `TPC` (42), `TIMING_MODE` (4), `LOADING`, `INITIALIZE_ASSERTED`, `IA`, `CONTROL_WORD`, `HIGH_Z` and `DRIVE_HIGH`/`DRIVE_LOW` (drive-state values), `CTRL_ADDR`, `/WE`, `/OE`, `/CE`;
- general: SRAM, EEPROM, ISA, UF (once, `01-system-overview.md:35`, never defined).
- Device IOT mnemonics (KCF, DCLR, ...) are defined in their controller documents, and micro-operations in the catalog; they need no entry.
- The ten entries whose links point to a section defining several names (`MS_EFF`, `VARIANT`, ...) are correct.

**M6. TPC has two meanings (Read).** The console timing pulse (Timing Terminology §3.3; 42 uses in 18 files, including six commit texts in the direct-control artifact) and DEC's TPC IOT, Teleprinter Print Character (KL8E §22). The dictionary requires unique names and resolves collisions by renaming (§2, §13). DEC's mnemonic cannot change. User decision: the console pulse's new name.

**M7. One term, several spellings (Read).**
- PDP-8/E 39, PDP-8/e 12 (DEC writes PDP-8/E).
- auto-index 14, Autoindex 1, Auto Index 2 (and `AUTO_INDEX_REQUIRED`).
- write-back 3, Writeback 3, Write back 1.
- wired-OR 3, wired OR 2.
- power-on 33, power-up 6, for the same event.
- Single Step 30, single-step 4 (the switch).
- Group 1/2/3 175, group 1/2 2.
- Hyphenated forms used as adjectives ("major-state transition", "control-store address") are correct and not listed.

**M8. Branch vocabulary in `docs/` (Read).** `04-control/02-control-addressing.md:377`: "In v2 the OPR micro-operation bits ...". `docs/` describes one design; "v2" means nothing once v1 is removed.

**M9. Open item (Read).** `09-timing/01-terminology.md:29`: "Multiple TCLK generation options are planned ... not yet defined." Timing Architecture §5.1 now fixes TCLK at 20 MHz with `TIMING_MODE`. Check in the read whether the note is still true.

**M10. Long sentences (Read).** 13 sentences over 40 words (Documentation Conventions §3.2), listed by file in section 6.

**Read in context in section 6:** 15 uses of "EXECUTE TP4" (Conventions §3.2 reserves it for that TP), and 17 claims about DEC behavior, each checked for a citation.

## 4. Parsed Documents

The 25 parsed files, taken from the artifacts' source references, match Documentation Conventions §4 exactly. Scripts: `parse_exec.py`, `parse_refs.py`, and checks run inline (session scratch area).

**Clean (Tested):**
- **Execution cases** (FETCH and DEFER, MRI, IOT, INTERRUPT, console, DMA, OPR groups): for every case, each catalog micro-operation named on a bullet or conditional line between its heading (or its `TSn:` label) and the next is in the case, and the case holds nothing else. No heading with micro-operation bullets lacks a case. The only items not on bullets are the external-IOT cases' `AC_CLEAR`, `DB_READ_TO_AC`, `DB_WRITE_FROM_AC`, and `PC_INC`, which come from the phase-binding sentences of IOT Execution §7, as Conventions §5.2 says. The three OPR groups are recognized as pass groups (extractor INFO).
- **Micro-operation catalog:** 57 level-3 headings, 57 extracted, none extra. No Sources text contains prose.
- **Control inputs:** no derivation expression contains prose (the "sentence after the code block" trap). Every value range and encoding is binary and of the field's width. All four `EXACTLY_ONE`/`AT_MOST_ONE` constraints and the one "Mutually exclusive with" pair (`IO_READ_REQ`, `IO_WRITE_REQ`) reach the equivalence analyzer. Every bullet in a definition is taken, except the notes listed under P1.
- **Control outputs:** every bullet in a Signal Definitions entry that the extractor reads (Encoding, Used by μops, Constraints) is taken. The bullets it does not record are the descriptive Timing, Preconditions, Description, and Consumed By lists of Architectural and Sequencing Control Signals, which no stage uses.
- **Direct control:** all 67 definitions are leaf numbered headings. The 37 leaf headings that are not definitions are overviews, result and encoding tables, summaries, exclusions, and related-document lists; except as listed under P2, none has a context or assignment block.
- **Timing constraints:** the 11 lone code-span bullets of Major-State Timing are exactly the 11 extracted constraints.
- **ISA group diagrams:** one box diagram in each of the three group documents, each extracted.

**P1. Descriptive bullets inside control-input definitions (Read).** Not parsed and harmless, but they sit in parsed regions:
- `02-ir-derived-fields.md:755-756` (`IR_OPR_BSW`: "rotation behavior", "byte swap operation").
- `04-external-inputs.md:153-156` (the console-command note: "includes the RUN = 0 acceptance qualification", ...).
Check in the read whether they are still true and whether they belong in a Realization paragraph.

**P2. Constraints under direct-control headings that are not definitions (Read).** These headings carry a `Constraints:` label but no context block, so the extractor emits no definition and their constraints reach no artifact:
- `01-sequencing-and-internal-control.md:1691` §4.5.5 Final Indirect MRI Access (its four subsections §4.5.5.1 to §4.5.5.4 are definitions).
- `02-interface-and-ownership-control.md:527` §5.5 DMA Ownership Release.
Decide in the read whether the constraints are meant for the tools or for people.

**P3. Machine-read text that is stale (Read).** In Architectural Control Signals, read by the control-output extractor:
- line 443: `IOT_ACTIVE` lists "I/O wait qualification" as a consumer. `/IO_WAIT` is removed (I/O Timing §5).
- lines 347-349: `IOA` is "driven by control during EXECUTE", but §3.2 says IOA and IOP are "always; taken from IR".
These lines are descriptive, so changing them changes artifact text but not the ROM.

**P4. Micro-operation catalog order (Read).** "μop Definitions (Alphabetical)" is out of order twice: `DIF_CLEAR` before `DF_TO_AC`, and `MEM_WRITE_FROM_MB` before `MEM_WRITE_FROM_FP_SR`. Moving a definition changes recorded line numbers only.

**P5. Parsed lines that M1 would change.** "Fetch & Defer" appears as link text in parsed direct-control definitions (their `sources` keep the label) and in the three OPR group documents. Renaming changes artifact text, not the ROM; confirm in scratch.

## 5. Design Fact Table

Each cross-cutting fact, its owning document, and every place it is restated. "Agrees" was checked by reading and, where marked, against the v2 control words (Tested). Disagreements point to their finding.

| Fact | Owner | Agrees | Disagrees |
|---|---|---|---|
| TS lengths 5/8/6/5 (FETCH, non-autoindex DEFER) and 6/8/7/7 (others); TCLK 20 MHz | Timing Architecture §5.1 | Terminology §3.5, §5.2; Major-State Timing §8.2; `sim/cpu/src/pdp8_cpu/design.py` (Tested) | Terminology §2.2 note (M9, partly) |
| Two-step TP exactly where memory can be written; `/WR_PULSE` its first step | Timing Architecture §5.1, Terminology §4.3, §5.7 | Memory Timing §4; Architectural Control Signals §3.2; decision 2.1 | none |
| Console transaction 9 TSTEPs, TPC two steps | Terminology §3.3, §4.4 | Major-State Timing §8.2; External Inputs §2 ("seven setup TSTEPs") | none |
| Nothing visible changes during TP; r1 at the rising edge, r2 at the falling edge | Timing Architecture §7.6 | Micro-Operation Sequencing §6; Major-State Timing §2; Terminology §4.3 | C3.3: README §4, State Model §7, §11, Execution Model §4, Control Model §8.3, Datapath Mapping §7, 09 README §2 |
| A TS uses only state committed by the previous TP; a control input that changes in a TS settles `T_CS` before the TP | Timing Architecture §7.2, §11.4 | I/O Timing §3.3; Control Constraints §13; Micro-Operation Sequencing §6 | C3.1, C4.7: State Model §10, Execution Model §6, Micro-Operation Sequencing §9, Control Model §7, Control Addressing §5.5, External Inputs §2, §7, §8, Class B §6.5.3, DMA Interface (05) §3, Controller Contract §9.3, DMA Arbitration §5, §7, §12, §14 |
| Instruction paths: OPR and direct JMP complete in FETCH, JMP I in DEFER, others in EXECUTE | IR-Derived Fields `IR_CLASS`, `IR_NO_EXECUTE`; FETCH and DEFER §2 | Microarchitecture README §4.1; State Model §4; Sequencing and Internal Direct Control §3.1.1; `INSTR_END` (ACS §4.10); DMA Arbitration §12; Major-State Timing §9.3; Console Execution §12; Tested | none |
| Load points: PC (FETCH TP1, direct JMP TP3, JMP I DEFER TP4, JMS EXECUTE TP3), IF (FETCH TP4 / DEFER TP4 / EXECUTE TP1), II (FETCH TP1 if CIFP = 0; TP3 of JMP; EXECUTE TP1 of JMS), IR (FETCH TP2), SKIP (FETCH TP3) | FETCH and DEFER §3, §4; MRI Execution §3.5; Interrupt Enable and Inhibit §12 | Registers PC, IF, II, IR, SKIP; Skip Model §12; Tested | A9.1: Major-State Timing §3.6 applies the field at TP3 |
| JMS loads IF at EXECUTE TP1, one TP after the KM8-E | Interrupt Enable and Inhibit §12 | decision 2.2 | C3.5: MRI Execution §3.5 says "as on the PDP-8/e" |
| `MS` changes only at TP4 while running, at the TPC of START, EXAMINE, DEPOSIT, and to FETCH at power-on | State Model §5.1 | Registers MS; Execution Model §11; Terminology §3.5; Sequencing and Internal Direct Control §3.2.11, §3.2.12; Tested | C4.9, C4.10: `MS_NEXT` Value Required When, `MS_LOAD` Used for |
| External IOT: request in TS2 or TS3, accepted at that TP, transfer in the next TS; no request in TS1 or TS4; skip only in TS4; clear at TP2 to TP4, not with a read | Major-State Timing §5.2 (parsed constraints) | I/O Timing §3; External IOT Interface §3 to §7; IOT Execution §5, §7, §8; Control Constraints §12.5; Registers `IOT_TRANSFER`; External Inputs §8; Tested | none |
| `/DB_READ`, `/DB_WRITE` decoded from `IOT_TRANSFER`; `/RD` and MDB drive gated off in an IOT's EXECUTE | Architectural Control Signals §3.2 | Registers `IOT_TRANSFER`; Terminology §5.8; IR-Derived Fields `IR_IS_IOT`; Tested (step 1, G1) | C4.1 (not in Control Model §8.4; forbidden by the "no logic after the ROM" rules); C4.2 (the fields duplicate the decode) |
| Who loads `IOT_TRANSFER` | Sequencing and Internal Direct Control §5.5 (what the ROM uses) | Tested | C4.8: micro-operation catalog, MCS, Direct-Control Model §4, index §4, §5.1, own §5.4 |
| Interrupt recognized only at instruction-completion TP4, with priority over DMA, except at CAF's EXECUTE TP4 | Interrupt Recognition and Sequencing §6 | Sequencing and Internal Direct Control §3.2.5 to §3.2.7; Interrupt Invalid Conditions §2; IOT Execution §9.8; Tested | C8.1: Recognition §7, §11, Interrupt Model §8, §11, README §4, §5 omit the CAF exception |
| IOT clears of an interrupt condition, enable, or DMA request commit by TP3 (CAF excepted) | Controller Contract §9.1, §9.2 | I/O Timing §4; every controller document (section 6.7); decision 2.4 | none |
| Event wins over an IOT clear at the same TP (`/INITIALIZE`, DCLC excepted) | Controller Contract §5.1 | KL8E §9.2, §17.2; PC8E §9.2, §16.2; RK8E §12; `sim/io` KL8E (G2, Tested) | none |
| DMA: request reflects the transfer at TP2; burst-enable clears at TP3; selection released at TP4; held selection without a request dropped at TP1; TP3 with no selection clears burst-enable | DMA Arbitration §11 to §13 | Controller Contract §9.2; DMA Execution §3, §5; Major-State Timing §7; Interface and Ownership §5.5; `sim/io/dma.py` (Tested) | C7.1: DMA Interface (07) §6.5 "ends the selection at TP3" |
| CPU memory-interface drivers released in DMA | Interface and Ownership §5.2, §5.4; DMA Interface (07) §3 | DMA Execution §2; Ownership Matrix §4.1; Invalid Conditions §9.4; simulator | C4.1 (realized by the `MS_EFF` decode, unlisted); C4.5 (memory-binding rules with DMA alternatives) |
| `/INITIALIZE` sources: CAF EXECUTE TS4, a CLEAR transaction, the power-on reset | Architectural Control Signals §4.9 | Terminology §3.4; I/O Timing §2.1; Console Execution §9; IOT §3.2 | C0.3 (Signal Conventions §8.4 omits power-on); A4.6 (Interface and Ownership §8.1 "one timing state"); H7.2 (I/O Invalid Conditions §4) |
| After the power-on reset: RUN = 0, MS = FETCH, HLT_REQ = 0, `IOT_TRANSFER` = NONE; CLEAR then clears AC, L, IE; everything else undefined | Terminology §3.4 | Registers (RUN, MS, HLT_REQ, IOT_TRANSFER, MAPR); CSO §5.4.3; simulator `state.py` | A1.2 (Registers lists "Power-on reset" as a writer of AC, L, IE); C8.2 (II, CIFP "unchanged") |
| Realizations outside the control word | Control Model §8.4 | Control Constraints §1.1 rule 2; Control Addressing §3.2; Invalid Conditions §1 | C4.1 (unlisted realizations; absolute prohibitions in five documents); C4.3 (the SRQ decode) |
| IOA and IOP: IR bits presented at all times, acted on only with `IOT_ACTIVE` | Architectural Control Signals §3.2 table | I/O Architecture §7 | C3.6: ACS §4.6, IOT Execution §6, I/O Interface §3 |
| START clears AC, L, MQ, IE, II and loads FETCH; CLEAR clears AC, L, IE and initializes; EXAMINE and DEPOSIT load FETCH | Console Execution §9, §10, §3 | Registers; Sequencing and Internal Direct Control §3.2.12, §3.3.3; Tested; decision 2.3 | A3.4 (no DEC citation for START; check whether DEC's START initializes) |
| Abbreviations defined before use, one spelling, one meaning | Abbreviation Dictionary; Documentation Conventions §3.2 | | M5, M6 (TPC), M7, M1, H3.5 |

## 6. Findings by Document

### 6.0 `docs/README.md` and `00-overview`

**`README.md`**
- **S0.1** §2: sections 10 to 13 and appendices are named without links (M4). §2.1's reading order is right.

**`00-overview/README.md`**
- **H0.1** §3 "Notes": "This section is incomplete ... Key areas still under development: Front panel, Backplane and physical design". The overview documents are complete; the incomplete areas are other sections, already listed in System Overview §5 and §6. Fix: remove §3, or point to System Overview §6.

**`00-overview/00-design-principles.md`**
- **S0.2** No Purpose section (M2).
- **C0.1** §3.1: the OPR pass unit is "one exception" to ROM control. Control Model §8.4 lists six realizations outside the control word (predecode gates, the pass unit, registered `MAPR`/`MS_EFF_IS_EXECUTE`/`SKIP`, RUN-selected overlays, decoded outputs, the timing ROM). System Overview §4.1 already says it correctly. Fix: "The exceptions are the realizations of Control Model §8.4, chiefly the OPR pass unit ...".
- **H0.2** §3.1: "CONTROL = ROM[MS, TS, IR, FLAGS]" is a sketch, not the address (`MS_EFF`, TS code, variant, overlays; Control Store Organization §5). Fix: say it is the idea, and link Control Store Organization §5.
- **H0.3** §3, "Open Decisions": only the backplane remains open; the timing model entry under §3.1 should link Timing Architecture rather than "09-timing".

**`00-overview/01-system-overview.md`**
- **S0.3** No Purpose section (M2).
- **H0.4** §3.2: "UF not implemented initially": UF is never defined (M5). Fix: "Time-share support (user mode is not implemented initially)".
- **C0.2** §4.1: the control store's outputs are "Datapath control signals" and "Next Major State". The sequencer slice also gives `RUN_NEXT`, `HLT_REQ_NEXT`, `MS_LOAD`, and `/INITIALIZE` (Control Store Organization §4). Fix: list "sequencing: next major state, run and halt-request state, and `/INITIALIZE`".
- **H0.5** §2: "Front panel modeled after PDP-8/I": no front-panel document exists to confirm it (10-front-panel is a placeholder). Keep, but it is the only statement of the panel's model.

**`00-overview/97-documentation-conventions.md`**
- **A0.1** §4's parsed-document table and the artifacts agree (section 4). No finding.
- **H0.6** §3.2 asks for every abbreviation in the dictionary before use; M5 lists the gaps.

**`00-overview/98-signal-conventions.md`**
- **C0.3** §8.4 (`/INITIALIZE`) lists CAF and front-panel CLEAR as sources but not the power-on reset, which Timing Terminology §3.4 and Architectural Control Signals §3.2 and §4.9 include (decision 2.3: the reset ends with one console CLEAR transaction). Fix: add "the power-on reset asserts `/INITIALIZE` while active, and ends by running one console CLEAR transaction, at whose TPC the controllers initialize".
- **H0.7** §8.4: "at the TP ending the assertion (TP4 or TPC)". Fix: "(EXECUTE TP4 for CAF, TPC for CLEAR)", as Controller Contract §6 says.
- **H0.8** §8.3: "must settle before the TP4 sampling boundary". Aggregate `/DMA_REQ` is a sequencer-slice address input (Control Store Organization §5.6), so it must settle `T_CS` before TP4 for the control word to settle. Check against Timing Architecture §11 in the timing read; the timing budget covers it.
- **H0.9** §6 says every Class A bus has a weak pull-up; §7 says `/INT_REQ` needs a strong one (220 Ω). Consistent (`/INT_REQ` is Class B), but §7's "weak pull-up is used where a line needs only an idle level" should name the Class A buses for clarity.

**`00-overview/99-Abbreviations.md`**
- **M5, M6** (section 3): missing entries; TPC collision.
- **H0.10** §7: `TP` links to Timing Terminology §4.4 "Generation"; `TPn` links to §4. Two entries for one signal. Fix: one entry, `TP, TPn`.
- **H0.11** §3: `MFB`'s anchor text is "MFB — Memory Field Bus", unlike the other three ("Address Bus (AB)"). Cosmetic; check in the 05 read.

### 6.1 `01-architecture`

Writers were checked against the micro-operation catalog's targets, and load points against the v2 execution cases (Tested).

**`01-architecture/README.md`**
- **H1.1** §3 links read "Microarchitecture/README.md", "ISA/README.md", "Control/README.md". Fix: name the sections.
- **H1.2** §3 lists the architectural registers as PC, AC, L, MQ, IF, DF, IE; Registers §2 also lists FP_SR there. Fix: one list; FP_SR is an input, not machine state.

**`01-architecture/02-dataflow-and-bus-model.md`**
- **S1.1** No Purpose section (M2); the opening sentence links "here".
- **H1.3** §5 "Registers are the only stable sources" and "No component may rely on bus state", but §3 has IR load from MDB. Both are true (IR captures the bus at a TP, like any register), but say so: a bus may be captured, never held.
- **H1.4** §6 "TS: stabilization, TP: capture" predates the two ranks. Fix: "TS: values settle from state committed at the previous TP; TP: r1 captures at its rising edge, r2 publishes at its falling edge", linking Timing Architecture §7.6.

**`01-architecture/01-registers.md`**
- **A1.1 AC Writers** omit `DB_READ_TO_AC` (external-IOT reads), `DF_TO_AC`, `IF_TO_AC`, `IB_TO_AC` (RDF, RIF, RIB), and `AC_CLEAR` in DCA (EXECUTE TS4) and in an external IOT's clear request (TP2 to TP4). "IOT execution (GTF)" is the only IOT writer listed.
- **A1.2 "Power-on reset" as a writer** of AC, L, and IE. The reset itself does not change them; the CLEAR transaction that ends it does, at its TPC (Timing Terminology §3.4). IE's constraint line already says this. Fix: drop the "Power-on reset" writer lines; "System initialization (... front-panel CLEAR)" covers it, adding "including the CLEAR that ends the power-on reset" as IE does.
- **A1.3 EA_ADDR** "Computed during FETCH/DEFER only", "Must not change during EXECUTE", and Writers omit `PC_TO_EA_ADDR`, which EXAMINE and DEPOSIT use while halted. Writers also say "page from MA[11:7] or zero (FETCH TS3)": the load is at FETCH TP3. DEFER TP4 also loads it (`MB_TO_EA_ADDR`), which "Indirect resolution path" covers.
- **A1.4 MA Writers** list "Address formation logic (page/indirect resolution)", which does not write MA, and omit `MA_CLEAR` (INTERRUPT TP1). Consumers: "MA holds the instruction's address from FETCH TP1 until DEFER or EXECUTE TS1 reloads it": a TS does not load; "until the TP1 of DEFER or EXECUTE". In an IOT's EXECUTE, MA is not reloaded.
- **A1.5 MB** Constraints "Must not change while ... DMA transfer is in progress using MB", and Consumers "DMA logic". A DMA transfer does not use MB: the selected controller drives AB, MFB, and MDB itself, and CPU control does nothing (DMA Execution §2, DMA Interface §3). Fix: remove both. Writers should name `FP_SR_TO_MB` (DEPOSIT), which does not use the internal bus.
- **A1.6 L Writers**: "ALU link output (ADD and INC ...)". No INC loads L: `PC_INC` and `MB_INC` do not, and the OPR pass unit's IAC is listed separately. Fix: "ADD".
- **C1.1 DF, IF Constraints** "Modified only by field-control and processor-state restoration instructions" / "Modified only by field control instructions", while each entry's Writers include interrupt entry and the LOAD ADDRESS console operation. Fix: make the constraint match the Writers.
- **H1.5 CIFP** Invariants line 86 is a 47-word sentence (M10). Split.
- **H1.6 II** Constraints line 320 is a 50-word sentence (M10). Split. Its load points are correct (Tested): FETCH TP1 when CIFP = 0; FETCH TP3 of a direct JMP, DEFER TP3 of a JMP I, EXECUTE TP1 of a JMS when CIFP = 1; START.
- **H1.7 MS** Constraints state "Set to FETCH by the power-on reset" twice (lines 548 and 550), and line 552 "Initially only 0-4 are valid values 5-7 are reserved" is a run-on. Fix: one statement; "Codes 0 to 4 are used; 5 to 7 are reserved (`MS_EFF` uses 7 for HALTED)".
- **H1.8** The section order is §2 Architectural, §3 Control-Visible, §4 Internal, but the definitions in §5 are alphabetical without saying so. Fix: say "alphabetical" in §5's title, as the micro-operation catalog does.
- Checked and correct (Tested): PC's load points (FETCH TP1 increment, direct JMP at FETCH TP3, JMP I at DEFER TP4, JMS at EXECUTE TP3, interrupt entry, console); IF's (direct JMP at FETCH TP4, JMP I at DEFER TP4, JMS at EXECUTE TP1, interrupt entry, LOAD ADDRESS); IR at FETCH TP2 from MDB; SKIP at FETCH TP3; MQ only by the pass unit and START; IE, II, CIFP, DIF, DF, IB writers.

### 6.2 `02-isa`

The ISA's facts agree with each other and with the execution cases: instruction classes, group bit positions, operation order in each OPR group, SKP, SWP and `CLA SWP`, the flags word, RTF's six effects, CAF's effects and EXECUTE TP4 commit, field rules for direct, indirect, JMP, and JMS, IA as the current-page source, and auto-indexing in IF.

**Layering (Documentation Conventions §2.1: `02-isa` must not define timing states, micro-operations, or signals).**
- **S2.1** `00-encoding-model.md` §1 "Defines how IR bits map directly into control behavior for a ROM-based microarchitecture"; §2 "Control logic operates on (MS, TS, IR bits, FLAGS)"; §7 "TS defines execution ordering ... a single pass in FETCH"; §8 "occur in the same TS". These are control and timing statements. Fix: §1 "Defines the instruction formats"; move §2's control rule to Control Model (which has it) or drop it; §7 and §8 keep only the observable order of combined operations, with a link to the OPR pass unit.
- **S2.2** `00-encoding-model.md` §3 defines `IR_IS_MRI`, `IR_IS_IOT`, `IR_IS_OPR`, which are control inputs owned by IR-Derived Fields. Fix: state the classes by opcode and link IR-Derived Fields for the signals.
- **S2.3** `04-iot.md` §5 defines `IOA[5:0]` and `IOP[2:0]`, which Architectural Control Signals §4.6 and §4.7 own. Fix: reduce to "the device address and operation fields reach the controllers", with links.
- **H2.1** `06-ea-generation.md` §6 "The CPU holds it in MA from FETCH TP1" and `05-addressing-model.md` §2.2 "EA_ADDR ... becomes the final operand address before EXECUTE" name internal registers and major states. Acceptable as pointers, but they belong in FETCH and DEFER Execution; keep one sentence with a link.

**`02-isa/README.md`**
- **H2.2** The links to the addressing and EA documents are listed twice (lines 35 and 47-48), and "The effective address is represented as (EA_FIELD, EA_ADDR)" repeats the encoding model. Fix: one list.
- **H2.3** §2 excludes timing, but the group documents' sections are titled "Flag Definition and Timing" (they describe order, not timing). Fix: "Flag Definitions and Order".

**`02-isa/00-encoding-model.md`**
- **H2.4** "Status: normative" appears only here. Fix: remove, or use it everywhere.
- **H2.5** §2 "No instruction decoding into symbolic instructions is permitted", while IR-Derived Fields decodes `IR_IS_CAF`, `IR_IS_GTF`, `IR_IS_RTF`, and `IR_CLASS`. These are bit-field predicates, so the rule holds, but the wording invites the question. Fix: "Instructions are selected by IR bit fields; no symbolic opcode table is used."
- **H2.6** §6 "Group two is further divided into an AND group and an OR Group" and the sentences after it lack full stops; §6 diagram letters A, B, C are explained only in the list. Minor.

**`02-isa/01-group-1.md`, `02-group-2.md`, `03-group-3.md`** (parsed: box diagrams)
- **S2.4** No Purpose section (M2).
- **A2.1 DEC claims without citations** (Conventions §3.1): Group 1 note 3 "BSW was added in the PDP-8/E"; note 4 "DEC left this combination undocumented and its effect varied between models"; Group 3 "Prior to the PDP-8/E ... reserved for the EAE", "Beginning with the PDP-8/E MQ was included", "as DEC advises for machines without the EAE". Fix: cite the Small Computer Handbook (1973) or the KK8-E, and separate fact from inference.
- **H2.7** Group 1 §2 last sentence lacks a full stop; Group 1's bold "**NOT**" is emphasis in a parsed document (harmless here: only box drawings are read).

**`02-isa/04-iot.md`**
- **A2.2 DEC check needed** §3.2: CAF "does not modify II, CIFP, DIF, IF, DF, IB". Check against the KM8-E Theory of Operation (INITIALIZE's effect on the field registers and INT INHIBIT) and the KK8-E; cite it either way. Architectural Control Signals §4.9 repeats the list.
- **H2.8** §1 Purpose: "Defines the CPU-internal IOT instructions", but §5 covers external-device transport (see S2.3).
- Checked (Read): GTF's word and RTF's effects agree with Registers (II, CIFP, IE set by RTF) and the MAINDEC-8E-D1HA citation; CAF at EXECUTE TP4 agrees with the IOT execution case (AC, L, IE clear in TS4).

**`02-isa/05-addressing-model.md`**
- **S2.5** No Purpose section; §1 is "Scope" (M2).
- **A2.3** §7 "This matches the PDP-8/e": no citation, and the spelling (M7). Fix: cite the KM8-E Theory of Operation (the field rule) and write PDP-8/E.
- **H2.9** §14 "Indirection is a field transition mechanism": not for JMP I or JMS I, which stay in IF (§9.2). Fix: "Indirection is how AND, TAD, ISZ, and DCA reach DF".

**`02-isa/06-ea-generation.md`**
- **S2.6** No Purpose section; §1 is "Scope" (M2).
- **C2.1** §6, line 85: "an instruction at the last word of a page addresses its own page ([Addressing Model §8](...))". IA is defined in Addressing Model §4.2 (Current Page); §8 is Direct Addressing. Fix: link §4.2.
- **H2.10** The diagram `diagrams/isa/addressing-model` is referenced; whether it shows IA or PC as the page source is a diagram item (handoff §6).

### 6.3 `03-microarchitecture`

Every execution case agrees with the v2 control words and with decisions 2.1 to 2.4 (section 4, and the load points in section 6.1): FETCH, DEFER, the JMPs, the OPR pass, the Group 2 skip, MRI and IOT EXECUTE, INTERRUPT, console, and DMA. The micro-operation index matches its 57 definitions and their categories (Tested). The findings are about the cross-cutting statements and DEC citations.

**Cross-cutting model statements (State Model, Execution Model, Micro-Operation Sequencing, README)**
- **C3.1 EXT stability, three versions.** State Model §10 "EXT must be stable before TP"; Execution Model §6 "EXT must be stable prior to TP"; Micro-Operation Sequencing §9 "stable for the duration of the TS in which it is evaluated". The timing invariant (decision 2.1) is stronger: a response derives only from the controller's state committed by the previous TP and never from DB in the same TS, and it addresses the control store, so it must settle early in the TS. External Inputs §2 owns this. Fix: one sentence in each, linking External Inputs §2.
- **C3.2 "Intermediate values".** State Model §8 "No behavior may depend on intermediate (non-registered) values at TP"; State Model §12.1 and Execution Model §10 forbid "combinational intermediate values". Read literally this forbids the ALU and the OPR pass unit, whose combinational results are exactly what a TP loads. The intent is that no selection or decision depends on a result computed in the same TS. Fix: "Every value loaded at TPn is a combinational function of state committed by TP(n-1) and of external inputs; no selection depends on a result computed in TSn."
- **C3.3 When state changes.** README §4 "All state changes occur only at TP"; State Model §7 "At TP: state transitions occur", §11; Execution Model §4. With two ranks, nothing visible changes during TP: r1 captures at its rising edge, and the change becomes visible as TP ends (decision 2.1; Documentation Conventions §3.2 forbids describing a visible value as changing during TP). Micro-Operation Sequencing §6 states it correctly. Fix: in each, "commits at TP and becomes visible as TP ends", linking Sequencing §6.
- **H3.1** Micro-Operation Sequencing §4 states the `SKIP` exception twice (lines 57 and 69); §8 "MS is updated at TP4" omits the console TPC; §8.1 "EA_ADDR ... is stored in the EA register" (the register is `EA_ADDR`; EA is not a register, Registers).
- **H3.2** State Model §5.1 "MS is stable during TP1–TP3" restates the next line badly; delete.
- **S3.1** README: the "Reference Diagram" precedes the Purpose section (Conventions §2.3).

**`02-micro-operations.md`** (parsed)
- **A3.1** `PC_TO_EA_ADDR`: "Transfers the program counter into the effective address register for instruction fetch." It is used only by EXAMINE and DEPOSIT (section 6.1). Description text only; the ROM is unchanged.
- **C3.4** `IOT_TRANSFER_CAPTURE` and `IOT_TRANSFER_CLEAR` are defined here, but no execution case selects them: `IOT_TRANSFER` is loaded by direct control (Sequencing and Internal Direct Control §5.5). Two definitions of one register's loading. Plan phase 10 lists this; settle which document owns it in the 04 read.
- **H3.3** `MEM_WRITE_FROM_MB` "writes ... to the memory location specified by MA", while its expression allows `AB_SRC = PC`. `DB_READ_TO_AC` precondition "DB contains valid data for the duration of the TS": DB is valid within `DB_VALID`, which opens 100 ns into the TS (Timing Terminology §5.8).
- **P4** (section 4): alphabetical order broken twice.

**`04-fetch-defer.md`** (parsed)
- **A3.2** KM8-E claims without sections: line 112 "as on the KM8-E, which negates INT INHIBIT at TP3 of a JMP or JMS" (KM8-E §2.10.1); line 141 "as the KM8-E does" (§2.9.2, §2.10.3). Add the sections, as `option2/docs-review.md` item Q cites them. Description text, safe place.

**`05-mri-execution.md`** (parsed)
- **C3.5** JMS: "the TS3 return-address write and the following FETCH both use the new instruction field, as on the PDP-8/e." Decision 2.2 records that a JMS loads IF at EXECUTE TP1, "a documented one-TP difference" from the KM8-E, which loads IF at the TP4 before the target. The observable result (return address and target in the new field) matches; the timing does not. Fix: say both, cite the KM8-E, and link where the difference is documented (check Interrupt Enable and Inhibit §12 in the 08 read).
- **H3.4** JMS TS1 gates `DIF_TO_IF` by `IF_CHANGE_PENDING` and `CIFP_CLEAR`, `II_CLEAR` by `CIFP`; FETCH and DEFER gate all three by `CIFP`. `IF_CHANGE_PENDING` is defined as `CIFP` (Derived Flags). Fix: use `CIFP` here too; it is a parsed predicate, so confirm in scratch that the ROM is unchanged.
- **M1**: line 137 links "Fetch & Defer §3.3, §4.5" to the document without an anchor.

**`06-iot-execution.md`** (parsed)
- **C3.6 IOA and IOP.** §6: "derived directly from IR", "driven by control, not by a micro-operation", "remain stable throughout external-IOT EXECUTE". Architectural Control Signals §3.2: "always; taken from IR"; its §4.6 says "driven by control during EXECUTE" (P3). Fix: everywhere, "IOA and IOP are IR's bits, presented at all times; controllers act on them only while `IOT_ACTIVE` is asserted."
- **H3.5** §11 "Timing constraints for device interaction follow the Execution Model": they are in Major-State Timing §5.2 and I/O Timing. §10 links "IR-Derived Flags", the title of `02-ir-derived-fields.md`; other documents call it "IR-Derived Fields" (Control Model §8.4). Choose one name, and match the file name.
- **H3.6** §9.4 to §9.6 indent their `TSn:` labels by two spaces. The extractor accepts them (section 4), but they render as part of the paragraph.
- Checked (Tested): the 8 external-IOT cases from the §7 phase-binding sentences match the timing constraints (no AC clear in TS1).

**`08-interrupt-execution.md`** (parsed)
- **A3.3** Line 85: "as on the PDP-8/e, where the memory extension saves and clears the fields before the return address is stored": no citation (KM8-E §2.16 or §2.19) and the spelling (M7).

**`09-console-execution.md`** (parsed)
- **C3.7 Stale rationale, §5 "Console Address Context".** "EXAMINE and DEPOSIT update both MA and EA_ADDR ... This maintains the expected state when the CPU resumes normal operations ... This allows CONT to reuse existing execution mechanisms." Since decision 2.3, EXAMINE and DEPOSIT load FETCH as the held major state (§3), and FETCH reloads MA at TP1 and EA_ADDR at TP3, so no later execution uses the values. MA is still shown on the panel; `EA_ADDR` has no consumer. **User decision:** keep `PC_TO_EA_ADDR` (and rewrite §5 to say why), or remove it (a control-store change). Line 155 is also a run-on sentence.
- **A3.4 DEC behavior without citations.**
  - §10 START clears AC, L, MQ, IE, and II and does not assert `/INITIALIZE`. No DEC source is given. Check the PDP-8/E START key (KK8-E, maintenance manual volume 1, Small Computer Handbook) for what it clears and whether it initializes; if DEC's START initializes, this is a difference to state or a change to propose.
  - §3 "CONTINUE then starts a new instruction at PC, as on the PDP-8/E".
  - §13 "matching DEC's SING STEP, which halts at the end of every memory cycle, including data break cycles".
- **H3.7** Names: "EXAM" (§3 list, §7 text), "CONT" (§5), "EXAM and DEP" (§5), "the LOAD command" (§10) for EXAMINE, CONTINUE, DEPOSIT, LOAD ADDRESS. §12 and §13 put one-line examples in code blocks.

**`10-dma-execution.md`** (parsed): no findings. Its halt, START, CONTINUE, and CLEAR cases agree with DMA Arbitration §13 and Console Execution §13.

**`07-opr/`** (01 to 03 parsed)
- **C3.8 Who owns the pass unit.** `00-pass-unit.md` "Defines the combinational unit"; Group 1 Execution §4 also defines every stage, all three groups' selections, and the stage-E table, and is the link target for "the unit" from `OPR_PASS` (catalog), Pass Unit §3, Group 2 §4, and Group 3 §4. Fix: make the pass unit document the owner; Group 1 §4 keeps Group 1's selections and the stage-E table; links to "the unit" point to the pass unit. The parsed `OPR Pass` headings stay.
- **A3.5** KK8-E claims without sections: Group 1 line 42, Group 2 line 46, Group 3 line 42. Add sections.
- **H3.8** Group 1 §3 cites Design Principles §3.1 for the exception; cite Control Model §8.4 (see C0.1).

### 6.4 `04-control` (part 1: model documents and control inputs)

Checked (Tested): the 33 inputs the equivalence analyzer reports `unreferenced` are exactly the inputs in Control Input Index §7 (handoff §3.3). Every IR derivation agrees with the encodings in `02-isa`.

**C4.1 Logic after the control store, and decisions outside it, that Control Model §8.4 does not list.** The design has these realizations outside the control word, each documented where it is used:
- the gate holding `/RD` and the CPU's MDB drive off in an IOT's EXECUTE, `MS_EFF_IS_EXECUTE AND IR_IS_IOT` (Architectural Control Signals §3.2; IR-Derived Fields `IR_IS_IOT` Consumed By);
- the `CW_VALID` and `DB_VALID` windows gating immediate-effect outputs (Architectural Control Signals §3.2);
- the `/INT_REQ` overlay qualifier, "one gate with the SRQ decode" (Control Store Organization §6.2, §8), see C4.3;
- the shadow copy's `LOADING`-driven output enables and the address buffers (Control Store Organization §8.1);
- the console command latch and `FP_CMD` priority encoder, and the panel input register (External Inputs §2, Control Store Organization §5.2).

Control Model §8.4 lists predecode gates, the pass unit, registered `MAPR`/`MS_EFF_IS_EXECUTE`/`SKIP`, RUN-selected overlays, decoded outputs, and the timing ROM; decision 2.2 makes it the one list. Several documents then forbid exactly these, with no exception:
- Control Store Organization §7.2: "No decoder or gate follows the control store."
- Control Addressing §2: "No additional decoding or interpretation is permitted after ROM lookup"; §8.5 prohibits "secondary decision logic after ROM lookup".
- Control Word §2: the same sentence.
- Control Constraints §14.5: "post-ROM decision logic" prohibited.
- Invalid Conditions §3: "decoding or interpretation occurring after ROM lookup"; §4: "post-ROM decision logic".
- Direct-Control Model §2 "No control decision may be introduced after the control-store lookup"; §11 "must not be represented as ... suppression applied after control-word selection"; §17 "No post-control-store decision may modify a direct-control result".

Fix: add rows to Control Model §8.4 ("Output gates and windows": the IOT gate and the `CW_VALID`/`DB_VALID` windows; "Console and panel inputs": the command latch, `FP_CMD` encoder, panel input register; and the `/INT_REQ` qualifier if kept), and make each prohibition above say "except the realizations of Control Model §8.4", as Control Constraints §1.1 rule 2 and Control Addressing §3.2 already do. Changes no behavior.

**C4.2 Redundant control-word fields.** Control Word §6.3 "Signals within CONTROL_WORD must not be redundant. No duplicated control information is permitted"; Datapath Mapping §9 "No two signals may produce identical effects unless explicitly intended"; Invalid Conditions §5 forbids "two CONTROL_WORD signals producing identical effects without explicit intent". Architectural Control Signals §3.2 keeps `/DB_READ` and `/DB_WRITE` fields that "specify the same values" as the hardware decode of `IOT_TRANSFER` (G5 added the reason). The control word also carries `IOT_READ_PENDING`/`IOT_WRITE_PENDING`-dependent assignments for them. **User decision:** declare them an explicit, intended duplicate (one sentence in Control Word §6.3 citing ACS §3.2), or remove the two fields in the phase 10 schema cleanup (saves two packed bits; still six devices).

**C4.3 The SRQ decode is defined nowhere.** Control Store Organization §6.2 qualifies `/INT_REQ` in overlay group 2 "by the SRQ decode", and §8 lists "one gate with the SRQ decode". No IR-derived signal defines it (it would be `IR_IS_IOT AND IR_IOA = 000000 AND IR_IOT_OP = 011`), it is not a predecode in Control Model §8.4, and neither the control-store packer nor the simulator models it: both present `/INT_REQ` unqualified (Tested: no reference in the packer source or `sim/`). The result is the same, because no group-2 word other than SRQ's depends on `/INT_REQ`, so this is a documentation and hardware-definition gap, not a behavior difference. Fix: define the decode in IR-Derived Fields (with a Realization paragraph), list it in Control Model §8.4, and decide whether the packer should verify it.

**C4.4 `IF_CHANGE_PENDING` duplicates `CIFP`.** Derived Flags defines `IF_CHANGE_PENDING = CIFP`. Control Model §6.3 and Control Constraints §7 require FLAGS to be "minimal and non-redundant". Overlay group 3 carries both (`DP_OVL[2]` and `DP_OVL[0]`), and JMS TS1 gates `DIF_TO_IF` by one and `CIFP_CLEAR`, `II_CLEAR` by the other (H3.4). **User decision:** remove `IF_CHANGE_PENDING` and use `CIFP` (changes the overlay assignment and the packed images, not behavior; scratch-tested before proposal), or state why it is kept.

**C4.5 Memory-binding rules that describe the CPU driving memory in DMA.** Control Constraints §12.3 "/RD = 0 without MEM_READ_TO_MB or MS = DMA", §12.4 "/WR + MDB_SRC = DMA + MS = DMA"; Invalid Conditions §7 "`/RD` asserted without `MEM_READ_TO_MB` (and `MS ≠ DMA`)", "`/WR` ... or DMA write". In DMA the CPU's `/RD`, `/WR`, and MDB drivers are released and the controller drives them (DMA Execution §2, Invalid Conditions §9.4). `MDB_SRC` has no DMA encoding (check in the MCS read). Fix: say the CPU asserts neither in DMA; drop the DMA alternatives.

**C4.6 A select field with its enable off.** Invalid Conditions §6 forbids "`IDB_SRC` selecting a source while `IDB_DRIVE` is deasserted". Control Word §5.6 and §8.2 allow any encoding in a select field whose operation is not enabled, and the packer shares bits on that basis. Fix: delete the second half of that bullet.

**C4.7 EXT settling, stated weakly.** External Inputs §2 (the owner): "changes only as a TP ends and settles before the next TP". `/INT_REQ`: "must settle ... before the TP at which control samples it"; `/DMA_REQ`: "setup and hold requirements before CPU control samples it at TP4"; responses: "stable before and through the TP"; Control Model §7 and Control Addressing §5.5 "stable before TP" / "during control evaluation". These inputs address the control store, so each must settle early enough for the control word to settle within `T_CS` (Timing Architecture §11), not merely before the TP; nothing "samples" `/DMA_REQ` at TP4. Fix: External Inputs §2 states the real requirement and links Timing Architecture §11; the others link it (with C3.1).

**Other findings**
- **H4.1** Control Model §8.3 and Datapath Mapping §7 "At TP(n): all state updates occur simultaneously" (see C3.3: two ranks).
- **H4.2** Control Addressing §5.3 "In v2 the OPR micro-operation bits ..." (M8).
- **H4.3** Control Store Organization §1.1 calls `MS_EFF_IS_EXECUTE` "a derived signal"; §5.1 registers it (decision 11a). Fix: "a registered decode".
- **H4.4** Control Store Organization §10 "Open Items": the timing item is resolved (TSTEP counts set in Timing Architecture §5.1); the diagram item belongs to the diagram list; the group-assignment item is a status note. Fix: retitle "Notes" or move.
- **A4.1** Control Store Organization §8.1 "DEC precedent: the KL10 processor loaded its microcode into control RAM from its front-end PDP-11": no citation.
- **H4.5** Control Store Organization §5.4.3 cites Major State Timing §9.1 ("DEFER follows an indirect MRI") for "IR is loaded only at FETCH TP2". Check the target in the 09 read.
- **H4.6** Datapath Mapping §12.2 lists "`/DMA_GRANT` asserted" among the DMA control word's defaults; it is decoded from `MS_EFF`, not a control-word field (Control Word §12.3). It also omits the released CPU drivers.
- **H4.7** Direct-Control Model §4's example (`IOT_TRANSFER_CLEAR` selecting `IOT_TRANSFER_LOAD = 1`, direct control supplying `IOT_TRANSFER_VAL = NONE`) does not happen: no case selects `IOT_TRANSFER_CLEAR`; direct control assigns both fields (see C3.4). Choose another example after C3.4 is settled.
- **H4.8** Link text naming documents by other titles: "Execution Architecture" (Direct-Control Model §18, for Execution Model), "Architectural Registers" (for Register Model Specification), "IR Derived Fields", "Primitive Flag Definitions", "Console Microarchitecture" (External Inputs, for Console Execution). See M1.
- **H4.9** Primitive Flags: `EAI` "Consumed By" lists `MB_INC` and `MEM_WRITE_FROM_MB`, and `MBZ` lists `PC_INC`; both reach them only through derived flags (Control Input Index §7). `IR_INDIRECT` lists only `MB_TO_EA_ADDR`, omitting FETCH TS4 sequencing and `AUTO_INDEX_REQUIRED`; `IR_IS_MRI` lists micro-operations rather than the MRI execution contexts. Plan phase 10 ("stale consumers") covers these; listed here so they are not lost.
- **H4.10** Derived Flags §1 names files "02-ir_derived_fields.md" and "01-flags.md" in plain text. `02-ir-derived-fields.md` is titled "IR-Derived Flags", and its §2.1 "IR Derived Fields" describes the class flags (H3.5).
- **P1** (section 4): `IR_OPR_BSW` descriptive bullets; `FP_CLEAR` "Accepted Event" bullets.

### 6.4 `04-control` (part 2: control outputs and direct control)

**C4.1, continued: DMA driver release.** Interface and Ownership §5.2 and §5.4 require the CPU's MFB, AB, MDB, `/RD`, and `/WR` drivers to be `HIGH_Z` in DMA. No control-word field is a driver enable (Control Store Organization §4.2 lists every field), so the release must come from the `MS_EFF` decode (`/DMA_GRANT`), outside the control store. Direct-Control Model §11 says a release must not be "an inferred consequence of a major state" or "suppression applied after control-word selection". Add the driver-enable decode to the C4.1 list, and say in Interface and Ownership §5.2 how the drive state is produced.

**C4.6, continued: "select fields always hold valid encodings".** Microarchitectural Control Signals §3.2 and §6.3 ("Select signals must always contain a valid encoding"), §6.1, §9.8, §10.2, §10.3, §10.10, and §12.8 ("No reserved encodings are used") contradict its own §2.7, §3.5, §6.12, and §12.2, and Control Word §5.6: a field whose Value Required When is false may hold any encoding, including a reserved one, and the packed images do this wherever bits are shared (for example `DF_SRC` reads 7, reserved, in a word that sets `AC_SRC = 7` without loading DF). Fix: qualify each rule with "wherever its Value Required When condition holds".

**C4.8 Who loads `IOT_TRANSFER` (extends C3.4).** Three descriptions:
- Direct control assigns both `IOT_TRANSFER_LOAD` and `IOT_TRANSFER_VAL` (Sequencing and Internal Direct Control §5.5.1 to §5.5.5); the symbolic control words take both from there (Tested: assignment sources `01:5.5.x`).
- The micro-operation catalog defines `IOT_TRANSFER_CAPTURE` and `IOT_TRANSFER_CLEAR`, and Microarchitectural Control Signals lists them under `IOT_TRANSFER_LOAD` and `IOT_TRANSFER_VAL`; no execution case selects them.
- Sequencing and Internal Direct Control §5.4, Direct-Control Definitions index §4, and Direct-Control Model §4 say `IOT_TRANSFER_VAL = NONE` is owned by the `IOT_TRANSFER_CLEAR` micro-operation and "must not be duplicated as direct-control bindings"; §5.5.3 does exactly that. The index §5.1 also says register load enables are micro-operation-owned.
Fix (recommended, no ROM change): keep direct control, which is what the ROM uses; remove the two micro-operations (plan phase 10 "unselected micro-operations") and their Used-by lines; correct §5.4, the index §4 and §5.1, and Direct-Control Model §4.

**C4.9 `MS_NEXT` "Value Required When: TS=4" omits the console loads.** Sequencing Control Signals §4.1 (parsed). START, EXAMINE, and DEPOSIT set `MS_NEXT = FETCH` with `MS_LOAD = 1` at TPC, while TS is held at TS1 (Sequencing and Internal Direct Control §3.2.12, §3.3.3; decision 2.3). The packer verifies a field only where its condition holds (Control Store Organization §9), so those three console words' `MS_NEXT` may be unverified. The value is right today because the sequencer slice shares no bits. Fix: `Value Required When: MS_LOAD=1`. Check the packer's verification in the ROM-generation phase; the change alters the schema, not the images (scratch-test).

**C4.10 MS_LOAD's console uses are incomplete.** Sequencing Control Signals §4.4 "Used for" lists TP4 transitions and START; EXAMINE and DEPOSIT also load MS (decision 2.3). Direct-Control Definitions index §3.1 links `MS_LOAD` to §3.2.11 and §3.3.3, but not §3.2.12.

**A4.2 Stale `/IO_WAIT` references (P3).** Architectural Control Signals §4.8: `IOT_ACTIVE` "qualifies IOA, IOP, controller responses, and I/O wait behavior", and lists "I/O wait qualification" under Consumed By; Interface and Ownership §7.2: "a read, write, skip, clear-AC, or wait response". `/IO_WAIT` is removed (I/O Timing §5). Descriptive text; artifact text changes, not the ROM.

**A4.3 `MDB_SRC` encodings.** "0 → Memory, 1 → MB, 2 → FP_SR, 3 → DMA". Code 0 means the CPU does not drive MDB (memory or a DMA controller may); code 3 ("DMA") is never used by any control word (Tested), and in DMA the CPU's MDB driver is released (Interface and Ownership §5.2). Fix: name code 0 "none (CPU does not drive MDB)" and make 3 reserved, in the phase 10 reserved-values cleanup. Control Constraints §12.3 and §12.4 use "MDB_SRC = Memory" and "MDB_SRC = DMA" (C4.5).

**A4.4 Domain rules that DEPOSIT breaks.** Microarchitectural Control Signals §7.11 and §8.3 allow only "MB → MDB" for a memory write. DEPOSIT drives MDB from FP_SR (`MDB_SRC = FP_SR`, `MEM_WRITE_FROM_FP_SR`). Fix: add FP_SR → MDB (console DEPOSIT) to both.

**A4.5 Wrong example.** Microarchitectural Control Signals §7.4 shows `MA_INPUT` as "IDB path" or zero; MA's sources are PC, EA_ADDR, and zero (`MA_SRC`), with no IDB path. Use a register that does have an IDB path (MB or AC).

**A4.6 `/INITIALIZE` duration.** Interface and Ownership §8.1: "is asserted for one timing state". CLEAR asserts it for the whole console transaction, and the power-on reset while active (Architectural Control Signals §4.9). Fix: "for EXECUTE TS4 of CAF, for a CLEAR transaction, or during the power-on reset".

**A4.7 DEC claims without citations.** Microarchitectural Control Signals §7.3.1 "This matches the PDP-8/e, where a carry out of AC bit 0 complements L"; Sequencing and Internal Direct Control §3.2.5 "on the PDP-8/e CAF's INITIALIZE clears the interrupt logic before TP4"; §4.5.5 "This matches the PDP-8/e, where the data field applies only to AND, TAD, ISZ, and DCA operands". (Its §3.2.12 cites the maintenance manual §3.8.2 correctly; Console Execution §3 can cite the same, see A3.4.)

**H4.11 Signal Definitions entries with empty or dangling lists.** `AB_SRC`, `DB_INPUT`, `MDB_INPUT`, `IF_DF_COMBINED` have an empty "Used by μops:"; `MDB_INPUT` and `IF_DF_COMBINED` say "Value Required When: Any micro-operation listed below is selected" with none listed (`IF_DF_TO_IB` uses `IF_DF_COMBINED`). `MFB_SRC` has no Used-by label at all. Direct control owns `AB_SRC` and `MFB_SRC`, so say so. Plan phase 10 "stale descriptions" may cover the generated side.
**H4.12** Microarchitectural Control Signals §7.5 "At transfer phase (TP)": TP is the timing pulse.
**H4.13** `MFB_SRC` "Value Required When: Always" while "During MS = DMA ... MFB_SRC has no effect"; its constraint says "Console EXAM/DEP" (H3.7).
**H4.14** Sequencing and Internal Direct Control §3.3.7 "and, for a direct JMP or an OPR, then for a JMP I:" is garbled; §3.4.6 "EXECUTE Single Step completion" should be "Single Step completion at instruction completion" (FETCH or DEFER too); §3.2.6 "`/DMA_REQ` must be established before TS4" against §3.2.9 "must settle before TP4" (C4.7).
**H4.15** Control Output Index line 112 has a space inside the link target (`...initialize )`). It renders, but the link checker's pattern skips it, so it is unchecked.
**H4.16** Interface and Ownership §5.2 and §5.4 repeat the same DMA drive states under two headings.
**P2** (section 4): the `Constraints:` of §4.5.5 and Interface §5.5 are not extracted.

### 6.5 `05-buses-and-signals`

These documents classify signals and define participation; they agree with the control and I/O documents except as listed.

- **C5.1 Signal Classes §4.3 lists only part of Class B.** It names `/RD`, `/WR`, `/INT_REQ`, `/DMA_REQ`, `/DMA_GRANT`, `MS[2:0]`, `INSTR_END`, `/INITIALIZE`. Class B §6.4 and §6.5 also include the external-IOT interface (`IOT_ACTIVE`, `IOA`, `IOP`, `/DB_READ`, `/DB_WRITE`, the four `IO_*_REQ` responses) and the DMA arbitration signals (`/DMA_REQ[14:0]`, `DMA_ENABLE`, `DMA_GRANT_ID[3:0]`). Fix: Signal Classes §4.3 lists them all, or points to Class B §6.
- **C5.2 Signal Classes §5.3 against Class C §3.** Signal Classes lists TS and TP as the distributed timing signals; Class C also distributes `/WR_PULSE` (to memory) and keeps `CW_VALID` and `DB_VALID` local. Fix: match Class C.
- **C5.3 MFB has no transport domain.** Domain Boundaries §2 "Each transport signal belongs to exactly one domain", but §3 defines AB, MDB, DB, and IDB, and MFB is in none. Memory Interface §2 and §5 likewise list AB and MDB as the participants while §3 and §6 use MFB. Fix: put MFB in the Address Domain ("AB and MFB"), and add it to Memory Interface §2 and §5.
- **A5.1 "I/O wait behavior".** I/O Interface §6: "I/O wait behavior is defined in I/O Timing". I/O Timing §5 now says the timing is fixed and "there is no wait signal". Fix: delete the bullet, or say "The external-IOT timing is fixed; there is no wait signal (I/O Timing §5)".
- **H5.1 Two documents titled "DMA Interface"** (`05-buses-and-signals/11-dma-interface.md`, `07-io/05-dma-interface.md`) and two titled "Memory Interface" (`05-buses-and-signals/09-memory-interface.md`, `06-memory/02-memory-interface.md`). Links then need extra words to tell them apart, and one does it as "DMA Interface Timing" (DMA Interface §1), a title neither has. Fix: retitle the 05 pair "DMA Signal Interface" and "Memory Signal Interface" (or similar), and link by title.
- **C3.6, C4.7** recur here: I/O Interface §3 "IOA and IOP ... remain stable throughout external-IOT EXECUTE"; Class B §6.5.3 and DMA Interface §3 "settle before CPU control samples it at TP4".
- **H5.2** Memory Interface §2 omits `/WR_PULSE`, which bounds every write (Timing Terminology §5.7). Add it, linking Memory Timing.
- **H5.3** Class A §4.4 heading "MFB — Memory Field Bus" differs from the other three ("Address Bus (AB)"); its §4.4.3 starts with a stray space. Signal Classes §4.3.4 is level 5 (M3).
- **H5.4** README §2 excludes control semantics "([../04-control/README.md](...))", showing a path as link text; name the sections.

### 6.6 `06-memory`

The memory documents agree with each other and with decision 2.1 (write enable = `/WR` AND `/WR_PULSE`, the first step of a two-step TP; address, data, and `/WR` stable from before TP to its end).

- **C6.1 `/WR_PULSE` missing from two interface lists.** Memory Interface §2 lists it as a memory input; the section README §4 and DMA and Console Access §2 list MFB, AB, MDB, `/RD`, `/WR` only. Fix: add it.
- **H6.1** Memory Interface §4: "memory captures the value at the commit TP". The write happens during `/WR_PULSE`, the first step of that TP (Memory Timing §4). Fix: "during `/WR_PULSE`, within the commit TP".
- **H6.2** Memory Timing §10 gives device limits (address access at most 35 ns, write pulse 15 ns, ...). `option2/experiments/timing_budget.py` reports a main-memory access limit of 168.7 ns (CONSOLE TS1). These may measure different things (a device requirement chosen with margin, against the slack the timing allows); check against Timing Architecture §11.4 in the 09 read and state which governs. No margin is quoted here without running the budget (handoff §4).
- **H6.3** The memory timing diagram (`diagrams/memory/memory_timing`) is referenced by Memory Interface §4; handoff §6 notes its source is WaveDrom text with a `.png` name (diagram item).

### 6.7 `07-io`

Checked against decision 2.4 (Read): an IOT that clears an interrupt condition, enable, or DMA request commits by TP3 in every controller (KL8E KCF/KCC at TP2, KRB/KIE/TCF/TLS at TP3; PC8E RPE/PCE at TP2, RRB/RFC/PCF/PLS at TP3; RK8E DCLR/DLDC at TP3); a device event wins over an IOT clear at the same TP, with `/INITIALIZE` and DCLC as the exceptions; a DMA request reflects the transfer at TP2; a held selection with no request drops at TP1; TP3 with no selection clears burst-enable. RK8E: transfer at the Current Address then increment (§9, §26.6), DCLR clears status first (§18.2), seeks set Done at start and leave the controller free (§15.1). The RK8E Command and Status bit assignments match DEC's, numbered from the most significant bit (Read: against SIMH `pdp8_rk.c` bit masks, secondary). The KL8E model in `sim/io` matches the KL8E document's request and commit points (step 1).

- **A7.1 Literal placeholder.** RK8E §18.2, line 344: "whose DCLS and DCLD both clear it ({H}, p. 6-72)". `{H}` should be "PDP-8/E Small Computer Handbook (1973)".
- **A7.2 "wait behavior" in scope.** README §2 "IOT timing and wait behavior"; I/O Timing §5 says there is no wait signal. Fix: "IOT timing".
- **C7.1 When a burst's selection ends.** DMA Interface §6.5: "the arbiter ends the selection at TP3". DMA Arbitration §12 and §13: burst-enable clears at DMA TP3, and "the active controller selection terminates at DMA TP4" (`DMA_GRANT_ID` ← 15 at TP4), which the simulator does. Fix: "the arbiter clears burst-enable at TP3 and releases the selection at TP4".
- **C4.7, continued.** I/O Timing §3.3 states the requirement correctly: "A response must be stable at least `T_CS` before the TP that accepts it". Its own §6 ("stable before the TP"), Controller Contract §9.3 ("settle before the TP at which CPU control samples it"), DMA Arbitration §5, §7, §12, §14 ("settle before TP4"), and DMA Interface §6.5 say less. Make I/O Timing §3.3 the reference for the controller side.
- **A7.3 DEC claims without citations.** KL8E §8 "as on the PDP-8/e, where INITIALIZE sets the KL8-E interrupt enable"; PC8E §8 the same for the PC8-E; I/O Timing §5 "The PDP-8/E's NOT LAST TRANSFER, which stops the timing until the device's BUS STROBE"; RK8E §30.3 "The standard bootstrap ... waits in a `JMP .` at `0031`" (cite the bootstrap listing). The others in this directory are cited (maintenance manual §3.41.2, §3.42; Small Computer Handbook pp. 6-72 to 6-74).
- **H7.1** RK8E §26.9: on grant loss the controller "deasserts /RD" and "deasserts /WR"; DMA Interface §3 has it release them, which is what lets the CPU drive them next. Fix: "releases".
- **H7.2** I/O Invalid Conditions §2 includes "more than one TSTEP increment on one TCLK rising edge", a timing-generator condition, not an I/O one; §4's "/INITIALIZE remaining asserted beyond its assigned interval" omits the power-on reset.
- **H7.3** Device Address Map §3 is titled "P1 Address Assignments"; "P1" is not defined.
- **H7.4** README §4 link text "KL8E Equivalent Serial Controller(Teletype keyboard/printer alternative)" lacks a space; the controller titles are "KL8E-Compatible ...". RK8E line 718 has a stray `----`.
- **H7.5** PC8E §15 (RRB RFC): the controller preserves the old reader buffer through TP4 while §9.2 lets a character become visible at the same TP3 as the clear. A new character cannot arrive at the TP that requests it, so the two do not conflict, but say so in §15.

### 6.8 `08-interrupts-and-skip`

These documents agree with the execution cases and with each other on recognition at instruction-completion TP4, precedence over DMA, the ION delay, the CIF/RMF/RTF inhibit, the deferred-field TPs (Interrupt Enable and Inhibit §12, which documents the one-TP JMS difference with KM8-E citations), interrupt entry, and every skip source.

- **C8.1 The CAF exception is missing from the general precedence rule.** Interrupt Recognition and Sequencing §6 states it ("except at the EXECUTE TP4 of CAF") and Sequencing and Internal Direct Control §3.2.5 to §3.2.7 implement it (CAF with a valid request goes to DMA or FETCH). Statements of the rule without it: Recognition §7 ("`MS_NEXT` must select `INTERRUPT`") and §11 ("DMA is selected only when no valid interrupt request exists"); Interrupt Model §8 and §11; README §4 and §5. Documentation Conventions §3.1: state exceptions where the general rule is stated. Fix: add "(except CAF, section 6)" to each.
- **C8.2 Power-on and II, CIFP.** Interrupt Enable and Inhibit §8: "On system initialization (CAF, front-panel CLEAR, or power-on reset): IE is cleared, II is unchanged, CIFP is unchanged". After the power-on reset, II and CIFP are undefined (Timing Terminology §3.4: every register the reset does not set is undefined), so "unchanged" does not apply. Fix: "after the power-on reset, II and CIFP are undefined until LOAD ADDRESS clears CIFP and START clears II" (the operator's normal sequence), or state what is required.
- **A8.1 DEC claims without citations.** Recognition §6: "This matches the PDP-8/e, where CAF asserts INITIALIZE at TP3 and it clears the interrupt-enable, delay, and request-synchronizing flip-flops before TP4"; Interrupt Enable and Inhibit §11.1: "RTF sets IE regardless of AC[7], matching the defined PDP-8/E behavior"; Skip Model §12: "The KK8-E's SKIP flip-flop is set at TP3 in the same way" (no section). Cite the KK8-E or the maintenance manual.
- **C3.5 resolved here:** Interrupt Enable and Inhibit §12 states the JMS difference correctly; MRI Execution §3.5 should link it rather than say "as on the PDP-8/e".
- **H8.1** Recognition §3 "subject to the applicable setup and hold requirements" (C4.7: say what they are, or link I/O Timing §3.3 and Timing Architecture §11).
- **H8.2** Interrupt Enable and Inhibit §13 links "Fetch and Defer", §12 and Entry and Return §14 and §15 "Fetch & Defer" (M1).

### 6.9 `09-timing` and the placeholder sections

The timing documents agree with decision 2.1 throughout: the two ranks (Timing Architecture §7.6), one TP flip-flop (Terminology §4.4), TS as a synchronous enable, 20 MHz TCLK, the lengths 5/8/6/5 and 6/8/7/7, the console transaction of 9 TSTEPs with a two-step TPC, the two-step TPs exactly where memory can be written, `/WR_PULSE` as the first step, `DB_VALID` at 100 ns, `CW_VALID` at 150 ns. The state invariants of Major-State Timing §9 match the control words (step 1: `IOT_TRANSFER` is `NONE` outside external-IOT TS3 and TS4). H4.5 needs no change: §9.1 does state that IR loads only at FETCH TP2.

- **A9.1 Direct JMP field application at TP3.** Major-State Timing §3.6 (TP3): "Direct JMP: PC loaded with the formed address; a pending instruction field is applied". The field is applied at FETCH TP4 (`DIF_TO_IF`, `CIFP_CLEAR` in TS4); TP3 clears `II` (FETCH and DEFER §3.4, Interrupt Enable and Inhibit §12, decision 2.2). §3.8 (TP4) omits it. Fix: TP3 "PC loaded; with a field change pending, II clears"; TP4 "a pending instruction field is applied". This document is parsed for its constraints only; the lines are prose.
- **A9.2 INTERRUPT summary.** Major-State Timing §6: "TS1–TS4: Save PC, Load vector". There is no vector: PC is set to 0001 (Interrupt Execution §4.4, Interrupt Entry and Return §5). It also omits the field save and clear. Fix: list the four TPs as Interrupt Execution does, or link it.
- **M9, resolved.** Terminology §2.2's note ("Multiple TCLK generation options are planned ... not yet defined") is half current: TCLK is 20 MHz (Timing Architecture §5.1); how it is derived from MCLK is still open. Fix: say both.
- **C4.7, the reference.** Timing Architecture §11.4: "A control input that changes during a TS, such as a controller response, must be stable at least `T_CS` before the TP that accepts it." External Inputs §2 should state this and link here.
- **A9.3 DEC claims without sections.** Timing Architecture §5.1 "(KK8-E; M8330)", "a directly addressed memory-reference instruction takes 2.6 µs, as on the PDP-8/E"; Terminology §5.2 "following DEC's fast- and slow-cycle design". Cite the sections (Terminology §3.4 and §3.5 already cite the maintenance manual §3.16 and the M8330).
- **H9.1** Timing Architecture §2: the overview diagram's alt text is "alt text".
- **H9.2** README §2 "Core Rules" (TS setup, TP transitions, "All state changes occur on TP") is the pre-two-rank wording (C3.3); §3 "Excludes: Behavior ([../04-control/README.md](...))" shows a path as link text. Terminology §3.5 links Control Store Organization §8 (Device Summary) for the shadow copy; §8.1 is the target.
- **H9.3** Major-State Timing §2 "All state changes occur exclusively at TP: captured at its leading edge, visible as it ends" is the correct form; use it in the places C3.3 lists.
- **H6.2, continued.** Timing Architecture §11.4 sets budget rules and physical limits but no memory access time; Memory Timing §10's device limits (35 ns access, ...) have no stated source. Say where they come from (the timing budget tool's report, once it moves out of `option2/`, section 3.6 of the handoff).

**`10-front-panel`, `11-backplane-and-physical`, `12-verification`, `13-implementation-plan`, `appendices`**
- **S9.1** Each is a title and "Status: draft" (M2, M4). Fix: a one-paragraph Purpose saying what the section will hold, and that it is not yet written; or remove them and the README entries until there is content. Console Execution §1 already says Front Panel "is not yet written".

## 7. Proposed Fix Batches

Nothing above has been applied. Proposed order, each batch tested in a scratch copy (handoff §5.3) with every artifact's content compared; batches touching parsed documents also confirm the ROM images are byte-identical, or explain every difference.

**B1. User decisions (needed before the batches they affect).** All applied 2026-11-24 in four steps (1: M6, C4.8, C4.3, C4.2 note; 2a: C4.4; 2b: C3.7; 2c: A3.4), each tested in scratch and promoted by the user. Found on the way: Control Store Organization §7.2 listed the wrong shared-bit groups (fixed in 2b); A2.4 (GTF bit 8, for B4).
- C4.2: **Decided 2026-11-24: remove in phase 10** (option A). Interim: Control Word §6.3 notes the known duplicate; plan phase 10 gets the removal (schema, ACS §4.3, §4.4 become decoded signals listed in Control Model §8.4; simulator checks the micro-operations against the decode).
- C4.4: **Decided 2026-11-24: remove `IF_CHANGE_PENDING`, use `CIFP`** (option A). Checked: no interrupt document or input uses it; interrupt eligibility reads `IE`, `II`, `CIFP` directly. Apply now (step 2).
- C3.7: **Decided 2026-11-24: remove `PC_TO_EA_ADDR`** (micro-operation, two console cases, MCS "Used by" entries); rewrite Console Execution §5 (MA loaded for the panel; `EA_ADDR` untouched, FETCH reloads it). Decision 2.3 kept (EXAMINE and DEPOSIT load FETCH): PC still moves, so a halted DEFER or EXECUTE cannot resume. Verify the §3.8.2 citation when volume 1 is available.
- M6: **Decided 2026-11-24: rename TPC to `TP_FP`** (matches the `FP_` console names; TP first marks it as the commit pulse, not a panel input). Use "the console TP" in prose where it reads better, `TP_FP` in tables, expressions, and rules. Define in Timing Terminology §3.3 and §4.4; add to the Abbreviation Dictionary. Regenerate v2 artifacts; images must be byte-identical. KL8E TPC (DEC IOT) unchanged.
- C4.3: **Decided 2026-11-24: define `IR_IS_SRQ`** in IR-Derived Fields (with Realization), list it in Control Model §8.4; ROM phase: packer checks only SRQ reads `/INT_REQ` in group 2; simulator phase: model the qualifier.
- C4.8: **Decided 2026-11-24: direct control owns `IOT_TRANSFER` loading**; remove `IOT_TRANSFER_CAPTURE`, `IOT_TRANSFER_CLEAR` and their Used-by lines; correct Sequencing and Internal Direct Control §5.4, Direct-Control Definitions index §4, §5.1, Direct-Control Model §4 (new example). No ROM change.
- A3.4: **Decided 2026-11-24: START = CLEAR then CONT in one key** (behavior change): asserts `/INITIALIZE` for the transaction; clears AC, L, MQ, IE, II; runs from FETCH at PC. Cite Small Computer Handbook (1973) pp. 2-12 item 5 and 3-2 (CLEAR, CONT). Clearing MQ is our choice (the 8/E CLEAR does not list MQ); state it as such. No 8/I claim. CLEAR: no change (decided 2026-11-24). The 8/E CLEAR clears "all interrupt system flip-flops" (handbook p. 3-2), but II has no effect while IE = 0 and every IE set (ION, RTF) also sets II; GTF does not report II. State this in Console Execution §9 with the citation.

**B2. Design consistency, no behavior change.** Applied 2026-11-24 (C3.4, C4.3, C4.8 were settled in B1); images byte-identical. C4.9 left open for the ROM phase: the packer's check count did not change with `MS_NEXT` required when `MS_LOAD=1`. C0.1 to C0.3, C1.1, C2.1, C3.1 to C3.6, C3.8, C4.1, C4.5, C4.6, C4.7, C4.9 (schema only), C4.10, C5.1 to C5.3, C6.1, C7.1, C8.1, C8.2, A9.1, A9.2.

**B3. Accuracy.** Applied 2026-11-24; images byte-identical. A1.1 to A1.6, A3.1, A4.2 to A4.6, A5.1, A7.1, A7.2, H4.11.

**B4. DEC citations.** Applied 2026-11-24 (sources in section 8); images byte-identical. A2.4 (new: ISA §3.1 says GTF bit 8 = 0 "as on the PDP-8/E"; handbook p. 4-8 Table 4-1 gives AC3 = interrupt inhibit flip-flop. Reword: differs from the handbook; MAINDEC-8E-D1HA requires it), A2.1, A2.2, A2.3, A3.2, A3.3, A3.5, A4.1, A4.7, A7.3, A8.1, A9.3. Needs the DEC sources (deramp.com scans; the user's Small Computer Handbook); each claim is either cited or reworded as inference.

**B5. Terms and dictionary.** Applied 2026-11-24. M1, M5, M7, M8, M9, H3.5, H4.8, H5.1, H0.10.

**B6. Structure.** Applied 2026-11-24 (placeholder sections removed, user decision). M2 (Purpose sections; the ISA group documents are parsed, so line references move), M3, M4, S-items, S9.1.

**B7. Parsing.** Applied 2026-11-24. P1 to P5.

**B8. Readability.** Applied 2026-11-24. Not done: H4.16 (parsed DMA definitions; merging changes artifacts), H2.10 and H6.3 (diagram items), H4.9 (plan phase 10), H6.2 (memory device limits need a source; ROM and timing phase). The remaining H items, including M10's long sentences.

## 8. DEC Sources Read

PDP-8/E Small Computer Handbook (1973), the user's scan; read 2026-11-24 as page images.
- p. 2-11, item 2: "Machine stops occur after TP4. Thus, the MA lamps indicate the next memory address to be accessed, while the major state indicator lamps show the next major state to be executed."
- p. 2-12, item 4: "Operation of the ADDR LOAD switch places the central processor in the FETCH major state."
- p. 2-12, item 5: "Program execution is started by operating and releasing the CLEAR switch, then operating and releasing the CONTinue switch." (The 8/E has no START key.)
- p. 3-2, Table 3-1, ADDR LOAD: "loads the contents of the SR into the CPMA register and enables the FETCH major state for the next processor cycle".
- p. 3-2, CLEAR: "generates an INITIALIZE pulse that loads a binary 0 into bits 0-11 of the AC, the link, all I/O device flag registers and all interrupt system flip-flops. This is equivalent to executing a CAF instruction."
- p. 3-2, CONT: "sets the RUN flip-flop and issues a MEM START L signal to begin program execution at the memory location addressed by the current content of the CPMA register."
- p. 3-2, EXAM: loads M[CPMA] into MB "and then increments the CPMA and PC registers".
- p. 3-3, DEP: SR into MB and memory at CPMA, "then increments the CPMA and PC registers".
- p. 3-3, HALT: stops "at the beginning of the next FETCH cycle"; SING STEP: stops "at TS1 of the next machine cycle".

PDP-8/E Maintenance Manual, the user's copies (vol. 1 DEC-8E-HMM1A-D-D Sep 73; vol. 2 DEC-8E-HMM2A-D-D Jan 74; vol. 3 DEC-8E-HMM3A-C-D Jul 73), read 2026-11-24 from their text layers. Section numbers are the body headings (the vol. 1 contents page is misnumbered by the scan).
- vol. 1 §1.3, Table 1-1, p. 1-7: fast cycle 1.2 µs (FETCH, internal IOT, non-autoindex DEFER), slow 1.4 µs (execute, autoindex DEFER); an instruction "requires one fast and one slow memory cycle or 2.6 µs".
- vol. 1 §3.7, p. 3-16: SING STEP "halts at the end of the current cycle ... does not necessarily finish the current instruction".
- vol. 1 §3.8.2, p. 3-19: after EXAM or DEP, "depressing the CONT key ... causes a FETCH cycle".
- vol. 1 §3.9.2.2, p. 3-25: Group 1 operations through the data path and adders in one pass.
- vol. 1 §3.9.5, p. 3-34: NOT LAST TRANSFER L stops the processor timing in TS3 until it is negated and BUS STROBE L is generated.
- vol. 1 §3.11, p. 3-45: TAD: "If CAR OUT L equals a 1, ... the LINK is complemented."
- vol. 1 §3.14, p. 3-48, and §3.17, p. 3-53: slow cycle 28 clocks, 1.4 µs; fast 200 ns shorter; jumper W1 holds SLOW CYCLE ONLY.
- vol. 1 §3.33.2.1, p. 3-113: CLEAR's INITIALIZE "clears the AC Register, the LINK, the Interrupt system, all peripheral flags".
- vol. 1 §3.35.2, p. 3-127: MQA asserts MQ → BUS and AC → BUS, an inclusive OR in the Data Line Multiplexer. §3.40, p. 3-144: SWP's two MQ paths at TP3.
- vol. 1 §3.38, p. 3-138: Group 2 skip: "BTP3 sets the flip-flop"; the SKIP flip-flop is reset by INITIALIZE, at FETCH TP1, and at JMS TP2 (p. 3-140).
- vol. 1 §3.41.4, p. 3-149: CAF triggers a one-shot at TP3 that asserts INITIALIZE until TP2 of the next cycle.
- vol. 1 §3.42.1, p. 3-152: INT ENA "is also cleared by INITIALIZE".
- vol. 1 §3.42.3, p. 3-153: GTF gates LINK, INT RQST, and INT ENA onto DATA 0, 2, 4; "the nine remaining AC bits ... are provided by the KM8-E and/or KE8-E"; RTF "sets the INT ENA flip-flop at TP3".
- vol. 1 §3.46.2, p. 3-160: KL8-E: "The INTER ENABLE flip-flop is also set by CAF and by operation of the CLEAR key."
- vol. 2 §2.9.2, p. 2-8: a CIF, RTF, or RMF takes effect after the next JMP, or when a JMS's EXECUTE is entered.
- vol. 2 §2.9.6, pp. 2-9, 2-10: "If the current instruction is an AND, TAD, ISZ, DCA or EAE instruction, and if the processor is currently in the DEFER state, the next EXECUTE cycle will use the data field. All other machine cycles that are not data break cycles use the instruction field."
- vol. 2 §2.10.1, p. 2-11: INT INHIBIT "is generated at TP3 whenever an RTF, KEY CONTROL, CIF, or RMF signal is asserted, and negated at TP3 whenever a JMP or JMS instruction occurs" (status display bit 3).
- vol. 2 §2.14, p. 2-15: DF0-2 and INT INHIBIT (1) H "are selected by IND L" onto the DATA BUS for the console status display; "The contents of the Interrupt Buffer can be selected by the GTF or RIB instruction." KM8-E Theory of Operation (Nov 71), Figure 5, p. 14, shows the same: INT INH reaches bit 3 through IND only.
- vol. 2 §2.16 and §2.19, pp. 2-18, 2-19: the interrupt buffers load at TP4 when an interrupt occurs, and IB, IF, DF clear at TP4 "if there is an interrupt and no data break is occurring, or if the machine is powered up" (not at INITIALIZE).
- vol. 3 §1.4, p. 2-2: PC8-E: connected to the interrupt system "by a previous 6010 instruction, or by the INITIALIZE signal".
- vol. 3 §11.12.3, p. 11-45: RK8-E bootstrap: clear the control, load the Command Register with 0000, load the disk address, then JMP.

Small Computer Handbook (1973), further pages: p. 2-10, Table 2-1: BSW (7002) is new on the 8/E (previously NOP); 7014 (RAR RAL) and 7016 (RTR RTL) "produced predictable but undocumented results in the PDP-8/I and PDP-8/L. In the PDP-8/E these codes are specifically reserved"; MQ instructions (74X1) previously "Only available with EAE". p. 3-12: at most one of RAR, RAL, RTR, RTL, BSW per instruction. p. 3-16: Group 3 "useful when the MQ is employed as a temporary storage register, even if an EAE is not installed". p. 4-8, Table 4-1: RTF enables the interrupt system "in the same manner as by an ION instruction"; CAF's INITIALIZE "generally ... sets the interrupt enable flip-flop in each peripheral device"; GTF AC3 "Interrupt inhibit flip-flop" (contradicted by the maintenance manual, above).

KL10 Technical Reference (EK-OKL10-TM, 2nd ed. July 1984), the user's copy, read as page images: §2.16.1, p. 2-13: the PDP-11 front-end processor's uses include "Microcode loading and system startup"; §3.2.1.2, p. 3-6: "The heart of the EBox is a high-speed 2 K word control random-access memory (CRAM). This memory is initialized to contain the microcode. The microcode is loaded into the EBox from the front-end disk subsystem or the RX11 floppy disk subsystem." (A4.1, confirmed.)

Not found: the bootstrap's `JMP .` address 0031 (only SIMH `pdp8_rk.c`, secondary); "as DEC advises" for the EAE bits (A2.1); "its effect varied between models" (A2.1, now replaced by the Table 2-1 wording).
