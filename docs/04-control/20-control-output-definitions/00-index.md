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
- [MEM_OP_SRC](./01-microarchitectural-control-signals.md#mem_op_src)  
- [MEM_WR_SRC](./01-microarchitectural-control-signals.md#mem_wr_src)  
- [PC_SRC](./01-microarchitectural-control-signals.md#pc_src)  

---

### Data Value Signals

- [DB_INPUT](./01-microarchitectural-control-signals.md#db_input)  
- [DF_VAL](./01-microarchitectural-control-signals.md#df_val)  
- [IE_VAL](./01-microarchitectural-control-signals.md#ie_val)  
- [IF_DF_COMBINED](./01-microarchitectural-control-signals.md#if_df_combined)  
- [IF_VAL](./01-microarchitectural-control-signals.md#if_val)  
- [II_VAL](./01-microarchitectural-control-signals.md#ii_val)  
- [MA_VAL](./01-microarchitectural-control-signals.md#ma_val)  
- [MDB_INPUT](./01-microarchitectural-control-signals.md#mdb_input)  
- [PC_VAL](./01-microarchitectural-control-signals.md#pc_val)  


---

## Architectural Control Signals

Defined in:
- [Architectural Control Signals](./02-architectural-control-signals.md)

---

### Memory Interface

- [RD](./02-architectural-control-signals.md#31-memory-read-rd)  
- [WR](./02-architectural-control-signals.md#32-memory-write-wr)  
- [DMA_GRANT](./02-architectural-control-signals.md#35-dma_grant)  

---

### I/O Interface

- [DB_READ](./02-architectural-control-signals.md#33-db_read)  
- [DB_WRITE](./02-architectural-control-signals.md#34-db_write)  
- [IOA[5:0]](./02-architectural-control-signals.md#36-io-address-bus-ioa50)  

---

## Sequencing Control Signals

Defined in:
- [Sequencing Control Signals](./03-sequencing-control-signals.md)

---

### Control Flow

- [MS_NEXT](./03-sequencing-control-signals.md#31-next-major-state-ms_next)  
- [RUN_NEXT](./03-sequencing-control-signals.md#32-run-state-next-value-run_next)  
- [HLT_REQ_NEXT](./03-sequencing-control-signals.md#33-halt-request-next-value-hlt_req_next)  

