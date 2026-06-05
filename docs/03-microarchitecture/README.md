## Microarchitecture Overview

Reference Diagram:
![High-Level Architecture Diagram](../../diagrams/architecture/High-Level-Architecture/export/High-Level-Architecture.png)

---

## Purpose

Defines how ISA behavior is **executed over time**.

This includes:
- execution ordering
- operation composition
- control evaluation model

This section defines **how behavior occurs**, not what the behavior is.

---

## Scope

Includes:
- mapping of execution onto the timing model
- operation ordering within EXECUTE
- composition rules for OPR instructions
- ROM-based control model

Excludes:
- instruction semantics (see ../02-isa/README.md)
- control signal definitions (see ../04-control/README.md)
- timing signal definitions (see ../09-timing/README.md)

---

## Execution Model

Execution is defined over:

(MS, TS)

- MS defines instruction phase
- TS defines ordering within the phase

All state changes occur at TP (see ../09-timing/README.md).

---

## OPR Execution

OPR instructions are **bitwise-composed operations**:

- Each active bit enables an operation
- Each operation is assigned to a TS
- Execution order is determined strictly by TS

No instruction normalization or decode layer exists.

---

## Control Model
 
Status: normative

### Definition
 
Control is implemented **exclusively** as a ROM-based mapping:  
There is no hardwired instruction sequencing logic.

### Inputs
- MS (Major State)
- TS (Time State)
- IR fields
- FLAGS

### Outputs
- Datapath control signals
- MS\_next (next major state)

### Semantics
 
During TS:
- CONTROL outputs are stable 

At TP:
- All state changes occur
- Registers latch
- MS ← MS\_next

### Constraints
- All instruction behavior must be representable as ROM entries
- No control behavior may exist outside the ROM mapping
- Timing (TS/TP) and control (ROM) are strictly separated

---

## Relationship to Other Sections

- Uses timing definitions from ../09-timing/README.md
- Executes semantics defined in ../02-isa/README.md
- Drives signals defined in ../04-control/README.md