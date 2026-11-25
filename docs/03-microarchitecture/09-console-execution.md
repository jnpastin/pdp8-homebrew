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
- Micro-operation sequences invoked by console controls

Control implementation details are defined in [Control](../04-control/README.md).

Operator-visible front-panel behavior belongs to the front-panel documentation, which is not yet written.

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

While halted, console operation switches invoke bounded micro-operation sequences.

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
CLEAR
LOAD ADDRESS
EXAMINE
DEPOSIT
START
CONTINUE
```

Each console operation executes as one console transaction ([Major State Timing §8](../09-timing/03-major-state-timing.md#8-halted-state-and-console-transactions)). The main timing sequence is held while halted, so CONTINUE resumes a halted Single Step or Single Instruction exactly where it stopped, unless an EXAMINE or DEPOSIT came between. Those advance PC, so an interrupted DEFER or EXECUTE would finish and continue from the wrong address; they load FETCH as the held major state, as START does. CONTINUE then starts a new instruction at PC, as on the PDP-8/E ([Sequencing and Internal Direct Control §3.2.12](../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#3212-examine-and-deposit-return-to-fetch)).

Only one console command is accepted at a time; the first accepted wins ([External Inputs §4.1](../04-control/10-control-input-definitions/04-external-inputs.md#41-console-command-acceptance)).

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

LOAD ADDRESS loads PC from FP_SR. EXAMINE and DEPOSIT then address memory from PC, and load MA from PC so that the front panel shows the address just examined or deposited.

They do not load `EA_ADDR`. An EXAMINE or DEPOSIT always leaves FETCH as the held major state (section 3), and FETCH reloads `EA_ADDR` at TP3 before anything reads it.

---

## 6. Load Address Operation

Applicable context:

```text
RUN = 0
FP_LOAD_ADDRESS = 1
```

Execution model:

```text
single TS-equivalent console transaction
```

μops:

- CIFP_CLEAR
- FP_SR_TO_PC
- FP_IF_TO_DIF
- FP_IF_TO_IF
- FP_DF_TO_DF


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

Applicable context:

```text
RUN = 0
FP_EXAMINE = 1
```

Execution model:

```text
single TS-equivalent console transaction
```

μops:

- PC_TO_MA
- PC_INC
- MEM_READ_TO_MB

Result:

```text
MA      ← PC
MB      ← Memory[IF:PC]
PC      ← PC + 1
```

The memory read drives AB from PC and MFB from IF, not MA or EA. This allows all micro-operations to occur simultaneously within a single TS. AB_SRC = PC and MFB_SRC = IF, while normal memory operations select AB_SRC and MFB_SRC per the active phase.

The processor remains halted, with FETCH as the held major state (section 3).

---

## 8. Deposit Operation

Applicable context:

```text
RUN = 0
FP_DEPOSIT = 1
```

Execution model:

```text
single TS-equivalent console transaction
```

μops:

- PC_TO_MA
- PC_INC
- FP_SR_TO_MB
- MEM_WRITE_FROM_FP_SR

Result:

```text

MA              ← PC
MB              ← FP_SR
Memory[IF:PC]   ← FP_SR
PC              ← PC + 1
```

`FP_SR_TO_MB` exists to update the observable MB state for the front panel.

`MEM_WRITE_FROM_FP_SR` exists to avoid an invalid same-TS dependency on the newly loaded MB value.

The memory write and MB update both consume FP_SR as their source, allowing the operation to remain a valid single TS-equivalent console transaction.

The memory write drives AB from PC and MFB from IF, not MA or EA. This allows all micro-operations to occur simultaneously within a single TS. AB_SRC = PC and MFB_SRC = IF, while normal memory operations select AB_SRC and MFB_SRC per the active phase.

The processor remains halted, with FETCH as the held major state (section 3).

---

## 9. Clear Operation
  
Front-panel CLEAR requests system initialization while the processor is halted.

Applicable context:

```text
RUN = 0
FP_CLEAR = 1
```

Execution model:

```text
single TS-equivalent console transaction
```

μops:

- AC_CLEAR
- L_CLEAR
- IE_CLEAR

The μops clear AC, L, and IE at TP_FP. `/INITIALIZE` initializes the I/O controllers.

The power-on reset ends with one CLEAR transaction, loaded into the command latch by the reset rather than accepted from the key ([Timing Terminology §3.4](../09-timing/01-terminology.md#34-power-on-reset)).

Acceptance:
- FP_CLEAR is accepted only when RUN = 0.
- FP_CLEAR is ignored when RUN = 1.
- One accepted press generates one /INITIALIZE assertion.
- A held FP_CLEAR input does not generate repeated pulses.
- FP_CLEAR is re-armed only after the synchronized input is released.

Execution:
- An accepted FP_CLEAR assertion causes /INITIALIZE to be asserted for the whole console transaction.
- The processor remains halted.
- Normal instruction sequencing does not begin.
- The operation does not use the normal instruction execution path.

Result:
- AC is cleared.
- L is cleared.
- IE is cleared.
- Each I/O controller enters its documented initialized state.
- II, CIFP, DIF, IF, DF, and IB are unchanged.

On the PDP-8/E, CLEAR "generates an INITIALIZE pulse that loads a binary 0 into bits 0-11 of the AC, the link, all I/O device flag registers and all interrupt system flip-flops", the same as CAF (Small Computer Handbook, 1973, Table 3-1, p. 3-2). CLEAR here leaves II unchanged: II has no effect while IE is 0, and ION and RTF, the only instructions that set IE, also set II ([Interrupt Enable and Inhibit](../08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md)). GTF does not report II ([IOT Instruction Detail §3.1](../02-isa/04-iot.md#31-processor-flags-word-gtf-rtf)).

The authoritative signal behavior is defined in [System Initialization](../04-control/20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize).

---

## 10. Start Operation

START is CLEAR then CONTINUE in one key. The PDP-8/E has no START key: "Program execution is started by operating and releasing the CLEAR switch, then operating and releasing the CONTinue switch" (Small Computer Handbook, 1973, p. 2-12). START gives the same result, and also clears MQ and II, which the PDP-8/E's CLEAR does not list.

Applicable context:

```text
RUN = 0
FP_START = 1
```

Execution model:

```text
single TS-equivalent console transaction
```

μops:

- AC_CLEAR
- L_CLEAR
- MQ_CLEAR
- IE_CLEAR
- II_CLEAR

Result:

```text
AC ← 0000
L ← 0
MQ ← 0000
IE ← 0
II ← 0
```

`/INITIALIZE` is asserted for the whole console transaction, so each I/O controller and the DMA arbiter enter their initialized states at TP_FP, the TP that also sets `RUN` ([System Initialization](../04-control/20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)). A DMA burst suspended by Single Step is therefore cancelled ([DMA Arbitration §13.2](../07-io/06-dma-arbitration.md#132-system-initialization)).

Execution begins in:

```text
FETCH
```

at the first timing state.

The address that execution begins at is set by LOAD ADDRESS (section 6).

The processor enters the Running state.

---

## 11. Continue Operation

Continue resumes execution from the preserved processor state.

Applicable context:

```text
RUN = 0
FP_CONTINUE = 1
```

Execution model:

```text
single TS-equivalent console transaction
```

μops:

- (no μops)

No architectural μops are executed.

Result:

```text
Execution resumes from the current machine state.
```

The major state resumed is the held one, which is FETCH after an EXAMINE or DEPOSIT (section 3).

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

## 12. Single Instruction Mode

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

```text
FETCH (direct JMP, OPR)
```

```text
FETCH → DEFER (JMP I)
```

Single Instruction does not alter execution behavior.

It only changes when execution halts.

---

## 13. Single Step Mode

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

```text
DMA
```

each execute individually.

A DMA major state is a step of its own, matching DEC's SING STEP, which "halts at the end of the current cycle" (PDP-8/E Maintenance Manual, volume 1, §3.7, p. 3-16), and a data break is a cycle of its own. When the halt leaves `MS = DMA` with the burst still selected, the burst is suspended: `/DMA_GRANT` is deasserted while halted, the controller and arbiter hold their state, and CONTINUE resumes the burst at DMA TS1, or at the next DMA entry after an EXAMINE or DEPOSIT. See [DMA Execution §4](./10-dma-execution.md#4-halting-between-dma-cycles).

Resumption requires:

```text
START
```

or:

```text
CONTINUE
```

---

## 14. Timing Relationships

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

## 15. Halted Idle Operation

Halted idle is the processor state while halted with no console transaction in progress.

Applicable context:

```text
RUN = 0
FP_START = 0
FP_CLEAR = 0
FP_CONTINUE = 0
FP_LOAD_ADDRESS = 0
FP_EXAMINE = 0
FP_DEPOSIT = 0
```

Execution model:

```text
single TS-equivalent console transaction
```

μops:

- (no μops)

While halted idle:

- no main-sequence TP and no console TP occurs, so no control-word result commits
- the control word is nevertheless presented continuously, so every output must hold its inactive or preserving value
- memory, I/O, and bus drive outputs remain deasserted
- the processor remains halted until a console command is accepted

The execution model is listed for uniformity with the console operations; halted idle is the control word presented between console transactions ([Major State Timing §8](../09-timing/03-major-state-timing.md#8-halted-state-and-console-transactions)).
