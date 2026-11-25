# I/O Controller Models

## 1. Purpose

Models of I/O controllers at the external-IOT interface, at the same timing-state level as the CPU simulator: each controller sees `IOT_ACTIVE`, `IOA`, `IOP`, and the TS, drives its response inputs (`IO_READ_REQ`, `IO_WRITE_REQ`, `IO_SKIP_REQ`, `IO_CLEAR_AC_REQ`, DB, and its interrupt contribution), and commits its state at the TP its contract names ([External IOT Interface](../../docs/07-io/02-external-iot-interface.md), [Controller Contract](../../docs/07-io/04-controller-contract.md)).

## 2. Interface

A controller provides:

| Method | Called |
|---|---|
| `present(bus) -> Response` | at the start of every TS and console transaction, before the control store is addressed |
| `commit(bus, tp, db_write, initialize)` | at every TP (`tp` = 1–4) and `TP_FP` (`tp` = "C"); `initialize` is true when `/INITIALIZE` is asserted |
| `initialize()` | at power-on |
| `at_boundary()` (optional) | after each TP4 that completes an instruction (`INSTR_END`) and after INTERRUPT TP4 (not DMA) |

The CPU combines the responses of every controller with any test stimulus: `/INT_REQ` is asserted if any controller requests, and two controllers driving DB at once is a `SpecViolation`.

## 3. KL8E

`pdp8_io.KL8E` implements [KL8E-Compatible UART Controller](../../docs/07-io/10-controllers/01-kl8e-uart.md): device 03 (KCF, KSF, KCC, KRS, KIE, KRB) and device 04 (TFL, TSF, TCF, TPC, TSK, TLS), the shared interrupt enable (set at initialization, §8), and the request and commit point of each IOT.

How output completes is outside the controller contract (§17.4). The model completes an accepted character after `output_delay` instruction boundaries (default 3), counted by `at_boundary()`, so the instruction-level KL8E in the reference model completes it at the same instruction. Completed characters are appended to `printed`. `type_character(c)` presents a keyboard character at once, as if it had arrived at an earlier TP. `arrive_at_next_tp(c)` presents it at the next TP, after that TP's IOT clears, so a character arriving at the TP of a KCF or KCC sets the flag ([Controller Contract §5.1](../../docs/07-io/04-controller-contract.md#51-event-and-clear-at-the-same-tp)).

## 4. DMA

`pdp8_io.DmaArbiter` is the DMA arbiter of [DMA Arbitration](../../docs/07-io/06-dma-arbitration.md), a system component outside the CPU. It provides fixed priority (lowest number first), non-preemptive bursts bounded by a per-channel limit, `DMA_ENABLE` (the TS4 in which `INSTR_END` is asserted, then the retained burst-enabled state), the aggregate `/DMA_REQ`, `DMA_GRANT_ID` (15 when nothing is selected), and initialization. The CPU passes it the major-state context, reads its aggregate request, and, while `/DMA_GRANT` is asserted, performs the selected controller's memory transfer at DMA TP2 ([DMA Interface](../../docs/07-io/05-dma-interface.md) §6). A DMA controller provides `dma_priority`, `dma_request()`, `dma_operation()`, `dma_transferred(value)` (TP2), `dma_advance()` (TP3), and `initialize()`.

`pdp8_io.DmaTestMaster` is test equipment, not a device model. It performs a queue of prepared single-word transfers, loaded by `load()` or at an instruction boundary by `schedule`, and follows the DMA controller contract: it requests only while its next transfer is prepared, completes one word per selection, and deasserts after its last word before the TP3 update. It has no IOTs or interrupt. The DMA logic is validated against real devices later, with the RK8E diagnostics and the DECX8 RK8 exerciser.

## 5. Testing

`tests/test_kl8e.py` drives the controller on its own at the external-IOT interface, with no CPU, checking each rule of the KL8E document: every IOT's requests and commits, the busy and discard rules, the interrupt contribution, initialization, and selection. The controller is also tested through the CPU, in lock-step with the reference model's KL8E: `sim/system/tests/test_kl8e.py`, and MAINDEC-8E-D0BB in `sim/system/tests/test_maindec.py`.

`tests/test_dma.py` drives the arbiter and the test master with no CPU, checking DMA Arbitration's enable, aggregation, selection, non-preemption, burst-limit and fairness, and initialization rules, and the master's request timing. DMA through the control store is tested in lock-step in `sim/system/tests/test_dma.py`.
