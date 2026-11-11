# Direct-Control Generator

## 1. Purpose

The direct-control generator creates a candidate direct-control artifact for review.

It takes the definitions written by the direct-control extractor, reports how they differ from the maintained artifact, and checks every definition's contexts and assignments against the maintained control-input schema, control-word schema, and micro-operation mapping. The candidate is the extracted definitions, unchanged, and is written only when no errors are found.

The generator does not:

- modify the definitions it checks
- interpret prose contexts or evaluate Boolean conditions
- compose control words

## 2. Inputs

| Input | Default path | Required |
|---|---|---|
| extracted definitions | `build/simulation_outputs/rom-generation/direct-control-extractor/direct-control-definitions.json` | yes |
| maintained artifact | `rom/microcode/v1/direct-control-definitions.json` | no; missing or blank is treated as absent |
| control-input schema | `rom/microcode/v1/control-input-schema.json` | yes |
| control-word schema | `rom/microcode/v1/control-word-schema.json` | yes |
| micro-operation mapping | `rom/microcode/v1/micro-operation-mapping.json` | yes |

The extracted definitions' layout is described in the direct-control extractor README. Of each definition, the generator reads `id`, `applicable_context`, `direct_assignments`, `micro_operation_assignments` and `control_supplied_values`; the maintained artifact is compared in full.

From the reference specifications it uses:

| Specification | Properties used |
|---|---|
| control-word schema | each field's `name`, `width`, `control_word_role`, `default_value`, and `values` (`encoding`, `meaning`) |
| control-input schema | each input's `name`, `width`, and `control_uses` |
| micro-operation mapping | each mapping's `micro_operation` and `assignments` |

The generator never writes the maintained artifact.

## 3. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── direct-control-generator/
            ├── direct-control-definitions.candidate.json
            └── generation-report.txt
```

Each run first deletes the candidate and report from any earlier run, so a candidate on disk always comes from the latest run, and that run succeeded (see the shared README, section 15.2). The tool refuses to run if an output path is one of its inputs or a directory.

The report is written on every run. The candidate is written only when the run reports no `ERROR` or `FATAL` diagnostics.

## 4. Candidate Structure

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "direct-control-definitions",
  "generation_stage": "candidate-generation",
  "sources": [],
  "definitions": [],
  "diagnostics": []
}
```

`format_version`, `control_design_version` and `sources` are copied from the extracted artifact, and `definitions` holds the extracted definitions unchanged, in extracted order. `diagnostics` is always empty: findings appear in the report.

## 5. Structural Validation

These checks run first. Any error stops the run before the review and definition checks.

Extracted artifact:

- every top-level property present: `format_version`, `control_design_version`, `artifact`, `extraction_stage`, `sources`, `definitions`, `diagnostics`
- `artifact` equal to `direct-control-definitions`, `format_version` equal to `1`, and `extraction_stage` equal to `documentation-extraction`
- a `diagnostics` array with no `ERROR` or `FATAL` entries; warnings are allowed
- a `definitions` array of objects with non-empty, unique `id` values
- `applicable_context`, `direct_assignments`, `micro_operation_assignments` and `control_supplied_values` arrays of strings in every definition

Maintained artifact, when present:

- the same `control_design_version` as the extracted artifact
- a `definitions` array of objects with non-empty, unique `id` values

Reference specifications:

- `specification_type` equal to `control-input-schema`, `control-word-schema` and `micro-operation-mapping`
- the same `control_design_version` as the extracted artifact

The reference specifications' contents are validated by the tools that generate them; here, malformed entries are skipped.

## 6. Review Against the Maintained Artifact

Each difference is reported as a warning for review before promotion:

| Code | Condition |
|---|---|
| `NEW_DEFINITION` | an extracted definition is not in the maintained artifact |
| `CHANGED_DEFINITION` | an extracted definition differs in any property from the maintained one |
| `STALE_DEFINITION` | a maintained definition is no longer extracted; it is left out of the candidate |

## 7. Definition Checks

### 7.1 Applicable Context

Each context line of the form `NAME = value` or `NAME != value` must name a control input, a control-word field, or `MS` or `TS` (`UNKNOWN_CONTEXT_SYMBOL`). Each `NAME is selected` line must name a micro-operation in the mapping (`UNKNOWN_MICRO_OPERATION`). Other lines, such as `AND (` or prose, are not checked, and context values are not checked.

### 7.2 Assignments

Direct assignments and micro-operation assignments are `NAME = value` lines; any other non-blank line is `MALFORMED_ASSIGNMENT`. For each assignment:

- the field must exist (`UNKNOWN_CONTROL_FIELD`) and be `encoded` (`NON_ENCODED_CONTROL_FIELD`)
- the value must resolve to a legal encoding (section 7.4)
- a field may not be assigned two different values within one kind (`CONFLICTING_ASSIGNMENT`), or different values by the direct and micro-operation assignments (`CROSS_DOMAIN_ASSIGNMENT_CONFLICT`)

When the context selects micro-operations, each micro-operation assignment must either equal the field's `default_value` or be a value one of the selected micro-operations assigns in the mapping (`MICRO_OPERATION_ASSIGNMENT_MISMATCH`).

### 7.3 Control-Supplied Values

A control-supplied value is `FIELD = source`. The field must exist and be `encoded`, as for assignments. The source is either:

- a control input: its `control_uses` must include `value` (`INPUT_NOT_VALUE_CAPABLE`) and its `width` must equal the field's (`VALUE_WIDTH_MISMATCH`)
- a constant, resolved as in section 7.4

A source that is neither is `UNKNOWN_VALUE_SOURCE`.

### 7.4 Values

A value resolves to an encoding of its field in one of two ways:

- **A number** is taken as the encoding itself and must be a legal one (`VALUE_OUT_OF_RANGE`). The legal encodings are those in the field's `values` not marked `reserved` or `invalid`; a field without `values` allows every octal value its width holds.
- **A symbol** must equal exactly one encoding's meaning, ignoring case and anything but letters and digits; `FETCH` matches the meaning `fetch`.

A value that resolves neither way is `UNKNOWN_CONTROL_VALUE`.

Symbols therefore work only for fields whose encoding meanings are names, such as `MS_NEXT` (`FETCH`, `DEFER`, ...) and `IOT_TRANSFER_VAL` (`NONE`, `READ`, `WRITE`). For a field whose meanings are prose, such as `AC_LOAD` (`no load`, `load`), the documentation uses the encoding number.

## 8. Diagnostics

| Severity | Meaning | Effect |
|---|---|---|
| `WARNING` | a review difference (section 6) | candidate is written |
| `ERROR` | invalid input or a failed definition check | no candidate; exit status `1` |
| `FATAL` | an input file is missing, unreadable, not UTF-8, not JSON, or not a JSON object | no candidate; exit status `1` |

`INFO` is defined but not currently emitted. The only fatal code is `GENERATION_FAILURE`.

The report lists every diagnostic, one per line:

```text
SEVERITY CODE [definition-id] [field]: message
```

`[definition-id]` and `[field]` appear only when they apply. Diagnostics are sorted by severity, code, definition id, field, and message. The console repeats the errors and fatal errors.

## 9. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/direct-control-generator/src/generate_direct_control.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--extracted INPUT_PATH                default: the extractor output (section 2)
--maintained INPUT_PATH               default: rom/microcode/v1/direct-control-definitions.json
--control-input-schema INPUT_PATH     default: rom/microcode/v1/control-input-schema.json
--control-word-schema INPUT_PATH      default: rom/microcode/v1/control-word-schema.json
--micro-operation-mapping INPUT_PATH  default: rom/microcode/v1/micro-operation-mapping.json
--candidate-output OUTPUT_PATH        default: <output directory>/direct-control-definitions.candidate.json
--report-output OUTPUT_PATH           default: <output directory>/generation-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool exits with status `1` when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise.

## 10. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/direct-control-generator/tests -p "test_*.py"
```

Tests build small inputs inline and use temporary directories; they do not read the real documentation or maintained files. They are grouped by stage:

- path resolution, argument defaults, and JSON reading
- structural validation of each input
- review against the maintained artifact
- value resolution: legal encodings, symbols, and constants
- definition checks, covering every error code
- candidate construction and report formatting
- the contract with the direct-control extractor
- complete runs through `main()`, including diagnostic order, removal of earlier outputs, and refused output paths

The contract tests read the extractor's golden output, `tools/rom-generation/direct-control-extractor/tests/golden/valid/direct-control-definitions.json`. They check that it passes structural validation and that the test builders have the same keys, in the same order. If the extractor's output format changes, these tests fail until this tool and its builders are updated to match.

## 11. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- preserve deterministic ordering
- report malformed input without inventing replacements
- remain proportional to the bounded task

The implementation is one Python source file, `src/generate_direct_control.py`, organized in pipeline order: reading inputs, structural validation, review, definition checks, candidate construction, output, and the command line.

## 12. Workflow

1. Update the direct-control documentation.
2. Run the direct-control extractor.
3. Run the direct-control generator.
4. Resolve any errors, normally by correcting the documentation or a maintained specification.
5. Review the new, changed, and stale definitions.
6. Promote the reviewed candidate to `rom/microcode/v1/direct-control-definitions.json`.

The generator never promotes its candidate.

## 13. Relationship to Later Stages

The symbolic control-word generator reads the maintained artifact and uses each definition's `applicable_context`, `direct_assignments`, and `control_supplied_values` to compose complete control words.
