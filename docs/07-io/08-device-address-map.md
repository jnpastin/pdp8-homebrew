# Device Address Map

## Purpose

This document defines the authoritative allocation of six-bit I/O device addresses.

All addresses are expressed in octal.

---

## Addressing Rules

- Each installed external controller has one active configured address for each device interface it implements.
- Address configuration is independent of physical backplane position.
- DEC-compatible controllers default to the standard address of the emulated DEC interface.
- Alternate addresses are permitted when the controller supports configuration and the associated software uses the configured address.
- Two installed controllers must not respond to the same active address.
- CPU-internal device addresses are unavailable to external controllers.
- An IOT to an unassigned address is ignored.

---

## P1 Address Assignments

| Address | Controller | Function | Compatibility |
|---:|---|---|---|
| `00` | CPU | CPU-internal IOT operations | PDP-8/E |
| `01` | Paper-tape controller | High-speed paper-tape reader | PC8E |
| `02` | Paper-tape controller | High-speed paper-tape punch | PC8E |
| `03` | Console controller | Console UART input | KL8E |
| `04` | Console controller | Console UART output | KL8E |
| `20` through `27` | CPU | Memory-extension IOT operations | PDP-8/E |
| `74` | Storage controller | RK05-compatible disk control | RK8E |

---

## Unassigned Addresses

All addresses not explicitly assigned or reserved in this document are unassigned.

An IOT to an unassigned address produces no controller response:

- no DB drive
- no DB capture
- no AC-clear request
- no skip request
- no wait request
- no controller state change
- no interrupt effect
- no DMA effect

---

## Unsupported Operations

An unsupported IOP value at an assigned address is ignored and produces the same result as an unassigned address.

