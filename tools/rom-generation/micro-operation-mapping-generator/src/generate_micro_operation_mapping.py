"""Generate a candidate micro-operation mapping for review.

Each micro-operation's control-field assignments come from the control-word
schema: a field whose ``used_by_micro_operations`` names the micro-operation
is assigned the value given there. When that entry gives no value, the
value reviewed in the maintained mapping is used. The candidate is written
for review; the maintained mapping is never modified.

Pipeline:

1. Read the micro-operation catalog, the control-word schema, and, if
   present, the maintained mapping.
2. Validate all three structurally. Any error stops candidate construction.
3. Check that every Used-by entry names a cataloged micro-operation.
4. Build one mapping per micro-operation, checking each assignment's field
   role and value.
5. Report unresolved and stale mappings.
6. Write the candidate (only when no errors remain) and the report.

See the tool README for the mapping contract.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_MICRO_OPERATIONS = Path(
    "build/simulation_outputs/rom-generation/micro-operation-extractor/"
    "micro-operations.json"
)
DEFAULT_CONTROL_WORD_SCHEMA = Path("rom/microcode/v1/control-word-schema.json")
DEFAULT_MAINTAINED_MAPPING = Path("rom/microcode/v1/micro-operation-mapping.json")

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/micro-operation-mapping-generator"
)
DEFAULT_CANDIDATE_OUTPUT = OUTPUT_DIRECTORY / "micro-operation-mapping.candidate.json"
DEFAULT_REPORT_OUTPUT = OUTPUT_DIRECTORY / "generation-report.txt"

# ---------------------------------------------------------------------------
# Expected inputs
# ---------------------------------------------------------------------------

MICRO_OPERATION_FORMAT_VERSION = 1
MICRO_OPERATION_STAGE = "definition-validation"
MICRO_OPERATION_STATUS = "definition-validated"
REQUIRED_MICRO_OPERATION_PROPERTIES = (
    "category",
    "description",
    "targets",
    "expression",
    "sources",
    "preconditions",
    "constraints",
    "source",
)

SCHEMA_TYPE = "control-word-schema"
SCHEMA_VERSION = 1
ENCODED = "encoded"
CONTROL_WORD_ROLES = frozenset({ENCODED, "derived", "external_input"})
EXPLICIT_VALUE_REQUIRED_VALUES = frozenset({"Yes", "No", "Conditionally"})

# Encodings with these meanings may never be assigned.
UNASSIGNABLE_MEANINGS = frozenset({"reserved", "invalid"})

# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------

MAPPING_TYPE = "micro-operation-mapping"
MAPPING_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"
MAPPING_DESCRIPTION = (
    "Maps documented micro-operations to symbolic control-field assignments."
)

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
    micro_operation: str | None = None
    field_name: str | None = None
    source_path: str | None = None
    source_line: int | None = None


class GenerationFailure(Exception):
    """An input could not be read; generation cannot proceed."""


def make_diagnostic(
    severity: str,
    code: str,
    message: str,
    *,
    micro_operation: str | None = None,
    field_name: str | None = None,
    source: Any = None,
) -> Diagnostic:
    """Build a diagnostic, taking its location from an extractor source.

    ``source`` is a ``{"path": ..., "line": ...}`` object. Parts of it with
    the wrong type, and any non-object value, are left out.
    """

    if not isinstance(source, dict):
        source = {}
    path = source.get("path")
    line = source.get("line")

    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        micro_operation=micro_operation,
        field_name=field_name,
        source_path=path if isinstance(path, str) else None,
        source_line=line if isinstance(line, int) else None,
    )


def make_error(code: str, message: str, **location: Any) -> Diagnostic:
    """Build an ERROR diagnostic."""

    return make_diagnostic(ERROR, code, message, **location)


def has_failures(diagnostics: Sequence[Diagnostic]) -> bool:
    """Return whether any diagnostic prevents a candidate from being written."""

    return any(item.severity in FAILURE_SEVERITIES for item in diagnostics)


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.source_path or "",
        diagnostic.source_line if diagnostic.source_line is not None else -1,
        diagnostic.micro_operation or "",
        diagnostic.field_name or "",
        diagnostic.message,
    )


def diagnostic_to_dict(diagnostic: Diagnostic) -> dict[str, Any]:
    """Return the JSON form of a diagnostic, omitting empty fields."""

    result: dict[str, Any] = {
        "severity": diagnostic.severity,
        "code": diagnostic.code,
        "message": diagnostic.message,
    }
    optional = {
        "micro_operation": diagnostic.micro_operation,
        "field_name": diagnostic.field_name,
        "source_path": diagnostic.source_path,
        "source_line": diagnostic.source_line,
    }
    result.update({key: value for key, value in optional.items() if value is not None})
    return result


def is_text(value: Any) -> bool:
    """Return whether ``value`` is a non-empty string."""

    return isinstance(value, str) and bool(value)


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
            f"Input is not valid JSON: {path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(data, dict):
        raise GenerationFailure(f"Input must contain a top-level JSON object: {path}")

    return data


# ---------------------------------------------------------------------------
# Micro-operation catalog validation
# ---------------------------------------------------------------------------


def validate_micro_operations(data: dict[str, Any]) -> list[Diagnostic]:
    """Validate the micro-operation extractor output."""

    diagnostics: list[Diagnostic] = []

    if data.get("format_version") != MICRO_OPERATION_FORMAT_VERSION:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_MICRO_OPERATION_FORMAT",
                "Expected micro-operation format_version 1.",
            )
        )
    if data.get("extraction_stage") != MICRO_OPERATION_STAGE:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_EXTRACTION_STAGE",
                f"Expected extraction_stage {MICRO_OPERATION_STAGE!r}.",
            )
        )
    if data.get("diagnostics") != []:
        diagnostics.append(
            make_error(
                "EXTRACTOR_DIAGNOSTICS_PRESENT",
                "Micro-operation input contains diagnostics.",
            )
        )

    operations = data.get("micro_operations")
    if not isinstance(operations, list):
        diagnostics.append(
            make_error("INVALID_MICRO_OPERATIONS", "micro_operations must be an array.")
        )
        return diagnostics

    seen_names: set[str] = set()
    for operation in operations:
        diagnostics += validate_micro_operation(operation, seen_names)

    return diagnostics


def validate_micro_operation(operation: Any, seen_names: set[str]) -> list[Diagnostic]:
    """Validate one micro-operation; record its name in ``seen_names``."""

    if not isinstance(operation, dict):
        return [
            make_error(
                "INVALID_MICRO_OPERATION", "Micro-operation entry must be an object."
            )
        ]

    name = operation.get("name")
    source = operation.get("source")

    if not is_text(name):
        return [
            make_error(
                "INVALID_MICRO_OPERATION_NAME",
                "Micro-operation name must be non-empty.",
                source=source,
            )
        ]

    diagnostics: list[Diagnostic] = []

    def report(code: str, message: str, location: Any = source) -> None:
        diagnostics.append(
            make_error(code, message, micro_operation=name, source=location)
        )

    if name in seen_names:
        report(
            "DUPLICATE_MICRO_OPERATION",
            f"Micro-operation {name!r} appears more than once.",
        )
    seen_names.add(name)

    if operation.get("extraction_status") != MICRO_OPERATION_STATUS:
        report(
            "INVALID_EXTRACTION_STATUS", "Micro-operation is not definition-validated."
        )

    for key in REQUIRED_MICRO_OPERATION_PROPERTIES:
        if key not in operation:
            report(
                "MISSING_MICRO_OPERATION_PROPERTY", f"Micro-operation lacks {key!r}."
            )

    if not (
        isinstance(source, dict)
        and isinstance(source.get("path"), str)
        and isinstance(source.get("heading"), str)
        and isinstance(source.get("line"), int)
    ):
        report(
            "INVALID_MICRO_OPERATION_SOURCE", "Micro-operation source is invalid.", None
        )

    return diagnostics


# ---------------------------------------------------------------------------
# Control-word schema validation
# ---------------------------------------------------------------------------


def validate_schema(
    data: dict[str, Any],
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the control-word schema and index its fields by name.

    The returned fields are only meaningful when no diagnostics are returned.
    """

    diagnostics: list[Diagnostic] = []

    if data.get("specification_type") != SCHEMA_TYPE:
        diagnostics.append(
            make_error(
                "INVALID_CONTROL_SCHEMA_TYPE", "Expected control-word-schema input."
            )
        )
    if data.get("schema_version") != SCHEMA_VERSION:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_CONTROL_SCHEMA_VERSION",
                "Expected control schema version 1.",
            )
        )
    if data.get("control_design_version") != CONTROL_DESIGN_VERSION:
        diagnostics.append(
            make_error(
                "CONTROL_DESIGN_VERSION_MISMATCH", "Control design version must be v1."
            )
        )

    fields = data.get("fields")
    if not isinstance(fields, list):
        diagnostics.append(
            make_error("INVALID_CONTROL_FIELDS", "fields must be an array.")
        )
        return diagnostics, {}

    fields_by_name: dict[str, dict[str, Any]] = {}

    for field in fields:
        if not isinstance(field, dict):
            diagnostics.append(
                make_error("INVALID_CONTROL_FIELD", "Control field must be an object.")
            )
            continue

        name = field.get("name")
        if not is_text(name):
            diagnostics.append(
                make_error(
                    "INVALID_CONTROL_FIELD_NAME",
                    "Control field name must be non-empty.",
                )
            )
            continue

        if name in fields_by_name:
            diagnostics.append(
                make_error(
                    "DUPLICATE_CONTROL_FIELD",
                    f"Control field {name!r} appears more than once.",
                    field_name=name,
                )
            )
        fields_by_name[name] = field
        diagnostics += validate_schema_field(field, name)

    return diagnostics, fields_by_name


def validate_schema_field(field: dict[str, Any], name: str) -> list[Diagnostic]:
    """Validate the properties of one control field that mapping relies on."""

    diagnostics: list[Diagnostic] = []

    def report(code: str, message: str, source: Any = None) -> None:
        diagnostics.append(make_error(code, message, field_name=name, source=source))

    if field.get("control_word_role") not in CONTROL_WORD_ROLES:
        report("INVALID_CONTROL_WORD_ROLE", "Control field has invalid role.")
    if field.get("explicit_value_required") not in EXPLICIT_VALUE_REQUIRED_VALUES:
        report(
            "INVALID_EXPLICIT_VALUE_REQUIREMENT",
            "Control field has invalid explicit-value requirement.",
        )
    if not isinstance(field.get("value_required_when"), str):
        report(
            "INVALID_VALUE_REQUIRED_WHEN",
            "Control field lacks a valid value-required condition.",
        )

    uses = field.get("used_by_micro_operations")
    if not isinstance(uses, list):
        report(
            "INVALID_USED_BY_MICRO_OPERATIONS",
            "used_by_micro_operations must be an array.",
        )
        return diagnostics

    seen_operations: set[str] = set()
    for use in uses:
        if not isinstance(use, dict) or not is_text(use.get("micro_operation")):
            report(
                "INVALID_USED_BY_MICRO_OPERATION",
                "Used-by entry must name a micro-operation.",
            )
            continue
        operation = use["micro_operation"]
        if operation in seen_operations:
            report(
                "DUPLICATE_USED_BY_MICRO_OPERATION",
                f"Micro-operation {operation!r} is listed more than once.",
                use.get("source"),
            )
        seen_operations.add(operation)
        if "value" in use and not is_text(use["value"]):
            report(
                "INVALID_USED_BY_VALUE",
                "Used-by value must be a non-empty string when present.",
                use.get("source"),
            )

    return diagnostics


# ---------------------------------------------------------------------------
# Maintained mapping validation
# ---------------------------------------------------------------------------


def validate_maintained(
    data: dict[str, Any] | None,
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the maintained mapping and index its mappings by name.

    A missing mapping (None) is valid and has no entries. The returned
    mappings are only meaningful when no diagnostics are returned.
    """

    if data is None:
        return [], {}

    diagnostics: list[Diagnostic] = []

    if data.get("specification_type") != MAPPING_TYPE:
        diagnostics.append(
            make_error(
                "INVALID_MAPPING_TYPE", "Expected micro-operation-mapping input."
            )
        )
    if data.get("schema_version") != MAPPING_VERSION:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_MAPPING_VERSION", "Expected mapping schema version 1."
            )
        )
    if data.get("control_design_version") != CONTROL_DESIGN_VERSION:
        diagnostics.append(
            make_error(
                "MAPPING_DESIGN_VERSION_MISMATCH",
                "Mapping control design version must be v1.",
            )
        )

    mappings = data.get("mappings")
    if not isinstance(mappings, list):
        diagnostics.append(make_error("INVALID_MAPPINGS", "mappings must be an array."))
        return diagnostics, {}

    mappings_by_name: dict[str, dict[str, Any]] = {}

    for mapping in mappings:
        if not isinstance(mapping, dict):
            diagnostics.append(
                make_error("INVALID_MAPPING", "Mapping must be an object.")
            )
            continue

        name = mapping.get("micro_operation")
        if not is_text(name):
            diagnostics.append(
                make_error(
                    "INVALID_MAPPING_NAME", "Mapping micro_operation must be non-empty."
                )
            )
            continue

        def report(code: str, message: str, name: str = name) -> None:
            diagnostics.append(make_error(code, message, micro_operation=name))

        if name in mappings_by_name:
            report("DUPLICATE_MAPPING", f"Mapping {name!r} appears more than once.")
        mappings_by_name[name] = mapping

        assignments = mapping.get("assignments")
        if not isinstance(assignments, list):
            report("INVALID_ASSIGNMENTS", "assignments must be an array.")
        elif not all(
            isinstance(item, dict)
            and is_text(item.get("field"))
            and is_text(item.get("value"))
            for item in assignments
        ):
            report(
                "INVALID_MAINTAINED_ASSIGNMENT",
                "Each assignment must have a non-empty string field and value.",
            )

        if not isinstance(mapping.get("notes"), list):
            report("INVALID_NOTES", "notes must be an array.")

    return diagnostics, mappings_by_name


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


def legal_encodings(field: dict[str, Any]) -> set[str] | None:
    """Return the values that may be assigned to a field.

    A field with documented encodings allows those not marked reserved or
    invalid. A field without them allows every octal value its width can
    hold. None means the field cannot be checked.
    """

    values = field.get("values")
    if isinstance(values, list) and values:
        return {
            value["encoding"]
            for value in values
            if isinstance(value, dict)
            and isinstance(value.get("encoding"), str)
            and str(value.get("meaning", "")).casefold() not in UNASSIGNABLE_MEANINGS
        }

    width = field.get("width")
    if isinstance(width, int) and width > 0:
        return {format(number, "o") for number in range(1 << width)}

    return None


def collect_uses(
    fields: dict[str, dict[str, Any]],
) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    """Index Used-by entries by micro-operation, in schema field order."""

    uses: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for field_name, field in fields.items():
        for use in field["used_by_micro_operations"]:
            uses.setdefault(use["micro_operation"], []).append((field_name, use))
    return uses


def find_undefined_uses(
    uses: dict[str, list[tuple[str, dict[str, Any]]]],
    operation_names: set[str],
) -> list[Diagnostic]:
    """Report Used-by entries naming a micro-operation not in the catalog."""

    return [
        make_error(
            "UNDEFINED_USED_BY_MICRO_OPERATION",
            f"Used-by entry names micro-operation {operation!r}, which is not "
            "in the micro-operation catalog.",
            micro_operation=operation,
            field_name=field_name,
            source=use.get("source"),
        )
        for operation, entries in uses.items()
        if operation not in operation_names
        for field_name, use in entries
    ]


def derive_assignments(
    name: str,
    uses: list[tuple[str, dict[str, Any]]],
    fields: dict[str, dict[str, Any]],
    maintained: dict[str, Any] | None,
    source: dict[str, Any],
) -> tuple[list[dict[str, str]], list[Diagnostic]]:
    """Build one micro-operation's assignments from its Used-by entries.

    A Used-by entry without a value takes the maintained mapping's value for
    that field. Each assignment's field must be encoded and its value legal.
    """

    reviewed = {
        item["field"]: item["value"]
        for item in (maintained or {}).get("assignments", [])
    }
    assignments: list[dict[str, str]] = []
    diagnostics: list[Diagnostic] = []

    for field_name, use in uses:
        value = use.get("value", reviewed.get(field_name))
        if value is None:
            diagnostics.append(
                make_error(
                    "MAPPING_VALUE_UNRESOLVED",
                    "Used-by relationship has no assignment value and no "
                    "reviewed value exists.",
                    micro_operation=name,
                    field_name=field_name,
                    source=use.get("source"),
                )
            )
            continue

        assignments.append({"field": field_name, "value": value})

        field = fields[field_name]
        role = field.get("control_word_role")
        if role != ENCODED:
            diagnostics.append(
                make_error(
                    "NON_ENCODED_ASSIGNMENT",
                    f"Field {field_name!r} has role {role!r} and cannot be assigned.",
                    micro_operation=name,
                    field_name=field_name,
                    source=source,
                )
            )
            continue

        legal = legal_encodings(field)
        if legal is not None and value not in legal:
            diagnostics.append(
                make_error(
                    "INVALID_ASSIGNED_VALUE",
                    f"Value {value!r} is not legal for field {field_name!r}.",
                    micro_operation=name,
                    field_name=field_name,
                    source=source,
                )
            )

    return assignments, diagnostics


def compare_with_maintained(
    name: str,
    assignments: list[dict[str, str]],
    maintained: dict[str, Any] | None,
    source: dict[str, Any],
) -> list[Diagnostic]:
    """Warn about every difference between the candidate and maintained mapping.

    Promoting the candidate would apply these changes, so they are listed
    for review: removed and changed assignments in maintained order, then
    added assignments in candidate order. A micro-operation without a
    maintained mapping has nothing to compare.
    """

    if maintained is None:
        return []

    old = {item["field"]: item["value"] for item in maintained["assignments"]}
    new = {item["field"]: item["value"] for item in assignments}
    diagnostics = []

    def warn(code: str, field_name: str, message: str) -> None:
        diagnostics.append(
            make_diagnostic(
                WARNING,
                code,
                message,
                micro_operation=name,
                field_name=field_name,
                source=source,
            )
        )

    for field_name, old_value in old.items():
        new_value = new.get(field_name)
        if new_value is None:
            warn(
                "MAINTAINED_ASSIGNMENT_REMOVED",
                field_name,
                f"Maintained assignment {field_name}={old_value!r} is no longer "
                "produced by the Used-by lists.",
            )
        elif new_value != old_value:
            warn(
                "MAINTAINED_ASSIGNMENT_CHANGED",
                field_name,
                f"Assignment {field_name} changes from {old_value!r} to {new_value!r}.",
            )

    for field_name, new_value in new.items():
        if field_name not in old:
            warn(
                "MAINTAINED_ASSIGNMENT_ADDED",
                field_name,
                f"Assignment {field_name}={new_value!r} is not in the maintained "
                "mapping.",
            )

    return diagnostics


def build_candidate(
    micro_operations: dict[str, Any],
    schema: dict[str, Any],
    maintained: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Validate the inputs and build the candidate mapping.

    Returns ``(None, diagnostics)`` when any error is found. Otherwise
    returns the candidate, whose ``diagnostics`` lists its warnings in the
    order they were found.
    """

    diagnostics = validate_micro_operations(micro_operations)
    schema_diagnostics, fields = validate_schema(schema)
    maintained_diagnostics, maintained_mappings = validate_maintained(maintained)
    diagnostics += schema_diagnostics + maintained_diagnostics

    if has_failures(diagnostics):
        return None, diagnostics

    operations = micro_operations["micro_operations"]
    operation_names = {operation["name"] for operation in operations}
    uses = collect_uses(fields)
    diagnostics += find_undefined_uses(uses, operation_names)
    mappings = []

    for operation in operations:
        name = operation["name"]
        source = operation["source"]
        maintained_mapping = maintained_mappings.get(name)

        assignments, assignment_diagnostics = derive_assignments(
            name, uses.get(name, []), fields, maintained_mapping, source
        )
        diagnostics += assignment_diagnostics
        diagnostics += compare_with_maintained(
            name, assignments, maintained_mapping, source
        )

        if not assignments:
            diagnostics.append(
                make_diagnostic(
                    WARNING,
                    "MAPPING_UNRESOLVED",
                    "No assignments were derived from control-output Used-by "
                    "relationships.",
                    micro_operation=name,
                    source=source,
                )
            )

        mappings.append(
            {
                "micro_operation": name,
                "assignments": assignments,
                "source": {
                    "document": source["path"],
                    "section": source["heading"],
                    "line": source["line"],
                },
                "notes": list(maintained_mapping["notes"])
                if maintained_mapping
                else [],
            }
        )

    diagnostics.extend(
        make_diagnostic(
            WARNING,
            "STALE_MAINTAINED_MAPPING",
            "Maintained mapping is absent from the extracted catalog.",
            micro_operation=name,
        )
        for name in maintained_mappings
        if name not in operation_names
    )

    if has_failures(diagnostics):
        return None, diagnostics

    candidate = {
        "specification_type": MAPPING_TYPE,
        "schema_version": MAPPING_VERSION,
        "control_design_version": CONTROL_DESIGN_VERSION,
        "description": MAPPING_DESCRIPTION,
        "sources": {
            "micro_operations": DEFAULT_MICRO_OPERATIONS.as_posix(),
            "control_word_schema": DEFAULT_CONTROL_WORD_SCHEMA.as_posix(),
        },
        "mappings": mappings,
        "diagnostics": [diagnostic_to_dict(item) for item in diagnostics],
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


def format_names(diagnostic: Diagnostic) -> str:
    """Return the bracketed micro-operation and field names of a diagnostic."""

    names = f"[{diagnostic.micro_operation or '-'}]"
    if diagnostic.field_name:
        names += f" [{diagnostic.field_name}]"
    return names


def build_report(
    diagnostics: Sequence[Diagnostic],
    mapping_count: int,
    candidate_written: bool,
) -> str:
    """Build the human-readable generation report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Micro-Operation Mapping Generation Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Mappings processed: {mapping_count}",
        f"Candidate written: {'yes' if candidate_written else 'no'}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    lines += [
        f"{item.severity} {item.code} {format_names(item)}: {item.message}"
        for item in diagnostics
    ] or ["No diagnostics."]
    return "\n".join(lines) + "\n"


def format_failure(diagnostic: Diagnostic) -> list[str]:
    """Format one failure diagnostic for the console."""

    location = diagnostic.source_path or "<unknown source>"
    if diagnostic.source_line is not None:
        location = f"{location}:{diagnostic.source_line}"

    names = ""
    if diagnostic.micro_operation:
        names += f" [{diagnostic.micro_operation}]"
    if diagnostic.field_name:
        names += f" [{diagnostic.field_name}]"

    return [
        f"{diagnostic.severity} {diagnostic.code}{names}",
        f"  Source: {location}",
        f"  {diagnostic.message}",
    ]


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate a candidate micro-operation mapping for review."
    )
    parser.add_argument(
        "--repo-root", required=True, type=Path, help="Path to the repository root."
    )
    parser.add_argument(
        "--micro-operations",
        type=Path,
        default=DEFAULT_MICRO_OPERATIONS,
        help="Micro-operation extractor JSON.",
    )
    parser.add_argument(
        "--control-word-schema",
        type=Path,
        default=DEFAULT_CONTROL_WORD_SCHEMA,
        help="Maintained control-word schema.",
    )
    parser.add_argument(
        "--maintained-mapping",
        type=Path,
        default=DEFAULT_MAINTAINED_MAPPING,
        help="Maintained micro-operation mapping; may be absent.",
    )
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=DEFAULT_CANDIDATE_OUTPUT,
        help="Candidate mapping output path.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help="Generation report output path.",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the generator; return 1 if any error-level diagnostic exists.

    Relative paths are resolved from the repository root.
    """

    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    micro_operations_path = resolve_from_repo(root, options.micro_operations)
    schema_path = resolve_from_repo(root, options.control_word_schema)
    maintained_path = resolve_from_repo(root, options.maintained_mapping)
    candidate_path = resolve_from_repo(root, options.candidate_output)
    report_path = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs(
            (candidate_path, report_path),
            (micro_operations_path, schema_path, maintained_path),
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    diagnostics: list[Diagnostic] = []
    mapping_count = 0
    candidate_written = False

    try:
        micro_operations = read_json(micro_operations_path)
        schema = read_json(schema_path)
        maintained = read_json(maintained_path, optional=True)
        operations = micro_operations.get("micro_operations")
        mapping_count = len(operations) if isinstance(operations, list) else 0
        candidate, diagnostics = build_candidate(micro_operations, schema, maintained)

        if candidate is not None:
            write_text(candidate_path, serialize_json(candidate))
            candidate_written = True
    except GenerationFailure as error:
        diagnostics = [make_diagnostic(FATAL, "GENERATION_FAILURE", str(error))]

    diagnostics = sorted(diagnostics, key=diagnostic_sort_key)
    write_text(report_path, build_report(diagnostics, mapping_count, candidate_written))

    failures = [item for item in diagnostics if item.severity in FAILURE_SEVERITIES]
    exit_code = 1 if failures else 0

    print("Micro-operation mapping generation")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Micro-operations: {mapping_count}")
    print(f"Candidate written: {'yes' if candidate_written else 'no'}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"Candidate output: {candidate_path}")
    print(f"Report output: {report_path}")

    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            print("\n".join(format_failure(item)))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
