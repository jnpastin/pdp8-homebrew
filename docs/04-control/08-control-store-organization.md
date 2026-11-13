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
| sequencer slice | the slice producing `MS_NEXT`, `MS_LOAD`, `RUN_NEXT`, `HLT_REQ_NEXT`, `/DMA_GRANT`, and `/INITIALIZE` (section 4.1) |
| datapath slice | the slice producing every encoded field except the sequencer fields (section 4.2) |
| first-level stage | ROM devices inside the control store that map IR and TS to the instruction-dependent part of the slice addresses ([Control Addressing §2.1](./02-control-addressing.md#21-partitioned-and-two-level-control-stores)) |
| `MS_A` | the 3-bit major-state code presented to the control store: `MS` while running, code 7 while halted (section 5.1); the `MS` register itself is unchanged |
| `E` | 1 when `MS_A` is EXECUTE (code 2), else 0; an address input of the first-level stage |
| `VARIANT` | a 5-bit first-level output identifying the instruction-dependent behavior that applies in the current TS of EXECUTE |
| overlay | an address field that carries different condition inputs in different contexts ([Control Addressing §6.3](./02-control-addressing.md#63-domain-separation)) |
| overlay group | one fixed assignment of condition inputs to `OVL[4:0]` |
| `OVL[4:0]` | the datapath slice's 5-bit overlay field |
| `OVL_SEL` | a 3-bit first-level output selecting which overlay group drives `OVL[4:0]` (section 6) |
| `IR_SEQ` | the 3-bit first-level output carrying the instruction decodes the sequencer slice needs: `IR_INDIRECT`, `IR_OPR_HLT`, `IR_IS_CAF` |
| `FP_CMD[2:0]` | the encoded front-panel command (section 5.2) |
| 28C256 | a parallel EEPROM with 15 address bits and 8 data bits (32K × 8) |

Status: the slice structure, device technology, and packing rules are design decisions. The specific address-bit assignments, variant counts, and overlay groups are the current proposal, measured from the maintained specifications; the packing tool will finalize and verify them.

---

## 2. Design Constraints

| Constraint | Consequence |
|---|---|
| Control logic is discrete: memory devices and 74-series logic only; no PAL, GAL, CPLD, or FPGA | Every function wider than a few gates is a ROM lookup; glue is limited to multiplexers, encoders, and latches |
| Control-store devices are parallel EEPROMs (28C256 class: 15 address bits, 8 data bits) | Each slice address is at most 15 bits; each device supplies 8 control-word bits |
| Device count matters but is not the primary concern | Control-word width, not address depth, sets the device count; width is reduced where it costs no logic |

The control store is sparse: most addresses are unreachable or repeat another address's word. Sparsity is permitted ([Control Addressing §7.2](./02-control-addressing.md#72-sparsity)).

---

## 3. Overview

![Control Store Organization](../../diagrams/control/control-store-organization/export/control-store-organization.png)

Signal flow:

- `MS` and `RUN` form `MS_A`; `MS_A` is decoded to `E`.
- The first-level stage reads `IR`, `TS`, and `E`, and produces `VARIANT`, `OVL_SEL`, and `IR_SEQ`.
- The overlay multiplexers present the runtime conditions or `FP_CMD` selected by `OVL_SEL` on `OVL[4:0]`.
- The datapath slice reads `MS_A`, `TS`, `VARIANT`, and `OVL[4:0]`.
- The sequencer slice reads `MS_A`, `TS`, the sequencer inputs (with `FP_CMD` in place of the running-only inputs while halted), and `IR_SEQ`.

---

## 4. Slices

The control store is partitioned into two slices ([Control Addressing §2.1](./02-control-addressing.md#21-partitioned-and-two-level-control-stores)). Every encoded control-word field is produced by exactly one slice.

### 4.1 Sequencer Slice

Fields:

```
MS_NEXT, MS_LOAD, RUN_NEXT, HLT_REQ_NEXT, /DMA_GRANT, /INITIALIZE
```

These fields depend on the same small set of inputs in every major state: run control, halt and front-panel inputs, the interrupt and DMA requests, and three instruction decodes. Separating them keeps those inputs out of the datapath slice address.

Width: 8 bits, one device.

### 4.2 Datapath Slice

Fields: every other encoded field of the control word, including the external-IOT transfer and interface fields.

Width: 46 bits after packing (section 7), six devices.

---

## 5. Address Formation

### 5.1 Major-State Code

`MS` uses five of its eight codes (`FETCH = 0`, `DEFER = 1`, `EXECUTE = 2`, `INTERRUPT = 3`, `DMA = 4`). The control store sees:

```
MS_A = 7    if RUN = 0
MS_A = MS   otherwise
```

realized by one 74HC157. Code 7 is the halted pseudo-state; no separate `RUN` address bit is needed.

`MS` itself is not changed while halted. It keeps the held major state, because CONTINUE resumes at TS1 of the held state ([Major State Timing §8.1](../09-timing/03-major-state-timing.md#81-main-timing-while-halted)), and because the DMA arbiter observes `MS` directly. Only the control store sees code 7.

The substitution loses no information the control store needs: while halted, no control word depends on which major state is held, and while running, `MS_A = MS`. It replaces a `RUN` address bit that would not fit in the 15-bit datapath slice address.

`E` is produced by a 74HC138 decoding `MS_A`; its EXECUTE output is `E`, and its other outputs are available for other major-state decodes.

### 5.2 Front-Panel Command Code

Console commands are accepted at most one at a time ([External Inputs §4.1](./10-control-input-definitions/04-external-inputs.md#41-console-command-acceptance)). A 74HC148 encodes them into `FP_CMD[2:0]`:

| `FP_CMD` | Command |
|---|---|
| 0 | none |
| 1 | `FP_START` |
| 2 | `FP_CONTINUE` |
| 3 | `FP_CLEAR` |
| 4 | `FP_LOAD_ADDRESS` |
| 5 | `FP_EXAMINE` |
| 6 | `FP_DEPOSIT` |

### 5.3 First-Level Stage

A first-level stage ([Control Addressing §2.1](./02-control-addressing.md#21-partitioned-and-two-level-control-stores)) maps the instruction to the address information each slice needs.

Address (both devices):

```
A14..A3 = IR[11:0]
A2..A1  = TS
A0      = E
```

Outputs:

| Output | Width | Meaning |
|---|---|---|
| `VARIANT` | 5 | the instruction-dependent behavior that applies in this TS of EXECUTE; a fixed value when `E = 0` |
| `OVL_SEL` | 3 | the overlay group presented to the datapath slice (section 6) |
| `IR_SEQ` | 3 | `IR_INDIRECT`, `IR_OPR_HLT`, `IR_IS_CAF` for the sequencer slice |
| spare | 5 | unassigned |

Two IR values share a variant only when they produce the same datapath words for every condition value in that TS. The current specification needs at most 26 variants in one TS (EXECUTE TS2), within the 32 that `VARIANT` allows. A single variant code shared by all four timing states would need 227 values, which is why the stage is indexed by TS.

The instruction-dependent conditions that select behavior within a case, such as OPR micro-operation bits and memory-extension decodes, are absorbed into the variant. Only runtime conditions reach the address through the overlay.

### 5.4 Datapath Slice Address

```
A14..A12 = MS_A
A11..A10 = TS
A9..A5   = VARIANT
A4..A0   = OVL[4:0]
```

### 5.5 Sequencer Slice Address

While running (`MS_A ≠ 7`):

```
A14..A12 = MS_A
A11..A10 = TS
A9       = HLT_REQ
A8       = FP_STOP
A7       = FP_SINGLE_INSTRUCTION
A6       = FP_SINGLE_STEP
A5       = INTERRUPT_REQUEST_VALID
A4       = /DMA_REQ
A3..A1   = IR_SEQ
A0       = 0
```

While halted (`MS_A = 7`), the running-only inputs are replaced by the front-panel command:

```
A7..A5   = FP_CMD[2:0]
```

realized by one 74HC157 on A7..A5 selected by `RUN`.

---

## 6. Datapath Overlay Groups

The five overlay bits `OVL[4:0]` are driven through five 74HC151 multiplexers selected by `OVL_SEL`. Each group presents the runtime conditions that can change the datapath word in its contexts ([Control Addressing §6.3](./02-control-addressing.md#63-domain-separation)).

| `OVL_SEL` | Group | Used in | `OVL[4:0]` |
|---|---|---|---|
| 0 | none | contexts with no runtime condition | — |
| 1 | state | FETCH, DEFER, INTERRUPT, DMA, halted | `FP_CMD[2:0]`, `CIFP`, `AUTO_INDEX_REQUIRED` |
| 2 | skip | OPR Group 2 TS1 | `SKIP_TAKEN` |
| 3 | interrupt | SKON, SRQ | `IE`, `/INT_REQ` |
| 4 | ISZ | ISZ TS4 | `ISZ_SKIP_REQUIRED` |
| 5 | field change | JMP, JMS TS4 | `CIFP`, `IF_CHANGE_PENDING` |
| 6 | external IOT TS1–TS3 | external-IOT EXECUTE | `IO_CLEAR_AC_REQ`, `IO_READ_REQ`, `IO_WRITE_REQ`, `IOT_READ_PENDING`, `IOT_WRITE_PENDING` |
| 7 | external IOT TS4 | external-IOT EXECUTE TS4 | `IO_CLEAR_AC_REQ`, `IO_SKIP_REQ`, `IOT_READ_PENDING`, `IOT_WRITE_PENDING` |

Unused overlay bits in a group are driven low. Group 7 relies on the TS4 request window ([Major State Timing §5.2.7](../09-timing/03-major-state-timing.md#527-ts4)), which excludes `IO_READ_REQ` and `IO_WRITE_REQ` in TS4.

---

## 7. Control-Word Packing

### 7.1 Hardwired Constants

Constant sources are hardwired in the datapath rather than supplied by value fields: `IF_SRC = 0` (zero), `MA_SRC = 2` (zero), `PC_SRC = 1` (0001). See [Microarchitectural Control Signals](./20-control-output-definitions/01-microarchitectural-control-signals.md).

### 7.2 Physical Bit Sharing

Fields that never require a value in the same control word share device outputs ([Control Word §5.6](./04-control-word.md#56-physical-bit-sharing)). The current packing:

| Bits | Fields |
|---|---|
| 4 | `ALU_OP`, `DF_VAL` |
| 3 | `AC_SRC`, `DIF_VAL`, `MA_SRC` |
| 3 | `ALU_B_SRC`, `DF_SRC` |
| 2 | `ALU_A_SRC`, `DIF_SRC` |
| 2 | `IF_SRC`, `IOT_TRANSFER_VAL`, `L_OP`, `MB_SRC` |
| 1 | `AB_SRC`, `CIFP_VAL`, `MQ_SRC` |
| 1 | `EA_ADDR_SRC`, `IE_VAL` |
| 1 | `II_VAL`, `PC_SRC` |
| 29 | the remaining fields, one bit each |

Total: 46 bits in six devices, two bits spare.

A field shares bits only through wiring. No decoder or gate follows the control store ([Control Addressing §2](./02-control-addressing.md#2-control-address-definition)).

---

## 8. Device Summary

| Function | Devices |
|---|---|
| First-level stage | 2 × 28C256 |
| Datapath slice | 6 × 28C256 |
| Sequencer slice | 1 × 28C256 |
| Major-state code and sequencer halted overlay | 2 × 74HC157 |
| `E` decode | 1 × 74HC138 |
| Front-panel command encoder | 1 × 74HC148 |
| Datapath overlay | 5 × 74HC151 |

Total: 9 EEPROMs and 9 logic devices.

The second first-level device exists for `IR_SEQ` and has five spare outputs. Section 10 lists ways to remove it.

---

## 9. Verification

The ROM-generation tools produce every device image from the maintained specifications and must verify that, for every reachable input state:

- the first-level stage, overlays, and slices together select the symbolic control word of the applicable execution case
- every field whose Value Required When condition holds has its required value after bit sharing is undone
- no address bit carries an input that the address map does not assign to it in that context

Reachability is defined by the input constraints, IR derivations, timing constraints, and state invariants already used by the symbolic generator and the equivalence analyzer.

---

## 10. Open Items

- **Timing:** EEPROM access time plus the first-level stage and overlay must fit within the TS evaluation window ([Control Addressing §9](./02-control-addressing.md#9-timing-model)). Whether the control word passes through a pipeline register is not yet defined.
- **Power-on state:** the TSEQ, MS, and RUN power-on state is not yet defined ([Timing Terminology](../09-timing/01-terminology.md)); every device image must define the reset address's word once it is.
- **Diagrams:** datapath diagrams that show a control-supplied input on the IF, MA, or PC source multiplexers must show the hardwired constants instead.
- **Group assignments:** the overlay groups and variant counts in sections 5 and 6 come from the current specification and may change when the packing tool assigns them.
- **Second first-level device:** two ways may remove it, bringing the total to 8 EEPROMs:
  - Each timing state appears to need at most one of the three `IR_SEQ` decodes (`IR_INDIRECT` in FETCH TS4, `IR_OPR_HLT` in EXECUTE TS3, `IR_IS_CAF` in EXECUTE TS4). Because the first-level stage is indexed by TS and `E`, it could output a single bit carrying whichever decode applies, which also frees two sequencer address bits. That bit fits in one device only if `VARIANT` and `OVL_SEL` together shrink to 7 bits, for example by merging overlay groups so that `OVL_SEL` needs 2 bits.
  - Generating `IR_SEQ` with gates instead, at the cost of about three logic devices.

  The packing tool will determine whether the first option fits.
