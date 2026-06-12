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

---

### Instruction Definitions (CPU Control - Device 0)

---

### IR[11:9] = 110 AND IOA = 000 AND IR[2:0] = 000

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

### IR[11:9] = 110 AND IOA = 000 AND IR[2:0] = 001

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

---


### Notes
  
- DB direction (CPU → device or device → CPU) is device-defined
- No CPU-visible μops are required unless a device operation transfers data into CPU registers
- Timing constraints for device interaction follow the [Execution Model](../03-microarchitecture/01-execution-model.md)