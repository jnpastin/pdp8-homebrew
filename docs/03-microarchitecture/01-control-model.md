# Control Model

Control is implemented using a ROM-based function:

CONTROL = ROM[MS, TS, IR_subfields, FLAGS]

## Inputs
- MS
- TS
- IR (opcode, indirect bit)
- Flags

## Outputs
- Datapath control signals
- MS_next

## Control Word

Each ROM entry defines:
- Register loads
- ALU operation
- Bus selection
- Memory read/write
- Next Major State
