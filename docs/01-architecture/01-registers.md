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
- SKIP: [Skip](#skip--skip)

---

## 4. Internal Registers
- DIF: [Deferred Instruction Field](#dif--deferred-instruction-field)
- EA_ADDR: [Effective Address (Address Portion)](#ea_addr--effective-address-address-portion)
- IB: [Interrupt Buffer](#ib--interrupt-buffer)
- IOT_TRANSFER: [IOT Transfer Pending](#iot_transfer---pending-external-iot-transfer)
- MA: [Memory Address](#ma--memory-address)
- MAPR: [Mapping Register](#mapr--mapping-register)
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
- Stable outside EXECUTE, except at the FETCH TP3 of an OPR and when cleared by the START or CLEAR console operation while halted

Constraints:
- Modified only during EXECUTE, at the FETCH TP3 of an OPR (`OPR_PASS`), or by the START or CLEAR console operation while halted
- Must not be written during DEFER, or during FETCH except at that TP3
- All operations affecting AC must define L behavior if carry/borrow arises

Writers:
- ALU result path
- OPR pass unit (Group 1 OPR: CLA, CMA, IAC, rotates, BSW, [Group 1 Execution](../03-microarchitecture/07-opr/01-group1-execution.md); Group 2 OPR: CLA, OSR, [Group 2 Execution](../03-microarchitecture/07-opr/02-group2-execution.md); Group 3 OPR: CLA, MQA, MQL, SWP, [Group 3 Execution](../03-microarchitecture/07-opr/03-group3-execution.md))
- Shift/rotate network (AC:L)
- IOT execution (GTF)
- System initialization (CAF, front-panel CLEAR; AC_CLEAR micro-operation)
- Console START (AC_CLEAR micro-operation)
- Power-on reset

---

### CIFP – Change Instruction Field Pending

Width: 1 bit

Role: Records that a deferred instruction-field change is pending, awaiting the next JMP or JMS.  

Visibility: Control-visible  

Invariants:
- Set from execution of CIF, RMF, or RTF until the deferred field is applied at the next JMP/JMS
- While set, interrupt recognition is inhibited by holding `II` set across the deferred-field-change interval  

Constraints:
- Set only by CIF, RMF, or RTF execution
- Cleared when JMP or JMS applies the pending field, during interrupt entry, or by Load Address
- Must not be directly modified by datapath logic  

Writers:
- IOT execution (CIF, RMF, or RTF; CIFP_SET micro-operation)
- FETCH TP3 (direct JMP), DEFER TP4 (JMP I), and MRI execution TP1 (JMS); CIFP_CLEAR micro-operation
- Interrupt entry (CIFP_CLEAR micro-operation)
- Console Load Address (CIFP_CLEAR micro-operation)

---

### DF – Data Field

Width: 3 bits

Role: Upper field for operand memory addressing

Visibility: Global

Invariants:
- Supplies the field for the final operand access of indirect MRI operations
- May differ from IF

Constraints:
- Modified only by field-control and processor-state restoration instructions
- Must remain stable during a memory access sequence  

Writers:
- IOT execution (CDF; IR_DF_TO_DF)
- IOT execution (RMF; IB_TO_DF)
- IOT execution (RTF; AC_TO_DF)
- Console Load Address (FP_DF_TO_DF)
- Interrupt entry (DF_CLEAR)

---

### DIF – Deferred Instruction Field
  
Width: 3 bits  

Role: Holds a pending instruction field value awaiting transfer to IF at the next JMP or JMS.  This register implements the deferred field-change behavior required for CIF, RMF, and RTF.  

Visibility: Internal (control-managed)  

Invariants:
- Equal to `IF` except while a deferred instruction-field change is pending
- When a deferred instruction-field change is pending, its value is applied to `IF` at the next JMP or JMS

Constraints:
- Loaded by CIF from IR, RMF from IB, RTF from AC[5:3], and Load Address from FP_IF
- Cleared at interrupt entry
- Applied to IF only at the JMP or JMS that concludes a pending deferred field change: at FETCH TP3 of a direct JMP, DEFER TP4 of a JMP I, or EXECUTE TP1 of a JMS
- Must not change during FETCH, DEFER, or EXECUTE except at the defined load, clear, and apply points  

Writers:
- IOT execution (CDF; IR_IF_TO_DIF)
- IOT execution (RMF; IB_TO_DIF)
- IOT execution (RTF; AC_TO_DIF)
- Console Load Address (FP_IF_TO_DIF)
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
- Address calculation logic: IR[6:0], with the page from MA[11:7] or zero (FETCH TS3)
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
- Cleared by the power-on reset
- Must not be directly modified by datapath logic or μops

Writers:
- Sequencing control (HLT_REQ_NEXT)

---

### IB – Interrupt Buffer

Width: 6 bits

Role: Holds the instruction and data fields (IF, DF) saved at interrupt entry, the save field.  Serves as the source for RIB (read into AC), GTF (AC[5:0] of the processor flags word), and RMF (restore to IF/DF).

Bit layout:
- IB[5:3] = saved IF
- IB[2:0] = saved DF

Visibility: Internal (control-managed)

Invariants:
- Captures IF and DF at interrupt entry
- Stable from interrupt entry until the next interrupt entry

Constraints:
- Written only at interrupt entry; not initialized at power-on or by system initialization, so undefined until the first interrupt entry
- Read only by RIB, GTF, and RMF

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
- Set only by ION or RTF
- Cleared by IOF, SKON, interrupt entry, system initialization (CAF, front-panel CLEAR), console START, or the power-on reset
- Changes only at defined TP events

Writers:
- IOT execution (ION or RTF; IE_SET micro-operation)
- IOT execution (IOF or SKON; IE_CLEAR micro-operation)
- Interrupt entry (IE_CLEAR micro-operation)
- System initialization (CAF, front-panel CLEAR; IE_CLEAR micro-operation)
- Console START (IE_CLEAR micro-operation)
- Power-on reset

---

### IF – Instruction Field
Width: 3 bits

Role: Upper field for instruction fetch addressing

Visibility: Global

Invariants:
- Supplies high-order bits of instruction fetch address
- Supplies high-order bits for direct MRI access and indirect pointer access
- Constant for the duration of an instruction cycle, except that a JMP or JMS applies a pending deferred field change: at FETCH TP3 of a direct JMP, DEFER TP4 of a JMP I, or EXECUTE TP1 of a JMS

Constraints:
- Modified only by field control instructions
- Must not change except where a JMP or JMS applies a pending deferred field change: at FETCH TP3 of a direct JMP, DEFER TP4 of a JMP I, or EXECUTE TP1 of a JMS

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
- Set only by ION, CIF, RMF, and RTF instructions
- Cleared during FETCH when no deferred instruction-field change is pending (CIFP = 0), when a JMP or JMS with a pending field change completes it (at FETCH TP3 of a direct JMP, DEFER TP3 of a JMP I, or EXECUTE TP1 of a JMS), and by the START console operation
- Must not be directly modified by datapath logic  

Writers:
- IOT execution (ION, CIF, RMF, or RTF; II_SET micro-operation)
- FETCH execution (II_CLEAR micro-operation)
- JMP or JMS applying a pending field change (II_CLEAR micro-operation)
- Console START (II_CLEAR micro-operation)

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
- Set to `00` by the power-on reset.

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
- Valid from FETCH TP2; stable from FETCH TP2 through the instruction's last major state

Constraints:
- Loaded only at FETCH TP2
- Must not change after decode begins

Writers:
- Memory data bus (MDB), at FETCH TP2, in parallel with MB

---

### L – Link
Width: 1 bit

Role: Carry/extend bit for AC; participates in shifts, arithmetic, and explicit bit ops

Visibility: Global

Invariants:
- Represents the 13th bit of AC:L during arithmetic
- Always defined after any instruction that targets it
- Stable outside EXECUTE, except at the FETCH TP3 of a Group 1 OPR (a Group 2 or Group 3 OPR reloads L unchanged at its FETCH TP3) and when cleared by the START or CLEAR console operation while halted

Constraints:
- Modified only during EXECUTE, at the FETCH TP3 of a Group 1 OPR (`OPR_PASS`), or by the START or CLEAR console operation while halted
- May be updated by:
  - ALU carry (a carry out of the most significant AC bit complements L)
  - Rotate operations
  - Explicit OPR instructions (CLL, CML, STL)
  - RTF processor-state restoration
  - System initialization (CAF, front-panel CLEAR; L_CLEAR micro-operation)
  - Console START (L_CLEAR micro-operation)
  - Power-on reset
- Multiple updates must follow defined micro-op ordering

Writers:
- ALU link output (ADD and INC; [ALU Evaluation](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#731-alu-evaluation))
- OPR pass unit link output (Group 1 OPR: CLL, CML, IAC carry, rotates)
- IOT execution (RTF; AC_TO_L)
- System initialization (CAF, front-panel CLEAR; L_CLEAR micro-operation)
- Console START (L_CLEAR micro-operation)
- Power-on reset

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

Consumers:
- AB (the memory address)
- The EA formation unit: MA[11:7] supplies the current page. MA holds the instruction's address from FETCH TP1 until DEFER or EXECUTE TS1 reloads it

---

### MAPR – Mapping Register
Width: 8 bits

Role: Holds the mapping ROM entry for the current TS of EXECUTE, so that the mapping ROM is evaluated one TS ahead and lies outside the control-store timing path ([Control Store Organization §5.4](../04-control/08-control-store-organization.md#54-mapping-register-and-execute-selection))

Visibility: Internal (control store)

Encoding:

```text
MAPR[4:0] = variant
MAPR[6:5] = overlay group
MAPR[7]   = sequencer decode
```

Invariants:
- During TS n, holds the mapping ROM entry for EXECUTE TS n of the current IR
- Holds the TS1 entry of the held instruction while halted
- Used only while MS_EFF_IS_EXECUTE = 1

Constraints:
- Loaded at every main-sequence TP (TP1 to TP4)
- Not loaded at TPC
- Not loaded by any micro-operation; it is not a control-word target
- Power-on value undefined; not used before the first EXECUTE, which follows a FETCH TP4 because the power-on reset leaves the processor halted in FETCH

Writers:
- Mapping ROM output, addressed by IR and the current TS

Consumers:
- EXECUTE selection forming VARIANT, DP_OVL_SEL, and IR_SEQ

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
- CPU datapath (operand use)
- Memory system (write cycles)
- DMA logic

Note: during instruction fetch, IR captures MDB at the same TP as MB, and MB still holds the instruction word.

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
- Loaded from MS_NEXT at a TP only when MS_LOAD = 1; held otherwise, including while halted
- Set to FETCH by the power-on reset
- Not directly influenced by datapath combinational logic
- Initially only 0-4 are valid values 5-7 are reserved

Writers:
- Control state machine (MS_NEXT, enabled by MS_LOAD)

---

### MQ – Multiplier Quotient
Width: 12 bits

Role: Secondary arithmetic register for multiply/divide and extensions

Visibility: Global

Invariants:
- Holds operand or intermediate state during extended arithmetic
- Remains unchanged when not explicitly used; a Group 3 OPR without MQL reloads it unchanged at its FETCH TP3

Constraints:
- Modified only by defined instructions, or by the START console operation while halted
- Must not be altered by general ALU operations

Writers:
- Multiply/divide microcode path
- OPR pass unit MQ output (Group 3 OPR at FETCH TP3: MQL, SWP; OPR_PASS_TO_MQ micro-operation)
- Console START (MQ_CLEAR micro-operation)

---

### PC – Program Counter
Width: 12 bits

Role: Holds the address of the next instruction to be fetched

Visibility: Global

Invariants:
- Forms the instruction fetch address when combined with IF
- Represents the next sequential instruction unless modified by control flow
- Incremented at FETCH TP1. From then on it holds the address of the next sequential instruction
- Always contains a valid address within the current instruction field

Constraints:
- Incremented at FETCH TP1; MA loads the pre-increment PC at the same TP
- After FETCH TP1, modified only by:
  - Conditional skip (increment: Group 2 OPR at FETCH TP4; ISZ and skip IOTs in EXECUTE)
  - Direct JMP (load, FETCH TP3)
  - JMP I (load, DEFER TP4)
  - JMS (EXECUTE: store return address, then load)
- Must not change during DEFER except at the TP4 of a JMP I
- Update must complete before next FETCH TS1

Writers:
- PC + 1 increment path (ALU_RESULT loaded directly when PC_INC = 1; [PC_INC](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#pc_inc))
- Control flow load paths: the EA formation unit (direct JMP); the IDB, from MB (JMP I) or EA_ADDR (JMS)

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
- Set to 0 by the power-on reset ([Timing Terminology §3.4](../09-timing/01-terminology.md#34-power-on-reset))
- Must not be directly modified by datapath logic or μops

Writers:
- Sequencing control (RUN_NEXT)

---

### SKIP – Skip

Width: 1 bit

Role: Holds a Group 2 OPR's skip decision from FETCH TP3, where it is made, to FETCH TP4, where it increments PC.

Visibility: Control-visible

Invariants:
- Meaningful only in FETCH TS4 of the Group 2 OPR that loaded it; its value at any other time has no effect
- Power-on value undefined; it is not read before it is loaded

Constraints:
- Loaded only at the FETCH TP3 of a Group 2 OPR, with `OPR_SKIP_REQ` (`SKIP_LOAD`; OPR_SKIP_REQ_TO_SKIP micro-operation)
- `OPR_SKIP_REQ` is formed from the AC and L held before that TP, so a CLA committed at the same TP does not affect it
- Must not be modified by any other μop

Writers:
- Group 2 skip logic (`OPR_SKIP_REQ`; [Group 2 Execution](../03-microarchitecture/07-opr/02-group2-execution.md))

