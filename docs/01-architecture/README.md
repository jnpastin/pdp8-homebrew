
## Architecture

### Purpose
Defines the programmer-visible machine model. This includes what software can observe and rely on.

### Scope
Includes:
- Architectural registers (PC, AC, L, MQ, IF, DF, IE)
- Memory model and addressing (fields, 12-bit addressing)
- Interrupt visibility (IE and /INT_REQ interaction)

Excludes:
- Execution behavior ([Microarchitecture/README.md](../03-microarchitecture/README.md))
- Instruction semantics ([ISA/README.md](../02-isa/README.md))
- Control signals ([Control/README.md](../04-control/README.md))

### Model Summary
- All state visible to software is represented as registers.
- Memory is addressed via fielded 12-bit addressing.
- Interrupts occur when IE is enabled and /INT_REQ is asserted.

### Related Documents
- [01-registers.md](01-registers.md)
- [02-dataflow-and-bus-model.md](02-dataflow-and-bus-model.md)
