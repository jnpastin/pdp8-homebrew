# Group 2 OPR Encoding Model

## 1. Purpose

Defines the encoding of Group 2 OPR instructions, the skip conditions of the AND and OR sub-groups, and the order in which their operations take effect.

---

Group 2 is divided into two sub-groups, the AND sub-group and the OR sub-group.  When combining operations into a single instruction, the AND sub-group treats all of its selected skip conditions as a logical AND.  The same is true of the OR sub-group, they are all treated as a logical OR.  The sub-group flag is bit 3, bit 0 is always `0`.  Regardless of the state of bit 3, the operations take effect in a fixed order: the skip test on the original AC and L; then `CLA`; then `OSR`; then `HLT`.

---

## 2. AND Sub-Group Definition
```
┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │
├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│  1 │  1 │  1  │ 1  │     │     │     │     │  1  │     │     │  0  │
├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│      OPR      │    │ CLA │ SPA │ SNA │ SZL │     │ OSR │ HLT │     │
└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

---

## 3. Flag Definitions and Order

| Mnemonic | Order | Operation |
|---|---|---|
| CLA | 2 | Clear AC |
| SPA | 1 | Skip on positive AC (`0000` is positive) |
| SNA | 1 | Skip on non-zero AC |
| SZL | 1 | Skip on zero L |
| OSR | 3 | Logical OR FP_SR with AC |
| HLT | 4 | Halt |

---

## 4. Combining AND Sub-Group operations

The skip conditions are evaluated as a logical AND.  For example, `SPA SNA` will skip if the AC is non-negative AND non-zero.  Similar to Group 1, combined operations take effect in their order (`SNA HLT` will skip if AC is non-zero, updating the PC then halting).

---

## 5. OR Sub-Group Definition
```
┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │
├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│  1 │  1 │  1  │ 1  │     │     │     │     │  0  │     │     │  0  │
├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│      OPR      │    │ CLA │ SMA │ SZA │ SNL │     │ OSR │ HLT │     │
└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

---

## 6. Flag Definitions and Order

| Mnemonic | Order | Operation |
|---|---|---|
| CLA | 2 | Clear AC |
| SMA | 1 | Skip on negative AC |
| SZA | 1 | Skip on zero AC |
| SNL | 1 | Skip on non-zero L |
| OSR | 3 | Logical OR FP_SR with AC |
| HLT | 4 | Halt |

---

## 7. SKP - Unconditional Skip

SKP (7410) is the AND sub-group with no skip predicates selected (SPA = SNA = SZL = 0). The AND of an empty predicate set is vacuously true, so SKP always skips. The skip is realized as the same PC increment as the conditional skips. SKP may be combined with CLA, OSR, and HLT, which take effect in their order.

---

## 8. Combining OR Sub-Group operations

The skip conditions are evaluated as a logical OR.  For example, `SMA SZA` will skip if the AC is negative OR zero.  Similar to Group 1, combined operations take effect in their order (`SZA HLT` will skip if AC is zero, updating the PC then halting).
