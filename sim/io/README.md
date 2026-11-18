# I/O Controller Models

## 1. Purpose

Models of I/O controllers at the external-IOT interface, at the same timing-state level as the CPU simulator: each controller sees `IOT_ACTIVE`, `IOA`, `IOP`, and the TS, drives its response inputs (`IO_READ_REQ`, `IO_WRITE_REQ`, `IO_SKIP_REQ`, `IO_CLEAR_AC_REQ`, DB, and its interrupt contribution), and commits its state at the TP its contract names ([External IOT Interface](../../docs/07-io/02-external-iot-interface.md), [Controller Contract](../../docs/07-io/04-controller-contract.md)).

## 2. Interface

A controller provides:

| Method | Called |
|---|---|
| `present(bus) -> Response` | at the start of every TS and console transaction, before the control store is addressed |
| `commit(bus, tp, db_write, initialize)` | at every TP (`tp` = 1–4) and TPC (`tp` = "C"); `initialize` is true when `/INITIALIZE` is asserted |
| `initialize()` | at power-on |
| `at_boundary()` (optional) | after the TP4 of every EXECUTE or INTERRUPT major state |

The CPU combines the responses of every controller with any test stimulus: `/INT_REQ` is asserted if any controller requests, and two controllers driving DB at once is a `SpecViolation`.

## 3. KL8E

`pdp8_io.KL8E` implements [KL8E-Compatible UART Controller](../../docs/07-io/10-controllers/01-kl8e-uart.md): device 03 (KCF, KSF, KCC, KRS, KIE, KRB) and device 04 (TFL, TSF, TCF, TPC, TSK, TLS), the shared interrupt enable (set at initialization, §8), and the request and commit point of each IOT.

How output completes is outside the controller contract (§17.4). The model completes an accepted character after `output_delay` instruction boundaries (default 3), counted by `at_boundary()`, so the instruction-level KL8E in the reference model completes it at the same instruction. Completed characters are appended to `printed`. `type_character(c)` presents a keyboard character.

## 4. Testing

The controller is tested through the CPU, in lock-step with the reference model's KL8E: `sim/system/tests/test_kl8e.py`, and MAINDEC-8E-D0BB in `sim/system/tests/test_maindec.py`.
