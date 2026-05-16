# Specs

## Purpose
Machine-readable specifications used to support tooling and validation.

---

## Examples
- Instruction encoding tables
- Control signal definitions
- Timing state definitions

---

## Formats
- YAML
- JSON
- CSV

---

## Relationship to `/sim`
`/sim` uses these specifications as the expected-behavior oracle. When a specification changes, corresponding simulations should be updated and re-validated.

---

## Notes
This directory supplements `/docs` but does not replace it
