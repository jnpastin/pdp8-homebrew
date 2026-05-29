## Instruction Encoding Model

Status: normative

### Purpose

Defines how IR bits map directly into control behavior for a ROM-based microarchitecture.

---

## IR Structure

IR[11:0]

- IR[11:9] → class (MRI/IOT/OPR)
- IR[8] → indirect (MRI)
- IR[7] → page (MRI)
- IR[6:0] → address / function bits

---

## Control Interpretation

IR must be interpreted strictly as a bitfield.

Control logic operates on:
(MS, TS, IR bits, FLAGS)

No instruction decoding into symbolic instructions is permitted.

---

## OPR Model

Each bit represents an independent operation.

Execution model:
For TS = 1..4:
  apply all operations whose bits are set for that TS

---

## Execute Time States

TS defines execution ordering within EXECUTE.

Operations assigned to different TS execute in strict order.

---

## Composition Constraint

Operations that:
- target the same register
- and occur in the same TS

are not required to be supported unless explicitly defined.
