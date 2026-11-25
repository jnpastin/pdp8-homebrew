# Interface and Ownership Direct Control

## 1. Purpose

This document defines direct-control results for:

- architectural interface qualification
- system initialization
- DMA authorization
- CPU ownership of shared interfaces
- CPU output-drive states
- ownership transfer between the CPU and external participants

Direct-control scope, composition, and representation are defined in the [Direct-Control Model](../07-direct-control-model.md).

Signal meanings, polarity, encodings, and timing remain defined by the [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md).

This document does not redefine:

- memory-operation micro-operations
- I/O-transfer micro-operations
- DMA-controller behavior
- DMA-arbiter selection
- external input values
- derived architectural outputs
- controller-local state
- physical driver implementation

---

## 2. Source and Representation Rules

Each definition in this document identifies, as applicable:

- the direct-control result
- the control conditions selecting the result
- the logical signal assignment
- the corresponding CPU output-drive state
- associated micro-operations
- ownership requirements
- timing requirements
- constraints
- authoritative sources

Logical signal values and physical output-drive states are distinct.

For an active-low signal:

```text
logical value 0 = asserted
logical value 1 = deasserted
```

The corresponding CPU output-drive states are:

```text
DRIVE_LOW
DRIVE_HIGH
HIGH_Z
```

`HIGH_Z` is not a logical value.

A released output may be observed as logic high because of a pull-up or another active driver. That observed value does not change the CPU output-drive state from `HIGH_Z` to `DRIVE_HIGH`.

Related:

- [Signal Conventions](../../00-overview/98-signal-conventions.md)
- [Control Constraints](../03-control-constraints.md)
- [Invalid Conditions](../06-invalid-conditions.md)
- [Bus Semantics](../../05-buses-and-signals/06-bus-semantics.md)
- [Signal Ownership Matrix](../../05-buses-and-signals/08-ownership-matrix.md)

---

## 3. Interface Ownership Model

### 3.1 CPU-Owned Interface

When the CPU owns an interface:

- CPU control determines the applicable CPU-driven values
- CPU control determines which CPU drivers are enabled
- external participants must not drive CPU-owned single-owner outputs
- every CPU output required by the selected operation must have a defined drive state

CPU ownership does not imply that every interface signal is actively driven.

For example, during a CPU memory read:

- the CPU drives the memory address
- the CPU drives the memory field
- the CPU asserts `/RD`
- the CPU deasserts `/WR`
- the CPU does not drive `MDB`
- memory drives `MDB`

---

### 3.2 External Ownership

When ownership belongs to an external participant:

- CPU drivers for externally owned signals must be `HIGH_Z`
- CPU control must not supply an active high or low value on those signals
- external ownership must be established by the applicable authorization and selection conditions
- CPU and external ownership must not overlap

External ownership does not permit an arbitrary external participant to drive the interface.

The externally selected participant must satisfy the applicable ownership contract.

---

### 3.3 Ownership and Selection

CPU release and external selection are separate decisions.

For DMA:

```text
CPU release:
    /DMA_GRANT = 0

controller selection:
    DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

A DMA controller owns the DMA interfaces only when both conditions are satisfied:

```text
/DMA_GRANT = 0
AND
DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

`/DMA_GRANT` does not identify the selected controller.

`DMA_GRANT_ID` does not by itself authorize ownership while `/DMA_GRANT` is deasserted.

Sources:

- [DMA and Console Memory Access](../../06-memory/06-dma-and-console-access.md)
- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)

---

## 4. CPU Memory-Interface Ownership

### 4.1 CPU-Owned Memory Interface

Outside DMA ownership, the CPU retains normal ownership of:

- `MFB`
- `AB`
- `/RD`
- `/WR`
- `MDB` when the selected CPU memory operation requires the CPU to drive write data

The applicable control case must define:

- `AB_SRC`
- `MFB_SRC`
- `MDB_SRC`
- `/RD`
- `/WR`

The required `AB_SRC` and `MFB_SRC` derivations are defined in [Sequencing and Internal Direct Control](./01-sequencing-and-internal-control.md).

The required `/RD`, `/WR`, and `MDB_SRC` assignments associated with memory micro-operations remain owned by their reviewed micro-operation mappings.

---

### 4.2 CPU Memory Read

Applicable context:

```text
MEM_READ_TO_MB is selected
```

Micro-operation assignments:

```text
/RD = 0
/WR = 1
```

CPU output-drive states:

```text
CPU AB driver  = driven according to AB_SRC
CPU MFB driver = driven according to MFB_SRC
CPU /RD driver = DRIVE_LOW
CPU /WR driver = DRIVE_HIGH
CPU MDB driver = HIGH_Z
```

External ownership:

```text
Memory MDB driver = active
```

Constraints:

- `/RD` and `/WR` must not both be asserted.
- The CPU must not drive `MDB` during a memory read.
- Memory must be the sole `MDB` producer.
- The selected address and field must remain valid for the memory-read interval.
- The read strobe does not itself select `AB_SRC`, `MFB_SRC`, or `MDB_SRC`.
- The `/RD` & `/WR` assignments remain part of the micro-operation mappings rather than a separate direct-control assignment.

Sources:

- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)
- [Memory Interface](../../06-memory/02-memory-interface.md)

---

### 4.3 CPU Memory Write From MB

Applicable context:

```text
MEM_WRITE_FROM_MB is selected
```

Micro-operation assignments:

```text
/RD     = 1
/WR     = 0
MDB_SRC = MB
```

CPU output-drive states:

```text
CPU AB driver  = driven according to AB_SRC
CPU MFB driver = driven according to MFB_SRC
CPU /RD driver = DRIVE_HIGH
CPU /WR driver = DRIVE_LOW
CPU MDB driver = driven from MB
```

External ownership:

```text
Memory captures MDB.
```

Constraints:

- `/RD` and `/WR` must not both be asserted.
- The CPU must be the sole `MDB` producer.
- Memory must not drive `MDB`.
- The selected address, field, and write data must remain valid for the memory-write interval.
- The `/RD` & `/WR` assignments remain part of the micro-operation mappings rather than a separate direct-control assignment.

Sources:

- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md#mem_write_from_mb)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)
- [Memory Interface](../../06-memory/02-memory-interface.md)

---

### 4.4 CPU Memory Write From Front Panel

Applicable context:

```text
MEM_WRITE_FROM_FP_SR is selected
```

Micro-operation assignments:

```text
/RD     = 1
/WR     = 0
MDB_SRC = FP_SR
```

CPU output-drive states:

```text
CPU AB driver  = driven according to AB_SRC
CPU MFB driver = driven according to MFB_SRC
CPU /RD driver = DRIVE_HIGH
CPU /WR driver = DRIVE_LOW
CPU MDB driver = driven from FP_SR
```

External ownership:

```text
Memory captures MDB.
```

Constraints:

- `/RD` and `/WR` must not both be asserted.
- The CPU must be the sole `MDB` producer.
- Memory must not drive `MDB`.
- The selected address, field, and front-panel value must remain valid for the memory-write interval.
- The `/RD` & `/WR` assignments remain part of the micro-operation mappings rather than a separate direct-control assignment.

Sources:

- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)
- [Console Execution](../../03-microarchitecture/09-console-execution.md#8-deposit-operation)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

### 4.5 Inactive CPU Memory Interface

Applicable context:

```text
MEM_READ_TO_MB is not selected
MEM_WRITE_FROM_MB is not selected
MEM_WRITE_FROM_FP_SR is not selected
MS != DMA
```

Logical control results:

```text
/RD = 1
/WR = 1
```

CPU output-drive states:

```text
CPU /RD driver = DRIVE_HIGH
CPU /WR driver = DRIVE_HIGH
```

The active `CONTROL_WORD` still contains valid encodings for:

- `AB_SRC`
- `MFB_SRC`
- `MDB_SRC`

Those encoded values do not initiate a memory operation while both `/RD` and `/WR` are deasserted.

Constraints:

- Deasserting `/RD` and `/WR` does not transfer memory ownership.
- CPU ownership remains distinct from whether a memory cycle is active.
- An inactive strobe must not be treated as `HIGH_Z` unless the interface documentation explicitly requires driver release.
- Select-field defaults do not imply a memory operation.

Source:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

## 5. DMA Authorization and Ownership

### 5.1 DMA Grant Result

`/DMA_GRANT` indicates that the CPU is in `MS = DMA` and has released normal CPU ownership of the memory interface.

Encoding:

```text
0 = DMA ownership authorized
1 = DMA ownership not authorized
```

`/DMA_GRANT`:

- is derived from `MS_EFF` by a comparator, not stored in the control word ([Architectural Control Signals §4.5](../20-control-output-definitions/02-architectural-control-signals.md#45-dma_grant))
- is not a micro-operation
- does not identify the selected controller
- does not define DMA address, data, direction, or device selection
- does not modify CPU architectural state
- does not modify `RUN` or `HLT_REQ`

Source:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

### 5.2 DMA Major State

Applicable context:

```text
RUN = 1
MS = DMA
```

Related derived values:

```text
/DMA_GRANT = 0
```

CPU output-drive states:

```text
CPU MFB driver = HIGH_Z
CPU AB driver  = HIGH_Z
CPU MDB driver = HIGH_Z
CPU /RD driver = HIGH_Z
CPU /WR driver = HIGH_Z
```

Constraints:

- `/DMA_GRANT` remains asserted throughout `MS = DMA` while `RUN = 1`; while halted it is deasserted (section 5.3).
- CPU control must not drive `MFB`, `AB`, `MDB`, `/RD`, or `/WR`.
- `AB_SRC`, `MFB_SRC`, and `MDB_SRC` may contain valid encoded values in the control word, but those values do not authorize CPU drivers during DMA ownership.
- CPU-generated `/RD` and `/WR` requests remain inactive because the CPU drivers are released.
- CPU and DMA ownership must not overlap.
- The CPU must not select an individual DMA controller.
- An external controller must not drive a DMA-owned interface unless it has a matching valid `DMA_GRANT_ID`.

Sources:

- [DMA & Console Access](../../06-memory/06-dma-and-console-access.md)
- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)
- [Signal Ownership Matrix](../../05-buses-and-signals/08-ownership-matrix.md)

---

### 5.3 Non-DMA Major States and Halted Operation

Applicable context:

```text
NOT (
    RUN = 1
    AND MS = DMA
)
```

Related derived values:

```text
/DMA_GRANT = 1
```

CPU output-drive state:

```text
CPU /DMA_GRANT driver = DRIVE_HIGH
```

Constraints:

- `/DMA_GRANT` must not be asserted during normal instruction execution.
- `/DMA_GRANT` is deasserted while halted, including while `MS = DMA` holds a suspended burst ([DMA Execution §4](../../03-microarchitecture/10-dma-execution.md#4-halting-between-dma-cycles)).
- External DMA controllers must not drive DMA-owned interfaces.
- `DMA_GRANT_ID` does not authorize ownership while `/DMA_GRANT` is deasserted.
- Pending `/DMA_REQ[n]` inputs do not themselves transfer ownership.
- Aggregate `/DMA_REQ` does not itself transfer ownership.

Sources:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)

---

### 5.4 DMA Ownership

Applicable context:

```text
MS = DMA
RUN = 1
```

CPU output-drive states:

```text
CPU MFB driver = HIGH_Z
CPU AB driver  = HIGH_Z
CPU MDB driver = HIGH_Z
CPU /RD driver = HIGH_Z
CPU /WR driver = HIGH_Z
```

External ownership:

```text
selected controller drives MFB
selected controller drives AB
selected controller asserts /RD
selected controller deasserts /WR
memory drives MDB
```

That block is a DMA read. For a DMA write, the external ownership is:

```text
selected controller drives MFB
selected controller drives AB
selected controller deasserts /RD
selected controller asserts /WR
selected controller drives MDB
```

Constraints:

- For a read, memory is the sole `MDB` producer, the selected controller must not drive `MDB`, and the controller captures `MDB` at TP2.
- For a write, the selected controller is the sole `MDB` producer, and memory stores `MDB` during `/WR_PULSE` at TP2.
- No CPU control assignment may replace the controller-supplied address, field, or direction.

Source:

- [DMA Interface](../../07-io/05-dma-interface.md)

---

### 5.5 DMA Ownership Release

When a controller selection terminates:

- the selected controller has driven none of `MFB`, `AB`, `MDB`, `/RD`, and `/WR` since it released them at the end of DMA TS2
- the arbiter sets `DMA_GRANT_ID` to the no-controller-selected value at DMA TP4
- CPU control deasserts `/DMA_GRANT` when control exits `MS = DMA`
- CPU ownership resumes during the following FETCH TS1

The release obeys these rules, which the definitions in sections 4 and 5 implement:

- The selected controller must release its drivers before CPU ownership resumes.
- CPU drivers must remain `HIGH_Z` through the end of the DMA major state.
- CPU and controller drive intervals must not overlap.
- CPU ownership must not resume solely because aggregate `/DMA_REQ` is deasserted.
- Ownership transition follows the documented TP4 release ordering.

Source:

- [DMA Arbitration](../../07-io/06-dma-arbitration.md)

---

## 6. System Data Bus Ownership

### 6.1 Inactive System Data Bus

Applicable context:

```text
IOT_WRITE_PENDING = 0
```

CPU output-drive state:

```text
CPU DB driver = HIGH_Z
```

Constraints:

- The CPU must not drive `DB` during a DB read.
- The CPU must not drive `DB` merely because an external IOT is active.
- A selected external controller may drive `DB` only during its documented read-transfer interval.
- At most one participant may drive `DB`.

Sources:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)
- [External IOT Interface](../../07-io/02-external-iot-interface.md)
- [Signal Ownership Matrix]( ../../05-buses-and-signals/08-ownership-matrix.md)

---

### 6.2 CPU DB Write

Applicable context:

```text
IOT_WRITE_PENDING = 1
```

Related derived values:

```text
/DB_READ  = 1
/DB_WRITE = 0
```

CPU output-drive state:

```text
CPU DB driver = driven from AC
```

Constraints:

- `/DB_READ` and `/DB_WRITE` must not both be asserted.
- The CPU is the sole `DB` driver.
- External controllers must not drive `DB`.
- `/DB_WRITE` and the CPU DB driver are decoded from `IOT_TRANSFER = WRITE` within `DB_VALID`; neither is a control-word field or a direct-control assignment.

Sources:

- [Micro Operations](../../03-microarchitecture/02-micro-operations.md)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

### 6.3 CPU DB Read

Applicable context:

```text
DB_READ_TO_AC is selected
```

Related derived values:

```text
/DB_READ  = 0
/DB_WRITE = 1
```

CPU output-drive state:

```text
CPU DB driver = HIGH_Z
```

External ownership:

```text
the selected controller may drive DB
```

Constraints:

- `/DB_READ` and `/DB_WRITE` must not both be asserted.
- `/DB_READ` must be paired with `DB_READ_TO_AC`.
- The CPU must not drive `DB`.
- At most one selected external controller may drive `DB`.
- `/DB_READ` is decoded from `IOT_TRANSFER = READ` within `DB_VALID`; it is not a control-word field. The DB-to-AC datapath selection remains owned by the `DB_READ_TO_AC` micro-operation mapping.

Sources:

- [Micro Operations](../../03-microarchitecture/02-micro-operations.md)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

## 7. External-IOT Qualification

### 7.1 IOT Active Result

`IOT_ACTIVE` indicates that the CPU is executing an external-device IOT and that controller-facing `IOA`, `IOP`, and response inputs are valid for the documented external-IOT interaction.

`IOT_ACTIVE`:

- is derived as `MS_EFF_IS_EXECUTE AND IR_IS_EXTERNAL_IOT`, not stored in the control word ([Architectural Control Signals §4.8](../20-control-output-definitions/02-architectural-control-signals.md#48-external-iot-active-iot_active))
- is not a micro-operation
- does not select a controller by itself
- does not cause a DB transfer by itself
- does not authorize a controller whose `IOA` does not match
- does not replace `/DB_READ` or `/DB_WRITE`

Source:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

### 7.2 External-Device IOT

Applicable context:

```text
RUN = 1
MS = EXECUTE
IR_IS_EXTERNAL_IOT = 1
```

Related derived values:

```text
IOT_ACTIVE = 1
IOA = IR_IOA
IOP = IR[2:0]
```

Constraints:

- `IOT_ACTIVE`, `IOA`, and `IOP` are derived outputs rather than direct-control assignments.
- Only the address-matched controller may respond.
- Controller response inputs are valid only while `IOT_ACTIVE = 1`.
- `IOT_ACTIVE` does not itself determine whether a read, write, skip, or clear-AC response is accepted.
- DB ownership remains governed by `/DB_READ`, `/DB_WRITE`, and the accepted transfer state.

Sources:

- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [External IOT Interface](../../07-io/02-external-iot-interface.md)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

### 7.3 Non-External-IOT Control Cases

Applicable context:

```text
NOT (
    RUN = 1
    AND MS = EXECUTE
    AND IR_IS_EXTERNAL_IOT = 1
)
```

Related derived values:

```text
IOT_ACTIVE = 0
```

Constraints:

- Processor IOT execution (device 00) and memory extension IOT execution (devices 20–27) must not qualify external controllers.
- An `IOA` value alone does not make a controller response valid.
- External response inputs must not affect control while `IOT_ACTIVE = 0`.

Sources:

- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [External IOT Interface](../../07-io/02-external-iot-interface.md)

---

## 8. System Initialization

### 8.1 Initialization Result

`/INITIALIZE` is the architectural system-initialization output.

Encoding:

```text
0 = initialization asserted
1 = initialization deasserted
```

`/INITIALIZE`:

- is specified by the control word and presented by the equivalent decode, outside the control store
- is not a micro-operation
- is asserted for EXECUTE TS4 of CAF, for a CLEAR or START console transaction, or during the power-on reset
- initializes controller state according to the controller contracts; the CPU-register effects are the micro-operations of the same TS

Source:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

---

### 8.2 CAF Initialization

Applicable context:

```text
MS = EXECUTE
TS = 4
IR_IS_CAF = 1
```

Assignment:

```text
/INITIALIZE = 0
```

CPU output-drive state:

```text
CPU /INITIALIZE driver = DRIVE_LOW
```

Constraints:

- `/INITIALIZE` is asserted during EXECUTE TS4 and its effects commit at TP4.
- `/INITIALIZE` overrides normal controller activity.
- Controller initialization behavior remains defined by each controller contract.
- Software is responsible for satisfying documented device-idle and safety requirements before executing CAF.
- `/INITIALIZE` must not be inferred from the CAF micro-operation list alone.

Sources:

- [ISA - IOT](../../02-isa/04-iot.md)
- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

---

### 8.3 Front-Panel Clear Initialization

Applicable context:

```text
RUN = 0
FP_CLEAR = 1
```

Assignment:

```text
/INITIALIZE = 0
```

CPU output-drive state:

```text
CPU /INITIALIZE driver = DRIVE_LOW
```

Constraints:

- `/INITIALIZE` is asserted for the console transaction and its effects commit at TP_FP.
- The associated CPU-state changes remain represented by their selected micro-operations and sequencing results.
- `/INITIALIZE` does not replace those internal state assignments.
- Controller initialization behavior remains defined by each controller contract.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md#fp_clear)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

---

### 8.4 Front-Panel Start Initialization

Applicable context:

```text
RUN = 0
FP_START = 1
```

Assignment:

```text
/INITIALIZE = 0
```

CPU output-drive state:

```text
CPU /INITIALIZE driver = DRIVE_LOW
```

Constraints:

- START is CLEAR then CONTINUE in one key. `/INITIALIZE` is asserted for the console transaction and its effects commit at TP_FP, the TP at which `RUN` also becomes 1 ([Sequencing and Internal Direct Control §3.3.3](./01-sequencing-and-internal-control.md#333-start)).
- The associated CPU-state changes remain represented by their selected micro-operations and sequencing results.
- Controller initialization behavior remains defined by each controller contract.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#10-start-operation)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md#fp_start)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

---

### 8.5 Inactive Initialization Output

Applicable context:

- Neither CAF initialization nor an accepted front-panel CLEAR or START applies

```text
NOT (
    MS = EXECUTE
    AND TS = 4
    AND IR_IS_CAF = 1
)
NOT (
    RUN = 0
    AND FP_CLEAR = 1
)
NOT (
    RUN = 0
    AND FP_START = 1
)
```

Assignment:

```text
/INITIALIZE = 1
```

CPU output-drive state:

```text
CPU /INITIALIZE driver = DRIVE_HIGH
```

Constraint:

- `/INITIALIZE` must not be asserted outside the TS or console transaction defined in sections 8.2 to 8.4.

Source:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

---

## 9. Direct-Control Case Summary

```text
Control context                     Direct-control result
----------------------------------  -----------------------------------------
RUN = 1 AND MS = DMA                /DMA_GRANT = 0
Otherwise, including while halted   /DMA_GRANT = 1
External-device IOT, RUN = 1        IOT_ACTIVE = 1
All other control cases             IOT_ACTIVE = 0
CAF initialization interval         /INITIALIZE = 0
Accepted front-panel CLEAR          /INITIALIZE = 0
Accepted front-panel START          /INITIALIZE = 0
All other control cases             /INITIALIZE = 1
DMA ownership                       CPU memory-interface drivers = HIGH_Z
CPU DB read                         CPU DB driver = HIGH_Z
CPU DB write                        CPU DB driver driven from AC
No CPU DB write                     CPU DB driver = HIGH_Z
```

The following output assignments remain owned by micro-operation mappings:

```text
/RD
/WR
```

The following outputs are derived rather than direct-control assignments; the summary above shows their values:

```text
/DMA_GRANT
IOT_ACTIVE
IOA
IOP
/DB_READ
/DB_WRITE
```

The following are external or arbiter-owned rather than CPU direct-control results:

```text
DMA_GRANT_ID
DMA_ENABLE
controller /DMA_REQ[n]
aggregate /DMA_REQ
controller-supplied DMA address
controller-supplied DMA field
controller-supplied DMA write data
controller-supplied DMA transfer direction
```

---

## 10. Explicit Exclusions

This document does not define:

- which DMA controller is selected
- DMA priority
- DMA burst limits
- DMA-controller address progression
- DMA-controller word-count state
- memory-generated read data
- controller-generated DB read data
- external controller response values
- internal electrical driver implementation
- connector assignments
- arbitration logic
- derived `IOA` or `IOP` logic
- micro-operation-owned strobe assignments
- physical pull-resistor values
- undocumented ownership transitions

No CPU-controlled interface value may be supplied by inference when its authoritative source is absent.

---

## 11. Required Invariants

The following invariants apply:

- Logical signal value and output-drive state remain distinct.
- `HIGH_Z` remains distinct from `DRIVE_HIGH`.
- CPU and external ownership of a single-owner interface must not overlap.
- At most one participant may drive a shared data bus.
- CPU memory-interface drivers must be `HIGH_Z` throughout DMA ownership.
- A DMA controller may drive DMA-owned interfaces only with a matching valid grant.
- Memory is the sole `MDB` producer during a memory read.
- The selected CPU or DMA writer is the sole `MDB` producer during a memory write.
- The CPU DB driver must be `HIGH_Z` during a DB read.
- The CPU is the sole DB driver during a CPU DB write.
- `/RD` and `/WR` must not both be asserted.
- `/DB_READ` and `/DB_WRITE` must not both be asserted.
- `/DMA_GRANT` does not select a DMA controller.
- `IOT_ACTIVE` does not itself initiate a DB transfer.
- `/INITIALIZE` remains distinct from associated CPU-state micro-operations.
- Micro-operation-owned assignments must not be duplicated as direct-control assignments.
- Derived outputs must not be represented as encoded direct-control assignments.

---

## 12. Related Documents

- [Direct-Control Model](../07-direct-control-model.md)
- [Control Constraints](../03-control-constraints.md)
- [Invalid Conditions](../06-invalid-conditions.md)
- [Sequencing and Internal Direct Control](./01-sequencing-and-internal-control.md)
- [Control Output Signals](../20-control-output-definitions/00-index.md)
- [Signal Conventions](../../00-overview/98-signal-conventions.md)
- [Bus Semantics](../../05-buses-and-signals/06-bus-semantics.md)
- [Bus Ownership Matrix](../../05-buses-and-signals/08-ownership-matrix.md)
- [Memory Interface](../../06-memory/02-memory-interface.md)
- [DMA & Console Access](../../06-memory/06-dma-and-console-access.md)
- [External IOT Interface](../../07-io/02-external-iot-interface.md)
- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)