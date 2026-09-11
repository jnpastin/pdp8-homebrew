# Control Microcode Version 1

## 1. Purpose

This directory contains the reviewed, version-controlled machine-readable specifications used to generate and validate version 1 CPU control behavior.

These specifications translate documented control behavior into maintained inputs suitable for automated processing. They do not replace the authoritative architecture and control documentation.

The initial scope is limited to:

- defining the symbolic control-word schema
- mapping documented micro-operations to symbolic control assignments
- generating and validating symbolic control words

Control-input mapping and logical control-address packing will be added after symbolic control-word generation has been validated.

Physical ROM packing and ROM image generation are outside the current scope.

## 2. Authority

The documentation under `docs/` is the authoritative source for:

- architecture
- micro-operations
- execution behavior
- timing behavior
- control inputs
- control outputs
- control constraints
- sequencing requirements

Files in this directory are maintained generation specifications derived from documented design decisions.

A specification in this directory must not introduce behavior that is absent from the authoritative documentation.

If a maintained specification conflicts with the documentation, the documentation governs. The documentation must be corrected first when the documented design itself is incomplete or incorrect.

## 3. Maintained Specifications

The initial maintained specifications are:

- `control-word-schema.json`
- `micro-operation-mapping.json`

### 3.1 Control-Word Schema

`control-word-schema.json` defines:

- every symbolic control field
- every legal field value
- the canonical inactive value for each field
- field requirements and constraints
- source references to the applicable documentation

It defines the logical control-word structure only.

It must not define:

- physical bit positions
- ROM-device allocation
- byte ordering
- image format
- control-address packing

### 3.2 Micro-Operation Mapping

`micro-operation-mapping.json` maps each documented micro-operation to the symbolic control-field assignments required to implement it.

Each mapping must:

- reference a documented micro-operation
- use only fields and values defined by `control-word-schema.json`
- preserve source references
- identify all required control assignments
- avoid encoding execution-selection conditions

Conditions select micro-operations and do not belong in the micro-operation mapping.

## 4. Generated Extractor Artifacts

Control-input and control-output extractor artifacts are generated under:

`build/simulation_outputs/rom-generation/`

Generated extractor artifacts:

- are derived from the authoritative documentation
- provide normalized source material for review and validation
- retain source traceability
- may be deleted and regenerated
- must not be edited manually
- must not be treated as maintained control specifications
- must not become authoritative merely because they were generated

The maintained specifications in this directory may be validated against generated extractor artifacts, but they must not depend on generated files that cannot be reproduced from the repository sources.

## 5. Specification Change Process

When documented control behavior changes:

1. Update the authoritative documentation.
2. Regenerate the affected extractor artifacts.
3. Review extractor diagnostics.
4. Update the affected maintained specification.
5. Validate the maintained specification against the extracted definitions.
6. Regenerate symbolic control behavior.
7. Review changed control words and validation results.
8. Run the applicable automated tests.

A maintained specification change without corresponding documented support is invalid.

A generated control-word change without a corresponding documentation or maintained-specification change indicates a process failure.

## 6. Source Traceability

Every maintained entry must retain enough source information to identify the documentation from which it was derived.

Source references must identify:

- repository-relative document path
- applicable section or definition
- source line when available

Generated diagnostics must report the applicable maintained entry and its source reference.

Repository-relative source paths must be used so that specifications remain portable across working directories.

## 7. Validation Requirements

The maintained specifications must be validated before they are used for symbolic control-word generation.

Validation must detect at least:

- references to undefined control fields
- references to undefined field values
- missing canonical inactive values
- duplicate field or micro-operation definitions
- mappings for undocumented micro-operations
- documented micro-operations without mappings
- conflicting assignments within one mapping
- missing source references
- malformed specification versions
- unsupported specification structures

Validation failure must prevent symbolic control-word generation.

## 8. Versioning

Each maintained specification must declare:

- specification type
- schema version
- control-design version

The directory name identifies the control-design version represented by the contained specifications.

Schema versions describe the machine-readable file formats and may change independently of the control-design version.

Tools must reject unsupported schema versions rather than silently interpreting them.

## 9. Generated Outputs

Symbolic control-word listings, validation reports, coverage reports, and other derived artifacts belong under the repository-level `build/` directory.

Generated outputs:

- must not be edited manually
- must not be committed as maintained specifications
- may be deleted and regenerated
- must be reproducible from documentation, maintained specifications, and tool source
- must retain source traceability where applicable

## 10. Scope Boundaries

This directory will eventually contain additional maintained specifications for:

- execution-selection rules
- sequencing rules
- logical control-address layout
- physical ROM layout

Those specifications must be introduced only when their corresponding generation stages are implemented.

The current work must not determine control-address packing before symbolic control behavior and control-input distinctions have been validated.

The current work must not generate binary or hexadecimal ROM images.
