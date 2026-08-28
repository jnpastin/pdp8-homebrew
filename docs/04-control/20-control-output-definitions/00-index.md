# Control Output Signal Index

## 1. Purpose

Defines the complete and authoritative index of all control output signals. 

All definitions reside in:

- [Microarchitectural Control Signals](./01-microarchitectural-control-signals.md)  
- [Architectural Control Signals](./02-architectural-control-signals.md)  
- [Sequencing Control Signals](./03-sequencing-control-signals.md)  

---

## 2. Domain Classification

Signals are partitioned into three strictly disjoint domains:

- Microarchitectural (datapath)  
- Architectural (external interface)  
- Sequencing (control flow)  

Each signal appears exactly once in this index.

---

## 3. Microarchitectural Control Signals

Defined in:
- [Microarchitectural Control Signals](./01-microarchitectural-control-signals.md)

---

### 3.1 Enable Signals

- [AC_LOAD](./01-microarchitectural-control-signals.md#ac_load)  
- [CIFP_LOAD](./01-microarchitectural-control-signals.md#cifp_load)  
- [DF_LOAD](./01-microarchitectural-control-signals.md#df_load)  
- [DIF_LOAD](./01-microarchitectural-control-signals.md#dif_load)  
- [EA_ADDR_LOAD](./01-microarchitectural-control-signals.md#ea_addr_load)  
- [IB_LOAD](./01-microarchitectural-control-signals.md#ib_load)  
- [IDB_DRIVE](./01-microarchitectural-control-signals.md#idb_drive)  
- [IE_LOAD](./01-microarchitectural-control-signals.md#ie_load)  
- [IF_LOAD](./01-microarchitectural-control-signals.md#if_load)  
- [II_LOAD](./01-microarchitectural-control-signals.md#ii_load)
- [IOT_TRANSFER_LOAD](./01-microarchitectural-control-signals.md#iot_transfer_load)  
- [IR_LOAD](./01-microarchitectural-control-signals.md#ir_load)  
- [L_LOAD](./01-microarchitectural-control-signals.md#l_load)  
- [MA_LOAD](./01-microarchitectural-control-signals.md#ma_load)  
- [MB_LOAD](./01-microarchitectural-control-signals.md#mb_load)  
- [MQ_LOAD](./01-microarchitectural-control-signals.md#mq_load)  
- [PC_INC](./01-microarchitectural-control-signals.md#pc_inc)  
- [PC_LOAD](./01-microarchitectural-control-signals.md#pc_load)  

---

### 3.2 Select Signals

- [AB_SRC](./01-microarchitectural-control-signals.md#ab_src)  
- [AC_SRC](./01-microarchitectural-control-signals.md#ac_src)  
- [ALU_A_SRC](./01-microarchitectural-control-signals.md#alu_a_src)  
- [ALU_B_SRC](./01-microarchitectural-control-signals.md#alu_b_src)  
- [ALU_OP](./01-microarchitectural-control-signals.md#alu_op)  
- [DF_SRC](./01-microarchitectural-control-signals.md#df_src)  
- [DIF_SRC](./01-microarchitectural-control-signals.md#dif_src)  
- [EA_ADDR_SRC](./01-microarchitectural-control-signals.md#ea_addr_src)  
- [IF_SRC](./01-microarchitectural-control-signals.md#if_src)  
- [IDB_SRC](./01-microarchitectural-control-signals.md#idb_src)  
- [L_OP](./01-microarchitectural-control-signals.md#l_op)  
- [MA_SRC](./01-microarchitectural-control-signals.md#ma_src)  
- [MB_SRC](./01-microarchitectural-control-signals.md#mb_src)  
- [MDB_SRC](./01-microarchitectural-control-signals.md#mdb_src)  
- [MFB_SRC](./01-microarchitectural-control-signals.md#mfb_src)  
- [PC_SRC](./01-microarchitectural-control-signals.md#pc_src)  

---

### 3.3 Data Value Signals

- [CIFP_VAL](./01-microarchitectural-control-signals.md#cifp_val)  
- [DB_INPUT](./01-microarchitectural-control-signals.md#db_input)  
- [DF_VAL](./01-microarchitectural-control-signals.md#df_val)  
- [IE_VAL](./01-microarchitectural-control-signals.md#ie_val)  
- [IF_DF_COMBINED](./01-microarchitectural-control-signals.md#if_df_combined)  
- [IF_VAL](./01-microarchitectural-control-signals.md#if_val)  
- [II_VAL](./01-microarchitectural-control-signals.md#ii_val)  
- [IOT_TRANSFER_VAL](./01-microarchitectural-control-signals.md#iot_transfer_val)
- [MA_VAL](./01-microarchitectural-control-signals.md#ma_val)  
- [MDB_INPUT](./01-microarchitectural-control-signals.md#mdb_input)  
- [PC_VAL](./01-microarchitectural-control-signals.md#pc_val)  


---

## 4. Architectural Control Signals

Defined in:
- [Architectural Control Signals](./02-architectural-control-signals.md)

---

### 4.1 Memory Interface

- [/RD](./02-architectural-control-signals.md#31-memory-read-rd)  
- [/WR](./02-architectural-control-signals.md#32-memory-write-wr)  
- [/DMA_GRANT](./02-architectural-control-signals.md#35-dma_grant)  

---

### 4.2 I/O Interface

- [/DB_READ](./02-architectural-control-signals.md#33-db_read)  
- [/DB_WRITE](./02-architectural-control-signals.md#34-db_write)  
- [IOA[5:0]](./02-architectural-control-signals.md#36-io-address-bus-ioa50)  
- [IOP[2:0]](./02-architectural-control-signals.md#37-io-operation-field-iop20)
- [IOT_ACTIVE](./02-architectural-control-signals.md#38-external-iot-active-iot_active)

---

## 5. Sequencing Control Signals

Defined in:
- [Sequencing Control Signals](./03-sequencing-control-signals.md)

---

### 5.1 Control Flow

- [MS_NEXT](./03-sequencing-control-signals.md#31-next-major-state-ms_next)  
- [RUN_NEXT](./03-sequencing-control-signals.md#32-run-state-next-value-run_next)  
- [HLT_REQ_NEXT](./03-sequencing-control-signals.md#33-halt-request-next-value-hlt_req_next)  

