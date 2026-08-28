# DMA Arbitration

## 1. Purpose

This document defines external DMA requester selection, priority, grant identity, bounded bursts, CPU fairness, and grant release.

---

## 2. Arbitration Boundary

DMA requester arbitration is external to the CPU.

The CPU observes one aggregate `/DMA_REQ` input and produces CPU-level DMA availability through its existing DMA major-state behavior. The CPU does not identify or select an individual DMA controller.

A distinct DMA arbiter subsystem selects the requesting controller. The architecture does not require the arbiter to occupy a separate physical card.

---

## 3. Major-State Visibility

The CPU provides `MS[2:0]`, TS, and TP timing context to the DMA arbiter.

The arbiter uses this context to:

- identify DMA TP3 for burst-termination state updates
- identify EXECUTE TS4 for DMA reenable
- identify TP4 as the CPU sampling boundary for aggregate `/DMA_REQ`

The DMA arbiter must not:

- modify `MS`
- influence `MS` encoding
- use `MS` to select a DMA controller
- infer DMA ownership from `MS` alone

DMA ownership requires:

```text
MS = DMA
AND
/DMA_GRANT = 0
AND
DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

---

## 4. Arbiter-Local State

The DMA arbiter maintains:

- DMA burst-enabled state
- active `DMA_GRANT_ID[3:0]`
- active burst count
- configured burst limit for each DMA priority channel

Arbiter state changes only at TP events.

The retained DMA burst-enabled state:

- remains set while the current DMA burst may continue
- clears at DMA TP3 when the current burst terminates
- sets at EXECUTE TP4

---

## 5. DMA_ENABLE Output

`DMA_ENABLE` is a combinational arbiter output used by the aggregate DMA-request logic.

During EXECUTE TS4:

```text
DMA_ENABLE = 1
```

During an active DMA burst:

```text
DMA_ENABLE = DMA_BURST_ENABLED
```

During FETCH, DEFER, INTERRUPT, and non-TS4 portions of EXECUTE:

```text
DMA_ENABLE = 0
```

`DMA_ENABLE` does not itself contain state. It reflects the applicable retained arbiter state or the EXECUTE TS4 reenable condition.

`DMA_ENABLE` must settle before TP4 whenever CPU control samples aggregate `/DMA_REQ`.

---

## 6. Priority Channels

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

---

## 7. Aggregate DMA Request

Each DMA-capable controller provides one active-low request line:

```text
/DMA_REQ[14:0]
```

The controller request lines and `DMA_ENABLE` feed separate combinational aggregation logic.

The aggregation logic derives:

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

The active-low aggregate CPU-facing request is:

```text
/DMA_REQ =
    NOT (
        DMA_ENABLE
        AND
        ANY_CONTROLLER_REQUEST_ASSERTED
    )
```

During a CPU major state:

- controllers may assert or deassert their `/DMA_REQ[n]` lines according to their controller contracts
- the arbiter establishes `DMA_ENABLE`
- the aggregation logic continuously derives aggregate `/DMA_REQ`
- `/DMA_REQ[n]`, `DMA_ENABLE`, and aggregate `/DMA_REQ` must settle before the TP4 sampling boundary

At TP4, CPU control samples aggregate `/DMA_REQ` as an input to the major-state transition decision.

Aggregate `/DMA_REQ` is:

- asserted when `DMA_ENABLE = 1` and at least one controller request is asserted
- deasserted when `DMA_ENABLE = 0`
- deasserted when no controller request is asserted
- a single combinational result, not a wired combination of `/DMA_REQ[14:0]`

Controller `/DMA_REQ[n]` lines may remain asserted while aggregate `/DMA_REQ` is deasserted.

---

## 8. Grant Interface

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

---

## 9. Selection Policy

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

---

## 10. Controller Operation Count

Each controller maintains its complete-operation address and remaining word count.

The controller keeps its request line asserted while additional DMA work remains pending. It deasserts the request when the complete operation finishes or is canceled.

---

## 11. Arbiter Burst Count

The DMA arbiter maintains:

- active controller selection
- active `DMA_GRANT_ID`
- configured burst limit for the selected priority
- words completed during the current burst

Every valid controller selection completes exactly one DMA word transfer at TP2. 

The resulting retained state determines `DMA_ENABLE` during the following DMA TS4.

The burst terminates when:

- the selected controller has deasserted its request
- the completed transfer reaches the configured burst limit

At DMA TP3:

- the active burst count increments for the transfer completed at TP2
- `DMA_ENABLE` clears when the burst terminates
- `DMA_ENABLE` remains set when the burst continues

A controller may deassert its request only after completing the transfer for which it was selected. A controller with remaining work keeps its request asserted only while another transfer is immediately ready. Otherwise, it deasserts its request and requests service again when the next transfer is prepared.

### 11.1 Configurable Burst Limits

Burst limits may differ by priority channel.  
Each configured burst limit must permit at least one completed DMA word transfer.  
A burst limit of zero is invalid.  
The architectural contract requires bounded bursts and forward progress for each valid controller selection.  
Configuration technology, counter width, and the maximum supported burst length belong to the physical implementation specification.  
The arbiter, not the requesting controller, enforces the active selection's burst limit.

---

## 12. CPU Fairness

At least one complete CPU instruction executes between completed DMA bursts.

When a DMA burst terminates:

- the arbiter clears retained DMA burst-enabled state at DMA TP3
- `DMA_ENABLE` becomes deasserted during DMA TS4
- aggregate `/DMA_REQ` becomes deasserted regardless of pending controller requests
- CPU control samples aggregate `/DMA_REQ` at DMA TP4
- CPU control commits `MS_NEXT = FETCH`
- pending controller `/DMA_REQ[n]` lines may remain asserted
- the active controller selection terminates at DMA TP4

Execution then proceeds through:

```text
FETCH
-> DEFER, when required
-> EXECUTE
```

`DMA_ENABLE` remains deasserted during FETCH, optional DEFER, and EXECUTE TS1 through TS3.

During EXECUTE TS4:

```text
DMA_ENABLE = 1
```

Controllers may assert pending `/DMA_REQ[n]` lines during EXECUTE TS4. The combinational aggregation logic continuously derives aggregate `/DMA_REQ` from `DMA_ENABLE` and `/DMA_REQ[14:0]`.

All inputs to the aggregation logic and the resulting aggregate `/DMA_REQ` must settle before TP4.

At EXECUTE TP4:

- CPU control samples aggregate `/DMA_REQ` for the major-state transition decision
- the arbiter sets retained DMA burst-enabled state
- CPU control may commit `MS_NEXT = DMA` when aggregate `/DMA_REQ` is asserted

The TP4 transition decision uses the aggregate `/DMA_REQ` value established during TS4. It does not depend on retained state committed at TP4.

---

## 13. Grant Release Ordering

When a controller selection terminates:

- the arbiter determines termination during DMA TS3
- retained DMA burst-enabled state clears at DMA TP3
- combinational `DMA_ENABLE` is deasserted during the following DMA TS4
- aggregate `/DMA_REQ` is deasserted during DMA TS4
- the previously selected controller releases MFB, AB, MDB, `/RD`, and `/WR` at DMA TP4
- the arbiter sets `DMA_GRANT_ID` to `15` at DMA TP4
- CPU control deasserts `/DMA_GRANT` when control exits `MS = DMA`
- CPU ownership begins in the following FETCH TS1

CPU and DMA ownership must not overlap.

---

## 14. Invariants

- Arbiter state changes only at TP events.
- Retained DMA burst-enabled state clears at DMA TP3 when the current burst terminates.
- Retained DMA burst-enabled state remains set at DMA TP3 when the current burst continues.
- Retained DMA burst-enabled state sets at EXECUTE TP4.
- `DMA_ENABLE` is a combinational arbiter output, not stored state.
- `DMA_ENABLE` is asserted during EXECUTE TS4.
- `DMA_ENABLE` is deasserted during FETCH, DEFER, INTERRUPT, and EXECUTE TS1 through TS3.
- Aggregate `/DMA_REQ` is continuously derived from `DMA_ENABLE` and `/DMA_REQ[14:0]`.
- Aggregate `/DMA_REQ` must settle before CPU control samples it at TP4.
- CPU control uses the pre-TP4 aggregate `/DMA_REQ` value for the TP4 major-state transition.
- Controller `/DMA_REQ[n]` lines may remain asserted while aggregate `/DMA_REQ` is deasserted.
- A completed DMA burst cannot be followed by another DMA major state until one complete CPU instruction reaches EXECUTE TP4.
- `MS` is visible to the DMA arbiter as a CPU-generated control field.
- The DMA arbiter does not modify or participate in generating `MS`.
- The DMA arbiter uses `MS = EXECUTE` and `TS4` to assert combinational `DMA_ENABLE`.
- EXECUTE TP4 sets retained DMA burst-enabled state; it does not directly set `DMA_ENABLE`.
- `MS = DMA` does not grant ownership unless `/DMA_GRANT` is also asserted.

---

## 15. Related Documents

- [DMA Interface](./05-dma-interface.md)
- [Controller Contract](./04-controller-contract.md)
- [Invalid Conditions](./07-invalid-conditions.md)
