## Derived Flags

### Purpose

Defines fully pre-decoded control condition signals derived from:

- IR-derived flags (02-ir_derived_fields.md)
- Primitive FLAGS (01-flags.md)

Derived flags are combinational and reduce multi-input control conditions into single-bit inputs for control.

---

## Derived Flag Definitions

---

### SKIP_TAKEN

**Inputs:**
- IR_OPR_GROUP2
- IR_OPR_SKIP_MODE
- IR_OPR_SMA
- IR_OPR_SZA
- IR_OPR_SNL
- ACN
- ACZ
- LZ

---

**Purpose:**
Determines whether a Group 2 OPR instruction causes a skip (PC increment).

---

**Internal Composition (local to this definition):**

OR-subgroup predicates (active when SKIP_MODE = 0):

```
SMA_OR = ( !IR_OPR_SKIP_MODE ) AND IR_OPR_SMA AND (ACN = 1)
SZA_OR = ( !IR_OPR_SKIP_MODE ) AND IR_OPR_SZA AND (ACZ = 1)
SNL_OR = ( !IR_OPR_SKIP_MODE ) AND IR_OPR_SNL AND (LZ = 0)
```

OR-subgroup result:

```
OR_ANY_TRUE =
      SMA_OR
   OR SZA_OR
   OR SNL_OR
```

AND-subgroup predicates (reinterpretation when SKIP_MODE = 1):

```
SPA = IR_OPR_SKIP_MODE AND IR_OPR_SMA
SNA = IR_OPR_SKIP_MODE AND IR_OPR_SZA
SZL = IR_OPR_SKIP_MODE AND IR_OPR_SNL
```

Masking for AND composition:

```
AND_ALL_TRUE =
      ( !SPA OR (ACN = 0) )
  AND ( !SNA OR (ACZ = 0) )
  AND ( !SZL OR (LZ = 1) )
```

Selected predicate presence:

```
ANY_AND_SELECTED =
      SPA
   OR SNA
   OR SZL
```

Final expression:

```
SKIP_TAKEN =
    IR_OPR_GROUP2
AND (
       ( !IR_OPR_SKIP_MODE AND OR_ANY_TRUE )
    OR ( IR_OPR_SKIP_MODE AND ANY_AND_SELECTED AND AND_ALL_TRUE )
)
```

---

**Value Encoding:**
- `0` → no skip
- `1` → increment PC

---

**Used By μops:**
- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### ISZ_SKIP_REQUIRED

**Inputs:**
- IR_IS_ISZ
- MBZ

---

**Purpose:**
Determines whether ISZ causes a skip after increment.

---

**Expression:**

```
ISZ_SKIP_REQUIRED =
    IR_IS_ISZ
AND MBZ
```

---

**Value Encoding:**
- `0` → no skip
- `1` → increment PC

---

**Used By μops:**
- [PC_INC](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### AUTO_INDEX_REQUIRED

**Inputs:**
- IR_INDIRECT
- EAI

---

**Purpose:**
Determines whether auto-index increment and writeback must occur.

---

**Expression:**

```
AUTO_INDEX_REQUIRED =
    IR_INDIRECT
AND EAI
```

---

**Value Encoding:**
- `0` → no auto-index
- `1` → perform auto-index increment

---

**Used By μops:**
- [MB_INC](../../03-microarchitecture/02-micro-operations.md#mb_inc)
- [MEM_WRITE_FROM_MB](../../03-microarchitecture/02-micro-operations.md#mem_write_from_mb)

---

### INTERRUPT_REQUEST_VALID

**Inputs:**
- IE
- II
- INT_REQ

---

**Purpose:**
Determines whether interrupt entry conditions are satisfied.

---

**Expression:**

```
INTERRUPT_REQUEST_VALID =
    IE
AND (II = 0)
AND INT_REQ
```

---

**Value Encoding:**
- `0` → no interrupt
- `1` → enter interrupt sequence

---

**Used By μops:**
- (none — used for MS transition control)

---

## Summary

Derived flags fully encode all composite control conditions for:

- Group 2 skip evaluation
- ISZ conditional skip
- Auto-index behavior
- Interrupt entry

All definitions use only:

- IR-derived flags from 02
- primitive FLAGS from 01

and introduce no new base signals.