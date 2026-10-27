# Direct-Control Definitions

## 1. Purpose

This directory contains the authoritative definitions of direct-control results used to construct the CPU control word.

Direct control supplies required control-word information that is not completely supplied by selected micro-operation mappings.

Direct-control results include:

- sequencing next-state values
- control-owned internal selections
- control-provided value bindings
- architectural interface qualification
- CPU output-drive states
- shared-interface ownership results

The governing model is defined in the [Direct-Control Model](../07-direct-control-model.md).

---

## 2. Definition Documents

### 2.1 Sequencing and Internal Control

[Sequencing and Internal Direct Control](./01-sequencing-and-internal-control.md) defines:

- `MS_NEXT`
- `RUN_NEXT`
- `HLT_REQ_NEXT`
- `AB_SRC`
- `MFB_SRC`
- control-provided `DF_VAL`
- control-provided `DIF_VAL`
- `IOT_TRANSFER_VAL`
- direct-control relationships that supplement selected micro-operations

---

### 2.2 Interface and Ownership Control

[Interface and Ownership Direct Control](./02-interface-and-ownership-control.md) defines:

- `/DMA_GRANT`
- `IOT_ACTIVE`
- `/INITIALIZE`
- CPU memory-interface ownership
- DMA memory-interface ownership
- system data bus ownership
- CPU output-drive states
- interface release and ownership-transfer requirements

It also documents the ownership implications of micro-operation-controlled outputs such as:

- `/RD`
- `/WR`
- `/DB_READ`
- `/DB_WRITE`

Those outputs remain assigned by their applicable micro-operation mappings.

---

## 3. Direct-Control Result Index

### 3.1 Sequencing Results

| Result | Definition |
|---|---|
| `MS_NEXT` | [Next Major State](./01-sequencing-and-internal-control.md#32-next-major-state) |
| `RUN_NEXT` | [Run-State Sequencing](./01-sequencing-and-internal-control.md#33-run-state-sequencing) |
| `HLT_REQ_NEXT` | [Halt-Request Sequencing](./01-sequencing-and-internal-control.md#34-halt-request-sequencing) |

---

### 3.2 Internal Selection Results

| Result | Definition |
|---|---|
| `AB_SRC` | [Address Bus Source](./01-sequencing-and-internal-control.md#41-address-bus-source) |
| `MFB_SRC` | [Memory Field Bus Source](./01-sequencing-and-internal-control.md#44-memory-field-bus-source) |

---

### 3.3 Control-Provided Value Bindings

| Destination | Direct-control value | Definition |
|---|---|---|
| `DF_VAL` | `IR_DF` | [Data Field From Instruction](./01-sequencing-and-internal-control.md#51-data-field-from-instruction) |
| `DIF_VAL` | `IR_IF` | [Deferred Instruction Field From Instruction](./01-sequencing-and-internal-control.md#52-deferred-instruction-field-from-instruction) |
| `DIF_VAL` | `0` | [Deferred Instruction Field Clear Value](./01-sequencing-and-internal-control.md#53-deferred-instruction-field-clear-value) |
| `IOT_TRANSFER_VAL` | `READ`, `WRITE`, or `NONE` | [Pending External-IOT Transfer Value](./01-sequencing-and-internal-control.md#55-pending-external-iot-transfer-value) |


---

### 3.4 Architectural Interface Results

| Result | Definition |
|---|---|
| `/DMA_GRANT` | [DMA Authorization and Ownership](./02-interface-and-ownership-control.md#5-dma-authorization-and-ownership) |
| `IOT_ACTIVE` | [External-IOT Qualification](./02-interface-and-ownership-control.md#7-external-iot-qualification) |
| `/INITIALIZE` | [System Initialization](./02-interface-and-ownership-control.md#8-system-initialization) |

---

### 3.5 Ownership and Drive-State Results

| Interface | Definition |
|---|---|
| CPU memory interface | [CPU Memory-Interface Ownership](./02-interface-and-ownership-control.md#4-cpu-memory-interface-ownership) |
| DMA memory interface | [DMA Authorization and Ownership](./02-interface-and-ownership-control.md#5-dma-authorization-and-ownership) |
| System data bus | [System Data Bus Ownership](./02-interface-and-ownership-control.md#6-system-data-bus-ownership) |
| CPU output-drive states | [Interface Ownership Model](./02-interface-and-ownership-control.md#3-interface-ownership-model) |

---

## 4. Composition Boundary

A symbolic control word is composed from:

```text
control-output defaults
+ selected micro-operation assignments
+ direct-control assignments
+ direct-control value bindings
+ direct-control output-drive states
```

The direct-control definitions supplement the micro-operation mappings.

They do not redefine assignments already completely supplied by a selected micro-operation.

Examples:

```text
IR_DF_TO_DF micro-operation mapping:
    DF_LOAD = 1
    DF_SRC  = Control

Direct-control binding:
    DF_VAL = IR_DF
```

```text
IR_IF_TO_DIF micro-operation mapping:
    DIF_LOAD = 1
    DIF_SRC  = Control

Direct-control binding:
    DIF_VAL = IR_IF
```

```text
DIF_CLEAR micro-operation mapping:
    DIF_LOAD = 1
    DIF_SRC  = Control

Direct-control assignment:
    DIF_VAL = 0
```

---

## 5. Excluded Output Classes

### 5.1 Micro-Operation-Owned Assignments

Outputs completely assigned by selected micro-operation mappings are not duplicated as direct-control assignments.

These include:

- `/RD`
- `/WR`
- `/DB_READ`
- `/DB_WRITE`
- register load enables
- datapath source selectors completely defined by the selected micro-operation
- fixed values completely defined by the selected micro-operation

Direct-control documentation may describe the ownership or drive-state consequences of these outputs without duplicating their control-word assignments.

---

### 5.2 Derived Outputs

Derived outputs are not direct-control assignments.

These include:

- `IOA[5:0]`
- `IOP[2:0]`
- `GTF_FLAGS`
- `IF_DF_COMBINED`

Their authoritative derivations remain in the applicable control-output definitions.

---

### 5.3 External Values

Values supplied by memory, external controllers, front-panel data inputs, or DMA controllers are not CPU direct-control values.

CPU control may select, qualify, or release a path associated with an external value, but it does not generate that value.

---

## 6. Required Properties

Every direct-control definition must preserve:

- authoritative source traceability
- explicit control conditions
- fixed assignments separately from value bindings
- current state separately from next-state value
- logical value separately from physical output-drive state
- signal polarity separately from output-drive state
- CPU ownership separately from external ownership
- micro-operation assignments separately from direct-control results
- derived values separately from encoded control-word values
- external values separately from CPU-generated values

No undocumented assignment, binding, transformation, priority, or ownership rule may be introduced.

---

## 7. Related Documents

- [Direct-Control Model](../07-direct-control-model.md)
- [Control Model](../01-control-model.md)
- [Control Addressing](../02-control-addressing.md)
- [Control Constraints](../03-control-constraints.md)
- [Control Word](../04-control-word.md)
- [Datapath Mapping](../05-datapath-mapping.md)
- [Invalid Conditions](../06-invalid-conditions.md)
- [Control Input Definitions](../10-control-input-definitions/00-index.md)
- [Control Output Definitions](../20-control-output-definitions/00-index.md)
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)
- [Signal Conventions](../../00-overview/98-signal-conventions.md)
- [Bus Semantics](../../05-buses-and-signals/06-bus-semantics.md)
- [Ownership Matrix](../../05-buses-and-signals/08-ownership-matrix.md)