# Timing

## 1. Purpose
Defines when operations occur.

---

## 2. Core Rules
- TS defines setup windows
- TP defines state transitions
- All state changes occur at TP: captured at its leading edge, visible as it ends ([Timing Architecture §7.6](./02-timing-architecture.md#76-rule-6--two-ranks))

---

## 3. Scope
- Clocking
- Event ordering

Excludes:
- Behavior ([Control](../04-control/README.md))

---

## 4. Related Documents
- [01-terminology.md](01-terminology.md)
- [02-timing-architecture.md](02-timing-architecture.md)
- [03-major-state-timing.md](03-major-state-timing.md)
