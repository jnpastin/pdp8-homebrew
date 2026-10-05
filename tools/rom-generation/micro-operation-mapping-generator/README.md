# Micro-Operation Mapping Generator

## 1. Purpose

The micro-operation mapping generator creates and validates a candidate mapping between documented micro-operations and symbolic control-field assignments.

The generator combines:

- the extracted micro-operation catalog
- the maintained control-word schema
- the existing maintained micro-operation mapping, when present

The generator produces a candidate mapping for review.

The generator does not:

- select which micro-operations execute
- generate complete control cases
- assign sequencing outcomes
- determine control-address packing
- generate binary ROM images

## 2. Authoritative and Maintained Inputs

The generator uses three inputs with different authority boundaries.

### 2.1 Extracted Micro-Operation Catalog

Default path:

```text
build/simulation_outputs/rom-generation/micro-operation-extractor/micro-operations.json
```

This generated file provides:

- the complete documented micro-operation list
- micro-operation categories
- targets
- sources
- expressions
- preconditions
- constraints
- source traceability

The authoritative source remains [Micro-Operations](../../../docs/03-microarchitecture/02-micro-operations.md).

### 2.2 Maintained Control-Word Schema

Default path:

```text
rom/microcode/v1/control-word-schema.json
```

This maintained file provides:

- control-field names
- control-word roles
- legal field encodings
- canonical default values
- explicit-value requirements
- value-validity conditions
- control-output constraints
- source traceability

The authoritative definitions remain:

- [Microarchitectural Control Signals](../../../docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md)
- [Architectural Control Signals](../../../docs/04-control/20-control-output-definitions/02-architectural-control-signals.md)
- [Sequencing Control Signals](../../../docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md)

### 2.3 Maintained Micro-Operation Mapping

Default path:

```text
rom/microcode/v1/micro-operation-mapping.json
```

This file contains reviewed implementation decisions that associate each documented micro-operation with exact symbolic control-field assignments.

The file may be missing or empty during initial generation.

The generator must not overwrite it automatically.

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

Generated outputs:

- must not be edited manually
- must not be treated as maintained source
- may be deleted and regenerated
- must be deterministic
- must preserve source traceability
- must be reviewed before promotion

## 4. Maintained Mapping Structure

The maintained mapping uses this top-level structure:

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
  "mappings": []
}
```

Each mapping uses this structure:

```json
{
  "micro_operation": "PC_INC",
  "assignments": [
    {
      "field": "ALU_OP",
      "value": "2"
    },
    {
      "field": "ALU_A_SRC",
      "value": "2"
    },
    {
      "field": "PC_INC",
      "value": "1"
    }
  ],
  "source": {
    "document": "docs/03-microarchitecture/02-micro-operations.md",
    "section": "PC_INC",
    "line": 1339
  },
  "notes": []
}
```

The values in this example define structure only. Actual assignments must use values permitted by the maintained control-word schema.

## 5. Mapping Scope

A micro-operation mapping defines only the control-field assignments required to implement one documented micro-operation.

A mapping does not define:

- the control-input conditions that select the micro-operation
- the major state in which the micro-operation executes
- the timing state in which the micro-operation executes
- sequencing outcomes
- unrelated architectural strobes
- direct control outcomes that are not implementations of the micro-operation
- a complete control word

Complete control words are created later by composing:

```text
canonical control-field defaults
+ selected micro-operation mappings
+ direct control outcomes
+ sequencing outcomes
```

## 6. Control Behavior Without a Micro-Operation

Not every control outcome corresponds to a micro-operation.

Examples may include:

- major-state sequencing
- RUN state updates
- halt-request updates
- architectural strobes
- external interface qualification
- initialization behavior
- other direct control outcomes defined outside the micro-operation catalog

Such behavior must not be represented using fabricated micro-operations.

Direct control outcomes will be represented in later execution and sequencing specifications.

The rule governing mapping references is therefore:

- every micro-operation mapping must reference an extracted micro-operation
- not every complete control word must contain a micro-operation
- not every control-field assignment must originate from a micro-operation mapping

## 7. Assignment Representation

Each assignment identifies:

- one encoded control-word field
- one legal encoded value

Example:

```json
{
  "field": "PC_INC",
  "value": "1"
}
```

Assignments must use encoded values rather than descriptive meanings.

This avoids introducing a second symbolic-value namespace when the control-word schema already defines the authoritative encodings.

The generator must preserve the encoded value exactly as represented by the control-word schema.

## 8. Assignment Rules

For each mapping:

1. `micro_operation` must reference exactly one extracted micro-operation.
2. Each assigned field must exist in the maintained control-word schema.
3. Each assigned field must have `control_word_role` equal to `encoded`.
4. Each assigned value must be legal for the field.
5. Each field may appear at most once in the mapping.
6. The mapping must contain only assignments required to implement the micro-operation.
7. Unassigned encoded fields receive their documented defaults during later control-word composition.
8. Derived fields must not appear on the assignment side.
9. External-input fields must not appear on the assignment side.
10. Sequencing fields must not appear in a micro-operation mapping unless the documentation explicitly defines them as part of that micro-operation.
11. A mapping must not contain control-input conditions.
12. A mapping must not introduce control behavior absent from the authoritative documentation.

## 9. Explicit-Value Requirements

The control-word schema distinguishes three explicit-value requirements.

### 9.1 Yes

A field with:

```text
Explicit Value Required: Yes
```

must receive an explicit value whenever the control outcome using that field is constructed.

The mapping validator must determine whether the micro-operation is responsible for supplying that value.

### 9.2 No

A field with:

```text
Explicit Value Required: No
```

does not require control to assign its value.

The field may still require a valid value from:

- combinational datapath logic
- processor state
- an external device
- another non-control source

The `Value Required When` expression remains relevant even when control does not provide the value.

### 9.3 Conditionally

A field with:

```text
Explicit Value Required: Conditionally
```

requires an explicit control assignment when its documented `Value Required When` condition applies.

Example:

```text
AC_LOAD = 1
```

The mapping validator must not assume that a canonical default satisfies a conditionally required explicit assignment.

## 10. Default Values and Don't-Care Fields

Every encoded field with a documented default receives that value when no explicit assignment overrides it.

A default value provides:

- deterministic complete control words
- reproducible output
- a defined electrical value
- stable comparison and serialization

A default value does not imply that the field affects behavior in every control case.

For example:

```text
AC_LOAD = 0
AC_SRC = 0
```

When `AC_LOAD = 0`, `AC_SRC` may be behaviorally irrelevant even though the complete symbolic word contains its canonical default.

Behavioral relevance and deterministic representation must remain separate.

Later equivalence analysis may treat a field as a don't-care when the field's `Value Required When` condition is false.

## 11. Preconditions and Constraints

Micro-operation preconditions and constraints do not directly assign control-field values.

They must still remain available to mapping validation because they may affect:

- whether a mapping is legal
- whether two mappings may be composed
- whether a required external or derived value is available
- whether a field's `Value Required When` condition applies
- whether a selected control-field combination is valid

The generator must preserve access to the micro-operation source metadata but must not copy all precondition and constraint prose into the maintained mapping.

The extracted micro-operation catalog remains the single generated source for that information.

## 12. Condition Ownership

Execution-selection conditions do not belong in micro-operation mappings.

Conditions determine which micro-operations and direct outcomes are selected for a control case.

The mapping defines only the implementation of the selected micro-operation.

The later validation relationship is:

```text
selected micro-operations
+ direct control outcomes
+ micro-operation preconditions
+ micro-operation constraints
+ control-field Value Required When rules
= required and legal assignments for one control case
```

The mapping generator does not yet evaluate a complete control case.

## 13. Mapping Derivation and Reverse Cross-Reference Validation

The generator must not infer control assignments from a micro-operation name alone.

The required assignments for a micro-operation are established through a reviewed comparison of:

1. The micro-operation definition, including its target, expression, sources, preconditions, and constraints.
2. The control-output definitions, including each field’s purpose, encodings, explicit-value requirement, and value-validity condition.
3. The `Used by μops` reverse references in the control-output documentation.

The micro-operation definition establishes the required behavior.

The control-output definitions establish the mechanisms available to implement that behavior.

The `Used by μops` entries provide reverse cross-references that should agree with the reviewed mapping, but they must not initially be assumed to be exhaustive or independently authoritative.

For example, a micro-operation that loads `AC` from `MB` may require:

```json
{
  "micro_operation": "AC_LOAD_FROM_MB",
  "assignments": [
    {
      "field": "AC_LOAD",
      "value": "1"
    },
    {
      "field": "AC_SRC",
      "value": "<documented encoding for MB>"
    }
  ]
}
```

This mapping is justified by the micro-operation’s required state transformation and the documented purposes and encodings of `AC_LOAD` and `AC_SRC`.

It must not be generated solely because the micro-operation name contains `AC`, `LOAD`, or `MB`.

### 13.1 Bidirectional Cross-Reference Validation

Mapping validation must compare each reviewed mapping with the `Used by μops` references extracted from the control-output documentation.

The validation must report:

- a mapped field whose control-output definition does not list the micro-operation under `Used by μops`
- a `Used by μops` reference whose corresponding micro-operation mapping does not assign that field
- a `Used by μops` reference to an undefined micro-operation
- a mapping assignment to a field that is derived or externally supplied
- a reverse reference that intentionally does not represent a control assignment

A reverse reference may intentionally not correspond to a mapping assignment when the field is:

- derived
- externally supplied
- observed rather than assigned
- required by a direct control outcome instead of the micro-operation
- otherwise explicitly documented as a non-assignment dependency

Such exceptions must be represented explicitly rather than silently ignored.

### 13.2 Validation Authority

A mismatch between a reviewed mapping and a `Used by μops` reference is a documentation or mapping review issue.

The validator must not automatically:

- add an assignment to a mapping
- remove an assignment from a mapping
- add a micro-operation to `Used by μops`
- remove a micro-operation from `Used by μops`
- decide which side of the mismatch is correct

The mismatch must include source references for both:

- the micro-operation definition
- the control-output definition

The documentation or maintained mapping must then be corrected through review.

### 13.3 Intended Outcome

The initial mapping effort also serves as a completeness review of the `Used by μops` lists.

After all mappings have been reviewed and all reported mismatches resolved:

- every mapped control field should have a corresponding reverse reference
- every assignment-related reverse reference should have a corresponding mapping assignment
- every intentional non-assignment reference should be explicitly classified
- mapping decisions should remain traceable to both the micro-operation and control-output documentation

The reviewed mapping remains the maintained source for implementation assignments.

The control-output documentation remains the maintained source for reverse usage references.

## 14. Candidate Generation

The generator creates one candidate mapping for every extracted micro-operation.

For each extracted micro-operation:

1. Match an existing maintained mapping by exact micro-operation name.
2. Preserve its reviewed assignments and notes.
3. Refresh its source metadata from the extracted micro-operation.
4. Emit the candidate entry in extracted micro-operation order.

If no maintained mapping exists:

- emit an empty `assignments` array
- emit an empty `notes` array
- copy current source traceability
- report `MAPPING_UNRESOLVED`

If a maintained mapping references a micro-operation no longer present in the extracted catalog:

- omit it from the candidate mapping
- report `STALE_MAINTAINED_MAPPING`
- do not silently discard the issue

## 15. Candidate Top-Level Structure

The candidate output uses:

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

Diagnostics may also be written separately to the human-readable report.

The candidate file must remain structurally usable when unresolved mappings are present.

## 16. Input Validation

The generator must validate the extracted micro-operation catalog before processing mappings.

Validation must include:

- supported format version
- expected extraction stage
- empty extractor diagnostics
- presence of the `micro_operations` array
- unique micro-operation names
- expected extraction status
- valid source traceability
- required micro-operation properties

The generator must validate the maintained control-word schema before processing assignments.

Validation must include:

- supported schema version
- expected specification type
- matching control-design version
- presence of the `fields` array
- unique field names
- recognized control-word roles
- legal encoding definitions
- required default and explicit-value metadata
- valid source traceability

## 17. Maintained Mapping Validation

The maintained mapping must be validated for:

- supported schema version
- expected specification type
- matching control-design version
- presence of the `mappings` array
- valid micro-operation names
- unique micro-operation mappings
- valid assignment arrays
- valid notes arrays
- valid source structures when present

Invalid maintained input must prevent candidate generation when reliable preservation is not possible.

A missing or empty maintained mapping is allowed during initial generation.

## 18. Assignment Validation

Every preserved assignment must be validated against the maintained control-word schema.

Validation must detect:

- an undefined assigned field
- assignment to a derived field
- assignment to an external-input field
- assignment to an unclassified field
- an invalid or reserved encoding
- an encoding that exceeds the field width
- duplicate assignments to one field
- conflicting values assigned to one field
- malformed assignment objects
- missing field names
- missing values

The generator must not infer a corrected value.

## 19. Mapping Completeness

Candidate generation completeness means:

- every extracted micro-operation has exactly one candidate mapping
- every maintained mapping corresponds to an extracted micro-operation or is reported as stale
- every preserved assignment is structurally legal
- every preserved assignment references a valid encoded field and value

An empty mapping is structurally complete but behaviorally unresolved.

The report must distinguish:

- missing mapping entries
- empty unresolved mappings
- invalid existing mappings
- complete reviewed mappings

## 20. Validation Boundary

The initial mapping generator does not prove that:

- the assignments implement the micro-operation expression
- all target registers are updated correctly
- all documented sources are selected correctly
- every explicitly required field has been assigned
- every `Value Required When` expression has been satisfied
- micro-operation preconditions hold
- micro-operation constraints are satisfied
- two individually valid mappings may execute concurrently
- a composed control word is legal
- execution schedules select the correct micro-operations

Those checks belong to later semantic mapping validation and control-word composition.

The initial generator validates structure, references, roles, encodings, coverage, and preservation.

## 21. Source Traceability

Every candidate mapping must identify the corresponding micro-operation source:

```json
{
  "source": {
    "document": "docs/03-microarchitecture/02-micro-operations.md",
    "section": "PC_INC",
    "line": 1339
  }
}
```

Source metadata must be refreshed from the current extracted micro-operation catalog.

The generator must not preserve stale source lines from the maintained mapping.

All source paths must be repository-relative.

## 22. Deterministic Output

Given identical inputs, the generator must produce identical output.

To preserve determinism:

- mapping order must follow extracted micro-operation order
- assignment order must preserve maintained assignment order
- note order must preserve maintained note order
- object property order must be consistent
- JSON indentation must be consistent
- output must use UTF-8
- output must end with one newline
- timestamps must not be included
- absolute paths must not be included

## 22. Diagnostics

Each diagnostic should contain:

- severity
- diagnostic code
- micro-operation name when applicable
- control-field name when applicable
- source path when available
- source line when available
- explanatory message

Supported severities are:

- `INFO`
- `WARNING`
- `ERROR`
- `FATAL`

Warnings identify unresolved or stale reviewed content that does not prevent candidate construction.

Errors identify invalid mappings or inputs that prevent reliable candidate generation.

Fatal errors identify failures that prevent reliable processing.

## 24. Command-Line Interface

The intended command form is:

```text
python tools/rom-generation/micro-operation-mapping-generator/src/generate_micro_operation_mapping.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides should include:

```text
--micro-operations INPUT_PATH
--control-word-schema INPUT_PATH
--maintained-mapping INPUT_PATH
--candidate-output OUTPUT_PATH
--report-output OUTPUT_PATH
```

Relative paths must be resolved from the supplied repository root.

Absolute paths must be used unchanged.

## 25. Testing

Tests must use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/micro-operation-mapping-generator/tests -p "test_*.py"
```

Required test coverage includes:

- repository-relative path resolution
- absolute-path preservation
- missing required input handling
- missing maintained mapping handling
- empty maintained mapping handling
- invalid UTF-8 handling
- invalid JSON handling
- unsupported schema versions
- invalid specification types
- mismatched control-design versions
- duplicate micro-operation names
- duplicate control-field names
- duplicate maintained mappings
- exact-name mapping preservation
- extracted mapping order
- source metadata refresh
- unresolved new mappings
- stale maintained mappings
- undefined assigned fields
- assignments to derived fields
- assignments to external-input fields
- invalid assigned values
- duplicate field assignments
- deterministic candidate output
- diagnostic-report generation
- complete command-line execution

Tests should cover representative behavior rather than every possible JSON permutation.

## 26. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- preserve repository-relative paths
- preserve deterministic ordering
- retain source traceability
- report malformed input without inventing replacements
- remain proportional to the bounded mapping task

The initial implementation should remain in one Python source file.

Shared ROM-generation code should be introduced only when duplicated behavior has stabilized enough to justify a common interface.

## 27. Maintained Mapping Workflow

The intended workflow is:

1. Update authoritative micro-operation or control-output documentation.
2. Run the micro-operation extractor.
3. Run the control-output extractor.
4. Regenerate and validate the maintained control-word schema.
5. Run the micro-operation mapping generator.
6. Review unresolved, stale, and invalid mapping diagnostics.
7. Add or update reviewed assignments in the maintained mapping.
8. Regenerate the candidate.
9. Compare the candidate with the maintained mapping.
10. Promote the candidate only when the changes are reviewed.
11. Run the complete mapping test suite.

The generator must never silently promote its candidate.

## 28. Non-Goals

The mapping generator does not:

- modify authoritative documentation
- modify the extracted micro-operation catalog
- modify the maintained control-word schema
- automatically invent micro-operation implementations
- infer assignments from micro-operation names
- infer assignments from expression prose
- infer assignments from target or source lists
- select micro-operations
- define direct control outcomes
- define sequencing outcomes
- compose complete control words
- evaluate execution schedules
- determine logical address packing
- define physical ROM packing
- generate binary or hexadecimal ROM images

## 29. Completion Boundary

The initial mapping generator is complete when it can:

- read the extracted micro-operation catalog
- read the maintained control-word schema
- optionally read an existing maintained mapping
- generate exactly one candidate mapping per extracted micro-operation
- preserve reviewed assignments and notes
- validate assigned fields and values
- reject assignments to non-encoded fields
- identify new unresolved mappings
- identify stale maintained mappings
- refresh source traceability
- generate deterministic JSON
- generate a human-readable report
- pass the targeted automated tests

Semantic implementation validation and complete symbolic control-word composition are the next stages after the maintained micro-operation mappings are populated.
