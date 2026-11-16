# Control Microcode Version 1

## 1. Purpose

This directory contains the reviewed, version-controlled machine-readable specifications used to generate and validate version 1 CPU control behavior.

These specifications translate documented control behavior into maintained inputs suitable for automated processing. They do not replace the authoritative architecture and control documentation.

The current scope covers:

- the control-input and control-word schemas
- mapping documented micro-operations to symbolic control assignments
- direct-control definitions, execution definitions, and timing constraints
- generating and validating symbolic control words

Logical control-store packing is performed by the control-store packer from these specifications ([Control Store Organization](../../../docs/04-control/08-control-store-organization.md)). Its packing and logical images are build outputs and are not maintained here.

Physical ROM image formats are outside the current scope.

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

The maintained specifications are:

| File | Contents |
|---|---|
| `control-input-schema.json` | control inputs, their domains, IR derivations, and input constraints |
| `control-word-schema.json` | control fields, legal values, inactive values, and Value Required When conditions (section 3.1) |
| `micro-operation-mapping.json` | control assignments for each micro-operation (section 3.2) |
| `direct-control-definitions.json` | direct control assignments, such as next major state and run control, in each context |
| `execution-definitions.json` | the micro-operations selected in each execution case and timing state |
| `timing-constraints.json` | timing constraints and state invariants on input combinations |
| `symbolic-control-words.json` | the complete symbolic control word of every execution case |

Each is a promoted generator output, reviewed before it replaces the previous version. The tools that produce them are listed in the [ROM-generation README](../../../tools/rom-generation/README.md#19-current-status).

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

A physical ROM layout specification must be introduced only when its generation stage is implemented.

Logical device images are written to `build/` for verification only. Physical ROM images, the files used to program devices, must not be generated until their format is defined and the logical images have been validated against the datapath.
