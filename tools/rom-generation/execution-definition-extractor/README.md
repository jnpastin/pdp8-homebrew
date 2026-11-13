# Execution-Definition Extractor

## 1. Purpose

The execution-definition extractor reads the microarchitecture execution documents and produces execution cases. Each case is one major state and timing state, or one console transaction, with the micro-operations it selects: unconditionally, and under documented predicates.

The extractor does not:

- derive instruction behavior from mnemonics
- evaluate predicates or reproduce derived-control logic; conditions such as `AUTO_INDEX_REQUIRED`, `ISZ_SKIP_REQUIRED` and `SKIP_TAKEN` are kept as written
- check that context and predicate names are defined control inputs

## 2. Authoritative Inputs

| Document | Cases |
|---|---|
| `docs/03-microarchitecture/04-fetch-defer.md` | FETCH and DEFER timing states |
| `docs/03-microarchitecture/05-mri-execution.md` | MRI instructions |
| `docs/03-microarchitecture/06-iot-execution.md` | external-IOT phase binding and CPU-handled IOT instructions |
| `docs/03-microarchitecture/08-interrupt-execution.md` | INTERRUPT timing states |
| `docs/03-microarchitecture/09-console-execution.md` | console operations |
| `docs/03-microarchitecture/10-dma-execution.md` | DMA timing states |
| `docs/03-microarchitecture/07-opr/01-group1-execution.md` | OPR Group 1 |
| `docs/03-microarchitecture/07-opr/02-group2-execution.md` | OPR Group 2 |
| `docs/03-microarchitecture/07-opr/03-group3-execution.md` | OPR Group 3 |
| `docs/03-microarchitecture/02-micro-operations.md` | none; the catalog of micro-operation names |

All are required.

## 3. Source Document Conventions

Each document has its own layout, and the extractor has one parser per layout. Each parser expects a fixed structure, and every place a document departs from it is an error (section 5), so a documentation change never silently drops or changes a case.

### 3.1 Common Elements

- **Headings** are level 2 to 6, optionally numbered (`### 3.1 TS1`). Headings inside code blocks are ignored. A heading's body runs to the next heading at or above its level.
- **μop lists** are the bullets after a `μops:` label (or, where noted, after a heading or `TSn:` marker). Blank lines between bullets are allowed; any other line ends the list. The placeholders `(no μops)` and `(no unconditional μops)` stand for an empty list.
- **Conditional μops** follow a `Conditional μops:` label as a text code block of `PREDICATE -> MICRO_OPERATION` lines.
- Markdown escapes (`\_`, `\[`, `\]`) and surrounding backticks are removed from every value.

Labels and text the parsers don't use, such as `Description:`, `Control Decisions:` and `Result:`, are ignored.

### 3.2 FETCH and DEFER

The `## n. FETCH Execution` and `## n. DEFER Execution` sections each have `### n.m TSk` headings for TS1 to TS4. Each heading gives one case, `fetch-defer:<number>`, with context `MS = FETCH` or `MS = DEFER`, its `μops:` list, and its `Conditional μops:`.

The DMA document's `## n. DMA Execution` section has the same layout and gives the cases `dma:<number>`, with context `MS = DMA`. Every DMA timing state has `- (no μops)`; the CPU does no datapath work during DMA.

### 3.3 MRI and IOT Instructions

Each numbered level-3 heading whose title contains `IR[` is an instruction, and its title, an `AND`-joined condition, is its context. The heading's body has `TSn:` markers for TS1 to TS4; each marker gives one case, `mri:<number>:ts<n>` or `iot:<number>:ts<n>`, with the bullets after the marker and any `Conditional μops:` before the next marker.

Heading terms are rewritten as control inputs:

| Heading term | Context term |
|---|---|
| `IR[11:9] = 000` to `101` | `IR_MRI_OPCODE = <opcode>` |
| `IR[11:9] = 110` | `IR_IS_IOT = 1` |
| `IR[2:0] = <bits>` | `IR_IOT_OP = <bits>` |
| `IOA = <nn>` | `IR_IOA = <6-bit binary>` |

Device addresses are written in octal, so `IOA = <nn>` takes a two-digit octal address and converts it to the 6-bit binary form of `IR_IOA`, which is `IR[8:3]`; for example, `IOA = 27` becomes `IR_IOA = 010111`. Any other `IOA = ` term is an `UNTRANSLATED_CONTEXT_TERM` error unless its heading is in the table below.

Some IOT headings select on IR bits that have a decoded control input instead. The extractor holds a table of these headings, keyed by the full heading title, giving each one's context. It has two entries: the CAF heading `IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 111` becomes `IR_IS_CAF = 1`, the same decode the CAF `/INITIALIZE` assignment is keyed on; and the memory extension heading `IR[11:9] = 110 AND IR[8:6] = 010` (devices 20–27) becomes `IR_IS_MEMEXT_IOT = 1`. That section's micro-operations are all conditional on the memory-management flags (`IR_WRITES_DF`, `IR_READS_IB`, and so on), written in its `Conditional μops:` block.

Every case's context starts with `MS = EXECUTE`; MRI cases then add `IR_IS_MRI = 1`.

### 3.4 External-IOT Phase Binding

The `## n. External IOT Phase Binding` section is prose. The extractor requires these two bullets verbatim (backticks ignored):

```text
- IO_CLEAR_AC_REQ selects AC_CLEAR during the TS in which the request is asserted.
- IO_SKIP_REQ selects PC_INC during TS4.
```

From them it builds four cases, `iot:external:ts1` to `ts4`, with context `MS = EXECUTE` and `IR_IS_EXTERNAL_IOT = 1`. Every case has the conditional `IO_CLEAR_AC_REQ = 1 -> AC_CLEAR`; TS4 also has `IO_SKIP_REQ = 1 -> PC_INC`. If the section's wording changes, the extractor's table of bindings must be updated with it.

### 3.5 INTERRUPT

Each level-3 heading whose title starts with `TSk`, such as `### 4.1 TS1 — PC Capture`, gives one case, `interrupt:<number>`, with context `MS = INTERRUPT`. Its μops are the bullets directly under the heading. TS1 to TS4 must each appear once.

### 3.6 Console Operations

Each `## n. <Name> Operation` section with a `μops:` label gives one case, `console:<n>`, with:

- its context from the `Applicable context:` code block
- an `Execution model:` code block that must read `single TS-equivalent console transaction`
- `execution_model` `console-transaction` and `timing_state` `null`

Operation sections without a `μops:` label, such as Clear and Continue, execute no micro-operations and produce no case.

### 3.7 OPR Groups

The context of every case is `MS = EXECUTE` followed by the lines of the document's `Applies when:` code block, such as `IR_IS_OPR = 1` and `IR_OPR_GROUP1 = 1`.

Within the `## n. Instruction Definition` section, a timing state starts at a `TSn:` line or a `### n.m TSn` heading; any other heading ends it. TS1 to TS4 must each appear once. Each timing state's top-level bullets must be one of:

| Bullet | Meaning |
|---|---|
| `if PREDICATE: MICRO_OPERATION` | a conditional μop |
| `if PREDICATE:` | a control-level effect with no μop, explained by nested bullets, such as HLT |
| a placeholder | nothing |

A `Conditional μops:` block within a timing state adds more conditional μops. Predicates must name IR-derived control inputs, such as `IR_OPR_CLA = 1`, never IR bits.

Every documented timing state produces a case, `opr<group>:ts<n>`, including one whose only bullet is a placeholder: that case selects no μops, so the control word for that group and TS is still defined. A case's line is the timing state's first line.

### 3.8 Micro-Operation Catalog

Every level-3 heading in `02-micro-operations.md` whose title is a name, such as `### AC_CLEAR`, defines a micro-operation.

## 4. Extracted Representation

```json
{
  "id": "mri:3.3:ts4",
  "source": {
    "path": "docs/03-microarchitecture/05-mri-execution.md",
    "line": 66
  },
  "execution_model": "major-state",
  "context": ["MS = EXECUTE", "IR_IS_MRI = 1", "IR_MRI_OPCODE = 010"],
  "timing_state": 4,
  "micro_operations": ["MEM_WRITE_FROM_MB"],
  "conditional_micro_operations": [
    {"predicate": "ISZ_SKIP_REQUIRED = 1", "micro_operation": "PC_INC"}
  ]
}
```

| Property | Meaning |
|---|---|
| `id` | the case id described in section 3 |
| `source` | the document and the line of the case's heading or first marker |
| `execution_model` | `major-state`, or `console-transaction` for console operations |
| `context` | the conditions that select the case, in document order |
| `timing_state` | 1 to 4, or `null` for console operations |
| `micro_operations` | the unconditional micro-operations, in document order |
| `conditional_micro_operations` | each `predicate` and the `micro_operation` it selects, in document order |

Cases are in document order, with documents in this order: FETCH/DEFER, MRI, IOT phase binding, IOT instructions, INTERRUPT, DMA, console, OPR Groups 1 to 3.

## 5. Validation

`ERROR` diagnostics:

| Code | Condition | Location |
|---|---|---|
| `MISSING_SECTION` | an expected section is absent: FETCH, DEFER, or DMA, phase binding, OPR Instruction Definition, or a heading in the decoded-IOT table | document |
| `MISSING_TIMING_STATE` | a state, instruction, INTERRUPT, or OPR group lacks one of TS1 to TS4 | section heading |
| `DUPLICATE_TIMING_STATE` | one of TS1 to TS4 appears more than once | section heading |
| `MISSING_CODE_BLOCK` | a `Conditional μops:` label has no code block after it | label |
| `MALFORMED_CONDITIONAL` | a conditional line is not `PREDICATE -> MICRO_OPERATION` | line |
| `UNTRANSLATED_CONTEXT_TERM` | an instruction heading term still names IR bits after rewriting, or an `IOA = ` term is not a two-digit octal address | heading |
| `MISSING_PHASE_BINDING` | a required phase-binding bullet is absent; no phase-binding cases are produced | section heading |
| `MISSING_CONTEXT` | a console operation lacks its `Applicable context:` block, or an OPR document its `Applies when:` block | heading or document |
| `UNEXPECTED_EXECUTION_MODEL` | a console operation's execution model is missing or different | heading |
| `UNRECOGNIZED_OPR_LINE` | an OPR bullet is not a conditional, a control-level effect, or a placeholder | line |
| `RAW_IR_BIT` | an OPR predicate contains `IR[` or `bit(` | line |
| `NO_CASES_FOUND` | a parser found no cases and reported nothing else | document |
| `DUPLICATE_CASE_ID` | a case id is used again; reported on the repeat | case |
| `MALFORMED_MICRO_OPERATION` | a μop is not an upper-case name | case |
| `UNKNOWN_MICRO_OPERATION` | a μop is not in the catalog | case |

`FATAL`: `EXTRACTION_FAILURE` when a source document is missing, unreadable, or not valid UTF-8. Its location is `<input>`, and its message names the file. No JSON is written.

Errors in one section do not stop the extraction of the others.

## 6. Generated Outputs

The default generated files are:

```text
build/
└── simulation_outputs/
    └── rom-generation/
        └── execution-definition-extractor/
            ├── execution-definitions.json
            └── extraction-report.txt
```

Each run first deletes the JSON and report from any earlier run (see the shared README, section 15.2), and refuses to run if an output path is a source document or a directory.

### 6.1 JSON Output

```json
{
  "format_version": 1,
  "control_design_version": "v1",
  "artifact": "execution-definitions",
  "extraction_stage": "documentation-extraction",
  "cases": [],
  "diagnostics": []
}
```

Each diagnostic has `severity`, `code`, `message`, `source_path`, `line` and `case_id`; `line` and `case_id` are `null` when unknown. Diagnostics are sorted by severity, code, source path, line, case id, and message.

The JSON is written whenever every document can be read, even when there are errors. It follows the shared output format: UTF-8 with LF line endings and one trailing newline, two-space indentation, non-ASCII characters written directly, and keys in the fixed order shown.

### 6.2 Extraction Report

The report gives the number of cases and of diagnostics by severity, then every diagnostic in the JSON's order, one per line:

```text
SEVERITY CODE [case-id] path:line: message
```

`[case-id]` and `:line` are left out when unknown.

## 7. Command-Line Interface

Run from the repository root:

```text
python tools/rom-generation/execution-definition-extractor/src/extract_execution_definitions.py --repo-root .
```

The required option is:

```text
--repo-root REPOSITORY_PATH
```

Optional overrides:

```text
--json-output OUTPUT_PATH      default: <output directory>/execution-definitions.json
--report-output OUTPUT_PATH    default: <output directory>/extraction-report.txt
```

Relative paths are resolved from the supplied repository root. Absolute paths are used unchanged.

The tool prints a short summary, followed by any `ERROR` or `FATAL` diagnostics, and exits with status `1` when any are reported, `0` otherwise.

## 8. Testing

Tests use Python's standard `unittest` framework.

Run the tests from the repository root:

```text
python -m unittest discover -s tools/rom-generation/execution-definition-extractor/tests -p "test_*.py"
```

The tests build small documents inline and use temporary directories; they do not read the real documentation. Unit tests are grouped by parser, covering every diagnostic code. End-to-end tests write all nine documents to a temporary repository and run `main()` against it.

Two end-to-end tests compare the complete JSON and report with expected files under `tests/golden/`:

- `valid/`: one document of each layout, including placeholders, ignored labels and prose, indented markers, and a control-level OPR bullet, which extract without diagnostics
- `invalid/`: documents that break each parser's expectations, which fixes diagnostic order

`valid/execution-definitions.json` is also the reference for later tools' contract tests.

After an intentional output change, regenerate the golden files from the repository root and review the diff before committing:

```text
UPDATE_GOLDEN=1 python -m unittest discover -s tools/rom-generation/execution-definition-extractor/tests -p "test_*.py"
```

On Windows PowerShell, set the variable first with `$env:UPDATE_GOLDEN = "1"` and remove it afterwards.

## 9. Implementation Constraints

The implementation must:

- use only the Python standard library
- support Windows, Linux, and macOS
- avoid shell-specific behavior
- use repository-relative source references
- preserve source ordering and traceability
- produce deterministic output
- report malformed documentation without inventing replacement values
- remain proportional to the tool's bounded purpose

The implementation is one Python source file, `src/extract_execution_definitions.py`, organized in pipeline order: constants and patterns, Markdown reading, one parser per document layout, validation, extraction, output, and the command line.

## 10. Relationship to Later Stages

The execution-definition generator reads this output, reports how it differs from the maintained artifact, and writes a candidate for `rom/microcode/v1/execution-definitions.json`. The symbolic control-word generator then combines each maintained case's context, timing state and micro-operations with the micro-operation mapping to compose control words.
