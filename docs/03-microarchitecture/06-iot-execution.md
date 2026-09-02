# IOT Execution

## 1. Purpose
  
Defines execution behavior for I/O Transfer Instructions (IOT) during the EXECUTE major state.

This document specifies only:
- IR-based instruction selection
- CPU-visible interaction with I/O devices

Device-specific behavior is implemented by individual I/O controllers and is not defined here.

All shared execution semantics are defined in:

- [Execution Model](../03-microarchitecture/01-execution-model.md)  
- [ISA Encoding Model](../02-isa/00-encoding-model.md)  

---

## 2. Scope
  
Applies to instructions where:

IR[11:9] = 110  

---

## 3. External IOT Execution Model

External IOT execution uses:

- `IOT_ACTIVE` to identify an external-IOT EXECUTE cycle
- `IOA[5:0]` for controller selection
- `IOP[2:0]` for controller-defined operation selection
- `DB[11:0]` for data transport
- phase-specific controller response inputs

The selected controller may request:

- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`

The selected controller may also assert `/IO_WAIT` during eligible setup steps.

The CPU remains responsible for all CPU-local state changes. A controller response does not directly modify CPU state.

---

## 4. Data Ingestion Rule

Device-to-CPU data transfer uses `DB_READ_TO_AC`:

```text
AC <- AC OR DB_INPUT
```

No direct DB transfer to another CPU register is defined.

---

## 5. Pending Transfer State

`IOT_TRANSFER` preserves an accepted DB transfer request for execution during the immediately following TS.

At external-IOT TP2 or TP3:

```text
if IO_READ_REQ = 1:
    IOT_TRANSFER <- READ
else if IO_WRITE_REQ = 1:
    IOT_TRANSFER <- WRITE
else if a pending transfer commits at this TP:
    IOT_TRANSFER <- NONE
```

`IO_READ_REQ` and `IO_WRITE_REQ` must not both be asserted.

During the transfer TS:

- `IOT_READ_PENDING` selects `/DB_READ` and `DB_READ_TO_AC`.
- `IOT_WRITE_PENDING` selects `/DB_WRITE` and `DB_WRITE_FROM_AC`.
- `IOT_TRANSFER = NONE` selects no DB transfer.

Transfer timing is:

```text
request during TS2
-> acceptance at TP2
-> transfer during TS3
-> commit at TP3

request during TS3
-> acceptance at TP3
-> transfer during TS4
-> commit at TP4
```

At the commit TP:

- the completed transfer clears to `NONE` when no new request is accepted
- a newly accepted request replaces the completed transfer when acceptance and completion occur at the same TP

The active transfer depends on committed `IOT_TRANSFER` state, not directly on the current request inputs.

`IOT_TRANSFER` records only transfer direction. It does not contain DB data, identify the selected controller, or independently authorize DB ownership.

---

## 6. IOA and IOP Handling

IOA and IOP are derived directly from IR.

Properties:

- `IOA[5:0]` reflects `IR[8:3]`.
- `IOP[2:0]` reflects `IR[2:0]`.
- IOA and IOP are driven by control, not by a micro-operation.
- IOA and IOP do not participate in the CPU datapath.
- IOA and IOP remain stable throughout external-IOT EXECUTE.
- IOA and IOP are meaningful to external controllers only while `IOT_ACTIVE` is asserted.

Constraints:

- No micro-operation may target IOA or IOP.
- IOA selects the external controller.
- IOP identifies the selected controller's operation.
- IOP does not independently determine transfer direction or CPU behavior.

---

## 7. External IOT Phase Binding

The phase-by-phase external-IOT schedule is defined in [Major State Timing](../09-timing/03-major-state-timing.md#52-execute-external-iot)

This document defines the microarchitectural operations that occur within that timing schedule:

- A transfer request accepted at TP2 is recorded in `IOT_TRANSFER` and executes during TS3.
- A transfer request accepted at TP3 is recorded in `IOT_TRANSFER` and executes during TS4.
- `IOT_READ_PENDING` selects `/DB_READ` and `DB_READ_TO_AC` during the transfer TS.
- `IOT_WRITE_PENDING` selects `/DB_WRITE` and `DB_WRITE_FROM_AC` during the transfer TS.
- The transfer commits at the TP associated with the transfer TS.
- A completed transfer clears `IOT_TRANSFER` to `NONE` unless another request is accepted at the same TP.
- When completion and request acceptance occur at the same TP, the newly accepted transfer replaces the completed transfer.
- `IO_CLEAR_AC_REQ` and `IO_SKIP_REQ` select their corresponding CPU micro-operations according to the timing and combination constraints defined by the external-IOT schedule.

The timing document defines when requests may be asserted, accepted, transferred, and committed. This document defines how those events map to CPU state and micro-operations.

---

## 8. Response Constraints

- `IO_READ_REQ` and `IO_WRITE_REQ` are mutually exclusive.
- Read and AC clear must not commit at the same TP.
- Write and AC clear may commit at the same TP.
- For a same-TP write and clear, the external controller captures the pre-TP AC value.
- A response applies only to the TS in which it is asserted.
- A controller must reassert a response during a later TS if another action is required at a later TP.
- Only the address-matched controller may respond.

Detailed transaction behavior is defined in [External IOT Interface](../07-io/02-external-iot-interface.md)

Timing behavior is defined in [I/O Timing](../07-io/03-io-timing.md)

---

## 9. Instruction Definitions (CPU Control - Device 0)

---

### 9.1 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 010

**Mnemonic (non-normative):** IOF

TS1:
- (no μops)

TS2:
- IE_CLEAR

TS3:
- (no μops)

TS4:
- (no μops)

---

### 9.2 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 001

**Mnemonic (non-normative):** ION

TS1:
- (no μops)

TS2:
- IE_SET
- II_SET

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Turns the interrupt system on (IE_SET)
- Sets II so interrupt recognition is delayed until after the instruction following ION; FETCH clears II when no deferred instruction field change is pending, realizing the standard one-instruction ION delay

---

### 9.3 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 000

**Mnemonic (non-normative):** SKON

TS1:
- (no μops)

TS2:
- if IE: PC_INC
- IE_CLEAR

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Skips the next instruction if the interrupt system is on, then turns it off
- The skip (PC_INC) is conditional on IE; IE_CLEAR is unconditional
- Both μops target different registers (PC, IE) and may occur in the same TS

---

### 9.4 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 011

**Mnemonic (non-normative):** SRQ

  TS1:
- (no μops)

  TS2:
- if /INT_REQ = 0: PC_INC

  TS3:
- (no μops)

  TS4:
- (no μops)

Description:

- Skips the next instruction if an interrupt request is currently asserted
- /INT_REQ is an external input; the skip does not modify interrupt state

---

### 9.5 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 100
  
**Mnemonic (non-normative):** GTF 
 
  TS1:
- AC_CLEAR  

  TS2:
- GTF_FLAGS_TO_AC  

  TS3:
- (no μops)  

  TS4:
- (no μops)  

Description:
- Clears AC at TP1.
- Assembles the processor flags word into AC at TP2.
- The processor flags word is defined in [Processor Flags](../02-isa/04-iot.md#31-processor-flags-word-gtf-rtf).
- Software does not need to clear AC before executing GTF.
- GTF does not acknowledge, clear, or consume /INT_REQ.

### 9.6 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 101
  
**Mnemonic (non-normative):** RTF  

  TS1:
- (no μops)  

  TS2:
- AC_TO_L
- AC_TO_DF
- AC_TO_DIF
- IE_SET
- II_SET
- CIFP_SET  

  TS3:
- (no μops)  

  TS4:
- (no μops)  

Description:
- Restores L from AC[11].
- Restores DF from AC[2:0].
- Stages AC[5:3] in DIF for application to IF by the next JMP or JMS.
- Sets IE, II, and CIFP.
- All TS2 μops observe the same pre-TP2 AC value and commit concurrently.
- AC is not modified.

---

### 9.7 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 110

**Mnemonic (non-normative):** SGT

TS1:
- (no μops)

TS2:
- (no μops)

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Executes as a defined no-op because the EAE Greater-Than flag is not implemented.
- Does not increment PC.
- Does not modify processor, memory, controller, interrupt, or DMA state.
- Does not initiate an external bus operation.

---

### 9.8 IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 111
  
**Mnemonic (non-normative):** CAF

TS1:
- (no μops)

TS2:
- (no μops)

TS3:
- (no μops)

TS4:
- (no μops)

Control action:
- /INITIALIZE is asserted during the EXECUTE TP4 TSTEP.

Description:
- /INITIALIZE clears AC, L, and IE at TP4.
- /INITIALIZE causes each I/O controller to enter its documented initialized state at TP4.
- II, CIFP, DIF, IF, DF, and IB are not modified.
- All processor and controller effects commit atomically at TP4.
- No CAF effect occurs unless execution reaches TP4.
- CAF does not use a CAF-specific micro-operation.

---

## 10. Instruction Definitions (Memory Extension Control - Devices 20-27)

---

### 10.1 IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2] = 0 AND IR[0] = 1

**Mnemonic (non-normative):** CDF

Where:
- n = target field number (IOA[2:0] = IR[5:3])  

TS1:
- (no μops)

TS2:
- IR_DF_TO_DF

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Loads DF with the target field n from IR (immediate)


---

### 10.2 IR[11:9] = 110 AND IOA = 2n AND IR[2] = 0 AND IR[1] = 1
  
**Mnemonic (non-normative):** CIF  

Where:
- n = target field number (IOA[2:0] = IR[5:3])  

TS1:
- (no μops)  

TS2:
- IR_IF_TO_DIF
- II_SET
- CIFP_SET  

TS3:
- (no μops)  

TS4:
- (no μops)

Description:
- Loads DIF with the target field n from IR (deferred; applied to IF at the next JMP/JMS)
- Sets II and CIFP to inhibit interrupts across the CIF-to-branch window

---

### 10.3 IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 001

**Mnemonic (non-normative):** RDF

TS1:
- (no μops)

TS2:
- DF_TO_AC

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Reads DF into AC[5:3] (OR'd into AC; other AC bits unaffected)

---

### 10.4 IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 010

**Mnemonic (non-normative):** RIF

TS1:
- (no μops)

TS2:
- IF_TO_AC

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Reads IF into AC[5:3] (OR'd into AC; other AC bits unaffected)

---

### 10.5 IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 011

**Mnemonic (non-normative):** RIB

TS1:
- (no μops)

TS2:
- IB_TO_AC

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Reads the interrupt-saved fields into AC: AC[5:3] <- saved IF, AC[2:0] <- saved DF (OR'd into AC)

---

### 10.6 IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 100

**Mnemonic (non-normative):** RMF

TS1:
- (no μops)

TS2:
- `IB_TO_DF`
- `IB_TO_DIF`
- `II_SET`
- `CIFP_SET`

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Restores `DF` from the saved `DF` value in `IB`
- Stages the saved `IF` value from `IB` in `DIF`
- Sets `II` and `CIFP` to inhibit interrupt recognition until the deferred instruction-field value is applied by the next JMP or JMS

---

## 11. Notes
  
- DB direction (CPU → device or device → CPU) is device-defined
- No CPU-visible μops are required unless a device operation transfers data into CPU registers
- Timing constraints for device interaction follow the [Execution Model](../03-microarchitecture/01-execution-model.md)