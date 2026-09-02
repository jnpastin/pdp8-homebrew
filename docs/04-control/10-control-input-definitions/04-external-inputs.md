# External Inputs

## 1. Purpose
 
Defines external input signals (`EXT`) used as inputs to the control function:
 
```text
CONTROL = f(MS, TS, IR_FIELDS, FLAGS, EXT)
```

External inputs originate outside the CPU control system and influence control decisions through the `EXT` input domain.

Related:
- [Control Model](../01-control-model.md)
- [Control Constraints](../03-control-constraints.md)
- [Console Microarchitecture](../../03-microarchitecture/09-console-execution.md)
- [Primitive Flags](./01-flags.md)
- [Derived Flags](./03-derived-flags.md)

---

## 2. Timing Model

External inputs must be stable for the duration of the timing state in which they are evaluated.

Constraints:
- External inputs must be synchronized to the control timing model before use.
- External inputs must not change during the control evaluation window.
- External inputs must not directly update registers.
- External inputs must not bypass the control function.
- External inputs must not introduce asynchronous state changes.

---

## 3. Signal Classes

External inputs are grouped into:

- Front-Panel Command Inputs
- Front-Panel Mode Inputs
- Front-Panel Data Inputs
- External Request Inputs
- External IOT Response Inputs

---

## 4. Front-Panel Command Inputs

Front-panel command inputs are momentary operator commands.

Properties:
- asserted by front-panel controls
- consumed by control only when valid for the current machine state
- do not directly execute behavior
- do not directly modify processor state

During normal execution, front-panel command inputs are ignored except for `FP_STOP`.

During halted execution, front-panel command inputs may select a single console operation.

### FP_START

**Name:** Front Panel Start Command  
**Type:** External Command Input  
**Bit Width:** 1

**Purpose:** Indicates that the operator has requested START from the front panel.

**Value Encoding:**
- 0 → START command not asserted
- 1 → START command asserted

**Consumed By:**
- Control decision:
  - run-state sequencing
  - console execution control
  
**Constraints:**
- meaningful only when `RUN = 0`
- must be treated as a momentary command input

### FP_CLEAR
  
**Name:** Front Panel Clear Command  
**Type:** External Command Input  
**Bit Width:** 1  

**Purpose:** 
Indicates that the operator has requested system initialization from the front panel.

**Value Encoding:**
- 0 -> CLEAR command not asserted
- 1 -> CLEAR command asserted

**Consumed By:**
- [System Initialization](../20-control-output-definitions/02-architectural-control-signals.md#49-system-initialization-initialize)

**Constraints:**
- meaningful only when RUN = 0
- ignored when RUN = 1
- must be synchronized and debounced before use
- must be treated as a momentary command input
- generates one /INITIALIZE pulse per distinct accepted press
- must not retrigger while the synchronized input remains asserted
- is re-armed only after the synchronized input is released
- must not directly modify processor or controller state

### FP_CONTINUE

**Name:** Front Panel Continue Command  
**Type:** External Command Input  
**Bit Width:** 1

**Purpose:** Indicates that the operator has requested CONTINUE from the front panel.

**Value Encoding:**
- 0 → CONTINUE command not asserted
- 1 → CONTINUE command asserted

**Consumed By:**
- Control decision:
  - run-state sequencing
  - console execution control
  
**Constraints:**
- meaningful only when `RUN = 0`
- must be treated as a momentary command input

### FP_STOP

**Name:** Front Panel Stop Command  
**Type:** External Command Input  
**Bit Width:** 1

**Purpose:** Indicates that the operator has requested STOP from the front panel.

**Value Encoding:**
- 0 → STOP command not asserted
- 1 → STOP command asserted

**Consumed By:**
- halt request generation

**Constraints:**
- may be recognized during normal execution
- must not halt execution immediately
- contributes only to halt-request behavior

### FP_LOAD_ADDRESS

**Name:** Front Panel Load Address Command  
**Type:** External Command Input  
**Bit Width:** 1

**Purpose:** Indicates that the operator has requested LOAD ADDRESS from the front panel.

**Value Encoding:**
- 0 → LOAD ADDRESS command not asserted
- 1 → LOAD ADDRESS command asserted

**Consumed By:**
- console execution control

**Constraints:**
- meaningful only when `RUN = 0`
- ignored during normal execution
- must be treated as a momentary command input

### FP_EXAMINE

**Name:** Front Panel Examine Command  
**Type:** External Command Input  
**Bit Width:** 1

**Purpose:** Indicates that the operator has requested EXAMINE from the front panel.

**Value Encoding:**
- 0 → EXAMINE command not asserted
- 1 → EXAMINE command asserted

**Consumed By:**
- console execution control

**Constraints:**
- meaningful only when `RUN = 0`
- ignored during normal execution
- must be treated as a momentary command input

### FP_DEPOSIT

**Name:** Front Panel Deposit Command  
**Type:** External Command Input  
**Bit Width:** 1

**Purpose:** Indicates that the operator has requested DEPOSIT from the front panel.

**Value Encoding:**
- 0 → DEPOSIT command not asserted
- 1 → DEPOSIT command asserted

**Consumed By:**
- console execution control

**Constraints:**
- meaningful only when `RUN = 0`
- ignored during normal execution
- must be treated as a momentary command input

---

## 5. Front-Panel Mode Inputs

Front-panel mode inputs are persistent operator-selected modes.

These inputs do not initiate execution.

### FP_SINGLE_INSTRUCTION

**Name:** Front Panel Single Instruction Mode  
**Type:** External Mode Input  
**Bit Width:** 1

**Purpose:** Indicates that Single Instruction mode is enabled.

**Value Encoding:**
- 0 → disabled
- 1 → enabled

**Consumed By:**
- run-state sequencing

**Constraints:**
- does not initiate execution
- does not modify instruction behavior
- affects only run/stop behavior

### FP_SINGLE_STEP

**Name:** Front Panel Single Step Mode  
**Type:** External Mode Input  
**Bit Width:** 1

**Purpose:** Indicates that Single Step mode is enabled.

**Value Encoding:**
- 0 → disabled
- 1 → enabled

**Consumed By:**
- run-state sequencing

**Constraints:**
- does not initiate execution
- does not modify instruction behavior
- affects only run/stop behavior

---

## 6. Front-Panel Data Inputs

Front-panel data inputs provide externally selected values used by console operations.

### FP_IF

**Name:** Front Panel Instruction Field Input  
**Type:** External Data Input  
**Bit Width:** 3

**Purpose:** Provides the front-panel Instruction Field value.

**Value Encoding:**
- 000-111 → instruction field value

**Consumed By:**
- [FP_IF_TO_IF](../../03-microarchitecture/02-micro-operations.md#fp_if_to_if)
- [FP_IF_TO_DIF](../../03-microarchitecture/02-micro-operations.md#fp_if_to_dif)

**Constraints:**
- must be stable when sampled
- must not directly modify IF

### FP_DF

**Name:** Front Panel Data Field Input  
**Type:** External Data Input  
**Bit Width:** 3

**Purpose:** Provides the front-panel Data Field value.

**Value Encoding:**
- 000-111 → data field value

**Consumed By:**
- [FP_DF_TO_DF](../../03-microarchitecture/02-micro-operations.md#fp_df_to_df)

**Constraints:**
- must be stable when sampled
- must not directly modify DF

---

## 7. External Request Inputs

### /DMA_REQ

**Name:** DMA Request  
**Type:** External Request Input  
**Bit Width:** 1  
**Polarity:** Active-low

**Purpose:** Indicates that an external DMA-capable device or device-side DMA arbiter is requesting DMA service.

**Value Encoding:**
- 0 → DMA request pending
- 1 → no DMA request pending

**Consumed By:**
- DMA sequencing control
- [/DMA_GRANT](../20-control-output-definitions/02-architectural-control-signals.md#45-dma_grant)
- [MS_NEXT](../20-control-output-definitions/03-sequencing-control-signals.md#41-next-major-state-ms_next)

**Constraints:**

- participates in EXT
- contributes to `CTRL_ADDR` formation
- is derived combinationally from `DMA_ENABLE` and registered controller `/DMA_REQ[n]` outputs
- must not pass through an additional stateful synchronization stage
- must satisfy the applicable setup and hold requirements before CPU control samples it at TP4
- must not directly modify processor state
- must not directly assert memory, address, or data-bus control
- may be deasserted while controller `/DMA_REQ[n]` lines remain asserted when `DMA_ENABLE = 0`

### /INT_REQ

**Name:** Interrupt Request  
**Type:** External Request Input  
**Bit Width:** 1
**Polarity:** Active-low

**Purpose:** Indicates that one or more external devices are requesting interrupt service.

**Value Encoding:**
- 0 → interrupt request pending
- 1 → no interrupt request pending

**Consumed By:**
- [Interrupt Request Valid](./03-derived-flags.md#interrupt_request_valid)
- [GTF_FLAGS](../20-control-output-definitions/01-microarchitectural-control-signals.md#gtf_flags)

**Constraints:**
- must be synchronized before use by control
- must not directly modify processor state

---

## 8. External IOT Response Inputs

External-IOT response inputs originate in the selected external controller and are consumed by CPU control or timing logic.

Shared properties:

- All external-IOT response inputs are one bit wide.
- The selected external controller is the only permitted producer.
- An unselected controller must deassert every external-IOT response input.
- The signals participate in EXT.
- Phase-specific response signals must be stable during the control-evaluation window preceding their commit TP.
- A response signal requests CPU or timing behavior and does not directly modify CPU state.
- Signal behavior must satisfy the [External IOT Interface](../../07-io/02-external-iot-interface.md).

### IO_READ_REQ

**Name:** I/O Read Request  
**Type:** External IOT Response Input  
**Bit Width:** 1  
**Polarity:** Active-high  

**Purpose:** Requests a device-to-CPU DB transfer during the phase following acceptance of the request.

**Value Encoding:**

- 0: no read requested
- 1: device-to-CPU read requested

**Consumed By:**

- CPU control at the TP following the request TS
- `/DB_READ` generation during the following TS
- `DB_READ_TO_AC` at the subsequent TP

**Constraints:**

- Valid only when `IOT_ACTIVE` is asserted.
- Valid only from the address-matched controller.
- Phase-specific.
- Mutually exclusive with `IO_WRITE_REQ`.
- Must be asserted early enough for the complete DB transfer to occur within the current external-IOT EXECUTE major state.
- Must be stable before and through the TP at which CPU control accepts the request.
- Must not cause the controller to drive DB during the request phase.
- Must not directly modify AC.
- The selected controller drives DB only while CPU control asserts `/DB_READ` during the following transfer phase.

### IO_WRITE_REQ

**Name:** I/O Write Request  
**Type:** External IOT Response Input  
**Bit Width:** 1  
**Polarity:** Active-high  

**Purpose:** Requests a CPU-to-device DB transfer during the phase following acceptance of the request.

**Value Encoding:**

- 0: no write requested
- 1: CPU-to-device write requested

**Consumed By:**

- CPU control at the TP following the request TS
- `/DB_WRITE` generation during the following TS
- controller DB capture at the subsequent TP

**Constraints:**

- Valid only when `IOT_ACTIVE` is asserted.
- Valid only from the address-matched controller.
- Phase-specific.
- Mutually exclusive with `IO_READ_REQ`.
- Must be asserted early enough for the complete DB transfer to occur within the current external-IOT EXECUTE major state.
- Must be stable before and through the TP at which CPU control accepts the request.
- Must not cause the controller to capture DB during the request phase.
- The selected controller captures DB only at the TP following the transfer phase in which CPU control asserts `/DB_WRITE`.

### IO_SKIP_REQ

**Name:** I/O Skip Request  
**Type:** External IOT Response Input  
**Bit Width:** 1  
**Purpose:** Requests PC increment at TP4.

**Value Encoding:**

- `0` -> no skip requested
- `1` -> skip requested

**Consumed By:**

- `PC_INC`

**Constraints:**

- Valid only during TS4 of an external IOT.
- Valid only from the address-matched controller.
- Must be based on controller state captured at TP3.
- Causes only CPU `PC_INC`.
- Must not depend on a result committed at TP4.
- Must not directly modify PC.

### IO_CLEAR_AC_REQ

**Name:** I/O Clear AC Request  
**Type:** External IOT Response Input  
**Bit Width:** 1  
**Purpose:** Requests AC clear at the following TP.

**Value Encoding:**

- `0` -> no AC clear requested
- `1` -> AC clear requested

**Consumed By:**

- AC clear control

**Constraints:**

- Valid only when `IOT_ACTIVE = 1`.
- Valid only from the address-matched controller.
- Phase-specific.
- May coincide with `IO_READ_REQ` during the read-request TS; AC clear commits when the read request is accepted, and the DB read commits during the following TS and TP.
- Must not be asserted during the transfer TS following an accepted `IO_READ_REQ`.
- Must not cause AC clear and `DB_READ_TO_AC` to commit at the same TP.
- May coincide with `IO_WRITE_REQ`.
- Must not directly modify AC.

### /IO_WAIT

**Name:** I/O Wait Request  
**Type:** External Timing Request Input  
**Bit Width:** 1  
**Polarity:** Active-low

**Purpose:** Holds the current eligible non-TP setup TSTEP until the selected controller is ready.

**Value Encoding:**

- `0` -> hold the current eligible non-TP setup TSTEP
- `1` -> normal TSTEP progression

**Consumed By:**

- TSTEP progression logic

**Constraints:**

- Valid only when `IOT_ACTIVE = 1`.
- Valid only from the address-matched controller.
- Ignored when the current TSTEP is a TP position.
- Must not extend, suppress, or repeat a TP.
- Must be synchronized before influencing TSTEP progression.
- Must not modify RUN.
- Must not directly modify MS or architectural state.

Detailed behavior is defined in [I/O Timing](../../07-io/03-io-timing.md)

---

## 9. Summary

External inputs define the complete set of non-register inputs available to control.

They:
- originate outside the CPU control system
- participate in the `EXT` input domain
- may influence control decisions
- must be stable during control evaluation
- must not directly modify processor state