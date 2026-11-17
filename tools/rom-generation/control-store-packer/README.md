# Control-Store Packer

## 1. Purpose

The control-store packer realizes the promoted symbolic control words in the control store organization of [Control Store Organization](../../../docs/04-control/08-control-store-organization.md): a mapping ROM, a datapath slice, and a sequencer slice, each addressed by 15 bits. It:

- groups instructions into EXECUTE variants
- packs the datapath's runtime conditions into overlay groups
- chooses the instruction decode the sequencer's `IR_SEQ` bit carries in each timing state
- allocates datapath control bits, sharing bits between fields that never require a value in the same word
- fills the logical image of every device
- verifies the images end to end against the symbolic words

The images are logical. They are written to the build directory for review and are not promoted; the shared README, section 13, governs physical images.

## 2. Inputs

From `rom/microcode/v1/`:

| File | Used for |
|---|---|
| `control-input-schema.json` | input domains, IR derivations, input constraints |
| `control-word-schema.json` | encoded fields, widths, octal encodings, defaults, Value Required When conditions |
| `symbolic-control-words.json` | each execution case's base context, guarded assignments, and defaults |
| `timing-constraints.json` | timing constraints and state invariants |

A symbolic assignment that takes its value from an input (`value_from_input`) is an error: a ROM cannot output a value it does not receive on its address ([Control Store Organization §7.1](../../../docs/04-control/08-control-store-organization.md#71-hardwired-constants)).

## 3. Method

### 3.1 Contexts

A context is what the control store sees apart from the instruction and the runtime inputs: each running major state and timing state (`MS_EFF` = the `MS` code, `RUN = 1`), and the halted pseudo-state (`MS_EFF = 7`, `RUN = 0`). While halted, `MS` and `TS` are not on the address, so the packer enumerates them and requires that no word depends on them.

### 3.2 Behaviors

For each context and each IR value, the packer selects the execution cases whose base context can hold. IR values are grouped when they agree on every IR-derived input that those cases compare **and** every IR-derived input a constraint or invariant mentions; the second condition keeps unreachable IR values, such as `IR_INDIRECT = 0` in DEFER, apart from reachable ones.

For each group it enumerates the runtime inputs the undecided guards and base contexts still compare. A combination is reachable unless it sets both inputs of an exclusive pair to 1 or violates a timing constraint or invariant. For each reachable combination it records the slice's word and the fields whose Value Required When condition holds. A context with no reachable combination at all is an error, so that nothing passes verification vacuously.

### 3.3 Dependence

The packer greedily drops each input whose removal leaves the required words consistent: two combinations that agree on the remaining inputs must require the same value for every field both require. The six front-panel commands count as one signal, `FP_CMD`.

- **Datapath:** in EXECUTE, IR groups with identical required words over identical inputs share a variant. Outside EXECUTE the word must not depend on IR, because the EXECUTE selection presents `VARIANT = 0` there.
- **Sequencer:** the inputs must be among `HLT_REQ`, `FP_STOP`, `/DMA_REQ`, and `SEQ_OVL` (the running-only inputs while running, `FP_CMD` while halted). In EXECUTE, its IR dependence must reduce to one of `IR_INDIRECT`, `IR_OPR_HLT`, `IR_IS_CAF` per timing state; that decode becomes the mapping entry's `IR_SEQ` bit. Outside EXECUTE, `IR_SEQ` is wired to `IR_INDIRECT`, so the word may depend on no other decode (`NON_EXECUTE_IR_SEQ`).

### 3.4 Mapping ROM

The mapping ROM is addressed by `IR` and the current timing state (A0 wired 0) and is evaluated one timing state ahead: the entry at TS *n* holds the EXECUTE `VARIANT`, overlay group, and `IR_SEQ` decode for TS *n*+1, and the entry at TS4 holds TS1's. The mapping register `MAPR` captures it at each main-sequence TP. Outside EXECUTE (`MS_EFF_IS_EXECUTE = 0`), the slices see `VARIANT = 0`, overlay group 1, and `IR_SEQ = IR_INDIRECT` instead ([Control Store Organization §5.4](../../../docs/04-control/08-control-store-organization.md#54-mapping-register-and-execute-selection)).

### 3.5 Overlay Groups

Each EXECUTE variant needs a set of overlay signals of at most 5 bits (`FP_CMD` takes 3). All contexts outside EXECUTE share one set, because they share the one wired group; it must also fit in 5 bits. The sets are packed first-fit, largest first, into at most four groups, and the groups are then renumbered so that the non-EXECUTE group is group 1. `FP_CMD`, when present, occupies bits 0–2; other signals follow in name order.

### 3.6 Bit Allocation

Two datapath fields conflict when some reachable word requires both. Fields are placed, widest first, into the first shared slot that is wide enough and holds no conflicting field. Slots are laid out from bit 0.

## 4. Verification

For every reachable combination of every context, the packer forms the addresses as the hardware does:

- in EXECUTE TS *n*, the mapping ROM image entry at `IR` and TS *n*−1 (TS4 for TS1), as `MAPR` holds it, gives `VARIANT`, `DP_OVL_SEL`, and `IR_SEQ`; outside EXECUTE, the fixed values and `IR_INDIRECT` do. IR values with the same entry address the slices identically, so each distinct entry is checked once
- the selected overlay group gives `DP_OVL`
- `SEQ_OVL` follows `RUN`

An input on the address that the combination does not compare can take any value in hardware, such as `/DMA_REQ` in a timing state that ignores DMA requests. Every value of it is checked, so the images must hold the word at all of them. The image writer fills those addresses the same way.

The packer then reads the datapath and sequencer images, unpacks every field whose condition holds, and compares it with the required value. Any difference is a `VERIFICATION_MISMATCH` error.

## 5. Outputs

Under `build/simulation_outputs/rom-generation/control-store-packer/`:

| File | Contents |
|---|---|
| `control-store-packing.json` | summary, address maps, mapping ROM fields and `IR_SEQ` decodes, overlay groups, EXECUTE variants, datapath and sequencer layouts |
| `images/mapping.hex`, `images/datapath-0.hex` to `datapath-5.hex`, `images/sequencer.hex` | one byte per line, two hex digits, 32768 lines, address 0 first |
| `packing-report.txt` | status, summary, groups, variants, layouts, diagnostics |

`datapath-0` holds datapath bits 0–7, `datapath-1` bits 8–15, and so on. Addresses that no reachable state uses hold the default word.

Earlier outputs are removed first. The packing and images are written only when no error is found.

## 6. Diagnostics

| Code | Meaning |
|---|---|
| `INPUT_SUPPLIED_VALUE` | a symbolic assignment takes an input's value |
| `UNKNOWN_ENCODING`, `INVALID_ASSIGNMENT`, `INVALID_CARE_CONDITION` | a value or condition cannot be interpreted |
| `IR_DERIVATION_UNUSABLE`, `MISSING_INPUT`, `MISSING_IR_DECODE`, `MISSING_SEQUENCER_FIELD`, `MS_CODE_CONFLICT` | an input the organization relies on is missing or unusable |
| `NO_REACHABLE_STATE` | a context has no reachable input state |
| `CASE_OVERLAP`, `CONFLICTING_ASSIGNMENTS` | the symbolic words are ambiguous for some state |
| `INVISIBLE_DEPENDENCY` | a word depends on an input its address does not carry |
| `NON_EXECUTE_IR_DEPENDENCE` | the datapath word depends on IR outside EXECUTE |
| `SEQUENCER_IR_DEPENDENCE`, `IR_SEQ_TOO_WIDE` | the sequencer word needs IR information beyond one decode per timing state |
| `NON_EXECUTE_IR_SEQ` | outside EXECUTE, the sequencer word needs a decode other than `IR_INDIRECT` |
| `VARIANT_OVERFLOW`, `OVERLAY_TOO_WIDE`, `OVERLAY_GROUP_OVERFLOW`, `DATAPATH_TOO_WIDE` | the organization's field widths are exceeded |
| `VERIFICATION_MISMATCH` | an image disagrees with a required value |

## 7. Command Line

```text
python tools/rom-generation/control-store-packer/src/pack_control_store.py --repo-root .
```

| Option | Default |
|---|---|
| `--artifacts` | `rom/microcode/v1` |
| `--packing-output` | `build/.../control-store-packer/control-store-packing.json` |
| `--report-output` | `build/.../control-store-packer/packing-report.txt` |
| `--images-output` | `build/.../control-store-packer/images` |

Exit status is 0 on success and 1 on any error. A run over the current specifications takes under ten seconds.

## 8. Testing

```text
python -m unittest discover -s tools/rom-generation/control-store-packer/tests -p "test_*.py"
```

Tests build a small machine inline and do not read the real specifications. They cover encodings, care conditions, dependence, overlay packing, bit allocation, address maps, end-to-end packing and verification, images that hold a word at every value of an input it ignores, detection of a corrupted image (including at such a value), and every structural error.
