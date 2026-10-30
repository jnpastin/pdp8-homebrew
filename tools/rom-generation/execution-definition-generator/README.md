# Execution-Definition Generator

Generates a reviewable execution-definition candidate from `execution-definitions.json`.

The generator compares extracted cases with the optional maintained artifact at `rom/microcode/v1/execution-definitions.json` and reports new, changed, or stale cases. The documentation-derived extraction remains authoritative; the maintained artifact is used to identify review changes.

## Run

```text
python tools/rom-generation/execution-definition-generator/src/generate_execution_definitions.py --repo-root .
```

## Test

```text
python -m unittest discover -s tools/rom-generation/execution-definition-generator/tests -p "test_*.py"
```

After review, promote `build/simulation_outputs/rom-generation/execution-definition-generator/execution-definitions.candidate.json` to `rom/microcode/v1/execution-definitions.json`.
