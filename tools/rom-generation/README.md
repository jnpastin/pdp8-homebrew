# Control ROM Generation

## 1. Purpose

This directory contains the tooling and process documentation used to generate the CPU control ROM.

The toolchain converts the documented control behavior into:

- normalized machine-readable specifications
- validated control words
- control-store listings
- physical ROM images
- coverage and diagnostic reports

The primary deliverables are the tooling, specifications, validation rules, and documented generation process. Generated ROM images are build artifacts.

## 2. Authority and Traceability

The design documentation under `docs/` is authoritative for:

- instruction behavior
- micro-operation definitions
- execution sequencing
- control inputs
- control outputs
- control constraints
- invalid conditions

Machine-readable specifications under this directory support generation and validation. They do not replace the authoritative design documentation.

Each generated control behavior must be traceable to:

- a documented execution rule
- a documented micro-operation
- a documented control-output definition
- a documented sequencing rule

The toolchain must not silently infer, repair, or invent behavior when the documentation or machine-readable specifications are incomplete or contradictory.

## 3. Design Assumption

The current control and micro-operation definitions may be incomplete or may require revision.

The toolchain must therefore:

- support incomplete specifications
- identify missing definitions
- identify contradictory definitions
- identify behavior that cannot be realized by the defined datapath
- permit specifications to be revised without restructuring the complete toolchain
- distinguish specification failures from software failures

A failed generation caused by an incomplete specification is a valid diagnostic result.

## 4. Directory Structure

Each independently executable stage resides in a separate tool directory.

```text
tools/
└── rom-generation/
    ├── README.md
    ├── common/
    ├── <tool-name>/
    │   ├── README.md
    │   ├── src/
    │   └── tests/
    └── ...
```

The `common/` directory contains schemas, libraries, or definitions used by more than one ROM-generation tool.

Tool-specific behavior must remain in the directory of the tool that owns it. Shared abstractions must not be introduced until more than one tool requires them.

## 5. Processing Pipeline

The intended ROM-generation pipeline is:

1. Extract candidate definitions from the authoritative documentation.
2. Normalize extracted definitions into machine-readable specifications.
3. Report missing, ambiguous, duplicate, and contradictory definitions.
4. Validate control-input and control-output definitions.
5. Map each micro-operation to the control outputs required to implement it.
6. Expand execution definitions into control cases.
7. Determine the reduced input permutations required to distinguish those cases.
8. Generate complete symbolic control words.
9. Validate each symbolic control word against the control constraints.
10. analyze control-address coverage, equivalence, and collisions
11. map logical control fields to physical ROM output bits
12. emit ROM images, listings, and validation reports

A later stage must not silently compensate for a failure detected in an earlier stage.

## 6. Machine-Readable Specifications

The generation process is expected to use machine-readable specifications for:

- control-input definitions
- control-output fields and encodings
- canonical inactive output values
- micro-operation definitions
- micro-operation-to-control-output mappings
- execution-selection rules
- sequencing rules
- architectural-operation bindings
- control-address layout
- control-word layout
- physical ROM layout

Specifications should use symbolic names rather than embedded numeric control words wherever practical.

Each maintained specification entry must include enough source information to identify the applicable authoritative document.

The exact file organization and schema formats will be established by the first tools that consume them.

## 7. Documentation Extraction

Documentation extraction minimizes manual transcription but does not make extracted data authoritative.

The extraction stage should identify candidate definitions such as:

- signal names
- field widths
- signal classes
- legal encodings
- default or inactive values
- micro-operation names
- micro-operation sources and targets
- execution timing assignments
- constraints
- source-document references

Extraction results must distinguish:

- successfully extracted values
- missing values
- ambiguous values
- conflicting values
- values requiring manual review

The extractor must not modify the authoritative documentation.

## 8. Micro-Operation Mapping

Each micro-operation must map to the complete set of control outputs required to implement it.

A mapping may include:

- register load enables
- source selections
- ALU operand selections
- ALU operation selection
- internal-bus controls
- memory-interface controls
- I/O-interface controls
- control-supplied values

The mapping stage must detect:

- micro-operations with no implementation mapping
- unsupported datapath transformations
- conflicting assignments to one control field
- multiple writers to one destination
- missing source selections
- missing architectural-operation bindings
- incompatible bus use

Execution rules must select micro-operations rather than duplicate their control-output mappings.

## 9. Control-Case Expansion

A control case is selected by a reduced control-input tuple containing only the distinctions required by documented behavior.

Conceptually:

```text
(MS, TS, IR_FIELDS, FLAGS, EXT)
    -> selected execution rules
    -> selected micro-operations
    -> sequencing results
    -> complete symbolic control word
```

The expansion stage must support multiple compatible rules applying to the same control case.

If applicable rules assign incompatible values to the same control field, generation must fail for that case.

## 10. Input Permutation Analysis

The toolchain must determine required control-input permutations from documented behavioral distinctions rather than by manually listing every possible combination.

For each candidate input tuple, the toolchain should derive a normalized symbolic control-word signature.

Input tuples that require different signatures must remain distinguishable in the control-address representation.

Input tuples that produce identical signatures may be reported as behaviorally equivalent.

The analysis must identify:

- required input distinctions
- behaviorally equivalent tuples
- unreachable tuples
- reachable but undefined tuples
- intentional aliases
- accidental control-address collisions
- control inputs that do not affect behavior

The toolchain must not assume that every defined input signal requires an independent control-address bit.

## 11. Control-Word Generation

Control-word generation must produce a complete symbolic control word for each reachable control case.

Each generated word must:

- assign every field a defined value
- use only documented legal encodings
- use canonical inactive values for unused fields
- explicitly define sequencing outputs
- contain all outputs required by the selected micro-operations
- satisfy architectural-operation binding rules
- remain independent of physical ROM device organization

Logical control-word generation must occur before physical bit packing.

## 12. Validation

The toolchain must reject any generated control word that violates the defined control constraints.

Validation must include at least:

- missing control fields
- invalid or reserved encodings
- conflicting assignments to one field
- multiple writes to one register at one TP
- incompatible register input sources
- invalid internal-bus ownership
- invalid ALU operand configuration
- simultaneous `PC_LOAD` and `PC_INC`
- simultaneous memory read and memory write
- simultaneous I/O read and I/O write
- missing memory-operation bindings
- missing I/O-operation bindings
- conflicting AC updates
- invalid pending-IOT-transfer values
- undefined `MS_NEXT`
- undefined `RUN_NEXT`
- undefined `HLT_REQ_NEXT`
- reachable control cases without defined behavior
- different required behaviors mapped to the same control address
- generated behavior without a documented source

Diagnostics should identify:

- the failing control case
- the violated rule
- the relevant specification entry
- the applicable source-document reference when available

## 13. Physical ROM Packing

Physical ROM packing is separate from logical control-word generation.

The packing stage defines:

- logical field bit positions
- physical ROM device allocation
- byte and word ordering
- unused physical output bits
- image format
- padding behavior

Changing the physical ROM organization must not require changing the logical behavior specification.

No physical ROM image may be generated from a symbolic control store that has failed validation.

## 14. Generated Artifacts

Generated artifacts may include:

- symbolic control-store listings
- packed control-store listings
- binary ROM images
- hexadecimal ROM images
- control-address maps
- control-case coverage reports
- equivalence reports
- unreachable-case reports
- validation reports
- source-traceability reports

ROM images belong under:

```text
build/rom_images/
```

Simulation and analysis outputs belong under:

```text
build/simulation_outputs/
```

Generated artifacts must not be edited manually.

## 15. Reproducibility

A complete generation run must be reproducible from:

- the authoritative documentation revision
- the machine-readable specifications
- the ROM-generation tool source
- the physical ROM layout definition

Generated reports should record:

- source revision when available
- tool version
- specification version
- logical control-word width
- control-address width
- physical ROM layout
- validation result

Identical source inputs must produce identical generated outputs.

## 16. Change Process

When documented control behavior or micro-operation logic changes:

1. Update the authoritative documentation.
2. Update or regenerate the affected machine-readable specifications.
3. Review extraction and consistency diagnostics.
4. Validate the specifications.
5. Regenerate the symbolic control store.
6. Review changed control cases and coverage.
7. Validate control-address distinctions.
8. Regenerate physical ROM images.
9. Run applicable regression and simulation tests.

A changed ROM image without a corresponding documented or machine-readable source change indicates a process failure.

## 17. Automated Generation Objective

The final ROM-generation solution will provide an automated and reproducible pipeline that:

1. Consumes the authoritative design documentation under `docs/`.
2. Extracts and validates the required control definitions.
3. Produces normalized machine-readable specifications where required.
4. Expands the documented execution behavior into control cases.
5. Determines the control-input permutations required to distinguish those cases.
6. Generates and validates complete symbolic control words.
7. Packs the validated control words into the configured physical ROM layout.
8. Emits ROM images, control-store listings, coverage reports, and diagnostic reports.

The complete process must be executable without manually constructing or editing individual control words.

Development will proceed incrementally. Each tool and processing stage will be developed, reviewed, and validated independently before it is incorporated into the end-to-end pipeline.

Once the process is stable, repository automation may invoke the same locally executable tools to rebuild and validate the control ROM after relevant changes. GitHub Actions is the expected automation platform, but the automation mechanism is not yet fixed.

Repository automation must:

- use the documented command-line interfaces
- execute the same tools available for local use
- avoid implementing generation logic that exists only in the automation workflow
- fail when required specifications are missing, contradictory, or invalid
- publish or retain the appropriate diagnostic and generated artifacts
- produce the same results as local execution when given identical inputs

The local toolchain remains the authoritative implementation of the generation process. Automation is an execution mechanism for that toolchain, not a separate ROM-generation implementation.

## 18. Source and Build Artifact Placement

ROM-generation files are divided into three categories:

1. Tool source
2. Maintained microcode source
3. Generated output

### 18.1 Tool Source

`tools/rom-generation/` contains the software and supporting files used to perform ROM generation.

This includes:

- executable tool source
- shared software libraries
- shared schemas used by multiple tools
- automated tests
- test fixtures
- tool-specific documentation
- pipeline orchestration code

Tool directories must not contain authoritative control specifications or final generated ROM images.

A persistent `tools/rom-generation/build/` directory is not part of the repository organization.

Tools may create temporary working directories during execution. Temporary files must either be removed when processing completes or be written to an explicitly designated repository-level build directory when they are intended for review.

### 18.2 Maintained Microcode Source

`rom/microcode/` contains version-controlled, machine-readable source files that are intentionally maintained and reviewed as part of the control-ROM design.

These files may include:

- reviewed control specifications
- reviewed micro-operation mappings
- execution-selection rules
- sequencing rules
- architectural-operation bindings
- control-address definitions
- logical control-word layouts
- physical ROM layouts
- version-specific generation configuration
- manually reviewed exceptions to documentation extraction

A file belongs under `rom/microcode/` when all of the following are true:

- it is intentionally maintained in version control
- it represents a design or generation decision
- it is reviewed when control behavior changes
- it is required to reproduce the ROM images
- it is an input to the generation process rather than an output from that process

Files under `rom/microcode/` must not be generated intermediates unless the repository explicitly identifies them as reviewed and maintained source files.

Version-specific source files should reside under the applicable version directory, such as:

```text
rom/
└── microcode/
    └── v1/
        ├── control-specification.yaml
        ├── micro-operation-mapping.yaml
        ├── control-address-layout.yaml
        ├── control-word-layout.yaml
        └── rom-layout.yaml
```

The exact filenames and formats will be established as the applicable tools are developed.

### 18.3 Generated Output

Generated files belong under the repository-level `build/` directory.

Final ROM programming images belong under:

```text
build/
└── rom_images/
```

Diagnostic, intermediate, and analytical outputs belong under:

```text
build/
└── simulation_outputs/
```

A more specific repository-level directory may be introduced later if the quantity or types of ROM-generation reports justify it. Until then, generated ROM images and supporting analysis must use the existing repository-level build structure.

Generated outputs may include:

- extracted candidate definitions
- normalized intermediate representations
- exception reports
- validation reports
- symbolic control-store listings
- packed control-store listings
- control-address maps
- coverage reports
- equivalence reports
- unreachable-case reports
- binary ROM images
- hexadecimal ROM images
- source-traceability reports

Generated outputs:

- are derived from maintained source files
- must not be edited manually
- must not become authoritative merely because they were generated
- may be deleted and reproduced
- must not be required as input when the same information can be reproduced from maintained source files

### 18.4 Placement Decision

Use the following rule when deciding where a file belongs:

- If the file implements the generation process, place it under `tools/rom-generation/`.
- If the file is a maintained design or generation input, place it under `rom/microcode/`.
- If the file is produced by running the toolchain, place it under `build/`.

In summary:

```text
tools/rom-generation/
    Programs, shared software, tests, schemas, and process documentation

rom/microcode/
    Maintained and reviewed inputs required to reproduce the ROM

build/
    Generated intermediates, reports, listings, and ROM images
```

No file should be copied between these locations solely for convenience. Each file must have one defined role and one authoritative location.

## 19. Current Status

The ROM-generation directory structure has been established.

Current contents:

```text
tools/
└── rom-generation/
    ├── README.md
    └── common/
```

No control-address layout, control-word bit layout, shared schema, implementation language, or physical ROM format is fixed by this README.

The first planned tool is a documentation extractor that produces candidate structured definitions and an exception report without modifying the source documentation.