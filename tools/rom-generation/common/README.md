# Shared ROM-Generation Modules

Modules here are used by more than one ROM-generation tool (see the shared README, section 4). Each tool adds this directory to `sys.path` and imports from it.

## `artifact_changes.py`

Classifies how a candidate artifact differs from the maintained one, entry by entry: `material` (its content differs), `moved` (only its source line numbers differ), `renamed` (new under its identifier, with the content of exactly one maintained entry that is no longer present), `added`, or `removed`. Source line numbers are the values of the `line` and `source_line` keys at any depth; a changed source path is material. A renamed entry may also differ in the leading section number of its `title` and `group`.

| Function | Use |
|---|---|
| `compare_entries` | two `{identifier: entry}` maps, as a generator holds them |
| `compare_artifacts` | two whole artifacts: each top-level list whose entries all carry a unique `id`, `execution_case_id`, `micro_operation`, or `name` is compared entry by entry, and any other top-level value as one entry |
| `strip_locations`, `describe`, `only_moved` | the content without line numbers, a one-line count, and whether only line numbers changed |

Current users: the execution-definition, timing-constraint, symbolic control-word, and direct-control generators, and the pipeline.

## `predicates.py`

The control-predicate rules used by every tool that interprets a condition from the maintained specifications:

| Part | Contents |
|---|---|
| Grammar | `parse_expression`, `canonical`, and the nested-tuple expression form; the grammar is described in the symbolic control-word generator README, section 5 |
| Evaluation | `evaluate`, three-valued over a partial assignment of names to values |
| Domains | `Domain` and `value_domains`: the values each comparable name (control input, encoded control-word field, `MS`, `TS`) can take |
| Reachability | `exclusive_pairs` (from `exactly_one` and `at_most_one` global constraints and "Mutually exclusive with X." field constraints) and `can_hold_together`, which also rejects IR-derived values no single IR value gives when passed an `IrValues` |
| IR derivations | `parse_derivation` and `ir_derivation_table`: parse the documented derivation of each IR-derived input (IR-Derived Flags §1.1, with `//` comments) and evaluate it for all 4,096 IR values; `IrValues` indexes the result as sets of IR values |

An input is IR-derived when it belongs to the IR-Derived Signals domain, or its derivation reads IR bits directly. So a decode built only from other decodes, such as `IR_IS_EXTERNAL_IOT`, is evaluated, while a derived flag that combines a decode with machine state, such as `AUTO_INDEX_REQUIRED = IR_INDIRECT AND EAI`, is not. An IR-derived input whose derivation cannot be evaluated is reported as a problem.

Current users:

- `symbolic-control-word-generator`
- `control-word-equivalence-analyzer`

A change here changes how every user reads a predicate, so run the tests of every user, and `tests/` here, after changing it:

```text
python -m unittest discover -s tools/rom-generation/common/tests -p "test_*.py"
```
