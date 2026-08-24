# RK8E-Compatible Storage Controller Contract

## Purpose

This document defines the architectural contract presented by an RK8E-compatible storage controller.

The controller provides:

- RK8E-compatible disk control at device address `74`
- RK05-compatible disk geometry
- asynchronous disk operations
- DMA transfers between the controller and memory
- RK8E-compatible status, completion, error, skip, and interrupt behavior
- RK8E-compatible bootstrap behavior

This document does not define the controller implementation.

## Scope

This document defines:

- default device address
- programmer-visible registers and flags
- RK05-compatible geometry
- IOT semantics
- IOT response timing
- interrupt and skip behavior
- reset and abort behavior
- disk-operation completion behavior
- DMA participation
- bootstrap-visible behavior
- unsupported-operation behavior

This document does not define:

- SD or CF interface technology
- backing-image file format
- card filesystem
- internal buffering
- caching
- sector translation implementation
- internal state machines
- internal register-transfer sequencing
- CRC implementation
- physical media-selection mechanism
- connector type
- component selection
- address-configuration hardware
- DMA-priority configuration hardware

Those items belong to the controller design and physical implementation documentation.

## Compatibility Target

The controller must reproduce the programmer-visible behavior required by the DEC RK8E controller operating with RK05-compatible media.

Internal implementation differences are permitted only when they do not change behavior visible through:

- IOA
- IOP
- DB
- controller response signals
- interrupt requests
- reset
- DMA request and grant behavior
- MFB
- AB
- MDB
- RD
- WR
- programmer-visible registers
- status indications
- completion behavior
- error behavior
- IOT results

The controller implements the RK8E interface only.

The RK8/RK01 instruction family using device addresses `73` through `75` is a different controller interface and is not implemented.

## Device Address

| Address | Function |
|---:|---|
| `74` | RK8E-compatible disk controller |

Device address `74` defines the standard compatibility configuration.

An alternate address is permitted when:

- the controller supports address configuration
- the associated software uses the configured address

The address-configuration mechanism is outside this contract.

Device addresses `73` and `75` are not assigned to this controller.

## Emulated Drives

The controller presents up to four RK05-compatible drives.

The Command Register selects the active drive using the standard RK8E unit-select field.

Drive numbering is:

```text
0 through 3
```

The mapping between an emulated drive number and physical storage is outside this contract.

A drive without valid available media must report the corresponding RK8E-compatible not-ready or error state.

## RK05-Compatible Geometry

Each emulated drive presents the following geometry:

| Property | Value |
|---|---:|
| Cylinders | 203 |
| Surfaces per cylinder | 2 |
| Sectors per surface | 16 |
| Sectors per cylinder | 32 |
| Words per sector | 256 |
| Word width | 12 bits |

The controller must interpret the RK8E disk address as the corresponding:

- drive
- cylinder
- surface
- sector

The controller must reject or report an error for disk addresses outside the RK05-compatible geometry.

The physical storage organization does not alter the geometry visible to software.

## Programmer-Visible State

The controller presents the following programmer-visible registers:

- 12-bit Command Register
- 12-bit Current Address Register
- 12-bit Disk Address Register
- 12-bit Status Register

The controller also presents the RK8E-defined:

- Control Done condition
- Error condition
- controller-busy condition
- interrupt-enable state
- selected-drive state
- 128-word or 256-word transfer selection
- maintenance behavior

The widths, bit assignments, and programmer-visible meanings of the Command Register and Status Register must match the DEC RK8E definitions exactly.

No implementation-specific status bits may be exposed through the RK8E Status Register.

## Command Register

The Command Register is 12 bits wide.

The Command Register is loaded by `DLDC`.

The Command Register is cleared by:

- system initialization
- `DCLC`

### Bit Assignments

| Bit or field | Name | Meaning |
|---:|---|---|
| `0` | Extended Cylinder Address | Most significant cylinder-address bit |
| `2:1` | Drive Select | Selects emulated drive `0` through `3` |
| `5:3` | Memory Field | Supplies MFB during DMA |
| `6` | Half-Block Transfer | Selects a 128-word transfer when set |
| `7` | Enable Done on Seek Done | Enables Control Done when a seek completes |
| `8` | Interrupt Enable | Enables controller interrupt contribution when Control Done or Error is asserted |
| `11:9` | Function | Selects the disk operation |

### Drive Select Encoding

| `COMMAND[2:1]` | Selected drive |
|---:|---:|
| `00` | `0` |
| `01` | `1` |
| `10` | `2` |
| `11` | `3` |

### Memory Field Encoding

`COMMAND[5:3]` is interpreted as an unsigned three-bit binary field number.

| `COMMAND[5:3]` | Memory field |
|---:|---:|
| `000` | `0` |
| `001` | `1` |
| `010` | `2` |
| `011` | `3` |
| `100` | `4` |
| `101` | `5` |
| `110` | `6` |
| `111` | `7` |

The selected memory field remains unchanged when the Current Address Register wraps from `7777` to `0000`.

### Transfer-Length Selection

| `COMMAND[6]` | Transfer length |
|---:|---:|
| `0` | 256 words |
| `1` | 128 words |

### Function Encoding

| `COMMAND[11:9]` | Function |
|---:|---|
| `000` | Read Data |
| `001` | Read All |
| `010` | Set Write Protect |
| `011` | Seek Only |
| `100` | Write Data |
| `101` | Write All |
| `110` | Unused |
| `111` | Unused |

Unused function encodings do not initiate a disk operation.

### Interrupt Contribution

When `COMMAND[8]` is set, the controller asserts its interrupt contribution when:

```text
CONTROL_DONE OR ERROR
```

### Seek Completion

When `COMMAND[7]` is set, successful completion of a seek sets Control Done.

### Extended Cylinder Address

`COMMAND[0]` combines with the cylinder-address bits supplied through the Disk Address Register to select one of the 203 valid RK05-compatible cylinders.

The complete disk-address field mapping is defined by the DEC RK8E-compatible Disk Address Register contract.

## Current Address Register

The Current Address Register is 12 bits wide.

The Current Address Register identifies the memory address used by DMA.

The Current Address Register is loaded by `DLCA`.

For each successful DMA word transfer:

1. The Current Address Register is incremented.
2. The incremented value is used as the memory address for that transfer.
3. The incremented value remains in the Current Address Register after the transfer.

If the Current Address Register contains `7777`, the next DMA transfer uses:

```text
0000
```

The memory-field value does not increment when the Current Address Register wraps.

## Disk Address Register

The Disk Address Register is 12 bits wide.

The Disk Address Register identifies the requested RK05-compatible disk location.

The Disk Address Register is loaded by `DLAG`.

The Disk Address Register, together with the applicable Command Register field, selects:

- cylinder
- surface
- sector

`DLAG` also initiates the operation selected by the Command Register.

## Status Register

The Status Register is 12 bits wide.

The Status Register is read by `DRST`.

Reading the Status Register does not clear it.

The Status Register is cleared by:

- `DCLS`
- `DCLC`
- a successful `DLDC`
- system initialization

### Bit Assignments

| Bit | Name | Meaning |
|---:|---|---|
| `0` | Cylinder Address Error | The cylinder address did not match the expected address |
| `1` | Drive Status Error | The selected drive reported an invalid operating status |
| `2` | Data Request Late | A required data transfer did not occur before the controller deadline |
| `3` | CRC Error | The controller detected a CRC failure |
| `4` | Write Lockout Error | A write was attempted while writing was prohibited |
| `5` | Timeout Error | The active operation exceeded the permitted completion interval |
| `6` | Control Busy Error | A prohibited controller operation was requested while the controller was busy |
| `7` | File Not Ready | The selected drive or its media is not ready |
| `8` | Seek Fail | The selected drive failed to reach the requested cylinder |
| `9` | Not Used | Always reads as `0` |
| `10` | RDYS/R/W | Reports the RK8E-defined selected-drive ready, seek, read, or write state |
| `11` | Control Done | The active operation completed or terminated with an error |

### Error Condition

The controller-wide Error condition is:

```text
STATUS[0]
OR STATUS[1]
OR STATUS[2]
OR STATUS[3]
OR STATUS[4]
OR STATUS[5]
OR STATUS[6]
OR STATUS[7]
OR STATUS[8]
```

`STATUS[9]`, `STATUS[10]`, and `STATUS[11]` do not contribute to Error.

### Control Done

`STATUS[11]` is set when required by RK8E-compatible behavior, including:

- completion of a data transfer
- completion of a seek-only operation when enabled by the Command Register
- completion of recalibration when enabled
- an error that terminates an active operation

For a write operation, Control Done must not be set until all accepted write data has been committed to the emulated media.

### DSKP Condition

During TS4 of `DSKP`, the controller asserts `IO_SKIP_REQ` when:

```text
STATUS[11]
OR
STATUS[8:0] != 0
```

`DSKP` does not clear the Status Register.

### Interrupt Condition

The controller asserts its interrupt contribution when:

```text
COMMAND[8]
AND
(
    STATUS[11]
    OR
    STATUS[8:0] != 0
)
```

### Unused Bit

`STATUS[9]` is not used and must read as `0`.

The controller must not expose implementation-specific status through this bit.

## Control Done

Control Done is set when required by RK8E-compatible behavior, including:

- successful completion of a data transfer
- completion of a seek-only operation
- completion of a recalibrate operation when enabled by the Command Register
- an error that terminates an active operation

Control Done remains set until cleared by a defined controller operation.

Control Done must not be set before all programmer-visible effects of a successful operation have completed.

For a write operation, Control Done must not be set until all accepted data has been committed to the emulated disk image.

## Error Condition

The Error condition represents the logical OR of the RK8E-defined active error conditions.

The Error condition is used by:

- `DSKP`
- controller interrupt generation
- operation termination behavior

The controller must not expose implementation-specific storage errors directly.

An implementation-specific failure must be translated into the closest applicable RK8E-visible status and error condition.

## Interrupt Behavior

The Command Register contains the RK8E interrupt-enable bit.

The controller asserts its interrupt contribution when:

```text
COMMAND[8]
AND
(CONTROL_DONE OR ERROR)
```

The controller does not modify the CPU interrupt-enable state.

Clearing the RK8E Status Register removes the interrupt contribution when neither Control Done nor another qualifying error remains asserted.

## Busy Behavior

The controller is busy while an RK8E operation is active.

While busy, the following instructions must not replace the active operation state:

- `DLAG`
- `DLCA`
- `DLDC`
- `DCLD`

If one of those operations is attempted while the controller is busy:

- the requested state change is not performed
- Control Busy Error is set
- the active operation continues
- Control Done is set when the active operation later completes or terminates

`DCLC` may abort an active operation.

## Device 74 IOT Table

| IOT | Mnemonic | Contract |
|---:|---|---|
| `6740` | Undefined | Ignore |
| `6741` | DSKP | Request skip when Control Done or Error is set |
| `6742` | DCLR | Perform the AC-selected clear or recalibrate operation and clear AC |
| `6743` | DLAG | Load Disk Address Register, clear AC, and initiate the selected operation |
| `6744` | DLCA | Load Current Address Register and clear AC |
| `6745` | DRST | Clear AC and read Status Register |
| `6746` | DLDC | Load Command Register, clear AC, and clear Status Register |
| `6747` | DMAN | Perform one selected maintenance operation and clear AC |

# DSKP

## Controller Contract

Nothing occurs during TS1 through TS3.

During TS4, the controller asserts `IO_SKIP_REQ` when:

```text
IOT_ACTIVE
AND
ADDRESS_MATCH
AND
(IOP = 1)
AND
(CONTROL_DONE OR ERROR)
```

DSKP does not modify controller state.

DSKP does not clear Control Done or Error.

# DCLR

## AC Selection

`DCLR` decodes `AC[1:0]`.

The bit numbering in this document follows the project convention in which `AC[11]` is the most significant bit and `AC[0]` is the least significant bit.

| `AC[1:0]` | Operation | Contract |
|---:|---|---|
| `00` | DCLS | Clear Status Register |
| `01` | DCLC | Clear RK8E controller logic and abort any active controller operation |
| `10` | DCLD | Initiate recalibration of the selected drive to cylinder `000` |
| `11` | DCLS | Clear Status Register |

## Controller Contract

During TS2:

- the controller combinationally decodes `AC[1:0]`
- the controller asserts `IO_WRITE_REQ`
- the controller asserts `IO_CLEAR_AC_REQ`

At TP2, the selected operation commits.

No intermediate selector register is required.

## DCLS

At TP2:

```text
STATUS_REGISTER <- 0
CONTROL_DONE <- 0
ERROR <- 0
```

DCLS does not abort an active disk operation unless required by a specific RK8E status-clearing rule.

## DCLC

At TP2:

- the active controller operation is aborted
- RK8E controller logic is cleared
- Command Register is cleared
- Status Register is cleared
- controller DMA request is deasserted
- controller DMA ownership is released at the next permitted ownership boundary
- pending controller completion is canceled

DCLC does not clear or reset the selected emulated drive state.

DCLC is destructive.

Data accepted for a write but not yet committed to the emulated disk may be discarded.

No additional error is raised solely because DCLC discarded uncommitted write data.

## DCLD

At TP2:

- recalibration of the selected drive to cylinder `000` is initiated
- the controller becomes busy
- Control Done is cleared as required by RK8E-compatible operation

Recalibration completes asynchronously relative to the initiating IOT.

When recalibration completes:

- the selected drive is positioned logically at cylinder `000`
- Control Done is set according to the Command Register completion-enable behavior
- controller busy state ends

No physical head movement is required by this contract.

# DLAG

## Controller Contract

During TS2:

- the controller asserts `IO_WRITE_REQ`
- the controller asserts `IO_CLEAR_AC_REQ`

At TP2, when the controller is idle:

```text
DISK_ADDRESS_REGISTER <- AC
```

At TP2, the controller also initiates the operation selected by the Command Register.

If the controller is busy:

- Disk Address Register is not loaded
- no new operation is started
- Control Busy Error is set
- the existing operation continues

The pre-TP2 AC value is used.

# DLCA

## Controller Contract

During TS2:

- the controller asserts `IO_WRITE_REQ`
- the controller asserts `IO_CLEAR_AC_REQ`

At TP2, when the controller is idle:

```text
CURRENT_ADDRESS_REGISTER <- AC
```

If the controller is busy:

- Current Address Register is not loaded
- Control Busy Error is set
- the existing operation continues

The pre-TP2 AC value is used.

# DRST

## Controller Contract

During TS3:

```text
IO_CLEAR_AC_REQ = 1
```

During TS4:

- the controller drives the Status Register onto DB
- the controller asserts `IO_READ_REQ`

DRST does not modify controller state.

DRST does not clear the Status Register.

# DLDC

## Controller Contract

During TS2:

- the controller asserts `IO_WRITE_REQ`
- the controller asserts `IO_CLEAR_AC_REQ`

At TP2, when the controller is idle:

```text
COMMAND_REGISTER <- AC
STATUS_REGISTER <- 0
CONTROL_DONE <- 0
ERROR <- 0
```

If the controller is busy:

- Command Register is not loaded
- Status Register is not cleared
- Control Busy Error is set
- the existing operation continues

The pre-TP2 AC value is used.

# DMAN

## Purpose

`DMAN` provides RK8E maintenance behavior.
 
Maintenance behavior is required only to the extent necessary to reproduce the RK8E-visible maintenance interface.

The controller implementation does not need to reproduce the physical RK8E register construction.

## Maintenance Function Selection

`DMAN` uses the pre-clear AC value as a maintenance control word.

Exactly one maintenance function-select bit may be asserted for one `DMAN` operation.

Maintenance function-select bits must not be combined.

A maintenance data bit may accompany a maintenance function when required by that function.

The statement that maintenance functions cannot be microprogrammed is preserved as the following contract:

```text
One DMAN instruction selects one maintenance function.
```
## Maintenance Controls

The project AC-bit numbering is used below.

| AC bit | Maintenance function |
|---:|---|
| `AC[11]` | Enter or enable maintenance mode |
| `AC[10]` | Enable the defined lower-data-buffer shift path |
| `AC[9]` | Shift maintenance data through the CRC path |
| `AC[8]` | Shift Command Register data into the lower data-buffer path |
| `AC[7]` | Shift Surface/Sector data into the lower data-buffer path |
| `AC[6]` | Shift maintenance data into the upper data-buffer path and advance maintenance counters |
| `AC[5]` | Initiate one maintenance DMA transfer |
| `AC[4]` | Read the lower maintenance-visible data buffer into AC |
| `AC[1]` | Maintenance data bit used by applicable shift functions |

The exact serial ordering and maintenance-visible results must match the DEC RK8E maintenance definitions.

## Controller Contract

During TS2:

- the controller asserts `IO_WRITE_REQ`
- the controller asserts `IO_CLEAR_AC_REQ`
- the controller evaluates the selected maintenance function from the pre-TP2 AC value

At TP2:

- the selected maintenance operation commits or is initiated
- AC is cleared through the standard CPU response contract

For the lower-data-buffer read function:

- the selected read function is accepted at TP2
- during TS4, the controller drives the maintenance-visible lower data-buffer value onto DB
- during TS4, the controller asserts `IO_READ_REQ`

The controller must preserve the selected read operation through TS4 without exposing any additional programmer-visible state.

## Unsupported DMAN Combinations

A DMAN operation with:

- no recognized function selected
- more than one maintenance function selected
- a reserved function combination

is ignored except for the AC-clear behavior defined for DMAN.

No maintenance operation is performed.

# Asynchronous Disk Operations

Disk operations initiated by `DLAG` continue after the IOT completes.

The processor may continue instruction execution between granted DMA cycles.

Software determines completion through:

- `DSKP`
- `DRST`
- interrupt service when enabled

The initiating IOT does not wait for the complete disk operation.

# Transfer Length

The Command Register selects a transfer length of:

- 128 words
- 256 words

The controller maintains the number of words remaining in the active RK8E operation.

The operation count persists across multiple DMA grants.

The operation completes only after the required number of successful word transfers has occurred or an RK8E-defined terminating error occurs.

# DMA Participation

### DMA Capability

The RK8E-compatible controller uses DMA.  
The controller occupies one configured DMA priority channel in the range 0 through 14.  
DMA priority 15 is reserved as the no-controller-selected encoding and must not be assigned to the controller.  
DMA priority is independent of device address 74.  
The priority-configuration mechanism is outside this contract.

## DMA Request

The controller asserts its configured `DMA_REQ[n]` when:

- an RK8E operation is active
- at least one word requires transfer
- the controller can complete the next DMA word transfer

The controller keeps its request asserted while additional immediately transferable words remain.

The controller may deassert its request when it cannot complete another word transfer.

The controller reasserts its request when another word can be transferred.

## Grant Acceptance

The controller accepts DMA ownership only when:

```text
DMA_GRANT = 1
AND
DMA_GRANT_ID = CONTROLLER_DMA_PRIORITY
```

The controller does not accept DMA ownership while DMA_GRANT_ID is 15.  
The controller must not drive DMA-owned interfaces without a matching valid controller selection..

## DMA Read from Disk to Memory

For an RK8E disk-read operation, data moves:

```text
controller -> memory
```

The controller:

- supplies MFB from the Command Register memory-field bits
- supplies AB from the incremented Current Address Register
- drives the next disk word onto MDB
- asserts WR
- deasserts RD

At TP2:

- memory accepts the word

At TP3:

- the Current Address Register retains the incremented address
- the RK8E operation count advances by one word
- the transferred word is complete from the RK8E DMA interface perspective

## DMA Write from Memory to Disk

For an RK8E disk-write operation, data moves:

```text
memory -> controller
```

The controller:

- supplies MFB from the Command Register memory-field bits
- supplies AB from the incremented Current Address Register
- asserts RD
- deasserts WR

Memory drives MDB.

At TP2:

- the controller accepts the memory word

At TP3:

- the Current Address Register retains the incremented address
- the RK8E operation count advances by one word
- the accepted word becomes part of the active disk-write operation

## Address Increment

For every successful DMA word transfer:

```text
NEXT_CURRENT_ADDRESS =
    (CURRENT_ADDRESS_REGISTER + 1) modulo 4096
```

The transfer uses `NEXT_CURRENT_ADDRESS`.

The memory field remains unchanged when the Current Address Register wraps from `7777` to `0000`.

## Bounded DMA Bursts

The RK8E operation count and DMA-arbiter burst count are independent.

The RK8E controller maintains:

- total words remaining in the active disk operation

The DMA arbiter maintains:

- words transferred during the current grant

An active RK8E operation may span multiple DMA grants.

When the arbiter terminates a grant because the configured burst limit is reached:

- the RK8E operation remains active
- the RK8E operation count is preserved
- the Current Address Register is preserved
- the controller keeps or later reasserts its DMA request while work remains
- the controller participates in normal re-arbitration

## DMA Completion

One DMA major-state cycle transfers at most one RK8E word.

A word is counted only after a successful TP2 memory transfer and the corresponding TP3 count update.

A failed or uncommitted transfer must not advance:

- Current Address Register
- RK8E operation count
- Control Done state

## DMA Grant Loss

When the controller-facing grant ends:

- the controller releases MFB
- the controller releases AB
- the controller releases MDB when applicable
- the controller deasserts RD
- the controller deasserts WR

The active RK8E disk operation remains pending when additional words remain.

# Write Completion and Data Integrity

A disk-write operation is complete only after all accepted words have been committed to the emulated disk.

Control Done must not be set while accepted write data remains uncommitted.

Normal grant termination does not discard accepted write data.

The following operations may destructively cancel uncommitted write data:

- system initialization
- `DCLC`

When either destructive operation occurs:

- the active write is aborted
- uncommitted write data may be discarded
- no additional error is required solely because the destructive clear discarded the data

# System Initialization

System initialization occurs during:

- system power-up
- the processor CLEAR operation
- another system-level initialization event defined by the architecture

System initialization clears:

- RK8E controller logic
- Command Register
- Current Address Register
- Disk Address Register
- Status Register
- Control Done
- Error
- maintenance state
- controller DMA request
- active controller operation
- pending controller completion

System initialization also resets the emulated RK05 drive-control state.

System initialization does not:

- erase an emulated disk image
- reformat media
- alter committed disk data

System initialization is destructive to active operations.

Uncommitted write data may be discarded without an additional error indication.

# DCLC and System Initialization Distinction

`DCLC` clears RK8E controller state but does not reset the selected emulated RK05 drive-control state.

System initialization clears both:

- RK8E controller state
- emulated RK05 drive-control state

Neither operation erases committed media contents.

# Bootstrap Compatibility

## Default Bootstrap Drive

The standard bootstrap drive is drive `0`.

Drive `0` must present valid RK05-compatible media for a successful bootstrap.

The mapping of drive `0` to physical storage is outside this contract.

## Bootstrap Initial State

After system initialization:

```text
COMMAND_REGISTER = 0000
CURRENT_ADDRESS_REGISTER = 0000
DISK_ADDRESS_REGISTER = 0000
STATUS_REGISTER = 0000
```

The controller is idle.

The controller DMA request is inactive.

## Bootstrap Operation

The standard RK8E bootstrap may issue `DLAG` with:

```text
AC = 0000
```

This selects the RK8E operation and disk location represented by the cleared Command Register and cleared disk-address value.

The bootstrap-visible source location is:

- drive 0
- cylinder 0
- surface 0
- sector 0

Because Current Address increments before each DMA transfer, the first transferred word is written to:

```text
memory field 0
address 0001
```

The remainder of the sector is transferred into sequential memory locations using the RK8E Current Address rules.

## Bootstrap Completion

Control Done is set only after the required bootstrap transfer has completed successfully.

Missing, unavailable, invalid, or unreadable drive-0 media must produce RK8E-compatible not-ready or error behavior.

The controller must not silently substitute zero-filled data for unavailable bootstrap media.

# Unsupported Operations

`6740` is unsupported.

An unsupported operation produces:

- no DB drive
- no DB capture
- no `IO_CLEAR_AC_REQ`
- no `IO_SKIP_REQ`
- no `IO_WAIT`
- no controller state change
- no register change
- no interrupt effect
- no DMA effect

Device addresses `73` and `75` are not part of this controller.

# Implementation Boundary

The controller implementation must satisfy this contract but may choose its own:

- internal buffering
- internal state machines
- SD or CF interface
- backing-image representation
- disk-image selection mechanism
- card filesystem
- caching
- write aggregation
- CRC implementation
- geometry-translation logic
- component selection
- DMA-priority configuration mechanism
- device-address configuration mechanism

None of those choices may alter the programmer-visible behavior defined in this document.
