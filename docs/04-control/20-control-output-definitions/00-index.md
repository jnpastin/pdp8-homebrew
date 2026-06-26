## Control Output Signal Index

### Purpose

Defines the complete and authoritative index of all control output signals. 

All definitions reside in:

- [Microarchitectural Control Signals](./01-microarchitectural-control-signals.md)  
- [Architectural Control Signals](./02-architectural-control-signals.md)  
- [Sequencing Control Signals](./03-sequencing-control-signals.md)  

---

## Domain Classification

Signals are partitioned into three strictly disjoint domains:

- Microarchitectural (datapath)  
- Architectural (external interface)  
- Sequencing (control flow)  

Each signal appears exactly once in this index.

---

## Microarchitectural Control Signals

Defined in:
- [Microarchitectural Control Signals](./01-microarchitectural-control-signals.md)

---

### Enable Signals

- [AC_LOAD](./01-microarchitectural-control-signals.md#ac_load)  
- [DF_LOAD](./01-microarchitectural-control-signals.md#df_load)  
- [EA_LOAD](./01-microarchitectural-control-signals.md#ea_load)  
- [IB_LOAD](./01-microarchitectural-control-signals.md#ib_load)  
- [IDB_DRIVE](./01-microarchitectural-control-signals.md#idb_drive)  
- [IE_LOAD](./01-microarchitectural-control-signals.md#ie_load)  
- [IF_LOAD](./01-microarchitectural-control-signals.md#if_load)  
- [II_LOAD](./01-microarchitectural-control-signals.md#ii_load)  
- [IR_LOAD](./01-microarchitectural-control-signals.md#ir_load)  
- [L_LOAD](./01-microarchitectural-control-signals.md#l_load)  
- [MA_LOAD](./01-microarchitectural-control-signals.md#ma_load)  
- [MB_LOAD](./01-microarchitectural-control-signals.md#mb_load)  
- [MQ_LOAD](./01-microarchitectural-control-signals.md#mq_load)  
- [PC_INC](./01-microarchitectural-control-signals.md#pc_inc)  
- [PC_LOAD](./01-microarchitectural-control-signals.md#pc_load)  

---

### Select Signals

- [ALU_A_SRC](./01-microarchitectural-control-signals.md#alu_a_src)  
- [ALU_B_SRC](./01-microarchitectural-control-signals.md#alu_b_src)  
- [ALU_OP](./01-microarchitectural-control-signals.md#alu_op)  
- [DF_SRC](./01-microarchitectural-control-signals.md#df_src)  
- [EA_SRC](./01-microarchitectural-control-signals.md#ea_src)  
- [IF_SRC](./01-microarchitectural-control-signals.md#if_src)  
- [IDB_SRC](./01-microarchitectural-control-signals.md#idb_src)  
- [L_OP](./01-microarchitectural-control-signals.md#l_op)  
- [MA_SRC](./01-microarchitectural-control-signals.md#ma_src)  
- [MB_SRC](./01-microarchitectural-control-signals.md#mb_src)  
- [PC_SRC](./01-microarchitectural-control-signals.md#pc_src)  

---

### Data Value Signals

- [CONST_1](./01-microarchitectural-control-signals.md#const_1)  
- [DB_INPUT](./01-microarchitectural-control-signals.md#db_input)  
- [DF_VAL](nals.md#pc_val)  

---

## Architectural Control Signals

Defined in:
- [Architectural Control Signals](./02-architectural-control-signals.md)

---

### Memory Interface

- [RD](./02-architectural-control-signals.md#31-memory-read-rd)  
- [WR](./02-architectural-control-signals.md#32-memory-write-wr)  

---

### I/O Interface

- [IOA[5:0]](./02-architectural-control-signals.md#33-io-address-bus-ioa50)  
- [DB_READ](./02-architectural-control-signals.md#34-db_read)  
- [DB_WRITE](./02-architectural-control-signals.md#db_write)  

---

## Sequencing Control Signals

Defined in:
- [Sequencing Control Signals](./03-sequencing-control-signals.md)

---

### Control Flow

- [MS_next](./03-sequencing-control-signals.md#31-next-major-state-ms_next)  
- [BRANCH_enable](./03-sequencing-control-signals.md#32-branch-enable-branch_enable)  
- [BRANCH_when_true](./03-sequencing-control-signals.md#33-branch-polarity-branch_when_true)  

