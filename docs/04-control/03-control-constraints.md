# Control Constraints

## Purpose

Defines the formal invariants and constraints governing the control system.

This document is normative:
- all control behavior must conform to these constraints
- violations are considered design errors

Definitions are provided in:
- [Control Model](01-control-model.md)
- [Control Addressing](02-control-addressing.md)

---

## 1. Functional Completeness

Constraint:
- The system must satisfy:

```
(MS, TS, IR_FIELDS, FLAGS, EXT)
→ CTRL_ADDR
→ CONTROL_WORD
→ complete system behavior
```

Constraint:
- CONTROL_WORD must fully determine all control behavior.
- No additional mechanisms may influence system behavior.

---

## 2. Input Domain Exclusivity

Constraint:
- Control may depend only on the following domains:
  - MS
  - TS
  - IR_FIELDS
  - FLAGS
  - EXT

Constraint:
- No other signals may influence control, including:
  - raw IR contents
  - register values
  - datapath outputs
  - transient combinational signals

---

## 3. Determinism

Constraint:
- CONTROL must be a deterministic function of its inputs.

Constraint:
- For any identical input tuple:
```
(MS, TS, IR_FIELDS, FLAGS, EXT)
```
the resulting CONTROL_WORD must be identical.

Constraint:
- No non-deterministic behavior is permitted.

---

## 4. Separation of Concerns

Constraint:
- The control system must maintain strict separation:

```
IR → IR_FIELDS
Registers → FLAGS
(MS, TS, IR_FIELDS, FLAGS, EXT) → CTRL_ADDR
CTRL_ADDR → CONTROL_WORD
```

Constraint:
- No stage may perform the role of another.
- No cross-layer logic is permitted.

---

## 5. IR_FIELDS Constraints

Defined in:
- [IR Derived Fields](10-control-input-definitions/02-ir-derived-fields.md)

Additional constraints:

- must not depend on MS or TS
- must not encode control behavior
- must not include timing or sequencing information
- must represent reduced instruction information only

Constraint:
- Raw IR bits must not be used in control decisions.

---

## 6. FLAGS Constraints

Defined in:
- [Derived Flags](10-control-input-definitions/01-derived-flags.md)

Additional constraints:

- must be derived only from stable register state
- must not depend on transient datapath signals
- must not be stored or latched
- must be stable during the control evaluation window

Constraint:
- FLAGS must be minimal and non-redundant.

---

## 7. Control Address Constraints

Defined in:
- [Control Addressing](02-control-addressing.md)

Additional constraints:

### 7.1 Decision Encoding

Constraint:
- CTRL_ADDR must encode control decisions only.
- CTRL_ADDR must not encode full machine state.

---

### 7.2 Input Reduction Requirement

Constraint:
- All information in CTRL_ADDR must originate from:
  - MS
  - TS
  - IR_FIELDS
  - FLAGS
  - EXT

Constraint:
- No unreduced state may be encoded.

---

### 7.3 PACK Constraints

Constraint:
- If implemented using PACK:
```
CTRL_ADDR = PACK(MS, TS, IR_FIELDS, FLAGS, EXT)
```

- PACK must be equivalent to the control function f
- PACK must not introduce new logic or decisions

Constraint:
- PACK must not:
  - decode IR
  - evaluate conditions
  - derive FLAGS
  - depend on datapath signals

Constraint:
- All decision logic must exist prior to address formation.

---

## 8. Control Word Constraints

Constraint:
- CONTROL_WORD must define:
  - all datapath control signals
  - all architectural updates
  - all sequencing behavior

Constraint:
- CONTROL_WORD must include MS_next.

Constraint:
- No control behavior may exist outside CONTROL_WORD.

---

## 9. Sequencing Constraints

Constraint:
- State transitions must be determined solely by CONTROL_WORD.

Constraint:
- MS_next must not be computed outside the control store.

Constraint:
- TS progression must be deterministic and independent of datapath signals.

---

## 10. Timing Constraints

Constraint:
- All control inputs must be stable during the evaluation window.

Constraint:
- CTRL_ADDR must be stable before control application.

Constraint:
- CONTROL_WORD must be stable at the point of state update.

Constraint:
- No control signal may depend on unstable inputs.

---

## 11. External Inputs (EXT)

Constraint:
- EXT must be stable during control evaluation.

Constraint:
- EXT must be synchronized to the control timing model.

Constraint:
- EXT must not introduce non-deterministic behavior.

---

## 12. Control Evolution Constraints

This section defines constraints governing extension of the control system.

Refer to:
- [Control Addressing](02-control-addressing.md)

---

### 12.1 Decision Space Consistency

Constraint:
- CTRL_ADDR must uniquely represent the full input decision space.

Constraint:
- If IR_FIELDS, FLAGS, or EXT are extended, CTRL_ADDR must be updated to encode the expanded domain.

Constraint:
- No distinct input conditions may be merged due to insufficient address encoding.

---

### 12.2 No Decision Relocation

Constraint:
- New control decisions must not be implemented by extending CONTROL_WORD alone.

Constraint:
- CONTROL_WORD must not be used to differentiate behaviors that are not uniquely identified by CTRL_ADDR.

Constraint:
- All control decisions must be resolved before or at CTRL_ADDR formation.

---

### 12.3 Output-Only Extensions

Constraint:
- CONTROL_WORD may be extended without modifying CTRL_ADDR only if:
  - no new control decisions are introduced
  - existing input domains fully determine behavior

Constraint:
- New CONTROL_WORD fields must not introduce implicit condition evaluation.

---

### 12.4 Backward Compatibility

Constraint:
- Extension of CTRL_ADDR or CONTROL_WORD must preserve existing behavior for all previously defined input combinations.

Constraint:
- Default values for new inputs must map to legacy behavior unless explicitly redefined.

---

### 12.5 No Implicit Expansion Mechanisms

Constraint:
- The following are prohibited when extending control:
  - post-ROM decision logic
  - hidden decoding stages
  - implicit interpretation of CONTROL_WORD fields

Constraint:
- All extensions must conform to the defined control pipeline:
```
(MS, TS, IR_FIELDS, FLAGS, EXT)
→ CTRL_ADDR
→ CONTROL_WORD
```

---

### 12.6 External Arbitration Constraints

Constraint:
- External arbitration mechanisms may suppress control effects but must not alter control decisions.

Constraint:
- CONTROL_WORD must remain a pure function of CTRL_ADDR.

Constraint:
- No external mechanism may introduce implicit control behavior.

---

## 13. Completeness

Constraint:
- Every reachable input combination must map to a defined CONTROL_WORD.

Constraint:
- No valid CTRL_ADDR may be undefined.

---

## 14. Non-Aliasing

Constraint:
- Distinct control behaviors must not map to the same CTRL_ADDR unless explicitly intended.

Constraint:
- Accidental aliasing is prohibited.

---

## 15. No Implicit Behavior

Constraint:
- All control behavior must be explicitly encoded.

Constraint:
- No behavior may be:
  - inferred
  - implied
  - implemented outside the control system

---

## 16. Invariant Summary

Constraint:
- The control system must operate exclusively as:

```
(MS, TS, IR_FIELDS, FLAGS, EXT)
→ CTRL_ADDR
→ CONTROL_WORD
→ system behavior
```

Constraint:
- This mapping must be:
  - complete
  - explicit
  - deterministic
