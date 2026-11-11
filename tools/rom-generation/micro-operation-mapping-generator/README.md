# Micro-Operation Mapping Generator

## 1. Purpose

The micro-operation mapping generator creates a candidate mapping from each documented micro-operation to the symbolic control-field assignments that implement it.

The assignments come from the `Used by μops` lists in the control-output documentation, as carried into the maintained control-word schema. The generator gathers them per micro-operation, checks them against the schema and the micro-operation catalog, and writes a candidate for review.

The generator does not:

- decide which control fields implement a micro-operation; the documentation does
- select which micro-operations execute
- compose complete control words
- assign sequencing outcomes
- determine control-address packing
- generate ROM images

## 2. Inputs

### 2.1 Micro-Operation Catalog

Default path:

```text
build/simulation_outputs/rom-generation/micro-operation-extractor/micro-operations.json
```

The micro-operation extractor's output. The generator uses each micro-operation's `name` and `source`, and checks that the other properties are present. Its layout is described in the micro-operation extractor README.

The authoritative source remains [Micro-Operations](../../../docs/03-microarchitecture/02-micro-operations.md).

### 2.2 Control-Word Schema

Default path:

```text
rom/microcode/v1/control-word-schema.json
```

The maintained control-word schema, promoted from the control-word schema generator's candidate. For each field the generator uses:

| Property | Use |
|---|---|
| `name` | the assigned field |
| `control_word_role` | only `encoded` fields may be assigned |
| `values`, `width` | the legal values (section 4.3) |
| `used_by_micro_operations` | the micro-operations that assign the field, and the value each assigns |
| `explicit_value_required`, `value_required_when` | validated only (section 7.2) |

The authoritative definitions remain:

- [Microarchitectural Control Signals](../../../docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Architectural Control Signals](../../../docs/04-control/20-control-output-definitions/02-architectural-control-signals.md)
- [Sequencing Control Signals](../../../docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md)

### 2.3 Maintained Micro-Operation Mapping

Default path:

```text
rom/microcode/v1/micro-operation-mapping.json
```

The reviewed mapping, normally a promoted candidate. The generator reads its header, and each mapping's `micro_operation`, `assignments` and `notes`:

- `notes` are carried into the candidate unchanged.
- An assignment's value is used only when the schema's Used-by entry for that field gives no value (section 4.1).

A missing or blank maintained mapping is treated as absent. This is allowed during initial generation.

The generator never writes the maintained mapping.

## 3. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── micro-operation-mapping-generator/
            ├── micro-operation-mapping.candidate.json
            └── generation-report.txt
```

Each run first deletes the candidate and report from any earlier run, so a candidate on disk always comes from the latest run, and that run succeeded (see the shared README, section 15.2). The tool refuses to run if an output path is one of its inputs or a directory.

The report is written on every run. The candidate is written only when the run reports no `ERROR` or `FATAL` diagnostics.

Generated outputs:

- must not be edited manually
- must not be treated as maintained source
- may be deleted and regenerated
- must be reviewed before promotion

## 4. Assignment Derivation

### 4.1 Source of Assignments

A micro-operation's assignments are the schema fields whose `used_by_micro_operations` names it. In the documentation this is the field's `Used by μops` list:

```markdown
**Used by μops:**
- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear) = 1
```

The value after `=` becomes the assignment value. When a Used-by entry gives no value, the value of the same field's assignment in the maintained mapping is used instead. With neither, the assignment is reported as `MAPPING_VALUE_UNRESOLVED`.

The generator never infers an assignment from a micro-operation's name, expression, targets, or sources.

### 4.2 Order

Assignments follow the schema's field order. Mappings follow the micro-operation catalog's order.

### 4.3 Checks on Each Assignment

- The field must have `control_word_role` equal to `encoded`. Derived and external-input fields may not be assigned (`NON_ENCODED_ASSIGNMENT`).
- The value must be legal for the field (`INVALID_ASSIGNED_VALUE`). A field with `values` allows their encodings, except those whose meaning is `reserved` or `invalid`. A field without `values` allows every octal value its `width` can hold.

Every Used-by entry must name a micro-operation in the catalog (`UNDEFINED_USED_BY_MICRO_OPERATION`). A misspelled name would otherwise silently drop an assignment.

### 4.4 Changes from the Maintained Mapping

When a micro-operation has a maintained mapping, its new assignments are compared with the maintained ones. Promoting the candidate would apply any difference, so each is reported as a warning for review:

- `MAINTAINED_ASSIGNMENT_REMOVED`: a maintained assignment's field is no longer produced by the Used-by lists
- `MAINTAINED_ASSIGNMENT_CHANGED`: a field is still assigned, but with a different value
- `MAINTAINED_ASSIGNMENT_ADDED`: a field is assigned that the maintained mapping does not assign

Removed and changed assignments are listed in maintained order, then added ones in candidate order. A micro-operation with no maintained mapping is not compared; it is new, and promotion adds its whole mapping.

## 5. Mapping Scope

A mapping holds only the control-field assignments that implement one micro-operation. It does not define:

- the control-input conditions that select the micro-operation
- the major state or timing state in which it executes
- sequencing outcomes
- direct control outcomes that are not part of the micro-operation
- a complete control word

Fields a mapping does not assign take their canonical defaults when complete control words are composed later:

```text
canonical control-field defaults
+ selected micro-operation mappings
+ direct control outcomes
+ sequencing outcomes
```

Control behavior that is not a micro-operation, such as major-state sequencing, RUN and halt-request updates, architectural strobes, and initialization, belongs to the direct-control and sequencing specifications. It must not be represented as a fabricated micro-operation.

## 6. Candidate Structure

```json
{
  "specification_type": "micro-operation-mapping",
  "schema_version": 1,
  "control_design_version": "v1",
  "description": "Maps documented micro-operations to symbolic control-field assignments.",
  "sources": {
    "micro_operations": "build/simulation_outputs/rom-generation/micro-operation-extractor/micro-operations.json",
    "control_word_schema": "rom/microcode/v1/control-word-schema.json"
  },
  "mappings": [],
  "diagnostics": []
}
```

`sources` always names the default input paths, even when other paths are given on the command line.

`diagnostics` holds the warnings found while building the candidate, in the order they were found: for each micro-operation in catalog order, its changes from the maintained mapping and then whether it is unresolved; then stale mappings in maintained order. A candidate is written only without errors, so it never contains errors. Each diagnostic has `severity`, `code` and `message`, plus `micro_operation`, `field_name`, `source_path` and `source_line` when known.

Each mapping uses this structure. The example is the actual mapping for `AC_CLEAR`, shortened:

```json
{
  "micro_operation": "AC_CLEAR",
  "assignments": [
    {"field": "AC_LOAD", "value": "1"},
    {"field": "IDB_DRIVE", "value": "1"},
    {"field": "AC_SRC", "value": "0"}
  ],
  "source": {
    "document": "docs/03-microarchitecture/02-micro-operations.md",
    "section": "AC_CLEAR",
    "line": 184
  },
  "notes": []
}
```

| Property | Content |
|---|---|
| `micro_operation` | the micro-operation name |
| `assignments` | `{"field", "value"}` pairs (section 4) |
| `source` | the micro-operation's `source`, with `path` as `document` and `heading` as `section`, refreshed on every run |
| `notes` | the maintained mapping's notes, or `[]` |

The properties always appear in the order shown; keys are not sorted.

## 7. Validation

Each input is validated in full on every run, so one run reports every structural problem it can find. Any validation error prevents candidate construction.

### 7.1 Micro-Operation Catalog

- `format_version` equal to `1`
- `extraction_stage` equal to `definition-validation`
- an empty `diagnostics` array
- a `micro_operations` array of objects with non-empty, unique names
- `extraction_status` equal to `definition-validated`
- every extracted property present: `category`, `description`, `targets`, `expression`, `sources`, `preconditions`, `constraints`, `source`
- a `source` with string `path` and `heading` and integer `line`

### 7.2 Control-Word Schema

- `specification_type` equal to `control-word-schema`
- `schema_version` equal to `1`
- `control_design_version` equal to `v1`
- a `fields` array of objects with non-empty, unique names
- a `control_word_role` of `encoded`, `derived`, or `external_input`
- an `explicit_value_required` of `Yes`, `No`, or `Conditionally`
- a string `value_required_when`
- a `used_by_micro_operations` array of objects, each naming a micro-operation at most once per field, with a non-empty string `value` when one is present

### 7.3 Maintained Mapping

When present:

- `specification_type` equal to `micro-operation-mapping`
- `schema_version` equal to `1`
- `control_design_version` equal to `v1`
- a `mappings` array of objects with non-empty, unique `micro_operation` names
- an `assignments` array whose entries have non-empty string `field` and `value`
- a `notes` array

## 8. Validation Boundary

The generator does not prove that:

- the assignments implement the micro-operation's expression
- every documented target and source is covered
- every field whose explicit value is required has been assigned, or every `Value Required When` condition is met
- preconditions hold or constraints are satisfied
- two individually valid mappings may execute together
- a composed control word is legal

Those checks belong to later semantic validation and control-word composition.

## 9. Diagnostics

Severities:

| Severity | Meaning | Effect |
|---|---|---|
| `WARNING` | an unresolved or stale mapping, or a change from the maintained mapping | candidate is written |
| `ERROR` | invalid input, a Used-by entry naming an unknown micro-operation, or an assignment that is unresolved, to a non-encoded field, or illegal | no candidate; exit status `1` |
| `FATAL` | an input file is missing, unreadable, not UTF-8, not JSON, or not a JSON object | no candidate; exit status `1` |

`INFO` is defined but not currently emitted.

Warning codes:

| Code | Condition |
|---|---|
| `MAPPING_UNRESOLVED` | no Used-by entry names the micro-operation, so it has no assignments |
| `STALE_MAINTAINED_MAPPING` | a maintained mapping names a micro-operation absent from the catalog; it is left out of the candidate |
| `MAINTAINED_ASSIGNMENT_REMOVED` | a maintained assignment is no longer produced (section 4.4) |
| `MAINTAINED_ASSIGNMENT_CHANGED` | a maintained assignment's value changes (section 4.4) |
| `MAINTAINED_ASSIGNMENT_ADDED` | an assignment is not in the maintained mapping (section 4.4) |

The only fatal code is `GENERATION_FAILURE`. Every other code is an error.

The report lists every diagnostic, one per line:

```text
SEVERITY CODE [micro-operation] [field]: message
```

`[field]` appears only when a field applies, and `-` stands in for a missing micro-operation name. Diagnostics are sorted by severity, code, source path, source line, micro-operation, field, and message. The console repeats the errors with their source locations.

## 10. Deterministic Output

Given identical inputs, the generator produces identical output:

- mappings follow catalog order, and assignments follow schema field order
- notes keep their maintained order
- properties appear in the fixed order of section 6; keys are not sorted
- JSON is indented by two spaces, with non-ASCII characters written directly
- output is UTF-8 with LF line endings and ends with one newline
- timestamps and absolute paths are not included

## 11. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/micro-operation-mapping-generator/src/generate_micro_operation_mapping.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--micro-operations INPUT_PATH       default: the extractor output (section 2.1)
--control-word-schema INPUT_PATH    default: rom/microcode/v1/control-word-schema.json
--maintained-mapping INPUT_PATH     default: rom/microcode/v1/micro-operation-mapping.json
--candidate-output OUTPUT_PATH      default: <output directory>/micro-operation-mapping.candidate.json
--report-output OUTPUT_PATH         default: <output directory>/generation-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics, and exits with status `1` when any are reported, `0` otherwise.

## 12. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/micro-operation-mapping-generator/tests -p "test_*.py"
```

Tests build small inputs inline and use temporary directories. They are grouped by stage:

- path resolution, argument defaults, and JSON reading
- validation of each input, covering every error code
- legal-value rules
- candidate construction: the complete candidate structure, assignment and mapping order, Used-by and maintained values, every assignment error, changes from the maintained mapping, and unresolved and stale mappings
- report and console formatting
- contracts with the upstream tools
- complete runs through `main()`, including diagnostic order, removal of earlier outputs, and refused output paths

The contract tests use real upstream output. The micro-operation catalog is the micro-operation extractor's golden file. The schema is built by running the control-word schema generator on the control-output extractor's golden file. The tests check that both pass validation, that they build a candidate, and that the test builders have the same keys, in the same order, as the real data. If an upstream output format changes, these tests fail until this tool and its builders are updated to match.

## 13. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- preserve repository-relative paths
- preserve deterministic ordering
- retain source traceability
- report malformed input without inventing replacements
- remain proportional to the bounded mapping task

The implementation is one Python source file, `src/generate_micro_operation_mapping.py`, organized in pipeline order: reading inputs, validation of each input, candidate construction, output, and the command line. Expected versions, stages, roles, and required properties are constants at the top of the module.

## 14. Workflow

1. Update the micro-operation or control-output documentation, including the `Used by μops` lists.
2. Run the micro-operation extractor and the control-output extractor.
3. Run the control-word schema generator and promote its reviewed candidate.
4. Run the micro-operation mapping generator.
5. Resolve any errors, normally by correcting the documentation.
6. Compare the candidate with the maintained mapping, and add or update notes in the maintained mapping where needed.
7. Promote only reviewed changes to `rom/microcode/v1/micro-operation-mapping.json`.
8. Run the applicable automated tests.

The generator never promotes its candidate.

## 15. Relationship to Later Stages

The maintained mapping is read by:

- the direct-control generator, when validating direct-control definitions
- the symbolic control-word generator, which composes each control case's selected micro-operation mappings with direct-control and sequencing outcomes into complete symbolic control words
