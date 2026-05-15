# Diagrams

## Purpose

This directory contains all visual diagrams used throughout the documentation.

Diagrams provide visual support for:
- System structure
- Execution behavior
- Timing and sequencing
- Interface relationships

They are supplemental to the written documentation and must remain consistent with it.

---

## Structure

Diagrams are organized by functional domain rather than by document structure.

Example:

diagrams/
  timing/
    cpu-timing/
      source/
      export/
    major-state/
      source/
      export/
  architecture/
  buses/

### Organization Rules

- Top-level folders represent system domains (timing, architecture, etc.)
- Subfolders represent specific topics or diagram sets
- Each diagram set contains:
  - source/ → editable diagrams (e.g., .wavedrom, .drawio)
  - export/ → rendered diagrams for documentation (e.g., .png, .svg)

---

## Usage

### Referencing in Documentation

Documentation must reference diagrams from the export directory.

Example:

../../diagrams/timing/cpu-timing/export/cpu-timing-overview.png

---

### Source of Truth

- Files in source/ are authoritative and editable
- Files in export/ are generated artifacts used in documentation

---

### Update Workflow

When modifying a diagram:

1. Update the file in source/
2. Regenerate the corresponding file in export/
3. Verify documentation references remain valid

---

## Naming Conventions

Diagram files must follow:

<domain>-<topic>-<purpose>

Examples:
- cpu-timing-overview
- fetch-cycle
- memory-read-cycle

Avoid:
- diagram1
- test
- final_v2

---

## Design Principles

- Diagrams must reflect documented behavior, not assumptions
- Diagrams must not introduce new semantics that are not defined in documentation
- Timing diagrams must follow established conventions:
  - TS signals represent states (windows)
  - TP signals represent events (explicitly marked)
- Diagrams must be interpretable without implicit assumptions

---

## Notes

- Diagrams are visual representations of the design, not the design itself
- If a diagram conflicts with documentation, the documentation is authoritative
- Diagrams must be updated alongside changes to the corresponding specification
