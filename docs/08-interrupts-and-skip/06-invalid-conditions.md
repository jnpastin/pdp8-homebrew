# Interrupt and Skip Invalid Conditions

## 1. Purpose

This document identifies illegal interrupt and skip conditions defined by Section 8.

## 2. Illegal Interrupt Conditions

The following conditions are illegal:

- `MS = EXECUTE` at TP4, `INTERRUPT_REQUEST_VALID = 1`, and `MS_NEXT != INTERRUPT`
- `MS = EXECUTE` at TP4, `INTERRUPT_REQUEST_VALID = 1`, aggregate `/DMA_REQ = 0`, and `MS_NEXT = DMA`
- `MS = EXECUTE` at TP4, `INTERRUPT_REQUEST_VALID = 0`, aggregate `/DMA_REQ = 0`, and `MS_NEXT != DMA`
- `MS = EXECUTE` at TP4, `INTERRUPT_REQUEST_VALID = 0`, aggregate `/DMA_REQ = 1`, and `MS_NEXT != FETCH`
- `MS = INTERRUPT` at TP4 and `MS_NEXT != FETCH`
- entry into `INTERRUPT` from a major state other than `EXECUTE`
- interrupt recognition at a timing pulse other than EXECUTE TP4
- any interrupt-entry state change before entry into the `INTERRUPT` major state
- `CIFP = 1` and FETCH selecting `II_CLEAR`
- a pending CIF- or RMF-staged instruction-field change being applied by an instruction other than JMP or JMS
- a JMP or JMS applying a pending instruction-field change without clearing `CIFP`
- interrupt recognition at the same EXECUTE TP4 that applies a pending instruction-field change

## 3. Illegal Interrupt-Entry and Return Conditions

The following conditions are illegal:

- interrupt entry completing without storing the return `PC` in memory field 0, address `0000`
- interrupt entry completing without storing the pre-entry `IF` and `DF` values in `IB`
- interrupt entry completing with `PC != 0001`
- interrupt entry completing with `IE != 0`
- interrupt entry completing with `IF != 0`
- interrupt entry completing with `DF != 0`
- interrupt entry completing with `DIF != 0`
- interrupt entry completing with `CIFP != 0`
- RMF completing without restoring `DF` from `IB`
- RMF completing without loading the saved `IF` from `IB` into `DIF`
- RMF completing without setting both `II` and `CIFP`
- return through location `0000` using direct rather than indirect JMP
- completion of the return JMP without applying the pending saved instruction field
- interrupt recognition between ION and the immediately following return JMP

## 4. Illegal Skip Conditions

The following conditions are illegal:

- a true skip condition producing no `PC_INC`
- a false skip condition producing `PC_INC`
- one skip decision producing more than one `PC_INC`
- `PC_INC` and `PC_LOAD` being selected at the same TP
- a skip increment committing at a TP other than the TP assigned to its source
- a skip decision using state committed at the same TP
- an external controller directly modifying `PC`
- `IO_SKIP_REQ` producing a skip outside external-IOT TS4 and TP4
- an unselected controller producing an effective `IO_SKIP_REQ`
- a skip result remaining effective after its assigned TP
- interrupt or DMA major-state selection canceling a valid skip committed at the same EXECUTE TP4

## 5. Summary

The illegal conditions in this document are limited to contradictions within the Section 8 interrupt and skip coordination model.

Invalid instruction encodings, micro-operation combinations, control words, controller responses, and timing behavior remain defined by their owning sections.