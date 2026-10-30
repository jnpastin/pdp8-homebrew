# Execution-Definition Extractor

Extracts normalized control-selection cases from the authoritative ISA and microarchitecture documentation.

## Output

The extractor writes:

- `build/simulation_outputs/rom-generation/execution-definition-extractor/execution-definitions.json`
- `build/simulation_outputs/rom-generation/execution-definition-extractor/extraction-report.txt`

Each execution case preserves its source location, execution context, timing state, unconditional micro-operations, and conditional micro-operations.

## OPR Encoding Diagrams

The Group 1, Group 2, and Group 3 ISA diagrams are parsed using their documented three-row convention:

- top row: IR bit position
- middle row: required bit value where constrained
- bottom row: bit mnemonic

Blank middle-row cells are unconstrained by that diagram. Execution-document references such as `IR[bit(CLA)]` are resolved using those diagrams.

## Boundaries

The extractor does not derive instruction behavior from mnemonics and does not reproduce derived-control logic. Conditions such as `AUTO_INDEX_REQUIRED`, `ISZ_SKIP_REQUIRED`, and `SKIP_TAKEN` are preserved as documented control predicates.

## Run

```text
python tools/rom-generation/execution-definition-extractor/src/extract_execution_definitions.py --repo-root .
```

## Test

```text
python -m unittest discover -s tools/rom-generation/execution-definition-extractor/tests -p "test_*.py"
```
