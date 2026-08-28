# Interrupts and Skip

## 1. Purpose

Section 8 coordinates the system-level behavior of:

- interrupt requests
- interrupt eligibility and recognition
- interrupt entry and return
- interrupt enable and inhibit state
- interrupt-source dispatch
- interrupt and DMA precedence
- instruction skips

Detailed register, instruction, micro-operation, controller, control-signal, and timing definitions remain in their owning sections and are not repeated here.

## 2. Scope

Section 8 defines:

- the architectural interrupt flow
- the boundary between interrupt eligibility, recognition, and entry
- the relationship among `IE`, `II`, `CIFP`, CIF, RMF, and ION
- interrupt entry and software-controlled return
- software identification and servicing of interrupt sources
- interrupt precedence over DMA at EXECUTE TP4
- the common architectural result of a taken skip
- the absence of persistent skip state
- Section 8-specific illegal conditions

Section 8 does not define:

- instruction encodings or individual instruction semantics
- register implementation
- micro-operation definitions or execution sequences
- controller-specific interrupt conditions or IOT behavior
- control-address or control-word encoding
- electrical request aggregation
- timing generation
- DMA arbitration

## 3. Documents

- [Interrupt Model](./01-interrupt-model.md) defines the system-level interrupt flow, hardware and software responsibilities, controller dispatch policy, and the relationship between interrupts and DMA.
- [Interrupt Recognition and Sequencing](./02-interrupt-recognition-and-sequencing.md) defines the interrupt-recognition boundary, next-major-state selection, and interrupt precedence over DMA.
- [Interrupt Enable and Inhibit](./03-interrupt-enable-and-inhibit.md) coordinates `IE`, `II`, `CIFP`, ION, IOF, SKON, CIF, RMF, and deferred instruction-field application.
- [Interrupt Entry and Return](./04-interrupt-entry-and-return.md) defines the architectural relationships among interrupt entry, preserved state, interrupt-service execution, field restoration, interrupt re-enabling, and return.
- [Skip Model](./05-skip-model.md) defines the common architectural result and invariants shared by Group 2 OPR, ISZ, CPU-internal IOT, and external-controller IOT skips.
- [Interrupt and Skip Invalid Conditions](./06-invalid-conditions.md) identifies illegal conditions defined by the Section 8 coordination model.

## 4. Model Summary

Interrupt requests are aggregated without preserving controller identity. CPU control recognizes an eligible interrupt only at EXECUTE TP4 and selects the INTERRUPT major state. Interrupt entry preserves the return address and field context, establishes the interrupt-service context in field 0, and disables interrupts.

Software identifies and services the requesting controller or controllers. Hardware does not assign priority among interrupting controllers.

A valid interrupt takes precedence over DMA at the same EXECUTE TP4 boundary. The INTERRUPT major state exits unconditionally to FETCH, so neither interrupt nor DMA service may begin directly from INTERRUPT.

A taken skip increments `PC` exactly once in addition to the normal FETCH increment. Skip conditions are evaluated and consumed at their assigned execution point; no persistent skip state exists.

## 5. Core Invariants

- Interrupt eligibility, interrupt recognition, and interrupt entry are distinct concepts.
- Interrupt recognition occurs only at EXECUTE TP4.
- Interrupt entry occurs only during the INTERRUPT major state.
- INTERRUPT exits unconditionally to FETCH.
- A valid interrupt takes precedence over an eligible DMA request at the same EXECUTE TP4 boundary.
- Interrupt recognition and entry do not identify, acknowledge, service, or clear an interrupting controller.
- Interrupt-controller priority and dispatch are controlled by software.
- ION delays interrupt recognition until the following instruction completes.
- CIF and RMF inhibit interrupt recognition until the staged instruction field is applied by JMP or JMS.
- `IE`, `II`, and `CIFP` do not control DMA eligibility.
- Every taken skip produces exactly one additional `PC_INC`.
- No persistent skip state exists.
- All same-TP decisions use pre-TP state.
- All state changes occur only at defined TP events.

## 6. Related Authoritative Documents

Definitions coordinated by Section 8 are owned by:

- [Register Model Specification](../01-architecture/01-registers.md)
- [IOT Instruction Detail](../02-isa/04-iot.md)
- [Group 2 OPR Encoding Model](../02-isa/02-group-2.md)
- [MRI Execution](../03-microarchitecture/05-mri-execution.md)
- [IOT Execution](../03-microarchitecture/06-iot-execution.md)
- [Group 2 Execution](../03-microarchitecture/07-opr/02-group2-execution.md)
- [Interrupt Execution](../03-microarchitecture/08-interrupt-execution.md)
- [Derived Flags](../04-control/10-control-input-definitions/03-derived-flags.md)
- [External Inputs](../04-control/10-control-input-definitions/04-external-inputs.md)
- [Controller Contract](../07-io/04-controller-contract.md)
- [DMA Arbitration](../07-io/06-dma-arbitration.md)
- [Controller Documentation](../07-io/10-controllers/README.md)
- [Major State Timing](../09-timing/03-major-state-timing.md)

These documents remain authoritative for their respective definitions.
