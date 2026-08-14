# DMA Arbitration

## Purpose

This document defines external DMA requester selection, priority, grant identity, bounded bursts, CPU fairness, and grant release.

## Arbitration Boundary

DMA requester arbitration is external to the CPU.

The CPU observes one aggregate `DMA_REQ` input and produces CPU-level DMA availability through its existing DMA major-state behavior. The CPU does not identify or select an individual DMA controller.

A distinct DMA arbiter subsystem selects the requesting controller. The architecture does not require the arbiter to occupy a separate physical card.

## Priority Channels

The DMA interface supports 16 configurable priority channels:

```text
DMA_REQ[15:0]
```

Each DMA-capable controller is configured to assert exactly one request line.

Properties:

- Priority is independent of IOA.
- Higher and lower numerical priority ordering must be defined consistently by the implementation.
- The configured priority remains stable while the controller requests service.
- Two installed controllers must not use the same active priority channel.

## Grant Interface

The arbiter returns:

```text
DMA_GRANT
DMA_GRANT_ID[3:0]
```

`DMA_GRANT_ID` identifies the selected priority channel.

A controller accepts the grant only when:

```text
DMA_GRANT = 1
AND DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

Exactly one controller may accept an active grant.

## Selection Policy

The arbiter uses configurable fixed priority.

Rules:

- The highest-priority asserted request wins.
- Arbitration occurs only when no controller-specific grant is active.
- An active grant is non-preemptive.
- A higher-priority request arriving during a burst waits until that burst ends.
- Priority is reevaluated between bursts.

## Controller Operation Count

Each controller maintains its complete-operation address and remaining word count.

The controller keeps its request line asserted while additional DMA work remains pending. It deasserts the request when the complete operation finishes or is canceled.

## Arbiter Burst Count

The DMA arbiter maintains:

- active grant state;
- active `DMA_GRANT_ID`;
- per-priority configured burst limit;
- words completed during the current grant.

The arbiter burst count increments at TP3 for the word transferred at TP2.

The arbiter terminates the active grant when:

- the selected controller no longer requests service
- the configured burst limit is reached
- the selected controller releases early

A controller with remaining work keeps its request asserted and competes again after grant release.

## Configurable Burst Limits

Burst limits may differ by priority channel.

The architectural contract requires bounded bursts. Configuration technology, counter width, and absolute maximum burst length belong to the physical implementation specification.

The arbiter, not the requesting controller, enforces the active grant's burst limit.

## CPU Fairness

One CPU instruction is guaranteed between completed DMA bursts.

At the end of a burst:

- the arbiter deasserts aggregate `DMA_REQ` during DMA TS4
- CPU control commits `MS_NEXT = FETCH` at DMA TP4
- pending controller request lines may remain asserted
- aggregate `DMA_REQ` may be reasserted after entry to FETCH because DMA eligibility is not evaluated again until the following instruction's EXECUTE TP4

No CPU control or `MS_NEXT` extension is required. The arbiter implements the fairness policy through aggregate `DMA_REQ`.

## Grant Release Ordering

When a grant terminates:

1. The arbiter determines termination before TP4.
2. Controller-facing `DMA_GRANT` becomes inactive at TP4.
3. The previously granted controller releases MFB, AB, MDB, RD, and WR at the same boundary.
4. Aggregate `DMA_REQ` is already deasserted for the CPU decision made at TP4.
5. CPU ownership begins in the following FETCH TS1.

CPU and DMA ownership must not overlap.

## Related Documents

- [DMA Interface](./05-dma-interface.md)
- [Controller Contract](./04-controller-contract.md)
- [Invalid Conditions](./07-invalid-conditions.md)
