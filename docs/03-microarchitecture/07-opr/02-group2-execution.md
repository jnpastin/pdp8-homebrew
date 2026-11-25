# Group 2 Execution

## 1. Purpose

Defines execution behavior for OPR Group 2 instructions.

This document specifies:

- the Group 2 stages of the OPR pass unit (CLA, OSR)
- the skip request and the `SKIP` register
- the HLT request
- when each acts

Instruction semantics and encoding details are defined in:

- [Group 2 ISA](../../02-isa/02-group-2.md)

Execution behavior follows:

- [Execution Model](../01-execution-model.md)

---

## 2. Scope

Applies when:

```text
IR_IS_OPR = 1
IR_OPR_GROUP2 = 1
```

---

## 3. Execution Model

A Group 2 instruction completes in FETCH and does not enter EXECUTE (`IR_CLASS = 100`, `IR_NO_EXECUTE = 1`).

- In FETCH TS3 ([FETCH and DEFER Execution §3.3](../04-fetch-defer.md#33-ts3)):
  - the control store selects `OPR_PASS`, which loads AC from the OPR pass unit at TP3 (section 4); L is reloaded unchanged
  - `OPR_SKIP_REQ_TO_SKIP` loads the `SKIP` register with `OPR_SKIP_REQ` at the same TP3 (section 5)
  - a HLT sets `HLT_REQ` at the same TP3 (section 6)
- In FETCH TS4, if `SKIP = 1`, `PC_INC` increments PC at TP4 ([FETCH and DEFER Execution §3.4](../04-fetch-defer.md#34-ts4)).
- The instruction completes at FETCH TP4 ([Sequencing and Internal Direct Control §3.1.1](../../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#311-instruction-completion)).

This follows the KK8-E: combinational skip logic sets the SKIP flip-flop at TP3 (PDP-8/E Maintenance Manual, volume 1, §3.38, p. 3-138), CLA and OSR act in the same pass, and PC, plus 1 if SKIP, is loaded at TP4.

---

## 4. OPR Pass

A Group 2 instruction selects two stages of the OPR pass unit ([OPR Pass Unit §4](./00-pass-unit.md#4-stage-selection)):

| Stage | Function | Selected by |
|---|---|---|
| A: zero gating | AC ← 0 | `IR_OPR_CLA` |
| B: OR inputs | AC ← AC OR FP_SR | `IR_OPR_OSR` |

Each stage's control is its IR bit qualified by `IR_CLASS = 100`. Stage A acts before stage B, so `CLA OSR` loads FP_SR into AC. L passes through the unit unchanged.

---

## 5. Skip Request

The skip decision is `OPR_SKIP_REQ`, which combines the enabled skip conditions of the selected sub-group, including AND-subgroup vacuous truth (SKP) and OR-subgroup behavior ([Derived Flags](../../04-control/10-control-input-definitions/03-derived-flags.md#opr_skip_req)).

- `OPR_SKIP_REQ` is computed from the AC and L held before TP3, so a CLA committed at the same TP3 cannot change the decision.
- `SKIP` holds the decision from FETCH TP3 to FETCH TP4, where it selects `PC_INC` ([Skip Model §12](../../08-interrupts-and-skip/05-skip-model.md#12-skip-state)).

---

## 6. HLT

- HLT is a control-level operation; no datapath μop is performed and no register other than `HLT_REQ` is modified
- `HLT_REQ` is set at FETCH TP3 ([Sequencing and Internal Direct Control §3.4.4](../../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#344-hlt-instruction-request-capture))
- The pending halt is consumed at this instruction's completion, FETCH TP4 ([Sequencing and Internal Direct Control §3.4.6](../../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#346-pending-halt-consumption)), concurrently with any skip increment committed at the same TP4

---

## 7. Composition Rules

- The skip decision, the pass (stages A then B), and the HLT request all act at FETCH TP3; the skip decision uses the pre-TP3 AC and L
- AC, L, and `SKIP` are each loaded once, at that TP
- A taken skip increments PC once, at FETCH TP4
- No two μops write the same register in the same TS

---

## 8. Notes

- The stage controls come from IR bits; the control word carries only `OPR_PASS` (`AC_SRC` = OPR pass unit, `L_OP` = OPR pass unit link) and `SKIP_LOAD`
- No symbolic instruction interpretation is used
- Skip behavior is realized solely via `PC_INC`
