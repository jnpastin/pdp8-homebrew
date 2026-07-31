# 03 Class C - Timing Signals

## Purpose

This document defines Class C signals and their organization within the system.

Class C signals define the timing framework used by the CPU.

This document defines:

- Class C signal characteristics
- Distribution scope
- Signal organization
- Relationship to the timing architecture

This document does NOT define:

- timing behavior
- timing generation
- event ordering
- execution sequencing
- major state transitions

Authoritative timing definitions are maintained in Section 9.

---

## Overview

Class C signals define the timing structure used by the system.

Class C signals:

- are CPU-local
- are timing-critical
- are not visible outside the CPU timing subsystem
- are not intended for use by independent system modules
- establish temporal execution structure

Class C signals do not directly define processor behavior.

---

## Distribution Scope

Class C signals remain local to the CPU timing subsystem.

Class C signals:

- must not be placed on the backplane
- must not be relied upon by independent modules
- must not be exposed as external interfaces

Physical distribution of Class C signals is implementation-dependent.

---

## Signal Categories

### Clock Signals

Clock signals provide the timing source used by the timing system.

Signals:

- MCLK
- TCLK

Authoritative definitions are maintained in:

- [Timing Terminology](../09-timing/01-terminology.md)

### Timing Sequence Signals

Timing sequence signals define progression through the timing system.

Signals:

- TSTEP
- TSEQ

Authoritative definitions are maintained in:

- [Timing Terminology](../09-timing/01-terminology.md)
- [Timing Architecture](../09-timing/02-timing-architecture.md)

### Timing Execution Signals

Timing execution signals define execution windows and execution events.

Signals:

- TS
- TP

Authoritative definitions are maintained in:

- [Timing Terminology](../09-timing/01-terminology.md)
- [Timing Architecture](../09-timing/02-timing-architecture.md)

---

## Relationship to Control

Class C signals define timing structure.

Control determines behavior within that structure.

Major State (MS) is not a Class C signal.

Although MS interacts with timing, it is part of the control architecture.

Major State transitions are determined by control behavior rather than by the timing system itself.

Authoritative definitions are maintained in:

- [Control Model](../04-control/01-control-model.md)
- [Sequencing Control Signals](../04-control/20-control-output-definitions/03-sequencing-control-signals.md)

---

## Global Invariants

- Class C signals are CPU-local.
- Class C signals must not be placed on the backplane.
- Class C signals must not be used as external interfaces.
- Class C signals define timing structure rather than system behavior.
- Timing behavior is defined by Section 9.
- Execution behavior is defined by the control system.
- Major State is part of the control architecture and is not a Class C signal.

---

## Summary

Class C signals define the timing framework of the system.

This document classifies timing signals and their organization. Timing definitions, timing behavior, and timing architecture are defined in Section 9.