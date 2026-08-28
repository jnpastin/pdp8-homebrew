# Interrupt Entry and Return

## 1. Purpose

This document defines the architectural relationships among:

- interrupt recognition
- interrupt entry
- preservation of return state
- interrupt-service execution
- restoration of processor state
- return to the interrupted program

The detailed register definitions, instruction semantics, micro-operations, and timing sequences remain in their owning documents and are not repeated here.

## 2. Scope

This document defines:

- the state preserved automatically during interrupt entry
- the state changed automatically during interrupt entry
- the initial execution context of the interrupt service routine
- the division of responsibility between hardware and software
- the use of the interrupt buffer during service and return
- the architectural return sequence
- interrupt-entry and return invariants

This document does not define:

- interrupt recognition conditions
- interrupt-versus-DMA precedence
- controller-specific interrupt conditions
- controller-specific service operations
- instruction encodings
- micro-operation implementation
- control-word encoding
- interrupt service routine structure
- software polling order

Interrupt recognition and precedence are defined in [Interrupt Recognition and Sequencing](./02-interrupt-recognition-and-sequencing.md).

## 3. Entry Boundary

Interrupt entry begins after CPU control recognizes a valid interrupt at EXECUTE TP4 and selects the INTERRUPT major state.

Recognition and entry are separate:

- recognition selects `MS_NEXT = INTERRUPT`
- the major-state transition commits at EXECUTE TP4
- interrupt-entry state changes occur during the following INTERRUPT major state

No interrupt-entry state change occurs directly as part of the recognition decision.

The interrupt-entry micro-operation sequence is defined in [Interrupt Execution](../03-microarchitecture/08-interrupt-execution.md).

## 4. Automatically Preserved State

Interrupt entry automatically preserves:

- the current `PC` in memory location field 0, address `0000`
- the current `IF` in `IB[5:3]`
- the current `DF` in `IB[2:0]`

The value preserved in memory location `0000` is the return address established before interrupt entry.

The interrupt buffer layout and lifetime are defined in the [Register Model Specification](../01-architecture/01-registers.md).

Interrupt entry does not automatically preserve:

- `AC`
- `L`
- `MQ`
- controller-local state
- controller flags
- the identity of the interrupting controller
- the number of controllers requesting service

Software must preserve any additional processor state required by the interrupted program.

## 5. Interrupt Vector

Interrupt entry transfers execution to:

- instruction field `0`
- program counter address `0001`

No vector table lookup occurs.

No controller supplies an interrupt vector.

No hardware-selected controller identity affects the entry address.

All interrupt requests use the same interrupt entry point.

## 6. Processor State Changes

During interrupt entry:

- `PC` becomes `0001`
- `IE` is cleared
- `IF` is cleared
- `DF` is cleared
- `DIF` is cleared

The detailed timing and micro-operations producing these changes are defined in [Interrupt Execution](../03-microarchitecture/08-interrupt-execution.md).

These changes establish the initial interrupt-service context in memory field 0 with interrupts disabled.

Interrupt entry does not modify controller state.

## 7. Interrupt Buffer

`IB` preserves the instruction and data fields that were active before interrupt entry.

Its layout is:

- `IB[5:3]` contains the saved `IF`
- `IB[2:0]` contains the saved `DF`

`IB` remains stable until the next interrupt entry.

`IB` does not contain:

- the saved `PC`
- `IE`
- `II`
- `CIFP`
- `AC`
- `L`
- `MQ`
- interrupt-controller identity
- controller priority

The saved `PC` resides in memory location field 0, address `0000`.

## 8. Deferred Field State

Interrupt entry clears `DIF`.

This prevents a deferred instruction-field value from remaining active as the interrupt service routine begins.

Interrupt entry does not define an independent saved copy of `DIF`.

The interrupted `IF` and `DF` values are preserved in `IB`. Restoration of those field values is performed through the defined memory-extension instructions.

The architectural behavior of `IB`, `DIF`, `IF`, and `DF` is defined in the [Register Model Specification](../01-architecture/01-registers.md).

## 9. Interrupt Enable and Inhibit State

Interrupt entry clears `IE`, preventing another interrupt from being recognized until software re-enables interrupts.

The interrupt-entry sequence does not itself establish a new software-selected interrupt nesting policy.

The relationships among `IE`, `II`, `CIFP`, ION, IOF, and deferred field changes are defined in [Interrupt Enable and Inhibit](./03-interrupt-enable-and-inhibit.md).

Software that re-enables interrupts during an interrupt service routine accepts responsibility for preserving any additional state required by nested service.

## 10. Controller State

Interrupt entry does not:

- acknowledge an interrupting controller
- clear a controller interrupt condition
- clear a controller flag
- disable a controller interrupt enable
- select a controller
- preserve a controller identity
- perform a controller-specific IOT

Controller interrupt requests remain governed by their controller-specific contracts.

A request may remain asserted throughout interrupt entry and interrupt-service execution until software performs the operation that clears, services, disables, cancels, or resets its underlying condition.

The persistent-request requirements are defined in the [Controller Contract](../07-io/04-controller-contract.md).

## 11. Interrupt-Source Identification

The hardware does not identify which controller requested interrupt service.

The interrupt service routine identifies requesting controllers through their programmer-visible status or skip operations.

When multiple controller requests are pending:

- interrupt entry occurs once
- software tests controller conditions
- software determines the service order
- software may service one or multiple controllers before returning

The polling order establishes software interrupt priority.

Controller-specific identification and service operations are defined in the [Controllers README](../07-io/10-controllers/README.md) and associated controller specific files.

## 12. Field-State Inspection and Restoration

The memory-extension instructions provide the defined mechanisms for inspecting and restoring the saved field state.

RIB makes the saved `IF` and `DF` values available to software through `AC`.

RMF:

- restores `DF` from the saved `DF` value
- stages the saved `IF` value in `DIF`
- defers application of the restored instruction field until the next JMP or JMS

The instruction semantics for RIB and RMF are defined in [IOT Instruction Detail](../02-isa/04-iot.md).

Their execution behavior is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

## 13. Return Address

The return address is stored in memory location field 0, address `0000`.

The interrupt service routine returns through an indirect JMP using location `0000`.

The indirect return obtains the saved address from location `0000` and transfers execution to that address according to the existing MRI addressing and JMP execution rules.

The return mechanism does not automatically restore:

- `AC`
- `L`
- `MQ`
- controller state
- interrupt enable state

Software must restore required state before completing the return sequence.

## 14. Return Field Application

When RMF is used before the return:

- saved `DF` is restored immediately
- saved `IF` is staged in `DIF`
- interrupt recognition remains inhibited across the deferred field-change interval
- the indirect JMP through location `0000` applies the staged instruction field
- the pending field-change state is cleared according to the JMP execution rules

The field-change application and interrupt-inhibit behavior are defined in [Interrupt Enable and Inhibit](./03-interrupt-enable-and-inhibit.md).

The JMP execution sequence is defined in [MRI Execution](../03-microarchitecture/05-mri-execution.md).

## 15. Interrupt Re-enabling and Return Sequence

Interrupt entry clears `IE`.

Software must explicitly execute ION when interrupts are to be re-enabled.

The expected interrupt return sequence is:

```text
RMF
ION
JMP I 0000
```

This sequence performs the following operations:

1. RMF restores the saved `DF` immediately and stages the saved `IF` in `DIF`.
2. ION sets `IE` and establishes the required one-instruction interrupt-recognition delay.
3. `JMP I 0000` obtains the saved return address, applies the deferred `IF`, and returns to the interrupted program.

The ION delay ensures that `JMP I 0000` completes before another interrupt may be recognized.

This sequence restores the saved field context, re-enables interrupts, and returns through the automatically preserved `PC`. It does not restore `AC`, `L`, or `MQ`. Software must restore any required general processor state before executing this sequence.

The instruction semantics are defined in [IOT Instruction Detail](../02-isa/04-iot.md), and the execution behavior is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md) and [MRI Execution](../03-microarchitecture/05-mri-execution.md).

## 16. DMA During Interrupt Service

Interrupt entry exits unconditionally to FETCH before interrupt-service instructions begin.

DMA is not enabled or disabled by `IE`, `II`, or interrupt entry.

After at least one interrupt-service instruction reaches EXECUTE TP4, an eligible aggregate DMA request may select the DMA major state according to [Interrupt Recognition and Sequencing](./02-interrupt-recognition-and-sequencing.md).

A valid interrupt request takes precedence over DMA at an EXECUTE TP4 boundary. However, interrupt entry clears `IE`, so another interrupt is not eligible unless software has re-enabled interrupts.

## 17. Software Responsibilities

The interrupt service routine is responsible for:

- preserving `AC`, `L`, and `MQ` when required
- identifying the requesting controller or controllers
- selecting the software service order
- servicing or disabling each handled interrupt condition
- preserving any additional software context
- inspecting saved field state when required
- restoring the required field state
- restoring other processor state preserved by software
- deciding whether and when to re-enable interrupts
- returning through the saved address in location `0000`

No omitted software responsibility is performed implicitly by interrupt entry or return.

## 18. Invariants

The following invariants apply:

- Interrupt recognition and interrupt entry are separate phases.
- Interrupt entry executes only in the INTERRUPT major state.
- The return `PC` is stored in memory location field 0, address `0000`.
- The interrupted `IF` and `DF` values are preserved in `IB`.
- `PC` becomes `0001` before the following FETCH begins.
- `IE`, `IF`, `DF`, and `DIF` are cleared during interrupt entry.
- Interrupt entry does not identify or acknowledge an interrupting controller.
- Interrupt entry does not clear controller state.
- Controller requests remain governed by their underlying controller conditions.
- Hardware does not determine controller service order.
- Software polling order determines interrupt priority.
- `AC`, `L`, and `MQ` are not automatically preserved.
- Field restoration uses the defined memory-extension instructions.
- The restored instruction field is applied through the deferred field-change mechanism.
- Return uses an indirect JMP through location `0000`.
- Interrupt re-enabling requires an explicit software operation.
- DMA eligibility is independent of interrupt-enable state.
- All processor and controller state changes occur only at TP events.
- Same-TP behavior uses pre-TP state.

## 19. Summary

Interrupt entry preserves the return address and interrupted field context, disables interrupts, establishes field 0, and begins execution at address `0001`.

The hardware does not identify or acknowledge the requesting controller and does not preserve general processor state. Software identifies and services requesting controllers, preserves and restores required state, restores the saved fields when necessary, re-enables interrupts when appropriate, and returns through memory location `0000`.