# IR-Derived Flags

## 1. Purpose

Defines all control input signals derived from the Instruction Register (IR).

These signals:

- provide a complete, explicit decode surface
- are purely combinational functions of IR
- expose instruction semantics at bit-level resolution

They are used by:

- control evaluation
- condition logic
- μoperation selection

They do not:

- perform control flow
- execute behavior
- depend on FLAGS or EXT

Related:
- [Control Model](../01-control-model.md)
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)

---

## 2. Signal Classes

### 2.1 IR Class Flags

Divide the instruction space based on opcode field `IR[11:9]`.

Encodings:

- 000–101 → MRI (Memory Reference Instructions)
- 110     → IOT (I/O Transfer)
- 111     → OPR (Operate)

Properties:

- exactly one flag must be asserted
- mutually exclusive and exhaustive

---

### 2.2 Addressing Mode Flags

Define addressing interpretation for MRI instructions.

Encodings:

- IR[8] → direct / indirect  
- IR[7] → current page / zero page  

Possible addressing modes:

- direct + current page  
- direct + zero page  
- indirect + current page  
- indirect + zero page  

Valid only when `IR_IS_MRI = 1`.

---

### 2.3 OPR Class Flags

Partition OPR instructions into groups:

- Group 1 → IR[8] = 0  
- Group 2 → IR[8] = 1 AND IR[0] = 0  
- Group 3 → IR[8] = 1 AND IR[0] = 1  

Properties:

- mutually exclusive
- define interpretation of remaining bits

---

### 2.4 OPR Bit Flags

Represent individual operations encoded in IR bits.

Group 1:

- CLA, CLL, CMA, CML, IAC, rotate

Group 2:

- CLA, SMA, SZA, SNL, OSR, HLT
- skip mode

---

### 2.5 Field Extraction Signals

Expose raw IR fields:

- IR_ADDR → IR[6:0]
- IR_IOA → IR[8:3]

---

## 3. Table of Contents

### IR Class Flags
- [IR_IS_IOT](#ir_is_iot)
- [IR_IS_MRI](#ir_is_mri)
- [IR_IS_OPR](#ir_is_opr)

### ISZ Detect
- [IR_IS_ISZ](#ir_is_isz)

### Addressing Mode
- [IR_INDIRECT](#ir_indirect)
- [IR_ZERO_PAGE](#ir_zero_page)

### OPR Classes
- [IR_OPR_GROUP1](#ir_opr_group1)
- [IR_OPR_GROUP2](#ir_opr_group2)
- [IR_OPR_GROUP3](#ir_opr_group3)


### OPR Bits
- [IR_OPR_BSW](#ir_opr_bsw)
- [IR_OPR_CLA](#ir_opr_cla)
- [IR_OPR_CLL](#ir_opr_cll)
- [IR_OPR_CMA](#ir_opr_cma)
- [IR_OPR_CML](#ir_opr_cml)
- [IR_OPR_HLT](#ir_opr_hlt)
- [IR_OPR_IAC](#ir_opr_iac)
- [IR_OPR_OSR](#ir_opr_osr)
- [IR_OPR_RAL](#ir_opr_ral)
- [IR_OPR_RAR](#ir_opr_rar)
- [IR_OPR_SKIP_MODE](#ir_opr_skip_mode)
- [IR_OPR_SMA](#ir_opr_sma)
- [IR_OPR_SNL](#ir_opr_snl)
- [IR_OPR_SZA](#ir_opr_sza)

### Fields
- [IR_ADDR](#ir_addr)
- [IR_IOA](#ir_ioa)

---

## 4. IF Flag Definitions

---

### IR_ADDR

**Mnemonic:** IR_ADDR  
**Name:** Memory Address Field  
**Type:** Field Extraction  
**Bit Width:** 7  

**Purpose:**  
Extracts the address field used by memory reference instructions.

**Derivation:**
```text
IR_ADDR = IR[6:0]
```

**Value Encoding:**
- 0000000–1111111 → address field

**Consumed By:**
- [IR_ADDR_TO_EA_ADDR](../../03-microarchitecture/02-micro-operations.md#ir_addr_to_ea_addr)


---

### IR_INDIRECT

**Mnemonic:** IR_INDIRECT  
**Name:** Indirect Addressing Flag  
**Type:** Addressing Mode  
**Bit Width:** 1  

**Purpose:**  
Indicates whether MRI uses indirect addressing.

**Derivation:**
```text
IR_INDIRECT = IR_IS_MRI AND IR[8]
```

**Value Encoding:**
- 0 → direct addressing  
- 1 → indirect addressing  

**Consumed By:**
- [MB_TO_EA](../../03-microarchitecture/02-micro-operations.md#mb_to_ea)

---

### IR_IOA

**Mnemonic:** IR_IOA  
**Name:** I/O Address Field  
**Type:** Field Extraction  
**Bit Width:** 6  

**Purpose:**  
Specifies the I/O device address for IOT instructions.

**Derivation:**
```text
IR_IOA = IR[8:3]
```

**Value Encoding:**

- 000000–111111 → device address  

**Consumed By:**


Consumed by:
- [Architectural Control Signals](../20-control-output-definitions/02-architectural-control-signals.md)

---

### IR_IS_IOT

**Mnemonic:** IR_IS_IOT  
**Name:** IOT Instruction Flag  
**Type:** IR Class  
**Bit Width:** 1  

**Purpose:**  
Indicates that the current instruction is an I/O transfer instruction.

**Derivation:**
```text
IR_IS_IOT = (IR[11:9] == 110)
```

**Value Encoding:**

- 0 → not IOT  
- 1 → IOT  

**Consumed By:**

---

### IR_IS_ISZ

**Mnemonic:** IR_IS_ISZ
**Name:**: ISZ Instruction Flag
**Type:** ISZ Detect
**Bit Width:** 1

**Purpose:**
Indicates that the current instruction is ISZ

**Derivation:**
```text
IR_IS_ISZ = (IR[11:9] == 010)
```

**Value Encoding:**

- 0 → not ISZ
- 1 → ISZ

**Consumed By:**

---

### IR_IS_MRI

**Mnemonic:** IR_IS_MRI  
**Name:** Memory Reference Instruction Flag  
**Type:** IR Class  
**Bit Width:** 1  

**Purpose:**  
Indicates that the instruction is a memory reference instruction.

**Derivation:**
```text
IR_IS_MRI =
    (IR[11:9] == 000) OR  // AND
    (IR[11:9] == 001) OR  // TAD
    (IR[11:9] == 010) OR  // ISZ
    (IR[11:9] == 011) OR  // DCA
    (IR[11:9] == 100) OR  // JMS
    (IR[11:9] == 101)     // JMP
```

**Value Encoding:**

- 0 → not MRI  
- 1 → MRI  

**Consumed By:**

- [AC_AND_MB](../../03-microarchitecture/02-micro-operations.md#ac_and_mb)
- [ADD_AC_MB](../../03-microarchitecture/02-micro-operations.md#add_ac_mb)
- [AC_TO_MB](../../03-microarchitecture/02-micro-operations.md#ac_to_mb)
- [MEM_READ_TO_MB](../../03-microarchitecture/02-micro-operations.md#mem_read_to_mb)
- [MEM_WRITE_FROM_MB](../../03-microarchitecture/02-micro-operations.md#mem_write_from_mb)
- [MB_INC](../../03-microarchitecture/02-micro-operations.md#mb_inc)
- [IR_ADDR_TO_EA_ADDR](../../03-microarchitecture/02-micro-operations.md#ir_addr_to_ea_addr)
- [MB_TO_EA](../../03-microarchitecture/02-micro-operations.md#mb_to_ea)
- [EA_TO_MA](../../03-microarchitecture/02-micro-operations.md#ea_to_ma)
- [PC_LOAD_EA_ADDR](../../03-microarchitecture/02-micro-operations.md#pc_load_ea_addr)


---

### IR_IS_OPR

**Mnemonic:** IR_IS_OPR  
**Name:** Operate Instruction Flag  
**Type:** IR Class  
**Bit Width:** 1  

**Purpose:**  
Indicates that the current instruction is an OPR instruction.

**Derivation:**
```text
IR_IS_OPR = (IR[11:9] == 111)
```

**Value Encoding:**

- 0 → not OPR  
- 1 → OPR  

**Consumed By:**

- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear)
- [AC_COMPLEMENT](../../03-microarchitecture/02-micro-operations.md#ac_complement)
- [AC_INC](../../03-microarchitecture/02-micro-operations.md#ac_inc)
- [L_CLEAR](../../03-microarchitecture/02-micro-operations.md#l_clear)
- [L_COMP](../../03-microarchitecture/02-micro-operations.md#l_comp)
- [AC_RAL](../../03-microarchitecture/02-micro-operations.md#ac_ral)
- [AC_RAR](../../03-microarchitecture/02-micro-operations.md#ac_rar)
- [AC_RTL](../../03-microarchitecture/02-micro-operations.md#ac_rtl)
- [AC_RTR](../../03-microarchitecture/02-micro-operations.md#ac_rtr)
- [AC_BSW](../../03-microarchitecture/02-micro-operations.md#ac_bsw)
- [AC_OR_MQ](../../03-microarchitecture/02-micro-operations.md#ac_or_mq)
- [AC_OR_SR](../../03-microarchitecture/02-micro-operations.md#ac_or_sr)
- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### IR_OPR_BSW

**Mnemonic:** IR_OPR_BSW  
**Name:** Byte Swap / Rotate Modifier  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Modifier bit used in Group 1 OPR operations.

This bit participates in:

- rotation behavior (single vs double rotation)
- byte swap operation

Interpretation depends on combination with other OPR bits.

**Derivation:**
```text
IR_OPR_BSW = IR_OPR_GROUP1 AND IR[1]
```

**Value Encoding:**

- 0 → modifier inactive  
- 1 → modifier active  

**Consumed By:**
- [AC_BSW](../../03-microarchitecture/02-micro-operations.md#ac_bsw)
- [AC_RTL](../../03-microarchitecture/02-micro-operations.md#ac_rtl)
- [AC_RTR](../../03-microarchitecture/02-micro-operations.md#ac_rtr)


---

### IR_OPR_CLA

**Mnemonic:** IR_OPR_CLA  
**Name:** Clear Accumulator  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Clears the accumulator (AC).

**Derivation:**
```text
IR_OPR_CLA = IR_IS_OPR AND IR[7]
```

**Value Encoding:**

- 0 → inactive  
- 1 → clear AC  

**Consumed By:**
- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear)

---

### IR_OPR_CLL

**Mnemonic:** IR_OPR_CLL  
**Name:** Clear Link  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Clears the Link (L).

**Derivation:**
```text
IR_OPR_CLL = IR_OPR_GROUP1 AND IR[6]
```

**Value Encoding:**

- 0 → inactive  
- 1 → clear Link  

**Consumed By:**
- [L_CLEAR](../../03-microarchitecture/02-micro-operations.md#l_clear)

---

### IR_OPR_CMA

**Mnemonic:** IR_OPR_CMA  
**Name:** Complement Accumulator  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Performs bitwise complement of the accumulator.

**Derivation:**
```text
IR_OPR_CMA = IR_OPR_GROUP1 AND IR[5]
```

**Value Encoding:**

- 0 → inactive  
- 1 → complement AC  

**Consumed By:**
- [AC_COMPLEMENT](../../03-microarchitecture/02-micro-operations.md#ac_complement)

---

### IR_OPR_CML

**Mnemonic:** IR_OPR_CML  
**Name:** Complement Link  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Performs bitwise complement of the Link register.

**Derivation:**
```text
IR_OPR_CML = IR_OPR_GROUP1 AND IR[4]
```

**Value Encoding:**

- 0 → inactive  
- 1 → complement Link  

**Consumed By:**
- [L_COMP](../../03-microarchitecture/02-micro-operations.md#l_comp)

---

### IR_OPR_GROUP1

**Mnemonic:** IR_OPR_GROUP1  
**Name:** OPR Group 1 Selection  
**Type:** OPR Class  
**Bit Width:** 1  

**Purpose:**  
Selects Group 1 OPR instruction format.

**Derivation:**
```text
IR_OPR_GROUP1 = IR_IS_OPR AND (IR[8] == 0)
```

**Value Encoding:**

- 0 → not Group 1  
- 1 → Group 1  

**Consumed By:**

- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear)
- [AC_COMPLEMENT](../../03-microarchitecture/02-micro-operations.md#ac_complement)
- [AC_INC](../../03-microarchitecture/02-micro-operations.md#ac_inc)
- [L_CLEAR](../../03-microarchitecture/02-micro-operations.md#l_clear)
- [L_COMP](../../03-microarchitecture/02-micro-operations.md#l_comp)
- [AC_RAL](../../03-microarchitecture/02-micro-operations.md#ac_ral)
- [AC_RAR](../../03-microarchitecture/02-micro-operations.md#ac_rar)
- [AC_RTL](../../03-microarchitecture/02-micro-operations.md#ac_rtl)
- [AC_RTR](../../03-microarchitecture/02-micro-operations.md#ac_rtr)
- [AC_BSW](../../03-microarchitecture/02-micro-operations.md#ac_bsw)


---

### IR_OPR_GROUP2

**Mnemonic:** IR_OPR_GROUP2  
**Name:** OPR Group 2 Selection  
**Type:** OPR Class  
**Bit Width:** 1  

**Purpose:**  
Selects Group 2 OPR instruction format.

**Derivation:**
```text
IR_OPR_GROUP2 = IR_IS_OPR AND IR[8] AND (IR[0] == 0)
```

**Value Encoding:**

- 0 → not Group 2  
- 1 → Group 2  

**Consumed By:**

- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear)
- [AC_OR_SR](../../03-microarchitecture/02-micro-operations.md#ac_or_sr)
- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc


---

### IR_OPR_GROUP3

**Mnemonic:** IR_OPR_GROUP3  
**Name:** OPR Group 3 Selection  
**Type:** OPR Class  
**Bit Width:** 1  

**Purpose:**  
Selects Group 3 OPR instruction format.

**Derivation:**
```text
IR_OPR_GROUP3 = IR_IS_OPR AND IR[8] AND IR[0]
```

**Value Encoding:**

- 0 → not Group 3  
- 1 → Group 3  

**Consumed By:**

- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear)
- [AC_OR_MQ](../../03-microarchitecture/02-micro-operations.md#ac_or_mq)
- [AC_TO_MQ_AND_CLEAR_AC](../../03-microarchitecture/02-micro-operations.md#ac_to_mq_and_clear_ac)


---

### IR_OPR_HLT

**Mnemonic:** IR_OPR_HLT  
**Name:** Halt  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Halts CPU execution.

**Derivation:**
```text
IR_OPR_HLT = IR_OPR_GROUP2 AND IR[1]
```

**Value Encoding:**

- 0 → inactive  
- 1 → halt  

**Consumed By:**

---

### IR_OPR_IAC

**Mnemonic:** IR_OPR_IAC  
**Name:** Increment Accumulator  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Increments the accumulator (AC).

**Derivation:**
```text
IR_OPR_IAC = IR_OPR_GROUP1 AND IR[3]
```

**Value Encoding:**

- 0 → inactive  
- 1 → increment AC  

**Consumed By:**

- [AC_INC](../../03-microarchitecture/02-micro-operations.md#ac_inc)

---

### IR_OPR_OSR

**Mnemonic:** IR_OPR_OSR  
**Name:** OR Switch Register  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Performs OR operation between switch register and accumulator.

**Derivation:**
```text
IR_OPR_OSR = IR_OPR_GROUP2 AND IR[2]
```

**Value Encoding:**

- 0 → inactive  
- 1 → OR switch register into AC  

**Consumed By:**

- [AC_OR_SR](../../03-microarchitecture/02-micro-operations.md#ac_or_sr)

---

### IR_OPR_RAL

**Mnemonic:** IR_OPR_RAL  
**Name:** Rotate Accumulator Left Enable  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Enables rotate-left behavior of the accumulator.

**Derivation:**
```text
IR_OPR_RAL = IR_OPR_GROUP1 AND IR[2]
```

**Value Encoding:**

- 0 → inactive  
- 1 → rotate-left component enabled  

**Consumed By:**


- [AC_RAL](../../03-microarchitecture/02-micro-operations.md#ac_ral)
- [AC_RTL](../../03-microarchitecture/02-micro-operations.md#ac_rtl)

---

### IR_OPR_RAR

**Mnemonic:** IR_OPR_RAR  
**Name:** Rotate Accumulator Right Enable  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Enables rotate-right behavior of the accumulator.

**Derivation:**
```text
IR_OPR_RAR = IR_OPR_GROUP1 AND IR[0]
```

**Value Encoding:**

- 0 → inactive  
- 1 → rotate-right component enabled  

**Consumed By:**

- [AC_RAR](../../03-microarchitecture/02-micro-operations.md#ac_rar)
- [AC_RTR](../../03-microarchitecture/02-micro-operations.md#ac_rtr)

---

### IR_OPR_SKIP_MODE

**Mnemonic:** IR_OPR_SKIP_MODE  
**Name:** Skip Mode Select  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Defines how Group 2 skip condition bits are combined.

**Derivation:**
```text
IR_OPR_SKIP_MODE = IR_OPR_GROUP2 AND IR[3]
```

**Value Encoding:**

- 0 → OR mode (any enabled condition true causes skip)  
- 1 → AND mode (all enabled conditions must be true)  

**Consumed By:**

- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### IR_OPR_SMA

**Mnemonic:** IR_OPR_SMA  
**Name:** Skip on AC Negative  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Enables skip condition when accumulator is negative (AC < 0).

**Derivation:**
```text
IR_OPR_SMA = IR_OPR_GROUP2 AND IR[6]
```

**Value Encoding:**

- 0 → condition disabled  
- 1 → condition enabled  

**Consumed By:**

- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### IR_OPR_SNL

**Mnemonic:** IR_OPR_SNL  
**Name:** Skip on Link Non-Zero  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Enables skip condition when Link register is non-zero.

**Derivation:**
```text
IR_OPR_SNL = IR_OPR_GROUP2 AND IR[4]
```

**Value Encoding:**

- 0 → condition disabled  
- 1 → condition enabled  

**Consumed By:**

- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### IR_OPR_SZA

**Mnemonic:** IR_OPR_SZA  
**Name:** Skip on AC Zero  
**Type:** OPR Bit Flag  
**Bit Width:** 1  

**Purpose:**  
Enables skip condition when accumulator equals zero.

**Derivation:**
```text
IR_OPR_SZA = IR_OPR_GROUP2 AND IR[5]
```

**Value Encoding:**

- 0 → condition disabled  
- 1 → condition enabled  

**Consumed By:**

- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### IR_ZERO_PAGE

**Mnemonic:** IR_ZERO_PAGE  
**Name:** Zero Page Select  
**Type:** Addressing Mode  
**Bit Width:** 1  

**Purpose:**  
Selects zero page vs current page addressing for MRI instructions.

**Derivation:**
```text
IR_ZERO_PAGE = IR_IS_MRI AND IR[7]
```

**Value Encoding:**

- 0 → current page addressing  
- 1 → zero page addressing  

**Consumed By:**
- [IR_ADDR_TO_EA_ADDR](../../03-microarchitecture/02-micro-operations.md#ir_addr_to_ea_addr)
