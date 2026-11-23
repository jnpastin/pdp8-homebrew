# Abbreviation Dictionary

## 1. Purpose

This document defines a global dictionary for all abbreviations used throughout the system design.

It serves as the single source of truth for:
- register names
- bus names
- control signals
- timing signals
- architectural and microarchitectural terms

All documents must reference these abbreviations to prevent ambiguity or collision.

---

## 2. Naming Rules

- Abbreviations should be short where possible; names of fields and derived inputs may be longer, with words joined by underscores
- Must be unique across all categories
- Must be stable once defined
- Must not be reused with different meanings

---

## 3. Buses (Class A)


AB   = [Address Bus](../05-buses-and-signals/01-class-a-buses.md#41-address-bus-ab) (AB[11:0])

DB   = [System Data Bus](../05-buses-and-signals/01-class-a-buses.md#42-system-data-bus-db) (DB[11:0])

MDB  = [Memory Data Bus](../05-buses-and-signals/01-class-a-buses.md#43-memory-data-bus-mdb) (MDB[11:0])

MFB  = [Memory Field Bus](../05-buses-and-signals/01-class-a-buses.md#44-mfb--memory-field-bus) (MFB[2:0])

---

## 4. Registers


AC   = [Accumulator](../01-architecture/01-registers.md#ac--accumulator)

CIFP = [Change Instruction Field Pending](../01-architecture/01-registers.md#cifp--change-instruction-field-pending)

DF   = [Data Field](../01-architecture/01-registers.md#df--data-field)

DIF  = [Deferred Instruction Field](../01-architecture/01-registers.md#dif--deferred-instruction-field)

EA_ADDR   = [Effective Address (Address Portion)](../01-architecture/01-registers.md#ea_addr--effective-address-address-portion)

FP_SR   = [Switch Register](../01-architecture/01-registers.md#fp_sr--switch-register)

HLT_REQ   = [Halt Request](../01-architecture/01-registers.md#hlt_req--halt-request)

IOT_TRANSFER = [Pending External-IOT Transfer](../01-architecture/01-registers.md#iot_transfer---pending-external-iot-transfer)

IB   = [Interrupt Buffer](../01-architecture/01-registers.md#ib--interrupt-buffer)

IE   = [Interrupt Enable](../01-architecture/01-registers.md#ie--interrupt-enable)

IF   = [Instruction Field](../01-architecture/01-registers.md#if--instruction-field)

II   = [Interrupt Inhibit](../01-architecture/01-registers.md#ii--interrupt-inhibit)

IR   = [Instruction Register](../01-architecture/01-registers.md#ir--instruction-register)

L    = [Link](../01-architecture/01-registers.md#l--link)

MA   = [Memory Address](../01-architecture/01-registers.md#ma--memory-address)

MAPR = [Mapping Register](../01-architecture/01-registers.md#mapr--mapping-register)

MB   = [Memory Buffer](../01-architecture/01-registers.md#mb--memory-buffer)

MS   = [Major State](../01-architecture/01-registers.md#ms--major-state)

MQ   = [Multiplier Quotient](../01-architecture/01-registers.md#mq--multiplier-quotient)

PC   = [Program Counter](../01-architecture/01-registers.md#pc--program-counter)

RUN  = [Run state](../01-architecture/01-registers.md#run--run-state)

SKIP = [Skip](../01-architecture/01-registers.md#skip--skip)


---

## 5. Global Control Signals (Class B)


/DMA_REQ = [DMA Request](../04-control/10-control-input-definitions/04-external-inputs.md#dma_req)

/DMA_GRANT = [DMA Grant](../04-control/20-control-output-definitions/02-architectural-control-signals.md#45-dma_grant)

/INITIALIZE = [System Initialization](../04-control/20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

/INT_REQ = [Interrupt Request](../04-control/10-control-input-definitions/04-external-inputs.md#int_req)

/RD      = [Memory Read](../04-control/20-control-output-definitions/02-architectural-control-signals.md#41-memory-read-rd)

/WR      = [Memory Write](../04-control/20-control-output-definitions/02-architectural-control-signals.md#42-memory-write-wr)



---

## 6. Control-Store Signals


DP_OVL[4:0] = [Datapath Overlay](../04-control/08-control-store-organization.md#6-datapath-overlay)

DP_OVL_SEL[1:0] = [Datapath Overlay Select](../04-control/08-control-store-organization.md#542-execute-selection)

FP_CMD[2:0] = [Front-Panel Command Code](../04-control/08-control-store-organization.md#52-front-panel-command-code)

INSTR_END = [Instruction End](../04-control/20-control-output-definitions/02-architectural-control-signals.md#410-instruction-end-instr_end)

IR_CLASS[2:0] = [Instruction Class](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_class)

IR_NO_EXECUTE = [Instruction Never Enters EXECUTE](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_no_execute)

IR_SEQ = [Sequencer Instruction Decode](../04-control/08-control-store-organization.md#542-execute-selection)

MS_EFF[2:0] = [Effective Major State](../04-control/08-control-store-organization.md#51-major-state-and-timing-state-codes)

MS_EFF_IS_EXECUTE = [Effective Major State Is EXECUTE](../04-control/08-control-store-organization.md#51-major-state-and-timing-state-codes)

OPR_PASS = [OPR Pass Unit Load](../03-microarchitecture/02-micro-operations.md#opr_pass)

SEQ_OVL[2:0] = [Sequencer Overlay](../04-control/08-control-store-organization.md#56-sequencer-slice-address)

TS_CODE[1:0] = [Timing-State Code](../04-control/08-control-store-organization.md#51-major-state-and-timing-state-codes)

VARIANT[4:0] = [Execution Variant](../04-control/08-control-store-organization.md#542-execute-selection)


---

## 7. Timing Signals (Class C)


MCLK  = [Master Clock](../09-timing/01-terminology.md#21-master-clock-mclk)

TCLK  = [Timing Clock](../09-timing/01-terminology.md#22-timing-clock-tclk)

TSTEP = [Timing Step](../09-timing/01-terminology.md#31-timing-step-tstep)

TSEQ  = [Timing Sequence](../09-timing/01-terminology.md#32-timing-sequence-tseq)

TPn   = [Timing Pulse n](../09-timing/01-terminology.md#4-timing-pulses-tp)

TSn   = [Timing State n](../09-timing/01-terminology.md#5-timing-states-ts)

T_CS  = [Control-Store Settle Time](../09-timing/01-terminology.md#55-control-store-settle-time-t_cs)

CW_VALID = [Control Word Valid](../09-timing/01-terminology.md#56-control-word-valid-cw_valid)

/WR_PULSE = [Write Pulse](../09-timing/01-terminology.md#57-write-pulse-wr_pulse)

DB_VALID  = [DB Transfer Window](../09-timing/01-terminology.md#58-db-transfer-window-db_valid)

TP    = [Timing Pulse: the one commit clock](../09-timing/01-terminology.md#44-generation)

r1, r2   = [Capture rank and output rank of a register](../09-timing/02-timing-architecture.md#76-rule-6--two-ranks)


---

## 8. I/O Signals


IOA[5:0] = [I/O Device Address Bus](../04-control/20-control-output-definitions/02-architectural-control-signals.md#46-io-address-bus-ioa50)

IOP[2:0] = [I/O Operation Field](../04-control/20-control-output-definitions/02-architectural-control-signals.md#47-io-operation-field-iop20)

IOT_ACTIVE = [External IOT Active](../04-control/20-control-output-definitions/02-architectural-control-signals.md#48-external-iot-active-iot_active)


---

## 9. Front Panel Signals (Class D)
  
FP_START     = [Start Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_start)
 
FP_CLEAR = [Clear Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_clear)

FP_CONTINUE  = [Continue Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_continue)

FP_STOP      = [Stop Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_stop)

FP_LOAD_ADDRESS = [Load Address Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_load_address)

FP_EXAMINE   = [Examine Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_examine)

FP_DEPOSIT   = [Deposit Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_deposit)

FP_SINGLE_INSTRUCTION = [Single Instruction Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_single_instruction)

FP_SINGLE_STEP = [Single Step Switch](../04-control/10-control-input-definitions/04-external-inputs.md#fp_single_step)

FP_IF        = [Instruction Field Switches](../04-control/10-control-input-definitions/04-external-inputs.md#fp_if)

FP_DF        = [Data Field Switches](../04-control/10-control-input-definitions/04-external-inputs.md#fp_df)

---

## 10. Control Inputs

Inputs to the control function that are not listed above.

ACN                     = [AC_IS_NEGATIVE](../04-control/10-control-input-definitions/01-flags.md#acn)

ACZ                     = [AC_IS_ZERO](../04-control/10-control-input-definitions/01-flags.md#acz)

AUTO_INDEX_REQUIRED     = [Auto Index Required](../04-control/10-control-input-definitions/03-derived-flags.md#auto_index_required)

EAI                     = [EA_IS_AUTOINDEX](../04-control/10-control-input-definitions/01-flags.md#eai)

IF_CHANGE_PENDING       = [Instruction Field Change Pending](../04-control/10-control-input-definitions/03-derived-flags.md#if_change_pending)

INTERRUPT_REQUEST_VALID = [Interrupt Request Valid](../04-control/10-control-input-definitions/03-derived-flags.md#interrupt_request_valid)

IOT_READ_PENDING        = [IOT Read Transfer Pending](../04-control/10-control-input-definitions/01-flags.md#iot_read_pending)

IOT_WRITE_PENDING       = [IOT Write Transfer Pending](../04-control/10-control-input-definitions/01-flags.md#iot_write_pending)

IO_CLEAR_AC_REQ         = [I/O Clear AC Request](../04-control/10-control-input-definitions/04-external-inputs.md#io_clear_ac_req)

IO_READ_REQ             = [I/O Read Request](../04-control/10-control-input-definitions/04-external-inputs.md#io_read_req)

IO_SKIP_REQ             = [I/O Skip Request](../04-control/10-control-input-definitions/04-external-inputs.md#io_skip_req)

IO_WRITE_REQ            = [I/O Write Request](../04-control/10-control-input-definitions/04-external-inputs.md#io_write_req)

IR_ADDR                 = [Memory Address Field](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_addr)

IR_DF                   = [Data Field](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_df)

IR_IF                   = [Instruction Field](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_if)

IR_INDIRECT             = [Indirect Addressing Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_indirect)

IR_IOA                  = [I/O Address Field](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_ioa)

IR_IOT_OP               = [IOT Operation Field](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_iot_op)

IR_IS_CAF               = [Clear All Flags Instruction Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_caf)

IR_IS_EXTERNAL_IOT      = [External-Device IOT Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_external_iot)

IR_IS_GTF               = [Get Flags Instruction Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_gtf)

IR_IS_IOT               = [IOT Instruction Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_iot)

IR_IS_MEMEXT_IOT        = [Memory Extension IOT Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_memext_iot)

IR_IS_MRI               = [Memory Reference Instruction Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_mri)

IR_IS_OPR               = [Operate Instruction Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_opr)

IR_IS_RTF               = [Restore Flags Instruction Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_is_rtf)

IR_MRI_OPCODE           = [Memory Reference Instruction Opcode](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_mri_opcode)

IR_OPR_BSW              = [Byte Swap / Rotate Modifier](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_bsw)

IR_OPR_CLA              = [Clear Accumulator](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_cla)

IR_OPR_CLL              = [Clear Link](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_cll)

IR_OPR_CMA              = [Complement Accumulator](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_cma)

IR_OPR_CML              = [Complement Link](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_cml)

IR_OPR_GROUP1           = [OPR Group 1 Selection](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_group1)

IR_OPR_GROUP2           = [OPR Group 2 Selection](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_group2)

IR_OPR_GROUP3           = [OPR Group 3 Selection](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_group3)

IR_OPR_HLT              = [Halt](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_hlt)

IR_OPR_IAC              = [Increment Accumulator](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_iac)

IR_OPR_MQA              = [MQ OR into AC](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_mqa)

IR_OPR_MQL              = [AC load to MQ](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_mql)

IR_OPR_OSR              = [OR Switch Register](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_osr)

IR_OPR_RAL              = [Rotate Accumulator Left Enable](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_ral)

IR_OPR_RAR              = [Rotate Accumulator Right Enable](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_rar)

IR_OPR_SKIP_MODE        = [Skip Mode Select](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_skip_mode)

IR_OPR_SMA              = [Skip on AC Negative](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_sma)

IR_OPR_SNL              = [Skip on Link Non-Zero](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_snl)

IR_OPR_SZA              = [Skip on AC Zero](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_opr_sza)

IR_READS_DF             = [Data Field Read Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_reads_df)

IR_READS_IB             = [Interrupt Buffer Read Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_reads_ib)

IR_READS_IF             = [Instruction Field Read Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_reads_if)

IR_RESTORES_IB          = [Restore Memory Field From IB Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_restores_ib)

IR_WRITES_DF            = [Data Field Change Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_writes_df)

IR_WRITES_IF            = [Instruction Field Change Flag](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_writes_if)

IR_ZERO_PAGE            = [Zero Page Select](../04-control/10-control-input-definitions/02-ir-derived-fields.md#ir_zero_page)

ISZ_SKIP_REQ            = [Increment Skip if Zero - Skip Request](../04-control/10-control-input-definitions/03-derived-flags.md#isz_skip_req)

LZ                      = [L_IS_ZERO](../04-control/10-control-input-definitions/01-flags.md#lz)

MBZ                     = [MB_IS_ZERO](../04-control/10-control-input-definitions/01-flags.md#mbz)

OPR_SKIP_REQ            = [OPR Skip Request](../04-control/10-control-input-definitions/03-derived-flags.md#opr_skip_req)

---

## 11. Control-Word Fields

Fields of the control word that are not listed above.

AB_SRC            = [Address Bus Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ab_src)

AC_LOAD           = [Accumulator Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ac_load)

AC_SRC            = [Accumulator Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ac_src)

ALU_A_SRC         = [ALU Input A Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#alu_a_src)

ALU_B_SRC         = [ALU Input B Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#alu_b_src)

ALU_OP            = [ALU Operation](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#alu_op)

CIFP_LOAD         = [CIF Pending Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#cifp_load)

CIFP_VAL          = [CIF Pending Value](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#cifp_val)

DB_INPUT          = [External I/O Data Input](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#db_input)

/DB_READ          = [DB Read](../04-control/20-control-output-definitions/02-architectural-control-signals.md#43-db_read)

/DB_WRITE         = [DB Write](../04-control/20-control-output-definitions/02-architectural-control-signals.md#44-db_write)

DF_LOAD           = [Data Field Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#df_load)

DF_SRC            = [DF Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#df_src)

DIF_LOAD          = [Deferred Instruction Field Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#dif_load)

DIF_SRC           = [DIF Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#dif_src)

EA_ADDR_LOAD      = [Effective Address Load (Address Portion)](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ea_addr_load)

EA_ADDR_SRC       = [EA_ADDR Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ea_addr_src)

GTF_FLAGS         = [Processor Flags Word](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#gtf_flags)

HLT_REQ_NEXT      = [Halt Request Next Value](../04-control/20-control-output-definitions/03-sequencing-control-signals.md#43-halt-request-next-value-hlt_req_next)

IB_LOAD           = [Interrupt Buffer Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ib_load)

IDB_DRIVE         = [Internal Data Bus Drive Enable](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#idb_drive)

IDB_SRC           = [Internal Data Bus Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#idb_src)

IE_LOAD           = [Interrupt Enable Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ie_load)

IE_VAL            = [Interrupt Enable Value](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ie_val)

IF_DF_COMBINED    = [IF/DF Combination](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#if_df_combined)

IF_LOAD           = [Instruction Field Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#if_load)

IF_SRC            = [IF Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#if_src)

II_LOAD           = [Interrupt Inhibit Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ii_load)

II_VAL            = [Interrupt Inhibit Value](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ii_val)

IOT_TRANSFER_LOAD = [Pending External-IOT Transfer Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#iot_transfer_load)

IOT_TRANSFER_VAL  = [Pending External-IOT Transfer Value](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#iot_transfer_val)

IR_LOAD           = [Instruction Register Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ir_load)

L_LOAD            = [Link Register Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#l_load)

L_OP              = [Link Operation](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#l_op)

MA_LOAD           = [Memory Address Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ma_load)

MA_SRC            = [MA Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#ma_src)

MB_LOAD           = [Memory Buffer Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#mb_load)

MB_SRC            = [MB Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#mb_src)

MDB_INPUT         = [Memory Data Bus Input](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#mdb_input)

MDB_SRC           = [Memory Data Bus Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#mdb_src)

MFB_SRC           = [Memory Field Bus Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#mfb_src)

MQ_LOAD           = [Multiplier Quotient Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#mq_load)

MQ_SRC            = [MQ Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#mq_src)

MS_LOAD           = [Major State Load](../04-control/20-control-output-definitions/03-sequencing-control-signals.md#44-major-state-load-ms_load)

MS_NEXT           = [Next Major State](../04-control/20-control-output-definitions/03-sequencing-control-signals.md#41-next-major-state-ms_next)

PC_INC            = [Program Counter Increment](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#pc_inc)

PC_LOAD           = [Program Counter Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#pc_load)

PC_SRC            = [Program Counter Source Select](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#pc_src)

RUN_NEXT          = [Run State Next Value](../04-control/20-control-output-definitions/03-sequencing-control-signals.md#42-run-state-next-value-run_next)

SKIP_LOAD         = [Skip Register Load](../04-control/20-control-output-definitions/01-microarchitectural-control-signals.md#skip_load)

---

## 12. Conventions

- Bracket notation indicates bus width (e.g., AB[11:0])
- Uppercase denotes signal-level identifiers
- Names reflect function, not implementation

---

## 13. Constraints

- New abbreviations must be added here before use
- Existing abbreviations must not be redefined
- Collisions must be resolved by renaming before implementation

---

## 14. Summary

This dictionary ensures consistency across:
- architecture definitions
- control logic
- hardware implementation
- documentation

It is authoritative and must be kept synchronized with all system specifications.
