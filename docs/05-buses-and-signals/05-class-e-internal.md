# Class E - Local and Internal Signals

## Purpose

This document defines Class E signals and their organization within the system.

Class E signals are local to a CPU subsystem or module and are used to implement datapath, control, decode, and internal transport behavior.

This document defines:

- Class E signal characteristics
- Distribution scope
- Signal organization
- Internal transport mechanisms not defined elsewhere

This document does NOT define:

- signal semantics
- control behavior
- signal encodings
- datapath operation
- timing behavior

Authoritative signal definitions are maintained in Section 4.

---

## Overview

Class E signals are local implementation signals used within the CPU.

Class E signals:

- are local to a CPU subsystem or module
- are not externally visible
- are not present on the backplane
- are not used for communication between independent modules
- may be single-bit or multi-bit
- may represent control, decode, derived conditions, or internal transport

Class E signals implement CPU behavior but are not part of the system interface.

---

## Distribution Scope

Class E signals remain within module boundaries.

Class E signals:

- must not be placed on the backplane
- must not be exposed as system interfaces
- must not be relied upon by independent modules
- must remain local to the subsystem that implements them

Physical implementation is implementation-dependent.

---

## Signal Categories

### Internal Transport Signals

Internal transport signals move information between internal CPU elements.

Examples include:

- Internal Data Bus (IDB)

### Internal Control Signals

Internal control signals direct datapath behavior.

Examples include:

- register load enables
- operation selects
- source selects

Authoritative definitions are maintained in:

- [Microarchitectural Control Signals](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)

### Internal Decode Signals

Internal decode signals represent reduced instruction information used by control.

Examples include:

- instruction classification signals
- addressing-mode signals
- instruction-specific decode signals

Authoritative definitions are maintained in:

- [Instruction Register Derived Fields](../04-control/10-control-input-definitions/02-ir-derived-fields.md)

### Internal Derived Signals

Internal derived signals represent internally generated conditions used by control.

Examples include:

- primitive flags
- derived flags

Authoritative definitions are maintained in:

- [Primitive Flags](../04-control/10-control-input-definitions/01-flags.md)
- [Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md)

---

## Internal Data Bus (IDB)

### Definition

The Internal Data Bus (IDB) is the CPU-internal transport domain used for datapath data movement.

### Width

- 12 bits

### Purpose

IDB provides a shared transport mechanism for movement of data between CPU registers and functional units.

### Characteristics

IDB:

- exists entirely within the CPU
- is not externally visible
- is not a Class A system bus
- is not present on the backplane
- participates in domain-isolation rules
- is used exclusively for internal datapath transport

### Relationship to Control

IDB operation is controlled through microarchitectural control signals.

Behavior, control, and constraints are defined in:

- [Microarchitectural Control Signals](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)

This document defines IDB as an architectural transport mechanism only.

---

## Global Invariants

- Class E signals are local to a CPU subsystem or module.
- Class E signals must not be placed on the backplane.
- Class E signals must not be exposed as system interfaces.
- Class E signals must not be relied upon by independent modules.
- IDB is a CPU-internal transport mechanism.
- IDB is not externally visible.
- Signal behavior is defined by the authoritative documents in Section 4.

---

## Summary

Class E signals provide the internal implementation infrastructure of the CPU.

This document classifies local and internal signals and defines the Internal Data Bus (IDB). Signal behavior, control semantics, and operational definitions are maintained in Section 4.