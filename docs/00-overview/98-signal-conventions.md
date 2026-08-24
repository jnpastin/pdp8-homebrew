# 98 Signal Conventions

## Purpose

This document defines global conventions for signal polarity, naming, and electrical behavior.

These rules apply to all signal classes and must be followed by all system modules.

---

## 1. Signal Polarity

Signal polarity is selected according to the electrical role of the interface rather than by applying one polarity to all control signals.

Active-low signals are used when:

- the receiving component provides an active-low control input
- the signal is a persistent shared request suitable for open-collector or open-drain aggregation
- a pull-up establishes the required inactive state during reset, power-up, or disconnection
 
Active-high signals are used for point-to-point qualified actions and authorization signals when active-low operation provides no required electrical or interface benefit.
 
Encoded buses and fields do not have an asserted polarity. Their individual bits represent binary values.
 
Behavioral text should use the terms asserted and deasserted unless the electrical level is specifically relevant.)

---

## 2. Naming Conventions

### Documentation

- Active-high signals:
  SIGNAL_NAME

- Active-low signals:
  /SIGNAL_NAME

### Schematics

- Active-low signals:
  S̅̅I̅̅G̅̅N̅̅A̅̅L̅̅_̅̅N̅̅A̅̅M̅̅E̅̅ (overbar)

---

## 3. Asserted and Deasserted Levels
 
For an active-low signal:
 
- asserted means electrical value 0
- deasserted means electrical value 1
 
For an active-high signal:
 
- asserted means electrical value 1
- deasserted means electrical value 0
 
Expressions that describe electrical values must reflect the defined polarity. Expressions that describe behavior should prefer asserted and deasserted terminology.

---

## 4. High-Impedance (High-Z) State

### Definition

A signal is in High-Z when:
- the output driver is electrically disconnected
- the device does not drive logic HIGH or LOW

### Properties

- affects output only
- devices can still read the bus

---

## 5. Bus Electrical Model

All Class A buses follow this model:

- exactly one active driver
- all other devices in High-Z
- weak pull-up defines default state

### Resulting Behavior

- driven HIGH -> logic 1
- driven LOW -> logic 0
- undriven -> defaults HIGH

---

## 6. Pull Resistors

- weak pull-up resistors are used
- ensure defined HIGH state when bus is undriven

### Rationale

- compatible with wired-OR signals
- avoids floating nodes
- aligns with TTL-style logic behavior

---

## 7. Wired-OR Signals

- devices may only pull LOW
- no device may actively drive HIGH
- pull-up resistor defines idle HIGH

Applies to:
- /INT_REQ
- /DMA_REQ

---

## 8. Global Invariants

- All signals must have explicit polarity
- No implicit active level is allowed
- Only one device may drive a bus at a time
- High-Z is required for all non-driving devices

---

## Summary

This document establishes consistent rules for:
- signal polarity
- naming
- electrical behavior

These conventions ensure:
- clarity in control logic
- prevention of electrical contention
- consistent interpretation across all system components
