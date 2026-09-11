"""Generate a candidate control-word schema from extracted control outputs."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


DEFAULT_INPUT = Path(
    "build/simulation_outputs/rom-generation/"
    "control-output-extractor/control-outputs.json"
)

DEFAULT_MAINTAINED_SCHEMA = Path(
    "rom/microcode/v1/control-word-schema.json"
)

DEFAULT_CANDIDATE_OUTPUT = Path(
    "build/simulation_outputs/rom-generation/"
    "control-word-schema-generator/control-word-schema.candidate.json"
)

DEFAULT_REPORT_OUTPUT = Path(
    "build/simulation_outputs/rom-generation/"
    "control-word-schema-generator/generation-report.txt"
)

SUPPORTED_INPUT_FORMAT_VERSION = 1
OUTPUT_SCHEMA_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"

EXPECTED_EXTRACTION_STAGE = "category-validation"
EXPECTED_EXTRACTION_STATUS = "category-validated"


@dataclass(frozen=True)
class ToolPaths:
    """Resolved paths used for one generator run."""

    repo_root: Path
    input_path: Path
    maintained_schema_path: Path
    candidate_output_path: Path
    report_output_path: Path

@dataclass(frozen=True)
class Diagnostic:
    """One generator diagnostic."""

    severity: str
    code: str
    message: str
    field_name: str | None = None
    source_path: str | None = None
    source_line: int | None = None


class GenerationFailure(Exception):
    """Raised when reliable candidate generation cannot continue."""


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Generate a candidate control-word schema from extracted "
            "control-output definitions."
        )
    )

    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Repository root used to resolve relative paths.",
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Control-output extractor JSON input.",
    )
    
    parser.add_argument(
        "--maintained-schema",
        type=Path,
        default=DEFAULT_MAINTAINED_SCHEMA,
        help=(
            "Reviewed maintained schema from which existing "
            "control-word roles are preserved. A missing file is allowed."
        ),
    )

    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=DEFAULT_CANDIDATE_OUTPUT,
        help="Candidate control-word schema output.",
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help="Human-readable generation report output.",
    )

    return parser.parse_args(arguments)


def resolve_from_repo(repo_root: Path, path: Path) -> Path:
    """Resolve a path relative to the repository root when necessary."""

    if path.is_absolute():
        return path.resolve()

    return (repo_root / path).resolve()


def build_tool_paths(arguments: argparse.Namespace) -> ToolPaths:
    """Build the fully resolved path set for one run."""

    repo_root = arguments.repo_root.resolve()

    return ToolPaths(
        repo_root=repo_root,
        input_path=resolve_from_repo(repo_root, arguments.input),
        maintained_schema_path=resolve_from_repo(
            repo_root,
            arguments.maintained_schema,
        ),
        candidate_output_path=resolve_from_repo(
            repo_root,
            arguments.candidate_output,
        ),
        report_output_path=resolve_from_repo(
            repo_root,
            arguments.report_output,
        ),
    )


def read_json_input(input_path: Path) -> dict[str, Any]:
    """Read and decode the extractor JSON input."""

    try:
        input_text = input_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise GenerationFailure(
            f"Input file does not exist: {input_path}"
        ) from error
    except UnicodeDecodeError as error:
        raise GenerationFailure(
            f"Input file is not valid UTF-8: {input_path}"
        ) from error
    except OSError as error:
        raise GenerationFailure(
            f"Unable to read input file {input_path}: {error}"
        ) from error

    try:
        result = json.loads(input_text)
    except json.JSONDecodeError as error:
        raise GenerationFailure(
            f"Input file is not valid JSON: {input_path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(result, dict):
        raise GenerationFailure(
            "Extractor input must contain a top-level JSON object."
        )

    return result

def read_maintained_schema(
    schema_path: Path,
) -> dict[str, Any] | None:
    """Read the maintained schema when it exists."""

    if not schema_path.exists():
        return None

    try:
        schema_text = schema_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise GenerationFailure(
            f"Maintained schema is not valid UTF-8: {schema_path}"
        ) from error
    except OSError as error:
        raise GenerationFailure(
            f"Unable to read maintained schema {schema_path}: {error}"
        ) from error

    if not schema_text.strip(): 
        return None

    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as error:
        raise GenerationFailure(
            f"Maintained schema is not valid JSON: {schema_path}: "
            f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(schema, dict):
        raise GenerationFailure(
            "Maintained schema must contain a top-level JSON object."
        )

    return schema
    
def diagnostic(
    severity: str,
    code: str,
    message: str,
    *,
    field_name: str | None = None,
    source: Any = None,
) -> Diagnostic:
    """Create a diagnostic with optional source information."""

    source_path: str | None = None
    source_line: int | None = None

    if isinstance(source, dict):
        path_value = source.get("path")
        line_value = source.get("line")

        if isinstance(path_value, str):
            source_path = path_value

        if isinstance(line_value, int):
            source_line = line_value

    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        field_name=field_name,
        source_path=source_path,
        source_line=source_line,
    )


def validate_source(
    source: Any,
    *,
    field_name: str,
    context: str,
) -> list[Diagnostic]:
    """Validate one extractor source-reference object."""

    diagnostics = []

    if not isinstance(source, dict):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_SOURCE",
                f"{context} source must be an object.",
                field_name=field_name,
            )
        )
        return diagnostics

    path = source.get("path")
    line = source.get("line")

    if not isinstance(path, str) or not path:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "MISSING_SOURCE_PATH",
                f"{context} source does not contain a valid path.",
                field_name=field_name,
                source=source,
            )
        )

    if not isinstance(line, int) or line < 1:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_SOURCE_LINE",
                f"{context} source does not contain a positive line number.",
                field_name=field_name,
                source=source,
            )
        )

    return diagnostics


def validate_top_level(input_data: dict[str, Any]) -> list:
    """Validate the extractor input's top-level structure."""

    diagnostics: list[Diagnostic] = []

    format_version = input_data.get("format_version")
    if format_version != SUPPORTED_INPUT_FORMAT_VERSION:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "UNSUPPORTED_FORMAT_VERSION",
                "Expected extractor format_version "
                f"{SUPPORTED_INPUT_FORMAT_VERSION}, found "
                f"{format_version!r}.",
            )
        )

    extraction_stage = input_data.get("extraction_stage")
    if extraction_stage != EXPECTED_EXTRACTION_STAGE:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "UNSUPPORTED_EXTRACTION_STAGE",
                f"Expected extraction_stage "
                f"{EXPECTED_EXTRACTION_STAGE!r}, found "
                f"{extraction_stage!r}.",
            )
        )

    input_diagnostics = input_data.get("diagnostics")
    if not isinstance(input_diagnostics, list):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_INPUT_DIAGNOSTICS",
                "Extractor diagnostics must be an array.",
            )
        )
    elif input_diagnostics:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "EXTRACTOR_DIAGNOSTICS_PRESENT",
                "Extractor input contains unresolved diagnostics.",
            )
        )

    signals = input_data.get("signals")
    if not isinstance(signals, list):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_SIGNALS",
                "Extractor input must contain a signals array.",
            )
        )

    return diagnostics


def validate_encoding(
    encoding: Any,
    *,
    field_name: str,
    width: int | None,
) -> list:
    """Validate one extracted encoding entry."""

    diagnostics: list[Diagnostic] = []

    if not isinstance(encoding, dict):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_ENCODING",
                "Encoding entry must be an object.",
                field_name=field_name,
            )
        )
        return diagnostics

    value = encoding.get("value")
    meaning = encoding.get("meaning")
    source = encoding.get("source")

    if not isinstance(value, str) or not value:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_ENCODING_VALUE",
                "Encoding value must be a non-empty string.",
                field_name=field_name,
                source=source,
            )
        )
    elif width is not None:
        try:
            numeric_value = int(value, 8)
        except ValueError:
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "NON_OCTAL_ENCODING",
                    f"Encoding {value!r} is not valid octal.",
                    field_name=field_name,
                    source=source,
                )
            )
        else:
            if numeric_value >= (1 << width):
                diagnostics.append(
                    diagnostic(
                        "ERROR",
                        "ENCODING_EXCEEDS_WIDTH",
                        f"Encoding {value!r} does not fit in "
                        f"{width} bits.",
                        field_name=field_name,
                        source=source,
                    )
                )

    if not isinstance(meaning, str) or not meaning:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_ENCODING_MEANING",
                "Encoding meaning must be a non-empty string.",
                field_name=field_name,
                source=source,
            )
        )

    diagnostics.extend(
        validate_source(
            source,
            field_name=field_name,
            context="Encoding",
        )
    )

    return diagnostics


def validate_signal(
    signal: Any,
    seen_names: set[str],
) -> list:
    """Validate one extracted control-output signal."""

    diagnostics: list[Diagnostic] = []

    if not isinstance(signal, dict):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_SIGNAL",
                "Signal entry must be an object.",
            )
        )
        return diagnostics

    name = signal.get("name")
    source = signal.get("source")

    if not isinstance(name, str) or not name:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_SIGNAL_NAME",
                "Signal name must be a non-empty string.",
                source=source,
            )
        )
        return diagnostics

    if name in seen_names:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "DUPLICATE_SIGNAL_NAME",
                f"Signal {name!r} appears more than once.",
                field_name=name,
                source=source,
            )
        )
    else:
        seen_names.add(name)

    category = signal.get("category")
    if not isinstance(category, str) or not category:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_CATEGORY",
                "Signal category must be a non-empty string.",
                field_name=name,
                source=source,
            )
        )

    extraction_status = signal.get("extraction_status")
    if extraction_status != EXPECTED_EXTRACTION_STATUS:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_EXTRACTION_STATUS",
                f"Expected extraction_status "
                f"{EXPECTED_EXTRACTION_STATUS!r}, found "
                f"{extraction_status!r}.",
                field_name=name,
                source=source,
            )
        )

    diagnostics.extend(
        validate_source(
            source,
            field_name=name,
            context="Index",
        )
    )

    definition = signal.get("definition")
    if not isinstance(definition, dict):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_DEFINITION",
                "Signal definition must be an object.",
                field_name=name,
                source=source,
            )
        )
        return diagnostics

    definition_source = definition.get("source")
    diagnostics.extend(
        validate_source(
            definition_source,
            field_name=name,
            context="Definition",
        )
    )

    heading = definition.get("heading")
    if not isinstance(heading, str) or not heading:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_DEFINITION_HEADING",
                "Definition heading must be a non-empty string.",
                field_name=name,
                source=definition_source,
            )
        )

    attributes = definition.get("attributes")

    if not isinstance(attributes, dict):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_ATTRIBUTES",
                "Definition attributes must be an object.",
                field_name=name,
                source=definition_source,
            )
        )
    else:
        default_value = attributes.get("default_value")
        explicit_value_required = attributes.get(
            "explicit_value_required"
        )
        value_required_when = attributes.get(
            "value_required_when"
        )

        if not isinstance(default_value, str) or not default_value:
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "INVALID_EXTRACTED_DEFAULT_VALUE",
                    "Extracted default_value must be a non-empty string.",
                    field_name=name,
                    source=definition_source,
                )
            )

        if explicit_value_required not in {
            "Yes",
            "No",
            "Conditionally",
        }:
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "INVALID_EXTRACTED_EXPLICIT_REQUIREMENT",
                    "Extracted explicit_value_required must be Yes, "
                    "No, or Conditionally.",
                    field_name=name,
                    source=definition_source,
                )
            )

        if (
            not isinstance(value_required_when, str)
            or not value_required_when
        ):
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "INVALID_EXTRACTED_VALUE_CONDITION",
                    "Extracted value_required_when must be a "
                    "non-empty string.",
                    field_name=name,
                    source=definition_source,
                )
            )


    width = definition.get("bit_width")
    normalized_width: int | None = None

    if not isinstance(width, int) or isinstance(width, bool) or width < 1:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_BIT_WIDTH",
                "Definition bit_width must be a positive integer.",
                field_name=name,
                source=definition_source,
            )
        )
    else:
        normalized_width = width

    encodings = definition.get("encodings")
    if not isinstance(encodings, list):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_ENCODINGS",
                "Definition encodings must be an array.",
                field_name=name,
                source=definition_source,
            )
        )
    else:
        seen_encoding_values: set[str] = set()

        for encoding in encodings:
            diagnostics.extend(
                validate_encoding(
                    encoding,
                    field_name=name,
                    width=normalized_width,
                )
            )

            if isinstance(encoding, dict):
                value = encoding.get("value")
                if isinstance(value, str):
                    if value in seen_encoding_values:
                        diagnostics.append(
                            diagnostic(
                                "ERROR",
                                "DUPLICATE_ENCODING_VALUE",
                                f"Encoding {value!r} appears more than once.",
                                field_name=name,
                                source=encoding.get("source"),
                            )
                        )
                    else:
                        seen_encoding_values.add(value)

    constraints = definition.get("constraints")
    if not isinstance(constraints, list):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_CONSTRAINTS",
                "Definition constraints must be an array.",
                field_name=name,
                source=definition_source,
            )
        )
    else:
        for constraint in constraints:
            if not isinstance(constraint, dict):
                diagnostics.append(
                    diagnostic(
                        "ERROR",
                        "INVALID_CONSTRAINT",
                        "Constraint entry must be an object.",
                        field_name=name,
                        source=definition_source,
                    )
                )
                continue

            text = constraint.get("text")
            constraint_source = constraint.get("source")

            if not isinstance(text, str) or not text:
                diagnostics.append(
                    diagnostic(
                        "ERROR",
                        "INVALID_CONSTRAINT_TEXT",
                        "Constraint text must be a non-empty string.",
                        field_name=name,
                        source=constraint_source,
                    )
                )

            diagnostics.extend(
                validate_source(
                    constraint_source,
                    field_name=name,
                    context="Constraint",
                )
            )

    return diagnostics


def validate_signals(input_data: dict[str, Any]) -> list:
    """Validate all extracted signals."""

    signals = input_data.get("signals")
    if not isinstance(signals, list):
        return []

    diagnostics: list[Diagnostic] = []
    seen_names: set[str] = set()

    for signal in signals:
        diagnostics.extend(validate_signal(signal, seen_names))

    return diagnostics

def validate_maintained_schema(
    schema: dict[str, Any] | None,
) -> list[Diagnostic]:
    """Validate maintained control-word role decisions."""

    if schema is None:
        return []

    diagnostics: list[Diagnostic] = []

    if schema.get("specification_type") != "control-word-schema":
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_MAINTAINED_SPECIFICATION_TYPE",
                "Maintained schema specification_type must be "
                "'control-word-schema'.",
            )
        )

    if schema.get("schema_version") != OUTPUT_SCHEMA_VERSION:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "UNSUPPORTED_MAINTAINED_SCHEMA_VERSION",
                "Maintained schema uses an unsupported schema_version.",
            )
        )

    if schema.get("control_design_version") != CONTROL_DESIGN_VERSION:
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_MAINTAINED_DESIGN_VERSION",
                "Maintained schema uses a different "
                "control_design_version.",
            )
        )

    fields = schema.get("fields")

    if not isinstance(fields, list):
        diagnostics.append(
            diagnostic(
                "ERROR",
                "INVALID_MAINTAINED_FIELDS",
                "Maintained schema must contain a fields array.",
            )
        )
        return diagnostics

    seen_names: set[str] = set()

    for field in fields:
        if not isinstance(field, dict):
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "INVALID_MAINTAINED_FIELD",
                    "Maintained field entry must be an object.",
                )
            )
            continue

        name = field.get("name")

        if not isinstance(name, str) or not name:
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "INVALID_MAINTAINED_FIELD_NAME",
                    "Maintained field name must be a non-empty string.",
                )
            )
            continue

        if name in seen_names:
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "DUPLICATE_MAINTAINED_FIELD",
                    f"Maintained field {name!r} appears more than once.",
                    field_name=name,
                )
            )
        else:
            seen_names.add(name)

        if "control_word_role" not in field:
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "MISSING_CONTROL_WORD_ROLE",
                    "Maintained field does not contain "
                    "control_word_role.",
                    field_name=name,
                )
            )
            continue

        if field["control_word_role"] not in {
            "encoded",
            "derived",
            "external_input",
        }:
            diagnostics.append(
                diagnostic(
                    "ERROR",
                    "INVALID_CONTROL_WORD_ROLE",
                    "Maintained control_word_role must be encoded, "
                    "derived, or external_input.",
                    field_name=name,
                )
            )

    return diagnostics


def build_maintained_role_map(
    schema: dict[str, Any] | None,
) -> dict[str, str | None]:
    """Return reviewed control-word roles indexed by field name."""

    if schema is None:
        return {}

    return {
        field["name"]: field.get("control_word_role")
        for field in schema["fields"]
        if isinstance(field, dict)
        and isinstance(field.get("name"), str)
    }
    
def convert_source(source: dict[str, Any]) -> dict[str, Any]:
    """Convert extractor source keys to maintained-schema source keys."""

    return {
        "document": source["path"],
        "line": source["line"],
    }


def convert_encoding(encoding: dict[str, Any]) -> dict[str, Any]:
    """Convert one extracted encoding without changing its meaning."""

    return {
        "encoding": encoding["value"],
        "meaning": encoding["meaning"],
        "source": convert_source(encoding["source"]),
    }


def convert_constraint(constraint: dict[str, Any]) -> dict[str, Any]:
    """Convert one extracted constraint with its source reference."""

    return {
        "text": constraint["text"],
        "source": convert_source(constraint["source"]),
    }


def convert_signal(
    signal: dict[str, Any],
    maintained_roles: dict[str, str | None],
) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Convert one extracted signal into one candidate field."""

    name = signal["name"]
    definition = signal["definition"]
    definition_source = definition["source"]
    extracted_attributes = definition["attributes"]

    control_word_role = maintained_roles.get(name)
    default_value = extracted_attributes["default_value"]
    explicit_value_required = extracted_attributes[
        "explicit_value_required"
    ]
    value_required_when = extracted_attributes[
        "value_required_when"
    ]

    field_attributes = {
        key: value
        for key, value in extracted_attributes.items()
        if key not in {
            "default_value",
            "explicit_value_required",
            "value_required_when",
        }
    }

    field = {
        "name": name,
        "category": signal["category"],
        "width": definition["bit_width"],
        "control_word_role": control_word_role,
        "default_value": (
            None
            if default_value == "N/A"
            else default_value
        ),
        "explicit_value_required": explicit_value_required,
        "value_required_when": value_required_when,
        "attributes": field_attributes,
        "values": [
            convert_encoding(encoding)
            for encoding in definition["encodings"]
        ],
        "constraints": [
            convert_constraint(constraint)
            for constraint in definition["constraints"]
        ],
        "sources": {
            "index": convert_source(signal["source"]),
            "definition": {
                "document": definition_source["path"],
                "section": definition["heading"],
                "line": definition_source["line"],
            },
        },
    }

    diagnostics: list[Diagnostic] = []

    if control_word_role is None:
        diagnostics.append(
            diagnostic(
                "WARNING",
                "CONTROL_WORD_ROLE_UNRESOLVED",
                "Control-word role requires review and was not inferred.",
                field_name=name,
                source=definition_source,
            )
        )

    return field, diagnostics


def build_candidate(
    input_data: dict[str, Any],
    maintained_schema: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Build a candidate using extracted control metadata."""

    fields: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []

    maintained_roles = build_maintained_role_map(
        maintained_schema
    )
    extracted_names = {
        signal["name"]
        for signal in input_data["signals"]
    }

    for signal in input_data["signals"]:
        field, field_diagnostics = convert_signal(
            signal,
            maintained_roles,
        )
        fields.append(field)
        diagnostics.extend(field_diagnostics)

    for maintained_name in maintained_roles:
        if maintained_name not in extracted_names:
            diagnostics.append(
                diagnostic(
                    "WARNING",
                    "STALE_MAINTAINED_FIELD",
                    "Maintained field is absent from the current "
                    "extractor output.",
                    field_name=maintained_name,
                )
            )

    candidate = {
        "specification_type": "control-word-schema",
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "control_design_version": CONTROL_DESIGN_VERSION,
        "description": (
            "Logical symbolic control-word schema for version 1 CPU control."
        ),
        "source": {
            "specification_type": "control-output-extractor",
            "format_version": input_data["format_version"],
            "extraction_stage": input_data["extraction_stage"],
        },
        "fields": fields,
    }

    return candidate, diagnostics

def has_errors(diagnostics: Sequence[Diagnostic]) -> bool:
    """Return whether any diagnostic has error severity."""

    return any(
        item.severity in {"ERROR", "FATAL"}
        for item in diagnostics
    )


def write_json_output(
    candidate: dict[str, Any],
    output_path: Path,
) -> None:
    """Write deterministic, human-readable candidate JSON."""

    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = json.dumps(
        candidate,
        indent=2,
        ensure_ascii=False,
    )

    output_path.write_text(
        text + "\n",
        encoding="utf-8",
        newline="\n",
    )


def format_diagnostic(item: Diagnostic) -> str:
    """Format one diagnostic for the human-readable report."""

    location_parts: list[str] = []

    if item.source_path is not None:
        location_parts.append(item.source_path)

    if item.source_line is not None:
        location_parts.append(str(item.source_line))

    location = ":".join(location_parts)
    field = item.field_name or "-"

    prefix = f"{item.severity} {item.code} [{field}]"

    if location:
        prefix += f" {location}"

    return f"{prefix}: {item.message}"


def write_report(
    diagnostics: Sequence[Diagnostic],
    report_path: Path,
    *,
    field_count: int,
    candidate_written: bool,
) -> None:
    """Write the human-readable generation report."""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    severity_counts = {
        "INFO": 0,
        "WARNING": 0,
        "ERROR": 0,
        "FATAL": 0,
    }

    for item in diagnostics:
        severity_counts[item.severity] = (
            severity_counts.get(item.severity, 0) + 1
        )

    lines = [
        "Control-Word Schema Generation Report",
        "=====================================",
        "",
        f"Fields processed: {field_count}",
        f"Candidate written: {'yes' if candidate_written else 'no'}",
        f"Information diagnostics: {severity_counts['INFO']}",
        f"Warnings: {severity_counts['WARNING']}",
        f"Errors: {severity_counts['ERROR']}",
        f"Fatal errors: {severity_counts['FATAL']}",
        "",
        "Diagnostics",
        "-----------",
    ]

    if diagnostics:
        lines.extend(format_diagnostic(item) for item in diagnostics)
    else:
        lines.append("No diagnostics.")

    report_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def run(arguments: Sequence[str] | None = None) -> int:
    """Run the complete candidate-generation process."""

    parsed_arguments = parse_arguments(arguments)
    paths = build_tool_paths(parsed_arguments)

    diagnostics: list[Diagnostic] = []
    candidate_written = False
    field_count = 0

    try:
        input_data = read_json_input(paths.input_path)
        maintained_schema = read_maintained_schema(
            paths.maintained_schema_path
        )

        diagnostics.extend(
            validate_maintained_schema(maintained_schema)
        )

        diagnostics.extend(validate_top_level(input_data))

        if not has_errors(diagnostics):
            diagnostics.extend(validate_signals(input_data))

        signals = input_data.get("signals")
        if isinstance(signals, list):
            field_count = len(signals)

        if not has_errors(diagnostics):
            candidate, generation_diagnostics = build_candidate(
                input_data,
                maintained_schema,
            )
            diagnostics.extend(generation_diagnostics)

            write_json_output(
                candidate,
                paths.candidate_output_path,
            )
            candidate_written = True

    except GenerationFailure as error:
        diagnostics.append(
            diagnostic(
                "FATAL",
                "GENERATION_FAILURE",
                str(error),
            )
        )
    except OSError as error:
        diagnostics.append(
            diagnostic(
                "FATAL",
                "OUTPUT_WRITE_FAILURE",
                f"Unable to write generated output: {error}",
            )
        )

    try:
        write_report(
            diagnostics,
            paths.report_output_path,
            field_count=field_count,
            candidate_written=candidate_written,
        )
    except OSError as error:
        print(
            f"Unable to write generation report: {error}",
            file=sys.stderr,
        )
        return 1

    return 1 if has_errors(diagnostics) else 0


def main() -> None:
    """Command-line entry point."""

    raise SystemExit(run())


if __name__ == "__main__":
    main()