# Direct-Control Generator

Generates and validates a reviewable direct-control candidate from the extractor output.

## Two-Stage Workflow

1. The extractor writes `direct-control-definitions.json`.
2. This generator:
   - compares extracted definitions with the optional maintained artifact at `rom/microcode/v1/direct-control-definitions.json`
   - reports new, changed, and stale definitions
   - validates the candidate against the control-input schema, control-word schema, and micro-operation mapping
   - writes `direct-control-definitions.candidate.json` only when validation succeeds
3. After review, copy the candidate to `rom/microcode/v1/direct-control-definitions.json`.

This matches the other ROM-generation workflows: extractor, then candidate generator with validation. There is no separate direct-control validator stage.

## Run

```text
python tools/rom-generation/direct-control-generator/src/generate_direct_control.py --repo-root .
```

## Test

```text
python -m unittest discover -s tools/rom-generation/direct-control-generator/tests -p "test_*.py"
```
