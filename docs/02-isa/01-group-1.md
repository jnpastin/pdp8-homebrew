# Group 1 OPR Encoding Model

## 1. Purpose

Defines the encoding of Group 1 OPR instructions and the order in which their operations take effect.

---

Each of the lower 8 bits of the instruction are flags for a specific operation.  If multiple flags are selected, they will all be executed.  The operations take effect in a fixed order, which must be taken into consideration when combining them: CLA and CLL; then CMA and CML; then IAC; then RAR, RAL, RTR, RTL, or BSW.

```
┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │
├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│  1 │  1 │  1  │ 0  │     │     │     │     │     │     │     │     │
├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│      OPR      │    │ CLA │ CLL │ CMA │ CML │ RAR │ RAL │ BSW │ IAC │
└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

---

## 2. Flag Definitions and Order

Each flag performs a single operation. Operations with a lower Order take effect first; those with the same Order are independent.

| Mnemonic | Order | Operation |
|---|---|---|
| CLA | 1 | Clear AC |
| CLL | 1 | Clear L |
| CMA | 2 | One's complement AC |
| CML | 2 | Complement L |
| IAC | 3 | Increment AC (carry propagates into L) |
| RAR | 4<sup>(1)</sup> | Rotate AC & L right |
| RAL | 4<sup>(2)</sup> | Rotate AC & L left |
| BSW | 4<sup>(3)</sup> | Swap 6 high bits of AC with 6 low bits of AC |

1. If `RAR` is combined with `BSW`, the effect will be to rotate right twice
2. If `RAL` is combined with `BSW`, the effect will be to rotate left twice
3. In order for `BSW` to actually swap, `RAR` and `RAL` must both be `0`.  Also, BSW was added in the PDP-8/E, where 7002 had been a NOP (Small Computer Handbook, 1973, Table 2-1, p. 2-10), so software that is intended to be portable to older systems should avoid using it.  Prior systems used bit 1 solely as a modifier to bits 2 and 3.
4. If `RAR` and `RAL` are both `1`, no rotate or swap occurs, whatever `BSW` holds; the other selected operations still execute.  DEC allows at most one of RAR, RAL, RTR, RTL, and BSW in an instruction (Small Computer Handbook, 1973, p. 3-12). The codes 7014 and 7016 "produced predictable but undocumented results in the PDP-8/I and PDP-8/L", and are reserved on the PDP-8/E (p. 2-10), so this machine replicates neither, and software should not use them.

### 2.1 NOP

NOP is encoded as 7000.

NOP selects the Group 1 OPR format with no operation bits set.

NOP:
- executes no operations
- does not modify processor state
- does not modify memory or controller state
- does not initiate an external bus operation
- advances normally to the next instruction

---

## 3. Combining Operations

All Group 1 operations can be combined with others into a single instruction.  This allows significant speedup by combining multiple operations, saving the FETCH of each additional instruction.  For example, `CLA` and `CLL` can be combined to clear both AC and L, or `CLA` and `IAC` can be combined to clear then increment the AC, setting it to `0001`.

However, it is critical to understand the order.  For example, if AC is `1354`, a `CMA IAC` complements first (AC = `6423`) and then increments (AC = `6424`).  It does not happen in the opposite order, incrementing and then complementing (AC = `6422`).