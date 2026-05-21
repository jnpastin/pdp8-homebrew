# Control Store Addressing

## Address Structure

ROM address is constructed from:
- MS bits
- TS bits
- Instruction fields (opcode, indirect)
- Flags

## Design Principle

Include only inputs that affect control behavior.

Unused combinations are implemented by duplicating ROM entries.

## Example

FETCH phase ignores opcode, so multiple addresses map to identical control outputs.
