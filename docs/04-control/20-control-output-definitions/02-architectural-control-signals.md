# Architectural Control Signals

## 1. Purpose

Defines all control signals that produce externally observable system behavior.

These signals coordinate:
- memory operations
- I/O device selection

Architectural control signals:
- are specified by the control word, or derived as section 3.2 and their definitions state
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
- must be stable before TP and through its end
- have no edge-triggered semantics

The control word may take transient values for up to `T_CS` after each TS boundary ([Timing Architecture §11](../../09-timing/02-timing-architecture.md#11-control-word-settling)). Signals that act while asserted are therefore presented only within a validity window:

| Signal | Presented when |
|---|---|
| `/RD` | the control word asserts it, `CW_VALID` is asserted, and the CPU is not in the EXECUTE of an IOT |
| `/DB_READ` | `IOT_TRANSFER = READ` and `DB_VALID` is asserted |
| `/DB_WRITE` | `IOT_TRANSFER = WRITE` and `DB_VALID` is asserted |
| CPU drive onto MDB (`MDB_SRC` = MB or FP_SR) | the control word selects it, `CW_VALID` is asserted, and the CPU is not in the EXECUTE of an IOT |
| `/WR` | the control word asserts it; memory acts on it only during `/WR_PULSE`, so it needs no window |
| `/INITIALIZE`, CAF and front-panel CLEAR | `INITIALIZE_ASSERTED` (section 4.9), decoded by gates, and `CW_VALID` is asserted |
| `/INITIALIZE`, power-on | the power-on reset is active ([Timing Terminology §3.4](../../09-timing/01-terminology.md#34-power-on-reset)) |
| `/DMA_GRANT`, `IOT_ACTIVE`, `INSTR_END` | always; derived from registered state, so they do not glitch (sections 4.5, 4.8, and 4.10) |
| `IOA`, `IOP` | always; taken from IR |

Each window is a gate on the signal: an OR with the inverted window for an active-low signal, an AND for an active-high one. The DB strobes are decoded outside the control store, because the control-store address carries controller responses that may change while their window is open. The control word's `/DB_READ` and `/DB_WRITE` fields specify the same values. `/INITIALIZE` is decoded for the same reason. `/RD` and the MDB drive are gated off by `MS_EFF_IS_EXECUTE AND IR_IS_IOT`, so a changing response or request cannot glitch them. An IOT's EXECUTE has no memory operation. The gate does not act in FETCH, so the IOT itself is read normally, nor in DEFER, INTERRUPT, DMA, or while halted.

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

**Mnemonic:** /RD  
**Name:** Memory Read  
**Polarity:** Active-low externally (`/RD`), active-high internally  
**Domain:** Architectural  

**Bit Width:** 1

**Default Value:** 1  
**Explicit Value Required:** Yes  
**Value Required When:** Always  

**Encoding:**
```text
0 → asserted
1 → deasserted
```

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

**Used by μops:**
- [MEM_READ_TO_MB](../../03-microarchitecture/02-micro-operations.md#mem_read_to_mb) = 0

---

### 4.2 Memory Write (/WR)

**Mnemonic:** /WR  
**Name:** Memory Write  
**Polarity:** Active-low externally (`/WR`), active-high internally  
**Domain:** Architectural  

**Bit Width:** 1

**Default Value:** 1  
**Explicit Value Required:** Yes  
**Value Required When:** Always  

**Encoding:**
```text
0 → asserted
1 → deasserted
```

**Description:** Indicates that the CPU is requesting a memory write operation.

When asserted:
- memory must store the selected data into the address selected by `AB_SRC` and `MFB_SRC`, during `/WR_PULSE`

**Preconditions**
- the address selected by `AB_SRC` and `MFB_SRC` is valid
- the selected MDB data source is valid
- `AB_SRC` and `MFB_SRC` contain valid encodings

**Timing**
- asserted during the TS corresponding to a write operation
- data must be stable before TP and through its end

**Constraints**
- must not be asserted simultaneously with `/RD`
- does not select the memory address source
- does not select the MDB data source
- must be paired with a valid memory-write μop or DMA

**Used by μops:**
- [MEM_WRITE_FROM_MB](../../03-microarchitecture/02-micro-operations.md#mem_write_from_mb) = 0
- [MEM_WRITE_FROM_FP_SR](../../03-microarchitecture/02-micro-operations.md#mem_write_from_fp_sr) = 0
  
---

### 4.3 /DB_READ

**Mnemonic:** /DB_READ  
**Name:** DB Read  
**Category:** Architectural Control Signal  

**Bit Width:** 1

**Default Value:** 1  
**Explicit Value Required:** Yes  
**Value Required When:** Always  

**Encoding:**
```text
0 → asserted
1 → deasserted
```

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

**Used by μops:**
- [DB_READ_TO_AC](../../03-microarchitecture/02-micro-operations.md#db_read_to_ac) = 0

---

### 4.4 /DB_WRITE

**Mnemonic:** /DB_WRITE  
**Name:** DB Write  
**Category:** Architectural Control Signal  

**Bit Width:** 1

**Default Value:** 1  
**Explicit Value Required:** Yes  
**Value Required When:** Always  

**Encoding:**
```text
0 → asserted
1 → deasserted
```

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

**Used by μops:**

- [DB_WRITE_FROM_AC](../../03-microarchitecture/02-micro-operations.md#db_write_from_ac) = 0

---

### 4.5 /DMA_GRANT

**Mnemonic:** /DMA_GRANT  
**Name:** DMA Grant  
**Polarity:** Active-low  
**Domain:** Architectural  

**Bit Width:** 1

**Default Value:** 1  
**Explicit Value Required:** No  
**Value Required When:** Always  

**Description:** Indicates that the CPU is in `MS = DMA` and has released normal CPU ownership of the memory interface.

**Derivation:**

```text
/DMA_GRANT = NOT (MS_EFF = DMA)
```

`/DMA_GRANT` is decoded from `MS_EFF` ([Control Store Organization §5.1](../08-control-store-organization.md#51-major-state-and-timing-state-codes)) by a comparator. It is not stored in the control word, so it stays clean across TS boundaries for the whole DMA major state and is deasserted while halted.

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
- must be generated only by the `MS_EFF` decode
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

**Mnemonic:** IOA[5:0]  
**Name:** I/O Address Bus  
**Polarity:** Active-high  
**Domain:** Architectural  

**Bit Width:** 6

**Default Value:** N/A  
**Explicit Value Required:** No  
**Value Required When:** Instruction class is IOT  

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

**Mnemonic:** IOP[2:0]  
**Name:** I/O Operation Field  
**Polarity:** Active-high  
**Domain:** Architectural  

**Bit Width:** 3

**Default Value:** N/A  
**Explicit Value Required:** No  
**Value Required When:** Instruction class is IOT  

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

**Mnemonic:** IOT_ACTIVE  
**Name:** External IOT Active  
**Polarity:** Active-high  
**Domain:** Architectural  

**Bit Width:** 1

**Default Value:** 0  
**Explicit Value Required:** No  
**Value Required When:** Always  

**Description:** Identifies execution of an external IOT and qualifies IOA, IOP, controller responses, and I/O wait behavior.

**Derivation:**

```text
IOT_ACTIVE = MS_EFF_IS_EXECUTE AND IR_IS_EXTERNAL_IOT
```

`IOT_ACTIVE` is formed by one gate from `MS_EFF_IS_EXECUTE` and the `IR_IS_EXTERNAL_IOT` predecode. It is not stored in the control word, so it stays clean across TS boundaries for the whole external-IOT EXECUTE major state.

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

**Mnemonic:** /INITIALIZE  
**Name:** System Initialization  
**Polarity:** Active-low  
**Domain:** Architectural  

**Bit Width:** 1

**Default Value:** 1  
**Explicit Value Required:** Yes  
**Value Required When:** Always  

**Description:** System-wide reset signal to the I/O controllers, asserted by CAF, an accepted front-panel CLEAR operation, or the power-on reset.

**Sources:**
- CAF during EXECUTE TS4
- an accepted front-panel CLEAR operation during its console transaction while RUN = 0
- the power-on reset, which ends with a CLEAR transaction ([Timing Terminology §3.4](../../09-timing/01-terminology.md#34-power-on-reset))

**Assertion Condition:**

```text
INITIALIZE_ASSERTED =
    (
        IR_IS_CAF
        AND (MS = EXECUTE)
        AND (TS = 4)
    )
    OR
    (
        RUN = 0
        AND FP_CLEAR
    )
```

`/INITIALIZE` is asserted when `INITIALIZE_ASSERTED = 1` and deasserted otherwise.

While halted, `FP_CLEAR` is the latched accepted console command ([External Inputs §4.1](../10-control-input-definitions/04-external-inputs.md#41-console-command-acceptance)). It is held for one console transaction and is not stored as a pending request.

**Behavior:**
- causes each I/O controller to enter its documented initialized state

The CPU's AC, L, and IE are cleared by the `AC_CLEAR`, `L_CLEAR`, and `IE_CLEAR` micro-operations of CAF and CLEAR in the same TS, including the CLEAR that ends the power-on reset; `/INITIALIZE` has no direct CPU-register effect.

**Preserved Processor State:**
- II
- CIFP
- DIF
- IF
- DF
- IB

**Timing:**
- CAF asserts /INITIALIZE during EXECUTE TS4; resulting state changes commit at TP4, and /INITIALIZE is deasserted when TS4 ends
- an accepted front-panel CLEAR operation asserts /INITIALIZE for its whole console transaction while the processor is halted ([Major State Timing §8](../../09-timing/03-major-state-timing.md#8-halted-state-and-console-transactions)); resulting state changes commit at the console TP (TPC), and /INITIALIZE is deasserted when the transaction ends
- /INITIALIZE is sampled only at that TP; controllers must not act on its level before the TP

**Priority:**
- when asserted, /INITIALIZE overrides all controller commands, transfers, flag updates, interrupt requests, DMA activity, and other controller-local actions that would otherwise commit at the same TP
- only the controller's documented initialized state commits

**Constraints:**
- front-panel CLEAR is accepted only when RUN = 0
- front-panel CLEAR is ignored when RUN = 1
- one /INITIALIZE assertion is generated per distinct accepted front-panel CLEAR press
- a held front-panel CLEAR input must not generate repeated /INITIALIZE assertions
- front-panel CLEAR is re-armed only after the synchronized input is released
- CAF has no effect unless execution reaches EXECUTE TP4
- CAF and front-panel CLEAR produce the same initialization result
- /INITIALIZE does not modify II, CIFP, DIF, IF, DF, or IB
- controller-specific initialized states are defined in the corresponding controller documents

---

### 4.10 Instruction End (INSTR_END)

**Mnemonic:** INSTR_END  
**Name:** Instruction End  
**Polarity:** Active-high  
**Domain:** Architectural  

**Bit Width:** 1

**Default Value:** 0  
**Explicit Value Required:** No  
**Value Required When:** Always  

**Description:** Marks the TS4 of an instruction's last major state, at whose TP4 the instruction completes.

**Derivation:**

```text
INSTR_END =
    (TS = 4)
    AND (
            (MS_EFF = EXECUTE)
         OR (MS_EFF = FETCH AND IR_NO_EXECUTE AND NOT IR_INDIRECT)
         OR (MS_EFF = DEFER AND IR_NO_EXECUTE)
    )
```

`INSTR_END` is decoded by gates from `MS_EFF`, TS, and the predecodes `IR_NO_EXECUTE` and `IR_INDIRECT` ([IR-Derived Fields](../10-control-input-definitions/02-ir-derived-fields.md#ir_no_execute)). Every input is registered state that changes only as a TP ends, so `INSTR_END` does not glitch within a TS. It is not stored in the control word: a control-store output would feed back through the arbiter's `DMA_ENABLE` and aggregate `/DMA_REQ` into the sequencer slice's address within the same TS4. It is deasserted while halted (`MS_EFF = HALTED`).

The derivation restates the instruction-completion condition of [Sequencing and Internal Control §3](../30-direct-control-definitions/01-sequencing-and-internal-control.md#3-sequencing-control); the two must agree.

**Timing**
- asserted for the whole of the TS4 that ends an instruction
- deasserted in every other TS, in INTERRUPT and DMA, and while halted

**Constraints**
- must be generated only by this decode
- does not modify CPU architectural state

**Consumed By**
- the external DMA arbiter: `DMA_ENABLE` and the retained burst-enabled state ([DMA Arbitration](../../07-io/06-dma-arbitration.md))

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

Architectural signals participate in externally visible operations only when paired with corresponding μops.

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