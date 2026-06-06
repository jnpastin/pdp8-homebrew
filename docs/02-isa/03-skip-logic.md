## Skip Logic Definition

Status: normative

### Predicate Definitions

- SZA: AC == 0
- SNA: AC != 0
- SNL: Link != 0
- SZL: Link == 0
- SMA: AC < 0
- SPA: AC >= 0

---

## Combination Rules

### OR Group

- SZA
- SNL
- SMA

Uses OR:
OR_result = any true

---

### AND Group

- SNA
- SZL
- SPA

Uses AND:
AND_result = all true

---

## Mixed Case

skip = OR_result AND AND_result

---

## Unconditional

If SKP set:
skip = true

---

## Result

If skip:
SKIP_PENDING ← 1
