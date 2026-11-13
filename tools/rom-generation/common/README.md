# Shared ROM-Generation Modules

Modules here are used by more than one ROM-generation tool (see the shared README, section 4). Each tool adds this directory to `sys.path` and imports from it.

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
