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

- are timing-critical
- establish temporal execution structure
- may be CPU-local or architecturally distributed

Class C signals do not directly define processor behavior.

---

## Distribution Scope
Class C signals have two distribution scopes.

### CPU-Local Timing Signals

The following signals remain within the CPU timing-generation and timing-distribution subsystem:

- MCLK
- TCLK
- TSTEP
- TSEQ

These signals:
- must not be placed on the backplane
- must not be relied upon by independent modules
- must not be exposed as external interfaces unless another architectural interface explicitly requires them

Physical distribution of Class C signals is implementation-dependent.

### Architecturally Distributed Timing Signals

The following signals are distributed to external I/O controllers:

- TS
- TP

These signals:
- are available through the external I/O interface
- may be placed on the backplane
- may be relied upon by external controllers only as defined by the [I/O Timing Contract](../07-io/03-io-timing.md)

Physical buffering, loading, and distribution are implementation-dependent.
---

## Signal Categories

Authoritative definitions are maintained in:

- [Timing Terminology](../09-timing/01-terminology.md)
- [Timing Architecture](../09-timing/02-timing-architecture.md)

### Clock Signals

Clock signals provide the timing source used by the timing system.

Signals:

- MCLK
- TCLK

### Timing Sequence Signals

Timing sequence signals define progression through the timing system.

Signals:

- TSTEP
- TSEQ

### Timing Execution Signals

Timing execution signals define execution windows and execution events.

Signals:

- TS
- TP

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

- MCLK, TCLK, TSTEP, and TSEQ are CPU-local unless another architectural interface explicitly requires them.
- MCLK, TCLK, TSTEP, and TSEQ must not be relied upon by independent modules.
- TS and TP are architecturally distributed timing signals.
- TS and TP are available to external I/O controllers.
- External controllers may use TS and TP only according to the [I/O Timing Contract](../07-io/03-io-timing.md).
- Class C signals define timing structure rather than system behavior.
- Timing behavior is defined by Section 9.
- Execution behavior is defined by the control system.
- Major State is part of the control architecture and is not a Class C signal.
 
### Summary
 
Class C signals define the timing framework of the system. MCLK, TCLK, TSTEP, and TSEQ remain CPU-local, while TS and TP are architecturally distributed to external I/O controllers. Timing definitions, behavior, and architecture are defined in Section 9 and the applicable external interface contracts.