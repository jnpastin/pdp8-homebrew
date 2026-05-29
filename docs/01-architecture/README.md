## 01 Architecture
 
Status: not started

### Purpose
 
Defines the programmer-visible machine model — what software observes.

Includes:
- register set
- memory model
- addressing behavior

Does not describe execution (see ../03-microarchitecture/README.md).

---

## Scope

Includes:
- registers (PC, AC, MQ, Link, SR)
- memory organization
- field registers (IF, DF)

Excludes:
- instruction semantics (see ../02-isa/README.md)
- execution behavior (see ../03-microarchitecture/README.md)
- control signals (see ../04-control/README.md)

---

## Dependencies

- Informed by: ../00-overview/README.md
- Constrains:
  - ../02-isa/README.md
  - ../03-microarchitecture/README.md

---

## Notes
 
This section will be written once the register model and memory architecture are stable.
Current working state is in `/notes`.

