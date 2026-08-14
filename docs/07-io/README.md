# I/O Subsystem

## Purpose

Section 7 defines the architectural interface between the CPU, external I/O controllers, the DMA arbiter, and memory-facing DMA devices.

## Scope

This section defines:

- external IOT selection and operation transport
- controller response signals
- IOT timing and wait behavior
- controller obligations
- DMA ownership, arbitration, and timing
- invalid architectural conditions

This section does not define:

- electrical configuration mechanisms
- connector or backplane implementation
- device-specific IOT instruction sets
- device-specific register sets
- the final device address map
- individual controller implementations

Those items will be added or refined as later design priorities are resolved.

## Documents

- [I/O Architecture](./01-io-architecture.md)
- [External IOT Interface](./02-external-iot-interface.md)
- [I/O Timing](./03-io-timing.md)
- [Controller Contract](./04-controller-contract.md)
- [DMA Interface](./05-dma-interface.md)
- [DMA Arbitration](./06-dma-arbitration.md)
- [Invalid Conditions](./07-invalid-conditions.md)

## Existing Authoritative Dependencies

- [IOT Instruction Detail](../02-isa/04-iot.md)
- [IOT Execution](../03-microarchitecture/06-iot-execution.md)
- [Control Model](../04-control/01-control-model.md)
- [Control Constraints](../04-control/03-control-constraints.md)
- [Sequencing Control Signals](../04-control/20-control-output-definitions/03-sequencing-control-signals.md)
- [Buses and Signals](../05-buses-and-signals/README.md)
- [I/O Interface](../05-buses-and-signals/10-io-interface.md)
- [DMA Interface](../05-buses-and-signals/11-dma-interface.md)
- [Memory Interface](../06-memory/02-memory-interface.md)
- [Timing Architecture](../09-timing/02-timing-architecture.md)

## Core Invariants

- I/O device selection is independent of physical placement.
- External controllers receive IOA and IOP as separate interfaces.
- Controller responses are phase-specific.
- All CPU and controller state changes occur only at TP events.
- Only the selected controller may respond to an external IOT.
- Only the granted DMA controller may drive DMA-owned interfaces.
- The CPU does not arbitrate among DMA controllers.
