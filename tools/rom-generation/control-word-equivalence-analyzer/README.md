# Control-Word Equivalence Analyzer

## 1. Purpose

The control-word equivalence analyzer partitions the promoted symbolic control words into legal concrete behavior and reports, for review:

- which complete control words each execution case can produce
- which words, or parts of words, are identical across cases or within one case (equivalence and aliasing)
- which assignments and input regions can never occur (unreachable analysis)
- where execution cases overlap, and which reachable input regions no case covers
- which control inputs affect the control word (input significance)

It is the "input permutation analysis" stage of the shared README, section 10, and must be accepted before logical control-address packing starts.

The analyzer does not:

- reconstruct behavior from the mappings or definitions: it reads only the conditions and values in the symbolic artifact
- modify any input, or produce a maintained artifact
- assign control addresses, choose an address encoding, or pack bits

## 2. Inputs

All four inputs are read from one directory, by default `rom/microcode/v1/`:

| Input | File | Used for |
|---|---|---|
| symbolic control words | `symbolic-control-words.json` | every case's base context, defaults and guarded assignments |
| control-input schema | `control-input-schema.json` | input domains, `exactly_one` / `at_most_one` constraints, "Mutually exclusive with X." field constraints |
| control-word schema | `control-word-schema.json` | the encoded fields and their domains, and the domain of `MS` |
| timing constraints | `timing-constraints.json` | combinations a timing context excludes |

The analyzer never writes any of its inputs.

## 3. Generated Outputs

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── control-word-equivalence-analyzer/
            ├── control-word-equivalence.json
            └── analysis-report.txt
```

Each run first deletes both outputs. The report is written on every run; the analysis only when no `ERROR` or `FATAL` diagnostic is reported. Both follow the shared output format (shared README, section 15.1).

## 4. Method

### 4.1 Regions and constraints

A region is a set of input combinations described as a box: each name is restricted to a subset of its domain. Domains are those of the shared predicate module (`tools/rom-generation/common/predicates.py`); a domain is enumerated, and a name with more than 4096 values cannot be compared.

A combination is reachable unless it violates a constraint:

| Kind | Violated when |
|---|---|
| `exactly_one` | two or more of its inputs are `1`, or none is |
| `at_most_one` | two or more of its inputs are `1` |
| `mutual_exclusion` | both inputs of a "Mutually exclusive with X." pair are `1` |
| `timing` | the timing context holds and its requirement does not |
| `derivation` (`ir-derivation`) | the IR-derived inputs take values that no 12-bit IR value produces; values come from evaluating every documented derivation for all 4,096 IR values (IR-Derived Flags §1.1). Only IR-derived inputs that some condition compares take part |

A derivation that mentions IR but cannot be evaluated is reported as `IR_DERIVATION_UNUSABLE`, and its input stays unconstrained.

Unlike the generator, which uses `exactly_one` only pairwise, the analyzer also excludes the all-zero combination of an `exactly_one` group. Field-constraint text is recognized only in the exact form `Mutually exclusive with X.`; other text is not interpreted.

### 4.2 Components

Each base context must be a conjunction of comparisons; it fixes the case's starting box. A name restricted to one value there is fixed; every other name a guard compares is free.

Before forming components, the IR-derivation constraint is specialized to the case: the base box is tightened to the IR-derived values its consistent IR values allow (so an MRI case has `IR_IS_IOT = 0`), and the table is projected onto the names that some still-undecided condition compares, then split into independent groups. Groups are accepted only when their product reproduces the table exactly. This keeps unrelated decode bits, such as the OPR micro-operation bits, in separate components.

Guards that assign the same field, compare the same free name, or compare free names tied together by one constraint form one component. Components share no fields, no free names and no constraints, so they are independent: a case's complete words are exactly the product of its components' partial words, and are never enumerated.

### 4.3 Partitioning

Each component is split by a decision tree. A node splits on the first free name, in first-use order, that keeps some guard undecided: one branch per compared value, plus one for all remaining values. A node is pruned, and recorded as an unreachable region, as soon as a constraint excludes it; a leaf must also contain at least one reachable combination.

At each leaf every guard is decided. The firing assignments give each component field its value, or its default when none fires. Two firing assignments with different values for one field is a `CONFLICTING_ASSIGNMENTS` error.

Leaves with the same partial word form a branch. A branch's condition is the union of its leaves, merged and written over the free names.

### 4.4 Equivalence and aliasing

Values are compared exactly. A field assigned by `value_from_input` holds `{"from_input": NAME}`, which differs from every literal value: a supplied value is never collapsed into a fixed encoding.

Components that are identical in every field, branch word, condition and provenance are one component class, shared by every case that has them. Alias kinds:

| Kind | Meaning |
|---|---|
| `within_case` | one branch is produced by more than one set of firing assignments |
| `default_only` | assignments fire but give every component field its default, so the branch equals inactivity |
| `supplied_data` | two branches with the same fields differ only in fields where one holds a supplied value |
| `cross_case` | two cases can produce the same complete word; `shared_word_count` is the exact number of shared words |

Cross-case counts join the components of both cases that share a field and compare the restricted words; a join larger than 200,000 combinations is skipped with `ALIAS_NOT_COMPUTED`.

### 4.5 Unreachable analysis

| Kind | Meaning | Assessment |
|---|---|---|
| `case` | the base context is contradictory, or no reachable combination satisfies it | `suspect` |
| `assignment` | the guard never holds in a reachable leaf | `suspect` when the guard contradicts itself within the base context, otherwise `expected` |
| `region` | a region of a component excluded by constraints | `expected` |

Each entry names the conflicting constraints: those that alone exclude it, otherwise every constraint on a name it restricts.

### 4.6 Case coverage

A second decision tree splits on the names compared by every base context. A reachable leaf where two bases hold is a case overlap; a reachable leaf where none holds is an uncovered region. Coverage considers only the names that bases compare.

### 4.7 Input significance

Within a case, a free name is significant when changing it alone, from one reachable combination to another, changes some field. This is found per field, so it does not depend on the component split.

When constraints tie inputs together, no single change may be reachable even though the word depends on the inputs (for example two members of an `exactly_one` group). Joint significance repairs this: while two reachable combinations with different words agree on every significant name, the first name, in component order, on which their regions differ is added. The result determines the word but is not necessarily minimal; choosing a minimal address set is left to address packing.

Each control input, `MS`, `TS`, and every encoded field compared as an input, gets one category:

| Category | Meaning |
|---|---|
| `behavioral` | significant in some case, or fixed by some reachable case's base context (it selects cases) |
| `supplied_data` | only supplies a `value_from_input` |
| `no_effect` | compared, but never changes a word |
| `unreferenced` | never compared or supplied |

## 5. Analysis Structure

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "control-word-equivalence",
  "generation_stage": "analysis",
  "representation": "factored",
  "sources": ["symbolic-control-words.json", "control-input-schema.json", "control-word-schema.json", "timing-constraints.json"],
  "summary": {},
  "constraints": [],
  "inputs": [],
  "cases": [],
  "component_classes": [],
  "aliases": [],
  "case_overlaps": [],
  "uncovered_regions": [],
  "unreachable_regions": [],
  "diagnostics": []
}
```

A case:

```json
{
  "execution_case_id": "fetch-defer:3.1",
  "source": {"path": "docs/03-microarchitecture/04-fetch-defer.md", "line": 42},
  "base_context": "(MS = FETCH AND TS = 1)",
  "reachable": true,
  "word_count": 16,
  "component_classes": ["cc-0001", "cc-0002"],
  "significant_inputs": ["CIFP", "RUN", "FP_EXAMINE"],
  "jointly_significant_inputs": [],
  "referenced_inputs": ["MS", "TS", "CIFP", "RUN", "FP_EXAMINE"]
}
```

A component class:

```json
{
  "class_id": "cc-0106",
  "fields": ["IOT_ACTIVE"],
  "inputs": ["IR_IOA"],
  "branches": [
    {
      "branch_id": "cc-0106.b2",
      "word": {"IOT_ACTIVE": "1"},
      "condition": "IR_IOA != 000000",
      "assignment_sets": 1,
      "assignments": [
        {"field": "IOT_ACTIVE", "value": "1", "origin": "direct-control definition", "source": "02:7.2", "in_every_region": true}
      ]
    }
  ],
  "cases": ["iot:10.1:ts1", "iot:10.1:ts2"]
}
```

A case's complete words are every choice of one branch from each of its component classes; fields in no component keep their defaults. `in_every_region` is false for an assignment that fires in only some of the branch's regions.

Ordering is deterministic: cases in artifact order; classes and branches in order of first appearance; class ids `cc-NNNN` and branch ids `cc-NNNN.bN` by that order.

## 6. Diagnostics

| Severity | Code | Meaning |
|---|---|---|
| FATAL | `ANALYSIS_FAILURE` | an input is missing, unreadable, not UTF-8, not JSON, or not an object |
| ERROR | `UNEXPECTED_ARTIFACT_TYPE`, `CONTROL_DESIGN_VERSION_MISMATCH` | wrong input file or version |
| ERROR | `INVALID_SPECIFICATION`, `INVALID_CONTROL_INPUT_SCHEMA`, `INVALID_SYMBOLIC_CONTROL_WORDS` | malformed input structure |
| ERROR | `INVALID_EXPRESSION`, `UNKNOWN_NAME`, `INVALID_COMPARED_VALUE`, `DOMAIN_TOO_LARGE` | a condition cannot be analyzed |
| ERROR | `MISSING_CONTROL_FIELD`, `UNKNOWN_CONTROL_FIELD`, `INVALID_FIELD_VALUE` | incomplete or invalid control word |
| ERROR | `UNKNOWN_SUPPLYING_INPUT`, `SUPPLYING_INPUT_WIDTH_MISMATCH` | invalid `value_from_input` |
| ERROR | `UNSUPPORTED_BASE_CONTEXT` | a base context is not a conjunction of comparisons |
| ERROR | `CONFLICTING_ASSIGNMENTS` | a reachable leaf gives one field two values |
| WARNING | `CASE_OVERLAP` | the case's base context holds together with another's |
| WARNING | `UNCOVERED_REGION` | no execution case applies in a reachable region |
| WARNING | `UNREACHABLE_CASE`, `CONTRADICTORY_ASSIGNMENT_GUARD` | suspect unreachable behavior |
| WARNING | `CONTROL_FIELD_COMPARED_AS_INPUT` | an encoded control-word field is compared as an input, though the control-input schema does not define it |
| WARNING | `ALIAS_NOT_COMPUTED` | a cross-case join was too large |
| WARNING | `IR_DERIVATION_UNUSABLE` | an IR derivation cannot be parsed or evaluated, or depends on an input not derived from IR |
| INFO | `JOINT_SIGNIFICANCE` | inputs that matter only together (section 4.7) |
| INFO | `EXPECTED_UNREACHABLE` | count of expected unreachable entries |

Warnings describe the specification under review; they do not stop the analysis.

## 7. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/control-word-equivalence-analyzer/src/analyze_control_word_equivalence.py --repo-root .
```

Optional overrides:

```text
--artifact-dir DIRECTORY        default: rom/microcode/v1
--analysis-output OUTPUT_PATH   default: <output directory>/control-word-equivalence.json
--report-output OUTPUT_PATH     default: <output directory>/analysis-report.txt
```

Relative paths are resolved from the repository root. The tool exits with status `1` when any `ERROR` or `FATAL` diagnostic is reported, and `0` otherwise. A full repository run takes about half a minute.

## 8. Testing

```text
python -m unittest discover -s tools/rom-generation/control-word-equivalence-analyzer/tests -p "test_*.py"
```

Small inline fixtures cover cross-case and within-case equivalence, one-field differences, default-only aliasing, conditional partitioning, supplied values, `exactly_one`, `at_most_one`, mutual-exclusion and timing constraints, contradictory predicates and base contexts, multi-valued inputs, provenance, deterministic ids and ordering, field coverage, malformed or unknown names, conflicts, overlaps and uncovered regions, single and joint significance, and complete runs through `main()`. Repository tests analyze every promoted case.

## 9. Implementation Constraints

The implementation uses only the Python standard library, is one source file, `src/analyze_control_word_equivalence.py`, plus the shared predicate module, and preserves deterministic ordering on every operating system.
