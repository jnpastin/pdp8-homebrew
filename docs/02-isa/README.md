
## Instruction Set Architecture

### Purpose
Defines instruction semantics independent of execution timing or implementation.

### Scope
Includes:
- Instruction classes (MRI, OPR, IOT)
- Operand and result behavior
- Skip logic behavior

Excludes:
- Timing ([09-timing/README.md](../09-timing/README.md))
- Microarchitectural execution ([03-microarchitecture/README.md](../03-microarchitecture/README.md))
- Control implementation ([04-control/README.md](../04-control/README.md))

### Model Summary
- Instructions are defined by IR bitfields.
- Behavior is determined without decoding into symbolic instructions.
- Skip behavior sets a pending control condition that affects PC update.

General information about the structure of the instructions and detailed information about MRI and IOT instructions can be found at [00-encoding-model.md](./00-encoding-model.md)
Detailed information about the OPR instructions can be found at:
- [01-group-1.md](./01-group-1.md)
- [02-group-2.md](./02-group-2.md)
- [03-group-3.md](./03-group-3.md)
