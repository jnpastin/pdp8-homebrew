# Timing-Constraint Extractor

## 1. Purpose

The timing-constraint extractor reads the major-state timing document and produces its machine-readable timing constraints. Each constraint states that whenever its context holds, its requirement must hold too; for example, a controller may not request an AC clear while a transfer is pending.

The extractor does not:

- parse or evaluate the context or requirement expressions
- check that the names they use are defined control inputs or fields
- derive constraints from prose

## 2. Authoritative Input

```text
docs/09-timing/03-major-state-timing.md
```

## 3. Source Document Conventions

### 3.1 Constraints

A constraint is a bullet, at any indentation, that is entirely one code span of the form `REQUIREMENT IF CONDITION`:

```markdown
#### 5.2.5 TS3

- The selected controller may assert `IO_CLEAR_AC_REQ` only when neither a read nor write transfer is pending:
  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1 OR IOT_WRITE_PENDING = 1`
```

Bullets with other text, code spans without ` IF `, and anything inside code blocks are ignored.

### 3.2 Timing State

A constraint's nearest enclosing heading must be a numbered timing-state heading, whose title starts with `TS1` to `TS4`, such as `#### 5.2.5 TS3` or `### 3.1 TS1 — Address Setup`. A constraint under any other heading, such as a `TPn` heading, is an error, except inside the State Invariants section (section 3.4).

### 3.3 Scope

A section declares the conditions under which its constraints apply with an `Applicable context:` label followed by a text code block, one condition per line:

````markdown
### 5.2 EXECUTE: External IOT

Applicable context:

```text
MS = EXECUTE
IOT_ACTIVE = 1
```
````

A constraint takes the scope of its nearest enclosing section that declares one. Every constraint must have a scope; a section may declare only one.

### 3.4 State Invariants

A level-2 section titled `State Invariants` holds conditions true in every reachable state, such as `IR_INDIRECT = 1 IF MS = DEFER`. Its constraints use the same bullet form but need no timing-state heading and no scope:

- the id is `invariant:` followed by the enclosing heading's number and the constraint's position under it, such as `invariant:9.1.1`
- the context is the parenthesized condition, preceded by the nearest scope when one is declared
- no `TS = n` term is added

Later stages treat invariants exactly like timing constraints: a state whose context holds and whose requirement does not is unreachable.

## 4. Extracted Representation

```json
{
  "id": "timing:5.2.5.1",
  "context": "MS = EXECUTE AND IOT_ACTIVE = 1 AND TS = 3 AND (IOT_READ_PENDING = 1 OR IOT_WRITE_PENDING = 1)",
  "requirement": "IO_CLEAR_AC_REQ != 1",
  "source": {
    "path": "docs/09-timing/03-major-state-timing.md",
    "line": 132
  }
}
```

| Property | Meaning |
|---|---|
| `id` | `timing:` followed by the timing-state heading's number and the constraint's position under it, from 1 |
| `context` | the scope conditions, `TS = n`, and the parenthesized condition, joined by `AND` |
| `requirement` | the text before ` IF ` |
| `source` | the document and the constraint's line |

Ids stay the same when lines are added or removed elsewhere in the document; they change only when the heading is renumbered or constraints under it are reordered.

## 5. Validation

`ERROR` diagnostics:

| Code | Condition | Location |
|---|---|---|
| `MISSING_TIMING_CONTEXT` | a constraint's nearest heading is not a `TS1` to `TS4` heading | constraint |
| `MALFORMED_CONSTRAINT` | the requirement or condition is empty | constraint |
| `MISSING_SCOPE` | no enclosing section declares an `Applicable context` | constraint |
| `MISSING_CODE_BLOCK` | an `Applicable context:` label is not followed by a non-empty text code block | label |
| `DUPLICATE_SCOPE` | a section declares a second `Applicable context` | label |
| `DUPLICATE_CONSTRAINT_ID` | an id is used again; reported on the repeat | constraint |
| `NO_CONSTRAINTS_FOUND` | the document has no constraints and nothing else was reported | document |

`FATAL`: `EXTRACTION_FAILURE` when the document is missing, unreadable, or not valid UTF-8. Its location is `<input>`, and its message names the file. No JSON is written.

## 6. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── timing-constraint-extractor/
            ├── timing-constraints.json
            └── extraction-report.txt
```

Each run first deletes the JSON and report from any earlier run (see the shared README, section 15.2), and refuses to run if an output path is the source document or a directory.

### 6.1 JSON Output

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "timing-constraints",
  "extraction_stage": "documentation-extraction",
  "sources": ["docs/09-timing/03-major-state-timing.md"],
  "constraints": [],
  "diagnostics": []
}
```

Each diagnostic has `severity`, `code`, `message`, `source_path`, `line` and `constraint_id`; `line` and `constraint_id` are `null` when unknown. Diagnostics are sorted by severity, code, source path, line, constraint id, and message.

The JSON is written whenever the document can be read, even when there are errors. It follows the shared output format: UTF-8 with LF line endings and one trailing newline, two-space indentation, non-ASCII characters written directly, and keys in the fixed order shown.

### 6.2 Extraction Report

The report gives the number of constraints and of diagnostics by severity, then every diagnostic in the JSON's order, one per line:

```text
SEVERITY CODE [constraint-id] path:line: message
```

`[constraint-id]` and `:line` are left out when unknown.

## 7. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/timing-constraint-extractor/src/extract_timing_constraints.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--json-output OUTPUT_PATH      default: <output directory>/timing-constraints.json
--report-output OUTPUT_PATH    default: <output directory>/extraction-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics, and exits with status `1` when any are reported, `0` otherwise.

## 8. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/timing-constraint-extractor/tests -p "test_*.py"
```

The tests build small documents inline and use temporary directories; they do not read the real documentation. Unit tests cover every diagnostic code; end-to-end tests write the document to a temporary repository and run `main()` against it.

Two end-to-end tests compare the complete JSON and report with expected files under `tests/golden/`:

- `valid/`: a document with a scoped section, several timing-state headings, a `TPn` heading, and ignored prose bullets, which extracts without diagnostics
- `invalid/`: a document that breaks each rule, which fixes diagnostic order

`valid/timing-constraints.json` is also the reference for the timing-constraint generator's contract tests.

After an intentional output change, regenerate the golden files from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/timing-constraint-extractor/tests -p "test_*.py"
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

The implementation is one Python source file, `src/extract_timing_constraints.py`, organized in pipeline order: constants and patterns, extraction, output, and the command line.

## 10. Relationship to Later Stages

The timing-constraint generator reads this output, reviews it against the maintained artifact, and writes a candidate for `rom/microcode/v1/timing-constraints.json`. The symbolic control-word generator treats each maintained constraint's context together with a violated requirement as impossible when it checks whether two assignments can conflict.
