# Direct-Control Extractor

## 1. Purpose

The direct-control extractor creates a machine-readable representation of the documented direct-control definitions: control results that are not micro-operations, such as major-state sequencing, RUN and halt-request updates, memory-field selection, interface drive states, and ownership.

Each definition pairs an applicable context with the control results that hold in it. The extractor preserves the documented text of both; it does not turn prose into Boolean expressions or infer missing behavior.

## 2. Authoritative Inputs

The extractor reads exactly two maintained documents:

- [Sequencing and Internal Control](../../../docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md)
- [Interface and Ownership Control](../../../docs/04-control/30-direct-control-definitions/02-interface-and-ownership-control.md)

The documents remain authoritative. Their paths are fixed in the extractor, relative to the repository root.

## 3. Source Document Conventions

### 3.1 Definitions

Definitions are found by heading:

- Headings at levels 2 to 6 (`##` to `######`) are recognized. Lines inside code blocks are never headings.
- A heading is numbered when its text starts with a section number such as `3.2.1`, with or without a trailing dot.
- A numbered heading with no recognized heading directly nested under it is a candidate definition. A heading with nested headings is a grouping, not a definition.
- A definition's text runs to the next heading at its own level or above.
- A candidate becomes a definition only if it has at least one content section (section 3.3). Descriptive sections, such as a purpose statement, are ignored.

Unnumbered headings are never definitions, though they can group definitions.

A grouping heading's own sections, such as constraints shared by its subsections, are not attached to any definition.

### 3.2 Labels

Within a definition, a section starts at a label line: a line ending in a colon, such as `Applicable context:`. It runs to the next label line. Lines inside code blocks are never labels.

Any line ending in a colon that is not a recognized label, such as `Examples include:`, ends the current section without starting another. The text after it, up to the next recognized label, is not extracted. This keeps explanatory prose and examples out of the definition.

The one exception is `or:` (in any case) inside an applicable context. It separates alternative context blocks, so the section continues:

````markdown
Applicable context:

```text
IR_MRI_OPCODE = 000
```

or:

```text
IR_MRI_OPCODE = 001
```
````

Elsewhere, `or:` ends the section like any other unrecognized label.

A label may appear more than once; each occurrence adds to the same field.

### 3.3 Recognized Labels

| Label | Output field | Read as | Content section |
|---|---|---|---|
| `Applicable context` | `applicable_context` | code blocks, or the prose when there are none | no |
| `Assignment`, `Assignments` | `direct_assignments` | code blocks | yes |
| `Micro-operation assignments`, `Logical control results` | `micro_operation_assignments` | code blocks | yes |
| `Control-supplied value`, `Control-supplied values` | `control_supplied_values` | code blocks | yes |
| `Commit`, `Commits` | `state_commits` | code blocks | yes |
| `CPU output-drive state`, `CPU output-drive states`, `CPU behavior` | `drive_states` | code blocks | yes |
| `External ownership` | `external_ownership` | code blocks | yes |
| `Memory behavior` | `memory_behavior` | code blocks | yes |
| `Related derived values` | `derived_values` | code blocks | yes |
| `Value relationship`, `Value relationships` | `value_relationships` | code blocks | no |
| `Widths` | `widths` | code blocks | no |
| `Constraint`, `Constraints` | `constraints` | `- ` bullets, including nested ones | no |
| `Source`, `Sources` | `sources` | Markdown links | no |

Labels are matched exactly, including case.

### 3.4 Code Blocks

A code block is a ```` ``` ```` or ```` ```text ```` fence; blocks in other languages are not read. Each non-empty block becomes one value, with its text and indentation preserved and surrounding blank lines removed.

## 4. Extracted Representation

Each definition uses this structure. The example is shortened from the actual definition `01:3.3.7`:

```json
{
  "id": "01:3.3.7",
  "title": "3.3.7 Single Instruction Halt",
  "group": "3.3 Run-State Sequencing",
  "source": {
    "path": "docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md",
    "line": 637
  },
  "applicable_context": ["RUN = 1\nFP_SINGLE_INSTRUCTION = 1\nMS = EXECUTE\nTS = 4"],
  "direct_assignments": ["RUN_NEXT = 0"],
  "control_supplied_values": [],
  "micro_operation_assignments": [],
  "state_commits": ["RUN <- 0 at TP"],
  "value_relationships": [],
  "widths": [],
  "constraints": ["Single Instruction mode executes one complete instruction."],
  "sources": [
    {"label": "Console Execution", "target": "../../03-microarchitecture/09-console-execution.md#12-single-instruction-mode"}
  ],
  "drive_states": [],
  "external_ownership": [],
  "memory_behavior": [],
  "derived_values": []
}
```

| Property | Content |
|---|---|
| `id` | the file's numeric prefix and the heading number, such as `01:3.3.7` |
| `title` | the heading's number and title |
| `group` | the number and title of the enclosing heading, or `null` |
| `source` | the repository-relative document path and heading line |
| other fields | the sections of section 3.3, each an array that is empty when the section is absent |

Several `applicable_context` blocks are alternatives: later tools treat the definition as applying when any one of them holds.

Definitions appear in document order, the first document before the second. The properties always appear in the order shown.

## 5. Validation

`ERROR` diagnostics:

| Code | Condition | Location |
|---|---|---|
| `UNSTRUCTURED_FIELD` | a code-block section other than `Applicable context` has no text code block | heading |
| `EMPTY_DEFINITION` | none of the definition's content sections produced a value | heading |
| `DUPLICATE_DEFINITION_ID` | an id is used again; reported on the repeat | heading |

`FATAL`: `EXTRACTION_FAILURE` when a source document is missing, unreadable, or not valid UTF-8. Its location is `<input>`, and its message names the file. No JSON is written.

Errors in one definition do not stop the extraction of the others.

The extractor does not validate the content of contexts or assignments, such as whether a named field or input exists. The direct-control generator checks those against the maintained schemas.

## 6. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── direct-control-extractor/
            ├── direct-control-definitions.json
            └── extraction-report.txt
```

Each run first deletes the JSON and report from any earlier run (see the shared README, section 15.2), and refuses to run if an output path is a source document or a directory.

### 6.1 JSON Output

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "direct-control-definitions",
  "extraction_stage": "documentation-extraction",
  "sources": [
    "docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md",
    "docs/04-control/30-direct-control-definitions/02-interface-and-ownership-control.md"
  ],
  "definitions": [],
  "diagnostics": []
}
```

Each diagnostic has `severity`, `code`, `message`, `source_path`, `line` and `definition_id`; `line` and `definition_id` are `null` when unknown. Diagnostics are sorted by severity, code, source path, line, definition id, and message.

The JSON is written whenever both documents can be read, even when there are errors. It follows the shared output format: UTF-8 with LF line endings and one trailing newline, two-space indentation, non-ASCII characters written directly, and keys in the fixed order shown.

### 6.2 Extraction Report

The report gives the number of definitions and of diagnostics by severity, then every diagnostic in the JSON's order, one per line:

```text
SEVERITY CODE [definition-id] path:line: message
```

`[definition-id]` and `:line` are left out when unknown.

## 7. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/direct-control-extractor/src/extract_direct_control.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--json-output OUTPUT_PATH      default: <output directory>/direct-control-definitions.json
--report-output OUTPUT_PATH    default: <output directory>/extraction-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics, and exits with status `1` when any are reported, `0` otherwise.

## 8. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/direct-control-extractor/tests -p "test_*.py"
```

The tests build small documents inline and use temporary directories; they do not read the real documentation. Unit tests are grouped by stage: arguments and reading, headings and definition selection, sections, and validation. End-to-end tests write both documents to a temporary repository and run `main()` against it.

Two end-to-end tests compare the complete JSON and report with expected files under `tests/golden/`:

- `valid/`: two documents covering every content section, prose and `or:`-separated contexts, a level-5 subsection, constraints, sources, and ignored explanatory text, which extract without diagnostics
- `invalid/`: documents with unstructured sections, empty definitions, and a duplicated id, which fixes diagnostic order

`valid/direct-control-definitions.json` is also the reference for later tools' contract tests.

After an intentional output change, regenerate the golden files from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/direct-control-extractor/tests -p "test_*.py"
```

On Windows PowerShell, set the variable first with `$env:UPDATE_GOLDEN = "1"` and remove it afterwards.

## 9. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- use repository-relative source references
- preserve source ordering and traceability
- produce deterministic output
- report malformed documentation without inventing replacement values
- remain proportional to the tool's bounded purpose

The implementation is one Python source file, `src/extract_direct_control.py`, organized in pipeline order: constants and patterns, headings, sections, definitions, output, and the command line.

## 10. Relationship to Later Stages

The direct-control generator reads this output, validates each definition's contexts and assignments against the maintained control-input and control-word schemas and the micro-operation mapping, and writes a candidate for `rom/microcode/v1/direct-control-definitions.json`. The symbolic control-word generator then uses the maintained definitions' `applicable_context`, `direct_assignments`, and `control_supplied_values` to compose complete control words.
