# Timing Terminology

## Purpose

This document defines all timing-related terminology used throughout the system.

All other timing documents must use these terms consistently.

---

# 1) Clocks

## 1.1 Master Clock (MCLK)

Primary system clock source.

- May be variable frequency
- May be externally provided or internally generated

---

## 1.2 Timing Clock (TCLK)

Clock that drives the CPU timing sequence.

- Derived from MCLK
- All timing progression occurs on TCLK

---

## 1.3 Clock Edge

All timing behavior is defined on:

TCLK rising edge (CLK↑)

---

# 2) Timing Sequence

## 2.1 Timing Step (TSTEP)

A single position in the timing sequence.

Properties:
- One-hot encoded
- Exactly one active at a time
- Advances on each TCLK rising edge

---

## 2.2 Timing Sequence (TSEQ)

The ordered progression of timing steps:

TSTEP0 → TSTEP1 → … → TSTEPN → repeat

TSEQ is the fundamental timebase of the system.

---

# 3) Timing Pulses (TP)

## 3.1 Definition

A Timing Pulse corresponds to a specific timing step:

TPn = (TSTEP == n)

---

## 3.2 Properties

- Active for exactly one TCLK cycle
- Mutually exclusive
- Represents a discrete execution event

---

## 3.3 Role

TP defines when actions occur.

All state changes are triggered by TP.

---

# 4) Time States (TS)

## 4.1 Definition

Time States represent execution phases:

TS1, TS2, TS3, TS4

---

## 4.2 Implementation

Each TS is defined as a group of timing steps:

TSn = decode(TSTEP range)

---

## 4.3 Properties

- One active at a time (one-cold)
- Span multiple TCLK cycles
- Derived from TSTEP

---

## 4.4 Role

TS defines when operations are allowed.

TS does not trigger state changes.

---

# 5) Major States (MS)

## 5.1 Definition

Major States represent instruction-level control flow:

FETCH  
DEFER  
EXECUTE  
INTERRUPT  

---

## 5.2 Role

MS defines what operation is being performed.

MS is independent of timing structure.

---

# 6) Summary

| Term  | Meaning |
|------|--------|
| MCLK | System clock |
| TCLK | CPU timing clock |
| TSTEP | Single timing position |
| TSEQ | Full timing sequence |
| TP | Event trigger |
| TS | Execution phase |
| MS | Instruction control state |
