# Diagram Changes for `one-cycle-fetch`

The user maintains the diagrams; Claude never edits them. This list gives, for each diagram, the changes the current docs require. Each change names the element as it is in the source and the doc section that requires it.

How the sources were read (2026-11-26):
- **draw.io:** every cell's label and every edge's endpoints and arrowheads were decoded from the source file. Where an edge end is not attached to a shape, the bus or shape it touches was computed from the stored coordinates.
- **WaveDrom:** the JSON was read directly.
- Nothing here is inferred from a rendered image.

No diagram source has changed on this branch (`git diff main -- diagrams` is empty), so every change is open. The earlier slice-by-slice list (entries A1 to E3) is in git history up to 0e7334d; each change below names the entries it replaces.

Changes marked **(also on main)** are differences between the diagram and the docs that predate the branch.

Timing waveforms count lengths in TSTEPs (one WaveDrom step, 50 ns). A TS's TP is at its end: a one-step TP is the TS's last step, and a two-step TP its last two.

---

## 1. `microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

Linked from the [Microarchitecture README](../docs/03-microarchitecture/README.md).

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 1.1 | IR (`2Ph0Qde3JH9-hkXoXRvS-49`) | Add **MDB → IR**. IR loads only from MDB. | MCS `IR_LOAD`; [Registers](../docs/01-architecture/01-registers.md#ir--instruction-register) (was A1) |
| 1.2 | IR – IDB edge `2Ph0Qde3JH9-hkXoXRvS-128` (arrowheads at both ends) | **Remove.** IR neither drives the IDB nor loads from it. | MCS `IDB_SRC` (was A1, E1) |
| 1.3 | MQ – IDB edge `2Ph0Qde3JH9-hkXoXRvS-124` (arrowheads at both ends) | Keep only the arrowhead at MQ: **IDB → MQ** (`MQ_SRC` = IDB, used by `MQ_CLEAR`). MQ no longer drives the IDB. | MCS `IDB_SRC`, `MQ_SRC` (was E2) |
| 1.4 | IR → EA_ADDR edge `cX9REWVKWh3u19Wi5yly-9`; PC (`2Ph0Qde3JH9-hkXoXRvS-47`) | Add the **address formation unit** between IR and EA_ADDR. Its inputs are IR[6:0], the page bit IR[7], and **MA[11:7]** (a new MA → unit edge). It has two outputs: **→ EA_ADDR** (`EA_ADDR_SRC` = 1) and **→ PC** (`PC_SRC` = 2, direct JMP). If you'd rather not draw the unit, add MA → EA_ADDR and EA formation → PC. | [Registers, EA_ADDR](../docs/01-architecture/01-registers.md); MCS `EA_ADDR_SRC`, `PC_SRC` (was A2, B6) |
| 1.5 | (new) | Add the **OPR pass unit**. Inputs: AC, L, MQ (MQA), FP_SR (OSR), and the IR stage decodes. Outputs: **→ AC** (`AC_SRC` = 7), **→ L** (`L_OP` = 1), **→ MQ** (`MQ_SRC` = 1). The ALU paths stay: MRIs, ISZ, and the PC increment use them. | [OPR Pass Unit §2, §3](../docs/03-microarchitecture/07-opr/00-pass-unit.md) (was C1-1, C2-6, C3-1) |
| 1.6 | (new), drawn like the other 1-bit registers | Add the 1-bit **SKIP** register. Input: the Group 2 skip logic (`OPR_SKIP_REQ`, from AC and L), beside the pass unit. Output: to Control. It loads at every main-sequence TP; no control-word field enables it. | [Registers, SKIP](../docs/01-architecture/01-registers.md#skip--skip); [OPR Pass Unit §2](../docs/03-microarchitecture/07-opr/00-pass-unit.md) (was C2-7) |
| 1.7 | Control (`2Ph0Qde3JH9-hkXoXRvS-67`); DMA Grant (`-66`, edge `-168`) | Add an **Instruction End (INSTR_END)** output to the DMA arbiter, drawn like DMA Grant. It is decoded by gates, not stored in the control word. | [ACS §4.10](../docs/04-control/20-control-output-definitions/02-architectural-control-signals.md#410-instruction-end-instr_end) (was B7) |
| 1.8 | FP_SR → ALU B `2Ph0Qde3JH9-hkXoXRvS-145`; MQ → ALU B `2Ph0Qde3JH9-hkXoXRvS-141`; MQ → AC `cX9REWVKWh3u19Wi5yly-27` | **Remove all three.** `ALU_B_SRC` is NONE or MB; `AC_SRC` has no MQ. | MCS `ALU_B_SRC`, `AC_SRC` (was P9-1) |
| 1.9 | AC → ALU B `2Ph0Qde3JH9-hkXoXRvS-142`; PC → ALU B `2Ph0Qde3JH9-hkXoXRvS-144` | **Remove both (also on main).** ALU B's only source is MB (`2Ph0Qde3JH9-hkXoXRvS-146`). v1's sources were MB, MQ, and FP_SR, never AC or PC. | MCS `ALU_B_SRC` |
| 1.10 | L → ALU A `2Ph0Qde3JH9-hkXoXRvS-136`; L → ALU B `2Ph0Qde3JH9-hkXoXRvS-143` | **Replace with one L → ALU edge (also on main).** L is the ALU's dedicated link input (LIN), not an A or B operand. The ALU → L edge (`-133`) stays. | [MCS §7.3.1](../docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#731-alu-evaluation) |

Checked, no change:
- MB ↔ MDB (`-151`), MB ↔ IDB (`cX9REWVKWh3u19Wi5yly-25`).
- FP_SR → IDB (`-132`), FP_SR → MDB (`-156`).
- PC ↔ IDB (`-125`), PC → ALU A (`-139`), PC → MA (`-158`).
- EA_ADDR → MA (`-157`), EA_ADDR ↔ IDB (`-127`).
- PC → AB (`cX9REWVKWh3u19Wi5yly-1`), MA → AB (`2GY4jtORsDWkwOyoSZJb-18`).
- AC ↔ IDB (`-129`), AC ↔ DB (`cX9REWVKWh3u19Wi5yly-15`).
- AC and MB → ALU A (`cX9REWVKWh3u19Wi5yly-14`, `-138`), MB → ALU B (`-146`).
- IF, DF, IB → AC (`-21`, `-19`, `-20`).

The hardwired sources (AC zero, `AC_SRC` = 5; PC's constant 1; MA's zero) are not drawn, consistently, so none needs adding.

---

## 2. `control/ms_next-flowchart/source/ms_next-flowchart.xml`

Linked from [Sequencing Control Signals §5.2](../docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md#52-major-state-transition).

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 2.1 | FETCH (`jyFapoluXV-c96oE9wt7-1`) → "Indirect Addressing?" (`-3`), edge `-4` | Add a decision after FETCH: **"Direct JMP or OPR?"** (`IR_NO_EXECUTE = 1` and not indirect). Yes → "Interrupt Request?" (`-10`). No → "Indirect Addressing?". | [FETCH and DEFER §3.4](../docs/03-microarchitecture/04-fetch-defer.md#34-ts4) (was B1, C1-2, C2-8, C3-2) |
| 2.2 | DEFER (`-5`) → Execute (`-7`), edge `-9` | Add a decision after DEFER: **"JMP I?"** (`IR_NO_EXECUTE = 1`). Yes → "Interrupt Request?". No → Execute. | [FETCH and DEFER §4.5](../docs/03-microarchitecture/04-fetch-defer.md#45-ts4) (was B2) |
| 2.3 | DMA (`-15`) – "DMA Request?" (`-16`), edge `-20` | **Move the arrowhead to the decision end (also on main).** It is at DMA (`startArrow`), so the edge reads as a second decision → DMA beside "Yes" (`-17`). After a DMA state, `/DMA_REQ` decides DMA again or FETCH. | Sequencing Control Signals §5.2 ("DMA → FETCH or DMA"); [DMA Interface §6.1](../docs/07-io/05-dma-interface.md#61-dma-timing-overview) |

Checked, no change: Execute → "Interrupt Request?" (`-11`), Yes → INTERRUPT (`-13`), INTERRUPT → FETCH (`-14`), No → "DMA Request?" (`-19`), No → FETCH (`-18`). Interrupt before DMA matches [Sequencing and Internal Direct Control §3](../docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#3-sequencing-control) ("The interrupt decision has priority over DMA entry").

---

## 3. `control/control-store-address-formation/source/control-store-address-formation.xml`

Linked from [CSO §5](../docs/04-control/08-control-store-organization.md#5-address-formation).

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 3.1 | "Equals 'EXECUTE'?" (`LYyLKf4eL-EtFkzbuk0P-1`), fed from the `MS_EFF` MUX (edge `-2`) | **`MS_EFF_IS_EXECUTE` is registered.** During TP, a gate decodes `MS = EXECUTE AND RUN = 1` from MS and RUN. As TP ends, a flip-flop publishes the result. Redraw as MS and RUN → gate → flip-flop → `MS_EFF_IS_EXECUTE` (`NrHUXa51DNh2OocIjt24-38`), and remove the edge from the MUX. | [CSO §5.1](../docs/04-control/08-control-store-organization.md#51-major-state-and-timing-state-codes) (new; decision 11a) |

Checked, no change:
- The `MS_EFF` MUX with wired 7.
- `/DMA_GRANT` = NOT (`MS_EFF` = DMA), and `IOT_ACTIVE` = `MS_EFF_IS_EXECUTE` AND `IR_IS_EXTERNAL_IOT`.
- The `FP_CMD` priority encoder, and the `SEQ_OVL` MUX selected by RUN.

---

## 4. `control/control-store-mapping/source/control-store-mapping.xml`

Linked from [CSO §5.3](../docs/04-control/08-control-store-organization.md#53-mapping-rom).

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 4.1 | "Wired 0 [5 Bits]" (`07B4lpnJHN1g52silYbh-50`) → "MUX [5 Bits]" (`-47`) | Relabel **"00·IR_CLASS [5 Bits]"**: `IR_CLASS` (3 bits, from predecode) with the two high bits 0. | [CSO §5.4.2](../docs/04-control/08-control-store-organization.md#542-execute-selection) (was B3) |

Checked, no change: "Wired 01" → DP_OVL_SEL MUX (`-55`), `IR_INDIRECT` → IR_SEQ MUX (`-61`), MAPR clocked by TP1 to TP4.

---

## 5. `control/control-store-organization/source/control-store-organization.xml`

Linked from [CSO §3](../docs/04-control/08-control-store-organization.md#3-overview).

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 5.1 | "Sequencer Slice ROM [7 Bits]" (`Smnm8CKmp2vPJFrs1iI9-13`) | Add two inputs, drawn like IR_SEQ (`-11`): **`IR_NO_EXECUTE` [1 Bit]** (address A2) and **`IR_OPR_HLT` [1 Bit]** (A1). | [CSO §5.6](../docs/04-control/08-control-store-organization.md#56-sequencer-slice-address) (was B4, C2-4) |
| 5.2 | "Datapath SliceROM [45 Bits]" (`-14`) | Relabel **"[40 Bits]"** (five devices). | [CSO §4.2](../docs/04-control/08-control-store-organization.md#42-datapath-slice) (was B5, C2-5, P9-2, E3) |
| 5.3 | (optional) | The slices are EEPROMs copied into shadow SRAMs at power-on. Draw it only if you want this diagram to show devices. | [CSO §8.1](../docs/04-control/08-control-store-organization.md#81-shadow-copy) (was D2) |

---

## 6. `control/control-store-overlay/source/control-store-overlay.xml`

Linked from [CSO §6](../docs/04-control/08-control-store-organization.md#6-datapath-overlay).

Each multiplexer's inputs are read top to bottom as groups 0 to 3. Every top input is the group 0 signal of CSO §6.2, which confirms the order.

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 6.1 | Group 1 inputs of DP_OVL[2], [1], [0]: `FP_CMD[2]` (`m7rejeYPD5JNTGzo8jMm-59`), `FP_CMD[1]` (`-76`), `FP_CMD[0]` (`-93`) | Put a **3-bit 2:1 multiplexer selected by RUN** in front of them. RUN = 0 selects `FP_CMD[2:0]`; RUN = 1 selects `SKIP`, 0, 0 (`SKIP` on DP_OVL[2]). | [CSO §6.2, §6.3](../docs/04-control/08-control-store-organization.md#63-state-group-run-multiplexer) (was C2-1) |
| 6.2 | DP_OVL[4] group 3: `SKIP_TAKEN` (`-9`) | **Wired 0.** | CSO §6.2 (was C2-2) |
| 6.3 | DP_OVL[3] group 3: `ISZ_SKIP_REQUIRED` (`-44`) | **Wired 0.** | CSO §6.2 (new) |
| 6.4 | DP_OVL[2] group 3: `IF_CHANGE_PENDING` (`-61`) | Replace with **`ISZ_SKIP_REQ`**. | CSO §6.2 (replaces C2-3's rename) |
| 6.5 | DP_OVL[0] group 2: `/INT_REQ` (`-94`) | Add a **gate with the SRQ decode** (`IR_IS_SRQ`) in front of it. It presents deasserted (1) to every other instruction. | CSO §6.2 (new) |

Checked, no change:
- Every group 0 and group 2 input, apart from 6.5's qualifier.
- Group 1's DP_OVL[4:3] (`CIFP`, `AUTO_INDEX_REQUIRED`).
- Group 3's DP_OVL[1:0] (`IE`, `CIFP`).

---

## 7. `timing/cpu-timing/source/cpu-timing-overview.json`

Linked from [Timing Architecture](../docs/09-timing/02-timing-architecture.md) (top, and §5.1).

The current waveform is one state of 30 steps: TS 6/9/7/6, every TP one step.

| # | Change | Doc |
|---|---|---|
| 7.1 | Draw the two mode-0 state lengths. **Fast** (FETCH; DEFER without auto-index): TS 5/8/6/5 = 24 steps, every TP one step. **Slow**, drawn as EXECUTE: TS 6/8/7/7 = 28 steps, with TP1 and TP2 one step and **TP3 and TP4 two steps**. | [Timing Architecture §5.1](../docs/09-timing/02-timing-architecture.md#51-structure) (was D1) |
| 7.2 | Optional: `/WR_PULSE` over the first step of each two-step TP. | [Timing Terminology §5.7](../docs/09-timing/01-terminology.md#57-write-pulse-wr_pulse) |
| 7.3 | Optional: the console transaction, 9 steps with a two-step TP_FP. | [Major State Timing §8](../docs/09-timing/03-major-state-timing.md#8-halted-state-and-console-transactions) |

---

## 8. `io/io_timing/source/io_timing.json`

Linked from [I/O Timing §3.1](../docs/07-io/03-io-timing.md#31-external-iot-timing-overview).

| # | Change | Doc |
|---|---|---|
| 8.1 | EXECUTE lengths **6/8/7/7**, with **TP3 and TP4 two steps** (TP1 and TP2 one step). Move every request signal with its TS: `IO_CLEAR_AC_REQ` in TS2, `IO_READ_REQ`/`IO_WRITE_REQ` in TS3, `IO_SKIP_REQ` in TS4. | Timing Architecture §5.1 |
| 8.2 | `/DB_READ`, `/DB_WRITE`, and DB valid: from **two steps (100 ns) into TS4** through the end of TP4. They now start at TS4's first step. | [Timing Terminology §5.8](../docs/09-timing/01-terminology.md#58-db-transfer-window-db_valid); [ACS §3.2](../docs/04-control/20-control-output-definitions/02-architectural-control-signals.md#32-timing-model) |
| 8.3 | **Also on main:** in the I/O Write group, `IOT_ACTIVE` (`01…1`) stays high at the end, where the read group's falls. Make it fall with the end of EXECUTE, as in the read group. | I/O Timing §3.1 ("valid throughout the external-IOT EXECUTE major state") |

---

## 9. `io/dma_timing/source/dma_timing.json`

Linked from [DMA Interface §6.1](../docs/07-io/05-dma-interface.md#61-dma-timing-overview).

| # | Change | Doc |
|---|---|---|
| 9.1 | The FETCH TS4 before the DMA state: **5 steps** (mode 0, fast), one-step TP4. The DMA state: **6/8/7/7**, with **TP2 two steps** and the other TPs one step. | Timing Architecture §5.1 |
| 9.2 | DMA Write group: add **`/WR_PULSE`** over the first step of TP2. | Timing Terminology §5.7; [DMA Interface §5.2](../docs/07-io/05-dma-interface.md#52-dma-write) |

Checked, no change: the controller's MFB, AB, MDB, `/RD`, and `/WR` are valid in TS2 only ([DMA Interface §3](../docs/07-io/05-dma-interface.md#3-dma-owned-interfaces)). The MS label FETCH → DMA is a valid sequence in v2.

---

## 10. `memory/memory_timing/source/memory_timing.png`

Linked from [Memory Interface §4](../docs/06-memory/02-memory-interface.md#4-memory-transaction-timing).

| # | Change | Doc |
|---|---|---|
| 10.1 | The source is WaveDrom text with a `.png` name. **Rename it `memory_timing.json`.** The export stays `.png`. | — |
| 10.2 | Read group: a fast state (5/8/6/5), read in TS2 with a one-step TP2, as in FETCH. | Timing Architecture §5.1 |
| 10.3 | Write group: a CPU write is in a slow state with a **two-step TP**, and memory stores during **`/WR_PULSE`**, the TP's first step. Add a `/WR_PULSE` row. TS2 has a two-step TP only in DMA, so draw the CPU write in EXECUTE TS3 (DCA: TS 7 steps, TP3 two steps). I'll then change Memory Interface §4's "TS2 and TP2 as a representative transaction phase" to match what you draw. | [Memory Timing §4](../docs/06-memory/04-memory-timing.md#4-active-write-window); Timing Terminology §5.7 |

---

## 11. `io/io_wait_timing/source/io_wait_timing.json`

| # | Change | Doc |
|---|---|---|
| 11.1 | **Obsolete.** `/IO_WAIT` is removed and no document links this diagram. Delete the source and its export, or keep them as history. | [I/O Timing §5](../docs/07-io/03-io-timing.md#5-fixed-iot-timing) |

---

## 12. `io/io_subsystem/source/io_subsystem.xml`

Linked from [I/O Architecture §4](../docs/07-io/01-io-architecture.md#4-io-subsystem-context).

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 12.1 | "I/O Response & Interrupt" signals (`ld4gAUsl70I4UcyXSL3b-61`) | Remove **"IO_WAIT, "**. | I/O Timing §5 |
| 12.2 | "DMA Authorization" signals (`-70`, "DMA_GRANT"; CPU → DMA Arbiter edge `-10`) | Add **INSTR_END**. The arbiter also takes MS[2:0], TS, and TP (also on main), which could go in the same cell. | [DMA Arbitration §3](../docs/07-io/06-dma-arbitration.md#3-major-state-visibility); ACS §4.10 |
| 12.3 | "CPU Memory Access" signals (`-67`) | Add **WR_PULSE**. The CPU drives it for DMA writes too. | [Memory Interface](../docs/06-memory/02-memory-interface.md); Timing Terminology §5.7 |
| 12.4 | "I/O Command & Timing" signals (`-35`, "IOT_ACTIVE, IOA[5:0], IOP[2:0], DB_WRITE, TS, TP") | **Add DB_READ (also on main).** | ACS §3.2 |

---

## 13. `isa/addressing-model/source/addressing-model.xml`

Linked from [EA Generation §3](../docs/02-isa/06-ea-generation.md#3-overview).

| # | Element (id) | Change | Doc |
|---|---|---|---|
| 13.1 | "EA_addr = PC[11:7] \|\| Address Offset" (`EGlYIu-c7P4GKegh5WQT-4`) | Relabel **"EA_addr = IA[11:7] \|\| Address Offset"**. IA is the instruction's own address (the PC before it is incremented), so an instruction in the last word of a page addresses its own page. | EA Generation §5; [Addressing Model §4.2](../docs/02-isa/05-addressing-model.md#42-current-page) (new; docs review A1.5) |

---

## 14. No Change

| Diagram | Checked |
|---|---|
| `architecture/class-a-buses/source/class-a-buses.xml` | CPU, Memory, I/O Device, DMA Device on AB, MFB, MDB, DB, matching [Class A Buses](../docs/05-buses-and-signals/01-class-a-buses.md) |
| `architecture/High-Level-Architecture/source/High-Level-Architecture.xml` | Plane-level text only. Optionally, the timing plane could list the timing ROM, and the control plane the control store. |

Not drawn anywhere: the timing ROM, TSEQ, the two register ranks, the shadow copy, and the inside of the OPR pass unit. The docs describe them in text and ASCII ([Timing Terminology §3.5](../docs/09-timing/01-terminology.md#35-timing-rom), [CSO §8.1](../docs/04-control/08-control-store-organization.md#81-shadow-copy), [OPR Pass Unit §2](../docs/03-microarchitecture/07-opr/00-pass-unit.md#2-structure)). Whether to draw them is the user's call.
