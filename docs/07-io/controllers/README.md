## I/O Controller Documentation

### Purpose

This folder contains programmer-visible and architecturally relevant definitions for individual I/O controllers.

The common electrical-independent controller contract is defined in [Controller Contract](04-controller-contract.md).

### Controller Documents

- 01-kl8e-uart.md
- [PC8E-Compatible Paper-Tape Controllere.md

### Required Controller Documentation

Each controller document must define:

- compatibility target
- default device address or addresses
- configurable-address behavior
- programmer-visible registers
- controller-local flags
- interrupt behavior
- reset behavior
- complete IOT table
- IOT phase and TP behavior
- DB direction and ownership
- buffering behavior
- unsupported operation behavior
- DMA behavior when applicable
- physical implementation boundary

### Compatibility Rule

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

