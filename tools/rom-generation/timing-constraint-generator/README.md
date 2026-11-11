# Timing-Constraint Generator

## 1. Purpose

The timing-constraint generator creates a candidate timing-constraint artifact for review.

It takes the constraints written by the timing-constraint extractor, checks their structure, and reports how they differ from the maintained artifact. The candidate is the extracted constraints, unchanged, and is written only when no errors are found.

The generator does not:

- modify the constraints it checks
- parse the context or requirement expressions, or check their names against the maintained schemas
- check that the constraints are consistent with each other

## 2. Inputs

| Input | Default path | Required |
|---|---|---|
| extracted constraints | `build/simulation_outputs/rom-generation/timing-constraint-extractor/timing-constraints.json` | yes |
| maintained artifact | `rom/microcode/v1/timing-constraints.json` | no; missing or blank is treated as absent |

The extracted constraints' layout is described in the timing-constraint extractor README. The maintained artifact is compared in full.

The generator never writes the maintained artifact.

## 3. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── timing-constraint-generator/
            ├── timing-constraints.candidate.json
            └── generation-report.txt
```

Each run first deletes the candidate and report from any earlier run, so a candidate on disk always comes from the latest run, and that run succeeded (see the shared README, section 15.2). The tool refuses to run if an output path is one of its inputs or a directory.

The report is written on every run. The candidate is written only when the run reports no `ERROR` or `FATAL` diagnostics.

## 4. Candidate Structure

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "timing-constraints",
  "generation_stage": "candidate-generation",
  "sources": [],
  "constraints": [],
  "diagnostics": []
}
```

`format_version`, `control_design_version` and `sources` are copied from the extracted artifact, and `constraints` holds the extracted constraints unchanged, in extracted order. `diagnostics` is always empty: findings appear in the report.

## 5. Structural Validation

Any error stops the run before the review.

Extracted artifact:

- every top-level property present: `format_version`, `control_design_version`, `artifact`, `extraction_stage`, `sources`, `constraints`, `diagnostics` (`MISSING_TOP_LEVEL_FIELDS`)
- `artifact` equal to `timing-constraints` (`UNEXPECTED_ARTIFACT_TYPE`), `format_version` equal to `1` (`UNSUPPORTED_FORMAT_VERSION`), and `extraction_stage` equal to `documentation-extraction` (`UNSUPPORTED_EXTRACTION_STAGE`)
- `sources` an array of strings (`INVALID_SOURCES`)
- a `diagnostics` array (`INVALID_EXTRACTOR_DIAGNOSTICS`) with no `ERROR` or `FATAL` entries (`EXTRACTOR_FAILURE_DIAGNOSTICS`); warnings are allowed
- a `constraints` array of objects with non-empty, unique `id` values (`INVALID_EXTRACTED_CONSTRAINTS`)
- in every constraint, non-empty string `context` and `requirement`, and a `source` with a string `path` and an integer `line` (`INVALID_CONSTRAINT_FIELD`, naming the field)

Maintained artifact, when present:

- the same `control_design_version` as the extracted artifact (`CONTROL_DESIGN_VERSION_MISMATCH`)
- a `constraints` array of objects with non-empty, unique `id` values (`INVALID_MAINTAINED_CONSTRAINTS`)

## 6. Review Against the Maintained Artifact

Each difference is reported as a warning for review before promotion:

| Code | Condition |
|---|---|
| `NEW_CONSTRAINT` | an extracted constraint is not in the maintained artifact |
| `CHANGED_CONSTRAINT` | an extracted constraint differs in any property from the maintained one |
| `STALE_CONSTRAINT` | a maintained constraint is no longer extracted; it is left out of the candidate |

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
SEVERITY CODE [constraint-id] [field]: message
```

`[constraint-id]` and `[field]` appear only when they apply. Diagnostics are sorted by severity, code, constraint id, field, and message. The console repeats the errors and fatal errors.

## 8. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/timing-constraint-generator/src/generate_timing_constraints.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--extracted INPUT_PATH          default: the extractor output (section 2)
--maintained INPUT_PATH         default: rom/microcode/v1/timing-constraints.json
--candidate-output OUTPUT_PATH  default: <output directory>/timing-constraints.candidate.json
--report-output OUTPUT_PATH     default: <output directory>/generation-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool exits with status `1` when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise.

## 9. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/timing-constraint-generator/tests -p "test_*.py"
```

Tests build small inputs inline and use temporary directories; they do not read the real documentation or maintained files. They cover argument defaults and JSON reading, every structural error code, the review, report formatting, the contract with the extractor, and complete runs through `main()`, including removal of earlier outputs and refused output paths.

Two end-to-end tests compare the report with expected files under `tests/golden/`: `review/` (new, changed, and stale constraints) and `invalid/` (structural errors). After an intentional output change, regenerate them from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/timing-constraint-generator/tests -p "test_*.py"
```

On Windows PowerShell, set the variable first with `$env:UPDATE_GOLDEN = "1"` and remove it afterwards.

The contract tests read the extractor's golden output, `tools/rom-generation/timing-constraint-extractor/tests/golden/valid/timing-constraints.json`. They check that it passes structural validation and that the test builders have the same keys, in the same order. If the extractor's output format changes, these tests fail until this tool and its builders are updated to match.

## 10. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- preserve deterministic ordering
- report malformed input without inventing replacements
- remain proportional to the bounded task

The implementation is one Python source file, `src/generate_timing_constraints.py`, organized in pipeline order: reading inputs, structural validation, review, candidate construction, output, and the command line.

## 11. Workflow

1. Update the timing documentation.
2. Run the timing-constraint extractor.
3. Run the timing-constraint generator.
4. Resolve any errors, normally by correcting the documentation.
5. Review the new, changed, and stale constraints.
6. Promote the reviewed candidate to `rom/microcode/v1/timing-constraints.json`.

The generator never promotes its candidate.

## 12. Relationship to Later Stages

The symbolic control-word generator reads the maintained artifact. It treats each constraint's context together with a violated requirement as an impossible state when it decides whether two control-word assignments can apply at once.
