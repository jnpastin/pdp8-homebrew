# Control Output Signal Index

This document organizes all control output signals into their respective domains and provides links to their canonical definitions in the Section 04/20 documents.

---

# Domain Classification

Signals are grouped into three primary domains:

- μop domain (datapath realization)
- Architectural control domain (external side effects)
- Sequencing domain (control flow)

Each signal must belong to exactly one domain.

---

# μop Domain (Datapath Realization)

These signals directly implement micro-operations defined in:
- [Micro Operations](../03-microarchitecture/02-micro-operations.md)

They control:
- register writes
- datapath movement
- ALU execution

## Register Load Enables

- AC_load → [AC load definition](../04-control/20-control-output-definitions/01-register-controls.md#ac_load)
- L_load → [L load definition](../04-control/20-control-output-definitions/01-register-controls.md#l_load)
- PC_load → [PC load definition](../04-control/20-control-output-definitions/01-register-controls.md#pc_load)
- MA_load → [MA load definition](../04-control/20-control-output-definitions/01-register-controls.md#ma_load)
- MB_load → [MB load definition](../04-control/20-control-output-definitions/01-register-controls.md#mb_load)
- IR_load → [IR load definition](../04-control/20-control-output-definitions/01-register-controls.md#ir_load)

## Register Source Selects

(Per-register select signals)

- AC_src → [AC source select](../04-control/20-control-output-definitions/01-register-controls.md#ac_src)
- PC_src → [PC source select](../04-control/20-control-output-definitions/01-register-controls.md#pc_src)
- MA_src → [MA source select](../04-control/20-control-output-definitions/01-register-controls.md#ma_src)
- MB_src → [MB source select](../04-control/20-control-output-definitions/01-register-controls.md#mb_src)

## ALU Control

- ALU_OP → [ALU operation encoding](../04-control/20-control-output-definitions/02-alu-control.md#alu_op)
- ALU_A_SEL → [ALU A input select](../04-control/20-control-output-definitions/02-alu-control.md#alu_a_sel)
- ALU_B_SEL → [ALU B input select](../04-control/20-control-output-definitions/02-alu-control.md#alu_b_sel)
- L_UPDATE_MODE → [L update mode](../04-control/20-control-output-definitions/02-alu-control.md#l_update_mode)

## Explicit State Control (Non-ALU)

- II_CLEAR → [Interrupt inhibit clear](../04-control/20-control-output-definitions/01-register-controls.md#ii_clear)
- IE_SET / IE_CLEAR → [Interrupt enable control](../04-control/20-control-output-definitions/01-register-controls.md#ie_control)

---

# Architectural Control Domain

These signals define externally observable behavior.

They do not directly perform data movement; they must bind to μops.

## Memory Control

- RD → [Read control signal](../04-control/20-control-output-definitions/03-architectural-control.md#rd)
- WR → [Write control signal](../04-control/20-control-output-definitions/03-architectural-control.md#wr)

## I/O Control

- DB_READ → [DB read control](../04-control/20-control-output-definitions/03-architectural-control.md#db_read)
- DB_WRITE → [DB write control](../04-control/20-control-output-definitions/03-architectural-control.md#db_write)
- IOA_ENABLE → [IOA control](../04-control/20-control-output-definitions/03-architectural-control.md#ioa)

---

# Sequencing Domain

These signals determine control flow across Major States.

They must not:
- move data
- update registers
- produce side effects

## Sequencing Signals

- MS_next → [Next major state](../04-control/20-control-output-definitions/03-sequencing-control.md#ms_next)
- CONDITION_SELECT → [Condition selection](../04-control/20-control-output-definitions/03-sequencing-control.md#condition_select)

---

# Cross-Domain Rules

## Domain Separation

- μop signals:
  - affect only internal state
- architectural signals:
  - affect only external interface
- sequencing signals:
  - affect only control flow

No signal may span domains.

---

## Binding Requirements

Certain signals must be paired across domains:

- RD must bind to:
  - μop: MEM_READ_TO_MB
- WR must bind to:
  - μop: MEM_WRITE_FROM_MB
- DB_READ / DB_WRITE must bind to:
  - corresponding DB μops

---

## Inactive Encoding Rules

- All enable signals default to 0
- All select signals must encode a valid inert value
- No field may be undefined in any CONTROL_WORD

---

# Notes

- This index is purely organizational
- It does not redefine signals
- All authoritative definitions reside in the linked documents