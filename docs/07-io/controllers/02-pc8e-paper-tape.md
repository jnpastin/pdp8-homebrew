# PC8E-Compatible Paper-Tape Controller Contract

## Purpose

This document defines the architectural contract presented by a PC8E-compatible high-speed paper-tape reader and punch controller.

The controller provides:

- paper-tape reader input at device address `01`
- paper-tape punch output at device address `02`
- PDP-8/E PC8E-compatible programmer-visible behavior
- optional interrupt requests based on reader and punch flags

This document does not define the controller implementation.

## Scope

This document defines:

- default device addresses
- programmer-visible state
- character representation
- interrupt behavior
- reset behavior
- IOT semantics
- IOT response timing
- externally visible acceptance and completion behavior
- unsupported-operation behavior

This document does not define:

- internal buffering
- internal register-transfer sequencing
- physical reader control
- physical punch control
- serial protocol
- baud rate
- character framing
- voltage levels
- connector type
- physical flow-control mechanism
- controller component selection
- address-configuration hardware

Those items belong to the controller design and physical implementation documentation.

## Compatibility Target

The controller must reproduce the programmer-visible behavior required by the PDP-8/E PC8E high-speed paper-tape interface.

The controller implements the standard DEC PC8E instruction set only.

The following third-party extensions are not implemented:

- additional meanings for reader IOP values `3`, `5`, and `7`
- reader direction control
- end-of-tape detection
- end-of-tape interrupt behavior
- an extended reader command register

Internal implementation differences are permitted only when they do not change behavior visible through:

- IOA
- IOP
- DB
- controller response signals
- interrupt requests
- reset
- controller flags
- IOT results

## Device Addresses

| Address | Function |
|---:|---|
| `01` | High-speed paper-tape reader |
| `02` | High-speed paper-tape punch |

These addresses define the standard compatibility configuration.

Alternate addresses are permitted when:

- the controller supports address configuration
- the associated software uses the configured addresses

The address-configuration mechanism is outside this contract.

## Programmer-Visible State

The controller presents the following state:

- one 8-bit reader buffer
- one reader flag
- one 8-bit punch buffer
- one punch flag
- one shared interrupt-enable bit

No additional state is visible through the PC8E-compatible device addresses.

## Character Representation

Paper-tape characters are eight bits wide.

### Reader Character

The reader buffer maps to:

```text
AC[7:0] <- character
```

Reader transfers use OR semantics:

- the reader character is ORed into `AC[7:0]`
- `AC[11:8]` is unaffected

### Punch Character

For a punch operation:

- the controller accepts `AC[7:0]`
- `AC[11:8]` is ignored

## Interrupt Behavior

The reader and punch interfaces share one controller-local interrupt-enable bit.

`RPE` sets the shared interrupt-enable bit.

`PCE` clears the shared interrupt-enable bit.

The controller asserts its interrupt contribution when:

```text
INTERRUPT_ENABLE
AND
(READER_FLAG OR PUNCH_FLAG)
```

The controller does not modify the CPU interrupt-enable state.

## Reset State

Reset establishes the following programmer-visible state:

| State | Reset value |
|---|---:|
| Reader buffer | `000` |
| Reader flag | Clear |
| Punch buffer | `000` |
| Punch flag | Set |
| Shared interrupt enable | Clear |
| Controller interrupt contribution | Inactive |

The punch flag is set so the punch initially appears ready to accept a character.

The reader flag remains clear until a reader operation completes.

Reset cancels any controller operation not yet reported as complete.

Characters not yet represented by a completed programmer-visible operation may be discarded by reset.

# Reader Interface

## Reader Buffer

The reader buffer contains the current character available to software.

## Reader Flag

The reader flag indicates whether the reader buffer contains a valid character.

The reader flag is set when a reader operation completes and a character is available in the reader buffer.

The reader flag is cleared by:

- `RRB`
- `RFC`
- `RRB RFC`
- reset

## Reader Capacity Contract

After setting the reader flag, the controller must preserve the visible reader character until software reads or clears it.

The controller must not replace the visible character while the reader flag remains set.

If additional physical input cannot be accepted while the visible character remains pending, the controller may reject or discard the additional input.

The mechanism used to control or limit physical input is outside this contract.

No reader-overrun status is visible through the PC8E-compatible interface.

## Reader Operation Contract

`RFC` requests acquisition of the next paper-tape character.

The reader flag remains clear while the requested character is unavailable.

When the requested character becomes available:

- the character becomes visible through the reader buffer
- the reader flag is set at a TP event

How the controller acquires the physical character is outside this contract.

## Device 01 IOT Table

| IOT | Mnemonic | Contract |
|---:|---|---|
| `6010` | RPE | Set shared interrupt enable |
| `6011` | RSF | Request skip when reader flag is set |
| `6012` | RRB | OR reader buffer into AC and clear reader flag |
| `6013` | Undefined | Ignore |
| `6014` | RFC | Clear reader flag and request the next character |
| `6015` | Undefined | Ignore |
| `6016` | RRB RFC | OR reader buffer into AC, clear reader flag, and request the next character |
| `6017` | Undefined | Ignore |

## RPE

### Controller Contract

At TP2:

```text
INTERRUPT_ENABLE <- 1
```

### Response Signals

No controller response signal is required.

RPE does not modify AC.

## RSF

### Controller Contract

During TS4, the controller asserts `IO_SKIP_REQ` when:

```text
IOT_ACTIVE
AND
ADDRESS_MATCH
AND
(IOP = 1)
AND
READER_FLAG
```

RSF does not modify controller state.

## RRB

### Controller Contract

During TS2:

- the controller drives the reader buffer onto DB
- the controller asserts `IO_READ_REQ`

At TP2:

```text
READER_FLAG <- 0
```

The character represented by the reader buffer is consumed at TP2.

RRB does not request AC clear.

## RFC

### Controller Contract

At TP3:

```text
READER_FLAG <- 0
```

At TP3, the controller accepts the request to acquire the next character.

The reader flag is set later, at a TP event, when the requested character becomes available in the reader buffer.

### Response Signals

No controller response signal is required.

## RRB RFC

### Controller Contract

During TS2:

- the controller drives the reader buffer onto DB
- the controller asserts `IO_READ_REQ`

At TP2:

```text
READER_FLAG <- 0
```

The character represented by the reader buffer is consumed at TP2.

At TP3, the controller accepts the request to acquire the next character.

The reader flag is set later, at a TP event, when the requested character becomes available in the reader buffer.

# Punch Interface

## Punch Buffer

The punch buffer contains the character accepted through the most recent valid `PPC` or `PLS` operation.

## Punch Flag

The punch flag indicates completion of the accepted programmer-visible punch operation.

The punch flag is set when the accepted character has completed output.

The punch flag is cleared by:

- `PCF`
- `PLS`
- reset, followed by the reset-specific set state defined above

## Punch Acceptance Contract

Software is expected to test the punch flag before supplying another character.

The controller must preserve an accepted character until:

- the punch operation completes
- reset cancels the operation

If the controller cannot accept a character supplied through `PPC` or `PLS`:

- the new character is discarded
- the previously accepted character is not overwritten
- the active punch operation is not changed
- the controller does not report completion of the discarded character

The controller must not discard an already accepted character to accept a newer character.

## Punch Completion Contract

The punch flag must not be set merely because the character was accepted by the controller.

The punch flag is set only when the programmer-visible punch operation has completed.

If output cannot complete, the punch flag may remain clear indefinitely.

How the controller performs or detects physical punch completion is outside this contract.

## Device 02 IOT Table

| IOT | Mnemonic | Contract |
|---:|---|---|
| `6020` | PCE | Clear shared interrupt enable |
| `6021` | PSF | Request skip when punch flag is set |
| `6022` | PCF | Clear punch flag |
| `6023` | Undefined | Ignore |
| `6024` | PPC | Accept `AC[7:0]` as the next punch character |
| `6025` | Undefined | Ignore |
| `6026` | PLS | Accept `AC[7:0]`, clear punch flag, and begin the punch operation |
| `6027` | Undefined | Ignore |

## PCE

### Controller Contract

At TP2:

```text
INTERRUPT_ENABLE <- 0
```

### Response Signals

No controller response signal is required.

PCE does not modify AC.

## PSF

### Controller Contract

During TS4, the controller asserts `IO_SKIP_REQ` when:

```text
IOT_ACTIVE
AND
ADDRESS_MATCH
AND
(IOP = 1)
AND
PUNCH_FLAG
```

PSF does not modify controller state.

## PCF

### Controller Contract

At TP3:

```text
PUNCH_FLAG <- 0
```

### Response Signals

No controller response signal is required.

## PPC

### Controller Contract

During TS2:

- the controller asserts `IO_WRITE_REQ`

At TP2, when the controller can accept a character:

```text
PUNCH_BUFFER <- AC[7:0]
```

At TP3, the controller accepts the request to perform the punch operation using the character in the punch buffer.

PPC does not clear the punch flag.

If the controller cannot accept the character:

- the new character is discarded
- the punch buffer is not changed
- the active punch operation is not changed

## PLS

### Controller Contract

During TS2:

- the controller asserts `IO_WRITE_REQ`

At TP2, when the controller can accept a character:

```text
PUNCH_BUFFER <- AC[7:0]
```

At TP3, when the character was accepted:

```text
PUNCH_FLAG <- 0
```

At TP3, the controller accepts the request to perform the punch operation using the character in the punch buffer.

If the controller cannot accept the character:

- the new character is discarded
- the punch buffer is not changed
- the active punch operation is not changed
- the punch flag is not cleared as a consequence of the rejected character

# Asynchronous Controller Events

Reader-character availability and punch completion may originate outside the system timing domain.

Before changing programmer-visible controller state, the controller must synchronize those events to the system timing model.

Programmer-visible state changes occur only at TP events.

The controller may set:

- reader flag when the requested reader character becomes visible
- punch flag when the accepted punch operation completes

The implementation-specific synchronization mechanism is outside this contract.

# Unsupported Operations

Unsupported IOP values are ignored.

For this controller, the unsupported operations are:

- `6013`
- `6015`
- `6017`
- `6023`
- `6025`
- `6027`

An ignored operation produces:

- no DB drive
- no DB capture
- no `IO_CLEAR_AC_REQ`
- no `IO_SKIP_REQ`
- no `IO_WAIT`
- no controller state change
- no flag change
- no interrupt-enable change
- no interrupt effect

# DMA Behavior

The PC8E-compatible controller does not use DMA.

Reader and punch operations use programmed I/O and optional interrupts.

# Implementation Boundary

The controller implementation must satisfy this contract but may choose its own:

- internal buffering
- internal state machines
- physical reader interface
- physical punch interface
- serial protocol
- flow-control mechanism
- baud-rate handling
- framing
- electrical representation
- connector
- component selection
- address-configuration mechanism

None of those choices may alter the programmer-visible behavior defined here.
