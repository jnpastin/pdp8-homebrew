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

The generated catalog provides the documented control-input definitions and source traceability.

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

The file may be missing during initial generation.

The generator must not overwrite it automatically.

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

The array may contain either or both values.

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

The generator must not infer `control_uses` solely from the input name.

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
  "diagnostics": []
}
```

## 9. Field Structure

Each field uses this structure:

```json
{
  "name": "ACZ",
  "category": "Primitive Flags",
  "width": 1,
  "control_uses": [
    "predicate"
  ],
  "polarity": "active-high",
  "domain": "Primitive Flags",
  "values": [
    {
      "encoding": "0",
      "meaning": "AC is nonzero"
    },
    {
      "encoding": "1",
      "meaning": "AC is zero"
    }
  ],
  "ranges": [],
  "dependencies": [],
  "derivation": null,
  "constraints": [],
  "sources": {
    "index": {},
    "definition": {}
  }
}
```

This example defines structure only. Values must be copied from the generated extractor output.

## 10. Candidate Generation

For each extracted control input:

1. Match an existing maintained field by exact input name.
2. Preserve the reviewed `control_uses` classification.
3. Refresh all extracted properties and source metadata.
4. Emit the candidate field in extracted input order.

If no maintained field exists:

- emit `control_uses` as an empty array
- report `CONTROL_USES_UNRESOLVED`

If a maintained field is absent from the current extraction:

- omit it from the candidate
- report `STALE_MAINTAINED_FIELD`

## 11. Extracted Properties

The generator must preserve, when present:

- input name
- display name
- category
- bit width
- purpose
- source register or external source
- polarity
- legal enumerated values
- legal ranges
- dependencies
- derivation
- constraints
- consumers
- source traceability

The generator must not infer replacement values for missing extracted data.

## 12. Value Domains

An input domain may be represented by:

- enumerated values
- numeric ranges
- a combination explicitly supported by the input documentation

Enumerated encodings must be preserved exactly as documented.

Ranges must retain their documented bounds and interpretation.

Reserved or invalid values must remain identifiable.

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

- their derivation expression
- their direct dependencies
- source traceability for the derivation

The generator preserves derivation text without converting it into executable logic in the initial implementation.

Later semantic validation may parse or evaluate supported derivation expressions.

The initial schema generator must detect references to undefined dependencies when the extractor provides structured dependency names.

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

The generator must validate the extractor artifact for:

- supported format version
- expected extraction stage
- empty extractor diagnostics
- presence of the signals array
- unique input names
- expected extraction status
- valid bit widths
- valid categories
- valid enumerated values
- valid ranges
- valid dependencies
- valid source traceability

Invalid extractor input must prevent candidate generation when reliable processing is not possible.

## 17. Maintained Schema Validation

The maintained schema must be validated for:

- expected specification type
- supported schema version
- matching control-design version
- presence of the fields array
- unique field names
- valid `control_uses` arrays
- recognized `control_uses` values

A missing maintained schema is allowed during initial generation.

## 18. Cross-Reference Validation

The initial generator should validate structural cross-references that can be evaluated without interpreting prose.

Validation should detect:

- a dependency on an undefined input
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

Given identical inputs, the generator must produce identical output.

To preserve determinism:

- field order must follow extracted input order
- value order must follow documented order
- dependency order must be preserved
- constraint order must be preserved
- object property order must be consistent
- JSON indentation must be consistent
- output must use UTF-8
- output must end with one newline
- timestamps must not be included
- absolute paths must not be included

## 21. Diagnostics

Each diagnostic should contain:

- severity
- diagnostic code
- input name when applicable
- referenced input when applicable
- source path when available
- source line when available
- explanatory message

Supported severities are:

- `INFO`
- `WARNING`
- `ERROR`
- `FATAL`

Warnings identify unresolved or stale reviewed classifications that do not prevent candidate construction.

Errors identify invalid input that prevents reliable candidate generation.

## 22. Command-Line Interface

The intended command form is:

```text
python tools/rom-generation/control-input-schema-generator/src/generate_control_input_schema.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides should include:

```text
--input INPUT_PATH
--maintained-schema INPUT_PATH
--candidate-output OUTPUT_PATH
--report-output OUTPUT_PATH
```

Relative paths must be resolved from the supplied repository root.

Absolute paths must be used unchanged.

## 23. Testing

Tests must use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/control-input-schema-generator/tests -p "test_*.py"
```

Required test coverage includes:

- repository-relative path resolution
- absolute-path preservation
- missing required input handling
- missing maintained schema handling
- invalid UTF-8 handling
- invalid JSON handling
- unsupported format versions
- unexpected extraction stages
- extractor diagnostics handling
- duplicate input names
- invalid bit widths
- duplicate enumerated encodings
- maintained classification preservation
- unresolved new inputs
- stale maintained fields
- invalid `control_uses` values
- extracted field ordering
- source metadata refresh
- deterministic candidate output
- diagnostic-report generation
- complete command-line execution

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
- remain proportional to the bounded schema task

The initial implementation should remain in one Python source file.

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
- identify unresolved new inputs
- identify stale maintained fields
- validate structural input references
- generate deterministic JSON
- generate a human-readable report
- pass the targeted automated tests

Defining direct control outcomes and control rules is the next stage after the maintained control-input schema is complete.
