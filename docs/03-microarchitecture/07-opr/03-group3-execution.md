# Group 3 Execution

## 1. Purpose

Defines execution behavior for OPR Group 3 instructions.

This document specifies:

- the Group 3 stages of the OPR pass unit (CLA, MQA, MQL, SWP) and its MQ output
- when the pass acts

Instruction semantics and encoding details are defined in:

- [Group 3 ISA](../../02-isa/03-group-3.md)

Execution behavior follows:

- [Execution Model](../01-execution-model.md)

---

## 2. Scope

Applies when:

```text
IR_IS_OPR = 1
IR_OPR_GROUP3 = 1
```

---

## 3. Execution Model

A Group 3 instruction completes in FETCH and does not enter EXECUTE (`IR_CLASS = 101`, `IR_NO_EXECUTE = 1`).

- In FETCH TS3 ([FETCH and DEFER Execution §3.3](../04-fetch-defer.md#33-ts3)):
  - the control store selects `OPR_PASS`, which loads AC from the OPR pass unit at TP3 (section 4); L is reloaded unchanged
  - `OPR_PASS_TO_MQ` loads MQ from the pass unit's MQ output at the same TP3; without MQL, the MQ output is MQ itself, so MQ is reloaded unchanged
- The instruction completes at FETCH TP4 ([Sequencing and Internal Direct Control §3.1.1](../../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#311-instruction-completion)).

This follows the KK8-E: MQA is an OR in the data-line multiplexer (PDP-8/E Maintenance Manual, volume 1, §3.35.2, p. 3-127), and SWP uses two paths loaded at the same TP3 (§3.40, p. 3-144).

---

## 4. OPR Pass

A Group 3 instruction selects these functions of the OPR pass unit ([OPR Pass Unit §4](./00-pass-unit.md#4-stage-selection)):

| Stage | Function | Selected by |
|---|---|---|
| A: zero gating (AC path) | AC ← 0 | `IR_OPR_CLA` or `IR_OPR_MQL` |
| B: OR inputs | AC ← AC OR MQ | `IR_OPR_MQA` |
| MQ output | with MQL: the AC after CLA (0 if CLA, else AC); without MQL: MQ | `IR_OPR_MQL`, `IR_OPR_CLA` |

Each control is qualified by `IR_CLASS = 101`. Every input is the value held before TP3, so the two loads at TP3 exchange values when both are selected:

| Instruction | AC after | MQ after |
|---|---|---|
| CLA | 0 | MQ |
| MQA | AC OR MQ | MQ |
| CLA MQA | MQ | MQ |
| MQL | 0 | AC |
| CLA MQL | 0 | 0 |
| SWP (MQA MQL) | MQ | AC |
| CLA SWP | MQ | 0 |

L passes through the unit unchanged. IR bits 5, 3, 2, and 1 (the EAE SCA and operation-code bits) select nothing ([Group 3 ISA](../../02-isa/03-group-3.md)).

---

## 5. Composition Rules

- All functions act in one pass, at FETCH TP3; CLA acts before MQA, MQL, and SWP
- AC, L, and MQ are each loaded once, at that TP
- No two μops write the same register in the same TS

---

## 6. Notes

- The stage controls come from IR bits; the control word carries only `OPR_PASS` (`AC_SRC` = OPR pass unit, `L_OP` = OPR pass unit link) and `OPR_PASS_TO_MQ` (`MQ_SRC` = OPR pass unit MQ output)
- No symbolic instruction interpretation is used
- No memory or I/O interaction occurs
