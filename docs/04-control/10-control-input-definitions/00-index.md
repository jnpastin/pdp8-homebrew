# Control Input Signal Index

## 1. Purpose

Defines the complete and authoritative index of all control input signals.

All definitions reside in:

- [Primitive Flags](./01-flags.md)
- [IR Derived Fields](./02-ir-derived-fields.md)
- [Derived Flags](./03-derived-flags.md)  
- [External Inputs](./04-external-inputs.md)

---

## 2. Domain Classification

Input signals are grouped into four domains:

- Primitive Flags (register-derived)
- IR-Derived Signals (instruction decode surface)
- Derived Flags (composed control conditions)
- External Inputs (conditions determined outside of the CPU)

Each signal appears exactly once.

---

## 3. Primitive Flags

Defined in:
- [Primitive Flags](./01-flags.md)

- [ACN](./01-flags.md#acn)  
- [ACZ](./01-flags.md#acz)  
- [CIFP](./01-flags.md#cifp)
- [EAI](./01-flags.md#eai)  
- [HLT_REQ](./01-flags.md#hlt_req)
- [IE](./01-flags.md#ie)  
- [II](./01-flags.md#ii)  
- [IOT_READ_PENDING](./01-flags.md#iot_read_pending)
- [IOT_WRITE_PENDING](./01-flags.md#iot_write_pending)
- [LZ](./01-flags.md#lz)  
- [MBZ](./01-flags.md#mbz)  
- [RUN](./01-flags.md#run)

---

## 4. IR-Derived Signals

Defined in:
- [IR Derived Fields](./02-ir-derived-fields.md)

---

### 4.1 IR Class Flags

- [IR_IS_IOT](./02-ir-derived-fields.md#ir_is_iot)  
- [IR_IS_MRI](./02-ir-derived-fields.md#ir_is_mri)  
- [IR_IS_OPR](./02-ir-derived-fields.md#ir_is_opr)  

---

### 4.2 Instruction Detection

- [IR_IS_ISZ](./02-ir-derived-fields.md#ir_is_isz)  

---

### 4.3 Addressing Mode

- [IR_INDIRECT](./02-ir-derived-fields.md#ir_indirect)  
- [IR_ZERO_PAGE](./02-ir-derived-fields.md#ir_zero_page)  

---

### 4.4 OPR Class

- [IR_OPR_GROUP1](./02-ir-derived-fields.md#ir_opr_group1)  
- [IR_OPR_GROUP2](./02-ir-derived-fields.md#ir_opr_group2)  
- [IR_OPR_GROUP3](./02-ir-derived-fields.md#ir_opr_group3)  

---

### 4.5 OPR Bit Flags

- [IR_OPR_BSW](./02-ir-derived-fields.md#ir_opr_bsw)  
- [IR_OPR_CLA](./02-ir-derived-fields.md#ir_opr_cla)  
- [IR_OPR_CLL](./02-ir-derived-fields.md#ir_opr_cll)  
- [IR_OPR_CMA](./02-ir-derived-fields.md#ir_opr_cma)  
- [IR_OPR_CML](./02-ir-derived-fields.md#ir_opr_cml)  
- [IR_OPR_HLT](./02-ir-derived-fields.md#ir_opr_hlt)  
- [IR_OPR_IAC](./02-ir-derived-fields.md#ir_opr_iac)  
- [IR_OPR_OSR](./02-ir-derived-fields.md#ir_opr_osr)  
- [IR_OPR_RAL](./02-ir-derived-fields.md#ir_opr_ral)  
- [IR_OPR_RAR](./02-ir-derived-fields.md#ir_opr_rar)  
- [IR_OPR_SKIP_MODE](./02-ir-derived-fields.md#ir_opr_skip_mode)  
- [IR_OPR_SMA](./02-ir-derived-fields.md#ir_opr_sma)  
- [IR_OPR_SNL](./02-ir-derived-fields.md#ir_opr_snl)  
- [IR_OPR_SZA](./02-ir-derived-fields.md#ir_opr_sza)  

---

### 4.6 Memory Management Flags

- [IR_READS_DF](./02-ir-derived-fields.md#ir_reads_df)  
- [IR_READS_IB](./02-ir-derived-fields.md#ir_reads_ib)  
- [IR_READS_IF](./02-ir-derived-fields.md#ir_reads_if)  
- [IR_RESTORES_IB](./02-ir-derived-fields.md#ir_restores_ib)  
- [IR_WRITES_DF](./02-ir-derived-fields.md#ir_writes_df)  
- [IR_WRITES_IF](./02-ir-derived-fields.md#ir_writes_if)  

---

### 4.7 Field Extraction Signals

- [IR_ADDR](./02-ir-derived-fields.md#ir_addr)  
- [IR_DF](./02-ir-derived-fields.md#ir_df)  
- [IR_IOA](./02-ir-derived-fields.md#ir_ioa)  
- [IR_IF](./02-ir-derived-fields.md#ir_if)  

---

## 5. Derived Flags

Defined in: [Derived Flags](./03-derived-flags.md)

- [AUTO_INDEX_REQUIRED](./03-derived-flags.md#auto_index_required)  
- [IF_CHANGE_PENDING](./03-derived-flags.md#if_change_pending)
- [INTERRUPT_REQUEST_VALID](./03-derived-flags.md#interrupt_request_valid)  
- [ISZ_SKIP_REQUIRED](./03-derived-flags.md#isz_skip_required)  
- [SKIP_TAKEN](./03-derived-flags.md#skip_taken)  

---

## 6. External Inputs

Defined in: [External Inputs](./04-external-inputs.md)

### 6.1 Front Panel Commands
- [FP_START](./04-external-inputs.md#fp_start)
- [FP_CONTINUE](./04-external-inputs.md#fp_continue)
- [FP_STOP](./04-external-inputs.md#fp_stop)
- [FP_LOAD_ADDRESS](./04-external-inputs.md#fp_load_address)
- [FP_EXAMINE](./04-external-inputs.md#fp_examine)
- [FP_DEPOSIT](./04-external-inputs.md#fp_deposit)

### 6.2 Front Panel Modes
- [FP_SINGLE_INSTRUCTION](./04-external-inputs.md#fp_single_instruction)
- [FP_SINGLE_STEP](./04-external-inputs.md#fp_single_step)

### 6.3 Front Panel Data
- [FP_IF](./04-external-inputs.md#fp_if)
- [FP_DF](./04-external-inputs.md#fp_df)

### 6.4 External Requests
- [/INT_REQ](./04-external-inputs.md#int_req)
- [/DMA_REQ](./04-external-inputs.md#dma_req)

### 6.5 External IOT Response Inputs

- [I/O_READ_REQ](./04-external-inputs.md#io_read_req)
- [I/O_WRITE_REQ](./04-external-inputs.md#io_write_req)
- [I/O_SKIP_REQ](./04-external-inputs.md#io_skip_req)
- [I/O_CLEAR_AC_REQ](./04-external-inputs.md#io_clear_ac_req)
- [/I/O_WAIT](./04-external-inputs.md#io_wait)
