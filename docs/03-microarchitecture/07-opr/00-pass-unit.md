# OPR Pass Unit

## 1. Purpose

Defines the combinational unit that performs the register operations of every OPR instruction in one pass, at FETCH TP3. Each group's use of it is defined in [Group 1](./01-group1-execution.md#4-opr-pass), [Group 2](./02-group2-execution.md#4-opr-pass), and [Group 3](./03-group3-execution.md#4-opr-pass) Execution. Circuit realization and propagation delay belong to the implementation documents.

## 2. Structure

```text
                 AC                                      L
                 |                                       |
                 +-------> skip logic <------------------+
                 |             |                         |
                 |             v                         |
                 |           SKIP                        |
                 |                                       |
                 +-------> MQ output --> MQ              |
                 |         (also reads MQ, and CLA)      |
                 v                                       v
           A: clear AC                              A: clear L
           (CLA or MQL)                               (CLL)
                 |                                       |
                 v                                       |
           B: OR FP_SR (OSR)                             |
              OR MQ    (MQA)                             |
                 |                                       |
                 v                                       v
           C: complement AC                         C: complement L
                 (CMA)                                 (CML)
                 |                                       |
                 v                                       v
           D: 13-bit increment of L and AC together (IAC)
                 |                                       |
                 v                                       v
           E: 13-bit rotate, or BSW of AC with L unchanged
                 |                                       |
                 v                                       v
             AC input                                 L input
```

The stages act in the order A to E, in one pass.

- **Skip logic:** beside the unit, not a stage of it. It reads AC and L as held before TP3, so it never sees a stage's result. Group 2 loads its decision into `SKIP`, which increments PC at FETCH TP4 ([Skip Model §12](../../08-interrupts-and-skip/05-skip-model.md#12-skip-state)).
- **MQ output:** reads AC and MQ as held before TP3. With MQL it applies CLA itself: the output is 0 if CLA is set, and AC otherwise. Without MQL it is MQ, so the load leaves MQ unchanged.
- **Stage E:** RAR or RAL rotates once, or twice with BSW (RTR, RTL); BSW alone exchanges AC[11:6] and AC[5:0]. RAR with RAL selects no rotate or swap, while the other stages still act ([Group 1 ISA](../../02-isa/01-group-1.md) note 4).
- **HLT** is not part of the unit: the sequencer captures it at FETCH TP3 ([Group 2 Execution §6](./02-group2-execution.md#6-hlt)).

## 3. Interfaces

| Input | Enters at |
|---|---|
| AC | stage A; also the MQ output and the skip logic |
| L | stage A; also the skip logic |
| MQ | stage B (MQA); also the MQ output |
| FP_SR | stage B (OSR) |
| IR bit decodes, each qualified by `IR_CLASS` | the selection of every stage (section 4) |

A stage's result feeds the next stage, so AC and L reach stages C, D, and E through the stages before them.

| Output | Loads | Selected by | When |
|---|---|---|---|
| AC result | AC | `OPR_PASS` | FETCH TP3, every OPR |
| L result | L | `OPR_PASS` | FETCH TP3, every OPR |
| MQ result | MQ | `OPR_PASS_TO_MQ` | FETCH TP3, Group 3 |
| skip decision (`OPR_SKIP_REQ`) | SKIP | `OPR_SKIP_REQ_TO_SKIP` | FETCH TP3, Group 2 |

## 4. Stage Selection

Each stage is selected by its IR bit, qualified by the instruction's class (`IR_CLASS`). The stages compose in the order of the [Group 1 ISA](../../02-isa/01-group-1.md) §2:

| Stage | Function | Selected by |
|---|---|---|
| A: zero gating | AC ← 0 | `IR_OPR_CLA`; also `IR_OPR_MQL` (Group 3) |
| A: zero gating | L ← 0 | `IR_OPR_CLL` |
| B: OR inputs | AC ← AC OR FP_SR (Group 2 OSR) | `IR_OPR_OSR` |
| B: OR inputs | AC ← AC OR MQ (Group 3 MQA) | `IR_OPR_MQA` |
| C: true/complement | AC ← NOT AC | `IR_OPR_CMA` |
| C: true/complement | L ← NOT L | `IR_OPR_CML` |
| D: increment | L·AC ← L·AC + 1, as a 13-bit increment: a carry out of AC bit 11 complements L | `IR_OPR_IAC` |
| E: rotate or swap | rotate the 13-bit L·AC right or left once (RAR, RAL), twice (RTR, RTL), or exchange AC[11:6] and AC[5:0] (BSW, L unchanged) | `IR_OPR_RAR`, `IR_OPR_RAL`, `IR_OPR_BSW` |

Stage E's selection is given in [Group 1 Execution §4](./01-group1-execution.md#4-opr-pass). The qualification by class:

| Stage | Group 1 (`011`) | Group 2 (`100`) | Group 3 (`101`) |
|---|---|---|---|
| A | CLA, CLL | CLA | CLA, MQL |
| B | none | OSR | MQA |
| C | CMA, CML | none | none |
| D | IAC | none | none |
| E | rotates, BSW | none | none |

## 5. Effect on Each Group

| Part | Group 1 | Group 2 | Group 3 |
|---|---|---|---|
| A, AC | CLA | CLA | CLA or MQL |
| A, L | CLL | passes L | passes L |
| B | passes | OSR | MQA |
| C | CMA, CML | passes | passes |
| D | IAC | passes | passes |
| E | rotates, BSW | passes | passes |
| MQ output | not loaded | not loaded | MQL: AC, or 0 with CLA. Otherwise MQ |
| Skip logic | not loaded | loads SKIP | not loaded |

## 6. Examples

| Instruction | Before | Through the unit | After TP3 |
|---|---|---|---|
| CMA IAC (7041) | AC = 1354, L = 0 | C gives 6423, D gives 6424 | AC = 6424 |
| CLA IAC (7201) | AC = 7070 | A gives 0000, D gives 0001 | AC = 0001 |
| CLA SZA (7640) | AC = 0000 | skip logic sees 0000; A gives 0000 | SKIP = 1, AC = 0000 |
| CLA OSR (7604) | AC = 7070, FP_SR = 0123 | A gives 0000, B gives 0123 | AC = 0123 |
| SWP (7521) | AC = 1111, MQ = 2222 | A clears the AC path, B gives 2222, MQ output gives 1111 | AC = 2222, MQ = 1111 |
| CLA MQL (7621) | AC = 1111, MQ = 2222 | A gives 0000; MQ output gives 0 | AC = 0000, MQ = 0000 |

## 7. Invariants

- The unit holds no state.
- Every input is the value held before TP3. All outputs commit together at TP3.
- IR bits select what each stage does. The control store selects only whether the results load (`OPR_PASS`, `OPR_PASS_TO_MQ`, `OPR_SKIP_REQ_TO_SKIP`), as it does for every register load ([Control Model §8.4](../../04-control/01-control-model.md#84-realizations-outside-the-control-word)).
- A stage that is not selected passes its input unchanged.
