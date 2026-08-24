# Controller Contract

## Purpose

This document defines the obligations common to all external I/O controllers.

### Address Configuration

Each controller must provide one active configured IOA address for each device interface it implements.  

The architectural behavior does not depend on how those addresses are physically configured.  

A DEC-compatible controller must default each device interface to the corresponding DEC device address when one is defined. Alternate addresses are permitted but may require software changes.

## Selection Qualification

Every controller action caused by an external IOT must be qualified by:

```text
IOT_ACTIVE
AND address match
AND decoded IOP behavior
AND assigned phase
```

A controller must not act on incidental IOA, IOP, TS, or TP values outside a selected external IOT.

## Response Qualification

The controller may assert:

- `IO_READ_REQ`
- `IO_WRITE_REQ`
- `IO_SKIP_REQ`
- `IO_CLEAR_AC_REQ`
- `/IO_WAIT`

Each assertion must satisfy the definitions in [External IOT Interface](./02-external-iot-interface.md) and [I/O Timing](./03-io-timing.md).

## DB Ownership

For a read:

- only the selected controller drives DB
- the controller supplies valid data before the commit TP
- the controller releases DB after the required hold interval

For a write:

- the controller does not drive DB
- the controller captures the CPU-driven DB value at the commit TP

A controller must never drive DB while unselected.

## Controller-Local State

Controller-local state changes:

- are defined by the controller's IOT instruction set
- occur only at TP events
- are qualified by selection and decoded operation
- use pre-TP state
- commit simultaneously with CPU actions at the same TP
- do not depend on a result committed at the same TP

## Skip Condition

A controller requesting skip during TS4 must derive `IO_SKIP_REQ` from:

- `IOT_ACTIVE`
- address match
- decoded IOP
- registered controller state

A separate skip-condition register is not required.

The controller may update or clear the underlying condition at TP4 only when the skip request is derived from its pre-TP4 value.

The controller does not perform or control the resulting CPU state change beyond asserting `IO_SKIP_REQ`.

## I/O Wait

A controller may assert `/IO_WAIT` only:

- while selected
- while `IOT_ACTIVE` is asserted
- during a non-TP setup TSTEP
- when additional setup time is required before the next TP

The controller must deassert `/IO_WAIT` when the pending operation is ready to proceed.

## Persistent Service Requests

Controller interrupt contributions and `/DMA_REQ[n]` are persistent registered request signals.

Rules:

- A persistent request is derived only from controller state captured at a TP.
- A persistent request remains asserted while its underlying controller condition remains true.
- Sampling a persistent request does not clear or consume it.
- The controller deasserts the request only when the underlying condition is cleared, serviced, completed, canceled, or reset according to the controller-specific contract.
- A persistent request may remain asserted across multiple TS, TP, instruction, and major-state boundaries.
- A controller must not generate a transient request pulse that could disappear before the receiving subsystem samples it.

### Interrupt Contribution

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

### DMA Request

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

The request remains asserted until:

- the complete DMA operation finishes
- the controller completes the current transfer and cannot immediately complete another transfer
- the operation is canceled
- reset clears the operation

A selected controller may keep /DMA_REQ[n] asserted across selection termination when additional immediately transferable work remains.  
Selection termination does not consume the controller request.  
A controller that cannot immediately complete another transfer must deassert /DMA_REQ[n] after completing the current transfer and request service again when the next transfer is prepared.  
The DMA arbiter determines the aggregate CPU-facing /DMA_REQ from /DMA_REQ[14:0].

### Receiving-Side Synchronization

Controller interrupt contributions and `/DMA_REQ[n]` are registered controller outputs.

Aggregate `/INT_REQ` and aggregate `/DMA_REQ` must be synchronized before they participate in CPU control decisions.

Synchronization does not change request ownership, persistence, or clearing semantics.

## DMA-Capable Controllers

A DMA-capable controller additionally must:

- use exactly one configured DMA priority in the range 0 through 14
- assert only the corresponding /DMA_REQ line
- assert /DMA_REQ only when it can complete the next DMA word transfer
- preserve transfer readiness from request assertion through TP2
- recognize ownership only when /DMA_GRANT is asserted and DMA_GRANT_ID matches its configured priority
- reject DMA_GRANT_ID value 15 as the no-controller-selected state
- drive DMA-owned interfaces only while validly selected
- complete exactly one DMA word transfer at TP2 after being selected
- maintain its complete-operation address and remaining word count
- update its address and remaining word count only for the transfer completed at TP2
- keep its request asserted while additional immediately transferable service remains pending
- deassert its request after the current transfer when it cannot immediately complete another transfer
- tolerate selection termination at the configured arbiter burst boundary
- resume through normal re-arbitration

## Physical Implementation Boundary

The following are outside this architectural contract:

- address configuration technology
- DMA priority configuration technology
- burst-limit configuration technology
- electrical driver selection
- connector assignment
- controller-local counter widths

## Asynchronous Event Boundary

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
- `/IO_WAIT`
- `/INT_REQ`
- `/DMA_REQ[n]`

Synchronization of a physical-device event is the responsibility of the controller that interprets that event.

Synchronization of aggregate `/INT_REQ`, aggregate `/DMA_REQ`, and `/IO_WAIT` before use by CPU control or timing remains the responsibility of the receiving CPU-side interface.

The synchronization mechanism and metastability-mitigation implementation belong to the controller or receiving-interface design and are outside this architectural contract.
