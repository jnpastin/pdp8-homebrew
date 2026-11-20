# Diagram Changes for Option 2 (running list)

The user maintains the diagrams; Claude never edits them. This list records, per slice, what each affected diagram **currently contains** (read from its source file, with element ids) and the change the slice's docs require.

How the sources were read: draw.io files were decoded and every cell's label and every edge's endpoints listed. Where an edge end is not attached to a shape (a free point), the shape or bus it touches was computed from the stored coordinates; bus arrows are 25 px wide, so a free end within about 13 px of a bus's centre line lies on the bus. Arrowheads are read from each edge's `startArrow` / `endArrow` style. Nothing here is inferred from a rendered image.

Status: **open** (the diagram still needs the change) or **done** (the user has updated it).

---

## Slice A (phase 3): IR at TP2, PC increment at TP1, EA page from MA

### `diagrams/microarchitecture/cpu-architecture/source/CPU_Architecture.xml`

| # | Current content (source) | Required change | Doc | Status |
|---|---|---|---|---|
| A1 | IR's only connection to a data source is edge `2Ph0Qde3JH9-hkXoXRvS-128`: IR to the IDB's right leg (free end at (990, 1210); IDB vertical at x = 970), arrowheads at both ends, IDB colour `#9673a6`. No MB → IR or MDB → IR edge exists. | Add **MDB → IR** (IR's load input is MDB, at FETCH TP2). The IR–IDB edge should show only **IR → IDB** (IR is an IDB source, `IDB_SRC` = 6); IR no longer loads from the IDB. | `01-registers.md` IR; `02-dataflow-and-bus-model.md` §3; `02-micro-operations.md` `MDB_TO_IR` | open |
| A2 | The EA unit's inputs: edge `cX9REWVKWh3u19Wi5yly-9` IR → EA_ADDR (enters EA_ADDR at the bottom centre). No edge from PC or MA to EA_ADDR; the page source is not drawn. | Add **MA → EA_ADDR** for the page bits (MA[11:7]); the IR → EA_ADDR edge carries IR[6:0] and the page bit. | `01-registers.md` MA, EA_ADDR; `02-micro-operations.md` `IR_ADDR_TO_EA_ADDR` | open |

Unchanged and verified: MB ↔ MDB (`2Ph0Qde3JH9-hkXoXRvS-151`, both arrowheads), MB ↔ IDB (`cX9REWVKWh3u19Wi5yly-25`), PC → MA (`…-158`), EA_ADDR → MA (`…-157`), PC → AB and MA → AB (`cX9REWVKWh3u19Wi5yly-1`, `2GY4jtORsDWkwOyoSZJb-18`, both ending on the AB arrow), PC → ALU A and B (`…-139`, `…-144`). The PC increment still goes through the ALU, so no PC-path change. The instruction fetch now addresses memory from MA (`AB_SRC = MA`, direct-control §4.3.1), which the existing MA → AB edge covers; PC → AB stays in use for console EXAMINE and DEPOSIT (§4.2), so neither AB edge changes.

### Checked, no slice A change

| Diagram | What the source contains | Why unchanged |
|---|---|---|
| `diagrams/timing/cpu-timing/source/cpu-timing-overview.json` | WaveDrom: 20 MHz clock, TS1 to TS4 = 6, 9, 7, 6 steps, TP1 to TP4 pulses; no register events | Shows no IR, PC, or EA events. Its TS lengths change in slice D |
| `diagrams/isa/addressing-model/source/addressing-model.xml` | Flowchart: `EA_addr = PC[11:7] \|\| Address Offset` for P = 1 | ISA view: PC is the instruction's address, as in `docs/02-isa`, which is unchanged |
| `diagrams/control/control-store-mapping/source/control-store-mapping.xml` | IR[12 bits] → Mapping ROM[8 bits] → MAPR (clocked by TP1 to TP4) → the three EXECUTE multiplexers | MAPR's clocking is unchanged; only the correctness argument in CSO §5.4.3 changed |
| `diagrams/architecture/class-a-buses/source/class-a-buses.xml` | CPU, Memory, I/O Device, DMA Device blocks on AB, MFB, MDB, DB | System level; no register detail |
| `diagrams/architecture/High-Level-Architecture/source/High-Level-Architecture.xml`, `control-store-address-formation.xml`, `control-store-organization.xml`, `control-store-overlay.xml`, `ms_next-flowchart.xml`, `io_subsystem.xml`, `io/*.json` | No IR source, PC increment, or EA page elements | Not touched by slice A |

---

## Later slices

Entries are added when each slice's docs are written, after reading the sources again. The spec's expected list ([spec.md](spec.md) §9) is a forecast, not yet checked against the sources.
