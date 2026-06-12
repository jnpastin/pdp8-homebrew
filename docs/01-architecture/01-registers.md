
## Register Model Specification

### Purpose
Defines all system state.

All stable values in the system must reside in registers.

---

### Architectural Registers
- AC: [Accumulator](#AC--Accumulator)
- DF: [Data Field](#DF--Data-Field)
- IE: [Interrupt Enable](#IE--Interrupt-Enable)
- IF: [Instruction Field](#IF--Instruction-Field)
- L:  [Link](#L--Link)
- MQ: [Multiplier Quotient](#MQ--Multiplier-Quotient)
- PC: [Program Counter](#PC--Program-Counter)
- SR: [Switch Register](#SR--Switch-Register)


---

### Control-Visible State
- IR: [Instruction Register](#IR--Instruction-Register)
- MS: [Major State](#MS--Major-State)
- II: [Interrupt Inhibit](#II--Interrupt-Inhibit)

---

### Internal Registers
- EA: [Effective Address](#EA--Effective-Address)
- MA: [Memory Address](#MA--Memory-Address)
- MB: [Memory Buffer](#MB--Memory-Buffer)

---

## Register Definitions

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
- MQ transfer path (if implemented)

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

### EA – Effective Address
Width: 12 bits

Role:
Holds the 12-bit address portion of the effective address.

The full logical effective address is represented as:

    EA_logical = (EA_fld, EA_addr)

Where:
- EA_addr is stored in EA
- EA_fld is provided by IF or DF

No register stores the combined value.

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

### IE – Interrupt Enable
Width: 1 bit

Role: Global interrupt gating flag

Visibility: Global

Invariants:
- Determines whether interrupts are recognized
- Stable during instruction execution
- EA must never directly drive memory; it must first be transferred to MA

Constraints:
- Modified only by ION/IOF instructions
- Effective change occurs only after EXECUTE completes

Writers:
- Interrupt control logic

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
- Set only by ION instruction  
- Cleared only during FETCH
- Must not be directly modified by control logic  

Writers:  
- IOT execution (ION)  
- FETCH execution (II_CLEAR μop)

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
  - Data break (DMA) transfer is in progress using MB
- Cannot be bypassed for architecturally visible memory transfers

Writers:
- Memory data return path
- CPU internal bus (store operations)

Consumers:
- CPU datapath (instruction load, operand use)
- Memory system (write cycles)
- Data break / DMA logic

---

### MS – Major State
Width: 3 bits

Role: Encodes processor phase (FETCH, DEFER, EXECUTE, INTERRUPT)

Visibility: Control

Invariants:
- Exactly one state active at a time
- Transitions follow defined state machine

Constraints:
- Changes only at cycle boundaries
- Not directly influenced by datapath combinational logic
- Initially only 0-3 are valid values 4-7 are reserved

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
- AC transfer path (if present)

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

### SR – Switch Register
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
