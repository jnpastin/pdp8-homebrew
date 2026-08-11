## IOT Instruction Detail

### Purpose

Defines the CPU-internal IOT instructions decoded directly by the processor.

IOT instructions (opcode 6) fall into two categories:
- External device IOTs, interpreted by an individual device controller. These are not defined here; see the device documentation in [Section 7](../07-io/README.md).
- CPU-internal IOTs, decoded by the processor itself. These are defined in this document.

This document defines encoding and observable semantics only. Micro-operation sequences are defined in [IOT Execution](../03-microarchitecture/06-iot-execution.md).

### Scope

Applies to instructions where IR[11:9] = 110 and the device address selects a CPU-internal function:
- Device 0 - processor IOTs (interrupt and flag control)
- Devices 20-27 - memory extension control (field instructions)

The IOT bit format (opcode, 6-bit device address, 3-bit operation) is defined in the [encoding model](./00-encoding-model.md).

All device-0 and memory-extension instructions listed here are PDP-8/E processor features. The memory-extension instructions additionally require the memory-extension option.


---

### Device 0 - Processor IOTs

These instructions control the interrupt system. They are decoded when IR[11:9] = 110 and IR[8:3] = 000000 (device address 0). The specific operation is selected by the value of IR[2:0].

┌────┬────┬────┬────┬────┬────┬────┬────┬────┬─────┬─────┬─────┐
│ 11 │ 10 │ 9  │ 8  │ 7  │ 6  │ 5  │ 4  │ 3  │  2  │  1  │  0  │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼─────┼─────┼─────┤
│ 1  │ 1  │ 0  │ 0  │ 0  │ 0  │ 0  │ 0  │ 0  │     │     │     │
├────┴────┴────┼────┴────┴────┴────┴────┴────┼─────┴─────┴─────┤
│     IOT      │        Device 0 (CPU)       │    Operation    │
└──────────────┴─────────────────────────────┴─────────────────┘

Unlike the field instructions and Group 1 OPR, these are distinct operations selected by the IR[2:0] value; they are not independent flags and may not be combined.

| Mnemonic | Octal | IR[2:0] | Name | Operation |
|---|---|---|---|---|
| SKON | 6000 | 000 | Skip if Interrupt On | Skip the next instruction if the interrupts are enabled, then disable interrupts |
| ION | 6001 | 001 | Interrupt On | Enable Interrupts |
| IOF | 6002 | 010 | Interrupt Off | Disable Interrupts |
| SRQ | 6003 | 011 | Skip on Interrupt Request | Skip the next instruction if an interrupt request is currently asserted |

Semantics:
- ION turns interrupts on, but the effect is deferred by one instruction: the instruction immediately following ION always executes before any interrupt can be recognized. This lets a routine execute ION followed by a return (for example, JMP I) without being interrupted between the two.
- IOF turns interrupts off immediately.
- SKON tests the interrupt state and turns interrupts off in a single instruction. It skips if interrupts were on. This provides a way to save and disable interrupt state together.
- SRQ tests whether any device is currently requesting an interrupt, without affecting interrupt state. It is used by software polling routines.

---

### Devices 20-27 - Memory Extension Control

These instructions manage the instruction field (IF) and data field (DF) for extended memory addressing. They are decoded when IR[11:9] = 110 and IR[8:6] = 010.

#### Field-Change Instructions (CDF, CIF)

The target field n is encoded in IR[5:3], making the device address 2n. The two low operation bits are independent flags: CDF (bit 0) and CIF (bit 1).

┌────┬────┬────┬────┬────┬────┬─────┬─────┬─────┬────┬─────┬─────┐
│ 11 │ 10 │ 9  │ 8  │ 7  │ 6  │  5  │  4  │  3  │ 2  │  1  │  0  │
├────┼────┼────┼────┼────┼────┼─────┼─────┼─────┼────┼─────┼─────┤
│ 1  │ 1  │ 0  │ 0  │ 1  │ 0  │     │     │     │ 0  │ CIF │ CDF │
├────┴────┴────┼────┴────┴────┼─────┴─────┴─────┼────┼─────┼─────┤
│     IOT      │     MEM      │      Field      │    │     │     │
└──────────────┴──────────────┴─────────────────┴────┴─────┴─────┘

| Flag | Bit | Name | Operation |
|---|---|---|---|
| CDF | 0 | Change Data Field | DF <- Field (immediate) |
| CIF | 1 | Change Instruction Field | IF <- Field, applied at the next JMP or JMS (deferred) |

Like Group 1 OPR, CDF and CIF are independent flags that may be combined (ORed) into a single instruction. The Field value (IR[5:3]) is shared by both flags.

- CDF alone (62n1): loads DF immediately.
- CIF alone (62n2): stages the target field and applies it to IF at the next JMP or JMS. The deferral preserves correct interrupt behavior across the field change.
- CDF CIF (62n3): both effects apply - DF immediately, IF deferred - using the same Field value.

Where n = IR[5:3] = target field (0-7).

#### Register Read / Restore Instructions

These are selected by IR[2:0] = 100, with the specific instruction determined by IR[5:3].

| Mnemonic | Octal | Name | Operation |
|---|---|---|---|
| RDF | 6214 | Read Data Field | AC[5:3] <- DF (OR'd into AC; other AC bits unaffected) |
| RIF | 6224 | Read Instruction Field | AC[5:3] <- IF (OR'd into AC; other AC bits unaffected) |
| RIB | 6234 | Read Interrupt Buffer | AC[5:3] <- saved IF, AC[2:0] <- saved DF |
| RMF | 6244 | Restore Memory Field | IF <- saved IF (deferred), DF <- saved DF |

Semantics:
- RDF and RIF place the current field into AC[5:3] by OR, so AC is not cleared first. A clean read is obtained by clearing AC (for example, CLA) in a preceding instruction.
- RIB reads the interrupt-saved fields from the interrupt buffer into AC. It is used within an interrupt service routine to capture the interrupted program's fields.
- RMF restores IF and DF from the interrupt buffer, typically at the end of an interrupt service routine. The IF restore is deferred to the next JMP or JMS, consistent with CIF.

---

### Deferred Instructions (Planned)

The following processor IOTs are recognized as part of the PDP-8/E device-0 set but are not yet defined for this system. They are listed here for completeness of the device-0 operation space (IR[2:0] = 100 through 111). Each is deferred pending a design dependency noted below.

Software targeting the first hardware build must not rely on these instructions.

| Mnemonic | Octal | IR[2:0] | Name | Planned Operation | Blocking Dependency |
|---|---|---|---|---|---|
| GTF | 6004 | 100 | Get Flags | Assemble the machine flags word (Link, interrupt state, saved fields, and related status) into AC | Flags-word bit layout not yet defined |
| RTF | 6005 | 101 | Restore Flags | Restore the machine flags word from AC, re-enabling interrupts | Flags-word bit layout not yet defined; interacts with interrupt state |
| SGT | 6006 | 110 | Skip if Greater Than | Skip the next instruction if the EAE greater-than flag is set | EAE (Extended Arithmetic Element) not implemented |
| CAF | 6007 | 111 | Clear All Flags | Clear AC, L, the interrupt system, and all device flags | Requires a system-wide I/O clear (INIT) broadcast, defined with the I/O system in section 07 |

Notes:
- GTF and RTF are the standard mechanism for saving and restoring full machine state in an interrupt service routine. Their definition is deferred until the flags-word format is specified, since that format depends on interrupt and memory-extension state that is still being finalized.
- SGT is meaningful only when the EAE option is present. This system does not currently implement the EAE, so SGT has no defined effect.
- CAF provides a single-instruction reset of processor and device state. Its device-clearing half depends on an I/O INIT broadcast signal that will be defined alongside the I/O system (section 07).