# Timing Integration

## Time State (TS)

TS defines execution phases:
- TS1
- TS2
- TS3
- TS4

TS provides a stable evaluation window and does not cause state changes.

## Timing Pulse (TP)

TP is the global state transition event.

At TP:
- Registers latch
- MS updates
- Timing advances

TP advances the system from one microstate to the next.
