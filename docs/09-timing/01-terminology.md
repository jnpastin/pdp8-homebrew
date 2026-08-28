# Timing Terminology

## 1. Purpose

This document defines all timing-related terminology used throughout the system.

All other timing documents must use these terms consistently.

---

## 2. Clocks

### 2.1 Master Clock (MCLK)

Primary system clock source.

- May be variable frequency
- May be externally provided or internally generated

---

### 2.2 Timing Clock (TCLK)

Clock that drives the CPU timing sequence.

- Derived from MCLK
- All timing progression occurs on TCLK

Note: Multiple TCLK generation options are planned (MCLK source selection, counter division ratios). The specific options and configuration are not yet defined.

---

### 2.3 Clock Edge

All timing behavior is defined on:

TCLK rising edge (CLK↑)

---

## 3. Timing Sequence

### 3.1 Timing Step (TSTEP)

A single position in the timing sequence.

Properties:

- One-hot encoded.
- Exactly one TSTEP is active at a time.
- TSTEP normally advances on each TCLK rising edge.
- During an external IOT, `/IO_WAIT` may hold an eligible non-TP setup TSTEP.
- MCLK and TCLK continue while TSTEP is held.
- `/IO_WAIT` is ignored when the current TSTEP is a TP position.
- TSTEP transition logic evaluates the pre-edge TSTEP value.
- At most one TSTEP increment occurs on each TCLK rising edge.

---

### 3.2 Timing Sequence (TSEQ)

The ordered progression of timing steps:

TSTEP0 → TSTEP1 → … → TSTEPN → repeat

TSEQ is the fundamental timebase of the system.

Note: TSEQ wrap and reset behavior (end-of-sequence handling, power-on state) is not yet defined.

---

## 4. Timing Pulses (TP)

### 4.1 Definition

A Timing Pulse corresponds to a specific timing step:

TPn = (TSTEP == n)

---

### 4.2 Properties

- Active-high.
- Active for exactly one TCLK cycle.
- Mutually exclusive.
- Represents a discrete execution event.
- Cannot be extended by `/IO_WAIT`.
- Cannot be suppressed by `/IO_WAIT`.
- Cannot be repeated by `/IO_WAIT`.

---

### 4.3 Role

TP defines when actions occur.

All state changes are triggered by TP.

---

## 5. Timing States (TS)

### 5.1 Definition

Timing States represent execution phases:

TS1, TS2, TS3, TS4

---

### 5.2 Implementation

Each TS is defined as a group of timing steps:

TSn = decode(TSTEP range)

TS ranges are based on DEC timing reference diagrams. See [cpu-timing-overview](../../diagrams/timing/cpu-timing/export/cpu-timing-overview.png) for the current TSTEP assignments. TS2 is intentionally the long cycle to accommodate memory access timing, following DEC's slow-cycle design. Short-cycle support is planned for a future implementation phase.

---

### 5.3 Properties

- Active-high signals
- Exactly one TS asserted at a time
- Span multiple TCLK cycles
- Derived from TSTEP

---

### 5.4 Role

TS defines when operations are allowed.

TS does not trigger state changes.

---

## 6. Major States (MS)

### 6.1 Definition

Major States represent instruction-level control flow:

FETCH  
DEFER  
EXECUTE  
INTERRUPT
DMA  

---

### 6.2 Role

MS defines what operation is being performed.

MS is independent of timing structure.

---

## 7. Summary

| Term  | Meaning | Polarity |
|-------|---------|----------|
| MCLK  | System clock | — |
| TCLK  | CPU timing clock | — |
| TSTEP | Single timing position | — |
| TSEQ  | Full timing sequence | — |
| TP    | Event trigger | Active-high |
| TS    | Execution phase window | Active-high |
| MS    | Instruction control state | — |
