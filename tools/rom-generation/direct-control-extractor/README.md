# Direct-Control Extractor

## Purpose

This tool extracts direct-control definitions from the authoritative documentation without using the removed direct-control outcome catalog or validator model.

## Sources

- [Sequencing and Internal Control](../../../docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md)
- [Interface and Ownership Control](../../../docs/04-control/30-direct-control-definitions/02-interface-and-ownership-control.md)

## Output

The extractor writes:

- `build/simulation_outputs/rom-generation/direct-control-extractor/direct-control-definitions.json`
- `build/simulation_outputs/rom-generation/direct-control-extractor/extraction-report.txt`

Each extracted definition preserves:

- its source heading and location
- applicable context
- assignments and logical results
- commit statements
- constraints
- source links
- interface drive-state or ownership information when present

Complex predicates and assignments are preserved as documented text. The extractor does not convert prose into invented Boolean expressions or infer missing behavior.

## Usage

```text
python tools/rom-generation/direct-control-extractor/src/extract_direct_control.py --repo-root .
```

## Exit Status

- `0`: extraction completed without `ERROR` or `FATAL` diagnostics
- `1`: extraction or output generation failed

The complete diagnostic set is written to the report. Failure diagnostics are also written to standard output when the exit status is nonzero.
