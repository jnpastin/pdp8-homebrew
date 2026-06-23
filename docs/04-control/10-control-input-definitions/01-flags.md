## Derived Flags

### Purpose

Defines primitive condition signals (FLAGS) used as inputs to the control function:

```
CONTROL = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

FLAGS provide stable, register-derived interpretations of system state.

---

### Core Invariants

1. **Flags must reference consuming μops**
   - Every FLAG definition must explicitly list the μops that depend on it.

2. **All references must use GitHub link format**
   - Must follow: `[Readable Text](relative/path.md)`
   - Raw paths are prohibited.

3. **Flags are derived only from stable register state**
   - Evaluated continuously during TS
   - Updated only after TP
   - Must not depend on transient datapath values

4. **Flags are not state**
   - No storage
   - No independent evolution

---

### Timing Model

- Registers are latched at TP(n)
- Registers are stable during TS(n)
- FLAGS are combinationally derived from register outputs
- FLAGS remain stable throughout TS(n)
- FLAGS may change only after TP(n+1)

---

### Constraints

FLAGS must:

- Be derived only from registers
- Not depend on:
  - MB
  - DB / MDB
  - μop intermediate values
  - control signals
- Represent minimal, orthogonal conditions
- Not duplicate derivable logic unnecessarily

---

## Flag Definitions

---

### ACN

**Name:** AC_IS_NEGATIVE  
**Source Register:** AC  
**Purpose:** Identifies whether the accumulator contains a negative value based on sign bit.  

**Value Encoding:**
- `0` → AC[11] = 0 (non-negative)
- `1` → AC[11] = 1 (negative)

**Used By μops:**
- Skip decision logic associated with Group 2 operations:
  - [Conditional Skip Execution](../03-microarchitecture/03-microoperation-sequencing.md)

---

### ACZ

**Name:** AC_IS_ZERO  
**Source Register:** AC  
**Purpose:** Detects whether the accumulator value is zero.  

**Value Encoding:**
- `0` → AC ≠ 0
- `1` → AC = 0

**Used By μops:**
- Skip decision logic:
  - [Conditional Skip Execution](../03-microarchitecture/03-microoperation-sequencing.md)

---

### EAI

**Name:** EA_IS_AUTOINDEX  
**Source Register:** EA_ADDR  
**Purpose:** Indicates that the effective address lies within the auto-index range and requires increment behavior.  

**Value Encoding:**
- `0` → EA_ADDR ∉ [0010–0017]
- `1` → EA_ADDR ∈ [0010–0017] (octal)

**Used By μops:**
- Auto-index increment sequencing:
  - [Memory Read μops](../03-microarchitecture/02-micro-operations.md)
  - [Microoperation Sequencing](../03-microarchitecture/03-microoperation-sequencing.md)

---

### IE

**Name:** IE_IS_SET  
**Source Register:** IE  
**Purpose:** Indicates whether interrupts are enabled.  

**Value Encoding:**
- `0` → Interrupts disabled
- `1` → Interrupts enabled

**Used By μops:**
- Interrupt entry control:
  - [Interrupt Control Flow](../04-control/03-control-constraints.md)
- Modified by:
  - [IE_SET](../03-microarchitecture/02-micro-operations.md)
  - [IE_CLEAR](../03-microarchitecture/02-micro-operations.md)

---

### II

**Name:** II_IS_SET  
**Source Register:** II  
**Purpose:** Indicates that interrupt inhibit is active, preventing immediate interrupt entry.  

**Value Encoding:**
- `0` → No inhibition
- `1` → Interrupts inhibited

**Used By μops:**
- Interrupt gating logic:
  - [Interrupt Control Flow](../04-control/03-control-constraints.md)
- Modified by:
  - [II_SET](../03-microarchitecture/02-micro-operations.md)

---

### IP

**Name:** INTERRUPT_PENDING  
**Source Register:** EXT (synchronized interrupt request)  
**Purpose:** Indicates that an interrupt request is pending from external devices.  

**Value Encoding:**
- `0` → No interrupt request
- `1` → Interrupt request pending

**Used By μops:**
- Interrupt entry sequencing:
  - [Interrupt Control Flow](../04-control/03-control-constraints.md)
- Combined with:
  - IE_IS_SET
  - II_IS_SET

---

### LZ

**Name:** L_IS_ZERO  
**Source Register:** L  
**Purpose:** Determines whether the Link register is zero.  

**Value Encoding:**
- `0` → L = 1
- `1` → L = 0

**Used By μops:**
- Skip decision logic:
  - [Conditional Skip Execution](../03-microarchitecture/03-microoperation-sequencing.md)

---

#### MBZ — Memory Buffer Zero

**Width:** 1 bit  
**Role:** Indicates whether the memory buffer contains zero  
**Visibility:** Control  
**Type:** Derived (combinational)

**Definition:**
```
MBZ = (MB == 0)
```

**Invariants:**
- Derived from MB register state only
- Valid only when MB is stable
- No storage; recomputed combinationally each TS

**Constraints:**
- Must not depend on:
  - control signals
  - memory bus state (MDB)
  - transient datapath values
- May be used only after MB has been updated and is stable

**Used By μops:**
- [PC_INC](../03-microarchitecture/02-micro-operations.md#pc_inc)

---

## Summary

This flag set is:

- Minimal (no redundancy)
- Orthogonal (independent conditions)
- Fully sufficient for:
  - Group 2 skips
  - Indirect auto-index behavior
  - Interrupt control flow

All FLAGS:

- Reflect only committed register state
- Are stable during TS
- Serve exclusively as inputs to control decisions