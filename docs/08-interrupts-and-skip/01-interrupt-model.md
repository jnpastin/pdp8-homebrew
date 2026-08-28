# Interrupt Model

## 1. Purpose

This document defines the system-level interrupt model and the relationships among:

- interrupt-capable controllers
- aggregate interrupt request
- interrupt eligibility
- interrupt recognition
- interrupt entry
- interrupt-source identification
- interrupt service
- interrupt return

Detailed definitions remain in their owning documents and are not repeated here.

## 2. Scope

This document defines:

- the architectural interrupt flow
- the division of responsibility between hardware and software
- the relationship between interrupt requests and interrupt recognition
- the relationship between interrupt recognition and interrupt entry
- interrupt priority and dispatch policy
- the relationship between interrupt and DMA service
- system-level interrupt invariants

This document does not define:

- register structure or register write behavior
- instruction encodings or instruction semantics
- micro-operation sequences
- control-signal encodings
- electrical aggregation of interrupt requests
- controller-specific interrupt conditions
- detailed timing behavior

Those definitions remain authoritative in their respective sections.

## 3. Interrupt Flow

The architectural interrupt flow is:

1. A controller establishes a persistent interrupt condition according to its controller-specific contract.
2. Interrupt-capable controllers contribute to the aggregate interrupt request.
3. CPU control evaluates interrupt eligibility at the defined instruction-completion boundary.
4. A valid interrupt request selects the INTERRUPT major state.
5. INTERRUPT execution preserves the defined return and field state and transfers control to the interrupt service routine.
6. Software identifies the requesting controller.
7. Software services or disables the controller condition responsible for the request.
8. Software restores the required processor state and returns to the interrupted program.

Each step is governed by the authoritative document that owns its detailed behavior.

## 4. Request Model

The interrupt request interface indicates only whether one or more interrupt-capable controllers are requesting service.

The aggregate request does not identify:

- the requesting controller
- the number of requesting controllers
- the relative priority of requesting controllers
- the operation required to service a controller

Sampling or accepting the aggregate request does not acknowledge, clear, or consume any controller request.

A controller request remains asserted until its underlying controller condition is cleared, serviced, canceled, disabled, or reset according to the applicable controller contract.

## 5. Eligibility and Recognition

Interrupt eligibility and interrupt recognition are separate concepts.

Interrupt eligibility is determined by the interrupt-related processor state and the aggregate interrupt request. The authoritative eligibility expression is defined in [Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md).

Interrupt recognition occurs when CPU control uses a valid interrupt condition to select the INTERRUPT major state at the defined sequencing boundary.

The detailed recognition boundary, control inputs, and major-state selection rules are defined in [Interrupt Recognition and Sequencing](./02-interrupt-recognition-and-sequencing.md).

## 6. Interrupt Entry

Interrupt recognition does not itself perform the interrupt-entry state changes.

Recognition selects the INTERRUPT major state. The state changes required for interrupt entry occur during that major state according to [Interrupt Execution](../03-microarchitecture/08-interrupt-execution.md).

Interrupt entry does not:

- identify the requesting controller
- acknowledge a controller
- clear a controller request
- service a controller operation
- assign hardware priority among interrupting controllers

## 7. Interrupt Priority and Dispatch

### 7.1 Controller Priority

The system does not implement hardware priority resolution among interrupting controllers.

Interrupt-source priority is established by the order in which the interrupt service routine tests controller conditions.

Software may:

- test controllers in a defined priority order
- service one requesting controller
- service multiple requesting controllers during one interrupt-service invocation
- change polling order without changing the hardware architecture

The controller-specific IOT operations used to identify and service a request are defined by the applicable controller contract.

### 7.2 Simultaneous Controller Requests

When multiple controller requests contribute to the aggregate interrupt request:

- hardware recognizes only that interrupt service is required
- INTERRUPT entry occurs once
- software determines which controllers are requesting service
- software determines the service order

No hardware-selected controller identity is preserved by interrupt entry.

### 7.3 Starvation Responsibility

Because interrupt priority is established by software polling order, the interrupt service routine is responsible for ensuring that its dispatch policy provides the required service behavior for all installed controllers.

No hardware fairness policy exists among interrupting controllers.

## 8. Interrupt and DMA Relationship

Interrupt recognition and DMA request recognition are evaluated at the same EXECUTE major-state completion boundary.

When both of the following are true at that boundary:

- an interrupt request is valid
- aggregate `/DMA_REQ` is asserted

the interrupt request takes precedence and CPU control selects the INTERRUPT major state.

The pending DMA request is not consumed by this decision. DMA-capable controllers retain their request state according to the [Controller Contract](../07-io/04-controller-contract.md) and participate in later DMA arbitration when DMA service again becomes eligible.

Interrupt priority over DMA is a fixed request-class precedence rule. It does not compare controller interrupt priority with DMA priority.

## 9. Software Responsibilities

The interrupt service routine is responsible for:

- identifying the requesting controller or controllers
- establishing the software dispatch order
- servicing or disabling each handled interrupt condition
- preserving processor state not automatically preserved by interrupt entry
- restoring the required processor state before return
- controlling whether interrupts are re-enabled
- preventing unintended starvation under its polling policy

The hardware does not perform these software responsibilities implicitly.

## 10. Controller Responsibilities

Each interrupt-capable controller is responsible for:

- defining its interrupt-enable state
- defining its interrupt condition
- producing a persistent interrupt contribution from registered controller state
- preserving the request while its qualifying condition remains true
- defining the operations that clear, service, disable, or reset the condition
- providing the programmer-visible operation used by software to identify its pending condition

Detailed controller obligations are defined in the [Controller Contract](../07-io/04-controller-contract.md).

## 11. Architectural Invariants

The interrupt system must satisfy all of the following:

- The aggregate interrupt request indicates request presence only.
- The aggregate interrupt request does not identify a controller.
- Hardware does not assign priority among interrupting controllers.
- Interrupt-controller priority is determined by software polling order.
- Interrupt recognition occurs only at the defined sequencing boundary.
- A valid interrupt request takes precedence over an eligible DMA request at the same EXECUTE completion boundary.
- Interrupt recognition selects INTERRUPT execution but does not perform interrupt-entry state changes directly.
- Interrupt entry does not acknowledge or clear controller state.
- Sampling a persistent interrupt request does not consume it.
- Controller requests remain asserted while their qualifying conditions remain true.
- Software identifies and services interrupting controllers.
- No interrupt-related state change occurs outside a TP event.
- No action committed at a TP may affect another decision committed at that same TP.
- Interrupt behavior must remain deterministic for every defined processor and controller state.

## 12. Summary

The interrupt architecture uses:

- one aggregate request indication
- CPU-controlled interrupt eligibility and recognition
- a dedicated INTERRUPT major state
- software identification of interrupt sources
- software-defined controller priority
- persistent controller requests
- fixed interrupt precedence over DMA at a simultaneous EXECUTE completion boundary

Detailed register, control, execution, timing, electrical, and controller behavior remains defined by the applicable owning documents.