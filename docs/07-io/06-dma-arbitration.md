# DMA Arbitration

## Purpose

This document defines external DMA requester selection, priority, grant identity, bounded bursts, CPU fairness, and grant release.

## Arbitration Boundary

DMA requester arbitration is external to the CPU.

The CPU observes one aggregate `DMA_REQ` input and produces CPU-level DMA availability through its existing DMA major-state behavior. The CPU does not identify or select an individual DMA controller.

A distinct DMA arbiter subsystem selects the requesting controller. The architecture does not require the arbiter to occupy a separate physical card.

## Priority Channels

The DMA interface provides 15 configurable priority channels through DMA_REQ[14:0].  
Each DMA-capable controller is configured to assert exactly one request line.

Properties:

- Valid DMA priority identifiers are 0 through 14.
- DMA priority identifier 15 is reserved as the no-controller-selected encoding.
- No DMA_REQ line exists for priority 15.
- Priority is independent of IOA.
- The configured priority remains stable while the controller requests service.
- Two installed controllers must not use the same active priority channel.
- Lower numerical DMA priority identifiers have higher priority.
- DMA priority 0 is the highest priority.
- DMA priority 14 is the lowest assignable priority.

## Grant Interface

CPU control produces DMA_GRANT.  
DMA_GRANT indicates that the CPU has released the memory interface during MS = DMA.  
DMA_GRANT does not identify or select an individual controller.

The arbiter produces DMA_GRANT_ID[3:0].  
DMA_GRANT_ID identifies the selected priority channel.

DMA_GRANT_ID values have the following meanings:

- 0 through 14: valid selected priority channel
- 15: no controller selected

The arbiter must drive DMA_GRANT_ID to 15 whenever no valid controller selection exists.

A controller accepts DMA ownership only when:

```text
DMA_GRANT = 1
AND
DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

No controller may be configured with priority 15.  
No controller accepts DMA ownership while DMA_GRANT_ID is 15.  
Exactly one controller may accept a valid controller selection.

## Selection Policy

The arbiter uses fixed numerical priority.

Rules:

- Lower numerical DMA priority identifiers have higher priority.
- DMA priority 0 is the highest priority.
- DMA priority 14 is the lowest assignable priority.
- The lowest-numbered asserted request wins.
- Arbitration occurs only when no controller is selected.
- An active controller selection is non-preemptive.
- A higher-priority request arriving during a burst waits until that burst ends.
- Priority is reevaluated between bursts.

## Controller Operation Count

Each controller maintains its complete-operation address and remaining word count.

The controller keeps its request line asserted while additional DMA work remains pending. It deasserts the request when the complete operation finishes or is canceled.

## Arbiter Burst Count

The DMA arbiter maintains:

- active controller selection
- active DMA_GRANT_ID
- per-priority configured burst limit
- words completed during the current selection

Every valid controller selection completes exactly one DMA word transfer at TP2.  
The arbiter burst count increments at TP3 for the word transferred at TP2.

The arbiter terminates the active controller selection when:

- the selected controller no longer requests service after completing the current transfer
- the configured burst limit is reached
- the selected controller releases early after completing the current transfer

A controller may release early only after completing the transfer for which it was selected.  
A controller with remaining work keeps its request asserted only while another transfer is immediately ready.  
Otherwise, it deasserts its request and competes again after the next transfer is prepared.

### Configurable Burst Limits

Burst limits may differ by priority channel.  
Each configured burst limit must permit at least one completed DMA word transfer.  
A burst limit of zero is invalid.  
The architectural contract requires bounded bursts and forward progress for each valid controller selection.  
Configuration technology, counter width, and the maximum supported burst length belong to the physical implementation specification.  
The arbiter, not the requesting controller, enforces the active selection's burst limit.

## CPU Fairness

One CPU instruction is guaranteed between completed DMA bursts.

At the end of a burst:

- the arbiter deasserts aggregate `DMA_REQ` during DMA TS4
- CPU control commits `MS_NEXT = FETCH` at DMA TP4
- pending controller request lines may remain asserted
- aggregate `DMA_REQ` may be reasserted after entry to FETCH because DMA eligibility is not evaluated again until the following instruction's EXECUTE TP4

No CPU control or `MS_NEXT` extension is required. The arbiter implements the fairness policy through aggregate `DMA_REQ`.

## Grant Release Ordering

When a controller selection terminates:

- The arbiter determines termination before TP4.
- The previously selected controller releases MFB, AB, MDB, RD, and WR at TP4.
- The arbiter sets DMA_GRANT_ID to 15 at the same boundary.
- Aggregate DMA_REQ is already deasserted for the CPU decision made at TP4.
- CPU control deasserts DMA_GRANT when control exits MS = DMA.
- CPU ownership begins in the following FETCH TS1.

CPU and DMA ownership must not overlap.

## Related Documents

- [DMA Interface](./05-dma-interface.md)
- [Controller Contract](./04-controller-contract.md)
- [Invalid Conditions](./07-invalid-conditions.md)
