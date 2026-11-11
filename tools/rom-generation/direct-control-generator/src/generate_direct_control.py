"""Generate a candidate direct-control artifact for review.

The generator takes the direct-control extractor's definitions, compares
them with the maintained artifact, checks each definition against the
maintained control-input schema, control-word schema and micro-operation
mapping, and writes a candidate plus a report. It never modifies the
maintained artifact.

Pipeline:

1. Read the extracted definitions, the maintained artifact if present, and
   the three reference specifications.
2. Validate their structure. Any error stops here.
3. Report definitions that are new, changed, or no longer extracted.
4. Check each definition's contexts and assignments against the reference
   specifications.
5. Write the candidate (only when no errors remain) and the report.

See the tool README for the validation rules.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_EXTRACTED = Path(
    "build/simulation_outputs/rom-generation/direct-control-extractor/"
    "direct-control-definitions.json"
)
DEFAULT_MAINTAINED = Path("rom/microcode/v1/direct-control-definitions.json")
DEFAULT_INPUT_SCHEMA = Path("rom/microcode/v1/control-input-schema.json")
DEFAULT_WORD_SCHEMA = Path("rom/microcode/v1/control-word-schema.json")
DEFAULT_MAPPING = Path("rom/microcode/v1/micro-operation-mapping.json")

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/direct-control-generator"
)
DEFAULT_CANDIDATE = OUTPUT_DIRECTORY / "direct-control-definitions.candidate.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "generation-report.txt"

# ---------------------------------------------------------------------------
# Expected inputs
# ---------------------------------------------------------------------------

ARTIFACT = "direct-control-definitions"
FORMAT_VERSION = 1
EXTRACTION_STAGE = "documentation-extraction"
GENERATION_STAGE = "candidate-generation"
REQUIRED_TOP_LEVEL = (
    "format_version",
    "control_design_version",
    "artifact",
    "extraction_stage",
    "sources",
    "definitions",
    "diagnostics",
)

# Definition fields this generator reads; each must be an array of text.
CHECKED_FIELDS = (
    "applicable_context",
    "direct_assignments",
    "micro_operation_assignments",
    "control_supplied_values",
)

# Reference specifications: label in messages and expected type.
REFERENCE_TYPES = {
    "inputs": "control-input-schema",
    "word": "control-word-schema",
    "mapping": "micro-operation-mapping",
}

ENCODED = "encoded"
VALUE_USE = "value"

# Encodings with these meanings may never be assigned.
UNASSIGNABLE_MEANINGS = frozenset({"reserved", "invalid"})

# Context names that are part of the control address, not control inputs.
CONTROL_ADDRESS_CONTEXT = frozenset({"MS", "TS"})

# ---------------------------------------------------------------------------
# Definition text syntax
# ---------------------------------------------------------------------------

ASSIGNMENT_PATTERN = re.compile(
    r"^\s*([A-Z/][A-Z0-9_/]*(?:\[[^]]+\])?)\s*=\s*(.+?)\s*$"
)
CONDITION_PATTERN = re.compile(r"^\s*([A-Z/][A-Z0-9_/]*)\s*(=|!=)\s*([^\s]+)\s*$")
SELECTED_PATTERN = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s+is selected\s*$")
NUMBER_PATTERN = re.compile(r"\d+")

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
FATAL = "FATAL"

SEVERITIES = (INFO, WARNING, ERROR, FATAL)
SEVERITY_ORDER = {severity: rank for rank, severity in enumerate(SEVERITIES)}
FAILURE_SEVERITIES = frozenset({ERROR, FATAL})


@dataclass(frozen=True)
class Diagnostic:
    """One validation or generation finding."""

    severity: str
    code: str
    message: str
    definition_id: str | None = None
    field_name: str | None = None


class GenerationFailure(Exception):
    """An input could not be read; generation cannot proceed."""


def make_error(
    code: str,
    message: str,
    definition_id: str | None = None,
    field_name: str | None = None,
) -> Diagnostic:
    """Build an ERROR diagnostic."""

    return Diagnostic(ERROR, code, message, definition_id, field_name)


def has_failures(diagnostics: Sequence[Diagnostic]) -> bool:
    """Return whether any diagnostic prevents a candidate from being written."""

    return any(item.severity in FAILURE_SEVERITIES for item in diagnostics)


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.definition_id or "",
        diagnostic.field_name or "",
        diagnostic.message,
    )


# ---------------------------------------------------------------------------
# Reading inputs
# ---------------------------------------------------------------------------


def resolve_from_repo(root: Path, path: Path) -> Path:
    """Resolve a relative path from the repository root."""

    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_json(path: Path, optional: bool = False) -> dict[str, Any] | None:
    """Read a JSON object from ``path``.

    An optional file that is missing or blank yields None. Every other
    problem raises ``GenerationFailure``.
    """

    if optional and not path.exists():
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise GenerationFailure(f"Required input does not exist: {path}") from error
    except UnicodeDecodeError as error:
        raise GenerationFailure(f"Input is not valid UTF-8: {path}") from error
    except OSError as error:
        raise GenerationFailure(f"Unable to read input {path}: {error}") from error

    if optional and not text.strip():
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise GenerationFailure(
            f"Input is not valid JSON: {path}: line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(data, dict):
        raise GenerationFailure(f"Input root must be a JSON object: {path}")

    return data


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


def index_definitions(
    data: dict[str, Any], label: str, code: str
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Index an artifact's definitions by id.

    ``label`` names the artifact in messages; ``code`` is the code of every
    problem found. The index is only meaningful without diagnostics.
    """

    definitions = data.get("definitions")
    if not isinstance(definitions, list):
        return [make_error(code, f"{label} must contain a definitions array.")], {}

    diagnostics = []
    index: dict[str, dict[str, Any]] = {}

    for position, item in enumerate(definitions):
        if not isinstance(item, dict):
            diagnostics.append(
                make_error(code, f"{label} definition {position} must be an object.")
            )
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            diagnostics.append(
                make_error(
                    code, f"{label} definition {position} has no nonempty string id."
                )
            )
            continue
        if identifier in index:
            diagnostics.append(
                make_error(
                    code,
                    f"{label} contains duplicate definition id {identifier}.",
                    identifier,
                )
            )
        index[identifier] = item

    return diagnostics, index


def validate_extracted(
    data: dict[str, Any],
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the extractor output and index its definitions by id."""

    diagnostics: list[Diagnostic] = []

    missing = [key for key in REQUIRED_TOP_LEVEL if key not in data]
    if missing:
        diagnostics.append(
            make_error(
                "MISSING_TOP_LEVEL_FIELDS",
                "Extracted artifact is missing: " + ", ".join(sorted(missing)),
            )
        )
    if data.get("artifact") != ARTIFACT:
        diagnostics.append(
            make_error("UNEXPECTED_ARTIFACT_TYPE", f"Expected artifact {ARTIFACT!r}.")
        )
    if "format_version" in data and data["format_version"] != FORMAT_VERSION:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_FORMAT_VERSION",
                f"Expected format_version {FORMAT_VERSION}.",
            )
        )
    if "extraction_stage" in data and data["extraction_stage"] != EXTRACTION_STAGE:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_EXTRACTION_STAGE",
                f"Expected extraction_stage {EXTRACTION_STAGE!r}.",
            )
        )

    extractor_diagnostics = data.get("diagnostics")
    if not isinstance(extractor_diagnostics, list):
        diagnostics.append(
            make_error(
                "INVALID_EXTRACTOR_DIAGNOSTICS",
                "Extracted artifact diagnostics must be an array.",
            )
        )
    elif any(
        isinstance(item, dict) and item.get("severity") in FAILURE_SEVERITIES
        for item in extractor_diagnostics
    ):
        diagnostics.append(
            make_error(
                "EXTRACTOR_FAILURE_DIAGNOSTICS",
                "Extracted artifact contains ERROR or FATAL diagnostics.",
            )
        )

    index_diagnostics, definitions = index_definitions(
        data, "Extracted artifact", "INVALID_EXTRACTED_DEFINITIONS"
    )
    diagnostics += index_diagnostics

    for identifier, definition in definitions.items():
        for field in CHECKED_FIELDS:
            values = definition.get(field)
            if not isinstance(values, list) or not all(
                isinstance(value, str) for value in values
            ):
                diagnostics.append(
                    make_error(
                        "INVALID_DEFINITION_FIELD",
                        f"Definition {field} must be an array of strings.",
                        identifier,
                    )
                )

    return diagnostics, definitions


def validate_maintained(
    data: dict[str, Any] | None,
    extracted: dict[str, Any],
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the maintained artifact and index its definitions by id.

    A missing artifact (None) is valid and has no definitions.
    """

    if data is None:
        return [], {}

    diagnostics: list[Diagnostic] = []

    if data.get("control_design_version") != extracted.get("control_design_version"):
        diagnostics.append(
            make_error(
                "CONTROL_DESIGN_VERSION_MISMATCH",
                "Maintained and extracted artifacts have different "
                "control_design_version values.",
            )
        )

    index_diagnostics, definitions = index_definitions(
        data, "Maintained artifact", "INVALID_MAINTAINED_DEFINITIONS"
    )
    return diagnostics + index_diagnostics, definitions


def validate_references(
    extracted: dict[str, Any], references: dict[str, dict[str, Any]]
) -> list[Diagnostic]:
    """Check each reference specification's type and every design version."""

    diagnostics = [
        make_error(
            "INVALID_SPECIFICATION_TYPE",
            f"Expected {label} specification_type {expected!r}, found "
            f"{references[label].get('specification_type')!r}.",
        )
        for label, expected in REFERENCE_TYPES.items()
        if references[label].get("specification_type") != expected
    ]

    versions = {"definitions": extracted.get("control_design_version")}
    versions.update(
        {
            label: data.get("control_design_version")
            for label, data in references.items()
        }
    )
    if len(set(versions.values())) > 1:
        diagnostics.append(
            make_error(
                "CONTROL_DESIGN_VERSION_MISMATCH",
                ", ".join(
                    f"{label}={version!r}" for label, version in versions.items()
                ),
            )
        )

    return diagnostics


# ---------------------------------------------------------------------------
# Review against the maintained artifact
# ---------------------------------------------------------------------------


def review_changes(
    extracted: dict[str, dict[str, Any]],
    maintained: dict[str, dict[str, Any]],
) -> list[Diagnostic]:
    """Warn about new, changed, and stale definitions."""

    diagnostics = []

    for identifier, definition in extracted.items():
        previous = maintained.get(identifier)
        if previous is None:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "NEW_DEFINITION",
                    "Definition is not present in the maintained artifact.",
                    identifier,
                )
            )
        elif previous != definition:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "CHANGED_DEFINITION",
                    "Extracted definition differs from the maintained artifact.",
                    identifier,
                )
            )

    diagnostics.extend(
        Diagnostic(
            WARNING,
            "STALE_DEFINITION",
            "Maintained definition is absent from the extracted artifact.",
            identifier,
        )
        for identifier in maintained
        if identifier not in extracted
    )

    return diagnostics


# ---------------------------------------------------------------------------
# Semantic validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class References:
    """The reference specifications, indexed for lookup."""

    fields: dict[str, dict[str, Any]]
    inputs: dict[str, dict[str, Any]]
    mappings: dict[str, dict[str, str]]


def index_fields(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a schema's fields by name."""

    fields = schema.get("fields")
    return {
        field["name"]: field
        for field in (fields if isinstance(fields, list) else [])
        if isinstance(field, dict) and isinstance(field.get("name"), str)
    }


def index_mappings(mapping: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Index each micro-operation's assignments as ``{field: value}``."""

    mappings = mapping.get("mappings")
    result: dict[str, dict[str, str]] = {}
    for item in mappings if isinstance(mappings, list) else []:
        if not isinstance(item, dict) or not isinstance(
            item.get("micro_operation"), str
        ):
            continue
        assignments = item.get("assignments")
        result[item["micro_operation"]] = {
            assignment["field"]: str(assignment["value"])
            for assignment in (assignments if isinstance(assignments, list) else [])
            if isinstance(assignment, dict)
            and "field" in assignment
            and "value" in assignment
        }
    return result


def normalized(text: str) -> str:
    """Return ``text`` uppercased with everything but letters and digits removed."""

    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def legal_encodings(field: dict[str, Any]) -> set[str]:
    """Return the values that may be assigned to a field.

    A field with documented encodings allows those not marked reserved or
    invalid. A field without them allows every octal value its width holds.
    """

    values = field.get("values")
    if isinstance(values, list) and values:
        return {
            str(value.get("encoding"))
            for value in values
            if isinstance(value, dict)
            and str(value.get("meaning", "")).casefold() not in UNASSIGNABLE_MEANINGS
        }
    width = field.get("width")
    if isinstance(width, int) and width > 0:
        return {format(number, "o") for number in range(1 << width)}
    return set()


def resolve_symbol(field: dict[str, Any], token: str) -> str | None:
    """Return the encoding a symbolic value names, or None.

    The symbol must equal exactly one encoding's meaning, ignoring case and
    punctuation.
    """

    target = normalized(token)
    matches = {
        str(value.get("encoding"))
        for value in field.get("values", [])
        if isinstance(value, dict)
        and normalized(str(value.get("meaning", ""))) == target
    }
    return matches.pop() if len(matches) == 1 else None


def parse_assignments(
    blocks: Sequence[str], definition_id: str, kind: str
) -> tuple[list[tuple[str, str]], list[Diagnostic]]:
    """Parse ``NAME = value`` lines; report any other non-blank line."""

    assignments = []
    diagnostics = []
    for block in blocks:
        for line in block.splitlines():
            if not line.strip():
                continue
            match = ASSIGNMENT_PATTERN.match(line)
            if match is None:
                diagnostics.append(
                    make_error(
                        "MALFORMED_ASSIGNMENT",
                        f"Malformed {kind} assignment: {line}",
                        definition_id,
                    )
                )
                continue
            assignments.append((match.group(1), match.group(2)))
    return assignments, diagnostics


def resolve_constant(
    field: dict[str, Any], token: str, definition_id: str
) -> tuple[str | None, list[Diagnostic]]:
    """Resolve a numeric or symbolic value to an encoding of ``field``."""

    name = field["name"]

    if NUMBER_PATTERN.fullmatch(token):
        legal = legal_encodings(field)
        if token in legal:
            return token, []
        if field.get("values"):
            message = f"{name} value {token} is not a legal encoding."
        else:
            message = f"{name} value {token} does not fit width {field.get('width')}."
        return None, [make_error("VALUE_OUT_OF_RANGE", message, definition_id, name)]

    value = resolve_symbol(field, token)
    if value is None:
        return None, [
            make_error(
                "UNKNOWN_CONTROL_VALUE",
                f"Cannot resolve {name} value {token!r} against the control-word "
                "schema.",
                definition_id,
                name,
            )
        ]
    return value, []


def assignable_field(
    name: str, fields: dict[str, dict[str, Any]], definition_id: str, kind: str
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Return the field ``name`` if it exists and is encoded."""

    field = fields.get(name)
    if field is None:
        return None, [
            make_error(
                "UNKNOWN_CONTROL_FIELD",
                f"{kind} references unknown control field {name}.",
                definition_id,
                name,
            )
        ]
    role = field.get("control_word_role")
    if role != ENCODED:
        return None, [
            make_error(
                "NON_ENCODED_CONTROL_FIELD",
                f"{kind} assigns {name}, whose role is {role!r}.",
                definition_id,
                name,
            )
        ]
    return field, []


def resolve_assignments(
    blocks: Sequence[str],
    fields: dict[str, dict[str, Any]],
    definition_id: str,
    kind: str,
) -> tuple[dict[str, str], list[Diagnostic]]:
    """Resolve a definition's assignments of one kind to ``{field: encoding}``."""

    pairs, diagnostics = parse_assignments(blocks, definition_id, kind)
    resolved: dict[str, str] = {}

    for name, token in pairs:
        field, found = assignable_field(name, fields, definition_id, kind)
        diagnostics += found
        if field is None:
            continue
        value, found = resolve_constant(field, token, definition_id)
        diagnostics += found
        if value is None:
            continue
        previous = resolved.get(name)
        if previous is not None and previous != value:
            diagnostics.append(
                make_error(
                    "CONFLICTING_ASSIGNMENT",
                    f"{kind} assigns conflicting values {previous} and {value} to "
                    f"{name}.",
                    definition_id,
                    name,
                )
            )
        resolved[name] = value

    return resolved, diagnostics


def selected_operations(definition: dict[str, Any]) -> list[str]:
    """Return the micro-operations the applicable context selects."""

    return [
        match.group(1)
        for block in definition["applicable_context"]
        for line in block.splitlines()
        if (match := SELECTED_PATTERN.match(line))
    ]


def validate_context(
    definition: dict[str, Any], references: References
) -> list[Diagnostic]:
    """Check that the context names known inputs, fields, and micro-operations."""

    identifier = definition["id"]
    diagnostics = []

    for block in definition["applicable_context"]:
        for line in block.splitlines():
            condition = CONDITION_PATTERN.match(line)
            if condition:
                name = condition.group(1)
                if not (
                    name in references.inputs
                    or name in references.fields
                    or name in CONTROL_ADDRESS_CONTEXT
                ):
                    diagnostics.append(
                        make_error(
                            "UNKNOWN_CONTEXT_SYMBOL",
                            f"Applicable context references unknown symbol {name}.",
                            identifier,
                            name,
                        )
                    )
            selected = SELECTED_PATTERN.match(line)
            if selected and selected.group(1) not in references.mappings:
                diagnostics.append(
                    make_error(
                        "UNKNOWN_MICRO_OPERATION",
                        "Applicable context selects unknown micro-operation "
                        f"{selected.group(1)}.",
                        identifier,
                    )
                )

    return diagnostics


def validate_micro_operation_assignments(
    definition: dict[str, Any], resolved: dict[str, str], references: References
) -> list[Diagnostic]:
    """Check micro-operation assignments against the selected mappings.

    Each assigned value must be the field's default or a value one of the
    selected micro-operations assigns. Unknown micro-operations are reported
    by ``validate_context`` and ignored here.
    """

    operations = [
        name for name in selected_operations(definition) if name in references.mappings
    ]
    if not operations:
        return []

    diagnostics = []
    for name, value in resolved.items():
        if value == str(references.fields[name].get("default_value")):
            continue
        if not any(references.mappings[op].get(name) == value for op in operations):
            diagnostics.append(
                make_error(
                    "MICRO_OPERATION_ASSIGNMENT_MISMATCH",
                    f"{name}={value} is neither the field default nor supplied by "
                    f"selected micro-operation(s): {', '.join(sorted(operations))}.",
                    definition["id"],
                    name,
                )
            )
    return diagnostics


def validate_control_supplied_values(
    definition: dict[str, Any], references: References
) -> list[Diagnostic]:
    """Check each control-supplied value: a constant, or a value input."""

    identifier = definition["id"]
    kind = "control-supplied value"
    pairs, diagnostics = parse_assignments(
        definition["control_supplied_values"], identifier, kind
    )

    for name, token in pairs:
        field, found = assignable_field(name, references.fields, identifier, kind)
        diagnostics += found
        if field is None:
            continue

        source = references.inputs.get(token)
        if source is None:
            if NUMBER_PATTERN.fullmatch(token) or resolve_symbol(field, token):
                diagnostics += resolve_constant(field, token, identifier)[1]
            else:
                diagnostics.append(
                    make_error(
                        "UNKNOWN_VALUE_SOURCE",
                        f"{name} is supplied from unknown control input {token}.",
                        identifier,
                        name,
                    )
                )
            continue

        if VALUE_USE not in source.get("control_uses", []):
            diagnostics.append(
                make_error(
                    "INPUT_NOT_VALUE_CAPABLE",
                    f"Control input {token} is not declared for value use.",
                    identifier,
                    name,
                )
            )
        if source.get("width") != field.get("width"):
            diagnostics.append(
                make_error(
                    "VALUE_WIDTH_MISMATCH",
                    f"{token} width {source.get('width')} does not match {name} "
                    f"width {field.get('width')}.",
                    identifier,
                    name,
                )
            )

    return diagnostics


def validate_definition(
    definition: dict[str, Any], references: References
) -> list[Diagnostic]:
    """Check one definition against the reference specifications."""

    identifier = definition["id"]
    diagnostics = validate_context(definition, references)
    combined: dict[str, str] = {}

    for key, kind in (
        ("direct_assignments", "direct-control"),
        ("micro_operation_assignments", "micro-operation"),
    ):
        resolved, found = resolve_assignments(
            definition[key], references.fields, identifier, kind
        )
        diagnostics += found
        for name, value in resolved.items():
            prior = combined.get(name)
            if prior is not None and prior != value:
                diagnostics.append(
                    make_error(
                        "CROSS_DOMAIN_ASSIGNMENT_CONFLICT",
                        "Direct-control and micro-operation assignments conflict "
                        f"on {name}: {prior} versus {value}.",
                        identifier,
                        name,
                    )
                )
            combined[name] = value
        if key == "micro_operation_assignments":
            diagnostics += validate_micro_operation_assignments(
                definition, resolved, references
            )

    return diagnostics + validate_control_supplied_values(definition, references)


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


def build_candidate(
    extracted: dict[str, Any],
    maintained: dict[str, Any] | None,
    references: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Validate the inputs and build the candidate artifact.

    ``references`` maps ``inputs``, ``word`` and ``mapping`` to the three
    reference specifications. Returns ``(None, diagnostics)`` when any error
    is found; otherwise the candidate and its warnings.
    """

    diagnostics, definitions = validate_extracted(extracted)
    maintained_diagnostics, maintained_definitions = validate_maintained(
        maintained, extracted
    )
    diagnostics += maintained_diagnostics
    diagnostics += validate_references(extracted, references)

    if has_failures(diagnostics):
        return None, diagnostics

    diagnostics += review_changes(definitions, maintained_definitions)

    indexed = References(
        fields=index_fields(references["word"]),
        inputs=index_fields(references["inputs"]),
        mappings=index_mappings(references["mapping"]),
    )
    for definition in definitions.values():
        diagnostics += validate_definition(definition, indexed)

    if has_failures(diagnostics):
        return None, diagnostics

    candidate = {
        "format_version": extracted["format_version"],
        "control_design_version": extracted["control_design_version"],
        "artifact": ARTIFACT,
        "generation_stage": GENERATION_STAGE,
        "sources": extracted["sources"],
        "definitions": list(definitions.values()),
        "diagnostics": [],
    }
    return candidate, diagnostics


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def serialize_json(data: dict[str, Any]) -> str:
    """Serialize JSON preserving key order, with a trailing newline."""

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings, creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def remove_previous_outputs(
    outputs: Sequence[Path],
    inputs: Sequence[Path],
) -> None:
    """Delete earlier output files, so no output outlives the run.

    Raises ``ValueError``, deleting nothing, if an output path is also an
    input or is a directory.
    """

    for path in outputs:
        if path in inputs:
            raise ValueError(f"Output path is also an input: {path}")
        if path.is_dir():
            raise ValueError(f"Output path is a directory: {path}")

    for path in outputs:
        path.unlink(missing_ok=True)


def format_heading(diagnostic: Diagnostic) -> str:
    """Return ``SEVERITY CODE`` followed by any bracketed id and field."""

    text = f"{diagnostic.severity} {diagnostic.code}"
    if diagnostic.definition_id:
        text += f" [{diagnostic.definition_id}]"
    if diagnostic.field_name:
        text += f" [{diagnostic.field_name}]"
    return text


def build_report(
    diagnostics: Sequence[Diagnostic],
    definition_count: int,
    candidate_written: bool,
) -> str:
    """Build the human-readable generation report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Direct-Control Candidate Generation Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Definitions processed: {definition_count}",
        f"Candidate written: {'yes' if candidate_written else 'no'}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    lines += [f"{format_heading(item)}: {item.message}" for item in diagnostics] or [
        "No diagnostics."
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate a reviewable direct-control candidate."
    )
    parser.add_argument(
        "--repo-root", required=True, type=Path, help="Path to the repository root."
    )
    parser.add_argument(
        "--extracted",
        type=Path,
        default=DEFAULT_EXTRACTED,
        help="Direct-control extractor JSON.",
    )
    parser.add_argument(
        "--maintained",
        type=Path,
        default=DEFAULT_MAINTAINED,
        help="Maintained direct-control artifact; may be absent.",
    )
    parser.add_argument(
        "--control-input-schema",
        type=Path,
        default=DEFAULT_INPUT_SCHEMA,
        help="Maintained control-input schema.",
    )
    parser.add_argument(
        "--control-word-schema",
        type=Path,
        default=DEFAULT_WORD_SCHEMA,
        help="Maintained control-word schema.",
    )
    parser.add_argument(
        "--micro-operation-mapping",
        type=Path,
        default=DEFAULT_MAPPING,
        help="Maintained micro-operation mapping.",
    )
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=DEFAULT_CANDIDATE,
        help="Candidate artifact output path.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT,
        help="Generation report output path.",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the generator; return 1 if any error-level diagnostic exists.

    Relative paths are resolved from the repository root.
    """

    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    extracted_path = resolve_from_repo(root, options.extracted)
    maintained_path = resolve_from_repo(root, options.maintained)
    reference_paths = {
        "inputs": resolve_from_repo(root, options.control_input_schema),
        "word": resolve_from_repo(root, options.control_word_schema),
        "mapping": resolve_from_repo(root, options.micro_operation_mapping),
    }
    candidate_path = resolve_from_repo(root, options.candidate_output)
    report_path = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs(
            (candidate_path, report_path),
            (extracted_path, maintained_path, *reference_paths.values()),
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    diagnostics: list[Diagnostic] = []
    definition_count = 0
    candidate_written = False

    try:
        extracted = read_json(extracted_path)
        maintained = read_json(maintained_path, optional=True)
        references = {label: read_json(path) for label, path in reference_paths.items()}
        definitions = extracted.get("definitions")
        definition_count = len(definitions) if isinstance(definitions, list) else 0
        candidate, diagnostics = build_candidate(extracted, maintained, references)

        if candidate is not None:
            write_text(candidate_path, serialize_json(candidate))
            candidate_written = True
    except GenerationFailure as error:
        diagnostics = [Diagnostic(FATAL, "GENERATION_FAILURE", str(error))]

    diagnostics = sorted(diagnostics, key=diagnostic_sort_key)
    write_text(
        report_path, build_report(diagnostics, definition_count, candidate_written)
    )

    failures = [item for item in diagnostics if item.severity in FAILURE_SEVERITIES]
    exit_code = 1 if failures else 0

    print("Direct-control candidate generation")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Definitions: {definition_count}")
    print(f"Candidate written: {'yes' if candidate_written else 'no'}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"Candidate output: {candidate_path}")
    print(f"Report output: {report_path}")

    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            print(format_heading(item))
            print(f"  {item.message}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
