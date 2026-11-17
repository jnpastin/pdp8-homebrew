# Control Store Organization

## 1. Purpose

Defines the physical organization of the control store: how the logical control function of [Control Addressing](./02-control-addressing.md) and the logical [Control Word](./04-control-word.md) are realized in memory devices and discrete multiplexers.

This document establishes:

- the device technology and its constraints
- how the control store is divided into independently addressed parts, and the fields each part produces
- the ROM stage that translates the instruction into address information
- the address map of each part, including address bits shared among condition inputs
- how control-word fields are packed into device outputs
- what the ROM-generation tools must verify

The logical control word, the control inputs, and the behavior they select are defined elsewhere and are not changed by this document.

### 1.1 Terms

| Term | Meaning |
|---|---|
| slice | a part of the control store that produces a fixed subset of control-word fields from its own address ([Control Addressing §2.1](./02-control-addressing.md#21-partitioned-and-two-level-control-stores)) |
| sequencer slice | the slice producing `MS_NEXT`, `MS_LOAD`, `RUN_NEXT`, `HLT_REQ_NEXT`, and `/INITIALIZE` (section 4.1) |
| datapath slice | the slice producing every encoded field except the sequencer fields (section 4.2) |
| `MS_EFF` | the effective major state: the 3-bit major-state code presented to the control store, `MS` while running and `HALTED` (code 7) while halted (section 5.1); the `MS` register itself is unchanged |
| `MS_EFF_IS_EXECUTE` | a derived signal: 1 when `MS_EFF` is EXECUTE (code 2), else 0; equivalently, `MS = EXECUTE` and `RUN = 1` (section 5.1) |
| mapping ROM | ROM devices inside the control store that map IR and TS to the instruction-dependent part of the slice addresses for the following TS of EXECUTE; the mapping stage of [Control Addressing §2.1](./02-control-addressing.md#21-partitioned-and-two-level-control-stores). The name follows the mapping PROMs of microprogrammed machines, which map an instruction to its microprogram |
| `MAPR` | the mapping register: holds the mapping ROM output for the current TS, loaded at each main-sequence TP ([Mapping Register](../01-architecture/01-registers.md#mapr--mapping-register); section 5.4) |
| `VARIANT` | a 5-bit slice address field identifying the instruction-dependent behavior that applies in the current TS of EXECUTE (section 5.4) |
| overlay | an address field that carries different condition inputs in different contexts ([Control Addressing §6.3](./02-control-addressing.md#63-domain-separation)) |
| `DP_OVL[4:0]` | the datapath slice's 5-bit overlay field |
| overlay group | one fixed assignment of condition inputs to `DP_OVL[4:0]` |
| `DP_OVL_SEL` | a 2-bit signal selecting which overlay group drives `DP_OVL[4:0]` (sections 5.4 and 6) |
| `FP_CMD[2:0]` | the encoded front-panel command (section 5.2) |
| `SEQ_OVL[2:0]` | the sequencer slice's 3-bit overlay field: the running-only sequencer inputs while running, `FP_CMD[2:0]` while halted (section 5.6) |
| `IR_SEQ` | the 1-bit sequencer address input carrying the one instruction decode the sequencer slice needs in the current TS (section 5.4) |
| 28C256 | a parallel EEPROM with 15 address bits and 8 data bits (32K × 8) |

Status: the slice structure, device technology, and packing rules are design decisions. The specific address-bit assignments, variant counts, and overlay groups are the current proposal, measured from the maintained specifications; the packing tool will finalize and verify them.

---

## 2. Design Constraints

| Constraint | Consequence |
|---|---|
| Control logic is discrete: memory devices and standard discrete logic only; no PAL, GAL, CPLD, or FPGA | Every function wider than a few gates is a ROM lookup; glue is limited to multiplexers, encoders, and latches |
| Control-store devices are parallel EEPROMs (28C256 class: 15 address bits, 8 data bits) | Each slice address is at most 15 bits; each device supplies 8 control-word bits |
| Device count matters but is not the primary concern | Control-word width, not address depth, sets the device count; width is reduced where it costs no logic |

The control store is sparse: most addresses are unreachable or repeat another address's word. Sparsity is permitted ([Control Addressing §7.2](./02-control-addressing.md#72-sparsity)).

---

## 3. Overview

![Control Store Organization](../../diagrams/control/control-store-organization/export/control-store-organization.png)

The diagram shows the address inputs of the two slices. Each input is formed by logic drawn separately: `MS_EFF` and `SEQ_OVL` in section 5, `VARIANT` and `IR_SEQ` in section 5.3, and `DP_OVL` in section 6. The fields each slice produces are listed in section 4.

Signal flow:

- `MS` and `RUN` form `MS_EFF`; `MS_EFF` is compared with EXECUTE to form `MS_EFF_IS_EXECUTE`.
- The front-panel commands are encoded into `FP_CMD[2:0]`.
- The mapping ROM reads `IR` and `TS` and produces the entry for the following TS of EXECUTE. `MAPR` captures it at each main-sequence TP, so during each TS `MAPR` holds the entry for that TS.
- `MS_EFF_IS_EXECUTE` selects, for each of three fields, either the `MAPR` field or a fixed source (section 5.4). Each field is an address input of a different part of the control store:
  - `VARIANT` → datapath slice
  - `IR_SEQ` → sequencer slice
  - `DP_OVL_SEL` → datapath overlay
- The datapath overlay presents the runtime conditions or `FP_CMD` selected by `DP_OVL_SEL` on `DP_OVL[4:0]` (section 6).
- The datapath slice reads `MS_EFF`, `TS`, `VARIANT`, and `DP_OVL[4:0]`.
- The sequencer slice reads `MS_EFF`, `TS`, the sequencer inputs, `SEQ_OVL[2:0]`, and `IR_SEQ`.

No field of the mapping ROM's output reaches the datapath or the sequencing logic directly; every field is used only to address the slice ROMs or to select the overlay.

Because the mapping ROM is evaluated one TS ahead, only one ROM access lies between a TS boundary and a settled control word (section 5.4.3).

---

## 4. Slices

The control store is partitioned into two slices ([Control Addressing §2.1](./02-control-addressing.md#21-partitioned-and-two-level-control-stores)). Every encoded control-word field is produced by exactly one slice.

### 4.1 Sequencer Slice

Fields:

```
MS_NEXT, MS_LOAD, RUN_NEXT, HLT_REQ_NEXT, /INITIALIZE
```

These fields depend on the same small set of inputs in every major state: run control, halt and front-panel inputs, the interrupt and DMA requests, and three instruction decodes. Separating them keeps those inputs out of the datapath slice address.

Width: 7 bits, one device; one output is spare.

### 4.2 Datapath Slice

Fields: every other encoded field of the control word, grouped here by function. Widths are in bits. The fields are defined in [Microarchitectural Control Signals §5](./20-control-output-definitions/01-microarchitectural-control-signals.md#5-signal-definitions), except `/RD`, `/WR`, `/DB_READ`, and `/DB_WRITE`, which are defined in [Architectural Control Signals §4](./20-control-output-definitions/02-architectural-control-signals.md#4-signal-definitions).

| Group | Fields (width) | Bits |
|---|---|---|
| Memory interface | `/RD` (1), `/WR` (1), `AB_SRC` (1), `MFB_SRC` (1), `MDB_SRC` (2), `MA_LOAD` (1), `MA_SRC` (2), `MB_LOAD` (1), `MB_SRC` (2), `EA_ADDR_LOAD` (1), `EA_ADDR_SRC` (1) | 14 |
| Internal data bus | `IDB_DRIVE` (1), `IDB_SRC` (3) | 4 |
| Registers and ALU | `AC_LOAD` (1), `AC_SRC` (3), `L_LOAD` (1), `L_OP` (2), `MQ_LOAD` (1), `MQ_SRC` (1), `ALU_A_SRC` (2), `ALU_B_SRC` (3), `ALU_OP` (4), `IR_LOAD` (1), `PC_LOAD` (1), `PC_INC` (1), `PC_SRC` (1) | 22 |
| Fields and interrupts | `IF_LOAD` (1), `IF_SRC` (2), `DF_LOAD` (1), `DF_SRC` (3), `DIF_LOAD` (1), `DIF_SRC` (3), `IB_LOAD` (1), `CIFP_LOAD` (1), `CIFP_VAL` (1), `IE_LOAD` (1), `IE_VAL` (1), `II_LOAD` (1), `II_VAL` (1) | 18 |
| External IOT | `IOT_TRANSFER_LOAD` (1), `IOT_TRANSFER_VAL` (2), `/DB_READ` (1), `/DB_WRITE` (1) | 5 |

The 43 fields total 63 bits; bit sharing packs them into 45 (section 7.2). Control-word fields that are derived or supplied from outside the control store (`/DMA_GRANT`, `IOT_ACTIVE`, `IOA[5:0]`, `IOP[2:0]`, `GTF_FLAGS`, `IF_DF_COMBINED`, `DB_INPUT`, `MDB_INPUT`) are not produced by either slice.

Width: 45 bits after packing (section 7), six devices.

---

## 5. Address Formation

![Control Store Address Formation](../../diagrams/control/control-store-address-formation/export/control-store-address-formation.png)

The diagram shows the major-state code and its decodes (section 5.1), the front-panel command code (section 5.2), and the `SEQ_OVL` multiplexer (section 5.6). The mapping stage is drawn in section 5.3.

### 5.1 Major-State Code

`MS` uses five of its eight codes (`FETCH = 0`, `DEFER = 1`, `EXECUTE = 2`, `INTERRUPT = 3`, `DMA = 4`). The control store sees:

```
MS_EFF = HALTED (7)   if RUN = 0
MS_EFF = MS           otherwise
```

realized by a 3-bit 2:1 multiplexer selected by `RUN`. `HALTED` is the halted pseudo-state; no separate `RUN` address bit is needed.

`MS` itself is not changed while halted. It keeps the held major state, because CONTINUE resumes at TS1 of the held state ([Major State Timing §8.1](../09-timing/03-major-state-timing.md#81-main-timing-while-halted)), and because the DMA arbiter observes `MS` directly. Only the control store sees code 7.

The substitution loses no information the control store needs: while halted, no control word depends on which major state is held, and while running, `MS_EFF = MS`. It replaces a `RUN` address bit that would not fit in the 15-bit datapath slice address.

`MS_EFF_IS_EXECUTE` is produced by comparing `MS_EFF` with the EXECUTE code.

Two architectural outputs are decoded from `MS_EFF` rather than stored in the control store, so that they stay clean across TS boundaries for a whole major state ([Architectural Control Signals §3.2](./20-control-output-definitions/02-architectural-control-signals.md#32-timing-model)):

```
/DMA_GRANT = NOT (MS_EFF = DMA)
IOT_ACTIVE = MS_EFF_IS_EXECUTE AND IR_IS_EXTERNAL_IOT
```

### 5.2 Front-Panel Command Code

Console commands are accepted at most one at a time ([External Inputs §4.1](./10-control-input-definitions/04-external-inputs.md#41-console-command-acceptance)). A priority encoder encodes them into `FP_CMD[2:0]`:

| `FP_CMD` | Command |
|---|---|
| 0 | none |
| 1 | `FP_START` |
| 2 | `FP_CONTINUE` |
| 3 | `FP_CLEAR` |
| 4 | `FP_LOAD_ADDRESS` |
| 5 | `FP_EXAMINE` |
| 6 | `FP_DEPOSIT` |

### 5.3 Mapping ROM

![Control Store Mapping](../../diagrams/control/control-store-mapping/export/control-store-mapping.png)

The diagram shows the mapping ROM (this section), `MAPR` and its clock (section 5.4.1), and the EXECUTE selection (section 5.4.2). Outside EXECUTE the multiplexers select the wired values and `IR_INDIRECT`; in EXECUTE they select `MAPR`. The 5-bit multiplexer with a wired 0 input is equivalent to the five AND gates of section 5.4.2.

The mapping ROM ([Control Addressing §2.1](./02-control-addressing.md#21-partitioned-and-two-level-control-stores)) maps the instruction to the address information each slice needs in EXECUTE. It is evaluated one TS ahead: the entry at TS *n* is the entry for TS *n*+1, and the entry at TS4 is the entry for TS1.

Address:

```
A14..A3 = IR[11:0]
A2..A1  = TS
A0      = 0 (wired)
```

Output fields, for the EXECUTE TS that follows the addressed TS:

| Field | Width | Meaning |
|---|---|---|
| variant | 5 (D4..D0) | the instruction-dependent behavior that applies in that TS of EXECUTE |
| overlay group | 2 (D6..D5) | the overlay group presented to the datapath slice in that TS (section 6) |
| sequencer decode | 1 (D7) | the instruction decode the sequencer slice needs in that TS |

The mapping ROM is one device. Its output is used only through `MAPR` (section 5.4).

The sequencer decode carries a different decode in different timing states of EXECUTE. Because the mapping ROM is indexed by TS, it outputs whichever decode the sequencer word depends on there:

| EXECUTE TS | Sequencer decode | Use |
|---|---|---|
| 3 | `IR_OPR_HLT` | HLT capture |
| 4 | `IR_IS_CAF` | CAF system initialization |
| other | 0 | the sequencer word depends on no instruction decode |

Two IR values share a variant only when they produce the same datapath words for every condition value in that TS. The current specification needs 6, 26, 12, and 12 variants in EXECUTE TS1 to TS4, within the 32 that `VARIANT` allows. A single variant code shared by all four timing states would need far more than 32 values, which is why the mapping ROM is indexed by TS.

The instruction-dependent conditions that select behavior within a case, such as OPR micro-operation bits and memory-extension decodes, are absorbed into the variant. Only runtime conditions reach the address through the overlay.

### 5.4 Mapping Register and EXECUTE Selection

#### 5.4.1 Mapping Register

`MAPR` is an 8-bit register that captures the mapping ROM output at every main-sequence TP (TP1 to TP4). It is defined in [Registers](../01-architecture/01-registers.md#mapr--mapping-register). During TS *n*, `MAPR` holds the mapping ROM entry for EXECUTE TS *n* of the current IR:

| `MAPR` bits | Field |
|---|---|
| `MAPR[4:0]` | variant |
| `MAPR[6:5]` | overlay group |
| `MAPR[7]` | sequencer decode |

`MAPR` does not load at the console timing pulse (TPC).

#### 5.4.2 EXECUTE Selection

The slice and overlay address inputs are formed from `MAPR` in EXECUTE and from fixed sources otherwise:

| Signal | `MS_EFF_IS_EXECUTE = 1` | `MS_EFF_IS_EXECUTE = 0` |
|---|---|---|
| `VARIANT` | `MAPR[4:0]` | 0 |
| `DP_OVL_SEL` | `MAPR[6:5]` | 1 (the state group, section 6.1) |
| `IR_SEQ` | `MAPR[7]` | `IR_INDIRECT` |

`VARIANT` is formed by five AND gates; `DP_OVL_SEL` and `IR_SEQ` by three sections of a quad 2:1 multiplexer selected by `MS_EFF_IS_EXECUTE`. Like the `MS_EFF` and `SEQ_OVL` multiplexers, this is address formation: it selects which inputs reach the address and evaluates no condition.

`IR_INDIRECT` is taken from its predecode gates on the live IR ([IR-Derived Fields](./10-control-input-definitions/02-ir-derived-fields.md#ir_indirect)), not from `MAPR`. FETCH TS4, where the sequencer selects DEFER or EXECUTE from it, is the one TS whose lookahead entry was formed before IR was loaded at FETCH TP3.

All contexts with `MS_EFF_IS_EXECUTE = 0` (FETCH, DEFER, INTERRUPT, DMA, and halted) therefore share one overlay group, wired as group 1. Its signals must fit `DP_OVL[4:0]`; the current group uses all five bits.

#### 5.4.3 Correctness and Timing

The lookahead entry is correct whenever it is used:

- IR is loaded only at FETCH TP3 ([Major State Timing §9.1](../09-timing/03-major-state-timing.md#91-defer-follows-an-indirect-mri)), and TS always advances from TS *n* to TS *n*+1, so the entry captured at TP *n*−1 is the entry for the current IR and TS. Every EXECUTE TS1 follows a TP4 whose IR is the instruction's IR, whether it was entered from FETCH, DEFER, or a held state.
- A halt commits only at TP4, and while halted TS is held at TS1 and IR is not loaded ([Major State Timing §8.1](../09-timing/03-major-state-timing.md#81-main-timing-while-halted)). `MAPR` therefore holds the TS1 entry of the held instruction until CONTINUE resumes it. Single Step and Single Instruction halt at TP4, so they are covered by the same rule. `MAPR` must not load at TPC, because the held TS is TS1 and an entry captured there would be the TS2 entry.
- `/IO_WAIT` holds only non-TP TSTEPs, so it never loads `MAPR`.
- `MAPR`'s power-on value is undefined. It is not used before the first EXECUTE, which always follows a FETCH TP4, because the power-on reset leaves the processor halted in FETCH ([Timing Terminology §3.4](../09-timing/01-terminology.md#34-power-on-reset)).

Timing: the mapping ROM has a whole TS to settle before the TP that loads `MAPR`. Between a TS boundary or a condition change and a settled control word lie the `MS_EFF`, `MS_EFF_IS_EXECUTE`, selection, and overlay logic and one slice-ROM access.

### 5.5 Datapath Slice Address

```
A14..A12 = MS_EFF
A11..A10 = TS
A9..A5   = VARIANT
A4..A0   = DP_OVL[4:0]
```

### 5.6 Sequencer Slice Address

Address, in every run mode:

```
A14..A12 = MS_EFF
A11..A10 = TS
A9       = HLT_REQ
A8       = FP_STOP
A7..A5   = SEQ_OVL[2:0]
A4       = /DMA_REQ
A3       = IR_SEQ
A2..A0   = 0
```

`SEQ_OVL[2:0]` is a 3-bit 2:1 multiplexer selected by `RUN`:

| `RUN` | `SEQ_OVL[2]` | `SEQ_OVL[1]` | `SEQ_OVL[0]` |
|---|---|---|---|
| 0 (halted) | `FP_CMD[2]` | `FP_CMD[1]` | `FP_CMD[0]` |
| 1 (running) | `FP_SINGLE_INSTRUCTION` | `FP_SINGLE_STEP` | `INTERRUPT_REQUEST_VALID` |

While halted, the running-only inputs cannot change the sequencer word and the front-panel command can; while running, the reverse holds.

### 5.7 Front-Panel Command Path

Console commands are executed only while halted ([Major State Timing §8.2](../09-timing/03-major-state-timing.md#82-console-transaction)), and they reach both slices without passing through `MAPR`.

While `RUN = 0`:

- `MS_EFF = HALTED` (7), so `MS_EFF_IS_EXECUTE = 0` and the EXECUTE selection ignores `MAPR` (section 5.4.2): `VARIANT = 0`, `DP_OVL_SEL = 1`, and `IR_SEQ = IR_INDIRECT`.
- `DP_OVL_SEL = 1` presents the state group, which carries `FP_CMD[2:0]` on `DP_OVL[2:0]` (section 6.2). The datapath slice address is therefore `MS_EFF = 7`, the held `TS`, `VARIANT = 0`, and `DP_OVL = {CIFP, AUTO_INDEX_REQUIRED, FP_CMD}`, which selects the command's datapath word.
- `SEQ_OVL` carries `FP_CMD[2:0]` (section 5.6), which selects the command's sequencer word: `RUN_NEXT` for START and CONTINUE, `MS_NEXT` and `MS_LOAD` for START, and `/INITIALIZE` for CLEAR.

No overlay selection depends on the command: being halted alone forces the state group. `MAPR` selects among the other groups only in EXECUTE.

A console transaction commits at TPC, and `MAPR` does not load at TPC (section 5.4.1). `MAPR` therefore keeps the entry it held when the processor halted, across any number of console commands. No console command loads IR, so that entry remains correct for CONTINUE (section 5.4.3). START enters FETCH, which does not use `MAPR`.

The front-panel inputs used while running (`FP_STOP`, `FP_SINGLE_STEP`, and `FP_SINGLE_INSTRUCTION`) reach only the sequencer slice address, `FP_STOP` directly and the other two through `SEQ_OVL` when `RUN = 1`. They do not pass through `MAPR` or the datapath overlay.

---

## 6. Datapath Overlay

![Datapath Overlay](../../diagrams/control/control-store-overlay/export/control-store-overlay.png)

The five overlay bits `DP_OVL[4:0]` are driven by five 4:1 multiplexers, one per bit, all selected by `DP_OVL_SEL[1:0]`. Input *n* of every multiplexer belongs to overlay group *n*, so `DP_OVL_SEL = n` presents group *n* on `DP_OVL[4:0]`. Each group presents the runtime conditions that can change the datapath word in its contexts ([Control Addressing §6.3](./02-control-addressing.md#63-domain-separation)).

### 6.1 Overlay Groups

| Input / `DP_OVL_SEL` | Group | Used in |
|---|---|---|
| 0 | external IOT | external-IOT EXECUTE TS1–TS3; also every EXECUTE variant with no runtime condition |
| 1 | state | `MS_EFF_IS_EXECUTE = 0`: FETCH, DEFER, INTERRUPT, DMA, halted; wired (section 5.4.2) |
| 2 | external IOT TS4 | external-IOT EXECUTE TS4; SRQ |
| 3 | instruction conditions | OPR Group 2 TS1 skip, SKON, ISZ TS4, JMP and JMS TS4 |

### 6.2 Multiplexer Inputs

| Input (group) | `DP_OVL[4]` | `DP_OVL[3]` | `DP_OVL[2]` | `DP_OVL[1]` | `DP_OVL[0]` |
|---|---|---|---|---|---|
| 0 (external IOT) | `IO_WRITE_REQ` | `IO_READ_REQ` | `IO_CLEAR_AC_REQ` | `IOT_WRITE_PENDING` | `IOT_READ_PENDING` |
| 1 (state) | `CIFP` | `AUTO_INDEX_REQUIRED` | `FP_CMD[2]` | `FP_CMD[1]` | `FP_CMD[0]` |
| 2 (external IOT TS4) | `IO_SKIP_REQ` | `IO_CLEAR_AC_REQ` | `IOT_WRITE_PENDING` | `IOT_READ_PENDING` | `/INT_REQ` |
| 3 (instruction conditions) | `SKIP_TAKEN` | `ISZ_SKIP_REQUIRED` | `IF_CHANGE_PENDING` | `IE` | `CIFP` |

Sixteen distinct signals drive all 20 inputs: the 13 runtime conditions and the three `FP_CMD` bits. `CIFP`, `IO_CLEAR_AC_REQ`, `IOT_READ_PENDING`, and `IOT_WRITE_PENDING` each drive two inputs.

The groups and pin assignments are produced by the control-store packer (section 9), which always places the `MS_EFF_IS_EXECUTE = 0` group at input 1. A variant with no runtime condition may use any group, because its datapath words do not depend on `DP_OVL`. Group 2 relies on the TS4 request window ([Major State Timing §5.2.7](../09-timing/03-major-state-timing.md#527-ts4)), which excludes `IO_READ_REQ` and `IO_WRITE_REQ` in TS4.

---

## 7. Control-Word Packing

### 7.1 Hardwired Constants

Constant and instruction-field sources are hardwired in the datapath rather than supplied by value fields: `IF_SRC = 0` (zero), `MA_SRC = 2` (zero), `PC_SRC = 1` (0001), `DF_SRC = 0` (zero), `DF_SRC = 4` (`IR[5:3]`), `DIF_SRC = 1` (zero), and `DIF_SRC = 4` (`IR[5:3]`). A control-store ROM cannot output a value it does not receive on its address, so no control-word field carries an input's value. See [Microarchitectural Control Signals](./20-control-output-definitions/01-microarchitectural-control-signals.md).

### 7.2 Physical Bit Sharing

Fields that never require a value in the same control word share device outputs ([Control Word §5.6](./04-control-word.md#56-physical-bit-sharing)). The current packing:

| Bits | Fields |
|---|---|
| 4 | `ALU_OP`, `DF_SRC` |
| 3 | `AC_SRC`, `DIF_SRC`, `MA_SRC` |
| 3 | `ALU_B_SRC`, `PC_SRC` |
| 2 | `IF_SRC`, `IOT_TRANSFER_VAL`, `L_OP`, `MB_SRC` |
| 1 | `AB_SRC`, `CIFP_VAL`, `MQ_SRC` |
| 1 | `EA_ADDR_SRC`, `IE_VAL` |
| 31 | the remaining 27 fields, unshared: `IDB_SRC` (3 bits), `ALU_A_SRC` and `MDB_SRC` (2 bits each), and 24 one-bit fields |

Total: 45 bits in six devices, three bits spare.

A field shares bits only through wiring. No decoder or gate follows the control store ([Control Addressing §2](./02-control-addressing.md#2-control-address-definition)).

---

## 8. Device Summary

| Function | Devices |
|---|---|
| Mapping ROM | 1 × 28C256 |
| Datapath slice | 6 × 28C256 |
| Sequencer slice | 1 × 28C256 |
| `MS_EFF` select | 3-bit 2:1 multiplexer |
| `SEQ_OVL` select | 3-bit 2:1 multiplexer |
| `MS_EFF_IS_EXECUTE` | comparator for the EXECUTE code |
| `/DMA_GRANT`, `IOT_ACTIVE` | comparator for the DMA code; one AND gate |
| `MAPR` | 8-bit register |
| EXECUTE selection | five AND gates for `VARIANT`; three sections of a quad 2:1 multiplexer for `DP_OVL_SEL` and `IR_SEQ` |
| `FP_CMD` | 8-to-3 priority encoder |
| Datapath overlay | five 4:1 multiplexers |

Total: 8 EEPROMs, plus the register, multiplexers, gates, comparator, and encoder. The `IR_INDIRECT` predecode gates belong to predecode, not to the control store.

---

## 9. Verification

The control-store packer (`tools/rom-generation/control-store-packer`) produces every device image from the maintained specifications and verifies that, for every reachable input state:

- the mapping ROM, overlays, and slices together select the symbolic control word of the applicable execution case
- every field whose Value Required When condition holds has its required value after bit sharing is undone
- no address bit carries an input that the address map does not assign to it in that context

Reachability is defined by the input constraints, IR derivations, timing constraints, and state invariants already used by the symbolic generator and the equivalence analyzer.

The packer forms each address as the hardware does: in EXECUTE TS *n*, `MAPR` holds the mapping ROM image entry at TS *n*−1 (TS4 for TS1) and supplies `VARIANT`, `DP_OVL_SEL`, and `IR_SEQ`; outside EXECUTE, `VARIANT` is 0, `DP_OVL_SEL` is 1, and `IR_SEQ` is `IR_INDIRECT`; the overlay groups supply `DP_OVL`; `SEQ_OVL` follows `RUN`. It then reads the slice images and compares every field whose condition holds.

---

## 10. Open Items

- **Timing:** one slice-ROM access plus the address-formation and overlay logic make up `T_CS`, which must fit within the TS evaluation window ([Timing Architecture §11](../09-timing/02-timing-architecture.md#11-control-word-settling)); the mapping ROM is off this path (section 5.4.3). The control word passes through no pipeline register; immediate-effect signals are windowed by `CW_VALID` and `WR_VALID`. The TSTEP counts per TS are to be set once the parts are chosen.
- **Datapath diagrams:** datapath diagrams that show a control-supplied input on the IF, MA, or PC source multiplexers must show the hardwired constants instead.
- **ALU_B_SRC width:** no micro-operation uses `ALU_B_SRC = AC` (1) or `ALU_B_SRC = PC` (5). Removing both would leave four values (NONE, MB, MQ, FP_SR) and reduce the field from 3 bits to 2, which changes the packing and the overlay diagrams. Deferred until the simulator has validated the control store.
- **Group assignments:** the overlay groups, pin assignments, variant counts, and bit sharing in sections 5 to 7 are the packer's current result. They change when the specifications do; the packer reports them on every run.
