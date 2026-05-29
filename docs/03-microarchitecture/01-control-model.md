## Control Model

Status: normative

### Definition

Control is implemented **exclusively** as a ROM-based mapping:

    CONTROL = ROM[MS, TS, IR_fields, FLAGS]

There is no hardwired instruction sequencing logic.

---

## Inputs

- MS (Major State)
- TS (Time State)
- IR fields:
  - opcode
  - indirect bit
- FLAGS (subset required)

---

## Outputs

- Datapath control signals
- MS_next (next major state)

---

## Semantics

During TS:
- CONTROL outputs are stable

At TP:
- All state changes occur
- Registers latch
- MS ← MS_next

---

## Constraints

- All instruction behavior must be representable as ROM entries
- No control behavior may exist outside the ROM mapping
- Timing (TS/TP) and control (ROM) are strictly separated

---

## Implication

The system is a microcoded machine.

All execution behavior is defined declaratively as:
    (MS, TS, IR, FLAGS) → CONTROL
