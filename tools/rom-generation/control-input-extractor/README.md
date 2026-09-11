# Control Input Extractor

## 1. Purpose

This tool extracts structured control-input information from the authoritative control-input documentation.

It provides a deterministic, machine-readable representation of:

- primitive flags
- IR-derived signals
- derived flags
- external inputs
- documented input attributes
- value encodings
- derivations and dependencies
- constraints
- consumed-by and used-by references
- source traceability
- extraction diagnostics

The generated output is review material. It is not an authoritative control-address specification or maintained microcode source.

## 2. Authoritative Inputs

The tool reads exactly these maintained documents:

```text
docs/04-control/10-control-input-definitions/00-index.md
docs/04-control/10-control-input-definitions/01-flags.md
docs/04-control/10-control-input-definitions/02-ir-derived-fields.md
docs/04-control/10-control-input-definitions/03-derived-flags.md
docs/04-control/10-control-input-definitions/04-external-inputs.md
```

Unrestricted Markdown discovery is intentionally not used.

The explicitly enumerated source list:

- prevents unrelated Markdown files from becoming accidental inputs
- makes the extraction boundary reviewable
- detects missing authoritative documents
- preserves deterministic processing order

All source documents must reside under the supplied repository root. Source files outside the repository are not supported because generated source references are stored as repository-relative paths.

The source Markdown remains authoritative.

## 3. Input Domains

The authoritative index partitions control inputs into four disjoint domains:

1. Primitive Flags
2. IR-Derived Signals
3. Derived Flags
4. External Inputs

Each indexed input must belong to exactly one domain.

The extractor preserves these domains. It must not collapse all control inputs into a generic flag classification.

Index subsections may provide additional categories within a domain, such as:

- IR class flags
- instruction detection
- addressing mode
- OPR class
- OPR bit flags
- memory management flags
- field extraction signals
- front-panel commands
- front-panel modes
- front-panel data
- external requests
- external IOT responses

These categories are preserved as indexed metadata and do not replace the four top-level domains.

## 4. Extracted Representation

For each indexed control input, the generated representation contains:

- indexed signal name
- indexed domain
- indexed category, when present
- applicable documented scalar attributes
- normalized bit width
- normalized polarity
- polarity provenance
- enumerated values or a bounded value range
- explicitly documented dependencies
- derivation, expression, or internal-composition text, when applicable
- documented constraints
- consumed-by and used-by references
- index source location
- definition source location
- value source locations
- dependency source locations
- logic-section source locations
- constraint source locations
- consumer source locations
- extraction status

Scalar attributes are included only when applicable to the input definition. Missing optional attributes are not invented.
Attributes are included only when applicable to the input definition.

Missing optional attributes must not be invented.

## 5. Polarity

Control-input polarity follows the project-wide convention:

- explicitly documented polarity is preserved
- active-low signal names beginning with `/` are interpreted as active-low
- when polarity is not otherwise specified, the signal is active-high

The generated representation records both:

- the normalized polarity
- whether the polarity was explicit, name-derived, or defaulted

Defaulting an unspecified polarity to active-high is a defined project rule, not an inferred documentation value.

## 6. Value Representation

Control inputs use several distinct value-description forms.

### 6.1 Enumerated Values

Enumerated values list individual encodings and meanings.

Example:

```text
0 -> inactive
1 -> active
```

The extractor records each value and its description separately.

### 6.2 Ranges

Range declarations describe a bounded set without enumerating every value.

Example:

```text
000-111 -> field value
```

The extractor preserves:

- range start
- range end
- value description
- source location

A range must not be expanded into every individual value during extraction.

### 6.3 Numeric Interpretation

Numeric values are interpreted according to the notation used by the source definition.

The extractor must preserve the original source text in addition to any normalized representation.

It must not assume that digit strings represent octal unless the applicable documentation establishes octal interpretation for that value.

## 7. Derivations and Dependencies

Primitive flags, IR-derived signals, and derived flags may document how their values are formed.

The extractor preserves:

- derivation text
- expression text
- internal-composition text
- explicitly listed dependencies
- explicitly identified source registers
- source traceability

Derived flags must provide an explicit dependency list. Each listed dependency must match an indexed control input.

IR-derived signals must provide a derivation. Derived flags must provide an expression or internal composition.

Structural validation verifies that applicable derivations and derived logic assign the indexed signal name.

The extractor does not:

- execute expressions
- prove logical equivalence
- simplify Boolean logic
- determine redundancy
- synthesize combinational logic
- infer dependencies that are not explicitly documented
- compare expression identifiers against the documented dependency list

## 8. Validation

The implementation validates:

- all required source files exist
- all source files are valid UTF-8
- every indexed input has exactly one definition
- index entries and definition blocks are not duplicated
- indexed domains and categories are preserved
- required scalar attributes are present by domain
- documented mnemonics agree with indexed names
- documented bit widths are positive integers
- primitive and derived flags default to one bit when width is omitted
- IR-derived and external inputs document their widths
- explicit values and ranges fit the normalized bit width
- every definition contains either enumerated values or a bounded range
- definitions do not mix enumerated values and ranges
- duplicate enumerated values are reported
- malformed value declarations are reported
- derived flags identify their documented dependencies
- dependencies refer to indexed control inputs
- required logic sections are present
- derivations and derived logic assign the indexed signal
- active-low names do not conflict with normalized polarity
- polarity is normalized according to the project rule
- source traceability is retained

Diagnostics identify:

- severity
- diagnostic code
- signal name, when applicable
- source file
- source line, when available
- explanatory message

## 9. Validation Boundary

The extractor does not validate whether:

- a documented derivation is logically correct
- two derivations are logically equivalent
- a flag is actually minimal or nonredundant
- a documented input is required by control behavior
- an indexed input belongs in the final control address
- the complete control-input space is sufficient
- the documented control rules are architecturally correct
- all reachable control cases are distinguishable
- control-address aliases are valid
- control-word permutations are complete

Those checks belong to later ROM-generation stages.

## 10. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── control-input-extractor/
            ├── control-inputs.json
            └── extraction-report.txt
```

Generated files:

- must not be edited manually
- must not be treated as authoritative source
- should not be committed to version control
- may be deleted and regenerated
- must be regenerated after relevant documentation changes

The repository-level `.gitignore` excludes the `build/` directory.

## 11. Command-Line Interface

The tool requires the repository root:

```text
--repo-root REPOSITORY_PATH
```

The optional `--json-output OUTPUT_PATH` argument overrides the default JSON output location.

The extraction report is written beside the JSON output using the filename `extraction-report.txt`.

Relative output paths are resolved from the supplied repository root. Absolute output paths are used unchanged.

The default output directory is:

build/simulation_outputs/rom-generation/control-input-extractor/

The generated files are:

- `control-inputs.json`
- `extraction-report.txt`

## 12. Running the Tool

Run the tool from the repository root:

```text
python tools/rom-generation/control-input-extractor/src/extract_control_inputs.py --repo-root .
```

The tool may be run from any working directory by supplying the applicable repository root:

```text
python path/to/extract_control_inputs.py --repo-root path/to/repository
```

The `python` command may be replaced by the applicable local Python 3 launcher.

## 13. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/control-input-extractor/tests -p "test_*.py"
```

The tests will use inline document content and temporary directories.

A persistent fixture directory is not created initially. It should be added only if multiple tests require the same representative source documents and inline content becomes harder to maintain.

Tests should cover representative behavior rather than every possible input permutation.

## 14. Implementation Constraints

The implementation must:

- use only the Python standard library
- support multiple operating systems
- avoid shell-specific behavior
- use repository-relative source references
- emit deterministic output
- preserve source ordering
- preserve source traceability
- report malformed documentation without inventing replacement values
- keep extraction separate from control-address design
- remain proportional to the tool's bounded purpose

Shared code must not be moved into the ROM-generation `common/` directory until actual duplicated requirements exist and a stable common interface can be identified.

## 15. Implementation Stages

The implementation consists of these completed stages:

- command-line parsing and path resolution
- required-source validation
- UTF-8 document loading
- authoritative-index extraction
- definition-block extraction
- scalar-attribute extraction
- required-attribute validation
- bit-width normalization
- polarity normalization
- value-form extraction
- value-width validation
- dependency extraction and validation
- logic-section extraction and validation
- constraint extraction
- consumer extraction
- final structural validation
- deterministic JSON generation
- diagnostic-report generation

Each stage has targeted unit-test coverage..

## 16. Completion Boundary

The control-input extractor is complete when it can:

- read the five authoritative control-input documents
- extract every indexed input
- preserve all four input domains
- preserve indexed subcategories
- normalize applicable attributes
- represent enumerated values and bounded ranges distinctly
- normalize explicit and defaulted polarity
- preserve derivations and dependencies
- preserve constraints
- preserve linked and plain-text consumers
- retain source traceability
- produce deterministic JSON
- produce a human-readable report
- report no unresolved structural errors against the authoritative documentation
- pass the targeted unit-test suite

The resulting JSON remains generated review material.

Control-input permutation generation, behavioral reduction, control-address construction, and promotion into maintained ROM source belong to later tools.