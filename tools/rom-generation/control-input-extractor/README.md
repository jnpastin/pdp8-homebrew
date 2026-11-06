# Control Input Extractor

## 1. Purpose

This tool extracts structured control-input information from the authoritative control-input documentation.

It provides a deterministic, machine-readable representation of:

- primitive flags
- IR-derived signals
- derived flags
- external inputs
- documented input attributes
- value encodings
- derivations and dependencies
- per-input constraints
- global constraints spanning several inputs
- consumed-by and used-by references
- source traceability
- extraction diagnostics

The generated output is review material. It is not an authoritative control-address specification or maintained microcode source.

## 2. Authoritative Inputs

The tool reads exactly these maintained documents:

```text
docs/04-control/10-control-input-definitions/00-index.md
docs/04-control/10-control-input-definitions/01-flags.md
docs/04-control/10-control-input-definitions/02-ir-derived-fields.md
docs/04-control/10-control-input-definitions/03-derived-flags.md
docs/04-control/10-control-input-definitions/04-external-inputs.md
```

Unrestricted Markdown discovery is intentionally not used.

The explicitly enumerated source list:

- prevents unrelated Markdown files from becoming accidental inputs
- makes the extraction boundary reviewable
- detects missing authoritative documents
- preserves deterministic processing order

All source documents must reside under the supplied repository root. Source files outside the repository are not supported because generated source references are stored as repository-relative paths.

The source Markdown remains authoritative.

## 3. Input Domains

The authoritative index partitions control inputs into four disjoint domains:

1. Primitive Flags
2. IR-Derived Signals
3. Derived Flags
4. External Inputs

Each indexed input must belong to exactly one domain.

The extractor preserves these domains. It must not collapse all control inputs into a generic flag classification.

Index subsections may provide additional categories within a domain. The current index uses:

| Domain | Categories |
|---|---|
| Primitive Flags | none |
| IR-Derived Signals | IR Class Flags, Instruction Selection, Addressing Mode, OPR Class, OPR Bit Flags, Memory Management Flags, Field Extraction Signals |
| Derived Flags | none |
| External Inputs | Front Panel Commands, Front Panel Modes, Front Panel Data, External Requests, External IOT Response Inputs |

Categories are taken from the index headings as written. They are preserved as indexed metadata and do not replace the four top-level domains. An input without a category has a `null` category.

## 4. Source Document Conventions

The parser is deliberately strict. Documentation that departs from these conventions produces diagnostics or is silently not extracted, so authors of the source documents should follow them exactly.

### 4.1 Common Text Normalization

Names, attribute values, and extracted text have Markdown escapes (`\_`, `\[`, `\]`) and inline-code backticks removed, and surrounding whitespace stripped. Heading section numbers such as `3.` or `4.2` are ignored.

### 4.2 Index

- A domain begins at a heading whose text, ignoring case and section number, is one of the four domain names in section 3.
- Any deeper heading within a domain names a category.
- A heading at the same level as the domain heading, or shallower, ends the domain.
- Each indexed input is a list item linking to an anchor in a Markdown file:

  ```text
  - [NAME](./01-flags.md#anchor)
  - [NAME](./01-flags.md#anchor) - optional description
  ```

- Links without a `.md#` anchor, such as links to whole documents, are not index entries.

### 4.3 Definitions

- Each definition in `01`–`04` begins at a level-three (`###`) heading whose text is either the indexed name or ends with the indexed name in parentheses:

  ```text
  ### ACN
  ### 4.1 Start Command (FP_START)
  ```

- A definition ends at the next heading of level three or shallower.
- Level-three headings that do not name an indexed input are ignored.
- Deeper headings inside a definition are not part of its content.

### 4.4 Scalar Attributes

Scalar attributes use a bold label followed by a value. Labels are case-insensitive, the colon may be inside or outside the bold markers, and several attributes may share one line.

| Label | Attribute |
|---|---|
| `**Mnemonic:**` | `mnemonic` |
| `**Name:**` | `display_name` |
| `**Type:**` | `input_type` |
| `**Bit Width:**` | normalized into `bit_width` |
| `**Polarity:**` | normalized into `polarity` |
| `**Purpose:**` | `purpose` |
| `**Source Register:**` | `source_register` |

Other bold labels are not scalar attributes.

### 4.5 Sections

Multi-line content follows one of these labels:

| Label | Content | Ends at |
|---|---|---|
| `**Value Encoding:**` | `- value → meaning` list items (section 7) | next bold label |
| `**Inputs:**` | `- NAME` list items, one per dependency | next bold label |
| `**Derivation:**`<br>`**Expression:**`<br>`**Internal Composition (local to this definition):**` | text on the label line and following lines; code-fence markers are dropped | next bold label or `---`, outside a code fence |
| `**Constraint:**`<br>`**Constraints:**` | each list item is one constraint; prose lines, including text on the label line, are joined into one constraint | next bold label or `---` |
| `**Consumed By:**`<br>`**Used By μops:**`<br>`**Used By uops:**` | list items, either a link `- [TEXT](target)` or plain text | next bold label or `---` |

Within a section, lines that are not list items are ignored, except in logic and constraint sections. When a section ends at an unrelated bold label, later occurrences of its label in the same definition are not read. When a section ends at `---`, a later occurrence of its label may start another section.

### 4.6 Global Constraints

Global constraints are nested list items, indented at least two spaces, in any of the five documents:

```text
- Instruction classes:
  - `EXACTLY_ONE(IR_IS_MRI, IR_IS_IOT, IR_IS_OPR)`
  - `AT_MOST_ONE(IR_OPR_GROUP1, IR_OPR_GROUP2, IR_OPR_GROUP3)`
```

The backticks are optional. Top-level list items are not read as global constraints.

## 5. Extracted Representation

For each indexed control input, the generated representation contains:

- indexed signal name
- indexed domain
- indexed category, when present
- applicable documented scalar attributes
- normalized bit width
- normalized polarity
- polarity provenance
- enumerated values or a bounded value range
- explicitly documented dependencies
- derivation, expression, or internal-composition text, when applicable
- documented constraints
- consumed-by and used-by references
- index source location
- definition source location
- value source locations
- dependency source locations
- logic-section source locations
- constraint source locations
- consumer source locations
- extraction status

Scalar attributes are included only when applicable to the input definition. Missing optional attributes must not be invented.

The JSON layout is described in section 12.

## 6. Polarity

Control-input polarity follows the project-wide convention:

- explicitly documented polarity is preserved
- active-low signal names beginning with `/` are interpreted as active-low
- when polarity is not otherwise specified, the signal is active-high

Accepted explicit values, case-insensitive, are `active-high`, `active high`, `active-low`, and `active low`. Any other documented value is reported as `INVALID_POLARITY` and the signal's polarity is `null`.

The generated representation records both:

- the normalized polarity
- whether the polarity was explicit, name-derived, or defaulted

Defaulting an unspecified polarity to active-high is a defined project rule, not an inferred documentation value.

## 7. Value Representation

Control inputs use two distinct value-description forms. Each definition must use exactly one of them.

Value lines are list items of the form `value SEPARATOR meaning`, where the separator is `->`, `→`, or `:`.

### 7.1 Enumerated Values

Enumerated values list individual encodings and meanings.

Example:

```text
- 0 -> inactive
- 1 -> active
```

The extractor records each value and its description separately. A value listed twice is reported.

### 7.2 Ranges

Range declarations describe a bounded set without enumerating every value. The endpoints are separated by `-` or `–`.

Example:

```text
- 000-111 -> field value
```

The extractor preserves:

- range start
- range end
- value description
- source location

A range must not be expanded into every individual value during extraction.

### 7.3 Numeric Interpretation

Values and range endpoints are binary.

The extractor records each value exactly as written. It does not store a converted numeric form.

For validation only, values are read as binary to check that they fit the normalized bit width and that a range's start does not exceed its end. Values that are not binary are reported as `INVALID_BINARY_VALUE` or `INVALID_BINARY_RANGE`. The extractor never interprets digit strings as octal or hexadecimal.

Meanings are free text and may describe octal or other notations. They are not interpreted.

## 8. Derivations and Dependencies

Primitive flags, IR-derived signals, and derived flags may document how their values are formed.

The extractor preserves:

- derivation text
- expression text
- internal-composition text
- explicitly listed dependencies
- explicitly identified source registers
- source traceability

Derived flags must provide an explicit dependency list. Each listed dependency must match an indexed control input.

IR-derived signals must provide a derivation. Derived flags must provide an expression or internal composition.

Structural validation verifies that applicable derivations and derived logic assign the indexed signal name, meaning some line of the text begins with `NAME =`. For a derived flag with both an expression and an internal composition, the expression is checked.

The extractor does not:

- execute expressions
- prove logical equivalence
- simplify Boolean logic
- determine redundancy
- synthesize combinational logic
- infer dependencies that are not explicitly documented
- compare expression identifiers against the documented dependency list

## 9. Global Constraints

Global constraints record relationships between several control inputs:

| Source form | `kind` | Meaning |
|---|---|---|
| `EXACTLY_ONE(A, B, ...)` | `exactly_one` | exactly one of the inputs is active |
| `AT_MOST_ONE(A, B, ...)` | `at_most_one` | no more than one of the inputs is active |

Each global constraint must name at least two inputs, every input must be indexed, and the same constraint must not appear twice.

The extractor records these relationships. It does not check that the documented derivations satisfy them. Later stages, starting with the control-input schema generator, consume them.

## 10. Validation

The implementation validates:

- all required source files exist
- all source files are valid UTF-8
- every indexed input has exactly one definition
- index entries and definition blocks are not duplicated
- indexed domains and categories are preserved
- scalar attributes are not documented twice
- required scalar attributes are present and non-blank by domain
- documented mnemonics agree with indexed names for IR-derived signals and derived flags
- documented bit widths are positive integers, optionally followed by `bit` or `bits`
- primitive and derived flags default to one bit when width is omitted
- IR-derived and external inputs document their widths
- documented polarity uses an accepted value
- active-low names do not conflict with normalized polarity
- every definition contains either enumerated values or a bounded range
- definitions do not mix enumerated values and ranges
- value declarations are well formed
- enumerated values are not duplicated
- values and range endpoints are binary
- ranges are not reversed
- values and ranges fit the normalized bit width
- derived flags document at least one dependency
- dependencies are not duplicated and refer to indexed control inputs
- required logic sections are present
- logic sections are not empty or duplicated
- derivations and derived logic assign the indexed signal
- global constraints are well formed, refer to indexed inputs, and are not duplicated
- source traceability is retained

Required scalar attributes by domain:

| Domain | Required attributes |
|---|---|
| Primitive Flags | `display_name`, `purpose`, `source_register` |
| IR-Derived Signals | `display_name`, `input_type`, `mnemonic`, `purpose` |
| Derived Flags | `display_name`, `mnemonic`, `purpose` |
| External Inputs | `display_name`, `input_type`, `purpose` |

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
| `INDEX_ENTRY_WITHOUT_DOMAIN` | an index entry appears outside any recognized domain and is skipped |
| `UNINDEXED_DEFINITION` | a definition does not match an indexed input |
| `MALFORMED_VALUE_ENCODING` | a value-encoding list item could not be parsed and is skipped |

## 11. Validation Boundary

The extractor does not validate whether:

- a documented derivation is logically correct
- two derivations are logically equivalent
- a flag is actually minimal or nonredundant
- a documented input is required by control behavior
- an indexed input belongs in the final control address
- the complete control-input space is sufficient
- the documented control rules are architecturally correct
- all reachable control cases are distinguishable
- control-address aliases are valid
- control-word permutations are complete
- documented derivations satisfy the global constraints

Those checks belong to later ROM-generation stages.

## 12. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── control-input-extractor/
            ├── control-inputs.json
            └── extraction-report.txt
```

Generated files:

- must not be edited manually
- must not be treated as authoritative source
- should not be committed to version control
- may be deleted and regenerated
- must be regenerated after relevant documentation changes

The repository-level `.gitignore` excludes the `build/` directory.

### 12.1 JSON Output

`control-inputs.json` is consumed by the control-input schema generator, so changes to its layout must be coordinated with that tool.

The JSON is UTF-8, indented by two spaces, written with object keys sorted, and ends with a newline. Characters such as `μ` and `→` are written directly, not escaped.

Top-level fields:

| Field | Content |
|---|---|
| `format_version` | `1` |
| `extraction_stage` | `"final-structure-validation"` |
| `sources` | the five repository-relative source paths, in processing order |
| `signals` | one object per indexed input, in index order |
| `constraints` | global constraints, in source order |
| `diagnostics` | all diagnostics, in the order described below |

Each `source` object below is `{"path": ..., "line": ...}`, using the repository-relative path and 1-based line number.

Signal fields:

| Field | Content |
|---|---|
| `name`, `domain`, `category` | from the index; `category` may be `null` |
| `attributes` | scalar attributes from section 4.4, excluding bit width and polarity |
| `bit_width` | integer, or `null` if missing or invalid |
| `polarity` | `{"value": "active-high" or "active-low", "source": "explicit", "name-derived", or "defaulted"}`, or `null` if invalid |
| `enumerated_values` | list of `{"value", "meaning", "source"}` |
| `value_ranges` | list of `{"start", "end", "meaning", "source"}` |
| `dependencies` | list of `{"name", "source"}` |
| `logic` | object keyed by `derivation`, `expression`, or `internal_composition`, each `{"text", "source"}` |
| `constraints` | list of `{"text", "source"}` |
| `consumers` | list of `{"text", "target", "source"}`; `target` is the link target or `null` for plain text |
| `definition_source` | `{"path", "line", "heading"}` for the definition heading |
| `index_source` | `source` of the index entry |
| `extraction_status` | `"structure-validated"` |

An indexed input with no matching definition is emitted with only `name`, `domain`, `category`, `index_source`, `"definition": null`, and `"extraction_status": "definition-missing"`.

Global constraint fields are `kind`, `inputs` (in source order), and `source`.

Diagnostic fields are `severity`, `code`, `message`, `source_path`, `line`, and `signal_name`. The last three may be `null`. Diagnostics are ordered by severity (`INFO`, `WARNING`, `ERROR`, `FATAL`), then by code, source path, line, signal name, and message.

### 12.2 Extraction Report

`extraction-report.txt` is a human-readable summary containing:

- extraction counts
- input counts by domain
- diagnostic counts by severity
- every diagnostic with its source location

## 13. Command-Line Interface

The tool requires the repository root:

```text
--repo-root REPOSITORY_PATH
```

Optional arguments override the default output locations:

```text
--json-output OUTPUT_PATH     default: <output directory>/control-inputs.json
--report-output OUTPUT_PATH   default: <output directory>/extraction-report.txt
```

The default output directory is `build/simulation_outputs/rom-generation/control-input-extractor/`.

Relative output paths are resolved from the supplied repository root. Absolute output paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics.

The tool exits with status `1` when a source file is missing or unreadable, or when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise. When a source file is missing or unreadable, no output files are written.

## 14. Running the Tool

Run the tool from the repository root:

```text
python tools/rom-generation/control-input-extractor/src/extract_control_inputs.py --repo-root .
```

The tool may be run from any working directory by supplying the applicable repository root:

```text
python path/to/extract_control_inputs.py --repo-root path/to/repository
```

The `python` command may be replaced by the applicable local Python 3 launcher.

## 15. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/control-input-extractor/tests -p "test_*.py"
```

The tests use inline document content and temporary directories. Unit tests are grouped by pipeline stage; end-to-end tests write a small five-document repository to a temporary directory and run `main()` against it.

A persistent fixture directory is not used. It should be added only if multiple tests require the same representative source documents and inline content becomes harder to maintain.

Tests should cover representative behavior rather than every possible input permutation.

## 16. Implementation Constraints

The implementation must:

- use only the Python standard library
- support multiple operating systems
- avoid shell-specific behavior
- use repository-relative source references
- emit deterministic output
- preserve source ordering
- preserve source traceability
- report malformed documentation without inventing replacement values
- keep extraction separate from control-address design
- remain proportional to the tool's bounded purpose

Shared code must not be moved into the ROM-generation `common/` directory until actual duplicated requirements exist and a stable common interface can be identified.

## 17. Implementation Structure

The implementation is a single module, `src/extract_control_inputs.py`, organized in pipeline order:

1. **Command line and loading:** parse arguments, resolve paths, require all sources, and read them as UTF-8.
2. **Index:** parse `00-index.md` into entries carrying name, domain, and category.
3. **Definition blocks:** split `01`–`04` into one block per indexed input and match blocks to entries.
4. **Global constraints:** read `EXACTLY_ONE` and `AT_MOST_ONE` bullets from all five documents.
5. **Per-signal extraction:** read each block's scalar attributes, bit width, polarity, values, dependencies, logic sections, constraints, and consumers into one `SignalDefinition`.
6. **Per-signal validation:** check required attributes, value form, value widths, dependencies, logic, and naming against the domain rules.
7. **Output:** sort diagnostics, then write the JSON and the report.

Domain-specific rules are kept in tables near the top of the module: required attributes, one-bit width defaults, mnemonic checks, and logic requirements. Recognized Markdown labels are kept in the same place.

`extract_control_inputs()` performs steps 2–6 on loaded documents without file access. `main()` handles loading, writing, and console output.

## 18. Completion Boundary

The control-input extractor is complete when it can:

- read the five authoritative control-input documents
- extract every indexed input
- preserve all four input domains
- preserve indexed subcategories
- normalize applicable attributes
- represent enumerated values and bounded ranges distinctly
- normalize explicit and defaulted polarity
- preserve derivations and dependencies
- preserve per-input and global constraints
- preserve linked and plain-text consumers
- retain source traceability
- produce deterministic JSON
- produce a human-readable report
- report no unresolved structural errors against the authoritative documentation
- pass the targeted unit-test suite

The resulting JSON remains generated review material.

Control-input permutation generation, behavioral reduction, control-address construction, and promotion into maintained ROM source belong to later tools.
