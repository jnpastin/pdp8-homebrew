# Architectural Control Signals

## Purpose

Defines all control signals that produce externally observable system behavior.

These signals coordinate:
- memory operations
- I/O device selection

Architectural control signals:
- originate from the control word
- are visible outside the CPU
- do not expose internal datapath behavior

See:
- [Control Model](../01-control-model.md)
- [Control Constraints](../03-control-constraints.md)

---

## 1. Scope

Architectural control signals define **when external subsystems perform actions**.

They:
- initiate memory transactions
- select I/O devices

They do NOT:
- transfer data
- control internal registers
- define ALU or datapath behavior

Bus behavior, ownership, and electrical semantics are defined in:

- [Bus Semantics](../../05-buses-and-signals/06-bus-semantics.md)

---

## 2. Global Properties

### 2.1 Polarity

- Signals are active-high internally unless specified otherwise
- External representation may be active-low

Defined in:
- [Signal Conventions](../../00-overview/98-signal-conventions.md)

---

### 2.2 Timing Model

All architectural signals are level-based.

- asserted during TS
- observed during TS
- must be stable before TP
- have no edge-triggered semantics

Timing definitions:
- [Timing Model](../../09-timing/README.md)

---

### 2.3 Completeness Requirement

For every TS:

- every architectural signal must have a defined value
- no signal may be implicit or undefined

---

## 3. Signal Definitions

---

### 3.1 Memory Read (RD)

**Name**  
RD

**Polarity**  
Active-low externally (`/RD`), active-high internally

**Domain**  
Architectural

**Description**  
Indicates that the CPU is requesting a memory read operation.

When asserted:
- memory must provide the contents of the address selected by `AB_SRC` and `MFB_SRC`

**Preconditions**
- the address selected by `AB_SRC` and `MFB_SRC` is valid
- the selected MDB data source is valid
- `AB_SRC` and `MFB_SRC` contain valid encodings

**Timing**
- asserted during the TS corresponding to a read operation
- memory must satisfy data availability before TP

**Constraints**
- must not be asserted simultaneously with `WR`
- does not imply data transfer into any register
- does not define MDB validity or timing behavior
- does not select the memory address source
- does not select the MDB data source
- must be paired with [MEM_READ_TO_MB](../../03-microarchitecture/02-micro-operations.md#mem_read_to_mb) or DMA

---

### 3.2 Memory Write (WR)

**Name**  
WR

**Polarity**  
Active-low externally (`/WR`), active-high internally

**Domain**  
Architectural

**Description**  
Indicates that the CPU is requesting a memory write operation.

When asserted:
- memory must store the selected data into the address selected by `AB_SRC` and `MFB_SRC`

**Preconditions**
- the address selected by `AB_SRC` and `MFB_SRC` is valid
- the selected MDB data source is valid
- `AB_SRC` and `MFB_SRC` contain valid encodings

**Timing**
- asserted during the TS corresponding to a write operation
- data must be stable before TP

**Constraints**
- must not be asserted simultaneously with `RD`
- does not select the memory address source
- does not select the MDB data source
- must be paired with a valid memory-write μop or DMA
- valid memory-write μops are:
  - [MEM_WRITE_FROM_MB](../../03-microarchitecture/02-micro-operations.md#mem_write_from_mb)
  - [MEM_WRITE_FROM_SR](../../03-microarchitecture/02-micro-operations.md#mem_write_from_sr)
  
---

### 3.3 DB_READ

**Category:** Architectural Control Signal  
**Description:** Indicates that the CPU is performing an I/O read operation and will sample the System Data Bus (DB) during this time state.

**Polarity:** Active-low (/DB_READ)

**Role:**
- Identifies the time window during which the CPU captures data from DB
- Must be paired with DB_READ_TO_AC for valid operation

**Behavior:**
- When asserted, the CPU samples DB and loads the value into AC via DB_READ_TO_AC
- Devices may drive DB based on device selection (IOA) and internal behavior

**Constraints:**
- Must not be asserted concurrently with DB_WRITE
- Must not be asserted without DB_READ_TO_AC
- CPU must not drive DB while DB_READ is asserted
- DB must be driven by at most one external device

---

### 3.4 DB_WRITE

**Category:** Architectural Control Signal  
**Description:** Indicates that the CPU is performing an I/O write operation and will drive the System Data Bus (DB) during this time state.

**Polarity:** Active-low (/DB_WRITE)

**Role:**
- Enables CPU-driven output onto DB
- Must be paired with DB_WRITE_FROM_AC for valid operation

**Behavior:**
- When asserted, the CPU drives DB using the value contained in AC via DB_WRITE_FROM_AC
- Selected I/O devices may capture DB during this interval

**Constraints:**
- Must not be asserted concurrently with DB_READ
- Must not be asserted without DB_WRITE_FROM_AC
- CPU is the sole driver of DB when this signal is asserted
- External devices must not drive DB during this interval

---

### 3.5 DMA_GRANT

**Name** DMA_GRANT  
**Polarity** Active-high  
**Domain** Architectural  

**Description**  
Indicates that the CPU has entered DMA service and has released normal CPU ownership of memory-cycle control.

When asserted:
- the external DMA-capable device or device-side DMA arbiter may perform memory access
- normal CPU instruction execution is suspended
- CPU-generated memory-cycle requests must remain inactive

**Preconditions**
- `MS = DMA`
- `DMA_REQ = 1`
- CPU instruction execution has reached a valid DMA entry boundary

**Timing**
- asserted during DMA major-state cycles
- remains asserted while control remains in `MS = DMA`
- deasserted when control exits DMA service

**Constraints**
- must be generated only by the control word
- must not be asserted during normal instruction execution
- must not be asserted concurrently with CPU-initiated `RD` or `WR`
- does not itself define DMA address, data, direction, or device selection
- does not modify CPU architectural state
- does not modify `RUN` or `HLT_REQ`
- external DMA ownership and multi-device arbitration are outside CPU control and must be resolved before or during DMA service

**Consumed By**
- external DMA-capable device interface
- external DMA device arbitration logic

---

### 3.6 I/O Address Bus (IOA[5:0])

**Name**  
IOA[5:0]

**Polarity**  
Active-high

**Domain**  
Architectural

**Description**  
Specifies the target I/O device address during execution of IOT instructions.

Properties:

- derived directly from IR
- driven by control during EXECUTE
- used by external devices to determine selection

**Preconditions**

- instruction class is IOT

Defined in:
- [IOT Execution Model](../../03-microarchitecture/06-iot-execution.md)

**Timing**

- valid during all TS of EXECUTE for IOT instructions

**Constraints**

- must not be driven during non-IOT instructions
- must not be modified by μops
- does not imply data transfer or direction
- does not define device behavior

---

## 4. Interaction Rules

---

### 4.1 Mutual Exclusion

The following must never occur:

- RD and WR asserted simultaneously

---

### 4.2 Domain Separation

Architectural control signals must not:

- select datapath sources
- enable register loads
- define ALU operations

They may only:

- initiate external operations
- define system-level interactions

---

### 4.3 No Implicit Data Movement

Architectural signals:

- do not move data
- do not imply valid data presence

All data movement requires:

- explicit μops
- explicit register loads

Defined in:
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)

---

### 4.4 Control Responsibility

Control must ensure:

- all signal preconditions are satisfied before assertion
- all required data is stable before TP
- no conflicting external operations are initiated

---

### 4.5 Cross-Domain Binding Requirement

Architectural signals participate in externally visible operations only
when paired with corresponding μops.

Defined in:
- [Cross-Domain Operation Binding Rules](../03-control-constraints.md#11-cross-domain-operation-binding-rules)

This ensures:

- no implicit operations
- complete and deterministic behavior per TS

---

## 5. Summary

Architectural control signals define the **external behavior of the CPU**.

They:

- initiate memory operations (RD, WR)
- select I/O devices (IOA)
- grant DMA service ('DMA_GRANT')

They do not:

- control datapath behavior
- move data
- define bus semantics

All behavior is:

- explicit
- deterministic
- fully defined per TS

This preserves:

- domain separation
- control completeness
- system-level correctness

See:

- [Control Model](../01-control-model.md)
- [Control Constraints](../03-control-constraints.md)
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)