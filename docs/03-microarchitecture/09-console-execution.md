# 09-console-execution.md

## Purpose

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

# Run and Halt Modes

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

# Console Operation Execution Model

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

# Halt Requests

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

# Console Address Context

Console operations use both:

```text
MA
EA_ADDR
```

as the current console address context.

The two registers are maintained in lockstep during console operation.

Purpose:

```text
MA
    Observable address register
    Visible on the front panel

EA_ADDR
    Internal address context used by existing CPU address-loading paths
```

This avoids introducing console-specific address loading behavior and allows START to reuse existing execution mechanisms.

---

# Load Address Operation

Load Address establishes the current console address context.

Microoperation sequence:

```text
FP_SR_TO_MA

FP_SR_TO_EA

FP_IF_TO_IF

FP_DF_TO_DF
```

Result:

```text
MA      ← SR
EA_ADDR ← SR

IF      ← Front Panel IF
DF      ← Front Panel DF
```

No memory access occurs.

The processor remains halted.

---

# Examine Operation

Examine reads the memory location identified by the current console address context.

Microoperation sequence:

```text
MEM_READ_TO_MB

MA_INC

EA_INC
```

Result:

```text
MB ← Memory[IF:EA_ADDR]

MA      ← MA + 1
EA_ADDR ← EA_ADDR + 1
```

Address advancement occurs automatically after the read.

The processor remains halted.

---

# Deposit Operation

Deposit writes the switch register value to the current console address and updates the memory buffer display value.

Microoperation sequence:

```text
FP_SR_TO_MB

MEM_WRITE_FROM_SR

MA_INC

EA_INC
```

Result:

```text
MB ← SR

Memory[IF:EA_ADDR] ← SR

MA      ← MA + 1
EA_ADDR ← EA_ADDR + 1
```

`FP_SR_TO_MB` exists to update the observable MB state for the front panel.

`MEM_WRITE_FROM_SR` exists to avoid an invalid same-TS dependency on the newly loaded MB value.

The memory write and MB update both consume SR as their source, allowing the operation to remain a valid single TS-equivalent console transaction.

The processor remains halted.

---

# Start Operation

Start establishes a known processor execution state.

Microoperation sequence:

```text
AC_CLEAR

L_CLEAR

MQ_CLEAR

IE_CLEAR

II_CLEAR

PC_LOAD_EA_ADDR
```

Result:

```text
AC ← 0000

L ← 0

MQ ← 0000

IE ← 0

II ← 0

PC ← EA_ADDR
```

Execution begins in:

```text
FETCH
```

at the first timing state.

The processor enters the Running state.

---

# Continue Operation

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

# Single Instruction Mode

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

# Single Step Mode

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

# Timing Relationships

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

---

# Console Operation Summary

```text
LOAD ADDRESS

    FP_SR_TO_MA
    FP_SR_TO_EA
    FP_IF_TO_IF
    FP_DF_TO_DF

EXAM

    MEM_READ_TO_MB
    MA_INC
    EA_INC

DEPOSIT

    FP_SR_TO_MB
    MEM_WRITE_FROM_SR
    MA_INC
    EA_INC

START

    AC_CLEAR
    L_CLEAR
    MQ_CLEAR
    IE_CLEAR
    II_CLEAR
    PC_LOAD_EA_ADDR

CONTINUE

    No architectural μops
```