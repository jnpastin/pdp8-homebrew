# Control Output Extractor

## 1. Purpose

This tool extracts candidate control-output definitions from the authoritative control-output documentation.

It provides a deterministic, machine-readable representation of:

- indexed control outputs and their index categories
- documented scalar attributes
- normalized bit widths
- enumerated octal encodings
- control-word value requirements: default value, explicit-value requirement, and the condition requiring a value
- per-signal constraints
- the micro-operations documented as using each signal
- source traceability
- extraction diagnostics

The generated output is review material. It is not an authoritative control specification or maintained microcode source.

## 2. Authoritative Inputs

The tool reads exactly these maintained documents:

```text
docs/04-control/20-control-output-definitions/00-index.md
docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md
docs/04-control/20-control-output-definitions/02-architectural-control-signals.md
docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md
```

Unrestricted Markdown discovery is intentionally not used.

The explicitly enumerated source list:

- prevents unrelated Markdown files from becoming accidental inputs
- makes the extraction boundary reviewable
- detects missing authoritative documents
- preserves deterministic processing order

All source documents must reside under the supplied repository root. Source files outside the repository are not supported because generated source references are stored as repository-relative paths.

The source Markdown remains authoritative.

## 3. Signal Categories

Each indexed signal takes its category from the index heading above it. The current index uses:

| Index section | Categories |
|---|---|
| Microarchitectural Control Signals | Enable Signals, Select Signals, Data Value Signals |
| Architectural Control Signals | Memory Interface, I/O Interface |
| Sequencing Control Signals | Control Flow |

Categories are taken from the index headings as written. An entry before the first category heading has the category `uncategorized`.

Two categories carry structural rules (section 8):

- `Enable Signals` must be one bit wide and document encodings.
- `Select Signals` and `Control Flow` must document encodings.

## 4. Source Document Conventions

The parser is deliberately strict. Documentation that departs from these conventions produces diagnostics or is silently not extracted, so authors of the source documents should follow them exactly.

### 4.1 Common Text Normalization

Names, attribute values, and extracted text have Markdown escapes (`\_`, `\[`, `\]`) and inline-code backticks removed, and surrounding whitespace stripped. Heading section numbers such as `3.` or `4.2` are ignored.

### 4.2 Index

- Each level-three (`###`) heading names the category of the entries that follow it.
- Each indexed signal is a list item linking to an anchor in one of the three definition documents:

  ```text
  - [AC_LOAD](./01-microarchitectural-control-signals.md#ac_load)
  ```

- Links to other files, and links without a `#` anchor, are not index entries.

### 4.3 Definitions

- Definitions are read only from the section of each definition document headed `## Signal Definitions`, ignoring any section number. The section ends at the next level-two heading.
- Each definition begins at a level-three heading whose text is either the indexed name or ends with the indexed name in parentheses:

  ```text
  ### AC_SRC
  ### 4.1 Next Major State (MS_NEXT)
  ```

- A definition ends at the next level-three heading or the end of the section. Deeper headings are part of the definition.
- A level-three heading in the section that does not name an indexed signal is reported as `UNINDEXED_DEFINITION`.

### 4.4 Scalar Attributes

A scalar attribute is a bold label at the start of a line, followed by its value on the same line. Labels are case-insensitive, and the colon may be inside or outside the bold markers or omitted. A label whose value is on the next line is not read.

| Label | Attribute |
|---|---|
| `**Mnemonic:**` | `mnemonic` |
| `**Name:**` | `display_name` |
| `**Class:**` | `signal_class` |
| `**Type:**` | `signal_type` |
| `**Domain:**` | `domain` |
| `**Bit Width:**`, `**Width:**` | normalized into `bit_width` |
| `**Polarity:**` | `polarity` |
| `**Purpose:**` | `purpose` |
| `**Description:**` | `description` |
| `**Default Value:**` | `default_value` |
| `**Explicit Value Required:**` | `explicit_value_required` |
| `**Value Required When:**` | `value_required_when` |

Other bold labels are not scalar attributes.

### 4.5 Sections

Multi-line content follows one of these labels:

| Label | Content |
|---|---|
| `**Encoding:**`, `**Value Encoding:**` | encoding lines (section 6), including one on the label line |
| `**Constraints:**` | each list item is one constraint |
| `**Used by μops:**`, `**Used by uops:**` | list items `- [NAME](target) = value`, `- NAME = value`, or either without `= value` |

A section ends at the next line-leading bold label that is not one of its own labels. Later occurrences of its label in the same definition are then not read. Within constraint and micro-operation sections, lines that are not list items are ignored.

Nested list items are read as separate entries. For example, both lines of

```text
- Field-merge encodings preserve other AC bits:
  - IF → AC[5:3]
```

become separate constraints.

## 5. Extracted Representation

For each indexed control output, the generated representation contains:

- indexed signal name
- index category
- definition heading
- documented scalar attributes, with control-word values normalized
- normalized bit width
- enumerated encodings
- documented constraints
- micro-operations that use the signal, with the value each one assigns
- index source location
- definition source location
- encoding, constraint, and micro-operation source locations
- extraction status

Attributes are included only when documented. Missing attributes must not be invented.

The JSON layout is described in section 10.

## 6. Encodings

An encoding line has the form `value SEPARATOR meaning`, optionally as a `- ` list item, where the separator is `->`, `→`, `=`, or `:`. The value is a run of letters and digits.

```text
0 → IDB
- 1: load
2 = pending write
```

Code-fence markers and blank lines in an encoding section are skipped.

Some fields describe their values in prose rather than listing encodings. These lines are accepted without producing encodings:

- value ranges such as `0-7777 (octal)`
- `external bus value` and `memory bus value`
- `where:`
- bit-slice expressions, meaning any line containing `[`

A heading or bold line that is not an encoding ends the section. Any other unparsable line is reported as `MALFORMED_ENCODING`.

Encoding values are octal. When the bit width is known, each value must be valid octal and fit the width. The extractor records values exactly as written and does not store a converted numeric form.

## 7. Control-Word Attributes

Every definition must document:

| Attribute | Accepted values |
|---|---|
| Default Value | `N/A`, or an octal value that fits the bit width |
| Explicit Value Required | `Yes`, `No`, or `Conditionally`, case-insensitive |
| Value Required When | a non-empty condition |

A `Conditionally` field must give a real condition, not `Always` or `N/A`. A `Yes` or `Conditionally` field must have an encoded default, not `N/A`.

Default Value is checked, including the `N/A` rule above, only when the bit width is known.

In the JSON, Explicit Value Required is written in its normalized form, and Default Value is normalized when the bit width is known. An invalid value becomes `null`.

## 8. Validation

The implementation validates:

- all required source files exist
- all source files are valid UTF-8
- the index lists at least one signal, without duplicates
- every indexed signal has exactly one definition
- every definition heading names an indexed signal
- scalar attributes are not documented twice
- a bit width and a purpose or description are documented
- documented bit widths are positive integers, optionally followed by `bit` or `bits`
- documented mnemonics agree with indexed names
- the control-word attributes in section 7 are present and valid
- encoding lines are well formed and their values are not duplicated
- encoding values are octal and fit the bit width
- enable signals are one bit wide; for them a missing bit width is an error, not only the `MISSING_BIT_WIDTH` warning
- enable, select, and control-flow signals document encodings
- source traceability is retained

Diagnostics identify:

- severity
- diagnostic code
- signal name, when applicable
- source file
- source line, when available
- explanatory message

Most findings are `ERROR`. These findings are `WARNING` and do not fail the run:

| Code | Meaning |
|---|---|
| `UNINDEXED_DEFINITION` | a definition heading does not name an indexed signal and is skipped |
| `MISSING_BIT_WIDTH` | a definition does not document a bit width |
| `MISSING_DESCRIPTION` | a definition documents neither a purpose nor a description |
| `MALFORMED_ENCODING` | an encoding line could not be parsed and is skipped |

## 9. Validation Boundary

The extractor does not determine whether:

- the documented signal behavior is architecturally correct
- the documented constraints are mutually consistent
- constraint text describes an enforceable rule; constraints are preserved as text only
- the listed micro-operations exist or assign valid encodings
- the control outputs are sufficient to implement the micro-operation catalog
- control outputs can be combined into a valid control word

The extractor does not assign:

- control-word bit positions
- physical ROM positions
- micro-operation mappings
- direct control-event mappings
- sequencing behavior
- control-address fields

Those decisions belong to later ROM-generation stages.

## 10. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── control-output-extractor/
            ├── control-outputs.json
            └── extraction-report.txt
```

Generated files:

- must not be edited manually
- must not be treated as authoritative source
- should not be committed to version control
- may be deleted and regenerated
- must be regenerated after relevant documentation changes

The repository-level `.gitignore` excludes the `build/` directory.

### 10.1 JSON Output

`control-outputs.json` is consumed by the control-word schema generator, so changes to its layout must be coordinated with that tool.

The JSON and the report follow the shared ROM-generation output format (`tools/rom-generation/README.md`, section 15.1): UTF-8, LF line endings, one trailing newline, two-space indentation, non-ASCII characters written directly, and object keys in the fixed order the tool builds them, as listed in the tables below.

Top-level fields:

| Field | Content |
|---|---|
| `format_version` | `1` |
| `extraction_stage` | `"category-validation"` |
| `signals` | one object per indexed signal, in index order |
| `diagnostics` | all diagnostics, in the order described below |

Each `source` object below is `{"path": ..., "line": ...}`, using the repository-relative path and 1-based line number.

Signal fields:

| Field | Content |
|---|---|
| `name`, `category` | from the index |
| `definition` | the definition object below, or `null` when no definition matched |
| `source` | location of the index entry |
| `extraction_status` | `"category-validated"`, or `"definition-missing"` when `definition` is `null` |

Definition fields:

| Field | Content |
|---|---|
| `heading` | the definition heading, without its section number |
| `attributes` | scalar attributes from section 4.4 in source order, excluding bit width; see section 7 for normalization |
| `bit_width` | integer, or `null` if missing or invalid |
| `encodings` | list of `{"value", "meaning", "source"}` |
| `constraints` | list of `{"text", "source"}` |
| `used_by_micro_operations` | list of `{"micro_operation", "source", "value"}`; `value` is omitted when not documented |
| `source` | location of the definition heading |

Diagnostic fields are `severity`, `code`, `message`, `source_path`, `line`, and `signal_name`. The last three may be `null`. Diagnostics are ordered by severity (`INFO`, `WARNING`, `ERROR`, `FATAL`), then by code, source path, line, signal name, and message.

### 10.2 Extraction Report

`extraction-report.txt` is a human-readable summary containing:

- extraction counts
- diagnostic counts by severity
- every diagnostic with its source location

## 11. Command-Line Interface

The tool requires the repository root:

```text
--repo-root REPOSITORY_PATH
```

Optional arguments override the default output locations:

```text
--json-output OUTPUT_PATH     default: <output directory>/control-outputs.json
--report-output OUTPUT_PATH   default: <output directory>/extraction-report.txt
```

The default output directory is `build/simulation_outputs/rom-generation/control-output-extractor/`.

Relative output paths are resolved from the supplied repository root. Absolute output paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics.

The tool exits with status `1` when the repository root or a source file is missing or unreadable, or when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise. When the repository root or a source file is missing or unreadable, no output files are written.

## 12. Running the Tool

Run the tool from the repository root:

```text
python tools/rom-generation/control-output-extractor/src/extract_control_outputs.py --repo-root .
```

The tool may be run from any working directory by supplying the applicable repository root:

```text
python path/to/extract_control_outputs.py --repo-root path/to/repository
```

The `python` command may be replaced by the applicable local Python 3 launcher.

## 13. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/control-output-extractor/tests -p "test_*.py"
```

The tests use inline document content and temporary directories. Unit tests are grouped by pipeline stage; end-to-end tests write a small four-document repository to a temporary directory and run `main()` against it.

Two end-to-end tests compare the complete JSON and report with expected files under `tests/golden/`:

- `valid/`: the four-document repository, which extracts without diagnostics
- `invalid/`: the same repository with defects that produce warnings and errors in several files, which fixes diagnostic order

After an intentional output change, regenerate the golden files from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/control-output-extractor/tests -p "test_*.py"
```

On Windows PowerShell, set the variable first with `$env:UPDATE_GOLDEN = "1"` and remove it afterwards.

The golden files are expected outputs, not source fixtures. A persistent fixture directory is not used. It should be added only if multiple tests require the same representative source documents and inline content becomes harder to maintain.

Tests should cover representative behavior rather than every possible input permutation.

## 14. Implementation Constraints

The implementation must:

- use only the Python standard library
- support multiple operating systems
- avoid shell-specific behavior
- use repository-relative source references
- emit deterministic output
- preserve source ordering
- preserve source traceability
- report malformed documentation without inventing replacement values
- keep extraction separate from control-word design
- remain proportional to the tool's bounded purpose

Shared code must not be moved into the ROM-generation `common/` directory until actual duplicated requirements exist and a stable common interface can be identified.

## 15. Implementation Structure

The implementation is a single module, `src/extract_control_outputs.py`, organized in pipeline order:

1. **Command line and loading:** parse arguments, resolve paths, require the repository root and all sources, and read them as UTF-8.
2. **Index:** parse `00-index.md` into entries carrying name and category.
3. **Definition blocks:** split the Signal Definitions section of `01`–`03` into heading blocks and match blocks to entries.
4. **Per-signal extraction:** read each block's scalar attributes, bit width, encodings, constraints, and micro-operation uses into one `SignalDefinition`.
5. **Per-signal validation:** check required attributes, mnemonic, control-word attributes, encoding widths, and category rules.
6. **Output:** sort diagnostics, then write the JSON and the report.

Recognized Markdown labels, control-word values, and category rules are kept in tables near the top of the module.

`extract_control_outputs()` performs steps 2–5 on loaded documents without file access. `main()` handles loading, writing, and console output.

## 16. Completion Boundary

The control-output extractor is complete when it can:

- read the four authoritative control-output documents
- extract every indexed signal with its category
- extract documented attributes, bit widths, encodings, constraints, and micro-operation uses
- validate control-word attributes and category rules
- retain source traceability
- produce deterministic JSON
- produce a human-readable report
- report no unresolved structural errors against the authoritative documentation
- pass the targeted unit-test suite

The resulting JSON remains generated review material.

New behavior belongs in this tool only when it concerns extracting or structurally validating documented control-output definitions. Control-word layout, micro-operation mapping, and ROM generation belong to later tools, starting with the control-word schema generator.
