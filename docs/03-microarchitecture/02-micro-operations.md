## Micro-Operations (μops)

### Purpose

Defines the complete set of atomic state transformations available to the system.

Each μop specifies:
- a target register (or registers)
- a transformation of state
- required source inputs
- constraints on valid usage

μops define what state change occurs, not how that change is implemented.

---

## Usage Rules

- All μops are atomic
- μops are evaluated during TS and committed at TP
- No μop may conflict with another in the same TS
- μops must not assume ordering within a TS
- μops operate only on defined source domains

---

## Conditions (Non-μop Concept)

Conditions are not μops.

Conditions:
- are functions of register state
- produce no persistent state
- are evaluated and consumed within the same TS
- are used by control to determine which μops execute

Example:
    if (L != 0):
        PC_INC

No intermediate state or flag storage is created.

---

## Index


### Address Formation
- [IR_ADDR_TO_EA_ADDR](#ir_addr_to_ea_addr)

### Arithmetic / Logical
- [AC_AND_MB](#ac_and_mb)
- [AC_COMP](#ac_comp)
- [AC_OR_MQ](#ac_or_mq)
- [AC_OR_SR](#ac_or_sr)
- [ADD_AC_MB](#add_ac_mb)
- [L_COMP](#l_comp)
- [MB_INC](#mb_inc)

#### Bit Operations

- [AC_ROR](#ac_ror)
- [AC_ROL](#ac_rol)
- [AC_RTR](#ac_rtr)
- [AC_RTL](#ac_rtl)
- [AC_BSW](#ac_bsw)

### Control Flow
- [PC_INC](#pc_inc)
- [PC_LOAD_EA_ADDR](#pc_load_ea_addr)

### Memory Operations
- [MEM_READ_TO_MB](#mem_read_to_mb)
- [MEM_WRITE_FROM_MB](#mem_write_from_mb)

### Register Transfer
- [AC_TO_MB](#ac_to_mb)
- [AC_TO_MQ_AND_CLEAR_AC](#ac_to_mq_and_clear_ac)
- [EA_TO_MA](#ea_to_ma)
- [L_CLEAR](#l_clear)
- [MB_TO_EA](#mb_to_ea)
- [MB_TO_IR](#mb_to_ir)
- [PC_TO_MA](#pc_to_ma)
- [PC_TO_MB](#pc_to_mb)

### State Manipulation
- [AC_CLEAR](#ac_clear)
- [AC_COMPLEMENT](#ac_complement)
- [AC_INC](#ac_inc)

---

## μop Definitions (Alphabetical)

---

#### AC_AND_MB
  
**Category:** 
Arithmetic / Logical  

**Description:** 
Performs a bitwise AND between the accumulator and the memory buffer, storing the result in the accumulator.  

**Target:** AC  

**Expression:** 
AC ← AC AND MB  

**Sources:** 
AC, MB  

---

### AC_BSW
  
**Category:** Bit Operations  

**Description:**  
Swaps the high and low 6-bit halves of the accumulator.  

**Target:**  
AC  

**Expression:**  
AC ← swap_halves(AC)  

**Sources:**  
AC 

---

### AC_CLEAR

**Category:**  
State Manipulation

**Description:**  
Sets the accumulator to zero, discarding any previous value.

**Target:**  
AC

**Expression:**  
AC ← 0

**Sources:**  
none

---

### AC_COMPLEMENT

**Category:**  
State Manipulation

**Description:**  
Performs a bitwise inversion of the accumulator value.

**Target:**  
AC

**Expression:**  
AC ← NOT AC

**Sources:**  
AC

---

### AC_INC

**Category:**  
State Manipulation

**Description:**  
Increments the accumulator by one, propagating any carry into the Link register.

**Target:**  
AC, L

**Expression:**  
(AC, L) ← AC + 1

**Sources:**  
AC

---

### AC_OR_MQ
  
**Category:** 
Arithmetic / Logical  

**Description:** 
Performs a bitwise OR between the accumulator and the multiplier quotient register, storing the result in the accumulator.  

**Target:** 
AC  

**Expression:** 
AC ← AC OR MQ  

**Sources:** 
AC, MQ

---

### AC_OR_SR
  
**Category:** 
Arithmetic / Logical  

**Description:** 
Performs a bitwise OR between the accumulator and the switch register, storing the result in the accumulator.  

**Target:** 
AC  

**Expression:** 
AC ← AC OR SR  

**Sources:** 
AC, SR

---

### AC_ROR
  
**Category:** 
Bit Operations  

**Description:**  
Rotates the combined L and AC register right by one bit.  

**Target:**  
AC, L  

**Expression:**  
(L, AC) ← rotate_right(L, AC, 1)  

**Sources:**  
AC, L  

---

### AC_ROL
  
**Category:** 
Bit Operations  

**Description:**  
Rotates the combined L and AC register left by one bit.  

**Target:**  
AC, L  

**Expression:**  
(L, AC) ← rotate_left(L, AC, 1)  

**Sources:**  
AC, L  

---

### AC_RTR
  
**Category:** 
Bit Operations  

**Description:**  
Rotates the combined L and AC register right by two bits.  

**Target:**  
AC, L  

**Expression:**  
(L, AC) ← rotate_right(L, AC, 2)  

**Sources:**  
AC, L  

---

### AC_RTL
  
**Category:** 
Bit Operations  

**Description:**  
Rotates the combined L and AC register left by two bits.  

**Target:**  
AC, L  

**Expression:**  
(L, AC) ← rotate_left(L, AC, 2)  

**Sources:**  
AC, L  

---

#### AC_TO_MB
  
**Category:** 
Register Transfer  

**Description:** 
Transfers the value of the accumulator into the memory buffer for subsequent use in memory write operations.  

**Target:** 
MB  

**Expression:** 
MB ← AC  

**Sources:** 
AC  

---

### AC_TO_MQ_AND_CLEAR_AC
  
**Category:** 
Register Transfer  

**Description:** 
Transfers the value of the accumulator into the multiplier quotient register and clears the accumulator. Both results are committed simultaneously as a single atomic transformation.  

**Target:** 
MQ, AC  

**Expression:**  
MQ ← AC  
AC ← 0  

**Sources:**
AC
---

### ADD_AC_MB

**Category:**  
Arithmetic / Logical

**Description:**  
Adds the value in MB to the accumulator and stores the result in AC, with overflow propagated into the Link register.

**Target:**  
AC, L

**Expression:**  
(AC, L) ← AC + MB

**Sources:**  
AC, MB

---

### EA_TO_MA

**Category:**  
Register Transfer

**Description:**  
Transfers the effective address into the memory address register for operand access.

**Target:**  
MA

**Expression:**  
MA ← EA

**Sources:**  
EA

---

### IR_ADDR_TO_EA_ADDR

**Category:**  
Address Formation

**Description:**  
Constructs the base effective address from the instruction address field using page selection rules.

**Target:**  
EA

**Expression:**

    if P == 0:
        EA ← (0…0 || IR[6:0])
    else:
        EA ← (PC[11:7] || IR[6:0])

**Sources:**  
IR, PC

---

### L_COMP
  
**Category:**
Arithmetic / Logical

**Description:**  
Computes the complement of the link register.  

**Target:**  
L  

**Expression:**  
L ← NOT L  

**Sources:**  
L  

---


### MB_INC

**Category:**  
Arithmetic / Logical

**Description:**  
Increments the value stored in MB, producing a new value for subsequent use.

**Target:**  
MB

**Expression:**

    MB ← MB + 1

**Sources:**  
MB

---

### MB_TO_EA

**Category:**  
Register Transfer

**Description:**  
Transfers the value currently held in MB into EA as the resolved effective address.

**Target:**  
EA

**Expression:**

    EA ← MB

**Sources:**  
MB

---

### MB_TO_IR

**Category:**  
Register Transfer

**Description:**  
Loads the instruction register with the value currently held in the memory buffer.

**Target:**  
IR

**Expression:**  
IR ← MB

**Sources:**  
MB

---

### MEM_READ_TO_MB

**Category:**  
Memory Operations

**Description:**  
Reads the value at the address specified by MA and places it into the memory buffer.

**Target:**  
MB

**Expression:**  
MB ← M[MA]

**Sources:**  
MA

---

### MEM_WRITE_FROM_MB

**Category:**  
Memory Operations

**Description:**  
Writes the value stored in MB to the memory location specified by MA.

**Target:**  
M[MA]

**Expression:**  
M[MA] ← MB

**Sources:**  
MA, MB

---

### PC_INC

**Category:**  
Control Flow

**Description:**  
Increments the program counter to point to the next sequential instruction.

**Target:**  
PC

**Expression:**  
PC ← PC + 1

**Sources:**  
PC

---

### PC_LOAD_EA_ADDR

**Category:**  
Control Flow

**Description:**  
Replaces the program counter with the contents of the EA register.

**Target:**  
PC

**Expression:**  
PC ← EA

**Sources:**  
EA

---

### PC_TO_MA

**Category:**  
Register Transfer

**Description:**  
Transfers the program counter into the memory address register for instruction fetch.

**Target:**  
MA

**Expression:**  
MA ← PC

**Sources:**  
PC

---


#### PC_TO_MB
  
**Category:** 
Register Transfer  

**Description:** 
Transfers the program counter into the memory buffer, typically used to stage a return address for storage in memory.  

**Target:** 
MB  

**Expression:** 
MB ← PC  

**Sources:** 
PC

---

## Notes

- This catalog is closed; all execution must be expressed using these μops.
- New μops may be introduced only when required for ISA completeness.
- Conditions are evaluated directly from register state and must not be represented as μops.

