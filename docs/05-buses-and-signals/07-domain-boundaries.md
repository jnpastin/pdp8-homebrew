# 07 Domain Boundaries

## Purpose

This document defines the transport domains used throughout the system and the boundaries that separate them.

This document defines:

- transport domains
- domain membership
- domain isolation principles
- domain crossing principles

This document does NOT define:

- bus semantics
- signal ownership
- operation behavior
- crossing mechanisms
- control behavior

These are defined in:

- [Bus Semantics](./06-bus-semantics.md)
- [Control Model](../04-control/01-control-model.md)

and related documents.

---

## Domain Model

A transport domain is a collection of signals that participate in a common data or address transport mechanism.

Each transport signal belongs to exactly one domain.

Domains are independent architectural constructs.

No domain is implicitly connected to any other domain.

---

## Domain Definitions

### Address Domain (AB)

The Address Domain consists of signals used to transport addresses within the system.

This domain is represented by:

- AB

Defined in:

- [Class A - Buses](./01-class-a-buses.md)

### Memory Data Domain (MDB)

The Memory Data Domain consists of signals used to transport memory data.

This domain is represented by:

- MDB

Defined in:

- [Class A - Buses](./01-class-a-buses.md)

### I/O Data Domain (DB)

The I/O Data Domain consists of signals used to transport I/O data.

This domain is represented by:

- DB

Defined in:

- [Class A - Buses](./01-class-a-buses.md)

### Internal Data Domain (IDB)

The Internal Data Domain consists of signals used for CPU-internal data transport.

This domain is represented by:

- IDB

Defined in:

- [Class E - Local & Internal Signals](./05-class-e-internal.md)

---

## Domain Isolation

Domains are independent.

Membership in one domain does not imply membership in another domain.

Signals belonging to one domain shall not be interpreted as belonging to another domain.

Operations occurring within one domain shall not implicitly affect another domain.

No domain may assume visibility into another domain unless explicitly defined by a system operation.

---

## Domain Crossings

Domain crossings must be explicit.

No domain may communicate with another domain except through mechanisms defined by the active operation.

Domain crossings are determined by the control architecture.

This document does not define crossing mechanisms.

Authoritative definitions are maintained in Section 4.

---

## Special Role of IDB

IDB differs from the other transport domains.

AB, MDB, and DB are externally visible architectural transport domains.

IDB exists entirely within the CPU and is used exclusively for internal datapath transport.

IDB is not externally accessible.

Despite this distinction, IDB participates in the same domain-isolation and domain-crossing principles as all other transport domains.

---

## Global Invariants

- Every transport signal belongs to exactly one domain.
- Domains are independent architectural constructs.
- Domain membership shall not be inferred.
- Domain crossings must be explicit.
- Domain crossings are determined by the control architecture.
- No implicit domain coupling is permitted.
- IDB is CPU-local.
- IDB is not externally visible.

---

## Summary

The system is partitioned into independent transport domains.

This document defines those domains and the principles that govern their separation. Domain crossings are explicit, control-defined operations and do not occur implicitly.