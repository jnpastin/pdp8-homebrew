## Group 2 OPR Encoding Model

Group 2 is divided into two sub-groups, the AND sub-group and the OR sub-group.  When combining operations into a single instruction, the AND sub-group treats all conditions for operations that happen in the same TP as a logical AND.  The same is true of the OR sub-group, they are all treated as a logical OR.  The sub-group flag is bit 3, bit 0 is always `0`.  Note that `CLA`, `OSR` and `HLT` are evaluated in order based off of their specific timing regardless of the state of bit 3.

---

### AND Sub-Group Definition and Timing
```
┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │
├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│  1 │  1 │  1  │ 0  │     │     │     │     │     │     │     │     │
├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│      OPR      │ G2 │ CLA │ SPA │ SNA │ SZL │  1  │ OSR │ HLT │  0  │
└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

### Flag Definition and Timing

| Mnemonic | TP | Operation |
|---|---|---|
| CLA | 2 | Clear AC |
| SPA | 1 | Skip on positive AC (`0000` is positive) |
| SNA | 1 | Skip on non-zero AC |
| SZL | 1 | Skip on zero L |
| OSR | 3 | Logical OR SR with AC |
| HLT | 3 | Halt |

### Combining AND Sub-Group operations

All operations that happen at TP1 are evaluated as if the conditions are a logical AND.  For example, `SPA SNA` will skip if the AC is non-negative AND non-zero.  Similar to Group 1, combined operations that happen at different TPs will happen in that order (`SNA HLT` will skip if AC is non-zero, updating the PC then halting).

---

### OR Sub-Group Definition and Timing
```
┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │
├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│  1 │  1 │  1  │ 0  │     │     │     │     │     │     │     │     │
├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│      OPR      │ G2 │ CLA │ SMA │ SZA │ SNL │  0  │ OSR │ HLT │  0  │
└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

### Flag Definition and Timing

| Mnemonic | TP | Operation |
|---|---|---|
| CLA | 2 | Clear AC |
| SMA | 1 | Skip on negative AC |
| SZA | 1 | Skip on zero AC |
| SNL | 1 | Skip on non-zero L |
| OSR | 3 | Logical OR SR with AC |
| HLT | 3 | Halt |

### Combining AND Sub-Group operations

All operations that happen at TP1 are evaluated as if the conditions are a logical OR.  For example, `SMA SZA` will skip if the AC is negative OR zero.  Similar to Group 1, combined operations that happen at different TPs will happen in that order (`SZA HLT` will skip if AC is zero, updating the PC then halting).
