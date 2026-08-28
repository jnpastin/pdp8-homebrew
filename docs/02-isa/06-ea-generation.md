# Effective Address (EA) Generation Algorithm

## 1. Scope

Applies only to Memory Reference Instructions (MRI).  

See:  
- [Encoding model](./00-encoding-model.md)
- [Addressing model](./05-addressing-model.md)

---

## 2. Notation

All final effective addresses are expressed as:

```
FXXXX
```

Where:

- F = field  
- XXXX = 12-bit address  

---

## 3. Overview

The EA as a logical construct is formed by:

1. Selecting a EA_addr address using the page bit (P)
2. Resolving direct or indirect addressing (mutually exclusive)
3. Applying field selection (IF or DF)

EA_logical = (EA_fld, EA_addr)

![A visual representation of the EA generation flowchart](../../diagrams/isa/addressing-model/export/addressing-model.png)

---

## 4. EA_addr Usage by Phase

EA_addr is a phase-dependent working value:

- During FETCH:
  EA_addr holds the current page or zero page address derived from IR and PC

- During DEFER (if indirect):
  EA_addr is updated with the resolved pointer value

- At entry to EXECUTE:
  EA_addr contains the final operand address

EA_addr must not be assumed to be final prior to EXECUTE

---

## 5. Inputs

- IR bits: I, P, offset[6:0]  
- PC (12-bit)  
- IF (Instruction Field)  
- DF (Data Field)  
- Memory M[]  

---

## 6. Step 1: EA_addr Address Formation (IF domain)

The EA_addr address is always initially formed in the IF domain, regardless of addressing mode.

If P = 0:

```
EA_addr = 0000 || offset
```

If P = 1:

```
EA_addr = PC[11:7] || offset
```

---

## 7. Step 2A: Direct Addressing Path (I = 0)

Direct addressing does not involve indirection.

```
EA_field = IF
EA_addr  = EA_addr

EA = (EA_field, EA_addr)
STOP
```

Properties:

- Uses IF for both EA_addr formation and final access  
- No interaction with DF  

---

## 8. Step 2B: Indirect Addressing Path (I = 1)

Indirect addressing resolves a pointer stored in memory.

### 8.1 Step 2B.1: Pointer Location (IF domain)

The pointer location is defined by EA_addr in the IF domain.

---

### 8.2 Step 2B.2: Auto-Index Handling

If EA_addr is in the auto-index range:

```
0010–0017 (octal)
```

Then:

```
M[(IF, EA_addr)] = M[(IF, EA_addr)] + 1
PTR_value     = M[(IF, EA_addr)]
```

Else:

```
PTR_value = M[(IF, EA_addr)]
```

---

### 8.3 Step 2B.3: Final EA Formation (DF domain)

```
EA_field = DF
EA_addr  = PTR_value

EA = (EA_field, EA_addr)
STOP
```

---

## 9. Invariants

- EA_addr is always formed using IF  
- Direct (I = 0) uses IF for final memory access  
- Indirect (I = 1):
  - Pointer location is (IF, EA_addr)  
  - Final EA is (DF, PTR_value)  
- Auto-index:
  - Applies only when I = 1  
  - Occurs before pointer use  
  - Operates in IF domain  
- Direct and indirect are mutually exclusive execution paths  

---

## 10. Notes

- Pointer location is always addressed in IF  
- Pointer value is interpreted as an address in DF  
- Indirect addressing enables cross-field access via DF  

