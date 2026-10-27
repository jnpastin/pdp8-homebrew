# Direct-Control Model

## 1. Purpose

This document defines the role, scope, composition, and representation of direct control within the CPU control system.

Direct control supplies control-word information that is required by documented processor behavior but is not completely represented by a selected micro-operation.

Direct control includes:

- sequencing results
- control-owned datapath selections
- control-provided values
- architectural interface qualification
- externally visible output-drive state
- ownership-dependent interface behavior

Direct control is part of the control word. It does not operate as a separate control mechanism.

Related:

- [Control Model](./01-control-model.md)
- [Control Addressing](./02-control-addressing.md)
- [Control Constraints](./03-control-constraints.md)
- [Control Word](./04-control-word.md)
- [Datapath Mapping](./05-datapath-mapping.md)
- [Invalid Conditions](./06-invalid-conditions.md)
- [Control Inputs](./10-control-input-definitions/00-index.md)
- [Control Outputs](./20-control-output-definitions/00-index.md)
- [Signal Conventions](../00-overview/98-signal-conventions.md)

---

## 2. Control Function

CPU control is defined as:

```text
CONTROL = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

The logical control-store address is derived from the control inputs:

```text
CTRL_ADDR = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

The selected control word is:

```text
CONTROL_WORD = ROM[CTRL_ADDR]
```

The control word completely defines the CPU-controlled behavior applicable to the selected control case.

No control decision may be introduced after the control-store lookup.

Direct-control information is selected through the same control-input and control-store mechanism as micro-operation control information.

---

## 3. Direct-Control Definition

A direct-control result is a required control-word assignment, value binding, or output-drive state that is not completely supplied by a selected micro-operation mapping.

Direct-control results may define:

- the next value of sequencing state
- a control-owned source selection
- a value supplied through a control-selected value path
- qualification of an architectural interface
- assertion or deassertion of an architectural output
- release of an externally shared interface
- another documented control-word result not represented by a micro-operation

Direct control does not imply that the affected hardware is external to the CPU.

The term identifies how the required control-word information is specified and composed, not the physical location of the controlled hardware.

---

## 4. Boundary With Micro-Operations

A micro-operation defines one documented state transformation or data movement.

Examples include:

- loading a register
- incrementing a register
- transferring a value between architectural or microarchitectural elements
- initiating a documented memory or I/O data transfer
- updating defined processor state

A direct-control result supplies required control behavior that is not itself a complete state transformation or data movement.

Examples include:

- selecting the next major state
- preserving or changing run and halt-request state
- selecting the memory address source for a documented memory operation
- supplying a value through a control-selected value path
- qualifying an external interface
- selecting whether the CPU drives or releases a shared interface

If a micro-operation mapping completely defines a control-output assignment, direct-control documentation must not duplicate that assignment.

If a micro-operation mapping selects a control-owned source but does not supply the required value, direct control supplies only the missing value binding.

For example, the documented `IR_DF_TO_DF` micro-operation selects the control path for `DF`:

```text
DF_LOAD = 1
DF_SRC  = Control
```

The corresponding direct-control binding supplies the value required by that selected path:

```text
DF_VAL = IR_DF
```

The direct-control binding supplements the micro-operation. It does not replace or redefine it.

---

## 5. Boundary With Control Inputs

Control inputs determine which control word is selected.

Control inputs may be used as:

- predicates affecting control-store selection
- values propagated into encoded control-word fields when explicitly documented

A predicate does not become a control output merely because it participates in a control decision.

A value-producing control input may be bound to an encoded control-output field only when the authoritative documentation explicitly defines that value relationship.

Direct-control documentation must not create:

- new control inputs
- new derived flags
- new instruction decodes
- new transformations between input and output values
- new dependencies not defined by the authoritative documentation

Control-input definitions remain authoritative for:

- input names
- widths
- encodings
- polarity
- derivations
- stability requirements
- permitted control uses

---

## 6. Boundary With Derived and External Values

Some control-output definitions identify values as derived rather than encoded in the control word.

Derived values are not direct-control assignments.

The direct-control documentation must not reproduce the derivation of a derived output as a control-word binding.

Some datapath values originate outside CPU control.

External input values are not direct-control assignments.

Direct control may select or qualify the consumption of an external value when that behavior is explicitly documented, but it does not supply or redefine the external value.

The following domains remain distinct:

```text
encoded control-word value
derived combinational value
external input value
physical output-drive state
```

These domains must not be collapsed into one representation.

---

## 7. Control-Word Composition

For a selected control case, the symbolic control word is composed from:

```text
control-output defaults
+ selected micro-operation assignments
+ direct-control assignments
+ direct-control value bindings
+ direct-control output-drive states
```

Each component contributes only the fields it owns.

Defaults establish the documented inactive or default value of control-word fields.

Micro-operation assignments implement selected state transformations and data movements.

Direct-control assignments provide fixed encoded results not owned by a micro-operation.

Direct-control value bindings propagate an explicitly documented control-input value into an encoded control-output field.

Direct-control output-drive states define whether a CPU-controlled physical output is actively driven high, actively driven low, or released.

Composition must produce one unambiguous result for every control-word field required by the selected control case.

---

## 8. Fixed Assignments

A fixed assignment gives an encoded control-output field one documented value.

Example:

```text
MS_NEXT = FETCH
```

The assigned value must:

- be valid for the control-output field
- use the encoding defined by the control-output documentation
- apply under explicitly documented control conditions
- preserve the distinction between symbolic meaning and encoded value

A fixed assignment does not define the conditions that cause a control case to be selected unless those conditions are included as part of the documented derivation.

---

## 9. Input-Value Bindings

An input-value binding assigns the value of a documented control input to an encoded control-output field.

Example:

```text
DF_VAL = IR_DF
```

A binding is valid only when the documentation explicitly establishes:

- the source control input
- the destination control-output field
- the applicable operation or control case
- compatible value width
- compatible representation
- the point at which the destination value is consumed

A binding represents value propagation.

It does not represent:

- a predicate
- a Boolean condition
- an implied conversion
- a source-selection encoding
- a micro-operation
- a general expression

A transformation may be used only when that exact transformation is defined by the authoritative documentation.

No general expression language is implied by the binding model.

---

## 10. Output-Drive States

### 10.1 Scope

An externally connected CPU output may require an electrical drive state in addition to, or instead of, a binary logical assignment.

The valid CPU output-drive states are:

```text
DRIVE_HIGH
DRIVE_LOW
HIGH_Z
```

These states describe CPU driver behavior.

They are not logical assertion states.

---

### 10.2 Drive High

`DRIVE_HIGH` means:

- the CPU output driver is enabled
- the CPU actively drives the output to electrical logic high

For an active-high signal, this normally represents assertion.

For an active-low signal, this normally represents deassertion.

The signal definition remains authoritative for polarity and behavioral meaning.

---

### 10.3 Drive Low

`DRIVE_LOW` means:

- the CPU output driver is enabled
- the CPU actively drives the output to electrical logic low

For an active-low signal, this normally represents assertion.

For an active-high signal, this normally represents deassertion.

The signal definition remains authoritative for polarity and behavioral meaning.

---

### 10.4 High Impedance

`HIGH_Z` means:

- the CPU output driver is electrically disconnected
- the CPU does not drive logic high
- the CPU does not drive logic low

An undriven interface may be observed at a defined logic level because of pull resistors or another active driver.

That observed level does not change the CPU drive state from `HIGH_Z` to `DRIVE_HIGH` or `DRIVE_LOW`.

`HIGH_Z` must therefore remain distinct from every binary control value.

---

### 10.5 Polarity Separation

Output-drive state and signal assertion state are separate representations.

For an active-low output:

```text
DRIVE_LOW  = CPU actively asserts the signal
DRIVE_HIGH = CPU actively deasserts the signal
HIGH_Z     = CPU does not drive the signal
```

For an active-high output:

```text
DRIVE_HIGH = CPU actively asserts the signal
DRIVE_LOW  = CPU actively deasserts the signal
HIGH_Z     = CPU does not drive the signal
```

The observed electrical value of a released output must not be used as a substitute for its drive state.

---

## 11. Interface Ownership

The applicable ownership documentation determines whether the CPU may drive an externally connected interface.

When the CPU owns an interface, the selected control case must define the required CPU-driven values and drive states.

When ownership belongs to another participant, the CPU must release every interface signal that the other participant is permitted to drive.

Releasing interface ownership is an explicit control result.

It must not be represented as:

- a default binary value
- deassertion of an unrelated control signal
- suppression applied after control-word selection
- an inferred consequence of a major state
- an undocumented hardware side effect

A control case that transfers ownership away from the CPU must explicitly establish the required `HIGH_Z` states for CPU drivers identified by the ownership documentation.

A control case must not permit simultaneous CPU and external ownership of the same single-owner interface.

---

## 12. Sequencing Results

Sequencing outputs are direct-control results.

They include:

- `MS_NEXT`
- `RUN_NEXT`
- `HLT_REQ_NEXT`

Sequencing outputs are not micro-operations.

They are explicit next-state values produced by the control word.

A required sequencing output must be assigned a defined value for every control case in which the corresponding output definition requires one.

Preserving the current state is an explicit next-state result when the selected output does not provide a separate hold or no-operation encoding.

Sequencing results commit only at their documented timing boundaries.

Direct-control documentation must preserve the distinction between:

- current state used as a control input
- next-state value contained in the control word
- state update committed at the applicable TP

---

## 13. Memory-Context Results

A memory micro-operation defines the documented memory data movement or memory-cycle action.

Direct control separately supplies memory context not completely owned by that micro-operation.

Memory-context results may include:

- address-bus source selection
- memory-field source selection
- CPU versus external interface ownership
- required CPU output-drive state

A memory-cycle strobe does not by itself select:

- the address source
- the memory field source
- the write-data source
- the physical bus owner

Each required result must be supplied by its documented owner.

Direct-control documentation must not infer a memory source from the selected memory operation unless that relationship is explicitly documented.

---

## 14. Architectural Interface Results

Architectural interface outputs that originate from the control word but are not completely represented by micro-operations are direct-control results.

These may include:

- interface qualification
- system initialization
- DMA authorization
- external-IOT qualification
- ownership release
- other explicitly documented CPU architectural outputs

Each result must preserve:

- signal polarity
- required timing
- applicable preconditions
- output-drive state
- ownership constraints
- interactions with associated micro-operations

Direct control must not define behavior owned by an external controller, memory subsystem, DMA arbiter, or other external participant.

---

## 15. Direct-Control Definitions

Individual direct-control definitions reside in:

- [Direct-Control Definitions](./30-direct-control-definitions/00-index.md)
- [Sequencing and Internal Direct Control](./30-direct-control-definitions/01-sequencing-and-internal-control.md)
- [Interface and Ownership Direct Control](./30-direct-control-definitions/02-interface-and-ownership-control.md)

Each direct-control definition must identify, as applicable:

- name
- purpose
- input conditions
- fixed assignments
- input-value bindings
- output-drive states
- associated micro-operations
- timing and commit point
- ownership requirements
- constraints
- authoritative behavioral sources

The definition must include only information established by authoritative documentation.

Absence of a documented assignment, binding, or drive state must not be resolved by inference.

---

## 16. Generated Artifacts

Machine-readable direct-control artifacts may be generated or maintained to support ROM generation.

Generated artifacts must conform to the authoritative documentation.

A validator, generator, schema, or maintained machine-readable catalog does not become authoritative merely because it exists or is used by the toolchain.

If a tool or generated artifact conflicts with the authoritative documentation:

- the documentation governs
- the tool or artifact must be corrected
- the conflict must not be resolved by changing architectural behavior without review

Tool-specific representation belongs in the ROM-generation tooling documentation and machine-readable schema.

This document defines the architectural model that those representations must preserve.

---

## 17. Required Invariants

The following invariants apply:

- Every direct-control result must have an authoritative documentation source.
- No undocumented assignment, binding, transformation, or drive state is permitted.
- A micro-operation assignment must not be duplicated as direct control.
- A required control-provided value must not be omitted because its selector was assigned by a micro-operation.
- Derived values must not be encoded as direct-control bindings.
- External values must not be represented as CPU-generated values.
- Output-drive state must remain distinct from observed logic level.
- `HIGH_Z` must remain distinct from `DRIVE_HIGH`.
- Signal polarity must remain distinct from electrical drive state.
- Interface ownership must be explicit.
- No two components may assign conflicting values to the same control-word field.
- No two participants may actively drive a single-owner interface simultaneously.
- Sequencing outputs must remain explicit next-state values.
- No post-control-store decision may modify a direct-control result.
- Tooling must conform to the documentation rather than define undocumented behavior.

---

## 18. Related Documents

- [Design Principles](../00-overview/00-design-principles.md)
- [Signal Conventions](../00-overview/98-signal-conventions.md)
- [Architectural Registers](../01-architecture/01-registers.md)
- [Dataflow and Bus Model](../01-architecture/02-dataflow-and-bus-model.md)
- [State Model](../03-microarchitecture/00-state-model.md)
- [Execution Architecture](../03-microarchitecture/01-execution-model.md)
- [Micro-Operations](../03-microarchitecture/02-micro-operations.md)
- [Control Model](./01-control-model.md)
- [Control Addressing](./02-control-addressing.md)
- [Control Constraints](./03-control-constraints.md)
- [Control Word](./04-control-word.md)
- [Datapath Mapping](./05-datapath-mapping.md)
- [Invalid Conditions](./06-invalid-conditions.md)
- [Control Input Definitions](10-control-input-definitions/00-index.md)
- [Control Output Definitions](./20-control-output-definitions/00-index.md)