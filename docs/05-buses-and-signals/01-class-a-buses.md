# 01 Class A – System Buses

## Purpose

This document defines all Class A signals: the system buses used for data and address transfer
between independent modules.

This document is limited to:
- signal definitions
- structural properties
- invariants

It does NOT define:
- ownership
- arbitration
- electrical drive specifics beyond baseline assumptions


This document follows the conventions defined in:
../00-overview/98-signal-conventions.md

---

## Overview

Class A signals are multi-bit buses that:
- are present on all backplane slots
- support shared communication between modules
- require strict ownership and tri-state discipline

The system defines three buses:

- Address Bus (AB)
- System Data Bus (DB)
- Memory Data Bus (MDB)

---

## Bit Ordering and Conventions

- Bit 0 = Least Significant Bit (LSB)
- Bit 11 = Most Significant Bit (MSB)
- All buses are 12 bits wide
- All signals are active-high

---

## Bus Definitions

### Address Bus (AB)

#### Logical Definition

AB = A[11:0]

#### Physical Signals

A0
A1
A2
A3
A4
A5
A6
A7
A8
A9
A10
A11

#### Function

Carries memory addresses for:
- instruction fetch (PC-derived)
- operand access (EA-derived)
- future data break operations

---

### System Data Bus (DB)

#### Logical Definition

DB = D[11:0]

#### Physical Signals

D0
D1
D2
D3
D4
D5
D6
D7
D8
D9
D10
D11

#### Function

Carries data for:
- I/O operations
- front panel interactions (via CPU)
- general system data transfers

---

### Memory Data Bus (MDB)

#### Logical Definition

MDB = MDB[11:0]

#### Physical Signals

MDB0
MDB1
MDB2
MDB3
MDB4
MDB5
MDB6
MDB7
MDB8
MDB9
MDB10
MDB11

#### Function

Carries data for:
- memory read/write operations
- future data break (DMA) transfers

MDB is logically independent from DB

---

## Structural Invariants

### Bus Independence

- AB, DB, and MDB are independent buses
- No implicit coupling exists between buses
- Any transfer between buses must occur via datapath elements

---

### Bus Completeness

- All bits of a bus must be driven by a single source
- Partial bus driving is not permitted

---

### Default State

- All bus drivers must support tri-state operation
- Default state for all buses is high-impedance (Z)

---

### Timing Constraint

- Bus values must be stable before the timing pulse (TP) that latches a receiving register
- Bus timing must align with the TS/TP timing model

---

### Width Constraint

- All buses are fixed at 12 bits
- No operation may assume a different width

---

## Exclusions

The following are NOT Class A signals:

- IOA (I/O Address Bus)
- RD / WR control lines
- interrupt signals
- timing signals (TS/TP/CLK)
- internal CPU control signals

These belong to other signal classes

---

## Summary

Class A buses provide the fundamental data and address transport mechanisms for the system.

They are:
- globally visible
- strictly controlled
- timing-constrained
- foundational to all module interaction

All subsequent control and ownership definitions rely on these buses being well-defined
and strictly adhered to.
