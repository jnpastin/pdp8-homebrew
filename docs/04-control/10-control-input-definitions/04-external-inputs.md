### External Inputs

#### Purpose
 
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

### Timing Model

External inputs must be stable for the duration of the timing state in which they are evaluated.

Constraints:
- External inputs must be synchronized to the control timing model before use.
- External inputs must not change during the control evaluation window.
- External inputs must not directly update registers.
- External inputs must not bypass the control function.
- External inputs must not introduce asynchronous state changes.

### Signal Classes
 
External inputs are grouped into:

- Front-Panel Command Inputs
- Front-Panel Mode Inputs
- Front-Panel Data Inputs
- External Request Inputs

### Front-Panel Command Inputs

Front-panel command inputs are momentary operator commands.

Properties:
- asserted by front-panel controls
- consumed by control only when valid for the current machine state
- do not directly execute behavior
- do not directly modify processor state

During normal execution, front-panel command inputs are ignored except for `FP_STOP`.

During halted execution, front-panel command inputs may select a single console operation.

#### FP_START

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

#### FP_CONTINUE

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

#### FP_STOP

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

#### FP_LOAD_ADDRESS

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

#### FP_EXAMINE

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

#### FP_DEPOSIT

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

### Front-Panel Mode Inputs

Front-panel mode inputs are persistent operator-selected modes.

These inputs do not initiate execution.

#### FP_SINGLE_INSTRUCTION

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

#### FP_SINGLE_STEP

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

### Front-Panel Data Inputs

Front-panel data inputs provide externally selected values used by console operations.

#### FP_IF

**Name:** Front Panel Instruction Field Input  
**Type:** External Data Input  
**Bit Width:** 3

**Purpose:** Provides the front-panel Instruction Field value.

**Value Encoding:**
- 000-111 → instruction field value

**Consumed By:**
- [FP_IF_TO_IF](../../03-microarchitecture/02-micro-operations.md#fp_if_to_if)

**Constraints:**
- must be stable when sampled
- must not directly modify IF

#### FP_DF

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

### External Request Inputs

#### DMA_REQ

**Name:** DMA Request  
**Type:** External Request Input  
**Bit Width:** 1  

**Purpose:** Indicates that an external DMA-capable device or device-side DMA arbiter is requesting DMA service.

**Value Encoding:**
- 0 → no DMA request pending
- 1 → DMA request pending

**Consumed By:**
- DMA sequencing control
- [DMA_GRANT](../20-control-output-definitions/02-architectural-control-signals.md#35-dma_grant)
- [MS_NEXT](../20-control-output-definitions/03-sequencing-control-signals.md#31-next-major-state-ms_next)

**Constraints:**
- participates in `EXT`
- contributes to `CTRL_ADDR` formation
- must be synchronized before use by control
- must not directly modify processor state
- must not directly assert memory, address, or data bus control
- must remain asserted while continued DMA service is requested

#### INT_REQ

**Name:** Interrupt Request  
**Type:** External Request Input  
**Bit Width:** 1

**Purpose:** Indicates that one or more external devices are requesting interrupt service.

**Value Encoding:**
- 0 → no interrupt request pending
- 1 → interrupt request pending

**Consumed By:**
- [Interrupt Request Valid](./03-derived-flags.md#interrupt_request_valid)

**Constraints:**
- must be synchronized before use by control
- must not directly modify processor state

### Summary

External inputs define the complete set of non-register inputs available to control.

They:
- originate outside the CPU control system
- participate in the `EXT` input domain
- may influence control decisions
- must be stable during control evaluation
- must not directly modify processor state