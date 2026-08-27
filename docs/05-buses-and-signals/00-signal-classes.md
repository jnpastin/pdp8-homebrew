# 00 Signal Classes

## Purpose

This document defines the formal classification of all signals in the system.

Signal classification is used to:
- enforce separation of concerns
- define backplane vs local signal placement
- prevent leakage of internal implementation details
- establish ownership and electrical behavior expectations

These classifications are normative and must be followed by all subsystems.

---

## Overview

All signals are classified into one of five categories:

- Class A: System Buses
- Class B: Global Control Lines
- Class C: Timing Signals
- Class D: External Interface Signals (Front Panel)
- Class E: Local / Internal Signals

Each class defines:
- visibility
- placement
- electrical behavior
- usage constraints

---

## Class A — System Buses

### Definition

Multi-bit shared signal groups used for data and addressing across independent modules.

### Characteristics

- Multi-drop (present on all slots)
- Require tri-state drivers
- Time-multiplexed ownership
- Electrically significant (fanout and loading)

### Signals

- Address Bus: A[11:0]
- Data Bus: D[11:0]
- Memory Data Bus: MDB[11:0]
- Memory Field Bus: MFB[2:0]

### Rules

- Must be present on all backplane slots
- Exactly one driver active at a time
- All other drivers must be tri-stated
- Ownership must be explicitly defined

### Notes

The system defines two distinct data paths:
- DB bus for system and I/O transactions
- MDB bus for memory transactions

This separation is required to support DMA functionality.

---

## Class B — Global Control Lines

### Definition

System-wide control signals that coordinate behavior across modules.

### Characteristics

- Single-bit control signals or multi-bit encoded control fields
- Visible to all modules
- May be single-driver or electrically shared, as defined by the applicable signal contract

### Signals

#### Memory Control

- /RD (Memory Read)
- /WR (Memory Write)

#### Interrupts

- /INT_REQ (wired-OR of asserted requests)

#### DMA

- /DMA_REQ
- /DMA_GRANT
- MS[2:0]

### Rules

- Must be present on all backplane slots
- Signal ownership must be explicitly defined
- Must not expose CPU internal micro-operations

---

## Class C — Timing Signals

### Definition

Signals that define the internal timing model and sequencing of execution.

### Characteristics

- High fanout
- Timing-critical
- Implementation-specific

### Signals

CPU-local timing signals:

- MCLK
- TCLK
- TSTEP
- TSEQ

Architecturally distributed timing signals:

- TS
- TP

### Rules

#### Rules

- MCLK, TCLK, TSTEP, and TSEQ remain within the timing-generation and timing-distribution subsystem unless another architectural interface explicitly requires them.
- TS and TP are architectural timing-distribution signals available to external I/O controllers.
- TS and TP may appear on the backplane.
- External controllers must use TS and TP only according to the [I/O Timing Contract](../07-io/03-io-timing.md).
- External controllers must not depend directly on TSTEP or TSEQ.
- Timing-signal loading, buffering, and electrical distribution belong to the physical implementation documentation.

---

## Class D — External Interface Signals (Front Panel)

### Definition

Signals connecting the system to the human operator interface.

### Characteristics

- Asynchronous inputs
- Low frequency
- Require synchronization before use

### Signals

#### Control Inputs

- Start
- Continue
- Stop
- Single Instruction
- Single Step
- Deposit
- Examine
- Load Address

#### Data Input

- SR[11:0]

#### Status Outputs

- PC
- AC
- MA
- MB
- IF / DF
- Link
- MS indicators

### Rules

- Must NOT be placed on the backplane
- Must terminate at a CPU-local panel interface
- Must be synchronized and debounced before use
- Must not directly drive datapath elements

---

## Class E — Local / Internal Signals

### Definition

Signals internal to a module used to implement datapath and control behavior.

### Characteristics

- Module-local
- High fanout
- Timing-sensitive

### Examples

- Register load enables (MA load, MB load, etc.)
- ALU operation selects
- Multiplexer selects
- IR field decode signals
- EA internal paths

### Rules

- Must NOT appear on the backplane
- Must remain entirely within module boundaries
- Must not be relied upon by other modules

---

## Global Rules

### Rule 1 — Backplane Eligibility

A signal may be placed on the backplane only if:
- It is required by multiple independent modules
- It is not internal implementation detail
- It is not timing-critical internal state

### Rule 2 — Ownership Definition

For all Class A and Class B signals:
- The driving entity must be defined
- Conditions for driving must be defined
- Default (idle) behavior must be defined

---

## Summary

This classification establishes strict boundaries between:
- architectural interfaces
- control coordination
- internal implementation
- operator interaction

These boundaries are required to:
- maintain system modularity
- prevent unintended coupling between subsystems
- support reliable hardware implementation
