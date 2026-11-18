# System Harness

## 1. Purpose

Joins the [CPU simulator](../cpu/README.md) and the [memory model](../memory/README.md) into a machine and drives it as an operator would. Importing `pdp8_system` puts both packages on the import path; no install step is needed.

## 2. Machine

`pdp8_system.machine.Machine` powers on a CPU with fresh memory and offers console helpers. Each helper sets the front-panel switches and presses one console key, so every operation runs through the console microcode:

| Helper | Console operation |
|---|---|
| `load_address(address, instruction_field, data_field)` | LOAD ADDRESS |
| `deposit(value)`, `deposit_block(address, values, instruction_field)` | DEPOSIT |
| `examine()` | EXAMINE; returns MB |
| `start()`, `cont()`, `clear()` | START, CONTINUE, CLEAR |
| `run(max_ts)` | steps timing states until the processor halts |

With `keep_trace=True`, every TS and console transaction is recorded in `trace`, with both control-store addresses, the decoded words, and the committed loads and memory operations.

The control store is loaded and validated once per process (`load_store`).

## 3. Command Line

```text
python sim/system/src/run_sim.py --check
```

Validates the images, the packing description, and the field encodings, then deposits and examines a HLT instruction and runs it from START. Exits 0 on success.

## 4. Lock-Step Comparison

`pdp8_system.lockstep.Lockstep` runs a machine beside the [reference model](../reference/README.md). After every instruction, and after every interrupt entry, both must agree on AC, L, MQ, PC, IF, DF, IE, the memory words written, whether the processor halted, and whether an interrupt was recognized at that boundary. The first difference raises `Divergence`, naming the step, the instruction (field, address, word, and mnemonic), and, for each differing register, the major state and TP at which the simulator committed it.

A boundary in the simulator is the TP4 of an EXECUTE or INTERRUPT major state. `int_req` supplies the interrupt request for each step, held constant within it. DMA, Single Step, and Single Instruction are outside the comparison.

`reference_from(machine)` builds a reference model from the machine's current state, so a comparison can start at any instruction boundary.

## 5. Paper Tapes and Controllers

`pdp8_system.papertape` reads DEC BIN-format tapes (leader, field settings, origins, data words, rubouts, checksum) and `load_tape(machine, tape)` loads one through console LOAD ADDRESS and DEPOSIT, refusing a tape whose checksum does not match.

`Machine(devices=[KL8E()])` attaches [I/O controller models](../io/README.md). `Machine.core_residue(seed)` gives every memory word an arbitrary defined value before a program is loaded, standing in for what core memory retained from earlier use: core keeps its contents through power-on and CLEAR, and some diagnostics read words they never load. A program that does not depend on leftover contents must give the same result for every seed. Without it, memory stays UNDEFINED.

## 6. Testing

```text
python -m unittest discover -s sim/system/tests -p "test_*.py"
```

`test_instructions.py` is the milestone M1 suite. Each program is placed with DEPOSIT and started with START or CONTINUE, and its expected results are derived from the ISA and interrupt documentation, citing the section each test checks:

| Area | Covered |
|---|---|
| Operate | every instruction 7000–7777 from five starting states |
| Memory reference | AND, TAD (carry into L), ISZ, DCA, JMS, JMP; direct, indirect, zero page, current page at a page's last word; autoindex in fields 0 and 1; PC wrap |
| Memory extension | CDF, CIF, CDF CIF, RDF, RIF; DF for indirect AND/TAD/ISZ/DCA operands; IF for JMP and JMS targets |
| Processor IOTs | ION, IOF, SKON, SRQ, GTF, RTF, SGT, CAF (no interrupt at CAF completion); external IOT with no device |
| Interrupts | ION delay, entry from non-zero fields, CIF inhibit window, RIB, RMF and `JMP I 0` return |
| Run control | HLT and CONTINUE, Single Step through DEFER, Single Instruction, STOP |

`test_lockstep.py` is the milestone M2 suite: the M1 programs and an interrupt-service program compared after every instruction; seeded random runs over all eight fields from random processor states, with memory biased toward the processor and memory-extension IOTs, checked for coverage of interrupts, field changes, and every processor IOT; and two checks that a divergence is detected and reported with its instruction and TP.

`test_papertape.py` checks the loader against every tape in `sim/test_programs`: checksums, the octal dumps, and the D0AB listing. `test_kl8e.py` runs the KL8E through the external-IOT microcode in lock-step with the reference model's KL8E. `test_maindec.py` is the milestone M3 suite: MAINDEC-8E-D0AB and D0BB, operated as their write-ups direct, for two passes each in lock-step, and D0BB's end-of-pass bell.
