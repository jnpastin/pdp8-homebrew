
## Control

### Purpose
Defines how system behavior is generated from machine state.

### Model
Control is defined as:

CONTROL = f(MS, TS, IR, FLAGS, EXT)

See full definition:
- [00-control-model.md](00-control-model.md)

### Responsibilities
- Generate datapath control signals
- Define memory and I/O operations
- Determine next major state

### Relationships
- Uses state from [../01-architecture/README.md](../01-architecture/README.md)
- Drives execution in [../03-microarchitecture/README.md](../03-microarchitecture/README.md)
- Evaluated within timing defined in [../09-timing/README.md](../09-timing/README.md)

### Constraints
- All behavior must be represented in ROM
- No external sequencing logic
