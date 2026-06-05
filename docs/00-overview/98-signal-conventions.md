# 98 Signal Conventions

## Purpose

This document defines global conventions for signal polarity, naming, and electrical behavior.

These rules apply to all signal classes and must be followed by all system modules.

---

## 1. Signal Polarity

### Active-High Signals

- Asserted when logic level is HIGH (1)
- Used for:
  - data buses
  - addresses

### Active-Low Signals

- Asserted when logic level is LOW (0)
- Used for:
  - single-driver control signals
  - multi-source request signals (wired-OR)

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

## 3. Signal Classification by Polarity

### Active-High

- AB, DB, MDB
- IOA[5:0]

### Active-Low

- RD, WR
- RESET
- HALT
- INT_ACK_IN / OUT
- DB_GRANT_IN / OUT
- DB_ADDR_EN, DB_DATA_EN
- DB_READ, DB_WRITE
- /INT_REQ
- /DB_REQ

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
- /DB_REQ

---

## 8. Daisy-Chain Signals

- propagated signal (not multi-driven)
- each device must:
  - pass through
  - or consume and block

Applies to:
- INT_ACK_IN / OUT
- DB_GRANT_IN / OUT

---

## 9. Global Invariants

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
