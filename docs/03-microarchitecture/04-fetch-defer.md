## FETCH and DEFER Execution

### Purpose

Defines the execution behavior of the FETCH and DEFER major states.

This includes:
- instruction fetch
- base effective address (EA_addr) formation
- indirect address resolution
- determination of next major state

All behavior is expressed using μops (for datapath) and control decisions (for sequencing).

---

## Overview

Execution begins in FETCH for every instruction.

Flow:

    FETCH → (DEFER if indirect) → EXECUTE

Responsibilities:

- FETCH:
  - load IR
  - increment PC
  - form EA_addr
  - determine next MS

- DEFER:
  - resolve indirect addressing
  - handle autoindex
  - finalize EA_addr

---

## FETCH Execution

### TS1

μops:
- PC_TO_MA

μops (conditional):
- if NOT CIFP: II_CLEAR

Description:
- Places the instruction address in MA for memory access.
- Clears the Interrupt Inhibit register, unless a CIF field change is pending (CIFP = 1), in which case the inhibit is held until the pending field is applied at the next JMP/JMS

---

### TS2

μops:
- MEM_READ_TO_MB

Description:
- Reads instruction word from memory into MB.

---

### TS3

μops:
- MB_TO_IR

Description:
- Loads IR with fetched instruction.

---

### TS4

μops:
- PC_INC
- IR_ADDR_TO_EA_ADDR

Control Decisions:

    if IR[INDIRECT] == 1:
        MS_next ← DEFER
    else:
        MS_next ← EXECUTE

Description:
- Advances PC
- Forms base EA
- Determines next major state

---

## DEFER Execution

### Purpose

Resolves indirect addressing by replacing EA with M[EA].
Handles autoindex increment when applicable.

---

### TS1

μops:
- EA_ADDR_TO_MA

Description:
- Prepares effective address for memory access.

---

### TS2

μops:
- MEM_READ_TO_MB

Description:
- Reads the indirect value into MB.

---

### TS3

μops (conditional):
- MB_INC
Description:
- Increments the value at the indirect address

---

### TS4

μops:
- MB_TO_EA_ADDR

μops (conditional):  
- MEM_WRITE_FROM_MB

Condition:

    if EA_ADDR is within autoindex range


Control Decisions:

    MS_NEXT ← EXECUTE

Description:
- Writes incremented value back to memory
- Updates EA_ADDR register with final resolved address
- Transitions to EXECUTE

---

## Invariants

- IR is valid after TP3 of FETCH
- PC is incremented exactly once per instruction
- EA is fully resolved before EXECUTE
- All state changes occur at TP
- Control decisions are based only on stable register values

---

## Execution Boundary Guarantee

All address resolution is completed before entering EXECUTE.

Instructions in EXECUTE must treat EA as final and must not
perform any indirect or autoindex handling.

---

## Summary

FETCH loads the instruction, advances the PC, and forms base addressing.
DEFER resolves indirection and prepares the final effective address.

