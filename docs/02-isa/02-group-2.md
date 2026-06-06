## Group 1 OPR Encoding Model

Each of the lower 8 bits of the instruction are flags for a specific operation.  If multiple flags are selected, they will all be executed.  Each operation occurs at a specific time during EXECUTE, this is fixed and must be taken into consideration when combining instructions.

```
┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │
├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│  1 │  1 │  1  │ 1  │     │     │     │     │     │     │     │     │
├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│      OPR      │ G1 │ CLA │ CLL │ CMA │ CML │ RAR │ RAL │ BSW │ IAC │
└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

### Flag Definition and Timing

Each flag performs a single operation, these actions will occur at a defined TP during EXECUTE.

| Mnemonic | TP | Operation |
|---|---|---|
| CLA | 1 | Clear AC
| CLL | 1 | Clear L
| CMA | 2 | One's complement AC
| CML | 2 | Complement L
| RAR | 4<sup>(1)</sup> | Rotate AC & L right
| RAL | 4<sup>(2)</sup> | Rotate AC & L left
| BSW | 4<sup>(3)</sup> | Swap 6 high bits of AC with 6 low bits of AC
| IAC | 3 | Increment AC

1. If `RAR` is combined with `BSW`, the effect will be to rotate right twice
2. If `RAL` is combined with `BSW`, the effect will be to rotate left twice
3. In order for `BSW` to actually swap, `RAR` and `RAL` must both be `0`

### Combining Operations

All Group 1 operations can be combined with others into a single instruction.  This allows significant speedup by combining multiple operations, skipping additional FETCH and EXECUTE states.  For example, `CLA` and `CLL` can be combined to clear both AC and L, or `CLA` and `IAC` can be combined to clear then increment the AC, setting it to `0001`.

However, it is critical to understand the timing.  For example, if AC is `1354`, a `CMA IAC` will happen with the CMA at TP2 and the IAC at TP3.  This will complement first (AC = `6423`) then increment (AC = `6424`).  It will NOT happen in the opposite order, incrementing and then complementing (AC = `6422`)