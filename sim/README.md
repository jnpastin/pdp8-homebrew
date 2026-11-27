# Simulation

## 1. Purpose

Simulates the machine from its generated control-store images, to validate the documentation, the ROM-generation tools, and the images before hardware is built. Every modelled behavior cites the document that defines it.

---

## 2. Structure

| Package | Contents |
|---|---|
| [`cpu`](./cpu/README.md) | the CPU, one timing state at a time, from the packed control-store and timing ROM images |
| [`memory`](./memory/README.md) | main memory (32K words, undefined until written) |
| [`io`](./io/README.md) | I/O controller models (KL8E) and the DMA arbiter |
| [`reference`](./reference/README.md) | an instruction-level reference model written from `docs/02-isa`, independent of the control store |
| [`system`](./system/README.md) | the assembled machine: console helpers, paper-tape loading, lock-step comparison, MAINDEC runs |
| [`test_programs`](./test_programs/README.md) | DEC MAINDEC-8E diagnostics, with their provenance |

The CPU and the reference model are compared in lock-step at every instruction boundary, interrupt entry, and DMA cycle: registers, fields, and memory writes must agree. The PC8E and RK8E controllers are not yet modelled.

`PDP8_DESIGN` selects the control design (`v1` or `v2`; [`cpu/src/pdp8_cpu/design.py`](./cpu/src/pdp8_cpu/design.py)).

---

## 3. Running the Tests

```text
python sim/run_all_tests.py                    # both designs, every suite
python sim/run_all_tests.py --design v2        # one design
python sim/run_all_tests.py --quick            # without the system suite
```

The system suite is much faster under PyPy. Long runs are opt-in:

| Variable | Adds |
|---|---|
| `PDP8_LONG_TESTS=1` | the MAINDEC-8E-D2AB timing routines on the reference model |
| `PDP8_FULL_PASSES=short` | complete passes of D0CC to D0JC and D1EC in lock-step (about 15 minutes) |
| `PDP8_FULL_PASSES=all` | also D1HA, D1FB, D1BC, D1AA, and D2AB (about 2 to 3 hours) |
