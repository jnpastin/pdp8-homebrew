# Class B - Global Control Signals

## 1. Purpose

This document defines Class B signals and their organization within the system.

Class B signals are control signals used by the CPU control system and by CPU interactions with external subsystems.

This document defines:

- Class B signal characteristics
- Distribution scope
- Organizational structure

This document does NOT define:

- signal semantics
- signal encodings
- signal behavior
- control-word structure
- control-flow behavior
- timing behavior

Authoritative signal classifications, constraints, and definitions are maintained in Section 4.

---

## 2. Overview

Class B signals communicate control information.

Class B signals:

- may be single-bit or multi-bit
- may be inputs or outputs
- may be CPU-local or system-distributed
- do not transport general-purpose address values
- do not transport general-purpose data values

Unlike Class A buses, Class B signals represent control information rather than communication paths.

---

## 3. Distribution Scope

### 3.1 CPU-Local

CPU-local signals exist entirely within the CPU implementation.

These signals are not visible outside the CPU boundary.

CPU-local classifications are defined in:

- [Input - Flags](../04-control/10-control-input-definitions/01-flags.md)
- [Input - IR Derived Fields](../04-control/10-control-input-definitions/02-ir-derived-fields.md)
- [Input - Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md)
- [Output - Microarchitecture](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Output - Sequencing](../04-control/20-control-output-definitions/03-sequencing-control-signals.md)

### 3.2 System-Distributed

System-distributed signals are visible outside the CPU boundary.

These signals coordinate CPU interaction with external memory, I/O devices, DMA hardware, and front-panel controls.

System-distributed classifications are defined in:

- [Input - External](../04-control/10-control-input-definitions/04-external-inputs.md)
- [Output - Architectural](../04-control/20-control-output-definitions/02-architectural-control-signals.md)

---

## 4. Input Organization

Control inputs are organized into four domains:

- Primitive Flags
- IR-Derived Signals
- Derived Flags
- External Inputs

---

## 5. Output Organization

Control outputs are organized into three domains:

- Microarchitectural Control Signals
- Architectural Control Signals
- Sequencing Control Signals


---

## 6. Width Classification

### 6.1 Single-Bit Signals

Single-bit Class B signals represent a binary control condition.

Single-bit signals may be either CPU-local or system-distributed.

### 6.2 Multi-Bit Signals

Multi-bit Class B signals represent encoded control information.

Multi-bit signals may be either CPU-local or system-distributed.

---

### 6.3 I/O Address Field (IOA)

#### 6.3.1 Definition

The I/O Address Field (IOA) is a CPU-generated control field used to identify the target I/O device during an I/O operation.

#### 6.3.2 Width

- 6 bits

#### 6.3.3 Characteristics

IOA:

- is a Class B control signal
- is system-distributed
- is multi-bit
- is driven exclusively by the CPU
- is not a shared transport bus
- is not a transport domain

#### 6.3.4 Purpose

IOA carries device-selection information used by I/O operations.

The interpretation of IOA values is defined by the addressed device and the active I/O operation.

#### 6.3.5 Relationship to Control

IOA generation and usage are defined by the control architecture.

This document defines IOA as a classified architectural signal only.

Authoritative definitions are maintained in:

- [Architectural Control Signals](../04-control/20-control-output-definitions/02-architectural-control-signals.md)

---

### 6.4 External IOT Interface Signals

#### 6.4.1 CPU to Controllers

- `IOT_ACTIVE`
- `IOA[5:0]`
- `IOP[2:0]`
- `/DB_READ`
- `/DB_WRITE`
- TS signals
- TP signals

#### 6.4.2 Selected Controller to CPU

- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`
- `/IO_WAIT`

### 6.5 DMA Arbitration Signals

#### 6.5.1 DMA Controllers to Arbiter

- /DMA_REQ[14:0]

The request interface provides 15 DMA priority-channel request lines.  
Each DMA-capable controller asserts exactly one request line corresponding to its configured DMA priority.  
Valid configured DMA priorities are 0 through 14.  
DMA priority 15 is reserved as the no-controller-selected encoding and has no corresponding /DMA_REQ line.

#### 6.5.2 DMA Arbiter to Aggregation Logic

- `DMA_ENABLE`

#### 6.5.3 DMA Aggregation Logic to CPU

- aggregate `/DMA_REQ`

Aggregate `/DMA_REQ` is continuously derived from `DMA_ENABLE` and `/DMA_REQ[14:0]`. It must settle before CPU control samples it at TP4.

#### 6.5.4 CPU to DMA Arbiter and Controllers

- `MS[2:0]`
- `/DMA_GRANT`
- shared TS signals
- shared TP signals

MS provides the current CPU major-state context. The DMA arbiter uses `MS = EXECUTE` and `TS4` to assert combinational `DMA_ENABLE`, allowing pending DMA requests to participate in the TP4 major-state transition decision.
 
`MS` does not grant DMA ownership. DMA ownership requires `/DMA_GRANT` asserted and a matching valid `DMA_GRANT_ID`.

/DMA_GRANT indicates that the CPU has entered DMA service and released the memory interface.  

/DMA_GRANT does not identify a selected controller.

#### 6.5.5 DMA Arbiter to Controllers

- DMA_GRANT_ID[3:0]

DMA_GRANT_ID identifies the DMA priority channel selected by the arbiter.  
DMA_GRANT_ID values 0 through 14 identify valid DMA priority channels.  
DMA_GRANT_ID value 15 indicates that no controller is selected.

### 6.6 Signal Responsibilities

- IOA, IOP, IOT_ACTIVE, /DB_READ, and /DB_WRITE are CPU outputs during external-IOT execution.
- IO_READ_REQ, IO_WRITE_REQ, IO_SKIP_REQ, IO_CLEAR_AC_REQ, and /IO_WAIT are selected-controller outputs and CPU inputs.
- /DMA_REQ[14:0] are controller-to-arbiter priority-channel requests.
- `DMA_ENABLE` is the arbiter-to-aggregation-logic qualification output.
- Aggregate `/DMA_REQ` is the aggregation-logic-to-CPU request.
- Aggregate `/DMA_REQ` is continuously derived from `DMA_ENABLE` and `/DMA_REQ[14:0]`.
- /DMA_GRANT is the CPU-generated authorization indicating that the CPU has released the memory interface during MS = DMA.
- DMA_GRANT_ID[3:0] is the arbiter-generated controller-selection field.
- DMA_GRANT_ID values 0 through 14 identify valid configured DMA priority channels.
- DMA_GRANT_ID value 15 indicates that no controller is selected.
- A controller owns the DMA interfaces only while /DMA_GRANT is asserted and DMA_GRANT_ID matches its configured DMA priority.
- During DMA, only the controller selected by /DMA_GRANT and DMA_GRANT_ID may drive /RD and /WR.
- During CPU memory operations, CPU control drives /RD and /WR.
- `MS[2:0]` is a CPU-generated control field distributed to the DMA arbiter.
- The DMA arbiter uses `MS = EXECUTE` and `TS4` to assert combinational `DMA_ENABLE`.
- `DMA_ENABLE` is not stored state.
- The DMA arbiter must not modify or participate in generating `MS`.

Detailed I/O behavior is defined in [I/O Architecture](../07-io/01-io-architecture.md).  
Detailed DMA arbitration is defined in [DMA Arbitration](../07-io/06-dma-arbitration.md).

---

## 7. Relationship to Other Signal Classes

Class A signals provide address and data transport.

Class B signals provide control information.

---

## 8. Summary

Class B signals comprise the complete control-signal infrastructure of the system.

This document defines the classification and organization of those signals. Signal definitions and behavior are defined in Section 4.
