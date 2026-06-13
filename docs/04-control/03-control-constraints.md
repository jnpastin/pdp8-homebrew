## Control Constraints Model

### Purpose

Defines the formal constraints governing all control behavior in the system.

This document is normative and establishes:
- how control signals are defined
- what inputs control may depend on
- how control interacts with timing and state
- how control store addressing is constrained

All control-related documents must conform to these rules.

Related:
- [Control Model](../04-control/01-control-store.md)

---

## 1. Control Signal Definition

### Requirement

Every control signal must have exactly one authoritative definition.

Each signal definition must include:
- Name
- Polarity
- Domain (architectural or microarchitectural)
- Description
- Preconditions (if applicable)
- Constraints (if applicable)

### Uniqueness Constraint

- A signal must not be defined in multiple locations
- All references must link to the authoritative definition

---

## 2. Control Signal Domains

Control signals are partitioned into two domains.

### 2.1 Architectural Control Signals

Define system-wide control behavior.

Examples:
- RD
- WR
- IOA\[5:0\]

Properties:
- Visible across CPU, memory, and I/O subsystems
- Coordinate inter-module behavior
- Must not expose internal datapath implementation

---

### 2.2 Microarchitectural Control Signals

Define internal CPU datapath behavior.

Examples:
- MA_load
- MB_load
- IR_load
- AB_src
- MDB_src
- PC_inc

Properties:
- Local to CPU
- Not visible to external modules
- Implement micro-operations

---

## 3. Control Function Definition

Control is defined as:

CONTROL = f(MS, TS, IR, FLAGS, EXT)

Where:
- MS: Major State
- TS: Time State
- IR: Instruction Register (reduced fields only)
- FLAGS: Derived from architectural register state
- EXT: Signals external to the CPU

### Determinism Requirement

For every combination of inputs:

(MS, TS, IR, FLAGS, EXT)

there must be exactly one control output.

No undefined or implicit behavior is permitted.

---

## 4. Control Output Definition

Control is implemented as a ROM-based control store.

### Control Word Requirement

The ROM output must be the complete control word.

This includes:
- all architectural control signals
- all microarchitectural control signals
- MS_next (next major state)

No additional decoding or interpretation is permitted downstream of the control store.

### Completeness Requirement

For every (MS, TS):

- All control outputs must be explicitly defined
- No signal may be left unspecified
- No implicit defaults are allowed

---

## 5. Timing Constraints

### 5.1 Evaluation Model

During TS:
- Control signals are evaluated
- Datapath configuration is established

At TP:
- Register state changes occur
- All updates are committed simultaneously

### 5.2 State Change Rule

Control signals must not directly modify state.

All state changes must occur:
- only at TP
- only through register updates

---

## 6. Control Signal Semantics

### 6.1 Level-Based Operation

All control signals are level-based.

Properties:
- Signals remain stable for the duration of a TS
- No edge-based or pulse-based behavior is encoded in control
- TP provides the only event boundary in the system

### 6.2 No Implicit Timing

Control must not encode:
- rising edge behavior
- falling edge behavior
- pulse width assumptions

All timing behavior is defined by:
- TS (evaluation window)
- TP (commit event)

---

## 7. Source Constraints

Control decisions may depend only on:

- Architectural registers
- Control-visible registers (IR, MS)
- FLAGS derived from registers
- EXT inputs

Control must NOT depend on:
- transient datapath signals
- control outputs
- intermediate combinational values

---

## 8. External Inputs (EXT)

### Definition

EXT represents signals external to the CPU.

Examples:
- /INT_REQ
- /DMA_REQ

### Constraints

- EXT must be stable prior to TP
- EXT must not include:
  - datapath signals
  - control signals
  - internal CPU state

EXT influences control selection only and must not directly modify processor state.

---

## 9. Control Store Address Constraints

Control is implemented as a ROM lookup.

The control store address is derived from a reduced encoding of:

(MS, TS, IR, FLAGS, EXT)

### Inclusion Rule

A signal may be included in the control store address only if:
- it affects control behavior

### Exclusion Rule

Signals must not be included if:
- they do not influence control outputs in a given context

Unused combinations must be handled by:
- duplicating ROM entries

### Encoding Requirement

The control address must be constructed from:
- reduced IR fields (not full IR)
- reduced FLAGS (only those required)
- reduced EXT inputs

The mapping must preserve determinism:
- each execution state maps to exactly one control word

See:
- [Control Store](../04-control/02-control-store.md)

---

## 10. Bus Interaction Constraints

Control defines when operations occur but does not define bus semantics.

Control MAY define:
- when RD is asserted
- when WR is asserted
- when a transfer operation is active

Control MUST NOT define:
- bus ownership
- electrical drive behavior
- bus validity rules

External data sources may originate from multiple system buses.

In this system:
- MDB_input corresponds to the memory data bus (MDB)
- DB_input corresponds to the system data bus (DB)

Control selects between these as inputs but does not define their behavior.

These are defined in:
- [Buses and Signals](../05-buses-and-signals/README.md)
- [Bus Semantics](../05-buses-and-signals/03-bus-semantics.md)
- [Ownership Matrix](../05-buses-and-signals/04-ownership-matrix.md)

---

## 11. Memory Interaction Constraints

Control may initiate memory operations via RD and WR.

Control MUST NOT define:
- memory internal behavior
- data propagation within memory
- memory timing implementation

Defined in:
- [Memory](../06-memory/README.md)

---

## 12. I/O Interaction Constraints

Control may:
- drive IOA
- define signal values during TS of EXECUTE for IOT instructions
- control data transfer direction via system buses

Control MUST NOT define:
- device behavior
- device internal state
- device-specific timing

I/O data is transferred via the system data bus (DB), distinct from the memory data bus (MDB).

Defined in:
- [I/O](../07-io/README.md)

---

## 13. Relationship to Micro-Operations

### Separation Rule

- Micro-operations define state transformations
- Control signals implement those transformations

Control MUST NOT:
- redefine micro-operations
- restate their semantics
- introduce symbolic instruction behavior

Defined in:
- [Micro-Operations](../03-microarchitecture/02-micro-operations.md)

---

## 14. Preconditions and Validity

Control signals may define required state.

Examples:
- WR requires MB to contain valid data
- RD requires MA to contain a valid address

### Constraint

Control may define required conditions but must not define:
- how the data was produced
- how buses carry values

---

## 15. Consumption Rule

No component may consume bus values directly.

All consumption must occur via registers.

Control must ensure:
- correct register loading
- correct sequencing of data availability

---

## 16. Next-State Control

Control is responsible for determining MS_next.

### Constraints

- MS_next must be determined during TS4
- MS updates occur only at TP4
- MS must not be modified by datapath operations

---

## 17. Control Invariants

The following properties must always hold during correct operation:

- For a given (MS, TS, IR, FLAGS, EXT), exactly one control word is active
- Control outputs remain stable for the duration of a TS
- No state changes occur outside TP
- The control store output fully defines system behavior at each step
- MS transitions occur only at TP4

---

## 18. Prohibited Behavior

The following are disallowed:

- implicit control behavior
- undefined signal states
- dependence on transient datapath signals
- duplication of signal definitions across documents
- encoding of timing edges in control signals
- embedding bus semantics in control
- embedding micro-operation definitions in control

---

## Summary

Control is a deterministic, level-based mapping from machine state to a complete control word.

It is responsible for:
- configuring datapath behavior
- initiating memory and I/O operations
- determining execution flow

It is not responsible for:
- defining data movement semantics
- defining device behavior
- defining micro-operation meaning

All control behavior must be:
- explicit
- deterministic
- complete
- consistent with system-wide abstractions