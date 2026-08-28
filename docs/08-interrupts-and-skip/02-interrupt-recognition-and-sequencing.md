# Interrupt Recognition and Sequencing

## 1. Purpose

This document defines:

- when an interrupt may be recognized
- how interrupt eligibility participates in major-state sequencing
- the relationship between interrupt recognition and interrupt entry
- the precedence between interrupt and DMA requests
- the sequencing invariants governing interrupt recognition

Detailed eligibility, timing, control, and execution definitions remain in their owning documents and are not repeated here.

## 2. Scope

This document applies to the major-state transition decision made at the completion of an instruction.

This document defines only the sequencing relationship among:

- completion of the current instruction
- interrupt eligibility
- DMA eligibility
- selection of the next major state

This document does not define:

- interrupt-request electrical aggregation
- controller-specific interrupt conditions
- interrupt-enable or interrupt-inhibit state transitions
- interrupt-entry micro-operations
- DMA requester arbitration
- timing-signal generation
- control-address encoding
- control-word encoding

## 3. Recognition Boundary

Interrupt recognition occurs only at the EXECUTE TP4 major-state transition boundary.

An interrupt request must not cause entry into the INTERRUPT major state:

- during FETCH
- during DEFER
- before the current instruction reaches EXECUTE TP4
- directly from a change in the aggregate interrupt request
- directly from a controller state change

An interrupt request that becomes valid before the EXECUTE TP4 sampling boundary may participate in that boundary's major-state transition decision, subject to the applicable setup and hold requirements.

An interrupt request that does not satisfy those requirements is not available for that decision and may be recognized at a later eligible boundary if it remains valid.

The major-state transition timing is defined in [Major State Timing](../09-timing/03-major-state-timing.md).

## 4. Recognition Input

CPU control uses the existing `INTERRUPT_REQUEST_VALID` derived flag as the interrupt-recognition input.

The derivation and value encoding of `INTERRUPT_REQUEST_VALID` are defined in [Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md).

This document does not separately evaluate:

- `IE`
- `II`
- `/INT_REQ`

Those inputs are reduced to the existing derived flag before the major-state transition decision.

## 5. Recognition and Entry

Interrupt recognition and interrupt entry are separate phases.

At EXECUTE TP4:

- CPU control evaluates the available sequencing conditions.
- A recognized interrupt selects `MS_NEXT = INTERRUPT`.
- The current instruction completes.
- The major-state transition commits.

During the following INTERRUPT major state:

- the interrupt-entry micro-operations execute
- the return state is preserved
- control is transferred to the interrupt service routine

Recognition at EXECUTE TP4 does not itself perform any interrupt-entry micro-operation.

Interrupt-entry execution is defined in [Interrupt Execution](../03-microarchitecture/08-interrupt-execution.md).

## 6. Next-Major-State Selection

At EXECUTE TP4, the next-major-state decision follows this precedence:

1. A valid interrupt request selects `INTERRUPT`.
2. Otherwise, an asserted aggregate DMA request selects `DMA`.
3. Otherwise, normal execution selects `FETCH`.

Conceptually:

```text
if INTERRUPT_REQUEST_VALID:
    MS_NEXT = INTERRUPT
else if /DMA_REQ = 0:
    MS_NEXT = DMA
else:
    MS_NEXT = FETCH
```

This expression defines the required sequencing result. Its implementation remains governed by the [Control Model](../04-control/01-control-model.md).

The precedence above applies only to the next-major-state decision at EXECUTE TP4.
 
At INTERRUPT TP4, `MS_NEXT` is unconditionally `FETCH`. Interrupt and DMA eligibility are not evaluated for that transition. Therefore, INTERRUPT cannot transition directly to another INTERRUPT or to DMA. A subsequent interrupt or DMA request may be recognized only after execution reaches a later EXECUTE TP4 boundary.

## 7. Interrupt Precedence over DMA

When `INTERRUPT_REQUEST_VALID` is asserted and aggregate `/DMA_REQ` is also asserted for the same EXECUTE TP4 decision:

- `MS_NEXT` must select `INTERRUPT`
- `MS_NEXT` must not select `DMA`
- the interrupt and DMA requests must not produce multiple major-state transitions
- the pending DMA request is not acknowledged or consumed by the CPU decision

Interrupt precedence over DMA is a fixed precedence between request classes.

It does not:

- compare an interrupt-controller priority with a DMA-controller priority
- identify the interrupting controller
- modify DMA arbitration priority
- cancel a controller DMA request
- grant DMA ownership
- acknowledge an interrupting controller

## 8. Deferred DMA Service

When interrupt recognition prevents immediate DMA entry:

- DMA-capable controllers retain their individual requests according to the [Controller Contract](../07-io/04-controller-contract.md)
- the DMA arbiter and aggregation logic continue to follow the [DMA Arbitration](../07-io/06-dma-arbitration.md) contract
- CPU control may select DMA at a later eligible EXECUTE TP4 boundary

Interrupt recognition does not guarantee that aggregate `/DMA_REQ` remains asserted throughout interrupt entry or interrupt-service execution.

Later DMA eligibility depends on the request and arbitration state defined by the DMA subsystem at the later sampling boundary.

## 9. Controller Request Persistence

Interrupt recognition does not acknowledge or consume the aggregate interrupt request.

Entry into the INTERRUPT major state does not require an interrupt-capable controller to clear its request.

A controller request remains governed by its controller-specific condition and the [Controller Contract](../07-io/04-controller-contract.md).

Software must service, clear, disable, or otherwise remove the underlying controller condition according to the controller-specific contract.

## 10. Same-Boundary Semantics

The EXECUTE TP4 transition decision uses values available before the TP4 commit.

A state change committed at EXECUTE TP4 must not affect another decision committed at that same TP4.

Therefore:

- the transition decision must not depend on state produced at TP4
- a controller state change at TP4 must not retroactively create or remove the interrupt recognized at that TP4
- a DMA-arbiter state change at TP4 must not retroactively alter the request value sampled for that TP4
- interrupt-entry state changes cannot participate in the recognition decision that selected INTERRUPT

## 11. Sequencing Invariants

The following invariants apply:

- Interrupt recognition occurs only at EXECUTE TP4.
- Interrupt recognition depends on `INTERRUPT_REQUEST_VALID`.
- Interrupt recognition does not directly evaluate unreduced processor state.
- A valid interrupt request selects exactly one next major state.
- A valid interrupt request takes precedence over an asserted aggregate `/DMA_REQ`.
- DMA is selected only when no valid interrupt request exists at the same recognition boundary.
- FETCH is selected only when neither interrupt nor DMA service is selected.
- Recognition selects INTERRUPT execution but does not perform interrupt-entry state changes.
- Interrupt recognition does not identify, acknowledge, service, or clear an interrupting controller.
- Interrupt recognition does not consume a pending DMA controller request.
- Major-state selection uses only values available before the TP4 commit.
- `MS_NEXT` commits according to the existing sequencing and timing rules.
- No request may produce an asynchronous major-state transition.
- No boundary may select more than one next major state.

## 12. Summary

Interrupt recognition is a synchronous sequencing decision made at EXECUTE TP4.

The decision uses the existing `INTERRUPT_REQUEST_VALID` derived flag. A valid interrupt request selects the INTERRUPT major state and takes precedence over an eligible DMA request. If no interrupt is valid, an asserted aggregate `/DMA_REQ` selects DMA. Otherwise, execution returns to FETCH.

Recognition selects the next major state only. Interrupt entry occurs during the subsequent INTERRUPT major state.