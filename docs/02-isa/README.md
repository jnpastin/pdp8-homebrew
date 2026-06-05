
## Instruction Set Architecture

### Purpose
Defines instruction semantics independent of execution timing or implementation.

### Scope
Includes:
- Instruction classes (MRI, OPR, IOT)
- Operand and result behavior
- Skip logic behavior

Excludes:
- Timing ([../09-timing/README.md](../09-timing/README.md))
- Microarchitectural execution ([../03-microarchitecture/README.md](../03-microarchitecture/README.md))
- Control implementation ([../04-control/README.md](../04-control/README.md))

### Model Summary
- Instructions are defined by IR bitfields.
- Behavior is determined without decoding into symbolic instructions.
- Skip behavior sets a pending control condition that affects PC update.

### Related Documents
- [00-isa_encoding-model.md](00-isa_encoding-model.md)
- [01-isa_skip-logic.md](01-isa_skip-logic.md)
