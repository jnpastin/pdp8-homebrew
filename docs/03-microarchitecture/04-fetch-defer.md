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

    FETCH → (DEFER if indirect) → (EXECUTE unless JMP or OPR)

The path of each instruction:

| Instruction | `IR_CLASS` | Major states | Completes at |
|---|---|---|---|
| AND, TAD, ISZ, DCA, JMS | 000 | FETCH, DEFER if indirect, EXECUTE | EXECUTE TP4 |
| IOT | 000 | FETCH, EXECUTE | EXECUTE TP4 |
| JMP | 001 | FETCH | FETCH TP4 |
| JMP I | 010 | FETCH, DEFER | DEFER TP4 |
| OPR Group 1 | 011 | FETCH | FETCH TP4 |
| OPR Group 2 | 100 | FETCH | FETCH TP4 |
| OPR Group 3 | 101 | FETCH | FETCH TP4 |

Responsibilities:

- FETCH:
  - load IR
  - increment PC
  - form EA_ADDR
  - complete a direct JMP or an OPR
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
IR_CLASS = 011 OR IR_CLASS = 100 OR IR_CLASS = 101 -> OPR_PASS
IR_CLASS = 100 -> OPR_SKIP_REQ_TO_SKIP
IR_CLASS = 101 -> OPR_PASS_TO_MQ
IR_CLASS = 001 AND CIFP = 1 -> II_CLEAR
```

Description:
- Forms the base EA from IR and the page of MA (the instruction's address). An OPR does not use it.
- What else happens at TP3 depends on the instruction:

| Instruction | At TP3 | Details |
|---|---|---|
| Group 1 OPR | AC and L load from the OPR pass unit | [Group 1 Execution](./07-opr/01-group1-execution.md) |
| Group 2 OPR | AC loads from the pass unit; `SKIP` loads the skip decision; a HLT sets `HLT_REQ` | [Group 2 Execution](./07-opr/02-group2-execution.md), [HLT capture](../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#344-hlt-instruction-request-capture) |
| Group 3 OPR | AC and MQ load from the pass unit | [Group 3 Execution](./07-opr/03-group3-execution.md) |
| Direct JMP | PC loads the formed address; with a field change pending, `II` clears (the field loads at TP4) | [Deferred Field Application](../08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md#12-deferred-field-application) |

- Every input is the value held before TP3, so the skip decision does not see a CLA in the same instruction.
- Because `II` clears at TP3, an interrupt may be recognized when the JMP completes at TP4, as on the KM8-E, which negates INT INHIBIT at TP3 of a JMP or JMS.

---

### 3.4 TS4

μops:
- (no μops)

Conditional μops:

```text
IR_CLASS = 100 AND SKIP = 1 -> PC_INC
IR_CLASS = 001 AND CIFP = 1 -> DIF_TO_IF
IR_CLASS = 001 AND CIFP = 1 -> CIFP_CLEAR
```

Control Decisions:

    if IR_NO_EXECUTE == 1 and IR_INDIRECT == 0:
        instruction completion (direct JMP, OPR): MS_NEXT per the instruction-completion rules
    else if IR_INDIRECT == 1:
        MS_NEXT ← DEFER
    else:
        MS_NEXT ← EXECUTE

Description:
- Determines the next major state. The instruction-completion rules (interrupt entry, DMA entry, halts) are defined in [Sequencing and Internal Control §3](../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#3-sequencing-control)
- A Group 2 OPR whose `SKIP` is set increments PC at this TP4, concurrently with the instruction-completion decision. An interrupt recognized at the same TP4 saves the incremented PC as the return address; no special case applies ([Skip Model §14](../08-interrupts-and-skip/05-skip-model.md#14-relationship-to-interrupt-and-dma-recognition))
- A direct JMP with a pending field change loads IF and clears `CIFP` at this TP4, the TP that completes it, as the KM8-E does ([Interrupt Enable and Inhibit §12](../08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md#12-deferred-field-application)). An interrupt recognized at the same TP4 saves the new field, because INTERRUPT reads IF after it.

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
        instruction completion (JMP I): MS_NEXT per the instruction-completion rules
    else:
        MS_NEXT ← EXECUTE

Description:

- Writes the incremented value back to memory when auto-index is required.
- Updates EA_ADDR register with the final resolved address.
- A JMP I (`IR_CLASS = 010`) loads PC with the final resolved address (MB, after any auto-index increment at TP3), applies a pending instruction-field change, and completes.
  - The field waits until TP4 because the auto-index write-back in this TS must still use the old field (`MFB_SRC = IF`).
  - `CIFP` waits with it, because `CIFP` gates `DIF_TO_IF`.
  - An interrupt recognized at this TP4 saves the new field, because the INTERRUPT state copies IF into IB after the TP.
- Otherwise transitions to EXECUTE.

---

## 5. Invariants

- IR is valid after TP2 of FETCH
- FETCH TP1 increments PC exactly once per instruction; a taken skip adds a separate increment
- EA is fully resolved before EXECUTE
- A direct JMP or an OPR completes at FETCH TP4, and a JMP I at DEFER TP4
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

