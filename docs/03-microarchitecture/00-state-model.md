# State Model

## Microstate Definition

ustate = (MS, TS)

- MS: Major State (instruction phase)
- TS: Time State (step within phase)

## Execution Flow

FETCH -> (optional DEFER) -> EXECUTE -> (optional INTERRUPT) -> FETCH

## Major State (MS)

MS represents instruction phases:
- FETCH
- DEFER
- EXECUTE
- INTERRUPT

MS is stored in a register and updated on TP:

MS <- MS_next

## State Transition

(MS, TS) -> (MS_next, TS_next)

- TS_next is timing-driven
- MS_next is control-driven
