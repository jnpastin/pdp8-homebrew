# Control Output Extractor

## 1. Purpose

This tool extracts candidate control-output definitions from the authoritative control documentation.

It produces:

- a normalized JSON representation of the documented signals
- a diagnostic report identifying missing, ambiguous, duplicate, or inconsistent information

The extracted JSON is generated review material. It is not an authoritative control specification.

## 2. Scope

The tool reads:

- `docs/04-control/20-control-output-definitions/00-index.md`
- `docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md`
- `docs/04-control/20-control-output-definitions/02-architectural-control-signals.md`
- `docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md`

All source documents must reside under the supplied repository root. Source files outside the repository are not supported because generated source references are stored as repository-relative paths.

For each documented control output, the tool attempts to extract:

- signal name
- descriptive name
- domain
- class
- bit width
- polarity
- purpose or description
- legal encodings
- constraints
- source file
- source heading
- source line number

## 3. Non-Goals

This tool does not:

- determine whether the documented control design is correct
- infer missing values
- repair contradictory definitions
- modify documentation
- assign control-word bit positions
- map micro-operations to control outputs
- generate control words
- generate ROM images

Later tools may consume the extractor output after it has been reviewed and validated.

## 4. Implementation

The tool is implemented in Python using only the standard library.

The initial implementation uses a line-oriented parser tailored to the documented control-output format. It is not intended to be a general-purpose Markdown parser.

Where documentation formatting cannot be interpreted reliably, the tool reports a diagnostic rather than adding inferred behavior.

## 5. Command-Line Interface

The tool requires the repository root:

```text
--repo-root REPOSITORY_PATH
```

The repository root identifies the base directory used to locate the authoritative input documents and resolve relative output paths.

The following optional arguments override the default output locations:

```text
--json-output OUTPUT_PATH
--report-output OUTPUT_PATH
```

Relative output paths are resolved from the supplied repository root. Absolute output paths are used unchanged.

The default output paths are:

```text
build/simulation_outputs/rom-generation/control-output-extractor/control-outputs.json
build/simulation_outputs/rom-generation/control-output-extractor/extraction-report.txt
```

The complete execution commands are documented in Section 17.

## 6. Default Outputs

Candidate definitions are written to:

```text
build/simulation_outputs/rom-generation/control-output-extractor/control-outputs.json
```

The extraction report is written to:

```text
build/simulation_outputs/rom-generation/control-output-extractor/extraction-report.txt
```

The tool creates missing output directories.

Generated files must not be edited manually.

## 7. Extraction Behavior

The tool processes each definition document as follows:

1. Identifies signal-definition headings.
2. Captures the content associated with each signal.
3. Extracts recognized labeled attributes.
4. Extracts documented encoding entries.
5. Extracts documented constraints.
6. Records source traceability.
7. Compares extracted definitions with the signal index.
8. Reports unresolved or inconsistent information.

Extracted text is normalized only where normalization does not change its meaning.

## 8. Missing Information

The tool does not require every signal definition to be complete before producing output.

When information is missing or ambiguous:

- the affected JSON property is empty or `null`
- a diagnostic is recorded
- the source text is not replaced with an inferred value

This behavior allows the extraction results to guide refinement of the authoritative documentation.

## 9. Diagnostics

Each diagnostic contains:

- severity
- diagnostic code
- source path
- source line number, when available
- signal name, when available
- explanatory message

Supported severity levels are:

- `INFO`: an extraction observation that requires no correction
- `WARNING`: incomplete information that does not prevent extraction
- `ERROR`: a definition could not be represented reliably
- `FATAL`: processing could not continue

The text report summarizes all diagnostics and extraction counts.

## 10. Exit Status

The tool returns:

- `0` when all source files were processed and outputs were written
- nonzero when a fatal error prevents reliable output

Warnings and definition-level errors do not initially cause a failing exit status because exposing documentation problems is a primary purpose of the tool.

Extraction diagnostics with severity `WARNING` or `ERROR` do not change the process exit status. A nonzero status is returned only when the tool cannot read its required inputs or write reliable output.

This policy may be tightened when the extracted specification becomes an input to ROM generation.

## 11. Testing

Tests use Python's standard `unittest` framework.

Targeted tests cover:

- extraction of a representative complete definition
- multiline descriptive text
- multiple encoding entries
- missing required attributes
- duplicate definitions
- index and definition mismatches
- missing source files
- deterministic JSON output

Test fixtures contain only the minimum documentation needed for each test.

Run the tests with:

```text
python -m unittest discover -s tests -p "test_*.py"
```

## 12. Directory Structure

```text
control-output-extractor/
├── README.md
├── src/
│   └── extract_control_outputs.py
└── tests/
    ├── fixtures/
    └── test_extract_control_outputs.py
```

The initial implementation remains in one Python source file. Additional modules will be introduced only if the implementation becomes materially difficult to understand or test.

## 13. Completion Criteria

The initial tool is complete when it can:

- process all four defined source documents
- identify indexed control-output signals
- extract recognized signal attributes
- preserve source traceability
- produce readable deterministic JSON
- produce a readable diagnostic report
- identify index and definition mismatches
- report unresolved information without guessing
- pass the targeted automated tests
- run on Windows, Linux, and macOS using standard Python

## 14. Current Status

The initial control-output extractor implementation is complete.

The tool currently:

- reads the four explicitly defined control-output documents
- validates that all required source files exist
- reads source documents as UTF-8
- parses the authoritative control-output index
- preserves deterministic signal ordering
- matches indexed signals to definition blocks
- reports missing, duplicate, and unindexed definitions
- extracts scalar definition attributes
- validates documented mnemonics against indexed signal names
- normalizes documented bit widths to positive integers
- extracts enumerated octal encodings
- validates octal encoding values against field widths
- extracts constraints with source-file and source-line traceability
- validates category-specific structural requirements
- generates deterministic JSON output
- generates a human-readable extraction report
- supports execution from any working directory
- includes targeted unit tests
- includes an end-to-end generation test

The current authoritative documentation produces a clean extraction report.

The generated JSON remains review material. It is not an authoritative control specification and must not be edited manually or committed as maintained source.

Constraint text is preserved for later processing, but the tool does not interpret constraints as executable validation rules.

## 15. Extracted Representation

For each indexed control output, the generated JSON contains:

- indexed signal name
- signal category
- normalized bit width
- descriptive attributes
- enumerated octal encodings, when documented
- documented constraints
- definition heading
- index source location
- definition source location
- encoding source locations
- constraint source locations
- extraction status

The extractor preserves the distinction between:

- documentation content
- normalized extracted values
- validation diagnostics
- later implementation decisions

The extractor does not assign:

- control-word bit positions
- canonical inactive values
- physical ROM positions
- micro-operation mappings
- direct control-event mappings
- sequencing behavior
- control-address fields

Those decisions belong to later ROM-generation stages.

## 16. Validation Performed

The tool currently detects:

- missing required source files
- unreadable or invalid UTF-8 source files
- missing index entries
- duplicate index entries
- missing definition blocks
- duplicate definition blocks
- unindexed definition blocks
- duplicate scalar attributes
- missing required widths
- missing purpose or description text
- invalid bit-width declarations
- mismatched documented mnemonics
- malformed enumerated encodings
- duplicate encoding values
- non-octal encoding values
- encoding values that exceed the documented field width
- enable signals whose width is not one bit
- missing enumerated encodings for enable signals
- missing enumerated encodings for select signals
- missing enumerated encodings for control-flow signals

The tool does not currently determine whether:

- the documented signal behavior is architecturally correct
- the documented constraints are mutually consistent
- a control output is sufficient to implement the micro-operation catalog
- a control output is assigned a valid default value
- control outputs can be combined into a valid control word
- a documented event requires a micro-operation, direct event, or sequencing rule
- a generated control word satisfies the complete datapath constraints

These checks belong to later tools.

## 17. Running the Tool

Run the tool from the repository root:

```text
python tools/rom-generation/control-output-extractor/src/extract_control_outputs.py --repo-root .
```

The tool may be run from any working directory by supplying the applicable repository root:

```text
python path/to/extract_control_outputs.py --repo-root path/to/repository
```

Relative input and output paths are resolved from the supplied repository root.

To specify alternate output paths:

```text
python tools/rom-generation/control-output-extractor/src/extract_control_outputs.py --repo-root . --json-output build/control-outputs.json --report-output build/extraction-report.txt
```

The `python` command may be replaced by the local Python 3 launcher when required by the operating system or Python installation.

Examples include:

```text
python3 tools/rom-generation/control-output-extractor/src/extract_control_outputs.py --repo-root .
```

```text
py tools/rom-generation/control-output-extractor/src/extract_control_outputs.py --repo-root .
```

## 18. Running the Tests

Run the tests from the control-output extractor directory:

```text
python -m unittest discover -s tests -p "test_*.py"
```

Alternatively, run them from the repository root:

```text
python -m unittest discover -s tools/rom-generation/control-output-extractor/tests -p "test_*.py"
```

As with the tool command, `python` may be replaced by the applicable local Python 3 launcher.

The tests cover representative behavior rather than every possible documentation permutation.

Current test coverage includes:

- repository-relative path resolution
- preservation of absolute output paths
- required source-file validation
- UTF-8 source loading
- deterministic source ordering
- signal-index extraction
- indexed bus names containing brackets
- category-heading extraction
- duplicate index detection
- definition-section extraction
- definition-block matching
- missing, duplicate, and unindexed definitions
- scalar attribute extraction
- alternate attribute-label formatting
- duplicate attributes
- required attribute validation
- mnemonic validation
- bit-width normalization
- encoding-line parsing
- octal encoding validation
- encoding-width validation
- constraint extraction
- Markdown identifier normalization
- category-specific validation
- complete command-line execution
- JSON and report generation

## 19. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── control-output-extractor/
            ├── control-outputs.json
            └── extraction-report.txt
```

These files are reproducible build artifacts.

They:

- must not be edited manually
- must not be treated as authoritative source
- should not be committed to version control
- may be deleted and regenerated
- must be regenerated after relevant documentation changes

The repository-level `.gitignore` excludes the `build/` directory.

## 20. Completion Boundary

The control-output extractor is complete for its initial purpose.

Further behavior should not be added merely because it relates to control outputs. New behavior belongs in this tool only when it concerns extracting or structurally validating documented control-output definitions.

The following work belongs to later ROM-generation stages:

- control-input extraction
- micro-operation extraction
- direct control-event extraction
- sequencing-rule extraction
- reviewed specification generation
- micro-operation implementation mapping
- direct control-event mapping
- execution-rule representation
- control-case expansion
- symbolic control-word validation
- behavioral signature generation
- control-address reduction
- logical control-word layout
- physical ROM packing
- ROM image generation

The next tool in the ROM-generation process is the control-input extractor.
