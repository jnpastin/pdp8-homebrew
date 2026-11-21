# FETCH and DEFER Execution

## 1. Purpose

Defines the execution behavior of the FETCH and DEFER major states.

This includes:
- instruction fetch
- base effective address (EA_ADDR) formation
- indirect address resolution
- determination of next major state

All behavior is expressed using μops (for datapath) and control decisions (for sequencing).

---

## 2. Overview

Execution begins in FETCH for every instruction.

Flow:

    FETCH → (DEFER if indirect) → (EXECUTE unless JMP or Group 1 OPR)

Responsibilities:

- FETCH:
  - load IR
  - increment PC
  - form EA_ADDR
  - complete a direct JMP or a Group 1 OPR
  - determine next MS

- DEFER:
  - resolve indirect addressing
  - handle autoindex
  - finalize EA_ADDR
  - complete a JMP I

---

## 3. FETCH Execution

### 3.1 TS1

μops:
- PC_TO_MA
- PC_INC

Conditional μops:

```text
CIFP = 0 -> II_CLEAR
```

Description:
- Places the instruction address in MA and advances PC; MA receives the pre-increment PC at the same TP.
- Clears the Interrupt Inhibit register, unless a deferred instruction field change is pending (CIFP = 1), in which case the inhibit is held until the pending field is applied at the next JMP/JMS

---

### 3.2 TS2

μops:
- MEM_READ_TO_MB
- MDB_TO_IR

Description:
- Reads the instruction word from memory into MB and IR.

---

### 3.3 TS3

μops:
- IR_ADDR_TO_EA_ADDR

Conditional μops:

```text
IR_CLASS = 001 -> IR_ADDR_TO_PC
IR_CLASS = 011 -> OPR_PASS
IR_CLASS = 001 AND CIFP = 1 -> DIF_TO_IF
IR_CLASS = 001 AND CIFP = 1 -> CIFP_CLEAR
IR_CLASS = 001 AND CIFP = 1 -> II_CLEAR
```

Description:
- Forms the base EA from IR and the page of MA (the instruction's address).
- A Group 1 OPR (`IR_CLASS = 011`) loads AC and L from the OPR pass unit, which performs the whole instruction in one pass ([Group 1 Execution](./07-opr/01-group1-execution.md)); the formed EA_ADDR is unused.
- A direct JMP (`IR_CLASS = 001`) loads PC with the same formed address and applies a pending instruction-field change. The same TP3 clears `II`, so an interrupt may be recognized at this instruction's completion ([Interrupt Enable and Inhibit §12](../08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md#12-deferred-field-application)); the KM8-E negates INT INHIBIT at TP3 of a JMP or JMS.

---

### 3.4 TS4

μops:
- (no μops)

Control Decisions:

    if IR_NO_EXECUTE == 1 and IR_INDIRECT == 0:
        instruction completion (direct JMP, Group 1 OPR): MS_next per the instruction-completion rules
    else if IR_INDIRECT == 1:
        MS_next ← DEFER
    else:
        MS_next ← EXECUTE

Description:
- Determines the next major state. The instruction-completion rules (interrupt entry, DMA entry, halts) are defined in [Sequencing and Internal Control §3](../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#3-sequencing-control)

---

## 4. DEFER Execution

### 4.1 Purpose

Resolves indirect addressing by replacing EA with M[EA].
Handles autoindex increment when applicable.

---

### 4.2 TS1

μops:
- EA_ADDR_TO_MA

Description:
- Prepares effective address for memory access.

---

### 4.3 TS2

μops:
- MEM_READ_TO_MB

Description:
- Reads the indirect value into MB.

---

### 4.4 TS3

Conditional μops:

```text
AUTO_INDEX_REQUIRED = 1 -> MB_INC
IR_CLASS = 010 AND CIFP = 1 -> II_CLEAR
```

Description:

- Increments the value at the indirect address when auto-index is required.
- A JMP I (`IR_CLASS = 010`) with a pending instruction-field change clears `II` at this TP3, as a direct JMP does at FETCH TP3, so an interrupt may be recognized at its completion. The field itself is applied at TP4 (section 4.5).

---

### 4.5 TS4

μops:
- MB_TO_EA_ADDR

Conditional μops:

```text
AUTO_INDEX_REQUIRED = 1 -> MEM_WRITE_FROM_MB
IR_CLASS = 010 -> MB_TO_PC
IR_CLASS = 010 AND CIFP = 1 -> DIF_TO_IF
IR_CLASS = 010 AND CIFP = 1 -> CIFP_CLEAR
```

Control Decisions:

    if IR_NO_EXECUTE == 1:
        instruction completion (JMP I): MS_next per the instruction-completion rules
    else:
        MS_next ← EXECUTE

Description:

- Writes the incremented value back to memory when auto-index is required.
- Updates EA_ADDR register with the final resolved address.
- A JMP I (`IR_CLASS = 010`) loads PC with the final resolved address (MB, after any auto-index increment at TP3), applies a pending instruction-field change, and completes. The field is applied at TP4, not TP3, because the auto-index write-back in this TS addresses the pointer's field through IF (`MFB_SRC = IF`); an IF change at TP3 would write the pointer into the new field. `CIFP` is cleared at the same TP4, because it gates `DIF_TO_IF`. An interrupt recognized at this TP4 saves the new field, because the INTERRUPT state copies IF into IB after the TP.
- Otherwise transitions to EXECUTE.

---

## 5. Invariants

- IR is valid after TP2 of FETCH
- PC is incremented at FETCH TP1
- PC is incremented exactly once per instruction
- EA is fully resolved before EXECUTE
- A direct JMP completes at FETCH TP4 and a JMP I at DEFER TP4
- All state changes occur at TP
- Control decisions are based only on stable register values

---

## 6. Execution Boundary Guarantee

All address resolution is completed before entering EXECUTE.

Instructions in EXECUTE must treat EA as final and must not
perform any indirect or autoindex handling.

---

## 7. Summary

FETCH loads the instruction, advances the PC, and forms base addressing.
DEFER resolves indirection and prepares the final effective address.

