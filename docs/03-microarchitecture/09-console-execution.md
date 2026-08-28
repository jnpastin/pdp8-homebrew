# Console Execution

## 1. Purpose

This document defines the microarchitectural behavior of console operations and halted execution.

It describes:

- Run and Halt operating modes
- Console operation execution
- Halt request handling
- Single Instruction behavior
- Single Step behavior
- Timing relationships
- Microoperation sequences invoked by console controls

Control implementation details are defined in Section 4.

Operator-visible behavior is defined in Section 10.

---

## 2. Run and Halt Modes

The processor operates in one of two modes:

```text
RUNNING
HALTED
```

When running:

```text
FETCH
DEFER
EXECUTE
INTERRUPT
DMA
```

major states execute normally.

When halted:

```text
Normal instruction sequencing is inactive.
```

Console operation switches become active.

The halted state preserves all architectural processor state.

No registers are modified unless explicitly changed by a console operation.

---

## 3. Console Operation Execution Model

While halted, console operation switches invoke bounded microoperation sequences.

Console operations are not executed through the normal instruction sequencing mechanism.

Each console operation executes as a single TS-equivalent transaction.

All μops associated with the operation execute concurrently.

Console operations must not rely on ordering between constituent μops.

Conceptually:

```text
HALTED
    +
Console Operation
    →
Single TS-equivalent transaction
    →
HALTED
```

or:

```text
HALTED
    +
START / CONTINUE
    →
RUNNING
```

The following switches execute console operations:

```text
LOAD ADDRESS
EXAM
DEPOSIT
START
CONTINUE
```

---

## 4. Halt Requests

The processor does not halt immediately when a halt request is generated.

Instead, a halt request is recorded and evaluated at an instruction completion boundary.

Sources of halt requests include:

```text
STOP switch

HLT instruction
```

Both mechanisms produce identical architectural behavior.

A halt request remains pending until consumed.

---

## 5. Console Address Context

Console operations update both:

```text
MA
EA_ADDR
```

This maintains the expected state when the CPU resumes normal operations.

The two registers are maintained in lockstep during console operation.

Purpose:

```text
MA
    Observable address register
    Visible on the front panel

EA_ADDR
    Internal address context used by existing CPU address-loading paths
```

This allows CONT to reuse existing execution mechanisms.

The PC is loaded via FP_SR, this is then used to drive MA and EA for EXAM and DEP actions

---

## 6. Load Address Operation

Load Address sets the front panel execution context by reading IF, DF, and PC from the switches

Microoperation sequence:

```text
CIFP_CLEAR
FP_SR_TO_PC
FP_IF_TO_DIF
FP_IF_TO_IF
FP_DF_TO_DF
```

Result:

```text
CIFP ← 0
DF      ← Front Panel DF
DIF     ← Front Panel IF
IF      ← Front Panel IF
PC      ← FP_SR
```

No memory access occurs.

The processor remains halted.

---

## 7. Examine Operation

Examine sets the address context from the PC, reads memory, and increments the PC

Microoperation sequence:

```text
PC_TO_MA
PC_TO_EA_ADDR
PC_INC
MEM_READ_TO_MB
```

Result:

```text
MA      ← PC
EA_ADDR ← PC
MB      ← Memory[IF:PC]
PC      ← PC + 1
```

The memory read drives AB from PC and MFB from IF, not MA or EA. This allows all microoperations to occur simultaneously within a single TS. AB_SRC = PC and MFB_SRC = IF, while normal memory operations select AB_SRC and MFB_SRC per the active phase.

The processor remains halted.

---

## 8. Deposit Operation

Deposit sets the address context from the PC, writes the value of FP_SR to memory, and increments the PC

Microoperation sequence:

```text
PC_TO_MA
PC_TO_EA_ADDR
PC_INC
FP_SR_TO_MB
MEM_WRITE_FROM_FP_SR
```

Result:

```text

MA              ← PC
EA_ADDR         ← PC
MB              ← FP_SR
Memory[IF:PC]   ← FP_SR
PC              ← PC + 1
```

`FP_SR_TO_MB` exists to update the observable MB state for the front panel.

`MEM_WRITE_FROM_FP_SR` exists to avoid an invalid same-TS dependency on the newly loaded MB value.

The memory write and MB update both consume FP_SR as their source, allowing the operation to remain a valid single TS-equivalent console transaction.

The memory write drives AB from PC and MFB from IF, not MA or EA. This allows all microoperations to occur simultaneously within a single TS. AB_SRC = PC and MFB_SRC = IF, while normal memory operations select AB_SRC and MFB_SRC per the active phase.

The processor remains halted.

---

## 9. Start Operation

Start establishes a known processor execution state.

Microoperation sequence:

```text
AC_CLEAR
L_CLEAR
MQ_CLEAR
IE_CLEAR
II_CLEAR
```

Result:

```text
AC ← 0000
L ← 0
MQ ← 0000
IE ← 0
II ← 0
```

Execution begins in:

```text
FETCH
```

at the first timing state.

The address that execution begins at is set via the LOAD command.

The processor enters the Running state.

---

## 10. Continue Operation

Continue resumes execution from the preserved processor state.

No architectural μops are executed.

Result:

```text
Execution resumes from the current machine state.
```

The processor enters the Running state.

Continue does not modify:

```text
PC
AC
L
MQ
IF
DF
MA
EA_ADDR
MS
TS
```

---

## 11. Single Instruction Mode

Single Instruction is an execution mode.

When enabled:

```text
One complete instruction is executed.
```

At instruction completion:

```text
RUNNING → HALTED
```

Instruction completion occurs after the final major state associated with the instruction.

Examples:

```text
FETCH → EXECUTE
```

```text
FETCH → DEFER → EXECUTE
```

Single Instruction does not alter execution behavior.

It only changes when execution halts.

---

## 12. Single Step Mode

Single Step is an execution mode.

When enabled:

```text
One major state is executed.
```

A halt is generated at major-state completion.

The halt point occurs after:

```text
TS4
```

of the currently executing major state.

Examples:

```text
FETCH
```

```text
DEFER
```

```text
EXECUTE
```

```text
INTERRUPT
```

each execute individually.

Resumption requires:

```text
START
```

or:

```text
CONTINUE
```

---

## 13. Timing Relationships

Console operation switches execute as single TS-equivalent transactions while halted.

Single Step halt evaluation:

```text
Major-state completion
(TS4)
```

Single Instruction halt evaluation:

```text
Instruction completion
```

STOP and HLT halt evaluation:

```text
Instruction completion
```

Execution never halts in the middle of a major state.
