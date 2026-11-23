# Controller Contract

## 1. Purpose

This document defines the obligations common to all external I/O controllers.

### 1.1 Address Configuration

Each controller must provide one active configured IOA address for each device interface it implements.  

The architectural behavior does not depend on how those addresses are physically configured.  

A DEC-compatible controller must default each device interface to the corresponding DEC device address when one is defined. Alternate addresses are permitted but may require software changes.

---

## 2. Selection Qualification

Every controller action caused by an external IOT must be qualified by:

```text
IOT_ACTIVE
AND address match
AND decoded IOP behavior
AND assigned phase
```

A controller must not act on incidental IOA, IOP, TS, or TP values outside a selected external IOT.

---

## 3. Response Qualification

The controller may assert:

- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`

Each assertion must satisfy the definitions in [External IOT Interface](./02-external-iot-interface.md) and [I/O Timing](./03-io-timing.md).

---

## 4. DB Ownership

For a read:

- only the selected controller drives DB
- the controller supplies valid data before the commit TP
- the controller releases DB no earlier than the end of the commit TP, which supplies the hold interval

For a write:

- the controller does not drive DB
- the controller captures the CPU-driven DB value at the commit TP

A controller must never drive DB while unselected.

---

## 5. Controller-Local State

Controller-local state changes:

- are defined by the controller's IOT instruction set
- occur only at TP events
- are qualified by selection and decoded operation
- use pre-TP state
- commit simultaneously with CPU actions at the same TP
- do not depend on a result committed at the same TP
- are captured at the leading edge of the TP
- become visible only as the TP ends, in every response, request, and driven value ([Timing Architecture §7.6](../09-timing/02-timing-architecture.md#76-rule-6--two-ranks))

---

## 6. System Initialization
  
Every controller must accept the active-low /INITIALIZE signal.

When /INITIALIZE is asserted:
- the controller enters its documented initialized state at the TP ending the assertion (EXECUTE TP4 for CAF, TPC for CLEAR)
- /INITIALIZE overrides all controller commands, transfers, flag updates, interrupt requests, DMA activity, and other controller-local actions that would otherwise commit at the same TP
- the controller samples /INITIALIZE only at that TP and must not act on its level earlier
- any active controller operation is terminated
- controller bus-driving outputs are released
- the controller interrupt contribution is deasserted
- any controller /DMA_REQ output is deasserted

A controller must respond to /INITIALIZE regardless of:
- IOT_ACTIVE
- address match
- IOP
- interrupt state
- DMA request state
- DMA grant state

Each controller-specific contract must define:
- the initialized value of every programmer-visible register
- the initialized value of every controller flag
- the initialized interrupt-enable state
- the disposition of active and pending operations
- the initialized interrupt-request state
- the initialized DMA-request state, when applicable
- any controller-specific or emulated-device state affected by initialization

The authoritative [System Initialization](../04-control/20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize) definition specifies the signal sources, polarity, and pulse timing.

---

## 7. Skip Condition

A controller requesting skip during TS4 must derive `IO_SKIP_REQ` from:

- `IOT_ACTIVE`
- address match
- decoded IOP
- registered controller state

A separate skip-condition register is not required.

The controller may update or clear the underlying condition at TP4 only when the skip request is derived from its pre-TP4 value.

The controller does not perform or control the resulting CPU state change beyond asserting `IO_SKIP_REQ`.

---

## 8. Response Time

A controller has no wait signal. It must respond within the fixed IOT timing, and an operation that takes longer completes later and reports completion through a flag ([I/O Timing §5](./03-io-timing.md#5-fixed-iot-timing)).

---

## 9. Persistent Service Requests

Controller interrupt contributions and `/DMA_REQ[n]` are persistent registered request signals.

Rules:

- A persistent request is derived only from controller state captured at a TP.
- A persistent request remains asserted while its underlying controller condition remains true.
- Sampling a persistent request does not clear or consume it.
- The controller deasserts the request only when the underlying condition is cleared, serviced, completed, canceled, or reset according to the controller-specific contract.
- A persistent request may remain asserted across multiple TS, TP, instruction, and major-state boundaries.
- A controller must not generate a transient request pulse that could disappear before the receiving subsystem samples it.

### 9.1 Interrupt Contribution

A controller interrupt contribution remains asserted while:

```text
CONTROLLER_INTERRUPT_ENABLE
AND
CONTROLLER_INTERRUPT_CONDITION
```

remains true.

The controller-specific contract defines:

- the interrupt-enable state
- the interrupt condition
- the operations that clear the condition

The shared `/INT_REQ` signal is the aggregate of all controller interrupt contributions.

An IOT that clears its controller's interrupt condition or interrupt enable must commit the clear by TP3. The instruction-completion decision at TP4 uses `/INT_REQ` as it stands during TS4, so a clear at TP4 would still be seen, and the CPU would enter INTERRUPT with no device requesting. The PDP-8/E likewise makes an IOT's transfer and samples the interrupt request at TP3 (maintenance manual, volume 1, §3.41.2 and §3.42).

- An IOT may set a condition at TP4. The interrupt is then recognized at a later instruction completion.
- CAF is the exception: its `/INITIALIZE` commits at TP4, and interrupt recognition excludes it ([Interrupt Recognition §6](../08-interrupts-and-skip/02-interrupt-recognition-and-sequencing.md#6-next-major-state-selection)).

### 9.2 DMA Request

A DMA-capable controller asserts exactly one configured /DMA_REQ[n] while DMA service remains pending, where n is in the range 0 through 14.  
DMA priority 15 is reserved as the no-controller-selected encoding and has no corresponding /DMA_REQ line.

A controller may assert /DMA_REQ[n] only when:

- DMA service remains pending
- the controller can complete the next DMA word transfer
- the complete transfer address is prepared
- the transfer direction is prepared
- write data is prepared when the controller will write to memory
- the controller can capture read data when the controller will read from memory

Once selected, the controller must complete exactly one DMA word transfer at TP2.  
The controller must preserve its readiness from request assertion through completion of the selected transfer.

At the TP2 that completes the transfer, `/DMA_REQ[n]` changes to reflect it: it deasserts when that was the last word, or when the next transfer is not prepared. The arbiter decides during TS3, from values committed by TP2, whether the burst continues ([DMA Arbitration §11](./06-dma-arbitration.md#11-arbiter-burst-count)), so a request that changed only at TP3 would keep a finished controller selected. The address and word count still update at TP3.

The request remains asserted until:

- the complete DMA operation finishes
- the controller completes the current transfer and cannot immediately complete another transfer
- the operation is canceled
- reset clears the operation

An IOT that cancels the operation deasserts the request by TP3, for the same reason as an interrupt clear (section 9.1): the DMA decision at TP4 must see it.

A selected controller may keep /DMA_REQ[n] asserted across selection termination when additional immediately transferable work remains.  
Selection termination does not consume the controller request.  
A controller that cannot immediately complete another transfer must deassert /DMA_REQ[n] at the TP2 that completes the current transfer, and request service again when the next transfer is prepared.  
The DMA arbiter produces `DMA_ENABLE`.

Separate combinational aggregation logic continuously derives aggregate CPU-facing `/DMA_REQ` from `DMA_ENABLE` and `/DMA_REQ[14:0]`.

The controller does not generate aggregate `/DMA_REQ`.

### 9.3 Receiving-Side Synchronization

Controller interrupt contributions and `/DMA_REQ[n]` are registered controller outputs.

Aggregate `/INT_REQ` is the wired OR of those registered interrupt contributions. Like aggregate `/DMA_REQ`, it is not passed through an additional synchronization stage, and it must settle before the TP at which CPU control samples it.

Aggregate `/DMA_REQ` is a combinational CPU input derived from `DMA_ENABLE` and the registered controller `/DMA_REQ[n]` outputs. It is not passed through an additional synchronization stage.

`DMA_ENABLE`, `/DMA_REQ[n]`, and aggregate `/DMA_REQ` must satisfy the applicable setup and hold requirements before CPU control samples aggregate `/DMA_REQ` at TP4.

---

## 10. DMA-Capable Controllers

A DMA-capable controller additionally must:

- use exactly one configured DMA priority in the range 0 through 14
- assert only the corresponding /DMA_REQ line
- assert /DMA_REQ only when it can complete the next DMA word transfer
- preserve transfer readiness from request assertion through TP2
- recognize ownership only when /DMA_GRANT is asserted and DMA_GRANT_ID matches its configured priority
- reject DMA_GRANT_ID value 15 as the no-controller-selected state
- drive DMA-owned interfaces only during DMA TS2, while validly selected
- complete exactly one DMA word transfer at TP2 after being selected
- maintain its complete-operation address and remaining word count
- update its address and remaining word count only for the transfer completed at TP2
- keep its request asserted while additional immediately transferable service remains pending
- deassert its request after the current transfer when it cannot immediately complete another transfer
- tolerate selection termination at the configured arbiter burst boundary
- resume through normal re-arbitration
- release DMA-owned interfaces whenever `/DMA_GRANT` is deasserted, even while still selected
- tolerate an indefinite pause between DMA words while the CPU is halted, holding its request and prepared transfer until the burst resumes or `/INITIALIZE` is asserted

---

## 11. Physical Implementation Boundary

The following are outside this architectural contract:

- address configuration technology
- DMA priority configuration technology
- burst-limit configuration technology
- electrical driver selection
- connector assignment
- controller-local counter widths

---

## 12. Asynchronous Event Boundary

Physical-device events may occur asynchronously relative to system timing.

Each controller must synchronize its physical-device events before those events affect:

- programmer-visible controller state
- controller flags
- controller response signals
- interrupt contribution
- DMA request state

Programmer-visible controller state changes occur only at TP events.

Controller response signals must be derived only from:

- `IOT_ACTIVE`
- address match
- IOP decode
- the current TS
- registered controller state

An unsynchronized physical-device signal must not directly drive:

- DB
- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_CLEAR_AC_REQ`
- `IO_SKIP_REQ`
- `/INT_REQ`
- `/DMA_REQ[n]`

Synchronization of a physical-device event is the responsibility of the controller that interprets that event.

Aggregate `/INT_REQ` is not synchronized through an additional stateful stage. It is the wired OR of registered controller outputs, which change only as a TP ends.

Aggregate `/DMA_REQ` is not synchronized through an additional stateful stage. It is derived combinationally from `DMA_ENABLE` and registered controller `/DMA_REQ[n]` outputs and must satisfy the CPU’s TP4 setup and hold requirements.

The synchronization mechanism and metastability-mitigation implementation belong to the controller design and are outside this architectural contract.
