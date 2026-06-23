# Sequencing Control Signals

## Purpose

Defines control outputs responsible for **control flow within the CPU**.

These signals determine:

- Major State progression
- conditional control decisions

Sequencing signals:

- originate from the control word
- operate only on control flow
- do not influence timing generation (TS/TP)
- do not perform datapath operations

Related:
- [Control Model](../01-control-model.md)
- [Control Constraints](../03-control-constraints.md)
- [Timing Model](../../09-timing/README.md)

---

## 1. Scope

Sequencing control signals define **how control transitions between Major States (MS)**.

They:

- select MS_next
- evaluate conditions
- control branching decisions

They do NOT:

- advance Time State (TS)
- control TP generation
- move data
- update registers

---

## 2. Global Properties

### 2.1 Functional Model

Control is defined as:

```
CONTROL = f(MS, TS, INST, FLAGS, EXT)
```

Sequencing signals are part of this function.

- TS and TP are inputs
- sequencing produces next-state decisions
- state updates occur only at TP

---

### 2.2 Determinism

For every tuple:

```
(MS, TS, INST, FLAGS, EXT)
```

there must be exactly one:

```
MS_next value
branch decision
```

No ambiguity is permitted.

---

### 2.3 Timing Independence

Sequencing signals:

- do not control TS progression
- do not interact with the shift register
- do not depend on timing generation mechanisms

TS/TP behavior is defined in:

- [Timing Model](../../09-timing/README.md)

---

## 3. Signal Definitions

---

### 3.1 Next Major State (MS_next)

**Name**  
MS_next  

**Type**  
Encoded field  

**Domain**  
Sequencing  

**Width**  
Sufficient to encode all Major States  

Defined in:
- [Major State Model](../../03-microarchitecture/00-state-model.md)

**Description**

Specifies the next Major State.

Typical values:

- FETCH
- DEFER
- EXECUTE
- INTERRUPT

**Behavior**

- evaluated during TS4
- committed at TP4
- becomes the new MS

**Constraints**

- must be defined for all states at TS4
- must not change outside TS4
- must not be modified by μops

---

### 3.2 Branch Enable (BRANCH_enable)

**Name**  
BRANCH_enable  

**Type**  
Single-bit  

**Domain**  
Sequencing  

**Description**

Enables conditional sequencing behavior.

**Behavior**

- when 1:
  - a condition is evaluated
  - sequencing selects between alternate outcomes

- when 0:
  - default sequencing behavior applies

**Constraints**

- must not be asserted without a valid condition context
- must not directly modify MS or TS
- only affects selection of MS_next or control flow path

---

### 3.3 Branch Polarity (BRANCH_when_true)

**Name**  
BRANCH_when_true  

**Type**  
Single-bit  

**Domain**  
Sequencing  

**Description**

Defines the polarity of the condition used for branching.

Values:

- 1 → branch when condition is true  
- 0 → branch when condition is false  

**Constraints**

- only meaningful when BRANCH_enable = 1
- must be explicitly defined for all valid control states

---

## 4. Sequencing Model

---

### 4.1 Time State Interpretation

Time State (TS):

- is derived from a one-hot shift register
- is not controlled by sequencing logic
- is treated as an input to control

Defined in:
- [Timing Model](../../09-timing/README.md)

Control:

- reacts to TS
- does not alter TS progression

---

### 4.2 Major State Transition

At TS4:

- MS_next is selected
- transition occurs at TP4

General transitions:

- FETCH → EXECUTE or DEFER
- DEFER → EXECUTE
- EXECUTE → FETCH or INTERRUPT
- INTERRUPT → FETCH

All transitions must be explicitly defined.

---

### 4.3 Conditional Sequencing

When BRANCH_enable = 1:

```
if condition == BRANCH_when_true:
    select alternate control decision
else:
    select default control decision
```

Branch decisions may affect:

- MS_next
- control word selection

---

### 4.4 TS Coverage Requirement

Control must define behavior for every:

```
(MS, TS, INST class)
```

Implications:

- no TS may be left undefined
- unused TS must produce safe control outputs
- all control outputs must be valid

---

## 5. Skip and Flow Behavior

Skip behavior is implemented through μops.

Sequencing signals:

- do not directly modify PC
- only determine whether skip-related μops are active

Defined in:
- [Group 2 Execution](../../03-microarchitecture/07-opr/02-group2-execution.md)

---

## 6. Interaction Rules

---

### 6.1 No Implicit Control Flow

All control flow must be:

- explicitly encoded
- fully determined by control inputs

No implicit transitions are permitted.

---

### 6.2 Single Effective Decision

At each TS:

- only one sequencing decision may be effective

This ensures deterministic behavior.

---

### 6.3 External Input Usage

External signals (EXT):

- may influence sequencing via conditions
- must not directly change MS or TS

---

### 6.4 Separation from Timing Extensions

Sequencing signals must not interact with:

- clock gating
- shift register control
- DMA hold mechanisms

Those are defined in:
- [Timing Model](../../09-timing/README.md)

---

## 7. Summary

Sequencing control signals define **how control progresses between Major States**.

They:

- select MS_next
- evaluate conditions
- control branching decisions

They do not:

- control timing (TS/TP)
- execute datapath operations
- move or transform data

All sequencing behavior is:

- explicit
- deterministic
- fully defined per TS

See:

- [Control Model](../01-control-model.md)
- [Control Constraints](../03-control-constraints.md)
- [Micro-Operations](../../03-microarchitecture/02-micro-operations.md)