# Symbolic Control-Word Generator

## 1. Purpose

The symbolic control-word generator combines the maintained control specifications into a candidate symbolic control word for every execution case, for review.

A symbolic control word lists the default value of every encoded control-word field, and every assignment that the case's micro-operations and the applicable direct-control definitions make to it, each with the condition under which it applies and where it came from. Conditions stay symbolic: the generator never enumerates control-input combinations into its output.

The generator checks that every name the specifications use is defined, that every compared value is one the name can take, and that no two assignments can set a field to different values in the same reachable state.

The generator does not:

- modify any input specification
- pack control words into bits, or assign control addresses

## 2. Inputs

All six input specifications are read from one directory, by default `rom/microcode/v1/`:

| Input | File | Entries | Entry id |
|---|---|---|---|
| control-input schema | `control-input-schema.json` | `fields` | `name` |
| control-word schema | `control-word-schema.json` | `fields` | `name` |
| micro-operation mapping | `micro-operation-mapping.json` | `mappings` | `micro_operation` |
| execution definitions | `execution-definitions.json` | `cases` | `id` |
| direct-control definitions | `direct-control-definitions.json` | `definitions` | `id` |
| timing constraints | `timing-constraints.json` | `constraints` | `id` |

The maintained symbolic artifact, `rom/microcode/v1/symbolic-control-words.json`, is read for the review (section 9). It is optional; missing or blank is treated as absent.

The generator never writes any of its inputs.

## 3. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── symbolic-control-word-generator/
            ├── symbolic-control-words.candidate.json
            └── generation-report.txt
```

Each run first deletes the candidate and report from any earlier run, so a candidate on disk always comes from the latest run, and that run succeeded (see the shared README, section 15.2). The tool refuses to run if an output path is one of its inputs or a directory.

The report is written on every run. The candidate is written only when the run reports no `ERROR` or `FATAL` diagnostics.

## 4. Candidate Structure

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "symbolic-control-words",
  "generation_stage": "candidate-generation",
  "representation": "predicate-preserving",
  "sources": [
    "control-input-schema.json",
    "control-word-schema.json",
    "micro-operation-mapping.json",
    "execution-definitions.json",
    "direct-control-definitions.json",
    "timing-constraints.json"
  ],
  "cases": [],
  "diagnostics": []
}
```

`control_design_version` is taken from the control-word schema. `cases` holds one entry per execution case, in execution-definition order. `diagnostics` is always empty: findings appear in the report.

Each case, abbreviated here to two fields and two definitions:

```json
{
  "execution_case_id": "fetch-defer:3.1",
  "source": {"path": "docs/03-microarchitecture/04-fetch-defer.md", "line": 42},
  "base_context": "(MS = FETCH AND TS = 1)",
  "defaults": {"AC_LOAD": "0", "MA_LOAD": "0"},
  "field_assignments": {
    "AC_LOAD": [],
    "MA_LOAD": [
      {
        "value": "1",
        "when": "(MS = FETCH AND TS = 1)",
        "origin": "micro-operation mapping",
        "source": "PC_TO_MA"
      }
    ]
  },
  "selected_micro_operations": {
    "II_CLEAR": "((MS = FETCH AND TS = 1) AND CIFP = 0)",
    "PC_TO_MA": "(MS = FETCH AND TS = 1)"
  },
  "applicable_direct_control_definitions": ["01:3.3.2", "01:3.3.3"]
}
```

| Property | Meaning |
|---|---|
| `execution_case_id`, `source` | the execution case's `id` and `source` |
| `base_context` | the case's context lines and `TS = n` (when the case has a timing state), joined by `AND`, plus `RUN = 1` when they do not compare `RUN` (section 8.2) |
| `defaults` | the encoded default of every encoded control-word field, in schema order |
| `field_assignments` | for every encoded field, in schema order, its assignments in the order made (section 8) |
| `selected_micro_operations` | each micro-operation the case selects, sorted by name, with the condition selecting it |
| `applicable_direct_control_definitions` | the direct-control definitions that can apply to the case, in definition order |

An assignment has `value`, the field's encoding, or `value_from_input`, the control input whose value the field takes. `when` is its condition, `origin` is one of `micro-operation mapping`, `conditional micro-operation mapping`, `direct-control definition` or `control-supplied value`, and `source` is the micro-operation or direct-control definition id.

Conditions are written in canonical form: every `AND` and `OR` is parenthesized, `NOT` is written `NOT (...)`, and a selection test that is decided outright is written `true` or `false`.

The candidate follows the shared output format: UTF-8 with LF line endings and one trailing newline, two-space indentation, non-ASCII characters written directly, and keys in the fixed order shown.

## 5. Expressions

Execution contexts and predicates, direct-control contexts, and timing-constraint contexts and requirements share one grammar:

| Form | Meaning |
|---|---|
| `NAME = VALUE`, `NAME != VALUE` | comparison |
| `MICRO_OP is selected`, `MICRO_OP is not selected` | selection test; direct-control contexts only |
| `NOT x`, `x AND y`, `x OR y`, `(x)` | logic; `NOT` binds tightest, then `AND`, then `OR` |

Keywords are case-insensitive. Two terms with no operator between them, such as the lines of a context block, are joined by `AND`.

A comparison may name a control input, an encoded control-word field, `MS`, or `TS`, and must compare it with a value in its domain:

| Name | Domain |
|---|---|
| control input with listed values | those values |
| control input without listed values | a binary string of exactly its width, within one of its `ranges` if it has any |
| encoded control-word field with listed values | their encodings |
| encoded control-word field without listed values | a binary string of exactly its width |
| `TS` | `1` to `4` |
| `MS` | the meanings of `MS_NEXT`'s values, such as `FETCH` |

A direct-control definition with several `applicable_context` entries applies when any of them holds.

Direct assignments and control-supplied values are `FIELD = VALUE` lines. `VALUE` is the field's encoding or the meaning of one of its listed values; for a field with no listed values, it is a binary string of at most the field's width or a decimal number below `2^width`, zero-filled to the width. A control-supplied value may instead name a control input.

## 6. Structural Validation

Any error stops the run before references are checked.

For every input:

- the identity property equal to the input's type: `specification_type` for the two schemas and the mapping, `artifact` for the others (`UNEXPECTED_ARTIFACT_TYPE`, naming the file)
- `control_design_version` equal to the control-word schema's, which must be a nonempty string (`CONTROL_DESIGN_VERSION_MISMATCH`, naming the file)
- an entries array of objects with nonempty, unique string ids (the input's own code, below)

Entry properties, reported with the input's own code, the entry id, and the property:

| Input | Code | Properties |
|---|---|---|
| control-input schema | `INVALID_CONTROL_INPUT_SCHEMA` | `width` a positive integer; `values` an array of `{value}` strings; `ranges` an array of `{start, end}` binary strings; `constraints` an array of objects; the top-level `constraints` an array of objects, with `inputs` a string array in each `exactly_one` and `at_most_one` constraint |
| control-word schema | `INVALID_CONTROL_WORD_SCHEMA` | `control_word_role` a nonempty string; for `encoded` fields, `width` a positive integer, `default_value` a nonempty string, and `values` an array of `{encoding, meaning}` strings |
| micro-operation mapping | `INVALID_MICRO_OPERATION_MAPPING` | `assignments` an array of `{field, value}` strings |
| execution definitions | `INVALID_EXECUTION_DEFINITIONS` | `source` `{path, line}`; `context` and `micro_operations` string arrays; `timing_state` 1 to 4 or null; `conditional_micro_operations` an array of `{predicate, micro_operation}` strings |
| direct-control definitions | `INVALID_DIRECT_CONTROL_DEFINITIONS` | `applicable_context`, `direct_assignments` and `control_supplied_values` string arrays |
| timing constraints | `INVALID_TIMING_CONSTRAINTS` | `context` and `requirement` nonempty strings |

Maintained symbolic artifact, when present:

- the same `control_design_version` as the control-word schema (`CONTROL_DESIGN_VERSION_MISMATCH`)
- a `cases` array of objects with nonempty, unique `execution_case_id` values (`INVALID_MAINTAINED_CASES`)

## 7. Reference Validation

Every expression and assignment in every input is checked, whether or not a case uses it. Any error stops the run before generation.

| Code | Condition |
|---|---|
| `INVALID_EXPRESSION` | an expression does not parse, or a selection test appears outside a direct-control context |
| `UNKNOWN_NAME` | a comparison names something other than a control input, an encoded control-word field, `MS` or `TS` |
| `INVALID_COMPARED_VALUE` | a comparison uses a value outside the name's domain (section 5); reported once per name and value in each expression |
| `UNKNOWN_MICRO_OPERATION` | an execution case or a selection test names a micro-operation with no mapping |
| `DUPLICATE_MICRO_OPERATION` | an execution case selects a micro-operation more than once, unconditionally or conditionally |
| `MISSING_APPLICABLE_CONTEXT` | a direct-control definition has no applicable context |
| `MALFORMED_ASSIGNMENT` | a direct assignment or control-supplied value line is not `FIELD = VALUE` |
| `UNKNOWN_CONTROL_FIELD` | a mapping, direct assignment or control-supplied value assigns something other than an encoded control-word field |
| `INVALID_FIELD_VALUE` | a default, mapping, direct assignment or control-supplied value is not a valid value of its field (section 5) |
| `RUN_INPUT_MISSING` | the control-input schema does not define `RUN`, so the run-mode context default (section 8.2) cannot be applied |
| `IR_DERIVATION_UNUSABLE` | an IR-derived input's documented derivation cannot be evaluated (section 8.1) |

Each diagnostic names the entry and, for expressions, the property holding it; for assignments, the field.

## 8. Generation

For each execution case:

1. Each unconditional micro-operation is selected under the base context; each conditional one under the base context `AND` its predicate.
2. Each selected micro-operation's mapping assignments are added, in selection order, with its selecting condition.
3. For each direct-control definition, in order, each selection test in its context is replaced by the condition selecting that micro-operation, or by `false` for `is selected` and `true` for `is not selected` when the case does not select it. The definition applies when the result can hold together with the base context (below). Its direct assignments and then its control-supplied values are added with the condition `base AND context`.

### 8.1 Reachable States

Two conditions can hold together when some state satisfies both and is reachable. A state is unreachable when:

- it sets both inputs of an exclusive pair to `1`; pairs come from input constraints reading `Mutually exclusive with X.` and from `exactly_one` and `at_most_one` global constraints
- it violates a timing constraint, meaning its context holds and its requirement does not
- it gives the IR-derived inputs values that no single IR value produces; for example, `IR_WRITES_DF = 1` with `IR_RESTORES_IB = 1`, or `IR_IS_MRI = 1` with `IR_IS_CAF = 1`

The IR-derived values come from evaluating each input's documented derivation ([IR-Derived Flags §1.1](../../../docs/04-control/10-control-input-definitions/02-ir-derived-fields.md#11-derivation-notation)) for all 4,096 IR values, using the shared `ir_derivation_table`. An input of the IR-Derived Signals domain whose derivation cannot be evaluated is an `IR_DERIVATION_UNUSABLE` error.

Each name ranges over every value it is compared with, in the conditions or in any timing constraint, plus one other value. The search does not use a name's full domain, so a state may give a name a value it cannot really take; for example, a one-bit input that is neither 0 nor 1. The check can therefore report a conflict that cannot occur, but never misses one.

### 8.2 Run-Mode Context Default

[Execution Model §2.3](../../../docs/03-microarchitecture/01-execution-model.md#23-run-mode-context-default) makes every context that does not compare `RUN` apply only while running. The generator applies it before generation:

- **Case base context:** the context lines and `TS = n`; when the result compares `RUN` nowhere, `AND RUN = 1` is added. An empty context becomes `RUN = 1`.
- **Conditional predicate:** when the case base already has `RUN = 1` as a top-level `AND` term, the predicate is used as written, since the base supplies the default. Otherwise a predicate that compares `RUN` nowhere gets `AND RUN = 1`.
- **Direct-control context:** each `applicable_context` alternative that compares `RUN` nowhere and contains no selection test gets `AND RUN = 1`. An alternative with a selection test takes its run mode from the case that selects the micro-operation.

A comparison of `RUN` anywhere, including inside `NOT (...)`, counts. The default appears explicitly in the generated `base_context` and `when` conditions.

### 8.3 Conflicts

`CONFLICTING_ASSIGNMENTS` is reported, naming the case and field, when two assignments to a field have different values, or take different inputs, or one takes an input and the other a fixed value, and their conditions can hold together. The message gives both assignments' values, origins, sources and conditions. Only the first conflict found for each field of a case is reported. Any conflict stops the candidate.

## 9. Review Against the Maintained Artifact

Each difference is reported as a warning for review before promotion:

| Code | Condition |
|---|---|
| `NEW_CASE` | a generated case is not in the maintained artifact |
| `CHANGED_CASE` | a generated case differs from the maintained one; the message lists the differing properties |
| `STALE_CASE` | a maintained case is no longer generated |

A run against a maintained artifact promoted from its own candidate reports no diagnostics.

## 10. Diagnostics

| Severity | Meaning | Effect |
|---|---|---|
| `WARNING` | a review difference (section 9) | candidate is written |
| `ERROR` | invalid input or a conflict (sections 6 to 8) | no candidate; exit status `1` |
| `FATAL` | an input file is missing, unreadable, not UTF-8, not JSON, or not a JSON object | no candidate; exit status `1` |

`INFO` is defined but not currently emitted. The only fatal code is `GENERATION_FAILURE`.

The report lists every diagnostic, one per line:

```text
SEVERITY CODE [entry-id] [field]: message
```

`[entry-id]` and `[field]` appear only when they apply. Diagnostics are sorted by severity, code, entry id, field, and message. The console repeats the errors and fatal errors.

## 11. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/symbolic-control-word-generator/src/generate_symbolic_control_words.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--artifact-dir DIRECTORY        default: rom/microcode/v1
--maintained INPUT_PATH         default: rom/microcode/v1/symbolic-control-words.json
--candidate-output OUTPUT_PATH  default: <output directory>/symbolic-control-words.candidate.json
--report-output OUTPUT_PATH     default: <output directory>/generation-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged. `--maintained` does not follow `--artifact-dir`.

The tool exits with status `1` when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise.

## 12. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/symbolic-control-word-generator/tests -p "test_*.py"
```

Tests build small inputs inline and use temporary directories; they do not read the real specifications. They cover the expression grammar, value encoding, every structural and reference error code, generation, conflicts and reachability, the review, report formatting, the contract with the upstream extractors, and complete runs through `main()`, including removal of earlier outputs and refused output paths.

Two end-to-end tests compare the report with expected files under `tests/golden/`: `review/` (new, changed, and stale cases) and `invalid/` (reference errors). After an intentional output change, regenerate them from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/symbolic-control-word-generator/tests -p "test_*.py"
```

On Windows PowerShell, set the variable first with `$env:UPDATE_GOLDEN = "1"` and remove it afterwards.

The contract tests read the golden outputs of the execution-definition, direct-control and timing-constraint extractors, whose entries the matching generators promote unchanged. They check that every golden entry passes this tool's entry checks and that the test builders have the same keys, in the same order. If an extractor's entry format changes, these tests fail until this tool and its builders are updated to match. The two schemas and the micro-operation mapping have no golden output yet and are not covered.

## 13. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- preserve deterministic ordering
- report malformed input without inventing replacements
- remain proportional to the bounded task

The implementation is one Python source file, `src/generate_symbolic_control_words.py`, organized in pipeline order: assignment blocks, reading inputs, structural validation, reference validation, generation, review, candidate construction, output, and the command line. The expression grammar (section 5), value domains, exclusive input pairs and the reachability check live in the shared module `tools/rom-generation/common/predicates.py`, so that every tool reads a predicate the same way.

## 14. Workflow

1. Update the documentation and promote the affected maintained specifications.
2. Run the symbolic control-word generator.
3. Resolve any errors, normally by correcting the documentation or a maintained specification.
4. Review the new, changed, and stale cases.
5. Promote the reviewed candidate to `rom/microcode/v1/symbolic-control-words.json`.

The generator never promotes its candidate.

## 15. Relationship to Later Stages

The control-word equivalence analyzer (`tools/rom-generation/control-word-equivalence-analyzer/`) reads the maintained artifact to find equivalent and aliased control words, unreachable assignments and regions, and which control inputs affect control behavior. Control-address packing and ROM image generation will consume it once they exist.
