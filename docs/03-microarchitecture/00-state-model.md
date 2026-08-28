# State Model

## Purpose

Defines the formal execution state of the processor and the rules governing its evolution over time.

This model provides the only mechanism by which execution progresses.

---

## Microstate Definition

Execution state is defined as:

    μstate = (MS, TS)

Where:
- MS: Major State (instruction-level phase)
- TS: Time State (phase-local step)

---

## State Evolution

Execution proceeds as a sequence of discrete transitions:

    (MS, TS) -> (MS_NEXT, TS_next)

With:
- TS_next determined solely by the timing system
- MS_NEXT determined by execution behavior

---

## Execution Flow

The processor follows this high-level progression:

    FETCH -> (optional DEFER) -> EXECUTE -> (optional INTERRUPT) -> FETCH

Properties:
- FETCH always occurs
- DEFER occurs only for indirect addressing
- EXECUTE occurs exactly once per instruction
- INTERRUPT occurs only when conditions are met at the end of EXECUTE
- DMA occurs only when conditions are met at the end of EXECUTE

---

## Major State (MS)

MS encodes the instruction-level phase of execution.

Valid states:
- FETCH
- DEFER
- EXECUTE
- INTERRUPT
- DMA

### MS Update Rule


MS_NEXT is determined by control logic during TS4 and is not represented as a μop.

MS updates are not produced by datapath operations.

MS is stored in a register and updated only at TP4:

    MS <- MS_NEXT   (only at TP4)

Constraints:
- MS is stable during TP1–TP3
- Exactly one MS is active at any time
- MS must not change outside TP4

---

## Time State (TS)

TS defines the execution phase within a major state.

Properties:
- TS progression is driven exclusively by the timing subsystem
- TS is independent of instruction semantics
- TS determines ordering of operations within a major state

---

## Timing Interaction (Normative)

Execution obeys the following invariant:

    During TS:
        system state is stable
        and evaluation occurs

    At TP:
        state transitions occur

Implications:
- No register or architectural state changes outside TP
- All observable behavior is the result of TP-triggered updates
- TS provides setup; TP commits results

---

## Behavioral Model

All processor behavior must be expressible as a sequence of state updates of the form:

    At TP_n:
        register <- function(registers, IR, memory values)

Constraints:
- No implicit state changes are permitted
- No behavior may depend on intermediate (non-registered) values at TP
- All inputs to a state update must be stable during the preceding TS

---

## Flags Model

Flags used for execution decisions are not stored independently.

Properties:
- Flags are derived from architectural registers
- Flags introduce no additional state
- Flags are valid only when their source registers are stable

Constraints:
- No dedicated flag register may exist
- Flags must not be used until corresponding register updates complete at TP

---

## External Inputs (EXT)

External inputs are the only non-register inputs that may influence execution.

Properties:
- EXT includes signals such as interrupt and DMA requests
- EXT must be stable before TP

Constraints:
- EXT must not include datapath or control signals
- EXT must be explicitly defined and bounded

---

## State Invariants

The following invariants must always hold:

- Exactly one MS is active
- Exactly one TS is active
- All architectural state resides in registers
- All state changes occur only at TP
- TS progression does not depend on instruction behavior
- MS transitions occur only at TP4

---

## State Transition Constraints

### Execution

Execution decisions must depend only on stable state.

Allowed inputs:
- Registers
- IR bits
- EXT inputs

Disallowed inputs:
- Transient datapath signals
- Control signals
- Combinational intermediate values

Requirement:
- Any datapath result must be captured into a register before it can influence future execution

### Control

Control decisions (including MS_NEXT) are evaluated during TS and committed at TP, subject to the same stability and input constraints as μops.


---

## Relationship to Other Models

[Timing (09)](../09-timing/README.md):
- Defines TS and TP generation
- Does not define behavior

Microarchitecture (this section):
- Defines execution ordering using MS and TS

[Control (04)](../04-control/README.md):
- Implements behavior as a function of (MS, TS, IR, FLAGS, EXT)

---

## Summary

The system executes as a sequence of discrete, deterministic state transitions driven by:

- timing progression (TS)
- execution-defined state updates (MS transitions and register writes at TP)

All behavior is expressed as ordered TP-triggered updates within the (MS, TS) state model.
