## OPR Execution Model

Status: normative

### Principle

OPR instructions are composable bitfields.

There is no concept of a single 'instruction identity'.

---

## Execution Algorithm

Within EXECUTE:

For each TS:
  For each bit in IR:
    If bit corresponds to operation assigned to TS:
      perform operation

---

## Ordering

Ordering is determined only by TS.

Example:
- CMA at TS2
- IAC at TS3

Produces correct CIA behavior.

---

## Constraint

No normalization of instructions is performed.
Equivalent mnemonics are ignored by control.
