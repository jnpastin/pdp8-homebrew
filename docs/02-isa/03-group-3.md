# Group 3 OPR Encoding Model

## 1. Purpose

Defines the encoding of Group 3 OPR instructions, which move data between AC and MQ.

---

Prior to the PDP-8/E, the MQ instructions were "only available with EAE" (Small Computer Handbook, 1973, Table 2-1, p. 2-10), and there was no Group 3.  Beginning with the PDP-8/E the MQ is included regardless of whether an EAE is present: Group 3 is "also useful when the MQ is employed as a temporary storage register, even if an EAE is not installed" (p. 3-16).  As a result, code that is intended to be portable to older systems should not use these instructions.

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

## 2. Flag Definitions and Order

Each flag performs a single operation. The operations take effect in a fixed order: CLA; then MQA, MQL, or SWP.

| Mnemonic | Order | Operation |
|---|---|---|
| CLA | 1 | Clear AC |
| MQA | 2 | Logical OR AC and MQ, with result in AC.  MQ is not affected |
| MQL | 2 | Clear MQ, then move the AC into MQ.  AC is cleared |

When MQA and MQL are combined, the result is the SWP instruction (7521), which exchanges AC and MQ (section 3).

Bits 5, 3, 2, and 1 are the SCA and operation-code bits of the KE8-E Extended Arithmetic Element (EAE). This machine has no EAE, so they select no operation; CLA, MQA, and MQL still execute. Software should keep them `0`.

---

## 3. Combining Operations

Similar to Group 1, combined operations take effect in their order.  `CLA MQL` will clear AC and then move that into MQ, effectively clearing both.  Conversely `CLA MQA` will clear the AC, then OR the MQ into the AC, resulting in AC = MQ.

`MQA` and `MQL` combined form `SWP` (7521), which exchanges AC and MQ: each receives the other's prior value. This parallels the Group 1 rotate encoding, where two bits that would otherwise conflict select a single combined operation. `SWP` may still be combined with `CLA`: since `CLA` acts before the exchange, `CLA SWP` (7721) results in AC = old MQ and MQ = 0.