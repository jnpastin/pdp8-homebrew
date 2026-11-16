# ROM-Generation Pipeline

## 1. Purpose

The pipeline runner runs every ROM-generation tool in order. It presents each tool's diagnostics, and it promotes a generator's candidate artifact into `rom/microcode/v1/` only when the user accepts the promotion.

It replaces running the tools one at a time and copying candidates by hand. It adds no behavior of its own: each stage is the tool's normal command line with `--repo-root`.

## 2. Stages

| # | Stage | Promotes |
|---|---|---|
| 1 | `control-input-extractor` | |
| 2 | `control-input-schema-generator` | `control-input-schema.json` |
| 3 | `control-output-extractor` | |
| 4 | `control-word-schema-generator` | `control-word-schema.json` |
| 5 | `micro-operation-extractor` | |
| 6 | `micro-operation-mapping-generator` | `micro-operation-mapping.json` |
| 7 | `direct-control-extractor` | |
| 8 | `direct-control-generator` | `direct-control-definitions.json` |
| 9 | `execution-definition-extractor` | |
| 10 | `execution-definition-generator` | `execution-definitions.json` |
| 11 | `timing-constraint-extractor` | |
| 12 | `timing-constraint-generator` | `timing-constraints.json` |
| 13 | `symbolic-control-word-generator` | `symbolic-control-words.json` |
| 14 | `control-word-equivalence-analyzer` | |
| 15 | `control-store-packer` | |

A generator reads the artifacts promoted before it, so the order matters.

## 3. Each Stage

1. Run the tool.
2. Print the diagnostics section of the tool's report, with a count by severity.
3. If the tool exited with a non-zero status, stop. The pipeline fails.
4. For a generator stage, compare the candidate with the maintained artifact, ignoring line endings:
   - **Equal:** nothing to promote; continue.
   - **Different:** print how many lines changed and ask `Promote …? [y]es / [n]o / [d]iff`.
     - `d` prints a unified diff and asks again.
     - `y` copies the candidate to `rom/microcode/v1/` and continues.
     - `n`, or the end of input, stops the pipeline. Later stages read the maintained artifacts, so they cannot run on a candidate that was not promoted.

The diagnostics are always shown before the promotion question. A generator's warnings, such as `CHANGED_CASE`, describe how its candidate differs from the maintained artifact.

The run ends with a summary of every stage's status: `ok`, `unchanged`, `promoted`, `pending` (dry run), `declined`, or `failed`.

## 4. Command Line

```text
python tools/rom-generation/pipeline/src/run_pipeline.py
```

Run it from the repository root, or pass `--repo-root`.

| Option | Meaning |
|---|---|
| `--repo-root PATH` | repository root; default the current directory |
| `--from STAGE` | start at this stage |
| `--to STAGE` | stop after this stage |
| `--dry-run` | run every stage and report pending promotions without asking or promoting; later stages then read the current maintained artifacts |
| `--list` | list the stages and what each promotes |

Exit status: `0` when every stage succeeded and every needed promotion was accepted, `1` when a tool failed, `2` when a promotion was declined.

A full run takes about 15 seconds.

## 5. Testing

```text
python -m unittest discover -s tools/rom-generation/pipeline/tests -p "test_*.py"
```

The tests run small fake tools in a temporary repository. They cover report parsing, accepted, declined, and unchanged promotions, the diff option, end of input, tool failure, dry runs, stage selection, and that every stage's script and maintained artifact exist.
