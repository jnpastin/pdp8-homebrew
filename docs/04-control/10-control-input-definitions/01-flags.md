# Primitive Flags

## 1. Purpose

Defines primitive condition signals (FLAGS) used as inputs to the control function:

```
CONTROL = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

FLAGS provide stable, register-derived interpretations of system state.

---

## 2. Timing Model

- Registers are latched at TP(n)
- Registers are stable during TS(n)
- FLAGS are combinationally derived from register outputs
- FLAGS remain stable throughout TS(n)
- FLAGS may change only after TP(n+1)

---

## 3. Constraints

FLAGS must:

- Be derived only from registers or synchronized external inputs
- Not depend on:
  - DB / MDB
  - μop intermediate values
  - control signals
  - transient datapath values
- Represent minimal, orthogonal conditions
- Not duplicate derivable logic unnecessarily

---

## 4. Flag Definitions

---

### ACN

**Name:** AC_IS_NEGATIVE  
**Source Register:** AC  
**Purpose:** Indicates whether the accumulator sign bit is set.

**Value Encoding:**
- `0` → AC[11] = 0 (non-negative)
- `1` → AC[11] = 1 (negative)

**Consumed By:**
- Skip logic driving:
  - [PC_INC μop](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### ACZ

**Name:** AC_IS_ZERO  
**Source Register:** AC  
**Purpose:** Indicates whether the accumulator value is zero.

**Value Encoding:**
- `0` → AC ≠ 0
- `1` → AC = 0

**Consumed By:**
- Skip logic driving:
  - [PC_INC μop](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### CIFP

**Name:** CIF_PENDING  
**Source Register:** CIFP  
**Purpose:** Indicates that a deferred instruction-field change (CIF) is pending, awaiting the next JMP/JMS.

**Value Encoding:**
- 0 → no CIF pending
- 1 → CIF pending

**Consumed By:**
- Control decision:
  - Interrupt inhibit gating (holds II across the CIF-to-branch window)
  - FETCH II_CLEAR selection (II_CLEAR is selected only when CIFP = 0)
- Modified by:
  - [CIFP_SET](../../03-microarchitecture/02-micro-operations.md#cifp_set)
  - [CIFP_CLEAR](../../03-microarchitecture/02-micro-operations.md#cifp_clear)

---

### EAI

**Name:** EA_IS_AUTOINDEX  
**Source Register:** EA_ADDR  
**Purpose:** Indicates that the effective address lies within the auto-index range.

**Value Encoding:**
- `0` → EA_ADDR ∉ [0010–0017]
- `1` → EA_ADDR ∈ [0010–0017] (octal)

**Consumed By:**
- Auto-index execution:
  - [MB_INC μop](../../03-microarchitecture/02-micro-operations.md#mb_inc)
  - [MEM_WRITE_FROM_MB μop](../../03-microarchitecture/02-micro-operations.md#mem_write_from_mb)

---

### HLT_REQ

**Name:** HALT_REQUEST_PENDING  
**Source Register:** HLT_REQ  
**Purpose:** Indicates that a halt request is pending.  

**Value Encoding:**
- 0 → no pending halt request
- 1 → halt request pending

**Consumed By:**
- Control decision:
  - Instruction-completion halt processing

---

### IE

**Name:** IE_IS_SET  
**Source Register:** IE  
**Purpose:** Indicates whether interrupts are enabled.

**Value Encoding:**
- `0` → interrupts disabled
- `1` → interrupts enabled

**Consumed By:**
- Control decision:
  - Interrupt entry condition (control logic)
- Modified by:
  - [IE_SET μop](../../03-microarchitecture/02-micro-operations.md#ie_set)
  - [IE_CLEAR μop](../../03-microarchitecture/02-micro-operations.md#ie_clear)

---

### II

**Name:** II_IS_SET  
**Source Register:** II  
**Purpose:** Indicates that interrupt inhibit is active.

**Value Encoding:**
- `0` → not inhibited
- `1` → inhibited

**Consumed By:**
- Control decision:
  - Interrupt entry gating (control logic)
- Modified by:
  - [II_SET μop](../../03-microarchitecture/02-micro-operations.md#ii_set)
  - [II_CLEAR μop](../../03-microarchitecture/02-micro-operations.md#ii_clear)

---

### IOT_READ_PENDING

**Name:** IOT Read Transfer Pending  
**Source Register:** `IOT_TRANSFER`  
**Purpose:** Indicates that an external-IOT read request was accepted at the preceding TP and must execute during the current TS.

**Derivation:**

```text
IOT_READ_PENDING = (IOT_TRANSFER = 01)
```

**Value Encoding:**

- 0: no device-to-CPU DB transfer is pending
- 1: a device-to-CPU DB transfer is pending

**Consumed By:**

- `/DB_READ` generation during the active transfer TS
- `DB_READ_TO_AC` selection at the associated transfer commit TP

---

### IOT_WRITE_PENDING

**Name:** IOT Write Transfer Pending  
**Source Register:** `IOT_TRANSFER`  
**Purpose:** Indicates that an external-IOT write request was accepted at the preceding TP and must execute during the current TS.

**Derivation:**

```text
IOT_WRITE_PENDING = (IOT_TRANSFER = 10)
```

**Value Encoding:**

- 0: no CPU-to-device DB transfer is pending
- 1: a CPU-to-device DB transfer is pending

**Consumed By:**

- `/DB_WRITE` generation during the active transfer TS
- `DB_WRITE_FROM_AC` selection during the active transfer TS

**Constraints:**

- `IOT_READ_PENDING` and `IOT_WRITE_PENDING` must never both be asserted.
- Both flags are combinational interpretations of committed `IOT_TRANSFER` state.
- Neither flag introduces additional stored state.

---

### LZ

**Name:** L_IS_ZERO  
**Source Register:** L  
**Purpose:** Indicates whether the Link register is zero.

**Value Encoding:**
- `0` → L = 1
- `1` → L = 0

**Consumed By:**
- Skip logic driving:
  - [PC_INC μop](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### MBZ

**Name:** MB_IS_ZERO  
**Source Register:** MB  
**Purpose:** Indicates whether the memory buffer contains zero.

**Value Encoding:**
- `0` → MB ≠ 0
- `1` → MB = 0

**Consumed By:**
- ISZ execution:
  - [PC_INC μop](../../03-microarchitecture/02-micro-operations.md#pc_inc)

---

### RUN

**Name:** RUN_STATE  
**Source Register:** RUN  
**Purpose:** Indicates whether normal instruction execution is active.  

**Value Encoding:**  
- 0 → processor halted
- 1 → processor executing

**Consumed By:**
- Control decision:
  - Front panel execution control
  - Single-step control
  - Single-instruction control

---

## 5. Summary

This flag set is:

- Minimal (no redundancy)
- Orthogonal (independent conditions)
- Fully sufficient for:
  - Group 2 skip evaluation
  - ISZ conditional skip
  - Auto-index behavior
  - Interrupt control

All FLAGS:

- Reflect only committed register state
- Are stable during TS
- Serve exclusively as inputs to control decisions