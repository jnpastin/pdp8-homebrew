# 00 Abbreviation Dictionary

## Purpose

This document defines a global dictionary for all abbreviations used throughout the system design.

It serves as the single source of truth for:
- register names
- bus names
- control signals
- timing signals
- architectural and microarchitectural terms

All documents must reference these abbreviations to prevent ambiguity or collision.

---

## Naming Rules

- Abbreviations should be 2–4 characters where possible
- Must be unique across all categories
- Must be stable once defined
- Must not be reused with different meanings

---

## Buses (Class A)


AB   = [Address Bus](../05-buses-and-signals/01-class-a-buses.md#address-bus-ab) (AB[11:0])

DB   = [System Data Bus](../05-buses-and-signals/01-class-a-buses.md#system-data-bus-db) (DB[11:0])

MDB  = [Memory Data Bus](../05-buses-and-signals/01-class-a-buses.md#memory-data-bus-mdb) (MDB[11:0])

MFB  = [Memory Field Bus](../05-buses-and-signals/01-class-a-buses.md#mfb--memory-field) (MFB[2:0])

---

## Registers


AC   = [Accumulator](../01-architecture/01-registers.md#ac--accumulator)

DF   = [Data Field](../01-architecture/01-registers.md#df--data-field)

DIF  = [Deferred Instruction Field](../01-architecture/01-registers.md#dif--deferred-instruction-field)

EA_ADDR   = [Effective Address (Address Portion)](../01-architecture/01-registers.md#ea_addr--effective-address-address-portion)

IB   = [Interrupt Buffer](../01-architecture/01-registers.md#ib--interrupt-buffer)

IE   = [Interrupt Enable](../01-architecture/01-registers.md#ie--interrupt-enable)

IF   = [Instruction Field](../01-architecture/01-registers.md#if--instruction-field)

II   = [Interrupt Inhibit](../01-architecture/01-registers.md#ii--interrupt-inhibit)

IR   = [Instruction Register](../01-architecture/01-registers.md#ir--instruction-register)

L    = [Link](../01-architecture/01-registers.md#l--link)

MA   = [Memory Address](../01-architecture/01-registers.md#ma--memory-address)

MB   = [Memory Buffer](../01-architecture/01-registers.md#mb--memory-buffer)

MS   = [Major State](../01-architecture/01-registers.md#ms--major-state)

MQ   = [Multiplier Quotient](../01-architecture/01-registers.md#mq--multiplier-quotient)

PC   = [Program Counter](../01-architecture/01-registers.md#pc--program-counter)

SR   = [Switch Register](../01-architecture/01-registers.md#sr--switch-register)


---

## Global Control Signals (Class B)


DMA_REQ = [DMA Request](../04-control/10-control-input-definitions/04-external-inputs.md#dma_req) (wired-OR)

DMA_GRANT = [DMA Grant](../04-control/20-control-output/02-architectural-control-signals.md#dma_grant

RD      = [Memory Read](../04-control/20-control-output-definitions/02-architectural-control-signals.md#31-memory-read-rd)

WR      = [Memory Write](../04-control/20-control-output-definitions/02-architectural-control-signals.md#32-memory-write-wr)

RESET   = System Reset

INT_REQ = Interrupt Request (wired-OR)


---

## Timing Signals (Class C)


MCLK  = [Master Clock](../09-timing/01-terminology.md#11-master-clock-mclk)

TCLK  = [Timing Clock](../09-timing/01-terminology.md#12-timing-clock-tclk)

TSTEP = [Timing Step](../09-timing/01-terminology.md#21-timing-step-tstep)

TSEQ  = [Timing Sequence](../09-timing/01-terminology.md#22-timing-sequence-tseq)

TPn   = [Timing Pulse n](../09-timing/01-terminology.md#3-timing-pulses-tp)

TSn   = [Timing State n](../09-timing/01-terminology.md#4-time-states-ts)


---

## I/O Signals


IOA[5:0] = I/O Device Address Bus


---

## Front Panel Signals (Class D)
  
FP_START     = [Start Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_start)
 
FP_CONTINUE  = [Continue Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_continue)

FP_STOP      = [Stop Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_stop)

FP_LOAD_ADDRESS = [Load Address Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_load_address)

FP_EXAMINE   = [Examine Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_examine)

FP_DEPOSIT   = [Deposit Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_deposit)

FP_SINGLE_INSTRUCTION = [Single Instruction Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_single_instruction)

FP_SINGLE_STEP = [Single Step Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_single_step)

FP_IF        = [Instruction Field Switches](../04-control/10-control-input-definitions/04-external-inputs.md#fp_if)

FP_DF        = [Data Field Switches](../04-control/10-control-input-definitions/04-external-inputs.md#fp_df)

---

## Conventions

- Bracket notation indicates bus width (e.g., AB[11:0])
- Uppercase denotes signal-level identifiers
- Names reflect function, not implementation

---

## Constraints

- New abbreviations must be added here before use
- Existing abbreviations must not be redefined
- Collisions must be resolved by renaming before implementation

---

## Summary

This dictionary ensures consistency across:
- architecture definitions
- control logic
- hardware implementation
- documentation

It is authoritative and must be kept synchronized with all system specifications.
