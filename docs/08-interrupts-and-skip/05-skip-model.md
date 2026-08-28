# Skip Model

## 1. Purpose

This document defines the common architectural model for conditional and unconditional instruction skips.

It coordinates the relationships among:

- skip-condition evaluation
- skip sources
- program-counter increment
- same-TP behavior
- subsequent instruction fetch

The individual skip conditions, instruction semantics, controller conditions, micro-operations, and timing assignments remain defined in their owning documents and are not repeated here.

## 2. Scope

This document defines:

- the common result of a taken skip
- the supported skip-source classes
- the relationship between condition evaluation and `PC_INC`
- the absence of persistent skip state
- the effect of a skip on subsequent instruction execution
- same-TP rules applying to skip decisions
- system-level skip invariants

This document does not define:

- instruction encoding
- Group 2 predicate equations
- ISZ increment behavior
- CPU-internal IOT semantics
- controller-specific flag behavior
- controller-specific IOT semantics
- control-address encoding
- control-word encoding
- program-counter implementation

## 3. Common Skip Effect

A taken skip increments `PC` exactly once in addition to any increment already performed during instruction fetch.

Conceptually:

```text
if SKIP_CONDITION:
    PC <- PC + 1
```

The additional increment causes the next sequential instruction word to be bypassed.

A skip does not:

- branch to an independently supplied address
- modify `IF`
- modify `DF`
- modify the skipped memory word
- fetch or execute the skipped instruction
- create persistent skip state

The `PC_INC` micro-operation is defined in [Micro-Operations](../03-microarchitecture/02-micro-operations.md).

## 4. Skip Sources

The system supports skip behavior from four source classes:

- Group 2 OPR instructions
- ISZ instructions
- CPU-internal IOT instructions
- external-controller IOT instructions

Each source class defines its own condition and timing.

The source-specific conditions remain independent. This document defines only their shared architectural result.

## 5. Group 2 OPR Skips

Group 2 OPR instructions evaluate predicates derived from `AC` and `L`.

The selected Group 2 subgroup determines how enabled predicates are combined:

- the OR subgroup skips when any enabled predicate is true
- the AND subgroup skips when all enabled predicates are true
- an empty AND-subgroup predicate set produces the unconditional SKP behavior
- an empty OR-subgroup predicate set does not skip

The complete instruction semantics are defined in [Group 2 OPR Encoding Model](../02-isa/02-group-2.md).

The execution behavior is defined in [Group 2 Execution](../03-microarchitecture/07-opr/02-group2-execution.md).

The reduced control condition is defined in [Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md).

A taken Group 2 skip selects one `PC_INC` at TP1 of EXECUTE.

Later operations encoded in the same Group 2 instruction execute at their assigned timing pulses whether or not the skip is taken.

## 6. ISZ Skip

ISZ increments the selected memory word and writes the result back to memory.

ISZ skips when the incremented value is zero.

The skip condition depends on the committed incremented value available before the ISZ skip decision. It does not depend on the pre-increment memory value.

The ISZ execution sequence is defined in [MRI Execution](../03-microarchitecture/05-mri-execution.md).

The reduced ISZ skip condition is defined in [Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md).

A taken ISZ skip selects one `PC_INC` at TP4 of EXECUTE.

The memory write and `PC_INC` may commit at the same TP because they target different state.

## 7. CPU-Internal IOT Skips

CPU-internal IOT instructions may define instruction-specific skip behavior.

The currently defined CPU-internal skip instructions are:

- SKON
- SRQ

The complete instruction semantics are defined in [IOT Instruction Detail](../02-isa/04-iot.md).

Their execution behavior is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

### 7.1 SKON

SKON tests the pre-TP interrupt-enable state.

When the defined SKON condition is true:

- one `PC_INC` commits
- `IE` is cleared at the same TP

The `IE` clear must not affect the skip decision committed at that same TP.

SKON does not test the aggregate interrupt-request input.

### 7.2 SRQ

SRQ tests whether the aggregate interrupt request is asserted.

When the defined SRQ condition is true, one `PC_INC` commits.

SRQ does not:

- require interrupt eligibility
- require `IE` to be set
- require `II` to be clear
- acknowledge an interrupting controller
- clear a controller interrupt condition
- alter interrupt-enable state

SRQ tests request presence rather than whether the CPU would recognize the request as an interrupt.

## 8. External-Controller IOT Skips

An external controller requests a skip through `IO_SKIP_REQ`.

Only the selected controller may assert `IO_SKIP_REQ`.

The selected controller derives the request from:

- `IOT_ACTIVE`
- address match
- decoded `IOP`
- registered controller state
- the assigned timing phase

The common external-IOT skip behavior is defined in [External IOT Interface](../07-io/02-external-iot-interface.md).

Controller-specific skip conditions are defined in the [Controllers README](../07-io/10-controllers/README.md) and applicable controller specific documents.

A valid external-controller skip request:

- is asserted during TS4
- selects one CPU `PC_INC`
- commits at TP4
- does not permit the controller to modify `PC` directly

## 9. External Skip Request Lifetime

`IO_SKIP_REQ` is phase-specific rather than persistent.

A controller asserts it only during the TS4 in which the applicable external IOT evaluates the controller's registered skip condition.

The request:

- applies only to the current external IOT
- does not remain effective after TP4
- does not create stored CPU skip state
- does not consume or clear the controller condition being tested

A controller-specific instruction may separately clear or modify its underlying controller condition at TP4 when the applicable controller contract defines that behavior.

## 10. Same-TP Semantics

A skip decision uses state available before its commit TP.

A state change committed at the same TP must not affect that skip decision.

Therefore:

- SKON tests the pre-TP `IE` value even though `IE` clears at that TP
- an external-controller skip request uses registered controller state available before TP4
- a controller state change committed at TP4 cannot create or remove the skip committed at that TP4
- an action committed at the same TP as `PC_INC` cannot use the incremented `PC` as its input
- a skip result cannot affect another action committed at the same TP

All updates selected for the same TP commit concurrently.

## 11. Program-Counter Update Exclusivity

A skip is realized only through `PC_INC`.

At any TP:

- at most one effective `PC_INC` may target `PC`
- `PC_INC` and `PC_LOAD` must not both be asserted
- multiple true skip conditions must not produce multiple increments
- a controller must not modify `PC` directly
- no skip source may bypass the defined program-counter update mechanism

When an instruction defines multiple predicates, those predicates are reduced to one boolean skip decision before `PC_INC` is selected.

## 12. No Persistent Skip State

The CPU does not contain a skip-pending register or stored skip result.

A skip condition is:

1. evaluated from the state and inputs defined for its source
2. consumed during the applicable timing state
3. realized as `PC_INC` at the associated timing pulse
4. discarded after that decision

A skip decision does not persist into another timing state, instruction, or major state.

If a controller condition remains true, software must execute another applicable skip IOT to test that condition again.

## 13. Relationship to Instruction Fetch

Normal FETCH increments `PC` to identify the instruction following the current instruction.

A taken skip performs one additional increment during execution of the current instruction.

The following FETCH therefore uses the address after the skipped instruction.

The skipped instruction:

- is not loaded into `IR`
- does not enter EXECUTE
- produces no instruction-defined state change
- cannot itself generate a skip, interrupt-control action, I/O operation, or memory operation

The next executed instruction follows the normal FETCH, optional DEFER, and EXECUTE sequence.

## 14. Relationship to Interrupt and DMA Recognition

A skip changes `PC`; it does not independently alter the major-state transition policy.

At EXECUTE TP4, a skip may commit concurrently with interrupt or DMA recognition when the applicable instruction defines its skip at TP4.

The transition decision and `PC_INC` use pre-TP4 state and commit concurrently.

If an interrupt is recognized at the same EXECUTE TP4:

- the incremented `PC` is the return address preserved during interrupt entry
- interrupt entry proceeds according to [Interrupt Entry and Return](./04-interrupt-entry-and-return.md)

If DMA is selected at the same EXECUTE TP4:

- the incremented `PC` remains the address used when normal instruction execution resumes
- DMA proceeds according to the existing DMA sequencing rules

Neither interrupt recognition nor DMA recognition cancels a valid skip committed at that same TP4.

## 15. Source-Specific State Effects

A skip source may define other state changes in addition to `PC_INC`.

Examples already defined by the owning documents include:

- SKON clearing `IE`
- ISZ writing the incremented memory value
- controller IOTs changing controller-local state
- Group 2 instructions performing later `AC` or halt-related operations

These additional effects do not change the common skip result.

Each additional effect:

- must be explicitly defined by the owning instruction or controller contract
- must obey the assigned TP
- must not conflict with another update to the same destination
- must not depend on a result committed at the same TP

## 16. Invariants

The following invariants apply:

- Every taken skip increments `PC` exactly once.
- Every untaken skip leaves `PC` unchanged by the skip mechanism.
- Normal FETCH increment and skip increment are distinct operations.
- A skip bypasses exactly one sequential instruction word.
- All skip effects use the defined `PC_INC` mechanism.
- No controller modifies `PC` directly.
- No persistent CPU skip state exists.
- Source-specific skip conditions remain defined by their owning documents.
- Multiple predicates within one instruction reduce to one skip decision.
- Multiple true predicates must not produce multiple `PC_INC` operations.
- `PC_INC` and `PC_LOAD` must not be active at the same TP.
- Skip decisions use pre-TP state.
- Same-TP state changes do not affect the skip decision committed at that TP.
- Group 2 skips commit at their defined Group 2 execution point.
- ISZ skip depends on the incremented memory value.
- SKON tests the pre-clear `IE` value.
- SRQ tests aggregate interrupt-request presence rather than interrupt eligibility.
- External-controller skips require a selected controller and a valid phase-specific `IO_SKIP_REQ`.
- Evaluating a controller skip condition does not implicitly clear that condition.
- A skip does not independently alter interrupt or DMA sequencing.
- A TP4 skip remains effective when an interrupt or DMA transition commits at the same TP4.

## 17. Summary

All skip sources share one architectural result: a taken skip increments `PC` exactly once so the next sequential instruction is bypassed.

Group 2 OPR, ISZ, CPU-internal IOT, and external-controller IOT instructions define distinct skip conditions and timing. Those conditions are evaluated from pre-TP state and reduced to one `PC_INC` decision.

No persistent skip state exists, and no controller may modify `PC` directly.