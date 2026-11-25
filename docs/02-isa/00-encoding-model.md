# Instruction Encoding Model

## 1. Purpose

Defines the instruction formats: which IR bits encode each instruction class and its operands. How control uses those bits is defined in [Control Model](../04-control/01-control-model.md).

---

## 2. Control Interpretation

IR is interpreted as a bitfield: an instruction's fields are its bits, and no symbolic decoding stands between IR and control ([Control Model](../04-control/01-control-model.md)).

---

## 3. IR Structure and Instruction-Class Selection

The opcode occupies `IR[11:9]`.

Its value selects the instruction class, and so the model that applies:

- 0 through 5: a memory-reference instruction (section 4)
- 6: an I/O transfer instruction (section 5)
- 7: an operate instruction (section 6)

The control inputs that identify the classes (`IR_IS_MRI`, `IR_IS_IOT`, `IR_IS_OPR`) are defined in [IR-Derived Fields](../04-control/10-control-input-definitions/02-ir-derived-fields.md).

---

## 4. MRI Model

```
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ 11 │ 10 │ 9  │ 8  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │
├────┴────┴────┼────┼────┼────┴────┴────┴────┴────┴────┴────┤
│    Opcode    │ I  │ P  │          Address offset          │
└──────────────┴────┴────┴──────────────────────────────────┘
```

### 4.1 Opcodes

- 0 - AND Y - AND AC with contents of address Y
- 1 - TAD Y - Twos Complement Add AC with contents of address Y
- 2 - ISZ Y - Increment contents of address Y, skip next instruction if result is zero
- 3 - DCA Y - Deposit AC contents into address Y, clear AC
- 4 - JMS Y - Jump to subroutine at address Y, store PC+1 (the return address) in Y and continue at Y+1
- 5 - JMP Y - Jump to address Y

### 4.2 Flag bits

- I - Indirect addressing required
- P - Page bit (0=page 0, 1=current page)
See the [addressing model](./05-addressing-model.md) doc for more details on address resolution

### 4.3 Effective Address

The final effective address is represented as:

    EA_logical = (EA_FIELD, EA_ADDR)

Where:
- EA_ADDR is derived from offset and page selection
- EA_FIELD is determined by IF or DF depending on addressing mode

---

## 5. IOT Model

```
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ 11 │ 10 │ 9  │ 8  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
│ 1  │ 1  │ 0  │ x  │ x  │ x  │ x  │ x  │ x  │ y  │ y  │ y  │
├────┴────┴────┼────┴────┴────┴────┴────┴────┼────┴────┴────┤
│      IOT     │        Device Address       │  Operation   │
└──────────────┴─────────────────────────────┴──────────────┘
```

- All IOT instructions have an opcode of 6
- Each I/O device has a unique 6 bit address that it responds to, all IOT instructions for other addresses are ignored
- Each device has eight possible IOP encodings. The selected controller defines whether each encoding identifies a supported operation, a combination of operations, or an unsupported operation.

The CPU implements two internal IOT device groups directly. See the [IOT](./04-iot.md) doc for full definitions:
- Device 0 - processor IOTs (interrupt and flag control)
- Devices 20-27 - memory extension control (field instructions)

---

## 6. OPR Model

There are three groups of OPR instructions, distinguished by sentinel bits. Group 2 is further divided into an AND sub-group and an OR sub-group.

```
┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐
│ 11 │ 10 │ 9  │ 8  │ 7  │ 6  │ 5  │ 4  │ 3  │ 2  │ 1  │ 0  │
├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
│ 1  │ 1  │ 1  │ x  │    │    │    │    │ y  │    │    │ z  │
├────┴────┴────┼────┼────┴────┴────┴────┼────┼────┴────┼────┤
│      OPR     │ A  │                   │ B  │         │ C  │
└──────────────┴────┴───────────────────┴────┴─────────┴────┘
```

See the pages linked below for full context on each group
- A=0 - [Group 1](./01-group-1.md)
- A=1 & B=1 & C=0 - [Group 2 (AND)](./02-group-2.md#2-and-sub-group-definition)
- A=1 & B=0 & C=0 - [Group 2 (OR)](./02-group-2.md#5-or-sub-group-definition)
- A=1 & C=1 - [Group 3](./03-group-3.md)

Each remaining bit represents an independent operation, these operations may be combined in various ways depending on the rules imposed at the group level

---

## 7. Operation Ordering

Operations combined in one OPR act in the order the group documents give ([Group 1](./01-group-1.md), [Group 2](./02-group-2.md), [Group 3](./03-group-3.md)). When each takes effect is defined in [OPR Execution](../03-microarchitecture/07-opr/README.md).

---

## 8. Composition Constraint

A combination of operations is defined only where the group documents define it. Combinations they reserve or leave undefined must not be used.
