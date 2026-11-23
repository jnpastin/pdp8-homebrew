# DMA Execution

## 1. Purpose

Defines the execution behavior of the DMA major state.

During `MS = DMA` the CPU performs no datapath work. The selected controller and memory perform the single-word transfer; CPU control only releases the memory interface, asserts `/DMA_GRANT`, and selects the next major state.

The transfer itself is defined in:

- [Major State Timing §7](../09-timing/03-major-state-timing.md#7-dma)
- [DMA Interface](../07-io/05-dma-interface.md)
- [DMA Arbitration](../07-io/06-dma-arbitration.md)

---

## 2. Overview

DMA is entered only at instruction completion (the TP4 of the instruction's last major state), when no interrupt is taken and aggregate `/DMA_REQ` is asserted. Each DMA major state transfers at most one memory word.

Flow:

    instruction completion (FETCH, DEFER, or EXECUTE TP4) → DMA → (DMA while the burst continues) → FETCH

CPU control during DMA:

- asserts `/DMA_GRANT` while running
- holds its `MFB`, `AB`, `MDB`, `/RD`, and `/WR` drivers released
- selects `MS_NEXT` at TP4 from aggregate `/DMA_REQ`

No CPU register changes during DMA. No μop is selected in any timing state.

---

## 3. DMA Execution

### 3.1 TS1

μops:
- (no μops)

Description:
- The arbiter selects a controller, or keeps the selection of a continuing burst if its controller still requests; `DMA_GRANT_ID` commits at TP1. A held selection whose request is gone is dropped ([DMA Arbitration §13.3](../07-io/06-dma-arbitration.md#133-held-selection-without-a-request)).

---

### 3.2 TS2

μops:
- (no μops)

Description:
- The selected controller drives `MFB`, `AB`, and `/RD` or `/WR`, and `MDB` for a write; exactly one word transfers at TP2.

---

### 3.3 TS3

μops:
- (no μops)

Description:
- The controller updates its address and word count, and the arbiter its burst count, at TP3.

---

### 3.4 TS4

μops:
- (no μops)

Control Decisions:

    if /DMA_REQ asserted:
        MS_NEXT ← DMA
    else:
        MS_NEXT ← FETCH

Description:
- Continues the burst or returns to FETCH; see [Sequencing and Internal Control §3.2.9 and §3.2.10](../04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md#329-dma-continuation).

---

## 4. Halting Between DMA Cycles

Single Step halts at the end of every major state, including DMA ([Console Execution §13](./09-console-execution.md#13-single-step-mode)). STOP, HLT, and Single Instruction halt only at instruction completion, so they never halt inside a burst.

When Single Step halts at DMA TP4 while the burst continues, `MS` holds `DMA`:

- `/DMA_GRANT` is deasserted while halted, so no controller may drive the memory interface.
- The selected controller keeps its request and its prepared next transfer.
- The arbiter keeps `DMA_GRANT_ID`, its burst-enabled state, and its burst count.
- Console Examine and Deposit use the memory interface normally, and load FETCH as the held major state.
- CONTINUE, with no EXAMINE or DEPOSIT since the halt, resumes at DMA TS1 with `/DMA_GRANT` asserted, and the burst continues with the same selection.
- START, or CONTINUE after an EXAMINE or DEPOSIT, resumes at FETCH TS1. The selection is kept, and the burst continues at the next DMA entry, if its controller still requests then ([DMA Arbitration §13.3](../07-io/06-dma-arbitration.md#133-held-selection-without-a-request)).
- CLEAR initializes the controllers and the arbiter ([DMA Arbitration §13.2](../07-io/06-dma-arbitration.md#132-system-initialization)), so a later CONTINUE runs one DMA major state with no selected controller.

---

## 5. DMA Major State Without a Selected Controller

A DMA major state can begin with no pending request; for example, when CAF or CLEAR initializes the requesting controller after `/DMA_REQ` was sampled.

It can also begin with a held selection whose controller no longer requests, which TP1 drops ([DMA Arbitration §13.3](../07-io/06-dma-arbitration.md#133-held-selection-without-a-request)).

In either case:

- `DMA_GRANT_ID` is `15` from TP1
- no memory transfer occurs at TP2
- no controller or burst count changes at TP3, and the arbiter clears its retained burst-enabled state
- aggregate `/DMA_REQ` is deasserted during TS4, even if a new request has arrived, so control returns to FETCH at TP4
