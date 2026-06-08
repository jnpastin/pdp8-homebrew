## FETCH and DEFER Execution

### Purpose

Defines the execution behavior of the FETCH and DEFER major states.

This includes:
- instruction fetch
- base effective address (EA) formation
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
  - form base EA
  - determine next MS

- DEFER:
  - resolve indirect addressing
  - handle autoindex
  - finalize EA

---

## FETCH Execution

### TS1

μops:
- PC_TO_MA

Description:
- Places the instruction address in MA for memory access.

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
- IR_ADDR_TO_EA

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
- EA_TO_MA

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
- MEM_WRITE_FROM_MB

Condition:

    if EA is within autoindex range

Description:
- Increments the value at the indirect address and writes it back to memory.

---

### TS4

μops:
- MB_TO_EA

Control Decisions:

    MS_next ← EXECUTE

Description:
- Updates EA with final resolved address
- Transitions to EXECUTE

---

## Invariants

- IR is valid after TP3 of FETCH
- PC is incremented exactly once per instruction
- EA is fully resolved before EXECUTE
- All state changes occur at TP
- Control decisions are based only on stable register values

---

## Summary

FETCH loads the instruction, advances the PC, and forms base addressing.
DEFER resolves indirection and prepares the final effective address.
