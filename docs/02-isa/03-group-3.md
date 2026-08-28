# Group 3 OPR Encoding Model

Prior to the PDP-8/E, any instruction that had bit 8 and bit 0 set was reserved for the EAE, and there was no Group 3.  Beginning with the PDP-8/E MQ was included in the system regardless of whether EAE was present or not.  As a result, code that is intended to be portable to older systems should not use these instructions.

```
┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐
│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │
├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│  1 │  1 │  1  │ 1  │     │     │     │     │     │     │     │  1  │
├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤
│      OPR      │    │ CLA │ MQA │     │ MQL │     │     │     │     │
└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘
```

---

## Flag Definition and Timing

Each flag performs a single operation, these actions will occur at a defined TP during EXECUTE.

| Mnemonic | TP | Operation |
|---|---|---|
| CLA | 1 | Clear AC |
| MQA | 2 | Logical OR AC and MQ, with result in AC.  MQ is not affected |
| MQL | 2 | Clear MQ, then move the AC into MQ.  AC is cleared |

When MQA and MQL are combined, the result is the SWP instruction (7521), which exchanges AC and MQ (AC and MQ each receive the other's prior value).

---

## Combining Operations

 Similar to Group 1, combined operations that happen at different TPs will happen in that order.  `CLA MQL` will clear AC and then move that into MQ, effectively clearing both.  Conversely `CLA MQA` will clear the AC, then OR the MQ into the AC, resulting in AC = MQ.
 
 `MQA` and `MQL` combined form `SWP` (7521), which exchanges AC and MQ. This parallels the Group 1 rotate encoding, where two bits that would otherwise conflict select a single combined operation. `SWP` may still be combined with `CLA`: since `CLA` clears AC at TP1 and the exchange occurs at TP2, `CLA SWP` (7621) results in AC = old MQ and MQ = 0.