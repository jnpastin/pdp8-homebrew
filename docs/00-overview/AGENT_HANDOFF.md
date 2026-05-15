\# PDP-8/e Compatible Discrete Logic Computer
## Agent Handoff Document

Status: active development (timing architecture defined)

---

# 1. Project Summary

## Objective
Design and build a discrete-logic computer compatible with the PDP-8/e architecture.

Primary goal:
- Run OS/8 and standard PDP-8 software (PAL-8, BASIC, diagnostics)

## Constraints
- Discrete logic only (no microcontrollers)
- SRAM-based memory (no core memory)
- Modular PCB system with backplane
- Strong observability and debug capability

## Compatibility Target
- Bit-accurate instruction encoding
- Correct instruction behavior
- Sufficient fidelity for OS/8

---

# 2. Repository Structure (Implemented)

Top-level directories now exist:

- /docs - Design documentation (authoritative)
- /hardware - KiCad schematics and PCB designs
- /firmware - Microcode / ROM content
- /sim - Simulation and validation
- /tools - Supporting utilities
- /diagrams - Visual documentation (domain-organized, source/export per topic)
- /specs - Machine-readable definitions
- /notes - Working exploration
- /build - Generated artifacts

Diagrams are organized by domain (e.g., timing/cpu-timing) with:
- source/ (editable)
- export/ (rendered)

---

# 3. Architectural Model (Current)

## Core
- 12-bit word
- PDP-8 instruction set

## Memory
- 4K words per field
- 8 fields (32K total)
- IF (Instruction Field)
- DF (Data Field)
- No UF initially

## Registers

Programmer-visible:
- PC, AC, MQ, Link, SR

Memory path:
- MA, MR, MB, IR

Field registers:
- IF, DF

Control state:
- Major State (FETCH, DEFER, EXECUTE, INTERRUPT)
- Timing defined as TS/TP model (see Section 6)
- IE, INT_REQ, INT_DELAY
- SKIP_PENDING

## Memory Data Flow

Memory → MR → MB → internal data bus

---

# 4. Behavioral Requirements

## Instruction Set
- MRI, OPR groups, IOT
- Exact bit encoding required
- Correct handling of:
  - indirect addressing
  - auto-index
  - page addressing

## Interrupts
- Recognized at instruction boundaries
- IE-controlled
- CIF introduces delay
- Entry: store PC, jump to location 1

## Skip Logic
- Latched SKIP_PENDING model
- Evaluated during execute
- Applied during next PC increment

---

# 5. Bus Model (Preliminary)

- AB[0:11] - Address bus  
- DB[0:11] - Internal data bus  
- MDB - Memory data bus  
- DEV[0:5] - I/O device select  

I/O data path not finalized.

---

# 6. Timing Model (Defined)

## Overview

The system now uses a formal timing architecture:

TCLK → TSTEP → TP → TS  
+ MS (Major State control)

Where:

- TCLK: timing clock  
- TSTEP: discrete timing position (one-hot)  
- TP: event trigger (derived from TSTEP)  
- TS: phase window (range of TSTEP)  
- MS: instruction-level control state  

---

## Key Semantics

### TS (Time State)
- Represents execution phase (window)
- Multi-cycle duration
- Defines when operations are allowed
- Does NOT trigger state changes

### TP (Timing Pulse)
- Represents execution event (instant)
- One TSTEP wide
- Aligned to rising edge of TCLK
- All state changes occur on TP

---

## Execution Model

TSn:
  data stabilizes

TPn:
  state changes occur

TS(n+1):
  results are consumed

---

## Critical Rules

- All state changes occur on TP (event-driven)
- TS provides setup/stability window
- TS transitions occur after TP
- No falling-edge dependence
- No level-driven state mutation

---

## Major State Integration

Major States:

- FETCH
- DEFER
- EXECUTE
- INTERRUPT

Model:

MS → TS → TP

- MS defines "what"

