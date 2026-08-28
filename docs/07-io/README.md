# I/O Subsystem

## 1. Purpose

Section 7 defines the architectural interface between the CPU, external I/O controllers, the DMA arbiter, and memory-facing DMA devices.

---

## 2. Scope

This section defines:

- external IOT selection and operation transport
- controller response signals
- IOT timing and wait behavior
- common controller obligations
- DMA ownership, arbitration, and timing
- device address allocation
- programmer-visible controller behavior
- invalid architectural conditions

This section does not define:

- electrical configuration mechanisms
- connector or backplane implementation
- physical driver technology
- physical media interfaces
- controller component selection

Those items belong to the physical implementation documentation.

---

## 3. Common Architecture Documents

- [I/O Architecture](./01-io-architecture.md)
- [External IOT Interface](./02-external-iot-interface.md)
- [I/O Timing](./03-io-timing.md)
- [Controller Contract](./04-controller-contract.md)
- [DMA Interface](./05-dma-interface.md)
- [DMA Arbitration](./06-dma-arbitration.md)
- [Invalid Conditions](./07-invalid-conditions.md)
- [Device Address Map](./08-device-address-map.md)

---

## 4. Controller Documents

- [Read Me](./controllers/README.md)
- [KL8E Equivalent Serial Controller(Teletype keyboard/printer alternative)](./controllers/01-kl8e-uart.md)
- [PC8E Equivalent Paper-Tape Controller](./controllers/02-pc8e-paper-tape.md)
- [RK8E Equivalent Disk Controller](./controllers/03-rk8e-storage.md)

---

## 5. Existing Authoritative Dependencies

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

---

## 6. Core Invariants

- I/O device selection is independent of physical placement.
- External controllers receive IOA and IOP as separate interfaces.
- Controller responses are phase-specific.
- All CPU and controller state changes occur only at TP events.
- Only the selected controller may respond to an external IOT.
- Only the granted DMA controller may drive DMA-owned interfaces.
- The CPU does not arbitrate among DMA controllers.
- DEC-compatible controllers reproduce the programmer-visible behavior of the emulated DEC controller.
- Controller-private physical interfaces do not alter programmer-visible compatibility behavior.
