# 01 Architecture

Status: not started

## Purpose
This section defines the programmer-visible machine model — what software observes when running on the system.

It covers the register set, memory model, addressing behavior, and the computational state visible at the ISA boundary. It does not describe how instructions are executed internally (that is microarchitecture, in section 03).

---

## Contents

To be populated. Planned topics:

- Register set (PC, AC, MQ, Link, SR)
- Memory organization (fields, pages, addressing)
- Extended memory registers (IF, DF)
- Programmer-visible state summary

---

## Dependencies

- Informed by: `00-overview/system-overview.md`
- Constrains: `02-isa`, `03-microarchitecture`

---

## Notes

This section will be written once the register model and memory architecture are stable. Current working state is captured in `docs/00-overview/AGENT_HANDOFF.md` (now in `notes/`).
