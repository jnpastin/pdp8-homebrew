# IOT Instruction Detail

## 1. Purpose

Defines the CPU-internal IOT instructions decoded directly by the processor.

IOT instructions (opcode 6) fall into two categories:
- External device IOTs, interpreted by an individual device controller. These are not defined here; see the device documentation in [Section 7](../07-io/README.md).
- CPU-internal IOTs, decoded by the processor itself. These are defined in this document.

This document defines encoding and observable semantics only. Micro-operation sequences are defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

---

## 2. Scope

Applies to instructions where IR[11:9] = 110 and the device address selects a CPU-internal function:
- Device 0 - processor IOTs (interrupt and flag control)
- Devices 20-27 - memory extension control (field instructions)

The IOT bit format (opcode, 6-bit device address, 3-bit operation) is defined in the [encoding model](./00-encoding-model.md).

All device-0 and memory-extension instructions listed here are PDP-8/E processor features. The memory-extension instructions additionally require the memory-extension option.


---

## 3. Device 0 - Processor IOTs

These instructions control the interrupt system. They are decoded when IR[11:9] = 110 and IR[8:3] = 000000 (device address 0). The specific operation is selected by the value of IR[2:0].

```
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬─────┬─────┬─────┐
│ 11 │ 10 │ 9  │ 8  │ 7  │ 6  │ 5  │ 4  │ 3  │  2  │  1  │  0  │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼─────┼─────┼─────┤
│ 1  │ 1  │ 0  │ 0  │ 0  │ 0  │ 0  │ 0  │ 0  │     │     │     │
├────┴────┴────┼────┴────┴────┴────┴────┴────┼─────┴─────┴─────┤
│     IOT      │        Device 0 (CPU)       │    Operation    │
└──────────────┴─────────────────────────────┴─────────────────┘
```

Unlike the field instructions and Group 1 OPR, these are distinct operations selected by the IR[2:0] value; they are not independent flags and may not be combined.

| Mnemonic | Octal | IR[2:0] | Name | Operation |
|---|---|---|---|---|
| SKON | 6000 | 000 | Skip if Interrupt On | Skip the next instruction if the interrupts are enabled, then disable interrupts |
| ION | 6001 | 001 | Interrupt On | Enable Interrupts |
| IOF | 6002 | 010 | Interrupt Off | Disable Interrupts |
| SRQ | 6003 | 011 | Skip on Interrupt Request | Skip the next instruction if an interrupt request is currently asserted |
| GTF | 6004 | 100 | Get Flags | Replace AC with the PDP-8/E processor flags word |
| RTF | 6005 | 101 | Restore Flags | Restore the implemented processor state from the PDP-8/E flags word and enable interrupts |
| CAF | 6007 | 111 | Clear All Flags | Generate the same system-wide initialization action as the front-panel CLEAR switch |

Semantics:
- ION turns interrupts on, but the effect is deferred by one instruction: the instruction immediately following ION always executes before any interrupt can be recognized. This lets a routine execute ION followed by a return (for example, JMP I) without being interrupted between the two.
- IOF turns interrupts off immediately.
- SKON tests the interrupt state and turns interrupts off in a single instruction. It skips if interrupts were on. This provides a way to save and disable interrupt state together.
- SRQ tests whether any device is currently requesting an interrupt, without affecting interrupt state. It is used by software polling routines.

### 3.1 Processor Flags Word (GTF, RTF)

GTF and RTF use the PDP-8/E processor flags-word format.

```text
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ 11 │ 10 │  9 │  8 │  7 │  6 │  5 │  4 │  3 │  2 │  1 │  0 │
├────┼────┼────┼────┼────┼────┼────┴────┴────┼────┴────┴────┤
│ L  │ 0  │ IR │ 0  │ IE │ 0  │      IF      │      DF      │
└────┴────┴────┴────┴────┴────┴──────────────┴──────────────┘
```

Where:
- L is the current Link value.
- IR is 1 when /INT_REQ is asserted and 0 when /INT_REQ is deasserted.
- IE is the current interrupt-enable value.
- IF is the current Instruction Field.
- DF is the current Data Field.
- Bit 10 is 0 because the EAE Greater-Than flag is not implemented.
- Bit 8 is 0 because the time-share interrupt-inhibit facility is not implemented.
- Bit 6 is 0 because user mode is not implemented.

The IR field reports raw interrupt-request presence. It does not report `INTERRUPT_REQUEST_VALID` and is independent of IE and II.

#### 3.1.1 GTF

GTF replaces AC with the processor flags word.

GTF execution:
- clears AC
- loads the processor flags word into AC
- does not require software to clear AC before execution
- observes /INT_REQ without acknowledging, clearing, or consuming any controller interrupt condition
- does not modify L, IE, II, IF, DF, DIF, or CIFP

#### 3.1.2 RTF

RTF restores the implemented processor state from the processor flags word.

RTF performs:
- L <- AC[11]
- DF <- AC[2:0]
- DIF <- AC[5:3]
- CIFP <- 1
- II <- 1
- IE <- 1

The restored instruction field is staged in DIF and is applied by the next JMP or JMS through the existing deferred instruction-field-change mechanism.

RTF ignores:
- AC[10]
- AC[9]
- AC[8]
- AC[7]
- AC[6]

RTF does not modify AC.

---

### 3.2 CAF

CAF generates the same system-wide initialization action as an accepted front-panel CLEAR operation.

CAF:
- clears AC
- clears L
- clears IE
- asserts the active-low /INITIALIZE signal
- causes each I/O controller to enter its documented initialized state

CAF does not modify:
- II
- CIFP
- DIF
- IF
- DF
- IB

CAF completes atomically at EXECUTE TP4. No CAF effect occurs before that boundary.

If CAF is executed while an I/O device is active, /INITIALIZE overrides the controller's normal activity and the controller enters its documented initialized state. Software is responsible for confirming that affected devices are idle and observing any device-specific safety interval before executing CAF.

#### 3.2.1 Programming Convention

Before executing CAF, software should:
- use each affected device's status instructions to confirm that the device is idle
- observe any device-specific safety interval required after the final operation
- avoid executing CAF while a device operation remains active

The processor does not enforce these checks or delays.  
CAF executes normally and asserts /INITIALIZE at EXECUTE TP4 regardless of peripheral activity.

---

## 4. Devices 20-27 - Memory Extension Control

These instructions manage the instruction field (IF) and data field (DF) for extended memory addressing. They are decoded when IR[11:9] = 110 and IR[8:6] = 010.

### 4.1 Field-Change Instructions (CDF, CIF)

The target field n is encoded in IR[5:3], making the device address 2n. The two low operation bits are independent flags: CDF (bit 0) and CIF (bit 1).

```
┌────┬────┬────┬────┬────┬────┬─────┬─────┬─────┬────┬─────┬─────┐
│ 11 │ 10 │ 9  │ 8  │ 7  │ 6  │  5  │  4  │  3  │ 2  │  1  │  0  │
├────┼────┼────┼────┼────┼────┼─────┼─────┼─────┼────┼─────┼─────┤
│ 1  │ 1  │ 0  │ 0  │ 1  │ 0  │     │     │     │ 0  │ CIF │ CDF │
├────┴────┴────┼────┴────┴────┼─────┴─────┴─────┼────┼─────┼─────┤
│     IOT      │     MEM      │      Field      │    │     │     │
└──────────────┴──────────────┴─────────────────┴────┴─────┴─────┘
```

| Flag | Bit | Name | Operation |
|---|---|---|---|
| CDF | 0 | Change Data Field | DF <- Field (immediate) |
| CIF | 1 | Change Instruction Field | IF <- Field, applied at the next JMP or JMS (deferred) |

Like Group 1 OPR, CDF and CIF are independent flags that may be combined (ORed) into a single instruction. The Field value (IR[5:3]) is shared by both flags.

- CDF alone (62n1): loads DF immediately.
- CIF alone (62n2): stages the target field and applies it to IF at the next JMP or JMS. The deferral preserves correct interrupt behavior across the field change.
- CDF CIF (62n3): both effects apply - DF immediately, IF deferred - using the same Field value.

Where n = IR[5:3] = target field (0-7).

### 4.2 Register Read / Restore Instructions

These are selected by IR[2:0] = 100, with the specific instruction determined by IR[5:3].

| Mnemonic | Octal | Name | Operation |
|---|---|---|---|
| RDF | 6214 | Read Data Field | AC[5:3] <- DF (OR'd into AC; other AC bits unaffected) |
| RIF | 6224 | Read Instruction Field | AC[5:3] <- IF (OR'd into AC; other AC bits unaffected) |
| RIB | 6234 | Read Interrupt Buffer | AC[5:3] <- saved IF, AC[2:0] <- saved DF (OR'd into AC; other AC bits unaffected) |
| RMF | 6244 | Restore Memory Field | DF <- saved DF immediately; saved IF is staged for application at the next JMP or JMS; interrupt recognition is inhibited until the staged IF is applied |

Semantics:
- RDF and RIF place the current field into AC[5:3] by OR, so AC is not cleared first. A clean read is obtained by clearing AC (for example, CLA) in a preceding instruction.
- RIB reads the interrupt-saved fields from the interrupt buffer into AC. It is used within an interrupt service routine to capture the interrupted program's fields.
- RMF restores DF from the interrupt buffer immediately and stages the saved IF for application at the next JMP or JMS. Interrupt recognition remains inhibited until the staged instruction field is applied, consistent with CIF.

---

## 5. External Device Address and Operation Transport

External-device IOT instructions present two distinct controller-facing fields:

- `IOA[5:0]` carries the six-bit device address from `IR[8:3]`.
- `IOP[2:0]` carries the three-bit device operation field from `IR[2:0]`.

IOP semantics are defined by the selected controller.

A controller compatible with a DEC device must reproduce the device address, operation encoding, combined-operation behavior, and programmer-visible effects required by the emulated controller.

A custom controller may define its own IOP semantics.

Device address configuration does not alter instruction encoding. Software issuing direct IOT instructions must use the controller's configured address.

Detailed external-IOT behavior is defined in the [IOT interface](../07-io/02-external-iot-interface.md)

---

## 6. Unsupported Instructions

### 6.1 SGT

SGT is recognized as PDP-8/E device-0 instruction 6006.

The EAE Greater-Than flag is not implemented. Therefore, SGT executes as a defined no-op.

SGT:
- does not skip
- does not modify processor state
- does not modify memory
- does not modify controller state
- does not affect interrupt or DMA state
- does not drive or initiate an external bus operation

Software that requires EAE Greater-Than behavior is not supported.
