# 00 Abbreviation Dictionary

## Purpose

This document defines a global dictionary for all abbreviations used throughout the system design.

It serves as the single source of truth for:
- register names
- bus names
- control signals
- timing signals
- architectural and microarchitectural terms

All documents must reference these abbreviations to prevent ambiguity or collision.

---

## Naming Rules

- Abbreviations should be 2–4 characters where possible
- Must be unique across all categories
- Must be stable once defined
- Must not be reused with different meanings

---

## Buses (Class A)

```
AB   = Address Bus (A[11:0])
DB   = System Data Bus (D[11:0])
MDB  = Memory Data Bus (MDB[11:0])
```

---

## Registers

```
PC   = Program Counter
AC   = Accumulator
L    = Link
MQ   = Multiplier Quotient
IF   = Instruction Field
DF   = Data Field
SR   = Switch Register
IE   = Interrupt Enable
IR   = Instruction Register
EA   = Effective Address
MA   = Memory Address
MB   = Memory Buffer
MS   = Major State
INT_REQ = Interrupt Request
```

---

## Timing Signals (Class C)

```
CLK  = System Clock
TS1  = Timing State 1
TS2  = Timing State 2
TS3  = Timing State 3
TS4  = Timing State 4
TP1  = Timing Pulse 1
TP2  = Timing Pulse 2
TP3  = Timing Pulse 3
TP4  = Timing Pulse 4
```

---

## Global Control Signals (Class B)

```
RD      = Memory Read
WR      = Memory Write
RESET   = System Reset
INT_REQ = Interrupt Request (wired-OR)
INT_ACK = Interrupt Acknowledge
```

### Data Break (Reserved)

```
DB_REQ     = Data Break Request
DB_GRANT   = Data Break Grant
DB_ADDR_EN = Data Break Address Enable
DB_DATA_EN = Data Break Data Enable
DB_READ    = Data Break Read
DB_WRITE   = Data Break Write
```

---

## I/O Signals

```
IOA[5:0] = I/O Device Address Bus
```

---

## Front Panel Signals (Class D)

```
DS   = Deposit Switch
ES   = Examine Switch
GS   = Go / Continue Switch
LAS  = Load Address Switch
SIS  = Single Instruction Switch
SSC  = Single Cycle Switch
SS   = Stop Switch
```

---

## Conventions

- Bracket notation indicates bus width (e.g., AB[11:0])
- Uppercase denotes signal-level identifiers
- Names reflect function, not implementation

---

## Constraints

- New abbreviations must be added here before use
- Existing abbreviations must not be redefined
- Collisions must be resolved by renaming before implementation

---

## Summary

This dictionary ensures consistency across:
- architecture definitions
- control logic
- hardware implementation
- documentation

It is authoritative and must be kept synchronized with all system specifications.
