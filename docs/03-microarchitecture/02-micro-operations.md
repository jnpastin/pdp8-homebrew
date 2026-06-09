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
- #ir_addr_to_ea_addr

### Arithmetic / Logical
- #add_ac_mb
- #mb_inc

### Control Flow
- #pc_inc
- #pc_load_ea_addr

### Memory Operations
- #mem_read_to_mb
- #mem_write_from_mb

### Register Transfer
- #ea_to_ma
- #mb_to_ea
- #mb_to_ir
- #pc_to_ma

### State Manipulation
- #ac_clear
- #ac_complement
- #ac_inc

---

## μop Definitions (Alphabetical)

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

## Notes

- This catalog is closed; all execution must be expressed using these μops.
- New μops may be introduced only when required for ISA completeness.
- Conditions are evaluated directly from register state and must not be represented as μops.

