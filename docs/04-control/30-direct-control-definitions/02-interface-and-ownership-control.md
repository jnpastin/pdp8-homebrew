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

The required `AB_SRC` and `MFB_SRC` derivations are defined in [Sequencing & Internal Control](./01-sequencing-and-internal-control.md).

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

- originates from the control word
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
MS = DMA
```

Assignment:

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

- `/DMA_GRANT` remains asserted throughout `MS = DMA`.
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

Assignment:

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

External ownership:

```text
selected controller drives MFB
selected controller drives AB
selected controller asserts /RD
selected controller deasserts /WR
memory drives MDB
```

Constraints:

- Memory is the sole `MDB` producer.
- The selected controller must not drive `MDB`.
- The controller captures `MDB` at TP2.
- No CPU control assignment may replace the controller-supplied address, field, or direction.

Source:

- [DMA Interface](../../07-io/05-dma-interface.md)

---

### 5.5 DMA Ownership Release

When a controller selection terminates:

- the selected controller releases `MFB`, `AB`, `MDB`, `/RD`, and `/WR` at DMA TP4
- the arbiter sets `DMA_GRANT_ID` to the no-controller-selected value at DMA TP4
- CPU control deasserts `/DMA_GRANT` when control exits `MS = DMA`
- CPU ownership resumes during the following FETCH TS1

Constraints:

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
DB_WRITE_FROM_AC is not selected
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
DB_WRITE_FROM_AC is selected
```

Micro-operation assignments:

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
- `/DB_WRITE` must be paired with `DB_WRITE_FROM_AC`.
- The `/DB_WRITE` assignment and AC-to-DB datapath selection remain owned by the `DB_WRITE_FROM_AC` micro-operation mapping rather than a separate direct-control result.

Sources:

- [Micro Operations](../../03-microarchitecture/02-micro-operations.md)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

### 6.3 CPU DB Read

Applicable context:

```text
DB_READ_TO_AC is selected
```

Micro-operation assignments:

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
- The `/DB_READ` assignment and DB-to-AC datapath selection remain owned by the `DB_READ_TO_AC` micro-operation mapping rather than a separate direct-control result.

Sources:

- [Micro Operations](../../03-microarchitecture/02-micro-operations.md)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

## 7. External-IOT Qualification

### 7.1 IOT Active Result

`IOT_ACTIVE` indicates that the CPU is executing an external-device IOT and that controller-facing `IOA`, `IOP`, and response inputs are valid for the documented external-IOT interaction.

`IOT_ACTIVE`:

- originates from the control word
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
MS = EXECUTE
IR_IS_EXTERNAL_IOT = 1
```

Assignment:

```text
IOT_ACTIVE = 1
```

Related derived values:

```text
IOA = IR_IOA
IOP = IR[2:0]
```

Constraints:

- `IOA` and `IOP` remain derived outputs rather than direct-control assignments.
- Only the address-matched controller may respond.
- Controller response inputs are valid only while `IOT_ACTIVE = 1`.
- `IOT_ACTIVE` does not itself determine whether a read, write, skip, clear-AC, or wait response is accepted.
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
    MS = EXECUTE
    AND IR_IS_EXTERNAL_IOT = 1
)
```

Assignment:

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

- originates from the control word
- is not a micro-operation
- is asserted for one timing state
- initializes CPU and controller state according to the applicable initialization contracts

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

- `/INITIALIZE` is asserted for the documented one-TSTEP interval.
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

- `/INITIALIZE` is asserted for the documented one-TSTEP interval.
- The associated CPU-state changes remain represented by their selected micro-operations and sequencing results.
- `/INITIALIZE` does not replace those internal state assignments.
- Controller initialization behavior remains defined by each controller contract.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md#fp_clear)
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

---

### 8.4 Inactive Initialization Output

Applicable context:

- Neither CAF initialization nor accepted front-panel CLEAR applies

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

- `/INITIALIZE` must not remain asserted beyond its documented one-TSTEP interval.

Source:

- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

---

## 9. Direct-Control Case Summary

```text
Control context                     Direct-control result
----------------------------------  -----------------------------------------
MS = DMA                            /DMA_GRANT = 0
MS != DMA                           /DMA_GRANT = 1
External-device IOT execution       IOT_ACTIVE = 1
All other control cases             IOT_ACTIVE = 0
CAF initialization interval         /INITIALIZE = 0
Accepted front-panel CLEAR          /INITIALIZE = 0
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
/DB_READ
/DB_WRITE
```

The following outputs are derived rather than direct-control assignments:

```text
IOA
IOP
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
- [Sequencing & Internal Control](./01-sequencing-and-internal-control.md)
- [Control Output Signals](../20-control-output-definitions/00-index.md)
- [Signal Conventions](../../00-overview/98-signal-conventions.md)
- [Bus Semantics](../../05-buses-and-signals/06-bus-semantics.md)
- [Bus Ownership Matrix](../../05-buses-and-signals/08-ownership-matrix.md)
- [Memory Interface](../../06-memory/02-memory-interface.md)
- [DMA & Console Access](../../06-memory/06-dma-and-console-access.md)
- [External IOT Interface](../../07-io/02-external-iot-interface.md)
- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)