# Control Constraints

## Purpose

Defines the formal invariants and constraints governing the control system.

This document is normative:
- all control behavior must conform to these constraints
- violations are considered design errors

Definitions are provided in:
- [Control Model](./01-control-model.md)
- [Control Addressing](./02-control-addressing.md)

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
- [Primitive Flags](10-control-input-definitions/01-flags.md)
- [Derived Flags](10-control-input-definitions/03-derived-flags.md)

Additional constraints:

- must be derived only from stable register state or direct reflection of stable one-bit state registers
- must not depend on transient datapath signals
- must not be stored or latched
- must be stable during the control evaluation window

Constraint:
- FLAGS must be minimal and non-redundant.

---

## 7. Control Address Constraints

Defined in:
- [Control Addressing](./02-control-addressing.md)

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
- CONTROL_WORD must include:
  - MS_NEXT
  - RUN_NEXT
  - HLT_REQ_NEXT
  
Constraint:
- No control behavior may exist outside CONTROL_WORD.

---

## 9. Sequencing Constraints

Constraint:
- State transitions must be determined solely by CONTROL_WORD.

Constraint:
- MS_NEXT, RUN_NEXT and HLT_REQ_NEXT must not be computed outside the control store.

Constraint:
- RUN and HALT_REQ must not be modified outside defined sequencing state updates.

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

### 11. Cross-Domain Operation Binding Rules

#### Purpose

Defines the required relationship between:
- architectural control signals (external operations)
- micro-operations (internal state transformations)

This section ensures:
- no implicit behavior
- correct coordination between CPU and external subsystems
- preservation of domain separation

---

### 11.1 General Principle

An externally visible operation is valid only when **both**:
1. the architectural control signal for that operation is asserted
2. the corresponding μop is active

Neither alone is sufficient.

Implication:
- architectural signals do not cause internal state changes
- μops do not initiate external behavior

---

### 11.2 Memory Read Binding

A memory read operation is defined by the combination of:

- Architectural signal:
  - RD = 1

- Micro-operation:
  - MEM_READ_TO_MB

#### Required Behavior

When both are active in the same TS:

- MB must capture MDB_input at TP
- Memory must place M[MEM_ADDR] onto MDB

Where:

- MEM_ADDR = {MFB, AB}  
- AB  = MA when AB_SRC = MA, PC when AB_SRC = PC  
- MFB = IF when MFB_SRC = IF, DF when MFB_SRC = DF  


#### Invalid Conditions

The following are invalid and must not occur:

- RD = 1 without MEM_READ_TO_MB or MS = DMA  
  → external read initiated with no defined data consumption

- MEM_READ_TO_MB without RD = 1  
  → MB attempts to capture undefined MDB_input

- RD = 1 without MDB_SRC = Memory
  → read can only be driven by memory
---

### 11.3 Memory Write Binding

A memory write operation is defined by the combination of:

- Architectural signal:
  - WR = 1

- One of the Micro-operations:
  - MEM_WRITE_FROM_MB
  - MEM_WRITE_FROM_SR

Effective control required for memory writes:
- WR + MDB_SRC = MB + MEM_WRITE_FROM_MB
- WR + MDB_SRC = SR + MEM_WRITE_FROM_SR
- WR + MDB_SRC = DMA + MS = DMA


#### Required Behavior

When both are active in the same TS:

Memory must store the selected source data into M[MEM_ADDR] at TP

Where:

- MEM_ADDR = {MFB, AB}  
- AB  = MA when AB_SRC = MA, PC when AB_SRC = PC  
- MFB = IF when MFB_SRC = IF, DF when MFB_SRC = DF  

#### Invalid Conditions

The following are invalid and must not occur:

- WR = 1 without a valid memory-write μop
  → external write initiated with no defined data source

- MEM_WRITE_FROM_MB without WR = 1
  → memory state modified without external coordination

- MEM_WRITE_FROM_SR without WR = 1
  → memory state modified without external coordination

- MEM_WRITE_FROM_MB with MDB_SRC ≠ MB
  → write-source mismatch

- MEM_WRITE_FROM_SR with MDB_SRC ≠ SR
  → write-source mismatch

---

### 11.4 External IOT Response Binding

During external-IOT EXECUTE:

- `IO_READ_REQ` selects `DB_READ` and `DB_READ_TO_AC` for the current phase.
- `IO_WRITE_REQ` selects `DB_WRITE` and `DB_WRITE_FROM_AC` for the current phase.
- `IO_SKIP_REQ` selects `PC_INC` at TP4.
- `IO_CLEAR_AC_REQ` selects AC clear at the following TP.

Constraints:

- Controller responses are phase-specific.
- A response asserted during a TS causes exactly one action at the following TP.
- Read and write are mutually exclusive.
- Read and AC clear must not target AC at the same TP.
- Write and AC clear may commit at the same TP using the pre-TP AC value.
- No TP action may depend on a result committed at that TP.
- Only the selected external controller may contribute an IOT response.
- Control does not centrally validate controller compliance with address qualification.

#### I/O Wait Binding

`IO_WAIT` may inhibit TSTEP progression only at eligible non-TP setup positions during external-IOT EXECUTE.

Constraints:

- `IO_WAIT` must not alter RUN.
- `IO_WAIT` must not alter MS.
- `IO_WAIT` must not directly modify architectural state.
- `IO_WAIT` must not suppress, extend, or repeat a TP.
- All control outputs and external values required by the pending phase must remain stable while TSTEP is held.
- TSTEP progression must resume normally when `IO_WAIT` is deasserted.

---

### 11.5 Domain Separation Constraint

Binding between architectural signals and μops:

- does not merge domains
- does not redefine signal semantics
- does not introduce implicit control behavior

Each domain retains its role:

- Architectural signals:
  - initiate external operations

- μops:
  - define internal state changes

The binding rule is a **consistency requirement**, not a mechanism.

---

### 11.6 Determinism Requirement

For any valid execution state:

- the active architectural signals and μops must form a consistent pair
- no partially defined external operation may exist

This ensures:

(control word + prior state) → exactly one valid system behavior

---

### 11.7 Extension Rule

Any future externally observable operation (e.g., DMA) must define:

- required architectural signal(s)
- required μop(s)
- explicit binding rules identical in structure to this section

No external operation may be defined without such a binding.

---

## 12. External Inputs (EXT)

Constraint:
- EXT must be stable during control evaluation.

Constraint:
- EXT must be synchronized to the control timing model.

Constraint:
- EXT must not introduce non-deterministic behavior.

---

## 13. Control Evolution Constraints

This section defines constraints governing extension of the control system.

Refer to:
- [Control Addressing](./02-control-addressing.md)

---

### 13.1 Decision Space Consistency

Constraint:
- CTRL_ADDR must uniquely represent the full input decision space.

Constraint:
- If IR_FIELDS, FLAGS, or EXT are extended, CTRL_ADDR must be updated to encode the expanded domain.

Constraint:
- No distinct input conditions may be merged due to insufficient address encoding.

---

### 13.2 No Decision Relocation

Constraint:
- New control decisions must not be implemented by extending CONTROL_WORD alone.

Constraint:
- CONTROL_WORD must not be used to differentiate behaviors that are not uniquely identified by CTRL_ADDR.

Constraint:
- All control decisions must be resolved before or at CTRL_ADDR formation.

---

### 13.3 Output-Only Extensions

Constraint:
- CONTROL_WORD may be extended without modifying CTRL_ADDR only if:
  - no new control decisions are introduced
  - existing input domains fully determine behavior

Constraint:
- New CONTROL_WORD fields must not introduce implicit condition evaluation.

---

### 13.4 Backward Compatibility

Constraint:
- Extension of CTRL_ADDR or CONTROL_WORD must preserve existing behavior for all previously defined input combinations.

Constraint:
- Default values for new inputs must map to legacy behavior unless explicitly redefined.

---

### 13.5 No Implicit Expansion Mechanisms

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

### 13.6 External Arbitration Constraints

Constraint:
- External arbitration mechanisms must not modify CTRL_ADDR formation.

Constraint:
- External arbitration mechanisms must not suppress CONTROL_WORD effects.

Constraint:
- DMA service must be represented through EXT inputs,
  CTRL_ADDR selection, CONTROL_WORD outputs,
  and defined sequencing behavior.

Constraint:
- No external mechanism may introduce implicit control behavior.

---

## 14. Completeness

Constraint:
- Every reachable input combination must map to a defined CONTROL_WORD.

Constraint:
- No valid CTRL_ADDR may be undefined.

---

## 15. Non-Aliasing

Constraint:
- Distinct control behaviors must not map to the same CTRL_ADDR unless explicitly intended.

Constraint:
- Accidental aliasing is prohibited.

---

## 16. No Implicit Behavior

Constraint:
- All control behavior must be explicitly encoded.

Constraint:
- No behavior may be:
  - inferred
  - implied
  - implemented outside the control system

---

## 17. Invariant Summary

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
