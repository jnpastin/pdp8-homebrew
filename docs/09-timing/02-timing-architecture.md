# Timing Architecture

## Purpose

This document defines the structure and rules of the timing system.

It describes:
- how time is represented
- how events are scheduled
- how execution is sequenced

---

## CPU Timing Overview

The CPU timing model is illustrated in the following diagram:

../../diagrams/timing/cpu-timing/export/cpu-timing-overview.png

This diagram represents the canonical timing structure:
- Time States (TS) define phase windows
- Timing Pulses (TP) define execution events
- All actions occur at TP events

---

# 1) Timing Model Overview

The system uses a layered timing model:

TCLK → TSTEP → TP → TS  

with a separate control layer:

MS (Major State)

---

# 2) Timing Sequence

## 2.1 Timing Progression

On each rising edge of TCLK:

- TSTEP advances to the next position
- Exactly one TSTEP is active

---

## 2.2 Timing Pulses

Each TSTEP generates a corresponding TP:

TPn = active when TSTEPn is active

TP is:
- one timing step wide
- aligned to the rising edge of TCLK
- the only event trigger in the system

---

# 3) Time States

## 3.1 Structure

Time States are defined as ranges of timing steps:

TS1 = TSTEP range  
TS2 = TSTEP range  
TS3 = TSTEP range  
TS4 = TSTEP range  

---

## 3.2 Function

TS provides:

- setup intervals
- stable conditions
- enabled datapaths

TS signals represent **phase windows**, not events.

Transitions of TS do not cause state changes.

---

# 4) Event Semantics

## 4.1 Core Rule

TS defines when an operation is allowed  
TP defines when the operation occurs  

---

## 4.2 Execution Pattern

TSn:
  data stabilizes

TPn:
  data is latched (state change occurs)

TS(n+1):
  results are used

---

## 4.3 Diagram Interpretation

As shown in the CPU timing overview diagram:

- TS signals are represented as level signals (windows)
- TP signals are represented as event markers (arrows)
- Only TP markers indicate execution events
- TS edges represent phase transitions only and have no event semantics

---

# 5) State Change Rules

## Rule 1 — Event-Driven Updates

All state changes occur on TP events.

---

## Rule 2 — Setup Before Event

All inputs must be stable before TP.

---

## Rule 3 — Phase Transition

TS transitions occur after TP on the next clock edge.

---

## Rule 4 — No Level-Driven Behavior

No state changes occur directly from TS levels.

---

## Rule 5 — No Falling Edge Dependence

Only the TP rising edge is significant.

---

# 6) Major State Integration

## 6.1 Role of MS

MS defines:
- operation type
- control flow

---

## 6.2 Relationship

MS operates over one or more TS/TP cycles:

MS → TS → TP

---

## 6.3 Transitions

Major State changes occur at defined TP events.

---

# 7) Fast vs Slow Timing

## 7.1 Mechanism

Timing speed is controlled by modifying TSTEP progression.

- Slow: all steps executed
- Fast: some steps skipped

---

## 7.2 Effect

- TS duration changes as a result of TSTEP changes
- TP count per cycle changes
- MS behavior remains unchanged

---

# 8) Summary

The system timing model enforces:

- deterministic execution
- discrete event-driven state changes
- clear separation between:
  - timing (TS, TP)
  - control (MS)

---

# 9) Next Steps

- Define Major State timing behavior
- Define instruction-level timing
- Define memory and I/O timing interactions
