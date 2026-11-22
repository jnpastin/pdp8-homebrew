# Documentation Conventions

## 1. Purpose

The documents under `docs/` have two readers:

- **People**, who must be able to understand and build the machine from them alone.
- **The ROM-generation extractors**, which turn parts of some documents into the control store.

This document says how the documentation is organized, what each reader needs, and how to edit a parsed document without changing the machine by accident.

The main danger is that the extractors read ordinary Markdown. A sentence, a bold word, or a blank-looking label change can add or delete control behavior, often with no error.

---

## 2. Structure

### 2.1 Sections

| Directory | Answers | Must not define |
|---|---|---|
| `00-overview` | What is being built, and the project-wide conventions | Behavior |
| `01-architecture` | What state exists, and who writes it | When each write happens, except as a constraint |
| `02-isa` | What a program observes | Timing states, micro-operations, signals |
| `03-microarchitecture` | What happens in each major state and timing state | Signal encodings |
| `04-control` | Which signals produce that behavior, and how the control store supplies them | Instruction semantics |
| `05-buses-and-signals` | Which signals cross which boundary, and who may drive them | Signal behavior |
| `06-memory` | What memory requires at its interface | How the CPU chooses addresses |
| `07-io` | The contracts with controllers and the DMA arbiter | Controller implementation |
| `08-interrupts-and-skip` | How interrupts and skips work across the sections above | New register, instruction, or signal definitions |
| `09-timing` | When events happen, and how long they take | What the events do |
| `10` to `13`, `appendices` | Panel, physical design, verification, plan, supporting material | Architecture |

### 2.2 Authority

- Each fact has one owning document. Other documents link to it, or repeat it only as far as a reader needs in order to follow them.
- `docs/` is the authority for the machine. A permanent document must not depend on a plan, handoff, branch working file, or conversation. Move what is needed into `docs/`.
- Generated artifacts and the simulator follow the documents. If they disagree, resolve the design question first, then correct whichever is wrong.
- Diagrams are maintained from their `source/` files. When text changes what a diagram shows, record the required diagram change.

### 2.3 Document Layout

1. A title, then a numbered Purpose section.
2. An overview that a person can follow before reaching any definition: a short explanation, a table, or a diagram.
3. The definitions and their detail.
4. Links to the owning documents for anything not defined there.

---

## 3. Human-Readability Requirements

### 3.1 Content

- State the behavior of the current machine. Design history and superseded behavior belong in the version history.
- Say what happens before how it is encoded. Give a name with a code: "direct JMP (`IR_CLASS = 001`)".
- Cover every case in a summary. "EXECUTE, except for JMP" is wrong if OPR is also an exception.
- State exceptions where the general rule is stated, not only in the document that introduces the exception.
- Give the reason for any rule that is not obvious.
- For DEC behavior, name the manual and section, and separate what it says from what is inferred. State deliberate differences from DEC.

### 3.2 Form

- One idea per sentence and one fact per bullet. Split sentences over about 40 words.
- Use a table when behavior varies by instruction, state, or group.
- Define an abbreviation or signal in the [Abbreviation Dictionary](./99-Abbreviations.md) before using it.
- Bits are numbered with 11 as the most significant, unless marked as DEC numbering. Addresses, instructions, and control-output encodings are octal. Control-input values are binary.
- Use "instruction completion" for the end of any instruction. Use "EXECUTE TP4" only for that specific TP.
- Use "applies", "commits", and "is recognized" with their TP when the order matters.
- Never describe a result in TSn as depending on something that occurs during TSn, or a visible value as changing during TP. A result depends only on state committed by TP(n-1) ([Microoperation Sequencing §6](../03-microarchitecture/03-microoperation-sequencing.md#6-register-visibility)).

### 3.3 Changes

After changing behavior, read the result as a person would:

1. Read each edited document in full, including text that was not edited.
2. Search all of `docs/` for the old behavior by meaning as well as by name: the old major state, TP, register source, and any "never", "only", or "no" rule that the change breaks.
3. Check the invariants, invalid-condition lists, summaries, section READMEs, and the glossary. The extractors don't read most of these, so no tool will find a contradiction in them.
4. Check the affected diagrams from their sources.

---

## 4. Machine-Read Documents

Only these documents are parsed. Everything else is for people only.

| Document | Extractor | What is taken |
|---|---|---|
| `02-isa/01-group-1.md`, `02-group-2.md`, `03-group-3.md` | control-input | Bit positions from the box diagrams |
| `03-microarchitecture/02-micro-operations.md` | micro-operation, execution-definition | The micro-operation catalog and names |
| `03-microarchitecture/04-fetch-defer.md` | execution-definition | FETCH and DEFER cases |
| `03-microarchitecture/05-mri-execution.md` | execution-definition | MRI cases |
| `03-microarchitecture/06-iot-execution.md` | execution-definition | Internal IOT cases and the external-IOT phase binding |
| `03-microarchitecture/07-opr/01` to `03` | execution-definition | That each group uses the OPR pass |
| `03-microarchitecture/08-interrupt-execution.md` | execution-definition | INTERRUPT cases |
| `03-microarchitecture/09-console-execution.md` | execution-definition | Console cases |
| `03-microarchitecture/10-dma-execution.md` | execution-definition | DMA cases |
| `04-control/10-control-input-definitions/00` to `04` | control-input | Inputs, values, derivations, constraints, consumers |
| `04-control/20-control-output-definitions/00` to `03` | control-output | Fields, defaults, encodings, constraints, micro-operation assignments |
| `04-control/30-direct-control-definitions/01`, `02` | direct-control | Contexts, assignments, drive states, constraints |
| `09-timing/03-major-state-timing.md` | timing-constraint | Constraints and state invariants that mark states unreachable |

Each extractor's `SOURCE_PATHS` or `SOURCE_PATH` is the definitive list.

---

## 5. Parsing Rules

### 5.1 All Parsed Documents

- Treat headings, their numbers and levels, labels, list markers, and code fences as syntax. Section numbers become case and definition identifiers.
- Artifacts record line numbers. Adding a line above parsed content changes the artifacts even when behavior is unchanged.
- Put explanations outside the parsed region: before the definitions, in a separate overview section, or at the safe places listed below.

### 5.2 Execution Documents

- A `μops:` label is recognized only as that exact line. The same applies to `Conditional μops:`, `Applicable context:`, `Execution model:`, and `Applies when:`.
- A micro-operation list ends at the first line that is neither blank nor a bullet. **Never put prose between a label and its bullets, or between two bullets.**
- In MRI and IOT execution, a `TSn:` line must be followed directly by its bullets.
- In INTERRUPT execution, the bullets directly under each TS heading are the micro-operations. Prose above them deletes them.
- Conditional blocks hold one `PREDICATE -> MICRO_OPERATION` per line.
- The external-IOT phase-binding sentences in IOT Execution §7 are matched word for word.
- An OPR group document needs its `Applies when:` block and its level-2 `OPR Pass` heading.
- **Safe place for prose:** below all the lists and blocks of that case: under `Description:` where the document has that label, otherwise after the case's last bullet and a blank line.

### 5.3 Micro-Operation Catalog

- Each level-3 heading in "μop Definitions (Alphabetical)" is a micro-operation.
- Category, Description, Target, Expression, and Sources each run to the next recognized label. Text after Sources becomes source names.
- Preconditions and Constraints take bullets only.
- **Safe place for prose:** in the Description. It is copied into the artifact as descriptive text, with no effect on the ROM images.

### 5.4 Control Inputs

- The index defines the inputs. A linked bullet under one of its domain headings is an entry.
- **Any bold text anywhere on a line is a label** inside a definition, and ends the section being read. Don't use bold for emphasis there.
- `Derivation`, `Expression`, and `Internal Composition` run to the next bold label or `---`. Text after the code block is still part of the logic. Comments inside a derivation use `//`.
- A line starting with `#` is read as a heading, even inside a code fence.
- Name, Purpose, and the other scalar attributes are read from one line only. A wrapped continuation is lost.
- Value Encoding bullets are binary values.
- A constraint reading exactly `Mutually exclusive with NAME.` affects reachability, as do indented `EXACTLY_ONE(...)` and `AT_MOST_ONE(...)` bullets. Rewording one changes the control store's reachable states.
- **Safe place for prose:** a `Realization` paragraph, with no other bold text in it.

### 5.5 Control Outputs

- Definitions are the level-3 headings under a level-2 "Signal Definitions" heading, for signals listed in the index.
- Scalar attributes are read from one line only. Bold text at the start of a line ends a section.
- Every line under Encoding is read as an encoding. `Note: text` becomes a value named `Note`.
- `Used by μops` bullets are the assignments that build the control word. They are not just cross-references.
- **Safe place for prose:** on the Purpose or Description line, or in section 7 of Microarchitectural Control Signals.

### 5.6 Direct Control

- A definition is a numbered heading with no heading nested below it. **Adding a subheading inside a definition removes the definition.**
- A label is any line outside a code block that ends in a colon. An ordinary sentence ending in a colon ends the current section.
- Assignments, contexts, commits, and drive states belong in `text` code blocks. The lines of a context are joined by AND.
- Write each context out in full. A name such as "instruction completion" is not expanded.
- **Safe place for prose:** at the end of a definition, in a paragraph without a trailing colon, or in the parent section's introduction.

### 5.7 Timing Constraints

- A bullet that is only a code span containing ` IF ` is a constraint, whatever was intended.
- Under a `TSn` heading, it is limited by that TS and the nearest `Applicable context:` block. Under "State Invariants", it holds in every TS.
- A constraint says the situation cannot occur, so the control store gives that situation no defined behavior. Don't use one to express a preference, and check it against every controller contract.
- **Safe place for prose:** any bullet or paragraph that is not a lone code span.

### 5.8 ISA Group Diagrams

- In the three OPR group documents, every box drawing is read as an encoding diagram: bit numbers in the first row, three-letter mnemonics in the last.
- Put any other box drawing in another document.

---

## 6. Known Traps

Each of these was triggered in a test copy with the current extractors.

| Edit | Effect | Reported by the extractor |
|---|---|---|
| A sentence after a derivation's code block | Becomes part of the expression | No |
| A bold word above a Consumed By list's bullets | The consumers are lost | No |
| A wrapped Purpose line | The second line is lost | No |
| A sentence above INTERRUPT's bullets | That TS loses its micro-operations | No |
| A sentence after `TS4:` in MRI execution | That TS loses its micro-operations | No |
| A reworded `μops:` label | That TS loses its micro-operations | No |
| A note between two micro-operation bullets | The bullets after it are lost | No |
| A sentence after a micro-operation's Sources | Becomes source names | No |
| A subheading inside a direct-control definition | The definition is lost | No |
| A line ending in a colon under Constraints | The section ends there | No |
| A code-span bullet containing ` IF ` | Becomes a reachability constraint | No |
| A `#` line inside a control-input code block | The definition is broken | Yes |
| A reworded phase-binding sentence | The external-IOT cases fail | Yes |
| A `Note:` line under Encoding | An invalid encoding | Yes |

A later stage may report a difference from the maintained artifact as a warning, but a warning does not block promotion.

---

## 7. Editing Procedure

For every edit to a document in section 4:

1. Make the edit, following section 5.
2. Run `python tools/rom-generation/pipeline/src/run_pipeline.py --dry-run --design <design>` for the design being edited. **Success here is not enough:** later stages read the maintained artifacts, not the new candidates.
3. In a disposable copy of the repository, run the pipeline without `--dry-run`, accept its promotions, and repeat until nothing changes.
4. Compare that copy's artifacts with the originals. For a prose-only edit, only line numbers and intended descriptive text may differ. The ROM images and packing report must be byte-identical.
5. For a behavior change, explain every difference and run the simulator suites on the copy.
6. The maintainer reviews and promotes in the repository.

For every edit to any document, also follow section 3.3 and check that its links and anchors resolve.
