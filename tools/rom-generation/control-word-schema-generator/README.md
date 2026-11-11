# Control-Word Schema Generator

## 1. Purpose

The control-word schema generator creates a candidate logical control-word schema for review.

The generator combines:

- the generated control-output extraction artifact
- an existing maintained control-word schema, when present

The schema establishes the legal names, categories, widths, encodings, defaults, and control-word roles of the processor's control outputs. It does not assign logical or physical ROM bit positions.

## 2. Authority

The documentation under `docs/` remains authoritative.

The control-output extractor output is a generated representation of the documented control-output definitions. It is not an authoritative control specification.

The maintained control-word schema under `rom/microcode/v1/` contains reviewed generation decisions. It must not introduce fields, encodings, default values, or constraints that are unsupported by the authoritative documentation.

Relevant documentation includes:

- [Control Word](../../../docs/04-control/04-control-word.md)
- [Control Constraints](../../../docs/04-control/03-control-constraints.md)
- [Microarchitectural Control Signals](../../../docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Architectural Control Signals](../../../docs/04-control/20-control-output-definitions/02-architectural-control-signals.md)
- [Sequencing Control Signals](../../../docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md)

## 3. Inputs

### 3.1 Generated Control-Output Catalog

Default path:

```text
build/simulation_outputs/rom-generation/control-output-extractor/control-outputs.json
```

The generated catalog provides the documented control-output definitions and source traceability. Its layout is described in the control-output extractor README.

The generator never parses the control-output documentation directly. Extraction, normalization, and documentation-level checks, such as whether a default value is a documented encoding, are the extractor's responsibility.

### 3.2 Maintained Control-Word Schema

Default path:

```text
rom/microcode/v1/control-word-schema.json
```

The maintained schema contains reviewed decisions not safely inferred from documentation structure alone.

The generator reads only the maintained schema's header (`specification_type`, `schema_version`, `control_design_version`) and each field's `name` and `control_word_role`. Every other property is refreshed from the extractor output. The maintained schema is normally a promoted candidate, so it contains those other properties too, but they are not read.

A missing or blank maintained schema is treated as absent. This is allowed during initial generation; every field's role is then unresolved.

The generator never writes the maintained schema.

## 4. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── control-word-schema-generator/
            ├── control-word-schema.candidate.json
            └── generation-report.txt
```

The report is written on every run. The candidate is written only when the run reports no `ERROR` or `FATAL` diagnostics.

A failed run does not delete a candidate left by an earlier successful run. Check the report's `Candidate written:` line, or the exit status, before reviewing a candidate file.

Generated outputs:

- must not be edited manually
- must not be treated as authoritative source
- may be deleted and regenerated
- must be deterministic
- must preserve source traceability
- must be reviewed before promotion

## 5. Schema Boundary

The control-word schema defines which control fields exist and what values they may take.

It does not define:

- micro-operation-to-field mappings
- direct control outcomes
- control rules or control-case expansion
- symbolic control words
- logical bit positions
- physical ROM bit positions or control-address packing
- binary ROM images

## 6. Control-Word Roles

Each schema field contains a reviewed `control_word_role`. Allowed values are:

| Role | Meaning | Example |
|---|---|---|
| `encoded` | the field is stored in the control word and assigned by micro-operations or direct control | `AC_LOAD` |
| `derived` | the field's value is formed from other fields or state, so it is not assigned directly | `IF_DF_COMBINED` |
| `external_input` | the field carries data driven from outside the control unit | `DB_INPUT` |

Later tools rely on the role. The micro-operation mapping generator and the direct-control generator reject assignments to fields that are not `encoded`, and the symbolic control-word generator builds words from `encoded` fields only.

The generator never infers a role. It only carries forward reviewed values.

## 7. Candidate Structure

The candidate uses this top-level structure:

```json
{
  "specification_type": "control-word-schema",
  "schema_version": 1,
  "control_design_version": "v1",
  "description": "Logical symbolic control-word schema for version 1 CPU control.",
  "source": {
    "specification_type": "control-output-extractor",
    "format_version": 1,
    "extraction_stage": "category-validation"
  },
  "fields": []
}
```

`fields` holds one field per extracted signal, in extracted order (section 8).

Diagnostics are not written to the candidate; they appear in the report only.

## 8. Field Structure

Each field uses this structure. The example is the actual field for `PC_SRC`, shortened:

```json
{
  "name": "PC_SRC",
  "category": "Select Signals",
  "width": 1,
  "control_word_role": "encoded",
  "default_value": "0",
  "explicit_value_required": "Conditionally",
  "value_required_when": "PC_LOAD=1",
  "attributes": {
    "display_name": "Program Counter Source Select",
    "mnemonic": "PC_SRC",
    "purpose": "Selects the input source for PC.",
    "signal_class": "Select"
  },
  "values": [
    {"encoding": "0", "meaning": "IDB", "source": {"document": "docs/.../01-microarchitectural-control-signals.md", "line": 1810}},
    {"encoding": "1", "meaning": "Control", "source": {"document": "docs/.../01-microarchitectural-control-signals.md", "line": 1811}}
  ],
  "constraints": [
    {"text": "When PC_LOAD = 1:", "source": {"document": "docs/.../01-microarchitectural-control-signals.md", "line": 1815}}
  ],
  "used_by_micro_operations": [
    {"micro_operation": "FP_SR_TO_PC", "value": "0", "source": {"document": "docs/.../01-microarchitectural-control-signals.md", "line": 1819}}
  ],
  "sources": {
    "index": {"document": "docs/.../00-index.md", "line": 75},
    "definition": {"document": "docs/.../01-microarchitectural-control-signals.md", "section": "PC_SRC", "line": 1796}
  }
}
```

Each property is taken from the extractor's signal, where `definition` is the signal's `definition` object:

| Field property | Extractor signal property |
|---|---|
| `name` | `name` |
| `category` | `category` |
| `width` | `definition.bit_width` |
| `control_word_role` | the maintained field's `control_word_role`, or `null` |
| `default_value` | `definition.attributes.default_value`, or `null` when it is `N/A` |
| `explicit_value_required` | `definition.attributes.explicit_value_required` |
| `value_required_when` | `definition.attributes.value_required_when` |
| `attributes` | `definition.attributes`, without the three properties above |
| `values` | `definition.encodings`, with `value` renamed `encoding` |
| `constraints` | `definition.constraints` |
| `used_by_micro_operations` | `definition.used_by_micro_operations`; `value` is present only when the extractor provides it |
| `sources.index` | `source` |
| `sources.definition` | `definition.source`, with `definition.heading` as `section` |

Every source reference is converted from the extractor's `{"path", "line"}` form to `{"document", "line"}`. Paths stay repository-relative.

Values are copied unchanged otherwise. Encodings keep their documented octal digits and are not converted between bases. The field properties, and the properties of each value, constraint, use, and source, always appear in the order shown.

`default_value` is `null` only when the documentation states `N/A`, which it does for fields that are never assigned a default, such as `derived` and `external_input` fields. The generator does not infer a default from the encodings.

## 9. Candidate Generation

For each extracted signal:

1. Match an existing maintained field by exact name.
2. Preserve the reviewed `control_word_role`.
3. Refresh all extracted properties and source metadata.
4. Emit the candidate field in extracted signal order.

If no maintained field exists:

- emit `control_word_role` as `null`
- report `CONTROL_WORD_ROLE_UNRESOLVED`

If a maintained field is absent from the current extraction:

- omit it from the candidate
- report `STALE_MAINTAINED_FIELD`

## 10. Input Validation

The generator validates the extractor artifact for:

- `format_version` equal to `1`
- `extraction_stage` equal to `category-validation`
- an empty `diagnostics` array
- a `signals` array
- signals that are objects with non-empty, unique names
- a non-empty `category`
- `extraction_status` equal to `category-validated`
- a `definition` object with a non-empty `heading` and an `attributes` object
- non-empty string `default_value` and `value_required_when` attributes
- an `explicit_value_required` attribute of `Yes`, `No`, or `Conditionally`
- a positive integer `bit_width`
- an `encodings` array whose entries are objects with a non-empty `meaning` and a unique `value` made of octal digits that fits in `bit_width`
- a `used_by_micro_operations` array whose entries name a micro-operation, with a non-empty `value` when one is present
- a `constraints` array whose entries are objects with non-empty `text`
- source references, on the signal, the definition, and every encoding, use, and constraint, with a non-empty `path` and a positive integer `line`

Only the first problem is reported for a signal that is not an object or has no usable name, and for a use that is not an object or names no micro-operation. Every other check runs independently, so one run reports every problem it can find.

The generator does not check that a default value is one of the field's encodings, or interpret constraint prose. The extractor checks default values against the documentation.

Any extractor validation error prevents candidate construction.

## 11. Maintained Schema Validation

When present, the maintained schema is validated for:

- `specification_type` equal to `control-word-schema`
- `schema_version` equal to `1`
- `control_design_version` equal to `v1`
- a `fields` array
- fields that are objects with non-empty, unique names
- a `control_word_role` of `encoded`, `derived`, or `external_input` on every field

Any maintained-schema validation error prevents candidate construction.

## 12. Deterministic Output

Given identical inputs, the generator produces identical output:

- field order follows extracted signal order
- value, constraint, and use order is preserved from the extractor
- properties appear in the fixed order of section 8; keys are not sorted
- JSON is indented by two spaces, with non-ASCII characters written directly
- output is UTF-8 with LF line endings and ends with one newline
- timestamps are not included
- the candidate contains only repository-relative paths

## 13. Diagnostics

Each diagnostic contains:

- severity
- diagnostic code
- explanatory message

and, when applicable:

- field name
- source path
- source line

Severities:

| Severity | Meaning | Effect |
|---|---|---|
| `WARNING` | unresolved or stale reviewed role | candidate is written |
| `ERROR` | invalid extractor or maintained-schema content | no candidate; exit status `1` |
| `FATAL` | an input file is missing, unreadable, not UTF-8, not JSON, or not a JSON object | no candidate; exit status `1` |

`INFO` is defined but not currently emitted.

Warning codes are `CONTROL_WORD_ROLE_UNRESOLVED` and `STALE_MAINTAINED_FIELD`. The only fatal code is `GENERATION_FAILURE`. Every other code is an error.

The report lists every diagnostic, one per line, as:

```text
SEVERITY CODE [field] path:line: message
```

`-` stands in for a missing field name, and the location is left out when it is unknown. Diagnostics are sorted by severity, code, source path, source line, field name, and message.

## 14. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/control-word-schema-generator/src/generate_control_word_schema.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--input INPUT_PATH                 default: the extractor output (section 3.1)
--maintained-schema INPUT_PATH     default: rom/microcode/v1/control-word-schema.json
--candidate-output OUTPUT_PATH     default: <output directory>/control-word-schema.candidate.json
--report-output OUTPUT_PATH        default: <output directory>/generation-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics.

The tool exits with status `1` when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise.

## 15. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/control-word-schema-generator/tests -p "test_*.py"
```

Tests build small extractor and maintained-schema documents inline and use temporary directories. They are grouped by stage:

- path resolution, argument defaults, and JSON reading, including missing, blank, invalid UTF-8, invalid JSON, non-object, and unreadable inputs
- extractor validation, covering every error code
- maintained-schema validation
- candidate construction: the complete field structure and key order, role carry-forward, unresolved and stale fields, `N/A` defaults, and ordering
- report content and diagnostic formatting
- the contract with the control-output extractor
- complete runs through `main()`, including diagnostic order in the report

The contract tests read the extractor's golden output, `tools/rom-generation/control-output-extractor/tests/golden/valid/control-outputs.json`. They check that real extractor output builds a candidate, and that the test helpers' extractor-shaped data has the same keys, in the same order, as the real output. If the extractor's output format changes, these tests fail until this tool and its test helpers are updated to match.

Tests should cover representative behavior rather than every possible JSON permutation.

## 16. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- preserve repository-relative paths
- preserve deterministic ordering
- retain source traceability
- report malformed input without inventing replacements
- report malformed input as diagnostics rather than failing with an exception
- remain proportional to the bounded schema task

The implementation remains in one Python source file, `src/generate_control_word_schema.py`, organized in pipeline order: reading inputs, extractor validation, maintained-schema validation, candidate construction, output, and the command line. Expected versions, stages, and allowed roles are constants at the top of the module.

## 17. Workflow

The intended workflow is:

1. Update the authoritative control-output documentation.
2. Run the control-output extractor and review its report.
3. Run the control-word schema generator and review its report.
4. Set `control_word_role` in the maintained schema for unresolved fields, and remove stale ones.
5. Regenerate the candidate.
6. Compare the candidate with the maintained schema.
7. Promote only reviewed changes to `rom/microcode/v1/control-word-schema.json`.
8. Run the applicable automated tests.

The generator must never silently promote its candidate, because extraction alone does not constitute review or approval of a maintained generation decision.

## 18. Relationship to Later Stages

The maintained control-word schema is consumed by:

- the micro-operation mapping generator
- the direct-control generator
- the symbolic control-word generator

Logical bit assignment, address packing, and ROM-image generation belong to later stages.

## 19. Completion Boundary

The initial stage is complete when the generator can:

- read the generated control-output catalog
- optionally read an existing maintained schema
- create one candidate field per extracted signal
- preserve reviewed `control_word_role` values
- preserve extracted encodings, defaults, constraints, uses, and traceability
- identify unresolved new fields
- identify stale maintained fields
- reject structurally invalid input
- generate deterministic JSON
- generate a human-readable report
- pass the targeted automated tests
