# Diagram Changes for Option 2 (running list)

The user maintains the diagrams; Claude never edits them. This list records, per slice, what each affected diagram **currently contains** (read from its source file, with element ids) and the change the slice's docs require.

How the sources were read: draw.io files were decoded and every cell's label and every edge's endpoints listed. Where an edge end is not attached to a shape (a free point), the shape or bus it touches was computed from the stored coordinates; bus arrows are 25 px wide, so a free end within about 13 px of a bus's centre line lies on the bus. Arrowheads are read from each edge's `startArrow` / `endArrow` style. Nothing here is inferred from a rendered image.

Status: **open** (the diagram still needs the change) or **done** (the user has updated it).

---

## Slice A (phase 3): IR at TP2, PC increment at TP1, EA page from MA

### `diagrams/microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| A1 | IR's only connection to a data source is edge `2Ph0Qde3JH9-hkXoXRvS-128`: IR to the IDB's right leg (free end at (990, 1210); IDB vertical at x = 970), arrowheads at both ends, IDB colour `#9673a6`. No MB → IR or MDB → IR edge exists. | Add **MDB → IR** (IR's load input is MDB, at FETCH TP2). The IR–IDB edge should show only **IR → IDB** (IR is an IDB source, `IDB_SRC` = 6); IR no longer loads from the IDB. | `01-registers.md` IR; `02-dataflow-and-bus-model.md` §3; `02-micro-operations.md` `MDB_TO_IR` | open |
| A2 | The EA unit's inputs: edge `cX9REWVKWh3u19Wi5yly-9` IR → EA_ADDR (enters EA_ADDR at the bottom centre). No edge from PC or MA to EA_ADDR; the page source is not drawn. | Add **MA → EA_ADDR** for the page bits (MA[11:7]); the IR → EA_ADDR edge carries IR[6:0] and the page bit. | `01-registers.md` MA, EA_ADDR; `02-micro-operations.md` `IR_ADDR_TO_EA_ADDR` | open |

Unchanged and verified: MB ↔ MDB (`2Ph0Qde3JH9-hkXoXRvS-151`, both arrowheads), MB ↔ IDB (`cX9REWVKWh3u19Wi5yly-25`), PC → MA (`…-158`), EA_ADDR → MA (`…-157`), PC → AB and MA → AB (`cX9REWVKWh3u19Wi5yly-1`, `2GY4jtORsDWkwOyoSZJb-18`, both ending on the AB arrow), PC → ALU A and B (`…-139`, `…-144`). The PC increment still goes through the ALU, so no PC-path change. The instruction fetch now addresses memory from MA (`AB_SRC = MA`, direct-control §4.3.1), which the existing MA → AB edge covers; PC → AB stays in use for console EXAMINE and DEPOSIT (§4.2), so neither AB edge changes.

### Checked, no slice A change

| Diagram | What the source contains | Why unchanged |
|---|---|---|
| `diagrams/timing/cpu-timing/source/cpu-timing-overview.json` | WaveDrom: 20 MHz clock, TS1 to TS4 = 6, 9, 7, 6 steps, TP1 to TP4 pulses; no register events | Shows no IR, PC, or EA events. Its TS lengths change in slice D |
| `diagrams/isa/addressing-model/source/addressing-model.xml` | Flowchart: `EA_addr = PC[11:7] \|\| Address Offset` for P = 1 | ISA view: PC is the instruction's address, as in `docs/02-isa`, which is unchanged |
| `diagrams/control/control-store-mapping/source/control-store-mapping.xml` | IR[12 bits] → Mapping ROM[8 bits] → MAPR (clocked by TP1 to TP4) → the three EXECUTE multiplexers | MAPR's clocking is unchanged; only the correctness argument in CSO §5.4.3 changed |
| `diagrams/architecture/class-a-buses/source/class-a-buses.xml` | CPU, Memory, I/O Device, DMA Device blocks on AB, MFB, MDB, DB | System level; no register detail |
| `diagrams/architecture/High-Level-Architecture/source/High-Level-Architecture.xml`, `control-store-address-formation.xml`, `control-store-organization.xml`, `control-store-overlay.xml`, `ms_next-flowchart.xml`, `io_subsystem.xml`, `io/*.json` | No IR source, PC increment, or EA page elements | Not touched by slice A |

---

## Slice B (phase 4): JMP completes in FETCH (direct) or DEFER (JMP I)

### `diagrams/control/ms_next-flowchart/source/ms_next-flowchart.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| B1 | FETCH → "Indirect Addressing?" (`jyFapoluXV-c96oE9wt7-4`); Yes → DEFER (`-6`), No → Execute (`-8`). | Before or within the FETCH decision, a direct JMP (`IR_NO_EXECUTE = 1`, not indirect) goes to the instruction-completion decision ("Interrupt Request?"), not to Execute. | `04-fetch-defer.md` §3.4; direct-control §3.2.2, §3.2.5 to §3.2.7 | open |
| B2 | DEFER → Execute (`jyFapoluXV-c96oE9wt7-9`), unconditional. | A JMP I (`IR_NO_EXECUTE = 1`) goes from DEFER to the instruction-completion decision ("Interrupt Request?"); other instructions go to Execute. | `04-fetch-defer.md` §4.5; direct-control §3.2.4 | open |

Unchanged and verified: Execute → "Interrupt Request?" (`-11`) and the INTERRUPT, DMA, and FETCH edges after it.

### `diagrams/control/control-store-mapping/source/control-store-mapping.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| B3 | "Wired 0 [5 Bits]" (`07B4lpnJHN1g52silYbh-50`) → "MUX [5 Bits]" (`-51`), the input selected outside EXECUTE. | Replace the wired 0 with `00·IR_CLASS` (IR_CLASS, 3 bits, from predecode; the two high bits 0). | CSO §5.3, §5.4.2 | open |

Unchanged and verified: "IR_INDIRECT [1 Bit]" → "MUX [1 Bit]" (`-61`); "Wired 01 [2 Bits]" → "MUX [2 Bits]" (`-55`).

### `diagrams/control/control-store-organization/source/control-store-organization.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| B4 | Sequencer Slice ROM inputs: TS, IR_SEQ, HLT_REQ, FP_STOP, /DMA_REQ, SEQ_OVL, MS_EFF (`Smnm8CKmp2vPJFrs1iI9-30` to `-36`); no A2 input. | Add `IR_NO_EXECUTE [1 Bit]` → Sequencer Slice ROM (address A2). | CSO §5.6 | open |
| B5 | Node `Smnm8CKmp2vPJFrs1iI9-14` is labelled "Datapath SliceROM [45 Bits]". The v1 packing was 44 bits, so the label already differed from the docs before slice B. | Change the label to 46 bits (the packer's slice B result, CSO §4.2, §7.2). It changes again in slice C. | CSO §4.2 | open |

### `diagrams/microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| B6 | PC's load inputs: PC ↔ IDB (`2Ph0Qde3JH9-hkXoXRvS-125`, arrowheads at both ends) and Control ↔ PC (`…-181`). No path from the address formation to PC. | Add the formed address (IR[6:0], with the page from MA, as in A2) as a PC input (`PC_SRC` = 2, direct JMP). JMP I's `PC ← MB` uses the existing MB ↔ IDB and PC ↔ IDB edges. | `02-micro-operations.md` `IR_ADDR_TO_PC`; MCS `PC_SRC` | open |
| B7 | Control's architectural outputs include "DMA Grant" (`Control -> DMA Grant`, `…-168`), Read, Write, and IOA; no instruction-end output. | Add an "Instruction End (INSTR_END)" output to the DMA arbiter, drawn like DMA Grant. It is a gate decode of MS_EFF, TS, `IR_NO_EXECUTE`, and `IR_INDIRECT`, not a control-store output. | ACS §4.10 | open |

### Checked, no slice B change

| Diagram | What the source contains | Why unchanged |
|---|---|---|
| `diagrams/io/dma_timing/source/dma_timing.json` | WaveDrom: MS goes from FETCH to DMA at the first TP4 (`data: [' FETCH', 'DMA']`) | In v1, DMA could follow only EXECUTE; in v2 a DMA state can follow FETCH after a direct JMP, so the label is now possible. No change required; whether it should name a specific state is your call |
| `diagrams/timing/cpu-timing/source/cpu-timing-overview.json` | TS and TP waveform only | No boundary events |

---

## Slice D (phase 5): state lengths (timing ROM), SRAM-shadowed control store

### `diagrams/timing/cpu-timing/source/cpu-timing-overview.json`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| D1 | WaveDrom, `CLK - 20MHz`, 30 steps: TS1 `01.....0…` (6 steps), TS2 9 steps, TS3 7 steps, TS4 6 steps, a TP pulse (`Hl`) at the end of each; one waveform, the slow lengths. | Show both lengths of Timing Architecture §5.1: the slow state (6/9/7/6, as drawn) and the fast state (5/8/6/5) for FETCH and non-autoindex DEFER, for example as a second group or a second diagram. The doc §5.1 links this diagram as "See:". | `09-timing/02-timing-architecture.md` §5.1 | open |

### `diagrams/control/control-store-organization/source/control-store-organization.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| D2 | Nodes "Sequencer Slice ROM [7 Bits]" (`Smnm8CKmp2vPJFrs1iI9-13`) and "Datapath SliceROM [45 Bits]" (`-14`); no device technology shown. | Optional: if the diagram should show the devices, the slices are EEPROMs copied into shadow SRAMs at power-on (CSO §8.1). No change is required for the address formation it draws. | CSO §2, §8, §8.1 | open (optional) |

No diagram exists for the timing ROM, the TSEQ counter, or the shadow-copy logic; the docs describe them in text (Timing Terminology §3.5, CSO §8.1). Whether to draw them is the user's call.

---

## Slice C1 (phase 6): OPR Group 1 completes in FETCH through the OPR pass unit

### `diagrams/microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C1-1 | AC's drawn connections: AC → ALU A (`cX9REWVKWh3u19Wi5yly-14`, ending at (530, 990) on "ALU A B"), AC → ALU B (`2Ph0Qde3JH9-hkXoXRvS-142`, (670, 990)), AC – IDB (`…-129`), AC → DB (`cX9REWVKWh3u19Wi5yly-15`), and DF, IB, IF, MQ → AC (`-19`, `-20`, `-21`, `-27`). L: L → ALU (`2Ph0Qde3JH9-hkXoXRvS-136`, `-143`), L – ALU top (`-133`). No OPR pass unit. | Add the OPR pass unit: inputs AC and L, stage controls from IR (the Group 1 bits, qualified by `IR_CLASS = 011`), outputs to AC (`AC_SRC` = 7) and to L (`L_OP` = 1). The ALU paths stay (MRIs, ISZ, PC increment). | `07-opr/01-group1-execution.md` §4; `02-micro-operations.md` `OPR_PASS`; MCS `AC_SRC`, `L_OP` | open |

### `diagrams/control/ms_next-flowchart/source/ms_next-flowchart.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C1-2 | As B1: FETCH → "Indirect Addressing?" → DEFER or Execute. | With B1's change, the FETCH completion path covers Group 1 OPR as well as direct JMP (`IR_NO_EXECUTE = 1`, not indirect). If B1 is drawn with a "JMP?" decision, it becomes "JMP or Group 1 OPR?" (or "IR_NO_EXECUTE?"). | `04-fetch-defer.md` §3.4 | open |

---

## Slice C2 (phase 7): OPR Group 2 completes in FETCH (SKIP register, HLT at FETCH TP3, RUN multiplexer)

### `diagrams/control/control-store-overlay/source/control-store-overlay.xml`

The five 4:1 multiplexers, read from the edges: `m7rejeYPD5JNTGzo8jMm-1` → DP_OVL[4] (inputs `SKIP_TAKEN`, `IO_SKIP_REQ`, `CIFP`, `IO_WRITE_REQ`); `-40` → DP_OVL[3] (`ISZ_SKIP_REQUIRED`, `IO_CLEAR_AC_REQ`, `AUTO_INDEX_REQUIRED`, `IO_READ_REQ`); `-57` → DP_OVL[2] (`IF_CHANGE_PENDING`, `IOT_WRITE_PENDING`, `FP_CMD[2]`, `IO_CLEAR_AC_REQ`); `-74` → DP_OVL[1] (`IE`, `IOT_READ_PENDING`, `FP_CMD[1]`, `IOT_WRITE_PENDING`); `-91` → DP_OVL[0] (`CIFP`, `/INT_REQ`, `FP_CMD[0]`, `IOT_READ_PENDING`). Input edges `rYJyN2ecPjk_JY8LC9AR-1` to `-20`.

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C2-1 | `FP_CMD[2]` (`-59`), `FP_CMD[1]` (`-76`), `FP_CMD[0]` (`-93`) drive the group 1 inputs of the DP_OVL[2], [1], [0] multiplexers directly (`rYJyN2ecPjk_JY8LC9AR-11`, `-15`, `-19`). | Put a 3-bit 2:1 multiplexer selected by `RUN` in front of those three inputs: `RUN = 0` → `FP_CMD[2:0]`; `RUN = 1` → `SKIP`, 0, 0 (SKIP on DP_OVL[2]). | CSO §6.2, §6.3 | open |
| C2-2 | Node `-9` "SKIP_TAKEN" → DP_OVL[4] multiplexer (`rYJyN2ecPjk_JY8LC9AR-1`), group 3's input. | Group 3 no longer uses DP_OVL[4] (the skip decision is now the `SKIP` register, in group 1): the input becomes wired 0. | CSO §6.2 | open |
| C2-3 | Node `-44` labelled "ISZ_SKIP_REQUIRED". | Rename to `ISZ_SKIP_REQ`. | Derived Flags; CSO §6.2 | open |

### `diagrams/control/control-store-organization/source/control-store-organization.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C2-4 | Sequencer Slice ROM inputs: TS, IR_SEQ, HLT_REQ, FP_STOP, /DMA_REQ, SEQ_OVL, MS_EFF (`Smnm8CKmp2vPJFrs1iI9-30` to `-36`); no A1 input (B4 adds A2). | Add `IR_OPR_HLT [1 Bit]` → Sequencer Slice ROM (address A1). | CSO §5.6 | open |
| C2-5 | Node `-14` "Datapath SliceROM [45 Bits]" (45 matches slice C1's packing). | 46 bits (slice C2 adds `SKIP_LOAD`). Replaces B5. | CSO §4.2, §7.2 | open |

### `diagrams/microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C2-6 | FP_SR → ALU B: edge `2Ph0Qde3JH9-hkXoXRvS-145`, free end at (670, 990) on "ALU A B" (v1's OSR path, `ALU_B_SRC = FP_SR`). No FP_SR input to an OPR pass unit (C1-1 adds the unit). | Add FP_SR → the OPR pass unit (stage B, OSR). The FP_SR → ALU B edge is no longer used in v2; remove it when the encoding goes (slice C3) or now, your call. | `07-opr/02-group2-execution.md` §4; `01-group1-execution.md` §4 | open |
| C2-7 | Halt Request (HLT_REQ) node `2GY4jtORsDWkwOyoSZJb-3`, written by Control (`2Ph0Qde3JH9-hkXoXRvS-174`). No SKIP register. | Add the 1-bit `SKIP` register: loaded from the Group 2 skip logic (`OPR_SKIP_REQ`, from AC, L, IR) under `SKIP_LOAD`, read by Control (state overlay). Drawn like HLT_REQ. | `01-registers.md` SKIP; MCS `SKIP_LOAD` | open |

### `diagrams/control/ms_next-flowchart/source/ms_next-flowchart.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C2-8 | As B1 and C1-2: FETCH (`-1`) → "Indirect Addressing?" (`-3`) → DEFER or Execute. | The FETCH completion path covers Group 2 OPR too: "JMP, Group 1 or Group 2 OPR?" (or "IR_NO_EXECUTE?"). | `04-fetch-defer.md` §3.4 | open |

### Checked, no slice C2 change

| Diagram | What the source contains | Why unchanged |
|---|---|---|
| `control-store-mapping.xml` | IR → Mapping ROM → MAPR → MUX[5], MUX[2] (Wired 01), MUX[1] (IR_INDIRECT / MAPR[7]) | The diagram does not name the sequencer decode's per-TS contents (CSO §5.3 table), so dropping EXECUTE TS3's `IR_OPR_HLT` changes nothing drawn |
| `control-store-address-formation.xml` | MS/RUN → MS_EFF; FP command priority encoder; SEQ_OVL MUX[3] by RUN | The new RUN multiplexer is on the datapath overlay (C2-1), not here |

---

## Slice C3 (phase 8): OPR Group 3 completes in FETCH (MQ output of the pass unit)

### `diagrams/microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C3-1 | MQ (`cX9REWVKWh3u19Wi5yly-26`) has three edges: MQ → AC (`cX9REWVKWh3u19Wi5yly-27`, v1's `AC_SRC` = 5 for SWP), MQ → ALU B (`2Ph0Qde3JH9-hkXoXRvS-141`, free end at (670, 990) on "ALU A B", v1's MQA through the ALU), and MQ – IDB (`2Ph0Qde3JH9-hkXoXRvS-124`, free end at (210, 1070), at the same x as the AC – IDB edge `-129` and the MB – IDB edge `cX9REWVKWh3u19Wi5yly-25`). No AC → MQ edge and no pass-unit connection. | Add MQ → the OPR pass unit (stage B, MQA) and the pass unit's MQ output → MQ (`MQ_SRC` = 1; MQL, SWP). MQ → AC and MQ → ALU B are no longer used in v2; remove them with the encodings in phase 9, or now, your call. MQ – IDB stays (`MQ_CLEAR`, `IDB_SRC` = MQ). | `07-opr/03-group3-execution.md` §4; MCS `MQ_SRC`; `01-registers.md` MQ | open |

### `diagrams/control/ms_next-flowchart/source/ms_next-flowchart.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| C3-2 | As C1-2 and C2-8: FETCH (`jyFapoluXV-c96oE9wt7-1`) → "Indirect Addressing?" (`-3`) → DEFER or Execute. | The FETCH completion path covers every OPR: "JMP or OPR?" (or "IR_NO_EXECUTE?"). Supersedes C1-2 and C2-8. | `04-fetch-defer.md` §3.4 | open |

### Checked, no slice C3 change

| Diagram | Why unchanged |
|---|---|
| `control-store-overlay.xml`, `control-store-organization.xml`, `control-store-mapping.xml`, `control-store-address-formation.xml` | The packing is unchanged from slice C2 (46 bits, the same overlay groups and pins); the class decode's new code is not drawn |

---

## Phase 9: ALU cleanup (decision 13, 2026-11-21)

### `diagrams/microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| P9-1 | FP_SR → ALU B (`2Ph0Qde3JH9-hkXoXRvS-145`), MQ → ALU B (`2Ph0Qde3JH9-hkXoXRvS-141`), MQ → AC (`cX9REWVKWh3u19Wi5yly-27`). | Remove all three edges. Settles the "your call" removals in C2-6 and C3-1. | MCS `ALU_B_SRC`, `AC_SRC` | open |

### `diagrams/control/control-store-organization/source/control-store-organization.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| P9-2 | Node `Smnm8CKmp2vPJFrs1iI9-14` "Datapath SliceROM [45 Bits]". | 44 bits. Supersedes B5 and C2-5. | CSO §4.2, §7.2 | open |

---

## Final list (phase 9, 2026-11-21)

No diagram source has changed on this branch (`git diff main -- diagrams` is empty), so every entry above is still open. Superseded entries are folded into the entry that replaces them. Per diagram:

| Diagram | Entries | Change |
|---|---|---|
| `CPU_Architecture.xml` | A1, A2, B6, B7, C1-1, C2-6, C2-7, C3-1, P9-1 | MDB → IR, IR → IDB only (A1); MA → EA_ADDR for the page (A2); formed address → PC (B6); INSTR_END output to the DMA arbiter (B7); the OPR pass unit with AC, L, FP_SR, and MQ inputs and AC, L, and MQ outputs (C1-1, C2-6, C3-1); the SKIP register (C2-7). Remove FP_SR → ALU B, MQ → ALU B, and MQ → AC (P9-1). |
| `ms_next-flowchart.xml` | B1 + C3-2 (C1-2, C2-8 superseded), B2 | FETCH: a direct JMP or any OPR (`IR_NO_EXECUTE = 1`, not indirect) goes to the instruction-completion decision; DEFER: a JMP I does too. |
| `control-store-mapping.xml` | B3 | The wired 0 into the 5-bit MUX becomes `00·IR_CLASS`. |
| `control-store-organization.xml` | B4, C2-4, P9-2 (B5, C2-5 superseded), D2 (optional) | Sequencer ROM inputs `IR_NO_EXECUTE` (A2) and `IR_OPR_HLT` (A1); the datapath slice label "[45 Bits]" becomes **44** (P9-2); optionally, EEPROMs shadowed into SRAM. |
| `control-store-overlay.xml` | C2-1, C2-2, C2-3 | The `RUN` multiplexer on group 1 bits 2 to 0 (`SKIP`, 0, 0 when running); group 3's DP_OVL[4] input `SKIP_TAKEN` becomes wired 0; `ISZ_SKIP_REQUIRED` → `ISZ_SKIP_REQ`. |
| `cpu-timing-overview.json` | D1 | Add the fast state (5/8/6/5) beside the slow state (6/9/7/6). |
| Not drawn | D (note) | No diagram exists for the timing ROM, the TSEQ counter, or the shadow-copy logic; drawing them is your call. |

Checked across all slices with no change: `control-store-address-formation.xml`, `addressing-model.xml`, `class-a-buses.xml`, `High-Level-Architecture.xml`, `io_subsystem.xml`, `io/*.json` (`dma_timing.json`'s FETCH → DMA label is now a possible sequence; optional). The spec §9 forecast is fully covered by the entries above.
