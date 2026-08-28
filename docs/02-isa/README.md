# Instruction Set Architecture

## 1. Purpose
Defines instruction semantics independent of execution timing or implementation.

---

## 2. Scope
Includes:
- Instruction classes (MRI, OPR, IOT)
- Operand and result behavior
- Skip logic behavior
- Addressing model (zero page, current page, indirection, fields)
- Effective address (EA) generation

Excludes:
- Timing ([09-timing/README.md](../09-timing/README.md))
- Microarchitectural execution ([03-microarchitecture/README.md](../03-microarchitecture/README.md))
- Control implementation ([04-control/README.md](../04-control/README.md))

---

## 3. Model Summary
- Instructions are defined by IR bitfields.
- Behavior is determined without decoding into symbolic instructions.
- Skip behavior sets a pending control condition that affects PC update.
- Addressing model and effective address generation define how operands are located and are used by all MRI instruction semantics.

---

General information about the structure of the instructions and detailed information about MRI and IOT instructions can be found at:

[00-encoding-model.md](./00-encoding-model.md)

Detailed information about the OPR instructions can be found at:
- [01-group-1.md](./01-group-1.md)
- [02-group-2.md](./02-group-2.md)
- [03-group-3.md](./03-group-3.md)

The effective address is represented as (EA_fld, EA_ADDR).
EA_ADDR is a 12-bit value; EA_fld is provided by IF or DF.

Addressing and effective address behavior is defined in:

- [05-addressing-model.md](./05-addressing-model.md)
- [06-ea-generation.md](./06-ea-generation.md)
