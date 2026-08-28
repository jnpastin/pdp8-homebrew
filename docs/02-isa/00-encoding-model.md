# Instruction Encoding Model

Status: normative

## 1. Purpose

Defines how IR bits map directly into control behavior for a ROM-based microarchitecture.

---

## 2. Control Interpretation

IR must be interpreted strictly as a bitfield.

Control logic operates on:
(MS, TS, IR bits, FLAGS)

No instruction decoding into symbolic instructions is permitted.

---

## 3. IR Structure

The contents of the instruction register are interpreted differently based on the opcode. The opcode is contained in the three MSBs (IR[11:9])

- 0-5 → Memory Reference Instruction (MRI)
- 6   → I/O Transfer Instruction (IOT)
- 7   → Operate Instruction (OPR)

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
- 4 - JMS Y - Jump to subroutine at address Y, store PC+1 in address Y for return
- 5 - JMP Y - Jump to address Y

### 4.2 Flag bits

- I - Indirect addressing required
- P - Page bit (0=page 0, 1=current page)
See the [addressing model](./05-addressing-model.md) doc for more details on address resolution

### 4.3 Effective Address

The final effective address is represented as:

    EA_logical = (EA_fld, EA_addr)

Where:
- EA_addr is derived from offset and page selection
- EA_fld is determined by IF or DF depending on addressing mode

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

There are three groups of OPR instructions, they are distinguished by sentinel bits.  Group two is further divided into an AND group and an OR Group

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
- A=1 & B=1 & C=0 - [Group 2 (AND)](./02-group-2.md#1-and-sub-group-definition-and-timing)
- A=1 & B=0 & C=0 - [Group 2 (OR)](./02-group-2.md#4-or-sub-group-definition-and-timing)
- A=1 & C=1 - [Group 3](./03-group-3.md)

Each remaining bit represents an independent operation, these operations may be combined in various ways depending on the rules imposed at the group level

---

## 7. Execute Time States

TS defines execution ordering within EXECUTE.

Operations assigned to different TS execute in strict order.

---

## 8. Composition Constraint

Operations that:
- target the same register
- and occur in the same TS

are not required to be supported unless explicitly defined.
