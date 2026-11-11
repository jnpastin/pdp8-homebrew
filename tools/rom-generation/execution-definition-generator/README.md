# Execution-Definition Generator

## 1. Purpose

The execution-definition generator creates a candidate execution-definition artifact for review.

It takes the cases written by the execution-definition extractor, checks their structure, and reports how they differ from the maintained artifact. The candidate is the extracted cases, unchanged, and is written only when no errors are found.

The generator does not:

- modify the cases it checks
- check context, predicate, or micro-operation names against the maintained schemas or mapping
- compose control words

## 2. Inputs

| Input | Default path | Required |
|---|---|---|
| extracted cases | `build/simulation_outputs/rom-generation/execution-definition-extractor/execution-definitions.json` | yes |
| maintained artifact | `rom/microcode/v1/execution-definitions.json` | no; missing or blank is treated as absent |

The extracted cases' layout is described in the execution-definition extractor README. The maintained artifact is compared in full.

The generator never writes the maintained artifact.

## 3. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── execution-definition-generator/
            ├── execution-definitions.candidate.json
            └── generation-report.txt
```

Each run first deletes the candidate and report from any earlier run, so a candidate on disk always comes from the latest run, and that run succeeded (see the shared README, section 15.2). The tool refuses to run if an output path is one of its inputs or a directory.

The report is written on every run. The candidate is written only when the run reports no `ERROR` or `FATAL` diagnostics.

## 4. Candidate Structure

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "execution-definitions",
  "generation_stage": "candidate-generation",
  "cases": [],
  "diagnostics": []
}
```

`format_version` and `control_design_version` are copied from the extracted artifact, and `cases` holds the extracted cases unchanged, in extracted order. `diagnostics` is always empty: findings appear in the report.

## 5. Structural Validation

Any error stops the run before the review.

Extracted artifact:

- every top-level property present: `format_version`, `control_design_version`, `artifact`, `extraction_stage`, `cases`, `diagnostics` (`MISSING_TOP_LEVEL_FIELDS`)
- `artifact` equal to `execution-definitions` (`UNEXPECTED_ARTIFACT_TYPE`), `format_version` equal to `1` (`UNSUPPORTED_FORMAT_VERSION`), and `extraction_stage` equal to `documentation-extraction` (`UNSUPPORTED_EXTRACTION_STAGE`)
- a `diagnostics` array (`INVALID_EXTRACTOR_DIAGNOSTICS`) with no `ERROR` or `FATAL` entries (`EXTRACTOR_FAILURE_DIAGNOSTICS`); warnings are allowed
- a `cases` array of objects with non-empty, unique `id` values (`INVALID_EXTRACTED_CASES`)
- in every case (`INVALID_CASE_FIELD`, naming the field):

| Field | Requirement |
|---|---|
| `source` | an object with a string `path` and an integer `line` |
| `execution_model` | `major-state` or `console-transaction` |
| `context` | an array of strings |
| `timing_state` | 1 to 4 for `major-state`; `null` for `console-transaction` |
| `micro_operations` | an array of strings |
| `conditional_micro_operations` | an array of objects with exactly `predicate` and `micro_operation`, in that order, both strings |

Maintained artifact, when present:

- the same `control_design_version` as the extracted artifact (`CONTROL_DESIGN_VERSION_MISMATCH`)
- a `cases` array of objects with non-empty, unique `id` values (`INVALID_MAINTAINED_CASES`)

The maintained cases' fields are not checked; any difference from the extracted cases is reported by the review.

## 6. Review Against the Maintained Artifact

Each difference is reported as a warning for review before promotion:

| Code | Condition |
|---|---|
| `NEW_CASE` | an extracted case is not in the maintained artifact |
| `CHANGED_CASE` | an extracted case differs in any property from the maintained one |
| `STALE_CASE` | a maintained case is no longer extracted; it is left out of the candidate |

A run against a maintained artifact promoted from its own candidate reports no diagnostics.

## 7. Diagnostics

| Severity | Meaning | Effect |
|---|---|---|
| `WARNING` | a review difference (section 6) | candidate is written |
| `ERROR` | invalid input (section 5) | no candidate; exit status `1` |
| `FATAL` | an input file is missing, unreadable, not UTF-8, not JSON, or not a JSON object | no candidate; exit status `1` |

`INFO` is defined but not currently emitted. The only fatal code is `GENERATION_FAILURE`.

The report lists every diagnostic, one per line:

```text
SEVERITY CODE [case-id] [field]: message
```

`[case-id]` and `[field]` appear only when they apply. Diagnostics are sorted by severity, code, case id, field, and message. The console repeats the errors and fatal errors.

## 8. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/execution-definition-generator/src/generate_execution_definitions.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--extracted INPUT_PATH          default: the extractor output (section 2)
--maintained INPUT_PATH         default: rom/microcode/v1/execution-definitions.json
--candidate-output OUTPUT_PATH  default: <output directory>/execution-definitions.candidate.json
--report-output OUTPUT_PATH     default: <output directory>/generation-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool exits with status `1` when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise.

## 9. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/execution-definition-generator/tests -p "test_*.py"
```

Tests build small inputs inline and use temporary directories; they do not read the real documentation or maintained files. They are grouped by stage:

- argument defaults, path resolution, and JSON reading
- structural validation of the extracted and maintained artifacts, covering every error code
- review against the maintained artifact and candidate construction
- report formatting
- the contract with the execution-definition extractor
- complete runs through `main()`, including removal of earlier outputs and refused output paths

Two end-to-end tests compare the report with expected files under `tests/golden/`: `review/` (new, changed, and stale cases) and `invalid/` (structural errors). After an intentional output change, regenerate them from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/execution-definition-generator/tests -p "test_*.py"
```

On Windows PowerShell, set the variable first with `$env:UPDATE_GOLDEN = "1"` and remove it afterwards.

The contract tests read the extractor's golden output, `tools/rom-generation/execution-definition-extractor/tests/golden/valid/execution-definitions.json`. They check that it passes structural validation and that the test builders have the same keys, in the same order. If the extractor's output format changes, these tests fail until this tool and its builders are updated to match.

## 10. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- preserve deterministic ordering
- report malformed input without inventing replacements
- remain proportional to the bounded task

The implementation is one Python source file, `src/generate_execution_definitions.py`, organized in pipeline order: reading inputs, structural validation, review, candidate construction, output, and the command line.

## 11. Workflow

1. Update the execution documentation.
2. Run the execution-definition extractor.
3. Run the execution-definition generator.
4. Resolve any errors, normally by correcting the documentation.
5. Review the new, changed, and stale cases.
6. Promote the reviewed candidate to `rom/microcode/v1/execution-definitions.json`.

The generator never promotes its candidate.

## 12. Relationship to Later Stages

The symbolic control-word generator reads the maintained artifact and combines each case's context, timing state, and micro-operations with the micro-operation mapping to compose control words.
