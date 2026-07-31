# 04 Class D - Front Panel Signals

## Purpose

This document defines Class D signals and their organization within the system.

Class D signals provide the interface between the system and the operator.

This document defines:

- Class D signal characteristics
- Distribution scope
- Signal organization
- Relationship to the front panel interface

This document does NOT define:

- front panel behavior
- switch semantics
- display behavior
- synchronization requirements
- panel implementation

Authoritative definitions are maintained in the control and front panel architecture documents.

---

## Overview

Class D signals connect the system to the operator interface.

Class D signals:

- are external to normal CPU execution
- originate from or terminate at the front panel
- may be inputs or outputs
- are CPU-local
- are not system buses
- are not backplane signals

---

## Distribution Scope

Class D signals terminate at a CPU-local front panel interface.

Class D signals:

- must not be placed on the backplane
- must not be used for communication between independent modules
- must not directly drive system behavior without control mediation

Physical implementation is implementation-dependent.

---

## Signal Categories

### Input Signals

Input signals provide operator control of the system.

Input categories:

- Command Inputs
- Mode Inputs
- Data Inputs

Authoritative definitions are maintained in:

- [External Inputs](../04-control/10-control-input-definitions/04-external-inputs.md)

### Output Signals

Output signals provide visibility into processor state.

Output category:

- Status Outputs

Status outputs may present processor state through front-panel indicators.

Examples include:

- Program Counter
- Accumulator
- Memory Address
- Memory Buffer
- Field Registers
- Link
- Major State

This document classifies status outputs only.

Displayed values and presentation behavior are defined elsewhere.

---

## Relationship to Control

Class D inputs influence system behavior through the control architecture.

Class D outputs observe system state but do not participate in control decisions.

Control definitions remain authoritative.

---

## Global Invariants

- Class D signals are CPU-local.
- Class D signals terminate at the front panel interface.
- Class D signals must not be placed on the backplane.
- Front panel inputs must not directly modify processor state.
- Front panel outputs expose system state but do not control system behavior.
- Front panel behavior is mediated through the control architecture.

---

## Summary

Class D signals define the operator interface of the system.

This document classifies front-panel inputs and outputs. Operational behavior and implementation details are defined elsewhere.