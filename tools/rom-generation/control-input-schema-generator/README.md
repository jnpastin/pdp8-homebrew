# Control-Input Schema Generator

## 1. Purpose

The control-input schema generator creates a reviewed, maintained schema for the processor inputs available to control-rule evaluation and symbolic control-word construction.

The generator combines:

- the generated control-input extraction artifact
- an existing maintained control-input schema, when present

The generator produces a candidate schema for review.

The schema establishes the legal names, widths, domains, values, dependencies, and control-use classifications of inputs. It does not assign logical or physical ROM address bits.

## 2. Why This Stage Exists

The control-input extractor preserves documented input definitions, but later ROM-generation stages require a stable maintained contract.

The schema provides that contract for:

- predicates used to select control cases
- input-dependent values supplied to control outputs
- derived conditions used during rule evaluation
- validation of control-rule references
- later logical-address analysis

The schema must keep condition selection separate from value propagation. An input may provide a value used by an output without becoming an independent control-store address field.

## 3. Inputs

### 3.1 Generated Control-Input Catalog

Default path:

```text
build/simulation_outputs/rom-generation/control-input-extractor/control-inputs.json
```

The generated catalog provides the documented control-input definitions and source traceability. Its layout is described in the control-input extractor README.

The authoritative sources remain the documents under:

```text
docs/04-control/10-control-input-definitions/
```

### 3.2 Maintained Control-Input Schema

Default path:

```text
rom/microcode/v1/control-input-schema.json
```

The maintained schema contains reviewed decisions not safely inferred from documentation structure alone.

The generator reads only the maintained schema's header (`specification_type`, `schema_version`, `control_design_version`) and each field's `name` and `control_uses`. Every other property is refreshed from the extractor output. The maintained schema is normally a promoted candidate, so it contains those other properties too, but they are not read.

A missing or blank maintained schema is treated as absent. This is allowed during initial generation; every input is then unresolved.

The generator never writes the maintained schema.

## 4. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── control-input-schema-generator/
            ├── control-input-schema.candidate.json
            └── generation-report.txt
```

The report is written on every run. The candidate is written only when the run reports no `ERROR` or `FATAL` diagnostics.

Each run first deletes the candidate and report from any earlier run, so a candidate on disk always comes from the latest run, and that run succeeded (see the shared README, section 15.2). The tool refuses to run if an output path is one of its inputs or a directory.

Generated outputs:

- must not be edited manually
- must not be treated as authoritative source
- may be deleted and regenerated
- must be deterministic
- must preserve source traceability
- must be reviewed before promotion

## 5. Schema Boundary

The control-input schema defines what inputs exist and how later tools may use them.

It does not define:

- control rules
- micro-operation selection
- direct control outcomes
- symbolic control words
- logical control-store address packing
- physical ROM address packing
- binary ROM images

Logical address packing remains a later reviewed stage.

## 6. Input Uses

Each control input may serve one or more distinct uses.

### 6.1 Predicate Input

A predicate input participates in a control-rule condition.

Examples include:

- major state
- timing state
- decoded instruction properties
- processor flags
- external request flags

### 6.2 Value Input

A value input supplies data to a control output selected by a control case.

Examples include values such as an instruction field copied into a control-supplied data field.

A value input is not automatically an independent control-store address field.

### 6.3 Derived Input

A derived input is computed from other documented inputs or processor state.

A derived input may be used by rule predicates or as a value source, but the schema must preserve its derivation and dependencies.

Derived inputs must not be independently packed into a logical address unless a later reviewed address design explicitly requires that representation.

### 6.4 External Input

An external input originates outside the processor control unit.

The schema must preserve synchronization, polarity, and validity requirements documented for external inputs.

## 7. Maintained Classification

Each schema field contains a reviewed `control_uses` array.

Allowed values are:

```text
predicate
value
```

The array may contain either or both values, each at most once. An empty array is valid but means the input is still unresolved.

The extracted documentation determines whether an input is primitive, derived, or external. `control_uses` identifies how ROM-generation tools may consume it.

Example:

```json
{
  "name": "IR_DF",
  "control_uses": [
    "value"
  ]
}
```

Example:

```json
{
  "name": "ACZ",
  "control_uses": [
    "predicate"
  ]
}
```

The generator must not infer `control_uses` solely from the input name. It never infers `control_uses` at all; it only carries forward reviewed values.

## 8. Candidate Structure

The candidate uses this top-level structure:

```json
{
  "specification_type": "control-input-schema",
  "schema_version": 1,
  "control_design_version": "v1",
  "description": "Logical control-input schema for version 1 CPU control.",
  "source": {
    "specification_type": "control-input-extractor",
    "format_version": 1,
    "extraction_stage": "final-structure-validation"
  },
  "fields": [],
  "constraints": [],
  "diagnostics": []
}
```

| Property | Content |
|---|---|
| `fields` | one field per extracted input, in extracted order (section 9) |
| `constraints` | the extractor's global constraints (`exactly_one` / `at_most_one`), copied unchanged |
| `diagnostics` | the warnings found while building the candidate, in the order they were found (section 21) |

## 9. Field Structure

Each field uses this structure. The example is the actual field for `ACZ`, shortened:

```json
{
  "name": "ACZ",
  "category": null,
  "width": 1,
  "control_uses": ["predicate"],
  "attributes": {
    "display_name": "AC_IS_ZERO",
    "purpose": "Indicates whether the accumulator value is zero.",
    "source_register": "AC"
  },
  "polarity": {"source": "defaulted", "value": "active-high"},
  "domain": "Primitive Flags",
  "values": [
    {"meaning": "AC ≠ 0", "source": {"line": 67, "path": "docs/.../01-flags.md"}, "value": "0"},
    {"meaning": "AC = 0", "source": {"line": 68, "path": "docs/.../01-flags.md"}, "value": "1"}
  ],
  "ranges": [],
  "dependencies": [],
  "derivation": null,
  "constraints": [],
  "consumers": [
    {"source": {"line": 72, "path": "docs/.../01-flags.md"}, "target": "../../03-microarchitecture/02-micro-operations.md#pc_inc", "text": "PC_INC μop"}
  ],
  "sources": {
    "index": {"line": 35, "path": "docs/.../00-index.md"},
    "definition": {"heading": "ACZ", "line": 60, "path": "docs/.../01-flags.md"}
  }
}
```

Each property is taken from the extractor's signal:

| Field property | Extractor signal property |
|---|---|
| `name` | `name` |
| `category` | `category`: the index subcategory, `null` for domains without categories |
| `width` | `bit_width` |
| `control_uses` | the maintained field's `control_uses`, or `[]` |
| `attributes` | `attributes` |
| `polarity` | `polarity` |
| `domain` | `domain` |
| `values` | `enumerated_values` |
| `ranges` | `value_ranges` |
| `dependencies` | `dependencies` |
| `derivation` | the first non-empty of `logic.derivation`, `logic.expression`, `logic.internal_composition`, as a `{"text", "source"}` object, or `null` |
| `constraints` | `constraints`, per-input documented constraints |
| `consumers` | `consumers` |
| `sources.index` | `index_source` |
| `sources.definition` | `definition_source` |

Values are copied unchanged from the extractor output, including the extractor's key order within nested objects. The field properties themselves always appear in the order shown.

## 10. Candidate Generation

For each extracted control input:

1. Match an existing maintained field by exact input name.
2. Preserve the reviewed `control_uses` classification.
3. Refresh all extracted properties and source metadata.
4. Emit the candidate field in extracted input order.

If no maintained field exists, or its `control_uses` is empty:

- emit `control_uses` as an empty array
- report `CONTROL_USES_UNRESOLVED`

If a maintained field is absent from the current extraction:

- omit it from the candidate
- report `STALE_MAINTAINED_FIELD`

## 11. Extracted Properties

The generator preserves, when present:

- input name
- display name, purpose, type, mnemonic, and source register, within `attributes`
- category
- bit width
- polarity and its provenance
- legal enumerated values
- legal ranges
- dependencies
- derivation
- constraints
- consumers
- source traceability

The generator must not infer replacement values for missing extracted data.

## 12. Value Domains

An input domain is represented by either enumerated values or binary ranges. The extractor rejects definitions that mix the two.

Enumerated encodings must be preserved exactly as documented.

Ranges must retain their documented bounds and interpretation.

Later control-rule validation must reject values outside the maintained schema domain.

## 13. Predicate and Value Separation

Control rules must distinguish predicates from value bindings.

A predicate compares an input to a legal value:

```json
{
  "input": "MS",
  "equals": "EXECUTE"
}
```

A value binding supplies an input-dependent value to an output:

```json
{
  "field": "DF_VAL",
  "from_input": "IR_DF"
}
```

The schema validates both references, but the two mechanisms must not be collapsed.

A `from_input` binding does not imply that the source input is independently encoded in the logical control address.

## 14. Dependencies and Derivations

Derived inputs must retain:

- their derivation text
- their direct dependencies
- source traceability for the derivation

Each field carries a single derivation. When the extractor provides more than one logic section, the first non-empty section in the order `derivation`, `expression`, `internal_composition` is used.

The generator preserves derivation text without converting it into executable logic.

Later semantic validation may parse or evaluate supported derivation expressions.

The generator reports `UNDEFINED_DEPENDENCY` for any structured dependency name that is not an extracted input.

## 15. Consumers

Consumer references are documentation cross-references rather than control-use classifications.

They may identify:

- control decisions
- micro-operations
- sequencing behavior
- direct control outcomes

The generator must preserve consumer references for traceability and later completeness checks.

A consumer reference does not automatically prove that an input is a predicate, a value source, or an address component.

## 16. Input Validation

The generator validates the extractor artifact for:

- `format_version` equal to `1`
- `extraction_stage` equal to `final-structure-validation`
- an empty `diagnostics` array
- a `signals` array
- a `constraints` array
- global constraints with a known `kind`, at least two inputs, and only extracted input names
- signals that are objects with non-empty, unique names
- `extraction_status` equal to `structure-validated`
- positive integer bit widths
- `enumerated_values` arrays whose entries are objects with unique string `value`s
- `value_ranges` and `dependencies` arrays
- `definition_source` objects with string `path` and `heading` and integer `line`

The generator does not validate categories, attributes, polarity, range bounds, or the contents of consumers and constraints. Those are the extractor's responsibility.

Any extractor validation error prevents candidate construction.

## 17. Maintained Schema Validation

When present, the maintained schema is validated for:

- `specification_type` equal to `control-input-schema`
- `schema_version` equal to `1`
- `control_design_version` equal to `v1`
- a `fields` array
- fields that are objects with non-empty, unique names
- `control_uses` arrays containing only unique `predicate` and `value` entries

Any maintained-schema validation error prevents candidate construction.

## 18. Cross-Reference Validation

The generator validates structural cross-references that can be evaluated without interpreting prose:

- a dependency on an undefined input
- a global constraint naming an undefined input
- a maintained input absent from extraction
- a duplicate enumerated encoding
- a duplicate field name
- an invalid `control_uses` value

Consumer prose and derivation prose remain review material unless the extractor provides structured references.

## 19. Address-Packing Boundary

The schema must not contain physical bit positions or ROM addresses.

The schema also must not assume that every predicate input becomes one independently packed address field.

Later logical-address analysis will determine:

- which predicate distinctions must be represented
- whether derived predicates replace primitive combinations
- whether mutually exclusive domains can share encoding space
- how instruction subcategories are represented within `EXECUTE`
- whether some rules can be reduced before packing

That analysis consumes the completed control rules, not only the input catalog.

## 20. Deterministic Output

Given identical inputs, the generator produces identical output:

- field order follows extracted input order
- value, range, dependency, constraint, and consumer order is preserved from the extractor
- field properties appear in the fixed order of section 9; keys are not sorted
- JSON is indented by two spaces, with non-ASCII characters written directly
- output is UTF-8 with LF line endings and ends with one newline
- timestamps are not included
- the candidate contains only repository-relative paths

## 21. Diagnostics

Each diagnostic contains:

- severity
- diagnostic code
- explanatory message

and, when applicable:

- input name
- referenced input
- source path
- source line

In the candidate JSON, these are the properties `severity`, `code`, `message`, `input_name`, `referenced_input`, `source_path`, and `source_line`; properties without a value are omitted.

Severities:

| Severity | Meaning | Effect |
|---|---|---|
| `WARNING` | unresolved or stale reviewed classification | candidate is written |
| `ERROR` | invalid extractor or maintained-schema content, or an undefined dependency | no candidate; exit status `1` |
| `FATAL` | an input file is missing, unreadable, not UTF-8, not JSON, or not a JSON object | no candidate; exit status `1` |

`INFO` is defined but not currently emitted.

Warning codes are `CONTROL_USES_UNRESOLVED` and `STALE_MAINTAINED_FIELD`. The only fatal code is `GENERATION_FAILURE`. Every other code is an error.

Because a candidate is written only when there are no errors, the candidate's `diagnostics` array contains only warnings. It lists them in the order they were found: unresolved inputs in field order, then stale fields in maintained order.

The report lists every diagnostic, sorted by severity, code, source path, source line, input name, referenced input, and message.

## 22. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/control-input-schema-generator/src/generate_control_input_schema.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--input INPUT_PATH                 default: the extractor output (section 3.1)
--maintained-schema INPUT_PATH     default: rom/microcode/v1/control-input-schema.json
--candidate-output OUTPUT_PATH     default: <output directory>/control-input-schema.candidate.json
--report-output OUTPUT_PATH        default: <output directory>/generation-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics.

The tool exits with status `1` when any `ERROR` or `FATAL` diagnostic is reported, and with status `0` otherwise.

## 23. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/control-input-schema-generator/tests -p "test_*.py"
```

Tests build small extractor and maintained-schema documents inline and use temporary directories. They are grouped by stage:

- path resolution, argument defaults, and JSON reading, including missing, blank, invalid UTF-8, invalid JSON, non-object, and unreadable inputs
- extractor validation
- maintained-schema validation
- candidate construction: classification carry-forward, unresolved and stale fields, ordering, refreshed properties, derivation selection, global constraints, and undefined dependencies
- output formatting and report content, including diagnostic order
- the contract with the control-input extractor
- complete runs through `main()`

The contract tests read the extractor's golden output, `tools/rom-generation/control-input-extractor/tests/golden/valid/control-inputs.json`. They check that real extractor output builds a candidate, and that the test helpers' extractor-shaped data has the same keys as the real output. If the extractor's output format changes, these tests fail until this tool and its test helpers are updated to match.

Tests should cover representative behavior rather than every possible JSON permutation.

## 24. Implementation Constraints

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

The implementation remains in one Python source file, `src/generate_control_input_schema.py`, organized in pipeline order: reading inputs, extractor validation, maintained-schema validation, candidate construction, output, and the command line. Expected versions, stages, and allowed `control_uses` values are constants at the top of the module.

## 25. Workflow

The intended workflow is:

1. Update authoritative control-input documentation.
2. Run the control-input extractor.
3. Run the control-input schema generator.
4. Review unresolved and stale classifications.
5. Add or update `control_uses` in the maintained schema.
6. Regenerate the candidate.
7. Compare the candidate with the maintained schema.
8. Promote only reviewed changes.
9. Run the complete schema test suite.

The generator must never silently promote its candidate.

## 26. Relationship to Later Stages

The maintained control-input schema will be consumed by:

- direct-control outcome validation
- control-rule validation
- input-dependent output binding
- symbolic control-word generation
- logical control-address analysis

The later control-rule layer will combine:

```text
input predicates
+ selected micro-operations
+ direct control outcomes
+ input-dependent output bindings
```

The result is one complete symbolic control word for each control case.

## 27. Non-Goals

The schema generator does not:

- modify control-input documentation
- define control rules
- select micro-operations
- define direct control outcomes
- assign control outputs
- compose symbolic control words
- assign logical address bits
- assign physical ROM bits
- generate binary or hexadecimal ROM images

## 28. Completion Boundary

The initial stage is complete when the generator can:

- read the generated control-input catalog
- optionally read an existing maintained schema
- create one candidate field per extracted input
- preserve reviewed `control_uses`
- preserve extracted domains and traceability
- preserve global constraints
- identify unresolved new inputs
- identify stale maintained fields
- validate structural input references
- generate deterministic JSON
- generate a human-readable report
- pass the targeted automated tests

Defining direct control outcomes and control rules is the next stage after the maintained control-input schema is complete.
