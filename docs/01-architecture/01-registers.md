# Register Model Specification

## 1. Purpose
Defines all system state.

All stable values in the system must reside in registers.

---

## 2. Architectural Registers
- AC: [Accumulator](#ac--accumulator)
- DF: [Data Field](#df--data-field)
- IE: [Interrupt Enable](#ie--interrupt-enable)
- IF: [Instruction Field](#if--instruction-field)
- L:  [Link](#l--link)
- MQ: [Multiplier Quotient](#mq--multiplier-quotient)
- PC: [Program Counter](#pc--program-counter)
- FP_SR: [Switch Register](#fp_sr--switch-register)


---

## 3. Control-Visible State
- CIFP: [Change Instruction Field Pending](#cifp--change-instruction-field-pending)
- HLT_REQ: [Halt Request](#hlt_req--halt-request)
- II: [Interrupt Inhibit](#ii--interrupt-inhibit)
- IR: [Instruction Register](#ir--instruction-register)
- MS: [Major State](#ms--major-state)
- RUN: [Run State](#run--run-state)

---

## 4. Internal Registers
- DIF: [Deferred Instruction Field](#dif--deferred-instruction-field)
- EA_ADDR: [Effective Address (Address Portion)](#ea_addr--effective-address-address-portion)
- IB: [Interrupt Buffer](#ib--interrupt-buffer)
- IOT_TRANSFER: [IOT Transfer Pending](#iot_transfer---pending-external-iot-transfer)
- MA: [Memory Address](#ma--memory-address)
- MB: [Memory Buffer](#mb--memory-buffer)

---

## 5. Register Definitions

### AC – Accumulator
Width: 12 bits

Role: Primary arithmetic and logical operand/result register

Visibility: Global

Invariants:
- Holds the canonical 12-bit result of the last completed operation
- Forms a composite 13-bit value with L for arithmetic and shifts
- Stable outside EXECUTE

Constraints:
- Modified only during EXECUTE
- Must not be written during FETCH or DEFER
- All operations affecting AC must define L behavior if carry/borrow arises

Writers:
- ALU result path
- Shift/rotate network (AC:L)
- OPR control operations (CLA, CMA, IAC)
- MQ transfer path

---

### CIFP – Change Instruction Field Pending

Width: 1 bit

Role: Records that a deferred instruction-field change is pending, awaiting the next JMP or JMS.  

Visibility: Control-visible  

Invariants:
- Set from execution of CIF or RMF until the deferred field is applied at the next JMP/JMS
- While set, interrupt recognition is inhibited by holding `II` set across the deferred-field-change interval  

Constraints:
- Set only by CIF or RMF execution (`IR_WRITES_IF` or `IR_RESTORES_IB`)
- Cleared when JMP or JMS applies the pending field, during interrupt entry, or by Load Address
- Must not be directly modified by datapath logic

Writers:
- IOT execution (CIF or RMF; `CIFP_SET` micro-operation)
- MRI execution (JMP/JMS; `CIFP_CLEAR` micro-operation)
- Interrupt entry (`CIFP_CLEAR` micro-operation)
- Console Load Address (`CIFP_CLEAR` micro-operation)

---

### DF – Data Field

Width: 3 bits

Role: Upper field for operand memory addressing

Visibility: Global

Invariants:
- Supplies high-order bits for all data memory accesses
- May differ from IF

Constraints:
- Modified only by field control instructions
- Must remain stable during a memory access sequence

Writers:
- Field instruction control logic

---

### DIF – Deferred Instruction Field
  
Width: 3 bits  

Role: Holds a pending instruction field value awaiting transfer to IF at the next JMP or JMS.  This register implements the deferred field-change behavior required for CIF and RMF.  

Visibility: Internal (control-managed)  

Invariants:
- Equal to `IF` except while a deferred instruction-field change is pending
- When a deferred instruction-field change is pending, its value is applied to `IF` at the next JMP or JMS

Constraints:
- Loaded by CIF (from IR), RMF (from IB), Load Address (from FP_IF), and cleared at interrupt entry
- Applied to IF only at the JMP/JMS that concludes a pending deferred field change
- Must not change during FETCH, DEFER, or EXECUTE except at the defined load, clear, and apply points  

Writers:
- IOT execution (CIF; IR_IF_TO_DIF)
- IOT execution (RMF; IB_TO_DIF)
- Console (Load Address; FP_IF_TO_DIF)
- Interrupt entry (DIF_CLEAR)

---

### EA_ADDR – Effective Address (Address Portion)

Width: 12 bits

Role: Holds the 12-bit address portion of the effective address.

The full logical effective address is a composite:

EA = (EA_FIELD, EA_ADDR)

Where:
- EA_ADDR is the 12-bit value stored in this register
- EA_FIELD is IF or DF, selected via MFB_SRC, and is not stored here

No register stores the combined value; EA is a composite concept, not a register.

Visibility: Internal

Invariants:
- Fully resolved before operand access
- Stable prior to EXECUTE

Constraints:
- Computed during FETCH/DEFER only
- Resolution may include indirect and auto-increment effects
- Must not change during EXECUTE

Writers:
- Address calculation logic
- Indirect resolution path

---

### FP_SR – Switch Register
Width: 12 bits

Role: External input register from front panel

Visibility: External (read-only to CPU)

Invariants:
- Reflects external switch state at sampling time
- No guarantee of stability outside explicit read

Constraints:
- Cannot be written by CPU
- Sampled only during specific instructions

Writers:
- External hardware only

---

### HLT_REQ – Halt Request

Width: 1 bit

Role: Records that a halt has been requested and is pending consumption at an instruction-completion boundary.

Visibility: Control-visible

Invariants:
- Set when a halt is requested (STOP switch or HLT instruction)
- Remains set until the pending halt is consumed at an instruction-completion boundary
- Stable within a major state; updated only at TP

Constraints:
- Updated only from HLT_REQ_NEXT (sequencing control), committed at TP
- Set by the STOP command and by the HLT instruction
- Cleared when the pending halt is consumed (RUN transitions to 0)
- Must not be directly modified by datapath logic or μops

Writers:
- Sequencing control (HLT_REQ_NEXT)

---

### IB – Interrupt Buffer

Width: 6 bits

Role: Holds the instruction and data fields (IF, DF) saved at interrupt entry.  Serves as the source for RIB (read into AC) and RMF (restore to IF/DF).

Bit layout:
- IB[5:3] = saved IF
- IB[2:0] = saved DF

Visibility: Internal (control-managed)

Invariants:
- Captures IF and DF at interrupt entry
- Stable from interrupt entry until the next interrupt entry

Constraints:
- Written only at interrupt entry
- Read only by RIB and RMF

Writers:
- Interrupt entry control (IF_DF_TO_IB)

---

### IE – Interrupt Enable
Width: 1 bit

Role: Global interrupt gating flag

Visibility: Global

Invariants:
- Determines whether interrupts are recognized
- Stable during instruction execution

Constraints:
- Set only by ION
- Cleared by IOF, SKON, and interrupt entry
- Changes only at defined TP events

Writers:
- IOT execution (ION, IOF, or SKON; `IE_SET` or `IE_CLEAR` micro-operation)
- Interrupt entry (`IE_CLEAR` micro-operation)

---

### IF – Instruction Field
Width: 3 bits

Role: Upper field for instruction fetch addressing

Visibility: Global

Invariants:
- Supplies high-order bits of instruction fetch address
- Constant for the duration of an instruction cycle

Constraints:
- Modified only by field control instructions
- Must not change during FETCH, DEFER, or EXECUTE of a single instruction

Writers:
- Field instruction control logic

---

### II – Interrupt Inhibit
Width: 1 bit

Role: Interrupt recognition gating flag

Visibility: Control-visible

Invariants:  
- Prevents interrupt recognition when set  
- Used in conjunction with IE to determine interrupt eligibility  
- Stable during instruction execution  

Constraints:
- Set only by ION, CIF, and RMF instructions
- Cleared during FETCH when no deferred instruction-field change is pending (`CIFP = 0`)
- Must not be directly modified by datapath logic  

Writers:
- IOT execution (ION, CIF, or RMF; `II_SET` μop)
- FETCH execution (`II_CLEAR` μop)

---

### IOT_TRANSFER - Pending External-IOT Transfer

Width: 2 bits  
Role: Preserves an accepted external-IOT DB transfer request for execution during the immediately following TS.  
Visibility: Internal

Encoding:

```text
00 = no pending DB transfer
01 = pending device-to-CPU read
10 = pending CPU-to-device write
11 = invalid
```

Invariants:

- `IOT_TRANSFER` is loaded at TP2 or TP3 when an external-IOT transfer request is accepted.
- An accepted `IO_READ_REQ` loads `01`.
- An accepted `IO_WRITE_REQ` loads `10`.
- No accepted transfer request loads `00`.
- Encoding `11` must never be loaded.
- The value remains stable throughout the following transfer TS.
- A transfer accepted at TP2 executes during TS3 and commits at TP3.
- A transfer accepted at TP3 executes during TS4 and commits at TP4.
- The completed transfer is cleared or replaced at its commit TP.

Constraints:

- `IOT_TRANSFER` records transfer direction only.
- It does not contain DB data.
- It does not identify the selected controller.
- It does not itself assert `/DB_READ` or `/DB_WRITE`.
- It must not persist beyond the external-IOT EXECUTE major state.

Writers:

- external-IOT request-acceptance control at TP2 or TP3
- external-IOT completion control at TP3 or TP4

Consumers:

- `/DB_READ` generation during the transfer TS
- `/DB_WRITE` generation during the transfer TS
- `DB_READ_TO_AC` selection at the transfer commit TP
- `DB_WRITE_FROM_AC` selection during the transfer TS

---

### IR – Instruction Register
Width: 12 bits

Role: Holds the current instruction being executed

Visibility: Control-visible

Invariants:
- Contains the instruction for decode and execution
- Stable from end of FETCH through EXECUTE

Constraints:
- Loaded only during FETCH
- Must not change after decode begins

Writers:
- Memory read path (via MB)

---

### L – Link
Width: 1 bit

Role: Carry/extend bit for AC; participates in shifts, arithmetic, and explicit bit ops

Visibility: Global

Invariants:
- Represents the 13th bit of AC:L during arithmetic
- Always defined after any instruction that targets it
- Stable outside EXECUTE

Constraints:
- Modified only during EXECUTE
- May be updated by:
  - ALU carry/borrow
  - Shift/rotate operations
  - Explicit OPR instructions (CLL, CML, STL)
- Multiple updates must follow defined micro-op ordering

Writers:
- ALU carry-out path
- Shift/rotate network
- OPR control logic

---

### MA – Memory Address
Width: 12 bits

Role: Address presented to memory

Visibility: Internal

Invariants:
- Holds valid address before memory access
- Reflects either PC-derived or EA-derived address

Constraints:
- Loaded only during address generation phases
- Must remain stable during memory cycle
- MA is the sole source of addresses presented to memory

Writers:
- PC path (instruction fetch)
- EA path (operand access)
- Address formation logic (page/indirect resolution)

---

### MB – Memory Buffer
Width: 12 bits

Role: Data interface register between CPU datapath and memory system

Visibility: Internal

Invariants:
- Holds the value to be written to memory during write cycles
- Holds the value returned from memory during read cycles
- Represents the only architecturally visible staging point for memory data
- Stable whenever either CPU or memory is actively consuming its value

Constraints:
- Must be stable:
  - During memory read data return (memory → MB)
  - During memory write (MB → memory)
  - During CPU consumption (MB → internal datapath)
- Loaded by:
  - Memory read operations
  - CPU datapath prior to memory write
- Must not change while:
  - Memory strobe is active
  - DMA transfer is in progress using MB
- Cannot be bypassed for architecturally visible memory transfers

Writers:
- Memory data return path
- CPU internal bus (store operations)

Consumers:
- CPU datapath (instruction load, operand use)
- Memory system (write cycles)
- DMA logic

---

### MS – Major State
Width: 3 bits

Role: Encodes processor phase (FETCH, DEFER, EXECUTE, INTERRUPT, DMA)

Visibility: Control

Invariants:
- Exactly one state active at a time
- Transitions follow defined state machine

Constraints:
- Changes only at cycle boundaries
- Not directly influenced by datapath combinational logic
- Initially only 0-4 are valid values 5-7 are reserved

Writers:
- Control state machine

---

### MQ – Multiplier Quotient
Width: 12 bits

Role: Secondary arithmetic register for multiply/divide and extensions

Visibility: Global

Invariants:
- Holds operand or intermediate state during extended arithmetic
- Remains unchanged when not explicitly used

Constraints:
- Modified only by defined instructions
- Must not be altered by general ALU operations

Writers:
- Multiply/divide microcode path
- AC transfer path

---

### PC – Program Counter
Width: 12 bits

Role: Holds the address of the next instruction to be fetched

Visibility: Global

Invariants:
- Forms the instruction fetch address when combined with IF
- Represents the next sequential instruction unless modified by control flow
- Stable from address issue through FETCH completion
- Always contains a valid address within the current instruction field

Constraints:
- Incremented during FETCH after address is issued
- Modified during EXECUTE only by:
  - Conditional skip (increment)
  - JMP (load)
  - JMS (store return address, then load)
- Must not change during DEFER
- Update must complete before next FETCH TS1

Writers:
- PC + 1 increment path
- Control flow load path (JMP/JMS)

---

### RUN – Run State

Width: 1 bit

Role: Indicates whether normal instruction sequencing is active.

Visibility: Control-visible

Invariants:
- When RUN = 1, the processor executes the normal major-state sequence
- When RUN = 0, normal instruction sequencing is inactive and console operations may be performed
- Preserves all other architectural state while halted
- Stable within a major state; updated only at TP

Constraints:
- Updated only from RUN_NEXT (sequencing control), committed at TP
- Set to 1 by START and CONTINUE
- Set to 0 when a pending halt is consumed at an instruction-completion boundary, and at the completion boundary defined by Single Instruction and Single Step modes
- Must not be directly modified by datapath logic or μops

Writers:
- Sequencing control (RUN_NEXT)

