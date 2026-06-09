## MRI Execution

### Purpose
  
Defines execution behavior for Memory Reference Instructions (MRI) during the EXECUTE major state.

This document specifies only:
- IR-based instruction selection
- μop sequences assigned to TS

All shared execution semantics are defined in:

- ../03-microarchitecture/01-execution-model.md  
- ../02-isa/00-encoding-model.md  

---

## Scope
  
Applies to instructions where:

IR[11:9] = 000–101  

---

## Instruction Definitions

---

### IR[11:9] = 000
  
**Mnemonic (non-normative):** AND  

TS1:
- EA_TO_MA  

TS2:
- MEM_READ_TO_MB  

TS3:
- AC_AND_MB  

TS4:
- (no μops)  

---

### IR[11:9] = 001
  
**Mnemonic (non-normative):** TAD  

TS1:
- EA_TO_MA  

TS2:
- MEM_READ_TO_MB  

TS3:
- ADD_AC_MB  

TS4:
- (no μops)  

---

### IR[11:9] = 010
  
**Mnemonic (non-normative):** ISZ  

TS1:
- EA_TO_MA  

TS2:
- MEM_READ_TO_MB  

TS3:
- MB_INC  

TS4:
- MEM_WRITE_FROM_MB  
- if (MB == 0): PC_INC  

---

### IR[11:9] = 011
  
**Mnemonic (non-normative):** DCA  

TS1:
- EA_TO_MA  

TS2:
- AC_TO_MB  

TS3:
- MEM_WRITE_FROM_MB  

TS4:
- AC_CLEAR  

---

### IR[11:9] = 100
  
**Mnemonic (non-normative):** JMS  

TS1:
- EA_TO_MA  

TS2:
- PC_TO_MB  

TS3:
- MEM_WRITE_FROM_MB  
- PC_LOAD_EA_ADDR  

TS4:
- PC_INC  

---

### IR[11:9] = 101
  
**Mnemonic (non-normative):** JMP  

TS1:
- (no μops)  

TS2:
- (no μops)  

TS3:
- PC_LOAD_EA_ADDR  

TS4:
- (no μops)  

---

## Summary
  
MRI execution is defined entirely by:

- IR[11:9] selecting instruction behavior  
- μop assignment to TS  

No additional rules are defined in this document.