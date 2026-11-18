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

## 4. Planned

The instruction-level reference model and the lock-step comparer (milestone M2), and the paper-tape loader that loads test programs through DEPOSIT (milestone M3).

## 5. Testing

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
