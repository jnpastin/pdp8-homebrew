# Control Invalid Conditions

## 1. Purpose

This document identifies architectural control-system conditions that are design errors.

---

## 2. Control Function and Input Domain Violations

The following are invalid:

- CONTROL_WORD not fully determined by `(MS, TS, IR_FIELDS, FLAGS, EXT)`
- a mechanism other than CONTROL_WORD influencing system behavior
- control depending on a signal outside `MS, TS, IR_FIELDS, FLAGS, EXT` (raw IR contents, register values, datapath outputs, transient combinational signals)
- identical `(MS, TS, IR_FIELDS, FLAGS, EXT)` tuples producing different CONTROL_WORD values
- the `MS`, `TS`, `IR_FIELDS`, `FLAGS`, and `EXT` input domains overlapping in definition or implementation
- a control-pipeline stage (`IR → IR_FIELDS`, `Registers → FLAGS`, inputs `→ CTRL_ADDR`, `CTRL_ADDR → CONTROL_WORD`) performing the role of another stage
- a control condition expressed in terms of raw register state (e.g. `AC == 0`) rather than a reduced FLAG or IR_FIELD
- IR_FIELDS depending on MS or TS, encoding control behavior, or including timing or sequencing information
- IR_FIELDS representing full or raw IR encoding rather than reduced, control-relevant decisions
- more than one, or none, of `IR_IS_MRI`, `IR_IS_IOT`, `IR_IS_OPR` asserted for a given IR value
- more than one of `IR_OPR_GROUP1`, `IR_OPR_GROUP2`, `IR_OPR_GROUP3` asserted simultaneously
- a FLAG derived from DB/MDB, μop intermediate values, control signals, or other transient datapath values rather than stable register state
- a FLAG that is stored or latched
- a redundant or non-orthogonal FLAG
- EXT changing during the control evaluation window, or introducing non-deterministic behavior
- EXT bypassing the control function, directly updating registers, or directly modifying processor state
- a front-panel command input directly executing behavior or directly modifying processor state rather than being consumed by control

---

## 3. Control Address (CTRL_ADDR) Violations

The following are invalid:

- a control decision not fully encoded in CTRL_ADDR
- decoding or interpretation occurring after ROM lookup
- CTRL_ADDR formation influenced by any signal outside `MS, TS, IR_FIELDS, FLAGS, EXT`
- predecode logic depending on TS or MS, or encoding control, timing, or sequencing behavior
- a conditional control decision computed or resolved outside CTRL_ADDR selection (i.e., outside the control store)
- CTRL_ADDR encoding full machine state rather than only the information needed to select a control word
- CTRL_ADDR containing raw IR contents, full instruction encoding, register values, datapath signals, or transient combinational outputs
- one input domain implicitly encoding another within CTRL_ADDR
- PACK producing a result different from the control function `f` for any input combination
- PACK performing IR decoding, evaluating conditions, deriving or generating FLAGS internally, or depending on datapath signals
- PACK encoding outcomes (e.g., `MS_NEXT`) rather than leaving all outcomes in CONTROL_WORD
- MS encoding datapath or register state
- TS encoding behavior rather than sequence position
- raw IR bits used directly in CTRL_ADDR instead of IR_FIELDS
- conditional state represented in CTRL_ADDR by something other than FLAGS
- a reachable CTRL_ADDR value with no defined CONTROL_WORD
- distinct control decisions mapping to the same CTRL_ADDR unintentionally (accidental aliasing)
- CTRL_ADDR not stable before the corresponding TP

---

## 4. Control Address and Control Store Evolution Violations

The following are invalid:

- CTRL_ADDR changing when no new control decision has been introduced
- a new control decision introduced without extending or re-encoding CTRL_ADDR to represent it
- an extension merging distinct input conditions into the same CTRL_ADDR due to insufficient encoding
- extending CTRL_ADDR in a way that changes the mapping of a previously defined input combination without explicit intent
- a newly added input signal lacking a default value that reproduces legacy behavior
- new CONTROL_WORD fields defaulting to values that change pre-existing behavior
- a new control decision implemented solely by extending CONTROL_WORD without a corresponding CTRL_ADDR distinction
- CONTROL_WORD used to differentiate behaviors that are not uniquely identified by CTRL_ADDR
- post-ROM decision logic, hidden decoding stages, or implicit interpretation of CONTROL_WORD fields introduced when extending control
- an external arbitration mechanism (e.g., DMA) modifying CTRL_ADDR formation or suppressing CONTROL_WORD effects

---

## 5. Control Word (CONTROL_WORD) Violations

The following are invalid:

- CONTROL_WORD not fully determining datapath, architectural, and sequencing behavior for the cycle
- control behavior existing outside CONTROL_WORD
- CONTROL_WORD lacking `MS_NEXT`, `RUN_NEXT`, or `HLT_REQ_NEXT`
- `MS_NEXT`, `RUN_NEXT`, or `HLT_REQ_NEXT` computed or modified outside the control store
- `RUN` or `HLT_REQ` modified outside the defined sequencing state update at TP
- an unused or undefined CONTROL_WORD bit influencing system behavior
- system behavior depending on an unspecified or uninitialized CONTROL_WORD bit
- a CONTROL_WORD signal with no defined semantic effect
- two CONTROL_WORD signals producing identical effects without explicit intent
- overlapping control definitions for the same control function
- CONTROL_WORD not stable before the state-update point (TP)
- CONTROL_WORD influencing or feeding back into CTRL_ADDR formation
- CONTROL_WORD performing instruction decoding, condition evaluation, or address formation

---

## 6. Control Signal and Datapath Mapping Violations

The following are invalid:

- an operation occurring without an explicit enable signal
- a select or data-value signal producing an effect when its associated operation is not enabled
- a select signal containing an invalid, reserved, or undefined encoding
- a state-output signal (`MS_NEXT`, `RUN_NEXT`, `HLT_REQ_NEXT`) left undefined, or a "noop" encoding used in place of an explicit state value
- a state-output signal not applied unconditionally at TP
- more than one enable signal targeting the same destination asserted in the same cycle
- more than one input source active for a register whose load enable is asserted
- more than one source driving the internal data bus (IDB) in the same cycle
- `IDB_DRIVE` asserted with no valid `IDB_SRC` selected, or `IDB_SRC` selecting a source while `IDB_DRIVE` is deasserted
- an ALU operand configuration violating its arity (e.g., `ALU_B_SRC` asserted for a unary operation, or `ALU_B_SRC = NONE` for a binary operation)
- `PC_LOAD` and `PC_INC` asserted simultaneously
- IDB, MDB, and DB conflated electrically or logically, or data crossing between them without passing through a defined boundary register
- a control signal from one domain (microarchitectural, architectural, sequencing) performing the role of another domain
- a control signal with no defined effect on datapath, architectural, or sequencing behavior
- a CONTROL_WORD leaving any control field undefined
- a required datapath operation not realizable through any combination of defined CONTROL_WORD signals
- implicit data movement not driven by an explicit enable/select combination

---

## 7. Cross-Domain Operation Binding Violations

The following are invalid:

- an externally visible operation occurring with only one of {architectural control signal, corresponding μop} active
- `/RD` asserted without `MEM_READ_TO_MB` (and `MS ≠ DMA`)
- `MEM_READ_TO_MB` asserted without `/RD` asserted
- `/RD` asserted with `MDB_SRC` other than Memory
- `/WR` asserted without a valid memory-write μop (`MEM_WRITE_FROM_MB`, `MEM_WRITE_FROM_FP_SR`, or DMA write)
- `MEM_WRITE_FROM_MB` or `MEM_WRITE_FROM_FP_SR` asserted without `/WR` asserted
- `MEM_WRITE_FROM_MB` asserted with `MDB_SRC ≠ MB`, or `MEM_WRITE_FROM_FP_SR` asserted with `MDB_SRC ≠ FP_SR`
- `/RD` and `/WR` asserted simultaneously
- `IOT_READ_PENDING` and `IOT_WRITE_PENDING` both asserted
- `IOT_TRANSFER` holding a value other than exactly one of `NONE`, `READ`, or `WRITE`
- `/DB_READ` and `/DB_WRITE` asserted simultaneously
- `/DB_READ` asserted without `DB_READ_TO_AC`, or `/DB_WRITE` asserted without `DB_WRITE_FROM_AC`
- the CPU driving DB while `/DB_READ` is asserted, or an external device driving DB while `/DB_WRITE` is asserted
- `IO_READ_REQ` and `IO_WRITE_REQ` both accepted for the same request
- an accepted external-IOT transfer request whose transfer TS or commit TP falls outside the current external-IOT EXECUTE major state
- AC clear and `DB_READ_TO_AC` committing at the same TP
- a TP action depending on a result committed at that same TP
- an unselected external controller responding to, or modifying local state because of, an IOT
- an external IOT response signal (`IO_READ_REQ`, `IO_WRITE_REQ`, `IO_SKIP_REQ`, `IO_CLEAR_AC_REQ`) directly modifying CPU architectural state rather than requesting CPU or timing behavior
- `/IO_WAIT` altering `RUN`, `MS`, or architectural state directly, or suppressing, extending, or repeating a TP
- a binding rule for a new externally observable operation omitting a required architectural signal, required μop, or explicit binding rule

---

## 8. DMA Control Ownership Violations

The following are invalid:

- `/DMA_REQ` directly suppressing or modifying control signals, or directly altering processor state
- DMA service represented by anything other than defined control words (a hidden control-suppression mechanism)
- `/DMA_GRANT` generated by anything other than CONTROL_WORD
- `/DMA_GRANT` altering CONTROL_WORD
- an external device using `/DMA_GRANT` to mask CPU control signals, modify CPU sequencing state, or alter CTRL_ADDR or CONTROL_WORD
- datapath behavior during `MS = DMA` inferred from `/DMA_REQ` rather than defined by the active CONTROL_WORD
- a CPU state update during `MS = DMA` that is not explicitly encoded in the DMA control word
- DMA continuation or exit decided by anything other than CTRL_ADDR/CONTROL_WORD, or DMA inhibiting `MS_NEXT`, `RUN_NEXT`, or `HLT_REQ_NEXT`
- external DMA ownership coordination modifying CPU control signals or CPU control state

---

## 9. Validation Boundary

These conditions are architectural design errors.

The architecture does not require centralized runtime validation of control compliance. Optional diagnostics may detect violations, but diagnostic behavior must not participate in normal control, timing, or sequencing.

---

## 10. Related Documents

- [Control Model](./01-control-model.md)
- [Control Addressing](./02-control-addressing.md)
- [Control Constraints](./03-control-constraints.md)
- [Control Word](./04-control-word.md)
- [Datapath Mapping](./05-datapath-mapping.md)
- [Primitive Flags](./10-control-input-definitions/01-flags.md)
- [IR Derived Fields](./10-control-input-definitions/02-ir-derived-fields.md)
- [External Inputs](./10-control-input-definitions/04-external-inputs.md)
- [Microarchitectural Control Signals](./20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Architectural Control Signals](./20-control-output-definitions/02-architectural-control-signals.md)
- [Sequencing Control Signals](./20-control-output-definitions/03-sequencing-control-signals.md)
