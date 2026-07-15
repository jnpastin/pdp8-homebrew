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

- All data ingress from external buses must occur through MB

Specifically:
- MDB → MB via MEM_READ_TO_MB
- DB  → MB via DB_READ_TO_MB

No μop may directly ingest DB_input into any register other than MB.

MB Lifetime Rule:
A value placed in MB must be consumed by all dependent μops
in the immediately following TS. No μop may rely on MB contents
beyond that TS.  If MB is not consumed in the following TS, its contents are considered undefined for subsequent use.

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

#### Bit Operations

- [AC_RAR](#ac_rar)
- [AC_RAL](#ac_ral)
- [AC_RTR](#ac_rtr)
- [AC_RTL](#ac_rtl)
- [AC_BSW](#ac_bsw)

### Control Flow
- [PC_INC](#pc_inc)
- [PC_LOAD_EA_ADDR](#pc_load_ea_addr)

### Memory Operations
- [MEM_READ_TO_MB](#mem_read_to_mb)
- [MEM_WRITE_FROM_MB](#mem_write_from_mb)
- [MEM_WRITE_FROM_SR](#mem_write_from_sr)

### I/O / External
- [DB_READ_TO_MB](#db_read_to_mb)
- [DB_WRITE_FROM_MB](#db_write_from_mb)

### Register Transfer
- [AC_TO_MB](#ac_to_mb)
- [AC_TO_MQ_AND_CLEAR_AC](#ac_to_mq_and_clear_ac)
- [DF_TO_AC](#df_to_ac)
- [EA_TO_MA](#ea_to_ma)
- [FP_DF_TO_DF](#fp_df_to_df)
- [FP_IF_TO_IF](#fp_if_to_if)
- [FP_SR_TO_EA](#fp_sr_to_ea)
- [FP_SR_TO_MA](#fp_sr_to_ma)
- [FP_SR_TO_MB](#fp_sr_to_mb)
- [IB_TO_DF](#ib_to_df)
- [IB_TO_IF](#ib_to_if)
- [IF_DF_TO_IB](#if_df_to_ib)
- [IF_TO_AC](#if_to_ac)
- [IR_DF_TO_DF](#ir_df_to_df)
- [IR_IF_TO_IF](#ir_if_to_if)
- [MB_TO_EA](#mb_to_ea)
- [MB_TO_IR](#mb_to_ir)
- [PC_TO_MA](#pc_to_ma)
- [PC_TO_MB](#pc_to_mb)

### State Manipulation
- [AC_CLEAR](#ac_clear)
- [AC_COMPLEMENT](#ac_complement)
- [AC_INC](#ac_inc)
- [DF_CLEAR](#df_clear)
- [EA_INC](#ea_inc)
- [IE_CLEAR](#ie_clear)
- [IF_CLEAR](#if_clear)
- [II_CLEAR](#ii_clear)
- [II_SET](#ii_set)
- [L_CLEAR](#l_clear)
- [L_COMP](#l_comp)
- [MA_CLEAR](#ma_clear)
- [MA_INC](#ma_inc)
- [MB_INC](#mb_inc)
- [MQ_CLEAR](#mq_clear)
- [PC_SET_1](#pc_set_1)


---

## μop Definitions (Alphabetical)

---

### AC_AND_MB
  
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

### AC_RAR
  
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

### AC_RAL
  
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

### AC_TO_MB
  
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

### DB_READ_TO_MB

**Category:** 
I/O / External  

**Description:**  
Reads the value present on the System Data Bus (DB) and loads it into the Memory Buffer (MB).  
This is the only defined mechanism for CPU ingestion of data from the DB domain.  

**Target:**  
MB  

**Expression:**  
MB ← DB_input  

**Sources:**  
DB_input  

**Preconditions:**  
- A device is currently driving DB  
- DB contains valid data for the duration of the TS  

**Constraints:**  
- Must not be used concurrently with MDB-based reads (MEM_READ_TO_MB)  
- MB must not be written by any other μop in the same TS  
- DB_input validity is defined externally and must not be assumed by control  

---

### DB_WRITE_FROM_MB

**Category:** I/O / External  
**Description:** Writes the value stored in MB to the System Data Bus (DB).

**Target:** DB  

**Expression:**  
DB_output ← MB  

**Sources:**  
MB  

**Preconditions:**  
- The CPU has control of the DB bus  
- No other device is actively driving DB  
- DB is in High-Z state prior to the write  

**Constraints:**  
- Must not be used concurrently with DB_READ_TO_MB  
- Must not be used concurrently with MDB-based operations  
- MB must remain stable for the duration of the TS  
- Only one device may drive DB at any time  

---

### DF_CLEAR

**Category:**  
State Manipulation

**Description:**  
Clears the data field register.

**Target:**  
DF

**Expression:**  
DF ← 0

**Sources:**  
(none)

---

### DF_TO_AC

**Category:**  
Register Transfer

**Description:**  
Transfers the current DF register value to AC[5:3]

**Target:**  
AC

**Expression:**  
AC[5:3] ← DF
AC remaining bits unaffected

**Sources:**  
DF

---

### EA_INC
  
**Category:**  
State Manipulation

**Description:**  
Increments the effective address register by one.

**Target:**  
EA

**Expression:**  
EA ← EA + 1

**Sources:**  
EA

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

### FP_DF_TO_DF
  
**Category:**  
Register Transfer

**Description:**  
Loads the Data Field register from the Front Panel DF switch setting.

**Target:**  
DF

**Expression:**  
DF ← FP_DF

**Sources:**  
FP_DF

---

### FP_IF_TO_IF
  
**Category:**  
Register Transfer

**Description:**  
Loads the Instruction Field register from the Front Panel IF switch setting.

**Target:**  
IF

**Expression:**  
IF ← FP_IF

**Sources:**  
FP_IF

---

### FP_SR_TO_EA
  
**Category:**  
Register Transfer

**Description:**  
Loads the Effective Address register from the Front Panel Switch Register.

**Target:**  
EA

**Expression:**  
EA ← SR

**Sources:**  
SR

---

### FP_SR_TO_MA
  
**Category:**  
Register Transfer

**Description:**  
Loads the Memory Address register from the Front Panel Switch Register.

**Target:**  
MA

**Expression:**  
MA ← SR

**Sources:**  
SR

---

### FP_SR_TO_MB
  
**Category:**  
Register Transfer

**Description:**  
Loads the Memory Buffer register from the Front Panel Switch Register.

**Target:**  
MB

**Expression:**  
MB ← SR

**Sources:**  
SR

---

### IB_TO_DF

**Category:**  
Register Transfer

**Description:**  
Transfers the DF value from IB (IB[5:3]) to the DF register

**Target:**  
DF

**Expression:**  
DF ← IB[5:3]

**Sources:**  
IB

---

### IB_TO_IF

**Category:**  
Register Transfer

**Description:**  
Transfers the IF value from IB (IB[2:0]) to the IF register

**Target:**  
IF

**Expression:**  
IF ← IB[2:0]

**Sources:**  
IB

---

### IE_CLEAR

**Category:**  
State Manipulation

**Description:**  
Clears the interrupt enable register.

**Target:**  
IE

**Expression:**  
IE ← 0

**Sources:**  
(none)

---

### IF_CLEAR

**Category:**  
State Manipulation

**Description:**  
Clears the instruction field register.

**Target:**  
IF

**Expression:**  
IF ← 0

**Sources:**  
(none)

---

### IF_DF_TO_IB

**Category:**  
Register Transfer

**Description:**  
Loads the contents of IF and DF into IB

**Target:**  
IB


Expression:
IB ← concat(IF, DF)

Sources:
IF, DF

Constraints:
- Exactly one IB_INPUT source must be active
- concat(IF, DF) is a combinational datapath value
- IB_VAL is provided by control

---

### IF_TO_AC

**Category:**  
Register Transfer

**Description:**  
Transfers the current IF register value to AC[5:3]

**Target:**  
AC

**Expression:**  
AC[5:3] ← IF
AC remaining bits unaffected

**Sources:**  
IF

---

### II_CLEAR

**Category:**  
State Manipulation

**Description:**  
Clears the interrupt inhibit register, allowing interrupt recognition.

**Target:**  
II

**Expression:**  
II ← 0

**Sources:**  
(none)

---

### II_SET

**Category:**  
State Manipulation

**Description:**  
Sets the interrupt inhibit register, preventing interrupt recognition until it is cleared.

**Target:**  
II

**Expression:**  
II ← 1

**Sources:**  
(none)

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

### IR_DF_TO_DF

**Category:**  
Register Transfer

**Description:**  
Transfers the current field value from the IR to DF

**Target:**  
DF

**Expression:**  
DF ← IR[5:3]

**Sources:**  
IR

---

### IR_IF_TO_IF

**Category:**  
Register Transfer

**Description:**  
Transfers the current field value from the IR to IF

**Target:**  
IF

**Expression:**  
IF ← IR[5:3]

**Sources:**  
IR

---

### L_CLEAR

**Category:**  
State Manipulation

**Description:**  
Sets the Link to zero, discarding any previous value.

**Target:**  
L

**Expression:**  
L ← 0

**Sources:**  
none

---

### L_COMP
  
**Category:**
State Manipulation

**Description:**  
Computes the complement of the link register.  

**Target:**  
L  

**Expression:**  
L ← NOT L  

**Sources:**  
L  

---

### MA_CLEAR

**Category:**  
State Manipulation

**Description:**  
Clears the memory address register.

**Target:**  
MA

**Expression:**  
MA ← 0

**Sources:**  
(none)

---

### MA_INC
  
**Category:**  
State Manipulation

**Description:**  
Increments the Memory Address register by one.

**Target:**  
MA

**Expression:**  
MA ← MA + 1

**Sources:**  
MA

---

### MB_INC

**Category:**  
State Manipulation

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

### MEM_WRITE_FROM_SR
  
**Category:**  
Memory Operations

**Description:**  
Writes the value currently present in the Front Panel Switch Register to the memory location specified by MA.

**Target:**  
M[MA]

**Expression:**  
M[MA] ← SR

**Sources:**  
MA, SR

**Constraints:**
- Intended for front-panel deposit operations
- May be executed concurrently with FP_SR_TO_MB
- Does not depend on MB contents

---

### MQ_CLEAR
  
**Category:**  
State Manipulation

**Description:**  
Clears the Multiplier Quotient register.

**Target:**  
MQ

**Expression:**  
MQ ← 0

**Sources:**  
(none)

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

### PC_SET_1

**Category:**  
State Manipulation

**Description:**  
Sets the program counter to address 0001.

**Target:**  
PC

**Expression:**  
PC ← 0001

**Sources:**  
(none)

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

### PC_TO_MB
  
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

