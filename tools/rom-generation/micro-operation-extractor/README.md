# Micro-Operation Extractor

## 1. Purpose

The micro-operation extractor creates a normalized, machine-readable representation of the documented micro-operation catalog.

The extractor converts the authoritative micro-operation definitions into generated review material used by later ROM-generation stages. It reports missing, empty, and duplicated definition content rather than inferring replacement values.

The extractor does not define how micro-operations are implemented by control signals.

## 2. Authoritative Input

The extractor reads exactly one maintained document:

- [Micro-Operations](../../../docs/03-microarchitecture/02-micro-operations.md)

The source document remains authoritative. Its path is fixed in the extractor, relative to the repository root; it is not a command-line option.

The explicit input path:

- prevents unrelated Markdown files from becoming accidental inputs
- makes the extraction boundary reviewable
- ensures missing source documentation is detected

## 3. Source Document Conventions

### 3.1 Text Normalization

Extracted text has `\_`, `\<`, and `\>` unescaped, and the backticks of inline code removed (`` `PC` `` becomes `PC`). Headings are normalized the same way.

### 3.2 Definition Section

Definitions are read only from the section whose heading is `μop Definitions (Alphabetical)`. A leading section number, such as `5.`, is ignored, so renumbering the document does not break extraction.

Each heading exactly one level below the section heading starts a definition; its text is the micro-operation name. A definition runs to the next definition heading, or to the end of the section. The section ends at the next heading at or above its own level.

Deeper headings inside a definition are ordinary text. Lines inside fenced code blocks are never headings.

### 3.3 Labels

Definition content is introduced by bold labels with the colon inside the bold markers:

```markdown
**Category:** Control Flow
```

These labels are recognized, ignoring case and space before the colon:

| Label | Kind | Required |
|---|---|---|
| `Category` | single-valued | yes |
| `Description` | single-valued | yes |
| `Target` | single-valued | yes |
| `Expression` | single-valued | yes |
| `Sources` | single-valued | yes |
| `Preconditions` | list | no |
| `Constraints` | list | no |

A label's content is the text after it on the same line plus every following line up to the next recognized label. Several labels may share one line. Text before the first label is ignored. Fenced code blocks are always content: a label inside one is not recognized.

Any other bold label at the start of a line, such as `**Note:**`, is reported as a warning, because it is usually a misspelling. Its line is then read as ordinary text of the preceding section.

### 3.4 Single-Valued Attributes

The content's non-empty lines are read in order. Fenced code-block markers and `---` rules are dropped. Lines are stripped of surrounding whitespace, except that lines inside a code block keep their indentation, so a conditional expression keeps its structure:

```json
"expression": [
  "if IO_READ_REQ = 1:",
  "    IOT_TRANSFER <- READ",
  "else:",
  "    IOT_TRANSFER <- NONE"
]
```

Explanatory text after an expression, such as a `Where:` block, is part of the expression.

| Attribute | Extracted as |
|---|---|
| `Category` | lines joined with spaces |
| `Description` | lines joined with spaces |
| `Target` | lines joined with spaces, then split at commas into `targets` |
| `Expression` | the lines, as an array |
| `Sources` | each line split at commas; a leading `- ` list marker is removed |

`Sources` written as a single `none` or `(none)`, in any case, is an empty list. Elsewhere in a list of sources, `none` is an ordinary name.

If a single-valued label occurs more than once, the last occurrence is used and the repetition is reported.

### 3.5 Lists

`Preconditions` and `Constraints` each produce a list of entries. The text after the label on its own line, if any, is the first entry; each following `- ` list item is another. Blank lines and `---` rules are skipped.

Any other text, and any fenced code block, is skipped and reported as a warning, because only list items are extracted. An unrecognized label is skipped too, reported once as an unrecognized label. Reading continues with the next list item.

A repeated list label adds to the same list.

## 4. Extracted Representation

Each micro-operation uses this structure. The example is the actual entry for `DB_READ_TO_AC`, with its description and lists shortened:

```json
{
  "name": "DB_READ_TO_AC",
  "category": "I/O / External",
  "description": "Reads the value present on the System Data Bus (DB) and ORs it into the Accumulator (AC).",
  "targets": ["AC"],
  "expression": ["AC ← AC OR DB_input"],
  "sources": ["AC", "DB_input"],
  "preconditions": [
    {"text": "A device is currently driving DB", "source": {"path": "docs/03-microarchitecture/02-micro-operations.md", "line": 547}}
  ],
  "constraints": [
    {"text": "AC must not be written by any other μop in the same TS", "source": {"path": "docs/03-microarchitecture/02-micro-operations.md", "line": 551}}
  ],
  "source": {
    "path": "docs/03-microarchitecture/02-micro-operations.md",
    "heading": "DB_READ_TO_AC",
    "line": 528
  },
  "extraction_status": "definition-validated"
}
```

| Property | Content |
|---|---|
| `name` | the definition heading |
| `category`, `description` | text, empty when missing |
| `targets`, `expression`, `sources` | arrays of text, empty when missing |
| `preconditions`, `constraints` | arrays of `{"text", "source"}` entries, empty when not documented |
| `source` | the definition heading's path, text, and line |
| `extraction_status` | `definition-error` when the definition has any `ERROR` diagnostic, otherwise `definition-validated` |

The extractor does not:

- execute, parse, or simplify expressions
- infer targets or sources from the expression, description, or name
- evaluate or interpret preconditions and constraints
- combine, reorder, or alphabetize extracted content

## 5. Validation

`ERROR` diagnostics:

| Code | Condition | Location |
|---|---|---|
| `MISSING_DEFINITION_SECTION` | no definition section heading | file |
| `NO_MICRO_OPERATIONS` | the definition section has no definition headings | file |
| `DUPLICATE_MICRO_OPERATION` | a name is defined again; reported on the repeat | heading |
| `MISSING_REQUIRED_ATTRIBUTE` | a required label is absent | heading |
| `EMPTY_REQUIRED_ATTRIBUTE` | a required label has no content | heading |
| `DUPLICATE_ATTRIBUTE` | a single-valued label occurs again; reported on the repeat | label |

`WARNING` diagnostics:

| Code | Condition | Location |
|---|---|---|
| `UNEXPECTED_LIST_TEXT` | text or a code block in a precondition or constraint list that is not a list item | that line |
| `UNRECOGNIZED_LABEL` | a bold label, outside code blocks, that is not one of the labels in section 3.3 | that line |

Warnings do not change a definition's `extraction_status` or the exit status.

`FATAL`: `EXTRACTION_FAILURE` when the source document is missing, unreadable, or not valid UTF-8. No JSON is written.

Errors in one definition do not stop the extraction of the others. Every diagnostic names the micro-operation when one applies.

## 6. Validation Boundary

The extractor does not validate whether:

- a micro-operation is architecturally correct
- a micro-operation is required by the instruction set or used by an execution schedule
- targets or sources agree with the expression
- two micro-operations are equivalent or may execute concurrently
- a micro-operation has a valid control-signal implementation
- preconditions are satisfiable or constraints are mutually consistent

Those checks belong to later mapping, composition, and control-validation stages.

## 7. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── micro-operation-extractor/
            ├── micro-operations.json
            └── extraction-report.txt
```

Generated outputs:

- must not be edited manually
- must not be treated as authoritative source
- must not be committed as maintained specifications
- may be deleted and regenerated
- must be regenerated after relevant documentation changes

### 7.1 JSON Output

```json
{
  "format_version": 1,
  "extraction_stage": "definition-validation",
  "source": {
    "path": "docs/03-microarchitecture/02-micro-operations.md"
  },
  "micro_operations": [],
  "diagnostics": []
}
```

`micro_operations` lists every definition in document order (section 4), including definitions with errors.

Each diagnostic has `severity`, `code`, `message`, and `source_path`, plus `line` and `micro_operation` when known. Diagnostics are sorted by severity, code, source path, line, micro-operation, and message.

Each run first deletes the JSON and report from any earlier run (see the shared README, section 15.2), and refuses to run if an output path is the source document or a directory. The JSON is written whenever the source document can be read, even when it has errors. Paths are repository-relative. The file follows the shared output format: UTF-8 with LF line endings and one trailing newline, two-space indentation, non-ASCII characters written directly, and keys in the fixed order shown, never sorted.

### 7.2 Extraction Report

The report gives counts of micro-operations and of diagnostics by severity, whether the JSON was written, and every diagnostic in the JSON's order, one per line:

```text
SEVERITY CODE [micro-operation] path:line: message
```

`-` stands in for a missing micro-operation name, and `:line` is left out when unknown.

## 8. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/micro-operation-extractor/src/extract_micro_operations.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--json-output OUTPUT_PATH      default: <output directory>/micro-operations.json
--report-output OUTPUT_PATH    default: <output directory>/extraction-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics, and exits with status `1` when any are reported, `0` otherwise.

## 9. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/micro-operation-extractor/tests -p "test_*.py"
```

The tests build small documents inline and use temporary directories. Unit tests are grouped by stage: arguments and reading, definition blocks, labeled sections, attributes, lists, validation, and output. End-to-end tests write a document to a temporary repository and run `main()` against it.

Two end-to-end tests compare the complete JSON and report with expected files under `tests/golden/`:

- `valid/`: a document covering multiline attributes, code blocks, list-form sources, `(none)`, preconditions, and constraints, which extracts without diagnostics
- `invalid/`: a document with missing, empty, and duplicated attributes, a duplicated name, stray list text, and an unrecognized label, which fixes diagnostic order

`valid/micro-operations.json` is also the reference for later tools' contract tests.

After an intentional output change, regenerate the golden files from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/micro-operation-extractor/tests -p "test_*.py"
```

On Windows PowerShell, set the variable first with `$env:UPDATE_GOLDEN = "1"` and remove it afterwards.

Tests should cover representative behavior rather than every possible Markdown permutation.

## 10. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- use repository-relative source references
- preserve source ordering and traceability
- produce deterministic output
- report malformed documentation without inventing replacement values
- remain proportional to the tool's bounded purpose

Shared code must not be moved into the ROM-generation `common/` directory until actual duplicated requirements exist and a stable shared interface can be identified.

## 11. Implementation Structure

The implementation is one Python source file, `src/extract_micro_operations.py`, organized in pipeline order:

1. constants: paths, output format, severities, recognized labels, and Markdown patterns
2. Markdown helpers and heading detection
3. definition blocks: finding the section and splitting it by heading
4. labeled sections: grouping block lines under labels, and reading single-valued and list content
5. micro-operations: reading attributes and reporting problems
6. JSON output and the report
7. the command line

## 12. Relationship to Later Stages

The micro-operation mapping generator reads this output, with the maintained control-word schema, to build the reviewed micro-operation mapping. It uses each micro-operation's `name`, `source`, and `extraction_status`.

This extractor does not map micro-operations to control-field assignments.

## 13. Non-Goals

The extractor does not:

- modify the authoritative documentation
- map micro-operations to control outputs
- create complete control words
- select micro-operations for execution
- evaluate control-input conditions
- assign logical control-word or physical ROM bit positions
- generate ROM images

## 14. Completion Boundary

The extractor is complete when it can:

- read the authoritative micro-operation document
- identify every documented micro-operation
- extract all required definition properties
- preserve multiline expressions, preconditions, and constraints
- retain source traceability
- report incomplete or malformed definitions without guessing
- generate deterministic JSON and a human-readable report
- pass the targeted automated tests
