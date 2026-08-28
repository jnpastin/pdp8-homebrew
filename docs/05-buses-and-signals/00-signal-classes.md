# Signal Classes

## 1. Purpose

This document defines the formal classification of all signals in the system.

Signal classification is used to:
- enforce separation of concerns
- define backplane vs local signal placement
- prevent leakage of internal implementation details
- establish ownership and electrical behavior expectations

These classifications are normative and must be followed by all subsystems.

---

## 2. Overview

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

## 3. Class A — System Buses

### 3.1 Definition

Multi-bit shared signal groups used for data and addressing across independent modules.

### 3.2 Characteristics

- Multi-drop (present on all slots)
- Require tri-state drivers
- Time-multiplexed ownership
- Electrically significant (fanout and loading)

### 3.3 Signals

- Address Bus: A[11:0]
- Data Bus: D[11:0]
- Memory Data Bus: MDB[11:0]
- Memory Field Bus: MFB[2:0]

### 3.4 Rules

- Must be present on all backplane slots
- Exactly one driver active at a time
- All other drivers must be tri-stated
- Ownership must be explicitly defined

### 3.5 Notes

The system defines two distinct data paths:
- DB bus for system and I/O transactions
- MDB bus for memory transactions

This separation is required to support DMA functionality.

---

## 4. Class B — Global Control Lines

### 4.1 Definition

System-wide control signals that coordinate behavior across modules.

### 4.2 Characteristics

- Single-bit control signals or multi-bit encoded control fields
- Visible to all modules
- May be single-driver or electrically shared, as defined by the applicable signal contract

### 4.3 Signals

#### 4.3.1 Memory Control

- /RD (Memory Read)
- /WR (Memory Write)

#### 4.3.2 Interrupts

- /INT_REQ (wired-OR of asserted requests)

#### 4.3.3 DMA

- /DMA_REQ
- /DMA_GRANT
- MS[2:0]

### 4.4 Rules

- Must be present on all backplane slots
- Signal ownership must be explicitly defined
- Must not expose CPU internal micro-operations

---

## 5. Class C — Timing Signals

### 5.1 Definition

Signals that define the internal timing model and sequencing of execution.

### 5.2 Characteristics

- High fanout
- Timing-critical
- Implementation-specific

### 5.3 Signals

CPU-local timing signals:

- MCLK
- TCLK
- TSTEP
- TSEQ

Architecturally distributed timing signals:

- TS
- TP

### 5.4 Rules

- MCLK, TCLK, TSTEP, and TSEQ remain within the timing-generation and timing-distribution subsystem unless another architectural interface explicitly requires them.
- TS and TP are architectural timing-distribution signals available to external I/O controllers.
- TS and TP may appear on the backplane.
- External controllers must use TS and TP only according to the [I/O Timing Contract](../07-io/03-io-timing.md).
- External controllers must not depend directly on TSTEP or TSEQ.
- Timing-signal loading, buffering, and electrical distribution belong to the physical implementation documentation.

---

## 6. Class D — External Interface Signals (Front Panel)

### 6.1 Definition

Signals connecting the system to the human operator interface.

### 6.2 Characteristics

- Asynchronous inputs
- Low frequency
- Require synchronization before use

### 6.3 Signals

#### 6.3.1 Control Inputs

- Start
- Continue
- Stop
- Single Instruction
- Single Step
- Deposit
- Examine
- Load Address

#### 6.3.2 Data Input

- SR[11:0]

#### 6.3.3 Status Outputs

- PC
- AC
- MA
- MB
- IF / DF
- Link
- MS indicators

### 6.4 Rules

- Must NOT be placed on the backplane
- Must terminate at a CPU-local panel interface
- Must be synchronized and debounced before use
- Must not directly drive datapath elements

---

## 7. Class E — Local / Internal Signals

### 7.1 Definition

Signals internal to a module used to implement datapath and control behavior.

### 7.2 Characteristics

- Module-local
- High fanout
- Timing-sensitive

### 7.3 Examples

- Register load enables (MA load, MB load, etc.)
- ALU operation selects
- Multiplexer selects
- IR field decode signals
- EA internal paths

### 7.4 Rules

- Must NOT appear on the backplane
- Must remain entirely within module boundaries
- Must not be relied upon by other modules

---

## 8. Global Rules

### 8.1 Rule 1 — Backplane Eligibility

A signal may be placed on the backplane only if:
- It is required by multiple independent modules
- It is not internal implementation detail
- It is not timing-critical internal state

### 8.2 Rule 2 — Ownership Definition

For all Class A and Class B signals:
- The driving entity must be defined
- Conditions for driving must be defined
- Default (idle) behavior must be defined

---

## 9. Summary

This classification establishes strict boundaries between:
- architectural interfaces
- control coordination
- internal implementation
- operator interaction

These boundaries are required to:
- maintain system modularity
- prevent unintended coupling between subsystems
- support reliable hardware implementation
