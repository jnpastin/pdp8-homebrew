# Architectural Control Signals

## 1. Purpose

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

## 2. Scope

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

## 3. Global Properties

### 3.1 Polarity

- Signals are active-high internally unless specified otherwise
- External representation may be active-low

Defined in:
- [Signal Conventions](../../00-overview/98-signal-conventions.md)

---

### 3.2 Timing Model

All architectural signals are level-based.

- asserted during TS
- observed during TS
- must be stable before TP
- have no edge-triggered semantics

Timing definitions:
- [Timing Model](../../09-timing/README.md)

---

### 3.3 Completeness Requirement

For every TS:

- every architectural signal must have a defined value
- no signal may be implicit or undefined

---

## 4. Signal Definitions

---

### 4.1 Memory Read (/RD)

**Name**  
/RD

**Polarity**  
Active-low externally (`/RD`), active-high internally

**Domain**  
Architectural

**Bit Width:** 1

**Description:** Indicates that the CPU is requesting a memory read operation.

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
- must not be asserted simultaneously with `/WR`
- does not imply data transfer into any register
- does not define MDB validity or timing behavior
- does not select the memory address source
- does not select the MDB data source
- must be paired with [MEM_READ_TO_MB](../../03-microarchitecture/02-micro-operations.md#mem_read_to_mb) or DMA

---

### 4.2 Memory Write (/WR)

**Name**  
/WR

**Polarity**  
Active-low externally (`/WR`), active-high internally

**Domain**  
Architectural

**Bit Width:** 1

**Description:** Indicates that the CPU is requesting a memory write operation.

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
- must not be asserted simultaneously with `/RD`
- does not select the memory address source
- does not select the MDB data source
- must be paired with a valid memory-write μop or DMA
- valid memory-write μops are:
  - [MEM_WRITE_FROM_MB](../../03-microarchitecture/02-micro-operations.md#mem_write_from_mb)
  - [MEM_WRITE_FROM_FP_SR](../../03-microarchitecture/02-micro-operations.md#mem_write_from_fp_sr)
  
---

### 4.3 /DB_READ

**Category:** Architectural Control Signal  

**Bit Width:** 1

**Description:** Indicates that the CPU is performing an I/O read operation and will sample the System Data Bus (DB) during this timing state.

**Polarity:** Active-low (/DB_READ)

**Role:**
- Identifies the time window during which the CPU captures data from DB
- Must be paired with DB_READ_TO_AC for valid operation

**Behavior:**
- When asserted, the CPU samples DB and loads the value into AC via DB_READ_TO_AC
- Devices may drive DB based on device selection (IOA) and internal behavior

**Constraints:**
- Must not be asserted concurrently with /DB_WRITE
- Must not be asserted without DB_READ_TO_AC
- CPU must not drive DB while /DB_READ is asserted
- DB must be driven by at most one external device

---

### 4.4 /DB_WRITE

**Category:** Architectural Control Signal  

**Bit Width:** 1

**Description:** Indicates that the CPU is performing an I/O write operation and will drive the System Data Bus (DB) during this timing state.

**Polarity:** Active-low (/DB_WRITE)

**Role:**
- Enables CPU-driven output onto DB
- Must be paired with DB_WRITE_FROM_AC for valid operation

**Behavior:**
- When asserted, the CPU drives DB using the value contained in AC via DB_WRITE_FROM_AC
- Selected I/O devices may capture DB during this interval

**Constraints:**
- Must not be asserted concurrently with /DB_READ
- Must not be asserted without DB_WRITE_FROM_AC
- CPU is the sole driver of DB when this signal is asserted
- External devices must not drive DB during this interval

---

### 4.5 /DMA_GRANT

**Name** /DMA_GRANT  
**Polarity** Active-low  
**Domain** Architectural  

**Bit Width:** 1

**Description:** Indicates that the CPU is in `MS = DMA` and has released normal CPU ownership of the memory interface.

When asserted:

- the external DMA arbiter is authorized to grant DMA ownership;
- normal CPU instruction execution is suspended;
- CPU-generated memory-cycle requests remain inactive.

`/DMA_GRANT` does not identify the selected DMA controller.

Controller selection uses the grant identity defined in [DMA Arbitration](../../07-io/06-dma-arbitration.md)

**Preconditions**

- `MS = DMA`
- CPU instruction execution entered DMA through a valid major-state transition

`/DMA_REQ` is not required to remain asserted throughout the DMA major state. The arbiter may deassert `/DMA_REQ` during DMA TS4 to select exit to FETCH at TP4 while `/DMA_GRANT` remains asserted until the DMA major state ends.

**Timing**
- asserted during DMA major-state cycles
- remains asserted while control remains in `MS = DMA`
- deasserted when control exits DMA service

**Constraints**
- must be generated only by the control word
- must not be asserted during normal instruction execution
- must not be asserted concurrently with CPU-initiated `/RD` or `/WR`
- does not itself define DMA address, data, direction, or device selection
- does not modify CPU architectural state
- does not modify `RUN` or `HLT_REQ`
- external DMA ownership and multi-device arbitration are outside CPU control and must be resolved before or during DMA service

**Consumed By**
- external DMA-capable device interface
- external DMA device arbitration logic

---

### 4.6 I/O Address Bus (IOA[5:0])

**Name**  
IOA[5:0]

**Polarity**  
Active-high

**Domain**  
Architectural

**Bit Width:** 6

**Description:** Specifies the target I/O device address during execution of IOT instructions.

Properties:

- derived directly from IR
- driven by control during EXECUTE
- used by external devices to determine selection

**Preconditions**

- instruction class is IOT

Defined in:
- [IOT Execution Model](../../03-microarchitecture/06-iot-execution.md)

**Timing:**

- Valid throughout external-IOT EXECUTE.
- Stable from TS1 through TP4.

**Constraints:**

- Meaningful to external controllers only while `IOT_ACTIVE` is asserted.
- Must not be modified by a micro-operation.
- Does not imply data transfer or direction.
- Does not define device behavior.

---

### 4.7 I/O Operation Field (`IOP[2:0]`)

**Name:**  
IOP[2:0]  

**Polarity:**  
Active-high  

**Domain:**  
Architectural  

**Bit Width:** 3

**Description:** Presents `IR[2:0]` unchanged to external I/O controllers during an external IOT.

**Timing:**

- Valid throughout external-IOT EXECUTE.
- Stable from TS1 through TP4.

**Constraints:**

- Does not select a controller.
- Does not directly determine DB direction.
- Does not define controller behavior.
- Must not be interpreted unless `IOT_ACTIVE` is asserted.
- Must not be modified by a micro-operation.

**Consumed By:**

- external I/O controllers

### 4.8 External IOT Active (`IOT_ACTIVE`)

**Name:**  
IOT_ACTIVE  

**Polarity:**  
Active-high  

**Domain:**  
Architectural  

**Bit Width:** 1

**Description:** Identifies execution of an external IOT and qualifies IOA, IOP, controller responses, and I/O wait behavior.

**Timing:**

- Asserted throughout EXECUTE for external-device IOT instructions.
- Deasserted for CPU-internal IOT instructions.
- Deasserted for all non-IOT instructions.

**Constraints:**

- Does not itself cause data movement.
- Does not itself cause controller state change.
- Must be paired with IOA, IOP, TS, and TP according to the controller contract.

**Consumed By:**

- external I/O controllers
- external IOT response qualification
- I/O wait qualification

---

### 4.9 System Initialization (/INITIALIZE)

**Name:** 
/INITIALIZE  

**Polarity:** 
Active-low  

**Domain:** 
Architectural  

**Bit Width:** 1

**Description:** System-wide reset signal asserted by CAF or an accepted front-panel CLEAR operation.

**Sources:**
- CAF during the EXECUTE TP4 TSTEP
- an accepted front-panel CLEAR operation while RUN = 0

**Assertion Condition:**

```text
INITIALIZE_ASSERTED =
    (
        IR_IS_CAF
        AND (MS = EXECUTE)
        AND (TP = 4)
    )
    OR
    (
        FP_CLEAR_ACCEPTED
    )
```

`/INITIALIZE` is asserted when `INITIALIZE_ASSERTED = 1` and deasserted otherwise.

`FP_CLEAR_ACCEPTED` represents one synchronized, debounced, and re-armed acceptance event derived from FP_CLEAR. It is not stored as a pending request.

**Behavior:**
- clears AC
- clears L
- clears IE
- causes each I/O controller to enter its documented initialized state

**Preserved Processor State:**
- II
- CIFP
- DIF
- IF
- DF
- IB

**Timing:**
- asserted for exactly one TSTEP
- CAF asserts /INITIALIZE during the EXECUTE TP4 TSTEP
- an accepted front-panel CLEAR operation asserts /INITIALIZE for one synchronized TSTEP while the processor is halted
- all resulting state changes commit at the TP ending the asserted TSTEP
- /INITIALIZE is deasserted before the next TSTEP begins

**Priority:**
- when asserted, /INITIALIZE overrides all controller commands, transfers, flag updates, interrupt requests, DMA activity, and other controller-local actions sampled during the same TSTEP
- only the controller's documented initialized state commits

**Constraints:**
- front-panel CLEAR is accepted only when RUN = 0
- front-panel CLEAR is ignored when RUN = 1
- one /INITIALIZE pulse is generated per distinct accepted front-panel CLEAR press
- a held front-panel CLEAR input must not generate repeated /INITIALIZE pulses
- front-panel CLEAR is re-armed only after the synchronized input is released
- CAF has no effect unless execution reaches EXECUTE TP4
- CAF and front-panel CLEAR produce the same /INITIALIZE action
- /INITIALIZE does not modify II, CIFP, DIF, IF, DF, or IB
- controller-specific initialized states are defined in the corresponding controller documents

---

## 5. Interaction Rules

---

### 5.1 Mutual Exclusion

The following must never occur:

- /RD and /WR asserted simultaneously

---

### 5.2 Domain Separation

Architectural control signals must not:

- select datapath sources
- enable register loads
- define ALU operations

They may only:

- initiate external operations
- define system-level interactions

/INITIALIZE is the only defined exception. It directly establishes the documented initialized state of AC, L, IE, and each I/O controller without selecting datapath sources or invoking micro-operations.

---

### 5.3 No Implicit Data Movement

Architectural signals:

- do not move data
- do not imply valid data presence

All data movement requires:

- explicit μops
- explicit register loads

Defined in:
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)

---

### 5.4 Control Responsibility

Control must ensure:

- all signal preconditions are satisfied before assertion
- all required data is stable before TP
- no conflicting external operations are initiated

---

### 5.5 Cross-Domain Binding Requirement

Architectural signals participate in externally visible operations only when paired with corresponding μops, except for /INITIALIZE, whose direct processor and controller effects are defined by its signal contract.

Defined in:
- [Cross-Domain Operation Binding Rules](../03-control-constraints.md#12-cross-domain-operation-binding-rules)

This ensures:

- no implicit operations
- complete and deterministic behavior per TS

---

## 6. Summary

Architectural control signals define the **external behavior of the CPU**.

They:

- initiate memory operations (/RD, /WR)
- select I/O devices (IOA)
- grant DMA service ('/DMA_GRANT')
- initialize processor and controller state (/INITIALIZE)

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