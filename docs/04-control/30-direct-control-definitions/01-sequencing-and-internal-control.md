# Sequencing and Internal Direct Control

## 1. Purpose

This document defines direct-control results for:

- major-state sequencing
- run-state sequencing
- halt-request sequencing
- CPU memory-context selection
- control-provided internal values

Direct-control scope, composition, and representation are defined in the [Direct Control Model](../07-direct-control-model.md).

Signal meanings and encodings remain defined by the [Control Output Definitions](../20-control-output-definitions/00-index.md).

This document does not redefine:

- micro-operations
- micro-operation mappings
- control inputs
- derived outputs
- external input values
- physical interface ownership
- externally visible output-drive states

Physical interface ownership and output-drive states are defined separately in [Interface and Ownership Control](./02-interface-and-ownership-control.md).

---

## 2. Source and Representation Rules

Each definition in this document identifies:

- the result being defined
- the control inputs or documented execution context that select the result
- fixed control-output assignments
- control-input-to-output value bindings
- associated micro-operations, if applicable
- timing and commit behavior
- constraints
- authoritative sources

The following forms are used:

Fixed assignment:

```text
OUTPUT = VALUE
```

Input-value binding:

```text
OUTPUT = INPUT
```

A binding represents direct value propagation. It does not imply a transformation.

Behavior not explicitly defined by the authoritative documentation remains unresolved.

---

## 3. Sequencing Control

### 3.1 General Sequencing Rules

The sequencing outputs are:

- `MS_NEXT`
- `RUN_NEXT`
- `HLT_REQ_NEXT`

These outputs:

- originate from the control word
- are explicit next-state values
- are not micro-operations
- are not modified by micro-operations
- commit only at their documented TP boundaries
- must not be computed or modified outside the control store

Current state and next-state value remain distinct:

```text
MS       -> current major state
MS_NEXT  -> next major-state value

RUN      -> current run state
RUN_NEXT -> next run-state value

HLT_REQ      -> current halt-request state
HLT_REQ_NEXT -> next halt-request value
```

Related definitions:

- [Sequencing Control Signals](../20-control-output-definitions/03-sequencing-control-signals.md)
- [Major State Model](../../03-microarchitecture/00-state-model.md)
- [Control Constraints](../03-control-constraints.md)

---

### 3.2 Next Major State

#### 3.2.1 Result

`MS_NEXT` specifies the next major state.

Encoding:

```text
FETCH     = 0
DEFER     = 1
EXECUTE   = 2
INTERRUPT = 3
DMA       = 4
```

`MS_NEXT` is evaluated during TS4 and committed at TP4.

It must be explicitly defined for every major state at TS4.

Outside TS4, `MS_NEXT` does not modify `MS`.

Source:

- [Sequencing Control Signals](../20-control-output-definitions/03-sequencing-control-signals.md#41-next-major-state-ms_next)

---

#### 3.2.2 FETCH Transition Without Indirection

Applicable context:

```text
MS = FETCH
TS = 4
IR_INDIRECT = 0
```

Assignment:

```text
MS_NEXT = EXECUTE
```

Commit:

```text
MS <- EXECUTE at TP4
```

Source:

- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)

---

#### 3.2.3 FETCH Transition With Indirection

Applicable context:

```text
MS = FETCH
TS = 4
IR_INDIRECT = 1
```

Assignment:

```text
MS_NEXT = DEFER
```

Commit:

```text
MS <- DEFER at TP4
```

Source:

- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)

---

#### 3.2.4 DEFER Completion

Applicable context:

```text
MS = DEFER
TS = 4
```

Assignment:

```text
MS_NEXT = EXECUTE
```

Commit:

```text
MS <- EXECUTE at TP4
```

Source:

- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)

---

#### 3.2.5 EXECUTE Completion With Valid Interrupt

Applicable context:

```text
MS = EXECUTE
TS = 4
INTERRUPT_REQUEST_VALID = 1
```

Assignment:

```text
MS_NEXT = INTERRUPT
```

Commit:

```text
MS <- INTERRUPT at TP4
```

Source:

- [Derived Flags](../10-control-input-definitions/03-derived-flags.md#interrupt_request_valid)
- [Interrupt Recognition & Sequencing](../../08-interrupts-and-skip/02-interrupt-recognition-and-sequencing.md)
- [Sequencing Control Signals](../20-control-output-definitions/03-sequencing-control-signals.md)

---

#### 3.2.6 EXECUTE Completion With DMA Request

Applicable context:

```text
MS = EXECUTE
TS = 4
INTERRUPT_REQUEST_VALID = 0
/DMA_REQ = 0
```

Assignment:

```text
MS_NEXT = DMA
```

Commit:

```text
MS <- DMA at TP4
```

Constraints:

- The interrupt decision has priority over DMA entry.
- `/DMA_REQ` must be established before TS4.
- DMA entry must be selected through the control word.
- The DMA arbiter does not modify `MS_NEXT`.

Sources:

- [DMA Arbitration](../../07-io/06-dma-arbitration.md)
- [DMA Interface](../../07-io/05-dma-interface.md)
- [Sequencing Control Signals](../20-control-output-definitions/03-sequencing-control-signals.md)

---

#### 3.2.7 EXECUTE Completion Without Interrupt or DMA

Applicable context:

```text
MS = EXECUTE
TS = 4
INTERRUPT_REQUEST_VALID = 0
/DMA_REQ = 1
```

Assignment:

```text
MS_NEXT = FETCH
```

Commit:

```text
MS <- FETCH at TP4
```

Sources:

- [Interrupt Recognition & Sequencing](../../08-interrupts-and-skip/02-interrupt-recognition-and-sequencing.md)
- [Sequencing Control Signals](../20-control-output-definitions/03-sequencing-control-signals.md)

---

#### 3.2.8 INTERRUPT Completion

Applicable context:

```text
MS = INTERRUPT
TS = 4
```

Assignment:

```text
MS_NEXT = FETCH
```

Commit:

```text
MS <- FETCH at TP4
```

Source:

- [Interrupt Execution](../../03-microarchitecture/08-interrupt-execution.md)

---

#### 3.2.9 DMA Continuation

Applicable context:

```text
MS = DMA
TS = 4
/DMA_REQ = 0
```

Assignment:

```text
MS_NEXT = DMA
```

Commit:

```text
MS <- DMA at TP4
```

Constraints:

- `/DMA_REQ` is the aggregate CPU-facing request.
- The request value used by CPU control must settle before TP4.
- DMA continuation must be selected through the control word.
- External DMA ownership must not modify `MS_NEXT`.

Sources:

- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)

---

#### 3.2.10 DMA Exit

Applicable context:

```text
MS = DMA
TS = 4
/DMA_REQ = 1
```

Assignment:

```text
MS_NEXT = FETCH
```

Commit:

```text
MS <- FETCH at TP4
```

Constraints:

- The selected controller and arbiter prepare release decisions before TP4.
- CPU ownership resumes in the following FETCH TS1.
- CPU and DMA ownership must not overlap.

Sources:

- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)

---

### 3.3 Run-State Sequencing

#### 3.3.1 Result

`RUN_NEXT` specifies the next value of `RUN`.

Encoding:

```text
0 = processor halted
1 = processor running
```

`RUN_NEXT`:

- is defined in every control word
- is evaluated as part of the control word
- is committed to `RUN` at TP
- is not computed outside the control store
- is not modified by micro-operations

State preservation requires an explicit value. Absence of a state transition does not permit omission of `RUN_NEXT`.

Source:

- [Sequencing Control Signals](../20-control-output-definitions/03-sequencing-control-signals.md#42-run-state-next-value-run_next)

---

#### 3.3.2 Continued Running

Applicable context:

```text
RUN = 1

AND

none of the following halt conditions applies at the current TP:

- a pending halt request is consumed at an instruction-completion boundary
- Single Instruction mode reaches an instruction-completion boundary
- Single Step mode reaches completion of the current major state
```

Assignment:

```text
RUN_NEXT = 1
```

Commit:

```text
RUN <- 1 at TP
```

Constraints:

- Preservation of the running state is explicit.
- `RUN_NEXT = 1` must not be inferred from the field default.
- Single Instruction mode does not halt before instruction completion.
- Single Step mode does not halt before completion of the current major state.
- Execution never halts in the middle of a major state.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md)

---

#### 3.3.3 Start

Applicable context:

```text
RUN = 0
FP_START = 1
the START command is accepted
```

Assignments:

```text
RUN_NEXT = 1
MS_NEXT  = FETCH
```

Commit:

```text
RUN <- 1 at TP
```

START also establishes the documented processor execution state and begins execution in FETCH at the first timing state.

The START micro-operations are separate from the `RUN_NEXT` and `MS_NEXT` assignments.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#10-start-operation)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md)

---

#### 3.3.4 Continue

Applicable context:

```text
RUN = 0
FP_CONTINUE = 1
the CONTINUE command is accepted
FP_START = 0
```

Assignment:

```text
RUN_NEXT = 1
```

Commit:

```text
RUN <- 1 at TP
```

CONTINUE resumes execution from the preserved machine state without executing architectural micro-operations or modifying the documented preserved state.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#11-continue-operation)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md)

---

#### 3.3.5 START and CONTINUE Priority

START and CONTINUE are meaningful only while the processor is halted.

If both commands are accepted in the same control case:

```text
START takes priority over CONTINUE.
```

The complete START behavior is selected:

```text
RUN_NEXT = 1
MS_NEXT  = FETCH
```

The START micro-operations are selected, and CONTINUE behavior is not selected.

This priority prevents simultaneous commands from partially preserving and partially reinitializing processor state.

This is a defined project behavior.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#11-continue-operation)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md)

---

#### 3.3.6 Pending-Halt Consumption

Applicable context:

```text
RUN = 1
HLT_REQ = 1
the current TP is an instruction-completion boundary
```

Assignments:

```text
RUN_NEXT     = 0
HLT_REQ_NEXT = 0
```

Commit:

```text
RUN     <- 0 at TP
HLT_REQ <- 0 at TP
```

Constraints:

- A pending STOP or HLT request is consumed only at an instruction-completion boundary.
- Consumption transitions the processor to the halted state.
- Consumption clears the pending halt request at the same TP.
- `RUN_NEXT` and `HLT_REQ_NEXT` are derived from the current committed `HLT_REQ` value.
- A new halt request must be committed before the instruction-completion decision that consumes it.

Sources:

- [Registers](../../01-architecture/01-registers.md)
- [Console Execution](../../03-microarchitecture/09-console-execution.md)

---

#### 3.3.7 Single Instruction Halt

Applicable context:

```text
RUN = 1
FP_SINGLE_INSTRUCTION = 1
the current TP completes the instruction
```

Assignment:

```text
RUN_NEXT = 0
```

Commit:

```text
RUN <- 0 at TP
```

Instruction completion occurs after the final major state associated with the instruction.

Examples of complete instruction paths include:

```text
FETCH -> EXECUTE
```

and:

```text
FETCH -> DEFER -> EXECUTE
```

Constraints:

- Single Instruction mode executes one complete instruction.
- It does not modify instruction behavior.
- It changes only when execution halts.
- It must not halt after FETCH when DEFER or EXECUTE remains part of the current instruction.
- If `HLT_REQ = 1` at instruction completion, the pending halt request is consumed and `HLT_REQ_NEXT = 0`.
- If no halt request is pending, Single Instruction mode does not create one.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#12-single-instruction-mode)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md)

---

#### 3.3.8 Single Step Halt

Applicable context:

```text
RUN = 1
FP_SINGLE_STEP = 1
TS = 4
```

Assignment:

```text
RUN_NEXT = 0
```

Commit:

```text
RUN <- 0 at TP4
```

Single Step executes one major state and halts after TS4 of that major state.

The documented individually stepped major states are:

- FETCH
- DEFER
- EXECUTE
- INTERRUPT

Constraints:

- Single Step mode does not initiate execution.
- Single Step mode does not modify the behavior of the major state being executed.
- Execution does not halt before completion of TS4.
- Resumption requires START or CONTINUE.
- Single Step does not create a pending halt request.
- If `HLT_REQ = 1` and the Single Step boundary is not an instruction-completion boundary, `HLT_REQ_NEXT = 1`.
- If `HLT_REQ = 1` and the Single Step boundary is also an instruction-completion boundary, the pending halt request is consumed and `HLT_REQ_NEXT = 0`.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md)

---

#### 3.3.9 Run-State Case Summary

The `RUN_NEXT` results are:

```text
Condition                                                     RUN_NEXT
------------------------------------------------------------  --------
Accepted START while halted                                   1
Accepted CONTINUE while halted and START is not accepted      1
Running with no applicable halt condition                     1
Halted with no accepted START or CONTINUE                     0
Pending halt consumed at instruction completion               0
Single Instruction reaches instruction completion             0
Single Step reaches completion of the current major state     0
```

When START and CONTINUE are accepted together:

```text
START takes priority.
```

When multiple halt conditions apply at the same TP, they agree on:

```text
RUN_NEXT = 0
```

The applicable `HLT_REQ_NEXT` result is defined separately by halt-request sequencing.

---

### 3.4 Halt-Request Sequencing

#### 3.4.1 Result

`HLT_REQ_NEXT` specifies the next value of `HLT_REQ`.

Encoding:

```text
0 = no halt request pending
1 = halt request pending
```

`HLT_REQ_NEXT`:

- is defined in every control word
- is evaluated as part of the control word
- is committed to `HLT_REQ` at TP
- is not computed outside the control store
- is not modified by micro-operations

`HLT_REQ` records a pending STOP or HLT request. It is separate from the `RUN` state.

Sources:

- [Sequencing Control signals](../20-control-output-definitions/03-sequencing-control-signals.md#43-halt-request-next-value-hlt_req_next)
- [Registers](../../01-architecture/01-registers.md)

---

#### 3.4.2 No Pending Halt

Applicable context:

```text
HLT_REQ = 0
no STOP request is accepted
IR_OPR_HLT = 0
```

Assignment:

```text
HLT_REQ_NEXT = 0
```

Commit:

```text
HLT_REQ <- 0 at TP
```

Constraint:

- Preservation of the clear state is explicit.

---

#### 3.4.3 STOP Request Capture

A synchronized STOP request is captured at a TP before the instruction-completion TP.

Applicable context:

```text
FP_STOP = 1
the STOP command is accepted
the current TP precedes the instruction-completion TP
```

Assignment:

```text
HLT_REQ_NEXT = 1
```

Commit:

```text
HLT_REQ <- 1 at TP
```

Constraints: 

- The STOP request affects an instruction-completion decision only after the request has committed to `HLT_REQ`.
- A request committed before the applicable instruction-completion TP is available to that decision.
- A request not committed before the applicable instruction-completion TP does not affect that decision.
- A request committed after that decision remains pending until the next instruction-completion boundary.
- Consumption of the committed request is defined separately by [Pending-Halt Consumption](#346-pending-halt-consumption).

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md)
- [External Inputs](../10-control-input-definitions/04-external-inputs.md)

---

#### 3.4.4 HLT Instruction Request Capture

Applicable context:

```text
MS = EXECUTE
TS = 3
IR_OPR_HLT = 1
```

Assignment:

```text
HLT_REQ_NEXT = 1
```

Commit:

```text
HLT_REQ <- 1 at TP3
```

Constraints:

- The request committed at TP3 is available as `HLT_REQ = 1` to the subsequent EXECUTE TP4 control decision.
- This definition covers only capture of the HLT request.
- The subsequent run-state transition and request consumption are defined separately by [Pending-Halt Consumption](#346-pending-halt-consumption).
- Request capture is independent of whether normal running, Single Instruction mode, or Single Step mode is active.

Sources:

- [Group 2 Execution](../../03-microarchitecture/07-opr/02-group2-execution.md)
- [IR-Derived Control Inputs](../10-control-input-definitions/02-ir-derived-fields.md)
- [Console Execution](../../03-microarchitecture/09-console-execution.md)

---

#### 3.4.5 Pending-Halt Preservation

Applicable context:

```text
HLT_REQ = 1
the current TP is not an instruction-completion boundary
```

Assignment:

```text
HLT_REQ_NEXT = 1
```

Commit:

```text
HLT_REQ <- 1 at TP
```

Constraints:

- A pending halt request remains set until consumed.
- The request must not be cleared during an intermediate TS or major-state boundary.
- Preservation of the pending state is explicit.
- A Single Step halt at a boundary that is not instruction completion does not consume the pending request.

Sources:

- [Registers](../../01-architecture/01-registers.md)
- [Console Execution](../../03-microarchitecture/09-console-execution.md)

---

#### 3.4.6 Pending-Halt Consumption

Applicable context:

```text
HLT_REQ = 1
the current TP is an instruction-completion boundary
```

Assignments:

```text
RUN_NEXT     = 0
HLT_REQ_NEXT = 0
```

Commit:

```text
RUN     <- 0 at TP
HLT_REQ <- 0 at TP
```

Constraints:

- The halt request is cleared only when consumed.
- Consumption and transition to the halted state commit at the same TP.
- Consumption applies regardless of whether another run-state halt condition also applies at that boundary.
- Single Instruction completion and EXECUTE Single Step completion do not prevent consumption of an existing pending halt request.
- A `HLT_REQ_NEXT = 1` value committed at the current TP is not available as `HLT_REQ = 1` for another decision at that same TP.

Sources:

- [Registers](../../01-architecture/01-registers.md)
- [Console Execution](../../03-microarchitecture/09-console-execution.md)

---

#### 3.4.7 Relationship to Single Instruction

Single Instruction mode determines `RUN_NEXT` at the instruction-completion boundary as defined by [Single Instruction Halt](#337-single-instruction-halt).

If `HLT_REQ = 1` at that boundary, the pending request is consumed according to [Pending-Halt Consumption](#346-pending-halt-consumption).

Single Instruction mode does not create a pending halt request and does not alter the pending-halt consumption rules.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#12-single-instruction-mode)

#### 3.4.8 Relationship to Single Step

Single Step mode determines `RUN_NEXT` at completion of the current major state as defined by [Single Step Halt](#338-single-step-halt).

If the completed major state is not the final major state of the instruction, an existing pending halt request is preserved according to [Pending-Halt Preservation](#345-pending-halt-preservation).

If the completed major state is the final major state of the instruction, an existing pending halt request is consumed according to [Pending-Halt Consumption](#346-pending-halt-consumption).

Single Step mode does not create a pending halt request and does not alter the pending-halt preservation or consumption rules.

Sources:

- [Console Execution](../../03-microarchitecture/09-console-execution.md)

---

#### 3.4.9 Halt-Request Case Summary

The `HLT_REQ_NEXT` results are:

```text
Condition                                                         HLT_REQ_NEXT
----------------------------------------------------------------  ------------
No pending or newly accepted halt request                         0
STOP captured before the applicable instruction-completion TP     1
HLT instruction executed at EXECUTE TP3                           1
Pending request before instruction completion                     1
Pending request at instruction completion                         0
Single Instruction halt with no pending request                   0
Single Instruction halt with a pending request                    0
Single Step at a non-instruction-completion boundary,
  with no pending request                                         0
Single Step at a non-instruction-completion boundary,
  with a pending request                                          1
Single Step at an instruction-completion boundary,
  with a pending request                                          0
```

The STOP and HLT request sequence is:

```text
request captured
    ->
HLT_REQ_NEXT = 1
    ->
HLT_REQ = 1
    ->
instruction-completion boundary
    ->
RUN_NEXT = 0
HLT_REQ_NEXT = 0
    ->
RUN = 0
HLT_REQ = 0
```

A STOP request captured too late for the current instruction-completion decision remains pending for the next instruction-completion boundary.

---

## 4. Memory-Context Selection

### 4.1 Address Bus Source

`AB_SRC` selects the source that drives the CPU address bus during CPU-owned memory operations.

The applicable encoding and electrical effect remain defined by the [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md).

The `AB_SRC` result must be selected independently from:

- `/RD`
- `/WR`
- `MDB_SRC`
- `MFB_SRC`

Selection of a memory micro-operation does not by itself define `AB_SRC`.

---

### 4.2 Program-Counter Address Context

Applicable context:

```text
the CPU owns the memory interface
the current memory operation uses PC as its address
```

Assignment:

```text
AB_SRC = PC
```

Constraints:

- This case applies to the documented instruction-fetch memory access.
- `AB_SRC` defines the address source independently from `/RD`, `/WR`, `MDB_SRC`, and `MFB_SRC`.

Sources:

- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)
- [Memory Field Selection](../../06-memory/05-memory-field-selection.md)

### 4.3 Memory-Address Register Context

Applicable context:

```text
the CPU owns the memory interface
the current memory operation uses MA as its address
```

Assignment:

```text
AB_SRC = MA
```

Constraints:

- This case applies only to documented memory operations for which `MA` drives `AB`.
- `AB_SRC` defines the address source independently from `/RD`, `/WR`, `MDB_SRC`, and `MFB_SRC`.

Sources:

- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)
- [MRI Execution](../../03-microarchitecture/05-mri-execution.md)
- [Interrupt Execution](../../03-microarchitecture/08-interrupt-execution.md)
- [Console Execution](../../03-microarchitecture/09-console-execution.md)

---

### 4.4 Memory Field Bus Source

`MFB_SRC` selects the CPU field register that drives `MFB` during CPU-owned memory operations.

Encoding:

```text
IF = 0
DF = 1
```

`MFB_SRC` governs the memory field only. It must remain distinct from:

- `AB_SRC`
- `MDB_SRC`
- `/RD`
- `/WR`
- physical ownership of `MFB`

During `MS = DMA`, the CPU does not drive `MFB`, and the encoded value of `MFB_SRC` does not determine the externally driven field value.

Sources:

- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Memory Field Selection](../../06-memory/05-memory-field-selection.md)
- [DMA Interface](../../07-io/05-dma-interface.md)

---

### 4.5 Memory Field Selection Rules

#### 4.5.1 Instruction Fetch

Applicable context:

```text
MS = FETCH
the CPU performs the instruction-fetch memory access
```

Assignment:

```text
MFB_SRC = IF
```

Source:

- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)

---

#### 4.5.2 Direct MRI Access

Applicable context:

```text
MS = EXECUTE
IR_IS_MRI = 1
IR_INDIRECT = 0
the current instruction performs a memory access
```

Assignment:

```text
MFB_SRC = IF
```

This applies to the documented memory access performed by a direct:

- AND
- TAD
- ISZ
- DCA
- JMS

JMP performs no memory access during EXECUTE.

Constraints:

- Direct MRI access never uses `DF`.
- The zero-page or current-page selection determines the 12-bit address within the field; it does not change the field source.
- `MFB_SRC` remains `IF` for both zero-page and current-page direct addressing.

Sources:

- [Addressing Model](../../02-isa/05-addressing-model.md)
- [MRI Execution](../../03-microarchitecture/05-mri-execution.md)

---

#### 4.5.3 Indirect Pointer Read

Applicable context:

```text
MS = DEFER
IR_IS_MRI = 1
IR_INDIRECT = 1
the CPU reads the indirect pointer
```

Assignment:

```text
MFB_SRC = IF
```

The pointer location is addressed within the instruction field.

Constraints:

- The indirect bit does not cause the pointer location itself to use `DF`.
- The zero-page or current-page selection determines the pointer address within `IF`.

Sources:

- [Addressing Model](../../02-isa/05-addressing-model.md)
- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)

---

#### 4.5.4 Indirect Autoindex Writeback

Applicable context:

```text
MS = DEFER
IR_IS_MRI = 1
IR_INDIRECT = 1
EAI = 1
the incremented pointer is written back to memory
```

Assignment:

```text
MFB_SRC = IF
```

The autoindex writeback updates the same pointer location that was read in the instruction field.

Constraints:

- Pointer read and autoindex writeback use the same field.
- Autoindex processing does not change the pointer-location field from `IF` to `DF`.

Sources:

- [Addressing Model](../../02-isa/05-addressing-model.md)
- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)

---

#### 4.5.5 Final Indirect MRI Access

Applicable context:

```text
MS = EXECUTE
IR_IS_MRI = 1
IR_INDIRECT = 1
the current instruction performs a memory access
```

Assignment:

```text
MFB_SRC = DF
```

This applies to the final resolved memory access performed by an indirect:

- AND
- TAD
- ISZ
- DCA
- JMS

JMP performs no memory access during EXECUTE.

Constraints:

- `DF` applies only to the final memory access after indirect address resolution.
- The indirect pointer read and any autoindex writeback remain in `IF`.
- The resolved 12-bit address is supplied separately from the field selection.
- `MFB_SRC = DF` does not alter the resolved address portion.

Sources:

- [Addressing Model](../../02-isa/05-addressing-model.md)
- [MRI Execution](../../03-microarchitecture/05-mri-execution.md)

---

#### 4.5.6 Interrupt Entry

Applicable context:

```text
MS = INTERRUPT
the return address is written to memory location 0000
```

Assignment:

```text
MFB_SRC = IF
```

Source:

- [Interrupt Execution](../../03-microarchitecture/08-interrupt-execution.md)

---

#### 4.5.7 Console Examine

Applicable context:

```text
RUN = 0
an EXAM command is accepted
```

Assignment:

```text
MFB_SRC = IF
```

The console operation reads memory at `IF:PC`.

Source:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#7-examine-operation)

---

#### 4.5.8 Console Deposit

Applicable context:

```text
RUN = 0
a DEPOSIT command is accepted
```

Assignment:

```text
MFB_SRC = IF
```

The console operation writes memory at `IF:PC`.

Source:

- [Console Execution](../../03-microarchitecture/09-console-execution.md#8-deposit-operation)

---

#### 4.5.9 DMA Ownership

Applicable context:

```text
MS = DMA
/DMA_GRANT is asserted
```

CPU behavior:

```text
CPU MFB driver = HIGH_Z
```

`MFB_SRC` may contain an encoded value in the control word, but that value does not drive `MFB` during DMA ownership.

The selected DMA controller supplies the memory field value.

Sources:

- [DMA & Console Access](../../06-memory/06-dma-and-console-access.md)
- [DMA Interface](../../07-io/05-dma-interface.md)

---

### 4.6 Memory Field Selection Summary

```text
Memory context                              MFB_SRC
------------------------------------------  -------------------
Instruction fetch                           IF
Direct MRI memory access                    IF
Indirect pointer read                       IF
Indirect autoindex writeback                IF
Final indirect MRI memory access            DF
Interrupt return-address write              IF
Console EXAM                                IF
Console DEPOSIT                             IF
DMA-owned memory access                     no CPU-driven value
```

For MRI instructions:

```text
IR_INDIRECT = 0:
    EXECUTE memory access uses IF

IR_INDIRECT = 1:
    DEFER pointer access uses IF
    DEFER autoindex writeback uses IF
    EXECUTE final memory access uses DF
```

The field-selection rule is independent of the MRI operation:

```text
AND
TAD
ISZ
DCA
JMS
```

Each memory-accessing MRI selects the field according to direct or indirect addressing.

JMP performs no memory access during EXECUTE and therefore requires no EXECUTE-stage `MFB_SRC` selection.

The summary applies only to documented memory operations.

`MFB_SRC` need not be interpreted as an active external field selection when no CPU-owned memory operation is occurring.

---

### 4.7 DMA Context

During `MS = DMA`:

- the CPU does not drive `MFB`
- the CPU does not drive `AB`
- `MFB_SRC` has no effect on the externally driven field value
- `AB_SRC` has no effect on the externally driven address value

The required physical output-drive states are defined in [Interface Ownership & Control](./02-interface-and-ownership-control.md).

Sources:

- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA & Console Access](../../06-memory/06-dma-and-console-access.md)

---

## 5. Control-Provided Internal Values

### 5.1 Data Field From Instruction

Applicable context:

```text
IR_WRITES_DF = 1
IR_DF_TO_DF is selected
```

Micro-operation assignments:

```text
DF_LOAD = 1
DF_SRC  = Control
```

Control-supplied value:

```text
DF_VAL = IR_DF
```

Value relationship:

```text
IR_DF  = IR[5:3]
DF_VAL = IR_DF
```

Widths:

```text
IR_DF = 3 bits
DF_VAL = 3 bits
```

Constraints:

- `DF_VAL` is required when `DF_LOAD = 1` and `DF_SRC = Control`.
- `IR_DF_TO_DF` binds the control input `IR_DF` directly to the control output `DF_VAL`.
- No transformation is applied.

Sources:

- [IR Derived Fields](../10-control-input-definitions/02-ir-derived-fields.md#ir_df)
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md#ir_df_to_df)
- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)

---

### 5.2 Deferred Instruction Field From Instruction

Applicable context:

```text
IR_WRITES_IF = 1
IR_IF_TO_DIF is selected
```

Micro-operation assignments:

```text
DIF_LOAD = 1
DIF_SRC  = Control
```

Control-supplied value:

```text
DIF_VAL = IR_IF
```

Value relationship:

```text
IR_IF  = IR[5:3]
DIF_VAL = IR_IF
```

Widths:

```text
IR_IF   = 3 bits
DIF_VAL = 3 bits
```

No transformation is applied.

Constraints:

- `DIF_VAL` is required when `DIF_LOAD = 1` and `DIF_SRC = Control`.
- `IR_IF_TO_DIF` binds the control input `IR_IF` directly to the control output `DIF_VAL`.
- `DIF_CLEAR` uses the same `DIF_SRC = Control` path but assigns `DIF_VAL = 0`.
- `DIF_SRC` does not distinguish between `IR_IF` and zero; the selected control case determines `DIF_VAL`.
- `IR_IF_TO_DIF` and `DIF_CLEAR` must not be selected concurrently.
- No dedicated `DIF_SRC = IR` encoding or direct IR-to-DIF datapath is used.
- No transformation is applied.

Sources:

- [IR Derived Fields](../10-control-input-definitions/02-ir-derived-fields.md#ir_if)
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md#ir_if_to_dif)
- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)

---

### 5.3 Deferred Instruction Field Clear Value

Applicable context:

```text
DIF_CLEAR is selected
```

Micro-operation assignments:

```text
DIF_LOAD = 1
DIF_SRC  = Control
```

Control-supplied value:

```text
DIF_VAL = 0
```

Constraints:

- `DIF_VAL` is required because `DIF_LOAD = 1` and `DIF_SRC = Control`.
- `DIF_CLEAR` and `IR_IF_TO_DIF` must not be selected concurrently.

Sources:

- [Micro-operations](../../03-microarchitecture/02-micro-operations.md#dif_clear)
- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)

---

### 5.4 Fixed Control Values Already Owned by Micro-Operations

The following control-selected values are completely defined by their corresponding micro-operation mappings and must not be duplicated as direct-control bindings:

- `DF_VAL = 0` for `DF_CLEAR`
- `IF_VAL = 0` for `IF_CLEAR`
- `MA_VAL = 0` for `MA_CLEAR`
- `PC_VAL = 1` for `PC_SET_1`
- `IOT_TRANSFER_VAL = NONE` for an unconditional `IOT_TRANSFER_CLEAR`

The maintained micro-operation mapping remains responsible for these fixed assignments.

Related:

- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)
- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)

---

### 5.5 Pending External-IOT Transfer Value

`IOT_TRANSFER_VAL` has the following documented encodings:

```text
NONE  = 0
READ  = 1
WRITE = 2
3     = invalid
```

#### 5.5.1 Read Request Acceptance

Applicable context:

```text
IO_READ_REQ is accepted
```

Assignments:

```text
IOT_TRANSFER_LOAD = 1
IOT_TRANSFER_VAL  = READ
```

Constraints:

- `IO_READ_REQ` and `IO_WRITE_REQ` must not both be accepted for the same request.
- The accepted request must have a transfer phase and commit TP within the current external-IOT EXECUTE major state.

Sources:

- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)
- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [External I/O Interface](../../07-io/02-external-iot-interface.md)
- [I/O Timing](../../07-io/03-io-timing.md)

#### 5.5.2 Write Request Acceptance

Applicable context:

```text
IO_WRITE_REQ is accepted
```

Assignments:

```text
IOT_TRANSFER_LOAD = 1
IOT_TRANSFER_VAL  = WRITE
```

Constraints:

- `IO_READ_REQ` and `IO_WRITE_REQ` must not both be accepted for the same request.
- The accepted request must have a transfer phase and commit TP within the current external-IOT EXECUTE major state.

Sources:

- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)
- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [External I/O Interface](../../07-io/02-external-iot-interface.md)
- [I/O Timing](../../07-io/03-io-timing.md)

#### 5.5.3 Completed Transfer Clear

Applicable context:

```text
a pending transfer completes
no replacement request is accepted at the same TP
```

Assignments:

```text
IOT_TRANSFER_LOAD = 1
IOT_TRANSFER_VAL  = NONE
```

Constraints:

- A newly accepted request does not affect the transfer committing at the same TP.
- This case applies only when no replacement request is accepted.

Sources:

- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)
- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [External I/O Interface](../../07-io/02-external-iot-interface.md)
- [I/O Timing](../../07-io/03-io-timing.md)

#### 5.5.4 Completion With Read Replacement

Applicable context:

```text
a pending transfer completes
IO_READ_REQ is accepted at the same TP
```

Assignments:

```text
IOT_TRANSFER_LOAD = 1
IOT_TRANSFER_VAL  = READ
```

Constraints:

- The newly accepted read request replaces the completed transfer.
- The new request does not affect the transfer committing at the current TP.
- The replacement request must have a transfer phase and commit TP within the current external-IOT EXECUTE major state.

Sources:

- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)
- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [External I/O Interface](../../07-io/02-external-iot-interface.md)
- [I/O Timing](../../07-io/03-io-timing.md)

#### 5.5.5 Completion With Write Replacement

Applicable context:

```text
a pending transfer completes
IO_WRITE_REQ is accepted at the same TP
```

Assignments:

```text
IOT_TRANSFER_LOAD = 1
IOT_TRANSFER_VAL  = WRITE
```

Constraints:

- The newly accepted write request replaces the completed transfer.
- The new request does not affect the transfer committing at the current TP.
- The replacement request must have a transfer phase and commit TP within the current external-IOT EXECUTE major state.

Sources:

- [Microarchitectural Control Signals](../20-control-output-definitions/01-microarchitectural-control-signals.md)
- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [External I/O Interface](../../07-io/02-external-iot-interface.md)
- [I/O Timing](../../07-io/03-io-timing.md)

#### 5.5.6 Invalid Encoding

```text
IOT_TRANSFER_VAL = 3
```

This encoding is invalid and must not appear in a generated control word.

---

## 6. Explicit Exclusions

The following do not require direct-control value bindings in this document:

- values selected directly from a named datapath source
- constant values completely assigned by a micro-operation mapping
- derived outputs
- external input values
- physical output-drive states
- values owned by an external DMA controller
- values for which no authoritative source relationship is defined

In particular:

- derived `IOA[5:0]` and `IOP[2:0]` values are not encoded direct-control values
- `GTF_FLAGS` is a derived combinational value
- `DB_INPUT` and `MDB_INPUT` are external values
- DMA-supplied `MFB`, `AB`, and `MDB` values are not CPU direct-control values

---

## 7. Related Documents

- [Direct Control Model](../07-direct-control-model.md)
- [Control Constraints](../03-control-constraints.md)
- [Invalid Conditions](../06-invalid-conditions.md)
- [Control Input Definitions](../10-control-input-definitions/00-index.md)
- [Control Output Definitions](../20-control-output-definitions/00-index.md)
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)
- [Fetch & Defer](../../03-microarchitecture/04-fetch-defer.md)
- [MRI Execution](../../03-microarchitecture/05-mri-execution.md)
- [IOT Execution](../../03-microarchitecture/06-iot-execution.md)
- [Interrupt Execution](../../03-microarchitecture/08-interrupt-execution.md)
- [Console Execution](../../03-microarchitecture/09-console-execution.md)
- [Memory Field Selection](../../06-memory/05-memory-field-selection.md)
- [DMA Interface](../../07-io/05-dma-interface.md)
- [DMA Arbitration](../../07-io/06-dma-arbitration.md)