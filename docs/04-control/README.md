# Control

## 1. Purpose
Defines the control system: how reduced machine state selects a control word, and how that control word drives datapath, architectural, and sequencing behavior.

It describes the mechanism that produces behavior, not the behavior itself.

---

## 2. Scope
Includes:
- Control as a function: CONTROL = f(MS, TS, IR_FIELDS, FLAGS, EXT)
- Control address formation and the control store (CTRL_ADDR -> CONTROL_WORD)
- Control constraints and invariants
- Control input definitions (flags, IR-derived fields, derived flags, external inputs)
- Control output definitions (microarchitectural, architectural, sequencing signals)
- Datapath mapping from control word to system behavior

Excludes:
- Instruction semantics ([02-isa/README.md](../02-isa/README.md))
- Microarchitectural execution ([03-microarchitecture/README.md](../03-microarchitecture/README.md))
- Timing signal definitions ([09-timing/README.md](../09-timing/README.md))

---

## 3. Model Summary
- Control is a deterministic function of reduced machine state.
- CTRL_ADDR selects a precomputed CONTROL_WORD from the control store.
- CONTROL_WORD fully determines datapath, architectural, and sequencing behavior for the cycle.
- All state updates occur at TP; control signals are evaluated during TS.

---

## 4. Related Documents
- [01-control-model.md](./01-control-model.md)
- [02-control-addressing.md](./02-control-addressing.md)
- [03-control-constraints.md](./03-control-constraints.md)
- [04-control-word.md](./04-control-word.md)
- [05-datapath-mapping.md](./05-datapath-mapping.md)
- Control input definitions:
  - [00-index.md](./10-control-input-definitions/00-index.md)
  - [01-flags.md](./10-control-input-definitions/01-flags.md)
  - [02-ir-derived-fields.md](./10-control-input-definitions/02-ir-derived-fields.md)
  - [03-derived-flags.md](./10-control-input-definitions/03-derived-flags.md)
  - [04-external-inputs.md](./10-control-input-definitions/04-external-inputs.md)
- Control output definitions:
  - [00-index.md](./20-control-output-definitions/00-index.md)
  - [01-microarchitectural-control-signals.md](./20-control-output-definitions/01-microarchitectural-control-signals.md)
  - [02-architectural-control-signals.md](./20-control-output-definitions/02-architectural-control-signals.md)
  - [03-sequencing-control-signals.md](./20-control-output-definitions/03-sequencing-control-signals.md)