# Interrupt Enable and Inhibit

## 1. Purpose

This document defines the relationships among:

- interrupt enable state
- interrupt inhibit state
- deferred instruction-field changes
- CPU-internal interrupt-control instructions
- interrupt eligibility

The individual registers, instructions, micro-operations, and control inputs are defined in their owning documents and are not redefined here.

## 2. Scope

This document defines:

- the distinct roles of `IE` and `II`
- the relationship between `II` and `CIFP`
- the interrupt-recognition delay following ION
- interrupt inhibition across the CIF-to-JMP/JMS interval
- the interrupt-related effects of IOF and SKON
- the conditions under which interrupt recognition becomes eligible

This document does not define:

- register implementation
- instruction encoding
- micro-operation implementation
- control-word encoding
- interrupt-entry execution
- controller interrupt conditions
- interrupt-source priority
- interrupt-service-routine behavior

## 3. Interrupt Enable State

`IE` is the global interrupt-enable state.

When `IE` is clear, an asserted aggregate `/INT_REQ` does not make an interrupt eligible for recognition.

When `IE` is set, interrupt recognition remains subject to:

- interrupt-inhibit state
- aggregate interrupt-request state
- the defined recognition boundary

The register definition for `IE` is provided by the [Register Model Specification](../01-architecture/01-registers.md#ie--interrupt-enable).

## 4. Interrupt Inhibit State

`II` prevents interrupt recognition while set.

`II` does not:

- clear `IE`
- clear or acknowledge `/INT_REQ`
- modify a controller interrupt condition
- prevent a controller from asserting its interrupt contribution
- prevent DMA recognition
- identify an interrupting controller

The register definition for `II` is provided by the [Register Model Specification](../01-architecture/01-registers.md#ii--interrupt-inhibit).

## 5. Interrupt Eligibility

Interrupt eligibility requires all of the following:

- interrupts are enabled
- interrupt recognition is not inhibited
- aggregate `/INT_REQ` is asserted

The complete derived condition is defined by [Interrupt Request Valid](../04-control/10-control-input-definitions/03-derived-flags.md#interrupt_request_valid).

Satisfying the eligibility condition does not itself cause an asynchronous state change. The condition participates in the next eligible recognition decision defined by [Interrupt Recognition and Sequencing](./02-interrupt-recognition-and-sequencing.md).

## 6. ION Behavior

ION enables interrupts and establishes a temporary interrupt inhibit.

Its instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md), and its execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

The relationship among the affected states is:
- ION sets `IE`.
- The EXECUTE TP4 boundary of ION cannot recognize an interrupt because `II` remains set.
- During FETCH of the following instruction, `II` is cleared at TP1 only if no deferred instruction-field change is pending (`CIFP = 0`).
- The following instruction executes before interrupt recognition may occur at its EXECUTE TP4 boundary.

This produces the required one-instruction recognition delay after ION.

The delay does not prevent:

- interrupting controllers from asserting requests
- `/INT_REQ` from remaining asserted
- DMA recognition at an eligible EXECUTE TP4 boundary

## 7. IOF Behavior

IOF clears `IE`.

Its instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md#3-device-0---processor-iots), and its execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

After `IE` is cleared, an asserted `/INT_REQ` does not produce `INTERRUPT_REQUEST_VALID`.

IOF does not:

- clear `II`
- clear `/INT_REQ`
- acknowledge an interrupting controller
- clear any controller interrupt condition
- affect DMA eligibility

## 8. SKON Behavior

SKON tests the pre-operation interrupt-enable state and then disables interrupts.

Its instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md#3-device-0---processor-iots), and its execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md#93-ir119--110-and-ioa--00-and-ir20--000).

- clears `IE`
- does not test `/INT_REQ`
- does not acknowledge or clear a controller interrupt request

The skip decision and `IE` clear use the same pre-TP state and commit at the same TP. The cleared `IE` value must not affect the skip decision committed at that TP.

## 9. CIF Inhibit Behavior

CIF stages a deferred instruction-field change and inhibits interrupt recognition until that field change is applied.

CIF:

- loads the requested field into `DIF`
- sets `CIFP`
- sets `II`


The instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md), and the execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

While `CIFP` remains set:

- FETCH does not clear `II`
- interrupt recognition remains inhibited
- the deferred field value remains pending for application by the next JMP or JMS

This preserves the CIF-to-branch sequence as an uninterrupted control-transfer interval.

## 10. RMF Inhibit Behavior

RMF restores the saved memory-field context and establishes the same deferred instruction-field protection used by CIF.

RMF:

- restores the saved `DF` from `IB`
- stages the saved `IF` from `IB` in `DIF`
- sets `CIFP`
- sets `II`

While `CIFP` remains set:

- FETCH does not clear `II`
- interrupt recognition remains inhibited
- the saved instruction field remains pending for application by the next JMP or JMS

The instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md), and the execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

RMF and CIF use the same pending-field and interrupt-inhibit mechanism. They differ only in the source and associated field behavior:

- CIF stages the instruction field from the current instruction.
- RMF restores `DF` and stages the saved instruction field from `IB`.

## 11. Deferred Field Application

The pending instruction-field change is applied by the next JMP or JMS.

At that operation:

- `DIF` is transferred to `IF` when the defined field-change condition is satisfied
- `CIFP` is cleared
- `II` remains governed by its existing update rules

The JMP and JMS execution sequences are defined in [MRI Execution](../03-microarchitecture/05-mri-execution.md).

Application of the pending field change does not permit an interrupt to be recognized at the same TP4 boundary. The recognition decision uses the pre-TP4 state, in which `II` remains set.

During the following FETCH, `CIFP` is clear, so the defined FETCH behavior may clear `II`. Interrupt recognition may then occur at the EXECUTE TP4 boundary of the instruction fetched in the new instruction field if all eligibility conditions are satisfied.

## 12. FETCH-Time Inhibit Clearing

FETCH clears `II` only when `CIFP` is clear.

The FETCH execution rule is defined in [Fetch and Defer](../03-microarchitecture/04-fetch-defer.md#31-ts1).

This conditional clear serves two distinct cases:

- after ION, `CIFP` is clear, so `II` is cleared during the FETCH of the instruction following ION
- after CIF or RMF, `CIFP` is set, so `II` remains set until the pending field change is applied

FETCH-time inhibit clearing does not:

- modify `IE`
- modify `/INT_REQ`
- acknowledge an interrupting controller
- itself recognize an interrupt

## 13. Combined ION and CIF Effects

`II` may be set by either ION, CIF or RMF.

The architectural effect depends on `CIFP`:

- when `CIFP` is clear, FETCH may clear `II`
- when `CIFP` is set, FETCH preserves `II`

No separate source identifier is stored for `II`.

The required behavior is determined by the committed `II` and `CIFP` state rather than by remembering which instruction originally set `II`.

## 14. Relationship to DMA

`IE`, `II`, and `CIFP` govern interrupt eligibility only.

They do not enable, inhibit, prioritize, acknowledge, or cancel DMA requests.

Therefore, DMA may be selected at an eligible EXECUTE TP4 boundary while interrupt recognition is prevented by:

- `IE` being clear
- `II` being set
- the CIF-to-JMP/JMS inhibit interval

When an interrupt is valid at the same EXECUTE TP4 boundary as DMA, the precedence rule is defined in [Interrupt Recognition and Sequencing](./02-interrupt-recognition-and-sequencing.md#7-interrupt-precedence-over-dma).

## 15. Invariants

The following invariants apply:

- `IE` and `II` represent distinct interrupt-control functions.
- `IE` globally enables or disables interrupt eligibility.
- `II` temporarily prevents recognition without clearing `IE`.
- Neither `IE` nor `II` clears or acknowledges a controller request.
- ION sets both `IE` and `II`.
- The instruction following ION executes before an interrupt may be recognized.
- IOF clears `IE` without clearing controller requests.
- SKON tests the pre-TP `IE` state and clears `IE` at the same TP.
- CIF sets `II` and `CIFP`.
- FETCH must not clear `II` while `CIFP` is set.
- A pending CIF inhibits interrupt recognition until its JMP or JMS applies the deferred field.
- Clearing `CIFP` and applying `DIF` at JMP or JMS does not permit interrupt recognition at that same TP4.
- Interrupt recognition after a deferred field change may occur only at a later eligible EXECUTE TP4 boundary.
- Interrupt enable and inhibit state do not control DMA eligibility.
- All changes to `IE`, `II`, and `CIFP` occur only at TP events.
- All same-TP decisions use pre-TP state.
- RMF sets `II` and `CIFP`.
- RMF uses the same deferred instruction-field protection mechanism as CIF.
- FETCH must not clear `II` while an RMF-restored instruction field remains pending.

## 16. Summary

`IE` provides global interrupt enable, while `II` provides temporary recognition inhibition.

ION sets both states, permitting the following instruction to execute before interrupt recognition. IOF clears global interrupt enable. SKON tests and clears interrupt enable. CIF sets `II` and `CIFP`, preserving the inhibit until the deferred field change is applied by JMP or JMS.

These states affect interrupt eligibility only. They do not acknowledge controller requests or control DMA eligibility.