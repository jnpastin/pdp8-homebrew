# Group 1 Execution

## 1. Purpose
  
Defines execution behavior for OPR Group 1 instructions.

This document specifies:

- the OPR pass unit, which performs a Group 1 instruction in one pass
- the IR bits that select each stage of the pass
- when the pass acts

Instruction semantics and encoding details are defined in:

- [Group 1 ISA](../../02-isa/01-group-1.md)

Execution behavior follows:

- [Execution Model](../01-execution-model.md)

---

## 2. Scope
  
Applies when:

```text
IR_IS_OPR = 1
IR_OPR_GROUP1 = 1
```

---

## 3. Execution Model

A Group 1 instruction completes in FETCH and does not enter EXECUTE (`IR_CLASS = 011`, `IR_NO_EXECUTE = 1`).

- In FETCH TS3 the control store selects `OPR_PASS`, which loads AC and L from the OPR pass unit at TP3 ([Fetch & Defer §3.3](../04-fetch-defer.md#33-ts3)).
- The pass unit is combinational. Its stage functions are selected directly by IR bits (section 4), not by the control word; the control store decides only when AC and L load from it ([Design Principles §3.1](../../00-overview/00-design-principles.md#31-resolved-decisions)).
- The instruction completes at FETCH TP4 ([Sequencing and Internal Control §3.1.1](../../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#311-instruction-completion)).

This follows the PDP-8/E, whose OPR operates in one pass in FETCH TS3 and loads AC and L at TP3 (KK8-E): AC goes onto the data path, CLA works by not gating it, a true/complement gate applies CMA, the adder's carry-in is IAC, and an output multiplexer selects no shift, a rotate, or BSW.

---

## 4. OPR Pass

The pass unit computes the 13-bit L·AC result from the pre-TP3 L and AC. Its stages compose in the order of the [Group 1 ISA](../../02-isa/01-group-1.md) §1, and all of them act in the one pass:

| Stage | Function | Selected by |
|---|---|---|
| A: zero gating | AC ← 0 | `IR_OPR_CLA`; also `IR_OPR_MQL` (Group 3) |
| A: zero gating | L ← 0 | `IR_OPR_CLL` |
| B: OR inputs | AC ← AC OR FP_SR (Group 2 OSR, [Group 2 Execution](./02-group2-execution.md)) | `IR_OPR_OSR` |
| B: OR inputs | AC ← AC OR MQ (Group 3 MQA, [Group 3 Execution](./03-group3-execution.md)) | `IR_OPR_MQA` |
| C: true/complement | AC ← NOT AC | `IR_OPR_CMA` |
| C: true/complement | L ← NOT L | `IR_OPR_CML` |
| D: increment | L·AC ← L·AC + 1, as a 13-bit increment: a carry out of AC bit 11 complements L | `IR_OPR_IAC` |
| E: rotate or swap | rotate the 13-bit L·AC right or left once (RAR, RAL), twice (RTR, RTL), or exchange AC[11:6] and AC[5:0] (BSW, L unchanged) | `IR_OPR_RAR`, `IR_OPR_RAL`, `IR_OPR_BSW` |

Stage E's selection follows the [Group 1 ISA](../../02-isa/01-group-1.md) notes 1 to 4:

| `IR_OPR_RAR` | `IR_OPR_RAL` | `IR_OPR_BSW` | Stage E |
|---|---|---|---|
| 0 | 0 | 0 | none |
| 1 | 0 | 0 | RAR |
| 0 | 1 | 0 | RAL |
| 1 | 0 | 1 | RTR |
| 0 | 1 | 1 | RTL |
| 0 | 0 | 1 | BSW |
| 1 | 1 | either | none (note 4: no rotate or swap; the other stages still act) |

Each stage's control is its IR bit qualified by the class: `IR_OPR_CLA` by `IR_CLASS` = 011, 100, or 101, `IR_OPR_OSR` by 100, `IR_OPR_MQA` and `IR_OPR_MQL` by 101, and the others by 011. The unit also has an MQ output, used only by Group 3 ([Group 3 Execution §4](./03-group3-execution.md#4-opr-pass)). Stage B (the OR inputs) belongs to Groups 2 and 3 and is not selected by a Group 1 instruction.

When `OPR_PASS` is not selected, AC and L do not load from the pass unit, so its output has no effect.

---

## 5. Composition Rules

- All stages act in one pass, at FETCH TP3; they compose in the order A, C, D, E
- AC and L are each loaded once, at that TP
- No two μops write AC or L in the same TS

---

## 6. Notes

- The stage controls come from IR bits; the control word carries only `OPR_PASS` (`AC_SRC` = OPR pass unit, `L_OP` = OPR pass unit link)
- No symbolic instruction interpretation is used
