# Major State Timing

## Purpose

This document defines the timing behavior of each Major State (MS) in the system.

It describes:
- what occurs during each Time State (TS)
- what actions are taken at each Timing Pulse (TP)
- how Major State transitions occur

This is independent of:
- instruction-specific logic
- control signal implementation

---

# 1) Overview

Major States define the high-level execution stages:

FETCH  
DEFER  
EXECUTE  
INTERRUPT  

Each Major State executes over one or more TS/TP cycles.

---

# 2) Execution Model

Each TS/TP cycle follows:

TSn:
  data is prepared and stabilized

TPn:
  data is latched / state changes occur

TS(n+1):
  next stage consumes data

---

# 3) FETCH

## Purpose

- Acquire next instruction
- Load instruction register (IR)
- Increment PC
- Determine next Major State

---

## Timing

### TS1 — Address Setup
- PC drives the address path

### TP1
MA ← PC

---

### TS2 — Memory Access
- MA stable
- memory read in progress

### TP2
MR ← memory data

---

### TS3 — Transfer to IR
- MR stable

### TP3
IR ← MR

---

### TS4 — PC Update / Decode Prep

### TP4
PC ← PC + 1

---

## Transition

At TP4:

if IR indicates indirect:
  MS ← DEFER  
else:
  MS ← EXECUTE  

---

# 4) DEFER

## Purpose

Resolve indirect addressing by accessing memory at the effective address.

---

## Behavior

- Uses address in MA
- Reads indirect word
- Replaces MA with fetched address

---

## Timing

### TS1 — Address Setup
- MA drives address path

### TP1
MA source is already valid  
(no change)

---

### TS2 — Memory Access
- memory read in progress

### TP2
MR ← memory data

---

### TS3 — Load Effective Address

### TP3
MA ← MR

---

### TS4 — Completion

### TP4
(no register change)

---

## Transition

At TP4:

if indirect bit still set:
  MS ← DEFER  
else:
  MS ← EXECUTE  

---

# 5) EXECUTE (Generic Structure)

## Purpose

Perform instruction-specific operations.

---

## Behavior

Varies based on instruction type:
- MRI instructions (memory reference)
- OPR instructions (operate)
- IOT instructions (I/O transfer)

---

## Timing (Generic Template)

The EXECUTE timing structure is defined as:

### TS1
- prepare operands
- address setup (if required)

### TP1
instruction-specific action

---

### TS2
- memory access (if applicable)

### TP2
instruction-specific action

---

### TS3
- data transfer / ALU operations

### TP3
instruction-specific action

---

### TS4
- finalization

### TP4
instruction-specific completion

---

## Transition

At TP4:

if interrupt pending and enabled:
  MS ← INTERRUPT  
else:
  MS ← FETCH  

---

# 6) INTERRUPT

## Purpose

Handle interrupt request.

---

## Behavior

- Save current PC
- Transfer control to interrupt vector

---

## Timing

### TS1 — Prepare Save

### TP1
(save address setup)

---

### TS2 — Save PC

### TP2
M[0] ← PC

---

### TS3 — Vector Load

### TP3
PC ← interrupt vector (usually address 1)

---

### TS4 — Completion

### TP4
(no additional action)

---

## Transition

At TP4:

MS ← FETCH  

---

# 7) Summary

## Major State Flow

FETCH
 → DEFER (if indirect)
 → EXECUTE
 → INTERRUPT (if pending)
 → FETCH

---

## Key Properties

- All state changes occur on TP
- TS provides setup intervals
- Each Major State uses TS1–TS4 structure
- Major State transitions occur at TP4

---

# 8) Notes

- This document defines base behavior only
- Instruction-specific details are defined in instruction timing
- Memory and I/O timing constraints may refine behavior in later sections