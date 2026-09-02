# PC8E-Compatible Paper-Tape Controller Contract

## 1. Purpose

This document defines the architectural contract presented by a PC8E-compatible high-speed paper-tape reader and punch controller.

The controller provides:

- paper-tape reader input at device address `01`
- paper-tape punch output at device address `02`
- PDP-8/E PC8E-compatible programmer-visible behavior
- optional interrupt requests based on reader and punch flags

This document does not define the controller implementation.

---

## 2. Scope

This document defines:

- default device addresses
- programmer-visible state
- character representation
- interrupt behavior
- /INITIALIZE behavior
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

---

## 3. Compatibility Target

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
- /INITIALIZE behavior
- controller flags
- IOT results

---

## 4. Device Addresses

| Address | Function |
|---:|---|
| `01` | High-speed paper-tape reader |
| `02` | High-speed paper-tape punch |

These addresses define the standard compatibility configuration.

Alternate addresses are permitted when:

- the controller supports address configuration
- the associated software uses the configured addresses

The address-configuration mechanism is outside this contract.

---

## 5. Programmer-Visible State

The controller presents the following state:

- one 8-bit reader buffer
- one reader flag
- one 8-bit punch buffer
- one punch flag
- one shared interrupt-enable bit

No additional state is visible through the PC8E-compatible device addresses.

---

## 6. Character Representation

Paper-tape characters are eight bits wide.

### 6.1 Reader Character

The reader buffer maps to:

```text
AC[7:0] <- character
```

Reader transfers use OR semantics:

- the reader character is ORed into `AC[7:0]`
- `AC[11:8]` is unaffected

### 6.2 Punch Character

For a punch operation:

- the controller accepts `AC[7:0]`
- `AC[11:8]` is ignored

---

## 7. Interrupt Behavior

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

---

## 8. System Initialization

The controller enters its initialized state when /INITIALIZE is asserted.

| State | Initialized value |
|---|---|
| Reader buffer | 000 |
| Reader flag | Clear |
| Punch buffer | 000 |
| Punch flag | Set |
| Shared interrupt enable | Clear |
| Controller interrupt contribution | Inactive |

The punch flag is set so the punch initially appears ready to accept a character.  
The reader flag remains clear until a reader operation completes.  
/INITIALIZE cancels any controller operation not yet reported as complete.  
Characters not yet represented by a completed programmer-visible operation may be discarded.

The controller responds to /INITIALIZE regardless of IOT_ACTIVE, address match, IOP, or interrupt state.  
The initialized state commits at the TP ending the asserted /INITIALIZE TSTEP.  
No other controller action commits at that TP.

---

## 9. Reader Interface

### 9.1 Reader Buffer

The reader buffer contains the current character available to software.

### 9.2 Reader Flag

The reader flag indicates whether the reader buffer contains a valid character.

The reader flag is set when a reader operation completes and a character is available in the reader buffer.

The reader flag is cleared by:

- `RRB`
- `RFC`
- `RRB RFC`
- /INITIALIZE

### 9.3 Reader Capacity Contract

After setting the reader flag, the controller must preserve the visible reader character until software reads or clears it.

The controller must not replace the visible character while the reader flag remains set.

If additional physical input cannot be accepted while the visible character remains pending, the controller may reject or discard the additional input.

The mechanism used to control or limit physical input is outside this contract.

No reader-overrun status is visible through the PC8E-compatible interface.

### 9.4 Reader Operation Contract

`RFC` requests acquisition of the next paper-tape character.

The reader flag remains clear while the requested character is unavailable.

When the requested character becomes available:

- the character becomes visible through the reader buffer
- the reader flag is set at a TP event

How the controller acquires the physical character is outside this contract.

---

## 10. Device 01 IOT Table

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

---

## 11. RPE

### 11.1 Controller Contract

At TP2:

```text
INTERRUPT_ENABLE <- 1
```

### 11.2 Response Signals

No controller response signal is required.

RPE does not modify AC.

---

## 12. RSF

### 12.1 Controller Contract

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

---

## 13. RRB

### 13.1 Controller Contract

During TS3:

- the controller asserts `IO_READ_REQ`

At TP3, CPU control accepts the read request.

During TS4:

- CPU control asserts `/DB_READ`
- the controller drives the reader buffer onto DB

At TP4:

```text
AC <- AC OR DB
READER_FLAG <- 0
```

The character represented by the reader buffer is consumed at TP4.  
RRB does not request AC clear.

---

## 14. RFC

### 14.1 Controller Contract

At TP3:

```text
READER_FLAG <- 0
```

At TP3, the controller accepts the request to acquire the next character.

The reader flag is set later, at a TP event, when the requested character becomes available in the reader buffer.

### 14.2 Response Signals

No controller response signal is required.

---

## 15. RRB RFC

### 15.1 Controller Contract

During TS3:

- the controller asserts `IO_READ_REQ`
- the controller accepts the request to acquire the next character

At TP3:

- CPU control accepts the read request
- `READER_FLAG <- 0`

During TS4:

- CPU control asserts `/DB_READ`
- the controller drives the previously visible reader-buffer value onto DB

At TP4:

```text
AC <- AC OR DB
```

The previously visible character is consumed at TP4.

The reader flag is set later, at a TP event, when the requested next character becomes available in the reader buffer. The controller must preserve the previous reader-buffer value through TP4 even if acquisition of the next character begins at TP3.

---

## 16. Punch Interface

### 16.1 Punch Buffer

The punch buffer contains the character accepted through the most recent valid `PPC` or `PLS` operation.

### 16.2 Punch Flag

The punch flag indicates completion of the accepted programmer-visible punch operation.

The punch flag is set when the accepted character has completed output.

The punch flag is cleared by:

- `PCF`
- `PLS`
- /INITIALIZE, which establishes the initialized set state defined above

### 16.3 Punch Acceptance Contract

Software is expected to test the punch flag before supplying another character.

The controller must preserve an accepted character until:

- the punch operation completes
- /INITIALIZE cancels the operation

If the controller cannot accept a character supplied through `PPC` or `PLS`:

- the new character is discarded
- the previously accepted character is not overwritten
- the active punch operation is not changed
- the controller does not report completion of the discarded character

The controller must not discard an already accepted character to accept a newer character.

### 16.4 Punch Completion Contract

The punch flag must not be set merely because the character was accepted by the controller.

The punch flag is set only when the programmer-visible punch operation has completed.

If output cannot complete, the punch flag may remain clear indefinitely.

How the controller performs or detects physical punch completion is outside this contract.

---

## 17. Device 02 IOT Table

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

---

## 18. PCE

### 18.1 Controller Contract

At TP2:

```text
INTERRUPT_ENABLE <- 0
```

### 18.2 Response Signals

No controller response signal is required.

PCE does not modify AC.

---

## 19. PSF

### 19.1 Controller Contract

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

---

## 20. PCF

### 20.1 Controller Contract

At TP3:

```text
PUNCH_FLAG <- 0
```

### 20.2 Response Signals

No controller response signal is required.

---

## 21. PPC

### 21.1 Controller Contract

During TS3:

- the controller asserts `IO_WRITE_REQ` when it can accept a character

At TP3, CPU control accepts the write request.

During TS4:

- CPU control asserts `/DB_WRITE`
- the CPU drives AC onto DB

At TP4, when the request was accepted:

```text
PUNCH_BUFFER <- DB[7:0]
```

The accepted character becomes the active programmer-visible punch operation.  
PPC does not clear the punch flag.

If the controller cannot accept the character:

- it does not assert `IO_WRITE_REQ`
- no DB transfer occurs
- the new character is discarded
- the active punch operation is not modified

---

## 22. PLS

### 22.1 Controller Contract

During TS3:

- the controller asserts `IO_WRITE_REQ` when it can accept a character

At TP3, CPU control accepts the write request.

During TS4:

- CPU control asserts `/DB_WRITE`
- the CPU drives AC onto DB

At TP4, when the request was accepted:

```text
PUNCH_BUFFER <- DB[7:0]
PUNCH_FLAG <- 0
```

The accepted character becomes the active programmer-visible punch operation.

If the controller cannot accept the character:

- it does not assert `IO_WRITE_REQ`
- no DB transfer occurs
- the new character is discarded
- the active punch operation is not modified
- the punch flag is not cleared

---

## 23. Asynchronous Controller Events

Reader-character availability and punch completion may originate outside the system timing domain.

Before changing programmer-visible controller state, the controller must synchronize those events to the system timing model.

Programmer-visible state changes occur only at TP events.

The controller may set:

- reader flag when the requested reader character becomes visible
- punch flag when the accepted punch operation completes

The implementation-specific synchronization mechanism is outside this contract.

---

## 24. Interrupt-Service Interface

The PC8E-compatible controller contributes an interrupt request when the shared controller interrupt enable is set and either the reader flag or punch flag is set.

The interrupt service routine identifies the requesting interface using the controller's existing skip operations:

- RSF tests the reader flag.
- PSF tests the punch flag.

The interrupt service routine clears or services the reader interrupt condition using the existing reader operations:

- RRB reads the reader buffer and clears the reader flag.
- RFC clears the reader flag and requests acquisition of the next character.
- RRB RFC reads the current reader buffer, clears the reader flag, and requests acquisition of the next character.

After RFC or RRB RFC, completion of the requested reader operation sets the reader flag again. If the shared interrupt enable remains set, that completion establishes another controller interrupt condition.

The interrupt service routine clears or services the punch interrupt condition using the existing punch operations:

- PCF clears the punch flag.
- PLS accepts a new punch character and clears the punch flag when the character is accepted.

PPC accepts a new punch character without clearing the punch flag. Therefore, PPC alone does not remove a punch interrupt condition.

RPE and PCE control whether reader and punch flags contribute to the controller interrupt request:

- RPE enables the shared controller interrupt contribution.
- PCE disables the shared controller interrupt contribution.

Servicing one flag does not clear the other flag. The controller interrupt contribution remains asserted while the shared interrupt enable is set and either flag remains set.

This section coordinates the existing controller operations for interrupt-service use. The individual instruction definitions remain authoritative for their complete behavior and timing.

---

## 25. Unsupported Operations

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
- no `/IO_WAIT`
- no controller state change
- no flag change
- no interrupt-enable change
- no interrupt effect

---

## 26. DMA Behavior

The PC8E-compatible controller does not use DMA.

Reader and punch operations use programmed I/O and optional interrupts.

---

## 27. Implementation Boundary

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
