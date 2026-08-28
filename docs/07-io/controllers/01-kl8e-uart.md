# KL8E-Compatible UART Controller Contract

## 1. Purpose

This document defines the architectural contract presented by a KL8E-compatible console controller.

The controller provides:

- console character input at device address `03`
- console character output at device address `04`
- PDP-8/E KL8E-compatible programmer-visible behavior
- optional interrupt requests based on the console flags

This document does not define the controller implementation.

---

## 2. Scope

This document defines:

- default device addresses
- programmer-visible state
- character representation
- interrupt behavior
- reset behavior
- IOT semantics
- IOT response timing
- externally visible busy and completion behavior
- unsupported-operation behavior

This document does not define:

- UART implementation
- internal buffering
- internal register-transfer sequencing
- baud rate
- character framing
- voltage levels
- connector type
- physical flow-control mechanism
- terminal implementation
- address-configuration hardware
- controller component selection

Those items belong to the controller design and physical implementation documentation.

---

## 3. Compatibility Target

The controller must reproduce the programmer-visible behavior required by the PDP-8/E KL8E console interface.

The controller does not implement KL8JA status-reporting extensions.

Internal implementation differences are permitted only when they do not change the behavior visible through:

- IOA
- IOP
- DB
- controller response signals
- interrupt requests
- reset
- controller flags
- IOT results

---

## 4. Device Addresses

| Address | Function |
|---:|---|
| `03` | Console character input |
| `04` | Console character output |

These addresses define the standard compatibility configuration.

Alternate addresses are permitted when:

- the controller supports address configuration
- the input address remains one less than the output address
- the associated software uses the configured addresses

The address-configuration mechanism is outside this contract.

---

## 5. Programmer-Visible State

The controller presents the following state:

- one 8-bit keyboard receive register
- one keyboard flag
- one 8-bit teleprinter transmit register
- one teleprinter flag
- one shared interrupt-enable bit

No additional state is visible through the KL8E-compatible device addresses.

---

## 6. Character Representation

Console characters are eight bits wide.

### 6.1 Input Character

The keyboard receive register maps to:

```text
AC[7:0] <- character
```

For an OR-style input operation:

- the character is ORed into `AC[7:0]`
- `AC[11:8]` is unaffected

For a clear-then-read operation:

- AC is cleared before the read
- the resulting value in `AC[11:8]` is zero
- the resulting value in `AC[7:0]` is the received character

### 6.2 Output Character

For an output operation:

- the controller accepts `AC[7:0]`
- `AC[11:8]` is ignored

---

## 7. Interrupt Behavior

The input and output interfaces share one controller-local interrupt-enable bit.

`KIE` loads the interrupt-enable bit from:

```text
AC[0]
```

All other AC bits are ignored by `KIE`.

The controller asserts its interrupt contribution when:

```text
INTERRUPT_ENABLE
AND
(KEYBOARD_FLAG OR TELEPRINTER_FLAG)
```

The controller does not modify the CPU interrupt-enable state.

---

## 8. Reset State

Reset establishes the following programmer-visible state:

| State | Reset value |
|---|---:|
| Keyboard receive register | `000` |
| Keyboard flag | Clear |
| Teleprinter transmit register | `000` |
| Teleprinter flag | Clear |
| Shared interrupt enable | Clear |
| Controller interrupt contribution | Inactive |

Reset cancels any controller operation not yet reported as complete.

Any characters not yet represented by a completed programmer-visible operation may be discarded by reset.

---

## 9. Input Interface

### 9.1 Keyboard Receive Register

The keyboard receive register contains the current character available to software.

### 9.2 Keyboard Flag

The keyboard flag indicates whether the keyboard receive register contains a valid character.

The keyboard flag is set when a complete character becomes available in the keyboard receive register.

The keyboard flag is cleared by:

- `KCF`
- `KCC`
- `KRB`
- reset

`KRS` does not clear the keyboard flag.

### 9.3 Input Capacity Contract

The controller must preserve a character after setting the keyboard flag until software clears or consumes that character.

The controller must not replace the visible character while the keyboard flag remains set.

If additional characters cannot be accepted while the visible character remains pending, the controller may reject or discard the additional characters.

The method used to limit or control incoming traffic is outside this contract.

No receive-overrun status is visible through the KL8E-compatible interface.

---

## 10. Device 03 IOT Table

| IOT | Mnemonic | Contract |
|---:|---|---|
| `6030` | KCF | Clear keyboard flag |
| `6031` | KSF | Request skip when keyboard flag is set |
| `6032` | KCC | Clear AC and clear keyboard flag |
| `6033` | Undefined | Ignore |
| `6034` | KRS | OR keyboard receive register into AC |
| `6035` | KIE | Load shared interrupt enable from `AC[0]` |
| `6036` | KRB | Clear AC, read keyboard receive register, and clear keyboard flag |
| `6037` | Undefined | Ignore |

---

## 11. KCF

### 11.1 Controller Contract

At TP2:

```text
KEYBOARD_FLAG <- 0
```

### 11.2 Response Signals

No controller response signal is required.

---

## 12. KSF

### 12.1 Controller Contract

During TS4, the controller asserts `IO_SKIP_REQ` when:

```text
IOT_ACTIVE
AND
ADDRESS_MATCH
AND
(IOP = 1)
AND
KEYBOARD_FLAG
```

KSF does not modify controller state.

---

## 13. KCC

### 13.1 Controller Contract

During TS2:

```text
IO_CLEAR_AC_REQ = 1
```

At TP2:

```text
KEYBOARD_FLAG <- 0
```

KCC does not transfer the keyboard receive register.

---

## 14. KRS

### 14.1 Controller Contract

During TS3:

- the controller asserts `IO_READ_REQ`

At TP3, CPU control accepts the read request.

During TS4:

- CPU control asserts `/DB_READ`
- the controller drives the keyboard receive register onto DB

At TP4:

```text
AC <- AC OR DB
```

KRS does not modify controller state.

---

## 15. KIE

### 15.1 Controller Contract

During TS3:

- the controller asserts `IO_WRITE_REQ`

At TP3, CPU control accepts the write request.

During TS4:

- CPU control asserts `/DB_WRITE`
- the CPU drives AC onto DB

At TP4:

```text
INTERRUPT_ENABLE <- DB[0]
```

All other DB bits are ignored.  
KIE does not request AC clear.

---

## 16. KRB

### 16.1 Controller Contract

During TS2:

- the controller asserts `IO_CLEAR_AC_REQ`

At TP2:

```text
AC <- 0
```

During TS3:

- the controller asserts `IO_READ_REQ`

At TP3, CPU control accepts the read request.

During TS4:

- CPU control asserts `/DB_READ`
- the controller drives the keyboard receive register onto DB

At TP4:

```text
AC <- AC OR DB
KEYBOARD_FLAG <- 0
```

The character represented by the keyboard receive register is consumed at TP4.

---

## 17. Output Interface

### 17.1 Teleprinter Transmit Register

The teleprinter transmit register contains the character accepted through the most recent valid output operation.

### 17.2 Teleprinter Flag

The teleprinter flag indicates completion of the accepted programmer-visible output operation.

The teleprinter flag is set when the accepted character has completed output.

The teleprinter flag is cleared by:

- `TCF`
- `TLS`
- reset

The teleprinter flag may be set directly by `TFL`.

### 17.3 Output Acceptance Contract

Software is expected to test the teleprinter flag before supplying another character.

The controller must preserve an accepted character until:

- the output operation completes
- reset cancels the operation

If the controller cannot accept a character supplied through `TPC` or `TLS`, the new character is discarded.

The controller must not discard or overwrite a previously accepted character to accept a newer character.

The controller must not set the teleprinter flag for a discarded character.

### 17.4 Output Completion Contract

The teleprinter flag must not be set merely because the character was accepted by the controller.

The teleprinter flag is set only when the programmer-visible output operation has completed.

If output cannot complete, the teleprinter flag may remain clear indefinitely.

How the controller achieves or detects physical output completion is outside this contract.

---

## 18. Device 04 IOT Table

| IOT | Mnemonic | Contract |
|---:|---|---|
| `6040` | TFL | Set teleprinter flag |
| `6041` | TSF | Request skip when teleprinter flag is set |
| `6042` | TCF | Clear teleprinter flag |
| `6043` | Undefined | Ignore |
| `6044` | TPC | Accept `AC[7:0]` as the next output character |
| `6045` | TSK | Request skip when keyboard flag or teleprinter flag is set |
| `6046` | TLS | Accept `AC[7:0]` and clear teleprinter flag |
| `6047` | Undefined | Ignore |

---

## 19. TFL

### 19.1 Controller Contract

At TP2:

```text
TELEPRINTER_FLAG <- 1
```

### 19.2 Response Signals

No controller response signal is required.

---

## 20. TSF

### 20.1 Controller Contract

During TS4, the controller asserts `IO_SKIP_REQ` when:

```text
IOT_ACTIVE
AND
ADDRESS_MATCH
AND
(IOP = 1)
AND
TELEPRINTER_FLAG
```

TSF does not modify controller state.

---

## 21. TCF

### 21.1 Controller Contract

At TP3:

```text
TELEPRINTER_FLAG <- 0
```

### 21.2 Response Signals

No controller response signal is required.

---

## 22. TPC

### 22.1 Controller Contract

During TS3:

- the controller asserts `IO_WRITE_REQ` when it can accept a character

At TP3, CPU control accepts the write request.

During TS4:

- CPU control asserts `/DB_WRITE`
- the CPU drives AC onto DB

At TP4, when the request was accepted:

```text
TELEPRINTER_TRANSMIT_REGISTER <- DB[7:0]
```

The accepted character becomes the active programmer-visible output operation.  
TPC does not clear the teleprinter flag.

If the controller cannot accept the character:

- it does not assert `IO_WRITE_REQ`
- no DB transfer occurs
- the new character is discarded
- the active output operation is not modified

---

## 23. TSK

### 23.1 Controller Contract

During TS4, the controller asserts `IO_SKIP_REQ` when:

```text
IOT_ACTIVE
AND
ADDRESS_MATCH
AND
(IOP = 5)
AND
(KEYBOARD_FLAG OR TELEPRINTER_FLAG)
```

TSK does not modify controller state.

---

## 24. TLS

### 24.1 Controller Contract

During TS3:

- the controller asserts `IO_WRITE_REQ` when it can accept a character

At TP3, CPU control accepts the write request.

During TS4:

- CPU control asserts `/DB_WRITE`
- the CPU drives AC onto DB

At TP4, when the request was accepted:

```text
TELEPRINTER_TRANSMIT_REGISTER <- DB[7:0]
TELEPRINTER_FLAG <- 0
```

The accepted character becomes the active programmer-visible output operation.

If the controller cannot accept the character:

- it does not assert `IO_WRITE_REQ`
- no DB transfer occurs
- the new character is discarded
- the active output operation is not modified
- the teleprinter flag is not cleared

---

## 25. Asynchronous Controller Events

Character arrival and output completion may originate outside the system timing domain.

Before changing programmer-visible controller state, the controller must synchronize those events to the system timing model.

Programmer-visible state changes occur only at TP events.

The controller may set:

- keyboard flag when a complete input character becomes visible
- teleprinter flag when the accepted output operation completes

The implementation-specific synchronization mechanism is outside this contract.

---

## 26. Unsupported Operations

Unsupported IOP values are ignored.

For this controller, the unsupported operations are:

- `6033`
- `6037`
- `6043`
- `6047`

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

## 27. DMA Behavior

The KL8E-compatible controller does not use DMA.

Console input and output use programmed I/O and optional interrupts.

---

## 28. Implementation Boundary

The controller implementation must satisfy this contract but may choose its own:

- internal buffering
- internal state machines
- UART technology
- physical terminal interface
- flow-control mechanism
- baud-rate handling
- framing
- electrical representation
- connector
- component selection
- address-configuration mechanism

None of those choices may alter the programmer-visible behavior defined here.