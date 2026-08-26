# DMA Arbitration

## Purpose

This document defines external DMA requester selection, priority, grant identity, bounded bursts, CPU fairness, and grant release.

## Arbitration Boundary

DMA requester arbitration is external to the CPU.

The CPU observes one aggregate `/DMA_REQ` input and produces CPU-level DMA availability through its existing DMA major-state behavior. The CPU does not identify or select an individual DMA controller.

A distinct DMA arbiter subsystem selects the requesting controller. The architecture does not require the arbiter to occupy a separate physical card.

## Arbiter-Local State

The DMA arbiter maintains:

- `DMA_ENABLE`
- active `DMA_GRANT_ID[3:0]`
- active burst count
- configured burst limit for each DMA priority channel

`DMA_ENABLE` controls whether pending controller requests may contribute to the aggregate CPU-facing `/DMA_REQ`.

`DMA_ENABLE` is internal to the DMA arbiter.  
It is not an architectural backplane signal and is not visible to DMA controllers or CPU control.

Encoding:

- `DMA_ENABLE = 0`: pending controller requests are inhibited from asserting aggregate `/DMA_REQ`
- `DMA_ENABLE = 1`: pending controller requests may assert aggregate `/DMA_REQ`

## Priority Channels

The DMA interface provides 15 configurable priority channels through /DMA_REQ[14:0].  
Each DMA-capable controller is configured to assert exactly one request line.

Properties:

- Valid DMA priority identifiers are 0 through 14.
- DMA priority identifier 15 is reserved as the no-controller-selected encoding.
- No /DMA_REQ line exists for priority 15.
- Priority is independent of IOA.
- The configured priority remains stable while the controller requests service.
- Two installed controllers must not use the same active priority channel.
- Lower numerical DMA priority identifiers have higher priority.
- DMA priority 0 is the highest priority.
- DMA priority 14 is the lowest assignable priority.

## Aggregate DMA Request

The controller request lines are active-low:

```text
/DMA_REQ[14:0]
```

The arbiter derives:

```text
ANY_CONTROLLER_REQUEST_ASSERTED =
    (/DMA_REQ[0] = 0)
    OR
    (/DMA_REQ[1] = 0)
    OR
    ...
    OR
    (/DMA_REQ[14] = 0)
```

The aggregate CPU-facing request is active-low:

```text
/DMA_REQ =
    NOT (
        DMA_ENABLE
        AND
        ANY_CONTROLLER_REQUEST_ASSERTED
    )
```

Therefore:

- aggregate `/DMA_REQ` is asserted when `DMA_ENABLE = 1` and at least one controller request is asserted
- aggregate `/DMA_REQ` is deasserted when `DMA_ENABLE = 0`
- aggregate `/DMA_REQ` is deasserted when no controller request is asserted
- controller request lines may remain asserted while aggregate `/DMA_REQ` is deasserted
- aggregate `/DMA_REQ` is not a direct electrical wired combination of `/DMA_REQ[14:0]`

## Grant Interface

CPU control produces /DMA_GRANT.  
/DMA_GRANT indicates that the CPU has released the memory interface during MS = DMA.  
/DMA_GRANT does not identify or select an individual controller.

The arbiter produces DMA_GRANT_ID[3:0].  
DMA_GRANT_ID identifies the selected priority channel.

DMA_GRANT_ID values have the following meanings:

- 0 through 14: valid selected priority channel
- 15: no controller selected

The arbiter must drive DMA_GRANT_ID to 15 whenever no valid controller selection exists.

A controller accepts DMA ownership only when:

```text
/DMA_GRANT = 0
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
- active `DMA_GRANT_ID`
- per-priority configured burst limit
- words completed during the current selection

Every valid controller selection completes exactly one DMA word transfer at TP2.  
The arbiter burst count increments at TP3 for the word transferred at TP2.

During DMA TS3, the arbiter determines whether the active burst terminates after the completed TP2 transfer.

The active burst terminates when:

- the selected controller no longer requests service
- the configured burst limit has been reached
- the selected controller has no immediately transferable next word

At DMA TP3:

- the active burst count increments for the transfer completed at TP2
- `DMA_ENABLE` clears when the active burst terminates
- `DMA_ENABLE` remains set when the active burst continues

A controller may release its request only after completing the transfer for which it was selected.  
A controller with remaining work keeps its request asserted only while another transfer is immediately ready.  
Otherwise, it deasserts its request and requests service again when the next transfer is prepared.

### Configurable Burst Limits

Burst limits may differ by priority channel.  
Each configured burst limit must permit at least one completed DMA word transfer.  
A burst limit of zero is invalid.  
The architectural contract requires bounded bursts and forward progress for each valid controller selection.  
Configuration technology, counter width, and the maximum supported burst length belong to the physical implementation specification.  
The arbiter, not the requesting controller, enforces the active selection's burst limit.

## CPU Fairness

At least one complete CPU instruction executes between completed DMA bursts.

When a DMA burst terminates:

- the arbiter clears `DMA_ENABLE` at DMA TP3
- aggregate `/DMA_REQ` becomes deasserted regardless of pending controller requests
- CPU control observes aggregate `/DMA_REQ` deasserted during DMA TS4
- CPU control commits `MS_NEXT = FETCH` at DMA TP4
- pending `/DMA_REQ[n]` lines may remain asserted
- the active controller selection terminates at DMA TP4

Execution then proceeds through:

```text
FETCH
-> DEFER, when required
-> EXECUTE
```

At the TP4 that completes EXECUTE:

```text
DMA_ENABLE <- 1
```

`DMA_ENABLE` is set unconditionally at every EXECUTE TP4.

If one or more controller request lines remain asserted, setting `DMA_ENABLE` causes aggregate `/DMA_REQ` to assert after EXECUTE TP4.  
DMA eligibility is then evaluated according to the normal major-state transition rules.

FETCH and DEFER do not set `DMA_ENABLE`.

## Grant Release Ordering

When a controller selection terminates:

- the arbiter determines termination during DMA TS3
- `DMA_ENABLE` clears at DMA TP3
- aggregate `/DMA_REQ` is deasserted during DMA TS4
- the previously selected controller releases MFB, AB, MDB, `/RD`, and `/WR` at DMA TP4
- the arbiter sets `DMA_GRANT_ID` to 15 at DMA TP4
- CPU control deasserts `/DMA_GRANT` when control exits `MS = DMA`
- CPU ownership begins in the following FETCH TS1

CPU and DMA ownership must not overlap.

## Related Documents

- [DMA Interface](./05-dma-interface.md)
- [Controller Contract](./04-controller-contract.md)
- [Invalid Conditions](./07-invalid-conditions.md)
