# Repository Tools

## 1. Purpose

This directory contains software used to develop, validate, generate, analyze, and maintain project artifacts.

Tools automate repeatable repository processes. They must not replace or silently redefine the authoritative design documentation.

## 2. Authority

The design documentation under `docs/` remains authoritative for system behavior, architecture, constraints, and design decisions.

Tools may:

- consume authoritative documentation
- validate documented definitions
- transform maintained source specifications
- generate derived artifacts
- report missing or contradictory information

Tools must not:

- silently invent unspecified behavior
- silently correct contradictory definitions
- treat generated output as authoritative design input
- embed undocumented design decisions in source code
- require manual modification of generated artifacts

When a tool cannot proceed because a required definition is missing or contradictory, it must report the condition clearly.

## 3. Directory Structure

Each major toolchain resides in a dedicated subdirectory under `tools/`.

```text
tools/
├── README.md
├── rom-generation/
│   ├── README.md
│   ├── common/
│   └── ...
└── ...
```

A toolchain may contain multiple independently executable tools.

Each independently executable tool should reside in its own directory and contain the files needed to understand, test, and execute that tool.

Repository-wide conventions belong in this README. Toolchain-specific processes belong in the README at the root of the applicable toolchain.

## 4. Tool Directory Requirements

Each independently executable tool should contain:

- source code
- a README
- automated tests
- dependency or runtime metadata when required
- minimal test fixtures when required

A tool README must document:

- purpose
- scope
- prerequisites
- command-line interface
- inputs
- outputs
- exit-status behavior
- diagnostic behavior
- test procedure

Tool-specific design decisions must be documented in the owning tool directory.

## 5. Shared Components

Shared code, schemas, and definitions belong in a `common/` directory within the narrowest toolchain scope that uses them.

For example:

```text
tools/
└── rom-generation/
    ├── common/
    ├── extractor/
    └── validator/
```

A component belongs in `common/` only when more than one tool requires it.

Tool-specific behavior must remain within the owning tool. Shared abstractions must not be introduced solely in anticipation of possible future use.

Repository-wide shared components should be introduced only when multiple toolchains require the same implementation.

## 6. Source and Generated Files

Tool source, maintained project source, and generated output are separate categories.

### 6.1 Tool Source

Programs, tests, schemas, and tool documentation belong under `tools/`.

### 6.2 Maintained Project Source

Machine-readable files that represent reviewed project decisions belong in the repository area associated with the artifact they define.

These files are version-controlled inputs to the tools.

For example, maintained control-ROM specifications belong under `rom/microcode/`, as defined by the [Control ROM Generation Process](README.md).

### 6.3 Generated Output

Files produced by running tools belong under the repository-level `build/` directory unless another repository document explicitly defines a different generated-output location.

Generated files must not be stored in tool source directories.

Temporary files may be created during execution, but they must not become persistent repository inputs unless they are explicitly reviewed and reclassified as maintained source files.

## 7. Command-Line Interfaces

Each tool must provide a documented command-line interface suitable for:

- direct local execution
- automated testing
- orchestration by another repository tool
- future continuous-integration execution

A tool must not require an interactive session when all required inputs can be supplied through files or command-line arguments.

Command-line behavior must be deterministic for identical inputs.

The interface should distinguish among:

- normal output
- diagnostic output
- warnings
- fatal errors

## 8. Exit Status

Each executable tool must return a meaningful process exit status.

At minimum:

- success must return zero
- a fatal processing or validation failure must return a nonzero value

Additional nonzero values may distinguish failure categories when doing so materially improves diagnosis or automation.

A tool must not return success when its required output is incomplete or invalid.

## 9. Diagnostics

Diagnostics must identify enough context to locate and correct the underlying problem.

When available, a diagnostic should include:

- severity
- tool or processing stage
- source file
- source location
- affected definition or artifact
- violated rule
- corrective context

Warnings are appropriate only when the reported condition does not prevent reliable output.

A correctness failure must not be downgraded to a warning to allow processing to continue.

## 10. Testing

Each tool must include automated tests appropriate to its responsibility.

Testing may include:

- unit tests
- parser tests
- schema-validation tests
- known-valid cases
- deliberately invalid cases
- deterministic-output tests
- integration tests
- regression tests

Test fixtures should be limited to the smallest input needed to exercise the behavior under test.

Tests must not duplicate the complete authoritative documentation set.

A corrected defect should receive a regression test when the defect can be reproduced through the tool interface.

## 11. Reproducibility

Tools that generate artifacts must record or expose enough information to reproduce the result.

Relevant information may include:

- tool version
- source revision
- input file versions
- active configuration
- output format version
- validation result

Identical inputs and configuration must produce identical outputs.

Generated timestamps, environment-specific paths, or nondeterministic ordering must not cause otherwise identical outputs to differ unless that information is explicitly required.

## 12. Failure Policy

A tool must stop with a failing status when it cannot produce reliable output.

Fatal conditions include:

- missing required input
- malformed required input
- contradictory source definitions
- unresolved required values
- invalid generated content
- internal processing errors
- inability to write required output

A tool must not silently:

- substitute guessed values
- discard conflicting definitions
- skip required processing stages
- emit known-invalid output
- use stale generated output in place of failed generation

Partial diagnostic artifacts may be retained when they help identify the failure, but they must be clearly identified as incomplete or invalid.

## 13. Incremental Tool Development

Toolchains may be developed as a sequence of independently useful stages.

During development:

- each stage should have a defined responsibility
- each stage should have inspectable inputs and outputs
- processing boundaries should remain explicit
- intermediate results should remain available for review where useful
- orchestration should be introduced only after the individual stages are understood and stable

Premature consolidation into a single program should be avoided when separate stages improve validation, diagnosis, or maintainability.

Conversely, tools should not be divided when the proposed boundary creates no independent responsibility or useful validation point.

## 14. Automation Objective

Repository toolchains should ultimately support automated execution through a continuous-integration pipeline.

GitHub Actions is the expected automation platform, but individual tools must not depend on GitHub Actions for their core behavior.

Automation must:

- invoke the same command-line interfaces used locally
- avoid duplicating tool logic in workflow definitions
- preserve the same validation and failure behavior as local execution
- operate reproducibly from version-controlled inputs
- make appropriate generated artifacts and diagnostics available for review

Local and automated execution must produce equivalent results from identical inputs and configuration.

Automation may orchestrate tools, but it must not become a separate implementation of the underlying process.

## 15. Toolchain Documentation

Each toolchain root must contain a README defining:

- the toolchain purpose
- authoritative inputs
- maintained machine-readable inputs
- processing stages
- stage dependencies
- generated artifacts
- artifact locations
- validation boundaries
- end-to-end execution process
- current implementation status

Detailed behavior for an individual program belongs in that program's README rather than in the toolchain-level README.

The current control-ROM toolchain is documented in the [Control ROM Generation Process](./rom-generation/README.md)

## 16. Current Toolchains

### 16.1 Control ROM Generation

The control-ROM generation toolchain is located under `tools/rom-generation/`.

It is responsible for developing the automated process that consumes the documented control design and produces validated control-ROM artifacts.

Its specific processing model, source placement, validation requirements, and output placement are defined in the [Control ROM Generation Process](README.md).
