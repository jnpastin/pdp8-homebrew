# Reference Model

## 1. Purpose

An instruction-level model of the ISA, used to check the control-store simulator. It is written only from the ISA documentation ([docs/02-isa](../../docs/02-isa/README.md)) and the architectural interrupt rules ([docs/08-interrupts-and-skip](../../docs/08-interrupts-and-skip/README.md)). It knows nothing of timing states, micro-operations, or the control store, so agreement between the two checks the microarchitecture and control layers against the ISA layer.

It does not check the ISA documentation against DEC. That is the role of the occasional SIMH comparison.

## 2. Model

`pdp8_reference.Reference` holds AC, L, MQ, PC, IF, DF, IE, the interrupt-saved fields (IB), a staged instruction field (set by CIF, RMF, or RTF and applied by the next JMP or JMS), the switch register, the interrupt request, and 32K words of memory.

`step()` executes one instruction, or one interrupt entry, and returns a `StepResult`: the instruction's address and field, the instruction word, the memory words written, whether it halted, and whether an interrupt is recognized at its completion.

| Behavior | Source |
|---|---|
| Memory-reference instructions, effective address, autoindex | Encoding Model §4, Addressing Model §7–§13, EA Generation §6–§8 |
| JMP and JMS targets in IF, after any staged field change | Addressing Model §7, IOT §4.1 |
| Operate groups 1–3 | Group 1, Group 2, Group 3 |
| Processor IOTs and memory extension | IOT §3–§4, §6 |
| Recognition at instruction completion; ION, CIF, RMF, RTF and a pending field change inhibit it; never at CAF's completion | Interrupt Recognition and Sequencing §6; Interrupt Enable and Inhibit §16; IOT §3.2 |
| Interrupt entry | Interrupt Entry and Return §4–§6 |

No device is attached: an external-device IOT selects no controller and has no effect. Reading an undefined memory word, or reading the interrupt buffer before any interrupt entry, raises `ReferenceError`.

`disassemble(ir)` gives a mnemonic for reports.

## 3. Testing

```text
python -m unittest discover -s sim/reference/tests -p "test_*.py"
```

The tests check the model against the values derived by hand for the M1 suite, so the model and the simulator are each checked against an independent expectation.
