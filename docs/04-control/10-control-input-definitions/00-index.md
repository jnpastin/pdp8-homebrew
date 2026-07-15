## Control Input Signal Index

### Purpose

Defines the complete and authoritative index of all control input signals.

All definitions reside in:

- [Primitive Flags](./01-flags.md)
- [IR Derived Fields](./02-ir-derived-fields.md)
- [Derived Flags](./03-derived-flags.md)  

---

## Domain Classification

Input signals are grouped into three domains:

- Primitive Flags (register-derived)
- IR-Derived Signals (instruction decode surface)
- Derived Flags (composed control conditions)

Each signal appears exactly once.

---

## Primitive Flags

Defined in:
- [Primitive Flags](./01-flags.md)

- [ACN](./01-flags.md#acn)  
- [ACZ](./01-flags.md#acz)  
- [EAI](./01-flags.md#eai)  
- [IE](./01-flags.md#ie)  
- [II](./01-flags.md#ii)  
- [IP](./01-flags.md#ip)  
- [LZ](./01-flags.md#lz)  
- [MBZ](./01-flags.md#mbz)  

---

## IR-Derived Signals

Defined in:
- [IR Derived Fields](./02-ir-derived-fields.md)

---

### IR Class Flags

- [IR_IS_IOT](./02-ir-derived-fields.md#ir_is_iot)  
- [IR_IS_MRI](./02-ir-derived-fields.md#ir_is_mri)  
- [IR_IS_OPR](./02-ir-derived-fields.md#ir_is_opr)  

---

### Instruction Detection

- [IR_IS_ISZ](./02-ir-derived-fields.md#ir_is_isz)  

---

### Addressing Mode

- [IR_INDIRECT](./02-ir-derived-fields.md#ir_indirect)  
- [IR_ZERO_PAGE](./02-ir-derived-fields.md#ir_zero_page)  

---

### OPR Class

- [IR_OPR_GROUP1](./02-ir-derived-fields.md#ir_opr_group1)  
- [IR_OPR_GROUP2](./02-ir-derived-fields.md#ir_opr_group2)  
- [IR_OPR_GROUP3](./02-ir-derived-fields.md#ir_opr_group3)  

---

### OPR Bit Flags

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

### Memory Management Flags

- [IR_READS_DF](./02-ir-derived-fields.md#ir_reads_df)  
- [IR_READS_IF](./02-ir-derived-fields.md#ir_reads_if)  
- [IR_RESTORES_IB](./02-ir-derived-fields.md#ir_restores_ib)  
- [IR_WRITES_IB](./02-ir-derived-fields.md#ir_writes_ib)  
- [IR_WRITES_DF](./02-ir-derived-fields.md#ir_writes_df)  
- [IR_WRITES_IF](./02-ir-derived-fields.md#ir_writes_if)  

---

### Field Extraction Signals

- [IR_ADDR](./02-ir-derived-fields.md#ir_addr)  
- [IR_DF](./02-ir-derived-fields.md#ir_df)  
- [IR_IOA](./02-ir-derived-fields.md#ir_ioa)  
- [IR_IF](./02-ir-derived-fields.md#ir_if)  

---

## Derived Flags

Defined in: [Derived Flags](./03-derived-flags.md)

- [SKIP_TAKEN](./03-derived-flags.md#skip_taken)  
- [ISZ_SKIP_REQUIRED](./03-derived-flags.md#isz_skip_required)  
- [AUTO_INDEX_REQUIRED](./03-derived-flags.md#auto_index_required)  
- [INTERRUPT_REQUEST_VALID](./03-derived-flags.md#interrupt_request_valid)  

