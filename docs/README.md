# Documentation

## 1. Purpose
This directory contains all human-readable design documentation for the system.

It serves as the authoritative source for:
- System behavior
- Architecture
- Design constraints

---

## 2. Structure

Before editing, read the [Documentation Conventions](./00-overview/97-documentation-conventions.md). Some of these documents are parsed to build the control store, and ordinary prose edits can change it.

- `00-overview` - High-level system overview and goals
- `01-architecture` - Programmer-visible machine model
- `02-isa` - Instruction set architecture
- `03-microarchitecture` - Execution model and micro-operations
- `04-control` - Control signals and state behavior
- `05-buses-and-signals` - Bus definitions and signal lists
- `06-memory` - Memory architecture and access model
- `07-io` - I/O system definition
- `08-interrupts-and-skip` - Interrupt and skip behavior
- `09-timing` - Clocking and timing model

The front panel, the backplane and physical design, verification, and the implementation plan are not yet written; their sections will be added when they are.

### 2.1 Reading Order

To learn the machine, read in this order:

1. [Overview](./00-overview/README.md): goals, principles, and status
2. [Architecture](./01-architecture/README.md): the programmer-visible registers and data paths
3. [ISA](./02-isa/README.md): what each instruction does
4. [Microarchitecture](./03-microarchitecture/README.md): how each instruction executes, major state by major state
5. [Control](./04-control/README.md): how the control store selects each control word
6. [Timing](./09-timing/README.md): TSTEP, TS, and TP, and how they commit state

Then, as needed: [buses and signals](./05-buses-and-signals/README.md), [memory](./06-memory/README.md), [I/O](./07-io/README.md), and [interrupts and skips](./08-interrupts-and-skip/README.md).

---

## 3. Rules

### 3.1 Separation of Concerns
Each section represents a distinct abstraction layer:

- ISA defines observable behavior
- Architecture defines the machine model
- Microarchitecture defines execution structure
- Control defines signal behavior
- Timing defines ordering of events
- Physical documents define implementation

Layers must not be conflated.

---

### 3.2 Single Source of Truth
Each concept is defined in exactly one location.

- Definitions must not be duplicated
