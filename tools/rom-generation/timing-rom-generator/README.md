# Timing ROM Generator

## 1. Purpose

The generator produces the timing ROM image ([Timing Terminology §3.5](../../../docs/09-timing/01-terminology.md#35-timing-rom)) from the documented TS lengths. The timing ROM gives each timing state's setup length and TP width; TSEQ sets TP after the setup length and holds it for the TP width.

## 2. Inputs

| Source | What is read |
|---|---|
| [Timing Architecture §5.1](../../../docs/09-timing/02-timing-architecture.md#51-structure) | the TS-length table (contexts, and the TS1/TS2/TS3/TS4 lengths with their stated total for each mode) and the table of timing states with a two-step TP |
| [Control Store Organization §5.1](../../../docs/04-control/08-control-store-organization.md#51-major-state-and-timing-state-codes) | the major-state codes (`FETCH = 0` …) |

A table's first column names contexts, separated by semicolons: a major state, optionally qualified by `AUTO_INDEX_REQUIRED = 0` or `1`. The console transaction row of the two-step table is skipped: the console transaction timer, not the ROM, times it.

## 3. Image

Layout (Timing Terminology §3.5):

| Address bits | Input |
|---|---|
| A7–A5 | `MS_EFF` |
| A4–A3 | TS code (TS − 1) |
| A2 | `AUTO_INDEX_REQUIRED` |
| A1–A0 | `TIMING_MODE` |
| A14–A8 | 0 |

| Data bits | Content |
|---|---|
| D2–D0 | setup length (TS length − TP width) |
| D3 | TP width − 1 |
| D7–D4 | 0 |

A context that does not name `AUTO_INDEX_REQUIRED` gets the same entries for both values. The reserved `TIMING_MODE` codes 2 and 3 repeat mode 1. `MS_EFF` codes that are not major states (5, 6, and 7, `HALTED`) hold EXECUTE's mode-1 TS lengths with one-step TPs. Addresses with A14–A8 not zero hold 0.

## 4. Outputs

Under the design's build directory, in `timing-rom-generator/`:

| File | Contents |
|---|---|
| `images/timing.hex` | one byte per line, two hex digits, 32768 lines, address 0 first |
| `timing-rom.json` | every documented entry: major state, `AUTO_INDEX_REQUIRED`, mode, TS, TS length, TP width, setup length, byte |
| `generation-report.txt` | status, the entries, diagnostics |

Earlier outputs are removed first. The image and JSON are written only when no error is found.

## 5. Diagnostics

| Code | Meaning |
|---|---|
| `MISSING_SOURCE` | a source document cannot be read |
| `MISSING_SECTION` | Timing Architecture §5.1 is not found |
| `UNKNOWN_CONTEXT` | a context is not a major state |
| `UNREADABLE_LENGTHS` | a length cell is not `a/b/c/d = total` |
| `TOTAL_MISMATCH` | a cell's lengths do not add up to its stated total |
| `MISSING_LENGTHS` | a major state, or one of its modes, has no lengths |
| `MISSING_MS_CODE` | a major state has no code in Control Store Organization §5.1 |
| `SETUP_OUT_OF_RANGE` | a setup length does not fit D2–D0 (1 to 7) |

All are errors.

## 6. Command Line

```text
python tools/rom-generation/timing-rom-generator/src/generate_timing_rom.py --repo-root .
```

The pipeline runs it after the control-store packer. It is not run for a frozen design.

## 7. Testing

```text
python -m unittest discover -s tools/rom-generation/timing-rom-generator/tests -p "test_*.py"
```

The tests cover the layout, every documented entry, the `AUTO_INDEX_REQUIRED`, reserved-mode, and unused-state rules, each diagnostic, and the repository's own documentation, including the 76-TSTEP ISZ + JMP loop of Timing Architecture §5.1.
