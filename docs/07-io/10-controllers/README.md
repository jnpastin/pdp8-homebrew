# I/O Controller Documentation

## 1. Purpose

This folder contains programmer-visible and architecturally relevant definitions for individual I/O controllers.

The common electrical-independent controller contract is defined in [Controller Contract](../04-controller-contract.md).

---

## 2. Controller Documents

- [KL8E-Compatible UART Controller](01-kl8e-uart.md)
- [PC8E-Compatible Paper-Tape Controller](02-pc8e-paper-tape.md)
- [RK8E-Compatible Storage Controller](03-rk8e-storage.md)

---

## 3. Required Controller Documentation

Each controller document must define:

- compatibility target
- default device address or addresses
- configurable-address behavior
- programmer-visible registers
- controller-local flags
- interrupt behavior
- interrupt-service identification and interrupt-condition clearing or servicing behavior, when the controller is interrupt-capable
- reset behavior
- complete IOT table
- IOT phase and TP behavior
- DB direction and ownership
- buffering behavior
- unsupported operation behavior
- DMA behavior when applicable
- physical implementation boundary

---

### 4. Interrupt-Service Documentation

Each interrupt-capable controller document must identify:

- the controller state that produces its interrupt contribution
- the existing IOT operation or operations used by software to test each interrupt condition
- the existing IOT operation or operations that clear or service each interrupt condition
- operations that inspect controller state without clearing the interrupt condition
- operations that may reestablish the interrupt condition
- the effect of servicing one condition when multiple controller conditions contribute to the same interrupt request
- the operation or state that enables or disables the controller interrupt contribution

This documentation coordinates the controller's existing instruction and state definitions for interrupt-service use. It must not create separate instruction semantics or redefine the behavior and timing specified elsewhere in the controller document.

---

## 5. Compatibility Rule

A controller claiming compatibility/equivalency with a DEC interface must reproduce:

- device addresses in the default compatibility configuration
- IOT encodings
- programmer-visible register widths
- programmer-visible bit assignments
- AC input and result behavior
- flag behavior
- skip behavior
- interrupt behavior
- reset behavior
- transfer completion behavior
- documented error behavior

The physical endpoint and internal implementation may differ when those differences are not programmer-visible.

