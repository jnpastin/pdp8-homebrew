"""Generate a candidate control-word schema for review.

The generator combines the control-output extractor's output with the
maintained schema's reviewed ``control_word_role`` decisions and writes a
candidate schema plus a report.  It never modifies the maintained schema.

Pipeline:

1. Read the extractor output and, if present, the maintained schema.
2. Validate both structurally.  Any error stops candidate construction.
3. Build one candidate field per extracted signal, carrying forward the
   reviewed ``control_word_role`` for that signal.
4. Report unresolved roles and stale maintained fields.
5. Write the candidate (only when no errors remain) and the report.

See the tool README for the schema contract.
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

DEFAULT_INPUT = Path(
    "build/simulation_outputs/rom-generation/control-output-extractor/"
    "control-outputs.json"
)
DEFAULT_MAINTAINED = Path("rom/microcode/v1/control-word-schema.json")

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/control-word-schema-generator"
)
DEFAULT_CANDIDATE = OUTPUT_DIRECTORY / "control-word-schema.candidate.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "generation-report.txt"

# ---------------------------------------------------------------------------
# Expected extractor output
# ---------------------------------------------------------------------------

EXTRACTOR_TYPE = "control-output-extractor"
EXTRACTOR_FORMAT_VERSION = 1
EXTRACTOR_STAGE = "category-validation"
VALIDATED_STATUS = "category-validated"
EXPLICIT_VALUE_REQUIRED_VALUES = frozenset({"Yes", "No", "Conditionally"})
NOT_APPLICABLE = "N/A"
OCTAL_PATTERN = re.compile(r"[0-7]+")

# Extracted attributes promoted to top-level field properties.
CONTROL_METADATA_KEYS = (
    "default_value",
    "explicit_value_required",
    "value_required_when",
)

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_TYPE = "control-word-schema"
SCHEMA_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"
SCHEMA_DESCRIPTION = "Logical symbolic control-word schema for version 1 CPU control."
CONTROL_WORD_ROLES = frozenset({"encoded", "derived", "external_input"})

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
    field_name: str | None = None,
    source: Any = None,
) -> Diagnostic:
    """Build a diagnostic, taking its location from an extractor source.

    ``source`` is an extractor ``{"path": ..., "line": ...}`` object.  Parts
    of it with the wrong type, and any non-object value, are left out.
    """

    if not isinstance(source, dict):
        source = {}
    path = source.get("path")
    line = source.get("line")

    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        field_name=field_name,
        source_path=path if isinstance(path, str) else None,
        source_line=line if isinstance(line, int) else None,
    )


def make_error(
    code: str,
    message: str,
    *,
    field_name: str | None = None,
    source: Any = None,
) -> Diagnostic:
    """Build an ERROR diagnostic."""

    return make_diagnostic(ERROR, code, message, field_name=field_name, source=source)


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
        diagnostic.field_name or "",
        diagnostic.message,
    )


def is_text(value: Any) -> bool:
    """Return whether ``value`` is a non-empty string."""

    return isinstance(value, str) and bool(value)


def is_positive_integer(value: Any) -> bool:
    """Return whether ``value`` is an integer (not a bool) of at least 1."""

    return isinstance(value, int) and not isinstance(value, bool) and value >= 1


# ---------------------------------------------------------------------------
# Reading inputs
# ---------------------------------------------------------------------------


def resolve_from_repo(root: Path, path: Path) -> Path:
    """Resolve a relative path from the repository root."""

    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_json(
    path: Path,
    label: str,
    optional: bool = False,
) -> dict[str, Any] | None:
    """Read a JSON object from ``path``; ``label`` names it in messages.

    An optional file that is missing or blank yields None.  Every other
    problem raises ``GenerationFailure``.
    """

    if optional and not path.exists():
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise GenerationFailure(f"{label} does not exist: {path}") from error
    except UnicodeDecodeError as error:
        raise GenerationFailure(f"{label} is not valid UTF-8: {path}") from error
    except OSError as error:
        raise GenerationFailure(
            f"Unable to read {label.lower()} {path}: {error}"
        ) from error

    if optional and not text.strip():
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise GenerationFailure(
            f"{label} is not valid JSON: {path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(data, dict):
        raise GenerationFailure(f"{label} must contain a top-level JSON object.")

    return data


# ---------------------------------------------------------------------------
# Extractor validation
# ---------------------------------------------------------------------------


def validate_extracted(data: dict[str, Any]) -> list[Diagnostic]:
    """Validate the structure of the extractor output."""

    diagnostics: list[Diagnostic] = []

    format_version = data.get("format_version")
    if format_version != EXTRACTOR_FORMAT_VERSION:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_FORMAT_VERSION",
                f"Expected extractor format_version {EXTRACTOR_FORMAT_VERSION}, "
                f"found {format_version!r}.",
            )
        )

    extraction_stage = data.get("extraction_stage")
    if extraction_stage != EXTRACTOR_STAGE:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_EXTRACTION_STAGE",
                f"Expected extraction_stage {EXTRACTOR_STAGE!r}, "
                f"found {extraction_stage!r}.",
            )
        )

    extractor_diagnostics = data.get("diagnostics")
    if not isinstance(extractor_diagnostics, list):
        diagnostics.append(
            make_error(
                "INVALID_INPUT_DIAGNOSTICS", "Extractor diagnostics must be an array."
            )
        )
    elif extractor_diagnostics:
        diagnostics.append(
            make_error(
                "EXTRACTOR_DIAGNOSTICS_PRESENT",
                "Extractor input contains unresolved diagnostics.",
            )
        )

    signals = data.get("signals")
    if not isinstance(signals, list):
        diagnostics.append(
            make_error(
                "INVALID_SIGNALS", "Extractor input must contain a signals array."
            )
        )
        return diagnostics

    seen_names: set[str] = set()
    for signal in signals:
        diagnostics += validate_signal(signal, seen_names)

    return diagnostics


def validate_source(source: Any, field_name: str, context: str) -> list[Diagnostic]:
    """Validate one extractor ``{"path": ..., "line": ...}`` reference.

    ``context`` names the source's owner in messages, e.g. "Encoding".
    """

    if not isinstance(source, dict):
        return [
            make_error(
                "INVALID_SOURCE",
                f"{context} source must be an object.",
                field_name=field_name,
            )
        ]

    diagnostics: list[Diagnostic] = []

    if not is_text(source.get("path")):
        diagnostics.append(
            make_error(
                "MISSING_SOURCE_PATH",
                f"{context} source does not contain a valid path.",
                field_name=field_name,
                source=source,
            )
        )
    if not is_positive_integer(source.get("line")):
        diagnostics.append(
            make_error(
                "INVALID_SOURCE_LINE",
                f"{context} source does not contain a positive line number.",
                field_name=field_name,
                source=source,
            )
        )

    return diagnostics


def validate_signal(signal: Any, seen_names: set[str]) -> list[Diagnostic]:
    """Validate one extracted signal; record its name in ``seen_names``."""

    if not isinstance(signal, dict):
        return [make_error("INVALID_SIGNAL", "Signal entry must be an object.")]

    name = signal.get("name")
    source = signal.get("source")

    if not is_text(name):
        return [
            make_error(
                "INVALID_SIGNAL_NAME",
                "Signal name must be a non-empty string.",
                source=source,
            )
        ]

    diagnostics: list[Diagnostic] = []

    def report(code: str, message: str) -> None:
        diagnostics.append(make_error(code, message, field_name=name, source=source))

    if name in seen_names:
        report("DUPLICATE_SIGNAL_NAME", f"Signal {name!r} appears more than once.")
    seen_names.add(name)

    if not is_text(signal.get("category")):
        report("INVALID_CATEGORY", "Signal category must be a non-empty string.")

    extraction_status = signal.get("extraction_status")
    if extraction_status != VALIDATED_STATUS:
        report(
            "INVALID_EXTRACTION_STATUS",
            f"Expected extraction_status {VALIDATED_STATUS!r}, "
            f"found {extraction_status!r}.",
        )

    diagnostics += validate_source(source, name, "Index")

    definition = signal.get("definition")
    if not isinstance(definition, dict):
        report("INVALID_DEFINITION", "Signal definition must be an object.")
        return diagnostics

    return diagnostics + validate_definition(definition, name)


def validate_definition(definition: dict[str, Any], name: str) -> list[Diagnostic]:
    """Validate one signal's extracted definition."""

    source = definition.get("source")
    diagnostics = validate_source(source, name, "Definition")

    def report(code: str, message: str) -> None:
        diagnostics.append(make_error(code, message, field_name=name, source=source))

    if not is_text(definition.get("heading")):
        report(
            "INVALID_DEFINITION_HEADING",
            "Definition heading must be a non-empty string.",
        )

    attributes = definition.get("attributes")
    if isinstance(attributes, dict):
        diagnostics += validate_attributes(attributes, name, source)
    else:
        report("INVALID_ATTRIBUTES", "Definition attributes must be an object.")

    width = definition.get("bit_width")
    if not is_positive_integer(width):
        report("INVALID_BIT_WIDTH", "Definition bit_width must be a positive integer.")
        width = None

    encodings = definition.get("encodings")
    if isinstance(encodings, list):
        diagnostics += validate_encodings(encodings, name, width)
    else:
        report("INVALID_ENCODINGS", "Definition encodings must be an array.")

    uses = definition.get("used_by_micro_operations")
    if isinstance(uses, list):
        for use in uses:
            diagnostics += validate_micro_operation_use(use, name, source)
    else:
        report(
            "INVALID_USED_BY_MICRO_OPERATIONS",
            "Definition used_by_micro_operations must be an array.",
        )

    constraints = definition.get("constraints")
    if isinstance(constraints, list):
        for constraint in constraints:
            diagnostics += validate_constraint(constraint, name, source)
    else:
        report("INVALID_CONSTRAINTS", "Definition constraints must be an array.")

    return diagnostics


def validate_attributes(
    attributes: dict[str, Any],
    name: str,
    source: Any,
) -> list[Diagnostic]:
    """Validate the control-word attributes the candidate promotes."""

    diagnostics: list[Diagnostic] = []

    def report(code: str, message: str) -> None:
        diagnostics.append(make_error(code, message, field_name=name, source=source))

    if not is_text(attributes.get("default_value")):
        report(
            "INVALID_EXTRACTED_DEFAULT_VALUE",
            "Extracted default_value must be a non-empty string.",
        )
    if attributes.get("explicit_value_required") not in EXPLICIT_VALUE_REQUIRED_VALUES:
        report(
            "INVALID_EXTRACTED_EXPLICIT_REQUIREMENT",
            "Extracted explicit_value_required must be Yes, No, or Conditionally.",
        )
    if not is_text(attributes.get("value_required_when")):
        report(
            "INVALID_EXTRACTED_VALUE_CONDITION",
            "Extracted value_required_when must be a non-empty string.",
        )

    return diagnostics


def validate_encodings(
    encodings: list[Any],
    name: str,
    width: int | None,
) -> list[Diagnostic]:
    """Validate a signal's encodings; ``width`` is None when it is invalid."""

    diagnostics: list[Diagnostic] = []
    seen_values: set[str] = set()

    for encoding in encodings:
        diagnostics += validate_encoding(encoding, name, width)

        value = encoding.get("value") if isinstance(encoding, dict) else None
        if not isinstance(value, str):
            continue
        if value in seen_values:
            diagnostics.append(
                make_error(
                    "DUPLICATE_ENCODING_VALUE",
                    f"Encoding {value!r} appears more than once.",
                    field_name=name,
                    source=encoding.get("source"),
                )
            )
        seen_values.add(value)

    return diagnostics


def validate_encoding(encoding: Any, name: str, width: int | None) -> list[Diagnostic]:
    """Validate one encoding entry on its own."""

    if not isinstance(encoding, dict):
        return [
            make_error(
                "INVALID_ENCODING",
                "Encoding entry must be an object.",
                field_name=name,
            )
        ]

    value = encoding.get("value")
    source = encoding.get("source")
    diagnostics: list[Diagnostic] = []

    def report(code: str, message: str) -> None:
        diagnostics.append(make_error(code, message, field_name=name, source=source))

    if not is_text(value):
        report("INVALID_ENCODING_VALUE", "Encoding value must be a non-empty string.")
    elif not OCTAL_PATTERN.fullmatch(value):
        report("NON_OCTAL_ENCODING", f"Encoding {value!r} is not valid octal.")
    elif width is not None and int(value, 8) >= 1 << width:
        report(
            "ENCODING_EXCEEDS_WIDTH",
            f"Encoding {value!r} does not fit in {width} bits.",
        )

    if not is_text(encoding.get("meaning")):
        report(
            "INVALID_ENCODING_MEANING", "Encoding meaning must be a non-empty string."
        )

    return diagnostics + validate_source(source, name, "Encoding")


def validate_micro_operation_use(
    use: Any,
    name: str,
    definition_source: Any,
) -> list[Diagnostic]:
    """Validate one ``used_by_micro_operations`` entry."""

    if not isinstance(use, dict) or not is_text(use.get("micro_operation")):
        location = use.get("source") if isinstance(use, dict) else definition_source
        return [
            make_error(
                "INVALID_USED_BY_MICRO_OPERATION",
                "Used-by entry must name a micro-operation.",
                field_name=name,
                source=location,
            )
        ]

    diagnostics: list[Diagnostic] = []

    if "value" in use and not is_text(use["value"]):
        diagnostics.append(
            make_error(
                "INVALID_USED_BY_VALUE",
                "Used-by value must be a non-empty string when present.",
                field_name=name,
                source=use.get("source"),
            )
        )

    return diagnostics + validate_source(
        use.get("source"), name, "Used-by micro-operation"
    )


def validate_constraint(
    constraint: Any,
    name: str,
    definition_source: Any,
) -> list[Diagnostic]:
    """Validate one extracted constraint."""

    if not isinstance(constraint, dict):
        return [
            make_error(
                "INVALID_CONSTRAINT",
                "Constraint entry must be an object.",
                field_name=name,
                source=definition_source,
            )
        ]

    diagnostics: list[Diagnostic] = []
    source = constraint.get("source")

    if not is_text(constraint.get("text")):
        diagnostics.append(
            make_error(
                "INVALID_CONSTRAINT_TEXT",
                "Constraint text must be a non-empty string.",
                field_name=name,
                source=source,
            )
        )

    return diagnostics + validate_source(source, name, "Constraint")


# ---------------------------------------------------------------------------
# Maintained schema validation
# ---------------------------------------------------------------------------


def validate_maintained(
    data: dict[str, Any] | None,
) -> tuple[list[Diagnostic], dict[str, str]]:
    """Validate the maintained schema and index its roles by field name.

    A missing schema (None) is valid and has no fields.  The returned roles
    are only meaningful when no diagnostics are returned.
    """

    if data is None:
        return [], {}

    diagnostics: list[Diagnostic] = []

    if data.get("specification_type") != SCHEMA_TYPE:
        diagnostics.append(
            make_error(
                "INVALID_MAINTAINED_SPECIFICATION_TYPE",
                f"Maintained schema specification_type must be {SCHEMA_TYPE!r}.",
            )
        )
    if data.get("schema_version") != SCHEMA_VERSION:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_MAINTAINED_SCHEMA_VERSION",
                "Maintained schema uses an unsupported schema_version.",
            )
        )
    if data.get("control_design_version") != CONTROL_DESIGN_VERSION:
        diagnostics.append(
            make_error(
                "INVALID_MAINTAINED_DESIGN_VERSION",
                "Maintained schema uses a different control_design_version.",
            )
        )

    fields = data.get("fields")

    if not isinstance(fields, list):
        diagnostics.append(
            make_error(
                "INVALID_MAINTAINED_FIELDS",
                "Maintained schema must contain a fields array.",
            )
        )
        return diagnostics, {}

    roles: dict[str, str] = {}

    for field in fields:
        if not isinstance(field, dict):
            diagnostics.append(
                make_error(
                    "INVALID_MAINTAINED_FIELD",
                    "Maintained field entry must be an object.",
                )
            )
            continue

        name = field.get("name")

        if not is_text(name):
            diagnostics.append(
                make_error(
                    "INVALID_MAINTAINED_FIELD_NAME",
                    "Maintained field name must be a non-empty string.",
                )
            )
            continue

        if name in roles:
            diagnostics.append(
                make_error(
                    "DUPLICATE_MAINTAINED_FIELD",
                    f"Maintained field {name!r} appears more than once.",
                    field_name=name,
                )
            )

        role = field.get("control_word_role")
        roles[name] = role

        if "control_word_role" not in field:
            diagnostics.append(
                make_error(
                    "MISSING_CONTROL_WORD_ROLE",
                    "Maintained field does not contain control_word_role.",
                    field_name=name,
                )
            )
        elif role not in CONTROL_WORD_ROLES:
            diagnostics.append(
                make_error(
                    "INVALID_CONTROL_WORD_ROLE",
                    "Maintained control_word_role must be encoded, derived, "
                    "or external_input.",
                    field_name=name,
                )
            )

    return diagnostics, roles


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


def convert_source(source: dict[str, Any]) -> dict[str, Any]:
    """Convert an extractor source to the schema's ``document``/``line`` form."""

    return {"document": source["path"], "line": source["line"]}


def field_from_signal(signal: dict[str, Any], role: str | None) -> dict[str, Any]:
    """Build one candidate field from a validated extracted signal.

    Key order is part of the output format.
    """

    definition = signal["definition"]
    attributes = definition["attributes"]
    default_value = attributes["default_value"]

    return {
        "name": signal["name"],
        "category": signal["category"],
        "width": definition["bit_width"],
        "control_word_role": role,
        "default_value": None if default_value == NOT_APPLICABLE else default_value,
        "explicit_value_required": attributes["explicit_value_required"],
        "value_required_when": attributes["value_required_when"],
        "attributes": {
            key: value
            for key, value in attributes.items()
            if key not in CONTROL_METADATA_KEYS
        },
        "values": [
            {
                "encoding": encoding["value"],
                "meaning": encoding["meaning"],
                "source": convert_source(encoding["source"]),
            }
            for encoding in definition["encodings"]
        ],
        "constraints": [
            {
                "text": constraint["text"],
                "source": convert_source(constraint["source"]),
            }
            for constraint in definition["constraints"]
        ],
        "used_by_micro_operations": [
            {
                "micro_operation": use["micro_operation"],
                **({"value": use["value"]} if "value" in use else {}),
                "source": convert_source(use["source"]),
            }
            for use in definition["used_by_micro_operations"]
        ],
        "sources": {
            "index": convert_source(signal["source"]),
            "definition": {
                "document": definition["source"]["path"],
                "section": definition["heading"],
                "line": definition["source"]["line"],
            },
        },
    }


def build_candidate(
    extracted: dict[str, Any],
    maintained: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Validate the inputs and build the candidate schema.

    Returns ``(None, diagnostics)`` when either input is structurally
    invalid.  Otherwise returns the candidate and its warnings.
    """

    diagnostics = validate_extracted(extracted)
    maintained_diagnostics, roles = validate_maintained(maintained)
    diagnostics += maintained_diagnostics

    if has_failures(diagnostics):
        return None, diagnostics

    signals = extracted["signals"]
    signal_names = {signal["name"] for signal in signals}
    fields = []

    for signal in signals:
        role = roles.get(signal["name"])

        if role is None:
            diagnostics.append(
                make_diagnostic(
                    WARNING,
                    "CONTROL_WORD_ROLE_UNRESOLVED",
                    "Control-word role requires review and was not inferred.",
                    field_name=signal["name"],
                    source=signal["definition"]["source"],
                )
            )

        fields.append(field_from_signal(signal, role))

    diagnostics.extend(
        make_diagnostic(
            WARNING,
            "STALE_MAINTAINED_FIELD",
            "Maintained field is absent from the current extractor output.",
            field_name=name,
        )
        for name in roles
        if name not in signal_names
    )

    candidate = {
        "specification_type": SCHEMA_TYPE,
        "schema_version": SCHEMA_VERSION,
        "control_design_version": CONTROL_DESIGN_VERSION,
        "description": SCHEMA_DESCRIPTION,
        "source": {
            "specification_type": EXTRACTOR_TYPE,
            "format_version": extracted["format_version"],
            "extraction_stage": extracted["extraction_stage"],
        },
        "fields": fields,
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


def write_json(data: dict[str, Any], path: Path) -> None:
    """Write deterministic JSON."""

    write_text(path, serialize_json(data))


def format_location(diagnostic: Diagnostic) -> str:
    """Return ``path:line``, either part, or "" when neither is known."""

    parts = [diagnostic.source_path, diagnostic.source_line]
    return ":".join(str(part) for part in parts if part is not None)


def format_diagnostic(diagnostic: Diagnostic) -> str:
    """Format one diagnostic as a report line."""

    location = format_location(diagnostic)
    prefix = f"{diagnostic.severity} {diagnostic.code} [{diagnostic.field_name or '-'}]"
    if location:
        prefix += f" {location}"
    return f"{prefix}: {diagnostic.message}"


def build_report(
    diagnostics: Sequence[Diagnostic],
    field_count: int,
    candidate_written: bool,
) -> str:
    """Build the human-readable generation report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Control-Word Schema Generation Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Fields processed: {field_count}",
        f"Candidate written: {'yes' if candidate_written else 'no'}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    lines += [format_diagnostic(item) for item in diagnostics] or ["No diagnostics."]
    return "\n".join(lines) + "\n"


def format_failure(diagnostic: Diagnostic) -> list[str]:
    """Format one failure diagnostic for the console."""

    location = diagnostic.source_path or "<unknown source>"
    if diagnostic.source_line is not None:
        location = f"{location}:{diagnostic.source_line}"
    name = f" [{diagnostic.field_name}]" if diagnostic.field_name else ""

    return [
        f"{diagnostic.severity} {diagnostic.code}{name}",
        f"  Source: {location}",
        f"  {diagnostic.message}",
    ]


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate a candidate control-word schema for review."
    )
    parser.add_argument(
        "--repo-root", required=True, type=Path, help="Path to the repository root."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Control-output extractor JSON.",
    )
    parser.add_argument(
        "--maintained-schema",
        type=Path,
        default=DEFAULT_MAINTAINED,
        help="Maintained control-word schema; may be absent.",
    )
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=DEFAULT_CANDIDATE,
        help="Candidate schema output path.",
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
    input_path = resolve_from_repo(root, options.input)
    maintained_path = resolve_from_repo(root, options.maintained_schema)
    candidate_path = resolve_from_repo(root, options.candidate_output)
    report_path = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs(
            (candidate_path, report_path), (input_path, maintained_path)
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    diagnostics: list[Diagnostic] = []
    field_count = 0
    candidate_written = False

    try:
        extracted = read_json(input_path, "Input file")
        maintained = read_json(maintained_path, "Maintained schema", optional=True)
        signals = extracted.get("signals")
        field_count = len(signals) if isinstance(signals, list) else 0
        candidate, diagnostics = build_candidate(extracted, maintained)

        if candidate is not None:
            write_json(candidate, candidate_path)
            candidate_written = True
    except GenerationFailure as error:
        diagnostics = [make_diagnostic(FATAL, "GENERATION_FAILURE", str(error))]

    diagnostics = sorted(diagnostics, key=diagnostic_sort_key)
    write_text(report_path, build_report(diagnostics, field_count, candidate_written))

    failures = [item for item in diagnostics if item.severity in FAILURE_SEVERITIES]
    exit_code = 1 if failures else 0

    print("Control-word schema generation")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Control outputs: {field_count}")
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
