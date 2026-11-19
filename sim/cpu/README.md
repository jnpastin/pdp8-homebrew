# CPU Simulator

## 1. Purpose

Simulates the CPU from its packed control-store images, one timing state (TS) at a time, to validate the documentation, the ROM-generation tools, the packer, and the images before hardware is built.

The simulator reads the images; it never regenerates control words from the symbolic artifacts. Every behavior it models cites the document that defines it. Where the documents are silent or inconsistent, it raises `SpecGap` instead of choosing a behavior.

Status: milestones M0 (images, address formation, power-on, console transactions), M1 (instruction execution, checked end to end by `sim/system/tests/test_instructions.py`), and M2 (lock-step comparison with the [reference model](../reference/README.md)) are complete. In M3, MAINDEC-8E-D0AB and D0BB pass in lock-step; the remaining phase-1 diagnostics follow.

## 2. Inputs

| Input | Source |
|---|---|
| Logical images `mapping.hex`, `datapath-0.hex` … `datapath-5.hex`, `sequencer.hex` | `build/simulation_outputs/rom-generation/control-store-packer/images/` (run the ROM-generation pipeline to create them) |
| Packing description: datapath and sequencer bit layouts, overlay-group pin assignments | `build/simulation_outputs/rom-generation/control-store-packer/control-store-packing.json` |
| Field encodings, checked at startup | `rom/microcode/v1/control-word-schema.json` |

The packing description supplies only the physical wiring the packer chose. A field narrower than its shared bits occupies their low-order end ([Control Store Organization §7.2](../../docs/04-control/08-control-store-organization.md#72-physical-bit-sharing)). Address formation, mapping-register fields, and command codes are coded from the documentation and only cross-checked against the packing description.

## 3. Modules

All modules are in `src/pdp8_cpu/`.

| Module | Models | Documentation |
|---|---|---|
| `encodings.py` | control-word field encodings; check against the schema | Microarchitectural Control Signals §5, Architectural Control Signals §4, Sequencing Control Signals §4 |
| `images.py` | image loading, validation, word decoding as wired | Control Store Organization §4, §7; packer README §5 |
| `state.py` | registers, power-on | Registers; Timing Terminology §3.4 |
| `inputs.py` | IR decodes, primitive and derived flags, external inputs | Control Input Definitions |
| `address.py` | `MS_EFF`, `TS_CODE`, mapping register selection, overlays, slice addresses | Control Store Organization §5, §6 |
| `derived.py` | `/DMA_GRANT`, `IOT_ACTIVE`, `/INITIALIZE` condition, and their cross-checks | Control Store Organization §5.1; Architectural Control Signals §4.5, §4.8, §4.9; Interface and Ownership Direct Control §5, §7 |
| `datapath.py` | ALU, IDB, EA formation, register inputs, memory and DB strobes | Microarchitectural Control Signals §5, §7, §11; Read/Write Protocol |
| `sequencer.py` | `MS`, `RUN`, `HLT_REQ` commits; TS advance | Sequencing Control Signals; Major State Timing §8.1 |
| `console.py` | front-panel switches, command latch | External Inputs §4.1; Control Store Organization §5.2 |
| `cpu.py` | one main-sequence TS or one console transaction | Major State Timing §8.2; Control Store Organization §5.4 |

## 4. Method

### 4.1 One Timing State

1. Form `MS_EFF`, the mapping-register selection, the overlay group, and both slice addresses from the state committed at the previous TP.
2. Read the datapath and sequencer words and evaluate the datapath. Evaluation starts from the enabled operations, so a select field is interpreted only when its operation is enabled (Control Word §5.6, §8.2).
3. Commit every load, the memory write, and the sequencer results together at the TP. At TP1–TP4, `MAPR` loads the mapping-ROM entry addressed by the pre-TP IR and the current TS; it never loads at the console TP (TPC).

A console command is accepted only while halted and runs as one console transaction with `MS_EFF = HALTED` and the held TS1, committing at TPC.

### 4.2 Undefined Values

A register holds UNDEFINED after power-on until loaded (Timing Terminology §3.4), and memory holds UNDEFINED until written. Undefined values propagate through the datapath. When an undefined value reaches a control-store address bit, the simulator evaluates the word at every combination of the undefined bits and requires the effects to agree; otherwise it raises `SpecGap`. An undefined memory address, MAPR in EXECUTE, MS, or RUN is a `SpecViolation`.

### 4.3 Checks

| Check | Error |
|---|---|
| Field encodings match the control-word schema; packing matches the documented slice fields, mapping fields, wired overlay group, and command codes | `ImageError` |
| Reserved encoding of an interpreted field; `/RD` with `/WR`; `/DB_READ` with `/DB_WRITE`; IDB consumed while not driven; MDB consumed or written with no valid driver; CPU drives MDB during a read; `PC_INC` with `PC_LOAD`; `PC_INC` without `ALU_OP = INC`, `ALU_A_SRC = PC`; binary ALU operation with `ALU_B_SRC = NONE`; reserved `MS_NEXT`; halt at a TP other than TP4; datapath and sequencer loading the same register | `SpecViolation` |
| Sequencer `/INITIALIZE` against the Architectural Control Signals §4.9 condition | `SpecViolation` |
| Decoded `/DMA_GRANT` and `IOT_ACTIVE` against the direct-control definitions, in every context reached | `SpecGap` |
| A word whose effect depends on an undefined address input | `SpecGap` |

Each error names the major state, TS, IR, PC, both slice addresses, and the rule.

### 4.4 Not Modelled

TSTEP-level timing (`T_CS`, `CW_VALID`, `WR_VALID`, `/IO_WAIT`, slow cycles). DMA major states are modelled: with a DMA arbiter attached (`Cpu(dma=...)`, [sim/io](../io/README.md) §4), its aggregate `/DMA_REQ` addresses the sequencer, and during DMA the datapath word must release the memory interface (a `SpecViolation` otherwise) while the selected controller's transfer commits at TP2. Single Step halts inside a DMA burst are not yet tested. I/O controllers are separate models attached through the CPU's external-IOT interface ([sim/io](../io/README.md)).

## 5. Known Specification Gaps

None open.

## 6. Testing

```text
python -m unittest discover -s sim/cpu/tests -p "test_*.py"
```

The tests cover the encodings and image validation, address formation (cross-checked against the packer's own address functions), the ALU, the control inputs, the datapath checks, the derived-output checks, power-on, and every console command executed through the console microcode.
