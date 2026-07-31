# 02 Class B - Global Control Signals

## Purpose

This document defines Class B signals and their organization within the system.

Class B signals are control signals used by the CPU control system and by CPU interactions with external subsystems.

This document defines:

- Class B signal characteristics
- Distribution scope
- Organizational structure

This document does NOT define:

- signal semantics
- signal encodings
- signal behavior
- control-word structure
- control-flow behavior
- timing behavior

Authoritative signal classifications, constraints, and definitions are maintained in Section 4.

---

## Overview

Class B signals communicate control information.

Class B signals:

- may be single-bit or multi-bit
- may be inputs or outputs
- may be CPU-local or system-distributed
- do not transport general-purpose address values
- do not transport general-purpose data values

Unlike Class A buses, Class B signals represent control information rather than communication paths.

---

## Distribution Scope

### CPU-Local

CPU-local signals exist entirely within the CPU implementation.

These signals are not visible outside the CPU boundary.

CPU-local classifications are defined in:

- [Input - Flags](../04-control/10-control-input-definitions/01-flags.md)
- [Input - IR Derived Fields](../04-control/10-control-input-definitions/02-ir-derived-fields.md)
- [Input - Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md)
- [Output - Microarchitecture](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Output - Sequencing](../04-control/20-control-output-definitions/03-sequencing-control-signals.md)

### System-Distributed

System-distributed signals are visible outside the CPU boundary.

These signals coordinate CPU interaction with external memory, I/O devices, DMA hardware, and front-panel controls.

System-distributed classifications are defined in:

- [Input - External](../04-control/10-control-input-definitions/04-external-inputs.md)
- [Output - Architectural](../04-control/20-control-output-definitions/02-architectural-control-signals.md)

---

## Input Organization

Control inputs are organized into four domains:

- Primitive Flags
- IR-Derived Signals
- Derived Flags
- External Inputs

---

## Output Organization

Control outputs are organized into three domains:

- Microarchitectural Control Signals
- Architectural Control Signals
- Sequencing Control Signals


---

## Width Classification

### Single-Bit Signals

Single-bit Class B signals represent a binary control condition.

Single-bit signals may be either CPU-local or system-distributed.

### Multi-Bit Signals

Multi-bit Class B signals represent encoded control information.

Multi-bit signals may be either CPU-local or system-distributed.

---

### I/O Address Field (IOA)

#### Definition

The I/O Address Field (IOA) is a CPU-generated control field used to identify the target I/O device during an I/O operation.

#### Width

- 6 bits

#### Characteristics

IOA:

- is a Class B control signal
- is system-distributed
- is multi-bit
- is driven exclusively by the CPU
- is not a shared transport bus
- is not a transport domain

#### Purpose

IOA carries device-selection information used by I/O operations.

The interpretation of IOA values is defined by the addressed device and the active I/O operation.

#### Relationship to Control

IOA generation and usage are defined by the control architecture.

This document defines IOA as a classified architectural signal only.

Authoritative definitions are maintained in:

- [Architectural Control Signals](../04-control/20-control-output-definitions/02-architectural-control-signals.md)

---

## Relationship to Other Signal Classes

Class A signals provide address and data transport.

Class B signals provide control information.

---

## Summary

Class B signals comprise the complete control-signal infrastructure of the system.

This document defines the classification and organization of those signals. Signal definitions and behavior are defined in Section 4.
