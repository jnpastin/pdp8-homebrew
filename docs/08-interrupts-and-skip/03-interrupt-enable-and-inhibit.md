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
- interrupt inhibition across the CIF/RMF/RTF-to-JMP/JMS interval
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
- The [instruction-completion TP4](../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#311-instruction-completion) boundary of ION cannot recognize an interrupt because `II` remains set.
- During FETCH of the following instruction, `II` is cleared at TP1 only if no deferred instruction-field change is pending (`CIFP = 0`).
- The following instruction executes before interrupt recognition may occur at its instruction-completion TP4 boundary.

This produces the required one-instruction recognition delay after ION.

The delay does not prevent:

- interrupting controllers from asserting requests
- `/INT_REQ` from remaining asserted
- DMA recognition at an eligible instruction-completion TP4 boundary

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

## 8. System Initialization

On system initialization (CAF, front-panel CLEAR, or power-on reset):
- IE is cleared
- II is unchanged
- CIFP is unchanged

Clearing IE prevents interrupt recognition without canceling a pending deferred instruction-field change.  
/INITIALIZE does not acknowledge or clear a controller interrupt condition except through the initialized-state behavior defined by that controller.

The authoritative signal behavior is defined in [System Initialization](../04-control/20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize).

## 9. SKON Behavior

SKON tests the pre-operation interrupt-enable state and then disables interrupts.

Its instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md#3-device-0---processor-iots), and its execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md#93-ir119--110-and-ioa--00-and-ir20--000).

SKON:

- clears `IE`
- does not test `/INT_REQ`
- does not acknowledge or clear a controller interrupt request

The skip decision and `IE` clear use the same pre-TP state and commit at the same TP. The cleared `IE` value must not affect the skip decision committed at that TP.

## 10. CIF Inhibit Behavior

CIF stages a deferred instruction-field change and inhibits interrupt recognition until that field change is applied.

CIF:

- loads the requested field into `DIF`
- sets `CIFP`
- sets `II`


The instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md), and the execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

While `CIFP` remains set:

- FETCH TS1 does not clear `II`
- interrupt recognition remains inhibited
- the deferred field value remains pending for application by the next JMP or JMS

This preserves the CIF-to-branch sequence as an uninterrupted control-transfer interval.

## 11. RMF Inhibit Behavior

RMF restores the saved memory-field context and establishes the same deferred instruction-field protection used by CIF.

RMF:

- restores the saved `DF` from `IB`
- stages the saved `IF` from `IB` in `DIF`
- sets `CIFP`
- sets `II`

While `CIFP` remains set:

- FETCH TS1 does not clear `II`
- interrupt recognition remains inhibited
- the saved instruction field remains pending for application by the next JMP or JMS

The instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md), and the execution sequence is defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

RMF and CIF use the same pending-field and interrupt-inhibit mechanism. They differ only in the source and associated field behavior:

- CIF stages the instruction field from the current instruction.
- RMF restores `DF` and stages the saved instruction field from `IB`.

### 11.1 RTF Inhibit Behavior
  
RTF restores processor state from the processor flags word and establishes the same deferred instruction-field protection used by CIF and RMF.

RTF:
- restores L from AC[11]
- restores DF from AC[2:0]
- stages the restored IF from AC[5:3] in DIF
- sets CIFP
- sets II
- sets IE

While CIFP remains set:
- FETCH TS1 does not clear II
- interrupt recognition remains inhibited
- the restored instruction field remains pending for application by the next JMP or JMS

RTF sets IE regardless of AC[7], matching the defined PDP-8/E behavior. Setting IE does not permit immediate interrupt recognition because RTF also sets II and CIFP.

The instruction-level behavior is defined in [IOT Instruction Detail](../02-isa/04-iot.md#312-rtf), and defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md#96-ir119--110-and-ioa--00-and-ir20--101).

## 12. Deferred Field Application

The pending instruction-field change is applied by the next JMP or JMS.

At that operation:

- `DIF` is transferred to `IF` when the defined field-change condition is satisfied
- `CIFP` is cleared
- `II` is cleared

The JMP execution sequences are defined in [Fetch & Defer](../03-microarchitecture/04-fetch-defer.md) (a JMP completes in FETCH or DEFER), and the JMS sequence in [MRI Execution](../03-microarchitecture/05-mri-execution.md).

When each commits:

| Instruction | `II` cleared | `IF` loaded and `CIFP` cleared | Instruction completes |
|---|---|---|---|
| Direct JMP | FETCH TP3 | FETCH TP4 | FETCH TP4 |
| JMP I | DEFER TP3 | DEFER TP4 | DEFER TP4 |
| JMS | EXECUTE TP1 | EXECUTE TP1 | EXECUTE TP4 |

Both JMPs load the field at the TP4 that completes them. A JMP I could not load it sooner: the auto-index write-back of its pointer, in DEFER TS4, still uses the old field ([Fetch & Defer §4.5](../03-microarchitecture/04-fetch-defer.md#45-ts4)). In every case `II` is clear before the instruction's completion, so interrupt recognition may occur at the instruction-completion TP4 of that same JMP or JMS if all eligibility conditions are satisfied. The interrupt entry then saves the new instruction field in `IB` and the transfer address (JMP) or the address after the return-address word (JMS) in location `0000`, so no field change is lost.

The JMP timing matches the PDP-8/E (KM8-E Memory Extension, Theory of Operation):

- The KM8-E negates its interrupt inhibit "at TP3 whenever a JMP or JMS instruction occurs" (§2.10.1).
- It loads IF at the TP4 of FETCH for a direct JMP or JMS, and of DEFER for an indirect one (§2.10.3).
- MAINDEC-8E-D1HA checks that the interrupt follows the field-changing JMP.

A JMS differs: it clears `II` and loads IF at EXECUTE TP1, one TP after the KM8-E's TP4. No program can see the difference, because nothing between those TPs uses IF or II. Matching it would need the control store to recognize a JMS in FETCH and DEFER, which `IR_CLASS` does not ([IR-Derived Fields](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_class)).

## 13. Inhibit Clearing in FETCH TS1

FETCH TS1 clears `II` only when `CIFP` is clear. A direct JMP also clears it in FETCH TS3 when `CIFP` is set, as it applies the pending field (section 12).

The FETCH execution rule is defined in [Fetch and Defer](../03-microarchitecture/04-fetch-defer.md#31-ts1).

This conditional clear serves two distinct cases:

- after ION, `CIFP` is clear, so `II` is cleared during the FETCH of the instruction following ION
- after CIF, RMF, or RTF, `CIFP` is set, so `II` remains set until the pending field change is applied

FETCH-time inhibit clearing does not:

- modify `IE`
- modify `/INT_REQ`
- acknowledge an interrupting controller
- itself recognize an interrupt

## 14. Combined ION, CIF, RMF, and RTF Effects
  
II may be set by ION, CIF, RMF, or RTF.  
The architectural effect depends on CIFP:
- when CIFP is clear, FETCH TS1 clears II
- when CIFP is set, FETCH TS1 preserves II until a JMP or JMS clears it (section 12)
  
No separate source identifier is stored for II.  
The required behavior is determined by the committed II and CIFP state rather than by remembering which instruction originally set II.

## 15. Relationship to DMA

`IE`, `II`, and `CIFP` govern interrupt eligibility only.

They do not enable, inhibit, prioritize, acknowledge, or cancel DMA requests.

Therefore, DMA may be selected at an eligible instruction-completion TP4 boundary while interrupt recognition is prevented by:

- `IE` being clear
- `II` being set
- a CIF-, RMF-, or RTF-established deferred instruction-field inhibit interval

When an interrupt is valid at the same instruction-completion TP4 boundary as DMA, the precedence rule is defined in [Interrupt Recognition and Sequencing](./02-interrupt-recognition-and-sequencing.md#7-interrupt-precedence-over-dma).

## 16. Invariants
  
The following invariants apply:
- IE and II represent distinct interrupt-control functions.
- IE globally enables or disables interrupt eligibility.
- II temporarily prevents recognition without clearing IE.
- Neither IE nor II clears or acknowledges a controller request.
- ION sets both IE and II.
- The instruction following ION executes before an interrupt may be recognized.
- IOF clears IE without clearing controller requests.
- SKON tests the pre-TP IE state and clears IE at the same TP.
- CIF, RMF, and RTF set II and CIFP.
- FETCH TS1 must not clear II while CIFP is set.
- START clears II and leaves CIFP set. This is harmless: START also clears IE, and ION sets II again before interrupts can be enabled, after which FETCH TS1 does not clear it while CIFP is set. The pending field is still applied by the next JMP or JMS, as on the PDP-8/E, whose next JMP or JMS loads IF from its instruction buffer.
- A pending instruction-field change established by CIF, RMF, or RTF inhibits interrupt recognition until JMP or JMS applies the deferred field.
- A JMP or JMS that applies a pending instruction-field change clears II and CIFP and loads IF at the TPs in section 12. Interrupt recognition may occur at that instruction's completion TP4.
- Interrupt recognition after a deferred field change may occur at the completion TP4 of the JMP or JMS that applies it, or at a later eligible one.
- Interrupt enable and inhibit state do not control DMA eligibility.
- All changes to IE, II, and CIFP occur only at TP events.
- All same-TP decisions use pre-TP state.
- CIF, RMF, and RTF use the same deferred instruction-field protection mechanism.

## 17. Summary
  
IE provides global interrupt enable, while II provides temporary recognition inhibition.  
ION sets both states, permitting the following instruction to execute before interrupt recognition. IOF clears global interrupt enable. SKON tests and clears interrupt enable. CIF, RMF, and RTF set II and CIFP, preserving the inhibit until the deferred instruction-field change is applied by JMP or JMS.  
These states affect interrupt eligibility only. They do not acknowledge controller requests or control DMA eligibility.