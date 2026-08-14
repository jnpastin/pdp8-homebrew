## IOT Execution

### Purpose
  
Defines execution behavior for I/O Transfer Instructions (IOT) during the EXECUTE major state.

This document specifies only:
- IR-based instruction selection
- CPU-visible interaction with I/O devices

Device-specific behavior is implemented by individual I/O controllers and is not defined here.

All shared execution semantics are defined in:

- [Execution Model](../03-microarchitecture/01-execution-model.md)  
- [ISA Encoding Model](../02-isa/00-encoding-model.md)  

---

### Scope
  
Applies to instructions where:

IR[11:9] = 110  

---

### Execution Model
  
IOT execution is defined as interaction between the CPU and an external device via:

- IOA (device selection)
- DB (data transfer)

The CPU:

- Selects a device via IOA
- Initiates a device-defined operation
- May participate in data transfer over DB

All instruction behavior beyond this interface is defined by the selected device.

---

### Data Ingestion Rule

Any data transfer from an I/O device to the CPU must be expressed as:

1. DB_READ_TO_AC (capture from AC)
2. A subsequent μop that consumes AC

No direct DB → arbitrary register transfer is permitted.

This ensures consistency with the MDB ingestion model and preserves
the invariant that all bus values are captured through registers.

---

### IOA Handling
  
IOA is implemented as control signals derived directly from IR.

Properties:

- IOA is populated as part of instruction decode
- IOA is driven by control, not by a μop
- IOA does not participate in the datapath
- IOA is stable during the EXECUTE phase

Constraints:

- No μop may target IOA
- IOA must reflect the device address encoded in IR

---

### Instruction Definition (General)

---

#### IR[11:9] = 110
  
**Mnemonic (non-normative):** IOT  

TS1:
- (no μops)  

TS2:
- (device interaction phase)  

TS3:
- (device interaction phase)  

TS4:
- (no μops)  

Note:  
The transfer direction (device drives DB into AC, or CPU drives AC onto DB) is not determined by IR. It is signaled at runtime by the selected device via device-response inputs, resolved when the I/O subsystem is defined. The generic IOT cycle provides the ordered interaction windows and the bus path; it does not itself select direction.

---

### Instruction Definitions (CPU Control - Device 0)

---

#### IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 010

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

#### IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 001

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
- Sets II so interrupt recognition is delayed until after the instruction following ION; FETCH clears II when no CIF field change is pending, realizing the standard one-instruction ION delay

---

#### IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 000

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

#### IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 011

**Mnemonic (non-normative):** SRQ

  TS1:
- (no μops)

  TS2:
- if INT_REQ: PC_INC

  TS3:
- (no μops)

  TS4:
- (no μops)

Description:

- Skips the next instruction if an interrupt request is currently asserted
- INT_REQ is an external input; the skip does not modify interrupt state

---

### Instruction Definitions (Memory Extension Control - Devices 20-27)

---

#### IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2] = 0 AND IR[0] = 1

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

#### IR[11:9] = 110 AND IOA = 2n AND IR[2] = 0 AND IR[1] = 1
  
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

#### IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 001

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

#### IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 010

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

#### IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 011

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

#### IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 100

**Mnemonic (non-normative):** RMF

TS1:
- (no μops)

TS2:
- IB_TO_DF
- IB_TO_DIF

TS3:
- (no μops)

TS4:
- (no μops)

Description:
- Restores the fields saved in IB: DF <- saved DF (immediate), IF <- saved IF (deferred via DIF; applied at the next JMP/JMS)

---

### Notes
  
- DB direction (CPU → device or device → CPU) is device-defined
- No CPU-visible μops are required unless a device operation transfers data into CPU registers
- Timing constraints for device interaction follow the [Execution Model](../03-microarchitecture/01-execution-model.md)