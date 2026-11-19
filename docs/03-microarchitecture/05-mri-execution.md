# MRI Execution

## 1. Purpose
  
Defines execution behavior for Memory Reference Instructions (MRI) during the EXECUTE major state.

This document specifies only:
- IR-based instruction selection
- μop sequences assigned to TS

All shared execution semantics are defined in:

- [Execution Model](./01-execution-model.md)
- [Encoding Model](../02-isa/00-encoding-model.md)

---

## 2. Scope
  
Applies to instructions where:

IR[11:9] = 000–101  

---

## 3. Instruction Definitions

---

### 3.1 IR[11:9] = 000
  
**Mnemonic (non-normative):** AND  

TS1:
- EA_ADDR_TO_MA  

TS2:
- MEM_READ_TO_MB  

TS3:
- AC_AND_MB  

TS4:
- (no μops)  

---

### 3.2 IR[11:9] = 001
  
**Mnemonic (non-normative):** TAD  

TS1:
- EA_ADDR_TO_MA  

TS2:
- MEM_READ_TO_MB  

TS3:
- ADD_AC_MB  

TS4:
- (no μops)  

---

### 3.3 IR[11:9] = 010
  
**Mnemonic (non-normative):** ISZ  

TS1:
- EA_ADDR_TO_MA  

TS2:
- MEM_READ_TO_MB  

TS3:
- MB_INC  

TS4:
- MEM_WRITE_FROM_MB

Conditional μops:

```text
ISZ_SKIP_REQUIRED = 1 -> PC_INC
```

---

### 3.4 IR[11:9] = 011
  
**Mnemonic (non-normative):** DCA  

TS1:
- EA_ADDR_TO_MA  

TS2:
- AC_TO_MB  

TS3:
- MEM_WRITE_FROM_MB  

TS4:
- AC_CLEAR  

---

### 3.5 IR[11:9] = 100
  
**Mnemonic (non-normative):** JMS  

TS1:
- EA_ADDR_TO_MA  

Conditional μops:

```text
IF_CHANGE_PENDING = 1 -> DIF_TO_IF
CIFP = 1 -> CIFP_CLEAR
CIFP = 1 -> II_CLEAR
```

TS2:
- PC_TO_MB  

TS3:
- MEM_WRITE_FROM_MB  
- PC_LOAD_EA_ADDR  

TS4:
- PC_INC  

A pending instruction-field change is applied at TP1, so the TS3 return-address write and the following FETCH both use the new instruction field, as on the PDP-8/e. The same TP1 clears `II`, so an interrupt may be recognized at this instruction's TP4 ([Interrupt Enable and Inhibit §12](../08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md#12-deferred-field-application)).

---

### 3.6 IR[11:9] = 101
  
**Mnemonic (non-normative):** JMP  

TS1:
Conditional μops:

```text
IF_CHANGE_PENDING = 1 -> DIF_TO_IF
CIFP = 1 -> CIFP_CLEAR
CIFP = 1 -> II_CLEAR
```

TS2:
- (no μops)  

TS3:
- PC_LOAD_EA_ADDR  

TS4:
- (no μops)  

A pending instruction-field change is applied at TP1, so the following FETCH uses the new instruction field. The same TP1 clears `II`, so an interrupt may be recognized at this instruction's TP4 ([Interrupt Enable and Inhibit §12](../08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md#12-deferred-field-application)).

---

## 4. Summary
  
MRI execution is defined entirely by:

- IR[11:9] selecting instruction behavior  
- μop assignment to TS  

No additional rules are defined in this document.