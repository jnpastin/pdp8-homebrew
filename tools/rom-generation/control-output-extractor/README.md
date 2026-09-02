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

Run the tool from any working directory by supplying the repository root:

```powershell
python src\extract_control_outputs.py --repo-root C:\Users\jeremy.pastin\git-repos\pdp8-homebrew
```

Optional output arguments:

```powershell
python src\extract_control_outputs.py `
    --repo-root C:\Users\jeremy.pastin\git-repos\pdp8-homebrew `
    --json-output build\simulation_outputs\rom-generation\control-output-extractor\control-outputs.json `
    --report-output build\simulation_outputs\rom-generation\control-output-extractor\extraction-report.txt
```

Relative output paths are resolved from the repository root.

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

```powershell
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

The initial implementation is complete.

The tool currently:

- reads the four defined control-output documents
- validates the required source files
- parses the authoritative signal index
- matches indexed signals to definition blocks
- extracts scalar definition attributes
- normalizes bit widths
- extracts enumerated octal encodings
- validates encoding values against bit widths
- extracts source-traceable constraints
- validates documented mnemonics
- validates category-specific structural requirements
- writes deterministic JSON output
- writes a human-readable diagnostic report
- supports execution from any working directory
- includes unit and end-to-end tests

The generated JSON remains review material and is not an authoritative microcode specification.

Constraint text is preserved but is not yet interpreted as executable validation logic.

The next ROM-generation tool will consume the extracted output only after the required reviewed specification format and promotion process are defined.