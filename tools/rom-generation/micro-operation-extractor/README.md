# Micro-Operation Extractor

## 1. Purpose

The micro-operation extractor creates a normalized, machine-readable representation of the documented micro-operation catalog.

The extractor converts the authoritative micro-operation definitions into generated review material used by later ROM-generation stages.

The extractor does not define how micro-operations are implemented by control signals.

## 2. Authoritative Input

The extractor reads exactly one maintained document:

- [Micro-Operations](../../../docs/03-microarchitecture/02-micro-operations.md)

The source document remains authoritative.

The explicit input path:

- prevents unrelated Markdown files from becoming accidental inputs
- makes the extraction boundary reviewable
- preserves deterministic processing order
- ensures missing source documentation is detected

The source document must reside under the supplied repository root.

## 3. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── micro-operation-extractor/
            ├── micro-operations.json
            └── extraction-report.txt
```

Generated outputs:

- must not be edited manually
- must not be treated as authoritative source
- should not be committed as maintained specifications
- may be deleted and regenerated
- must be regenerated after relevant documentation changes

## 4. Extraction Scope

For each documented micro-operation, the extractor attempts to preserve:

- micro-operation name
- category
- description
- targets
- expression
- sources
- preconditions
- constraints
- source document
- source heading
- source line number

Missing optional sections must be represented as empty arrays.

Missing or malformed required information must produce diagnostics rather than inferred replacement values.

## 5. Extracted Representation

The generated JSON uses this top-level structure:

```json
{
  "format_version": 1,
  "extraction_stage": "definition-validation",
  "source": {
    "path": "docs/03-microarchitecture/02-micro-operations.md"
  },
  "micro_operations": [],
  "diagnostics": []
}
```

Each micro-operation uses this structure:

```json
{
  "name": "PC_INC",
  "category": "Control Flow",
  "description": "Increments the program counter to point to the next sequential instruction.",
  "targets": [
    "PC"
  ],
  "expression": [
    "PC ← PC + 1"
  ],
  "sources": [
    "PC"
  ],
  "preconditions": [],
  "constraints": [],
  "source": {
    "path": "docs/03-microarchitecture/02-micro-operations.md",
    "heading": "PC_INC",
    "line": 1
  },
  "extraction_status": "definition-validated"
}
```

This example defines the representation only. Extracted values must come from the source document.

## 6. Definition Boundaries

The extractor must identify micro-operation definitions only within the documented micro-operation definition section.

A micro-operation definition begins at its definition heading and ends immediately before:

- the next micro-operation definition heading
- the end of the definition section
- a same-level or higher-level heading that leaves the definition section

Headings outside the micro-operation definition section must not be interpreted as micro-operation definitions.

## 7. Scalar Attributes

The extractor recognizes these required scalar attributes:

- `Category`
- `Description`
- `Target`
- `Sources`

Each required scalar attribute must occur exactly once in a definition.

A duplicated required attribute is an error.

An unrecognized attribute is preserved only when explicitly supported by the extractor format. The extractor must not infer the meaning of arbitrary labels.

## 8. Target Representation

The `Target` attribute identifies the architectural or microarchitectural state modified by the micro-operation.

Comma-separated targets must be converted into an ordered array.

Example:

```markdown
**Target:** AC, L
```

Generated representation:

```json
"targets": [
  "AC",
  "L"
]
```

Target names must preserve their documented spelling and order.

The extractor must not:

- combine distinct targets
- infer implied targets from the expression
- remove a target because it appears unchanged
- add a target based on the micro-operation name

## 9. Source Representation

The `Sources` attribute identifies values observed by the micro-operation.

Comma-separated sources must be converted into an ordered array.

The following documented forms identify an empty source list:

```text
none
(none)
```

Case and surrounding whitespace may be normalized when recognizing these forms.

The extractor must not derive sources from the expression or description.

## 10. Expression Extraction

The `Expression` section defines the documented state transformation.

Expressions may be:

- single-line
- multiline
- conditional
- composed of multiple simultaneous assignments
- followed by explanatory continuation lines

The extractor must preserve expressions as an ordered array of normalized source lines.

Example:

```markdown
**Expression:**
AC ← MQ
MQ ← AC
```

Generated representation:

```json
"expression": [
  "AC ← MQ",
  "MQ ← AC"
]
```

The extractor must not:

- execute expressions
- parse expressions into an abstract syntax tree
- simplify expressions
- infer control-field assignments
- change assignment order
- combine multiple assignments
- convert concurrent assignments into sequential behavior
- prove that expressions match descriptions, targets, or sources

## 11. Preconditions

A micro-operation may include a `Preconditions` section.

Preconditions must be preserved as an ordered array of text entries with source traceability.

Preconditions describe requirements that must already hold when the micro-operation is selected.

The extractor must not:

- evaluate preconditions
- convert preconditions into control-input conditions
- infer missing preconditions
- treat preconditions as micro-operations
- add preconditions to the control address

If no preconditions are documented, the generated array must be empty.

## 12. Constraints

A micro-operation may include a `Constraints` section.

Each constraint must retain:

- constraint text
- source document
- source line number

Example:

```json
"constraints": [
  {
    "text": "Observing /INT_REQ does not acknowledge, clear, or consume any controller interrupt condition.",
    "source": {
      "path": "docs/03-microarchitecture/02-micro-operations.md",
      "line": 1
    }
  }
]
```

The extractor preserves constraint text but does not interpret it as an executable validation rule.

If no constraints are documented, the generated array must be empty.

## 13. Source Traceability

Every extracted micro-operation must retain:

- repository-relative source path
- definition heading
- definition heading line number

Each extracted precondition and constraint must retain its own source line when available.

Absolute paths must not appear in generated output.

Diagnostics must identify:

- source path
- source line when available
- micro-operation name when available

## 14. Ordering

The extractor must preserve the order of micro-operation definitions in the authoritative document.

Within each definition, the extractor must preserve the documented order of:

- targets
- expression lines
- sources
- preconditions
- constraints

The extractor must not alphabetize or otherwise reorder extracted content.

Later tools may create alternate views without changing the generated extraction artifact.

## 15. Validation

The extractor must validate at least:

- the required source file exists
- the source file is valid UTF-8
- the micro-operation definition section exists
- at least one micro-operation definition is present
- micro-operation names are non-empty
- micro-operation names are unique
- required scalar attributes are present
- required scalar attributes are not duplicated
- categories are non-empty
- descriptions are non-empty
- targets are present
- expressions are present
- sources are present or explicitly documented as none
- precondition entries are non-empty
- constraint entries are non-empty
- source traceability is retained

The extractor must report incomplete or malformed definitions rather than infer missing information.

## 16. Validation Boundary

The extractor does not validate whether:

- a micro-operation is architecturally correct
- a micro-operation is required by the instruction set
- a micro-operation is used by an execution schedule
- targets agree logically with the expression
- sources agree logically with the expression
- two micro-operations are equivalent
- two micro-operations may execute concurrently
- a micro-operation has a valid control-signal implementation
- the control-output catalog is sufficient to implement a micro-operation
- the micro-operation can be represented in one timing state
- preconditions are satisfiable
- constraints are mutually consistent

Those checks belong to later mapping, composition, and control-validation stages.

## 17. Diagnostics

Each diagnostic must contain:

- severity
- diagnostic code
- micro-operation name when applicable
- source path
- source line when available
- explanatory message

Supported severities are:

- `INFO`
- `WARNING`
- `ERROR`
- `FATAL`

Definition-level errors should not prevent extraction of independent definitions when reliable processing can continue.

A fatal error prevents reliable output generation.

## 18. Deterministic Output

Given identical input and configuration, the extractor must produce identical output.

To preserve deterministic output:

- source order must be preserved
- object property order must be consistent
- JSON indentation must be consistent
- output must use UTF-8
- output must end with one newline
- generated timestamps must not be included
- absolute or working-directory-specific paths must not be included

## 19. Command-Line Interface

The intended command form is:

```text
python tools/rom-generation/micro-operation-extractor/src/extract_micro_operations.py --repo-root .
```

The required argument is:

```text
--repo-root REPOSITORY_PATH
```

Optional output overrides should be:

```text
--json-output OUTPUT_PATH
--report-output OUTPUT_PATH
```

Relative paths must be resolved from the supplied repository root.

Absolute output paths must be used unchanged.

## 20. Testing

Tests must use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/micro-operation-extractor/tests -p "test_*.py"
```

Tests should use minimal inline source documents and temporary directories.

A persistent fixture directory should be added only when multiple tests require the same representative source content and inline definitions become difficult to maintain.

Required test coverage includes:

- repository-relative path resolution
- absolute output-path preservation
- missing source-file handling
- invalid UTF-8 handling
- definition-section detection
- definition-heading extraction
- definition-boundary detection
- duplicate micro-operation names
- required scalar-attribute extraction
- duplicate scalar attributes
- missing required attributes
- comma-separated target extraction
- comma-separated source extraction
- recognition of `none` and `(none)`
- single-line expression extraction
- multiline expression extraction
- conditional expression preservation
- precondition extraction
- constraint extraction
- source-line preservation
- deterministic ordering
- deterministic JSON output
- diagnostic-report generation
- complete command-line execution

Tests should cover representative behavior rather than every possible Markdown permutation.

## 21. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- use repository-relative source references
- preserve source ordering
- preserve source traceability
- produce deterministic output
- report malformed documentation without inventing replacement values
- remain proportional to the tool's bounded purpose

The initial implementation should remain in one Python source file.

Additional modules should be introduced only if the implementation becomes materially difficult to understand or test.

Shared code must not be moved into a common ROM-generation module until actual duplicated requirements exist and a stable shared interface can be identified.

## 22. Relationship to Later Stages

The generated micro-operation catalog will be consumed with the maintained control-word schema when constructing the reviewed micro-operation mapping.

The later mapping stage will associate one micro-operation with exact symbolic control-field assignments.

This extractor does not create those assignments.

The subsequent process is:

1. Extract the documented micro-operation catalog.
2. Review extraction diagnostics.
3. Define the maintained micro-operation mapping.
4. Validate every mapped field and value against the maintained control-word schema.
5. Verify that every documented micro-operation has exactly one maintained mapping.
6. Compose compatible mappings into symbolic control words.
7. Validate composed words against documented control constraints.

## 23. Non-Goals

The extractor does not:

- modify the authoritative documentation
- map micro-operations to control outputs
- create complete control words
- select micro-operations for execution
- evaluate control-input conditions
- generate execution rules
- assign logical control-word bit positions
- determine control-address packing
- assign physical ROM positions
- generate binary or hexadecimal ROM images

## 24. Completion Boundary

The initial extractor is complete when it can:

- read the authoritative micro-operation document
- identify every documented micro-operation
- extract all required definition properties
- preserve multiline expressions
- preserve preconditions and constraints
- retain source traceability
- report incomplete or malformed definitions without guessing
- generate deterministic JSON
- generate a human-readable diagnostic report
- pass the targeted automated tests

The resulting JSON remains generated review material.

Defining the maintained micro-operation mappings is the next ROM-generation stage after this extractor is complete.