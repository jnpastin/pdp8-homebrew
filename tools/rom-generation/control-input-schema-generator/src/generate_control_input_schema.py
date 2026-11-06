"""Generate a candidate control-input schema for review.

The generator combines the control-input extractor's output with the
maintained schema's reviewed ``control_uses`` classifications and writes a
candidate schema plus a report.  It never modifies the maintained schema.

Pipeline:

1. Read the extractor output and, if present, the maintained schema.
2. Validate both structurally.  Any error stops candidate construction.
3. Build one candidate field per extracted signal, carrying forward the
   reviewed ``control_uses`` for that signal.
4. Report unresolved, stale, and undefined references.
5. Write the candidate (only when no errors remain) and the report.

See the tool README for the schema contract.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Hashable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_INPUT = Path(
    "build/simulation_outputs/rom-generation/control-input-extractor/"
    "control-inputs.json"
)
DEFAULT_MAINTAINED = Path("rom/microcode/v1/control-input-schema.json")

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/control-input-schema-generator"
)
DEFAULT_CANDIDATE = OUTPUT_DIRECTORY / "control-input-schema.candidate.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "generation-report.txt"

# ---------------------------------------------------------------------------
# Expected extractor output
# ---------------------------------------------------------------------------

EXTRACTOR_TYPE = "control-input-extractor"
EXTRACTOR_FORMAT_VERSION = 1
EXTRACTOR_STAGE = "final-structure-validation"
VALIDATED_STATUS = "structure-validated"
GLOBAL_CONSTRAINT_KINDS = frozenset({"exactly_one", "at_most_one"})

# Logic sections used as a field's derivation, in preference order.
DERIVATION_SECTIONS = ("derivation", "expression", "internal_composition")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_TYPE = "control-input-schema"
SCHEMA_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"
SCHEMA_DESCRIPTION = "Logical control-input schema for version 1 CPU control."
CONTROL_USES = frozenset({"predicate", "value"})

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
    input_name: str | None = None
    referenced_input: str | None = None
    source_path: str | None = None
    source_line: int | None = None


class GenerationFailure(Exception):
    """An input could not be read; generation cannot proceed."""


def make_diagnostic(
    severity: str,
    code: str,
    message: str,
    *,
    input_name: str | None = None,
    referenced_input: str | None = None,
    source: Any = None,
) -> Diagnostic:
    """Build a diagnostic, taking its location from an extractor source.

    ``source`` is an extractor ``{"path": ..., "line": ...}`` object; any
    other value leaves the location empty.
    """

    if not isinstance(source, dict):
        source = {}

    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        input_name=input_name,
        referenced_input=referenced_input,
        source_path=source.get("path"),
        source_line=source.get("line"),
    )


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.source_path or "",
        diagnostic.source_line if diagnostic.source_line is not None else -1,
        diagnostic.input_name or "",
        diagnostic.referenced_input or "",
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
        "input_name": diagnostic.input_name,
        "referenced_input": diagnostic.referenced_input,
        "source_path": diagnostic.source_path,
        "source_line": diagnostic.source_line,
    }
    result.update({key: value for key, value in optional.items() if value is not None})
    return result


def is_name(value: Any) -> bool:
    """Return whether ``value`` can be an input name."""

    return isinstance(value, str) and bool(value)


def as_reference(value: Any) -> str | None:
    """Return ``value`` if it is usable as a referenced-input name."""

    return value if isinstance(value, str) else None


# ---------------------------------------------------------------------------
# Reading inputs
# ---------------------------------------------------------------------------


def resolve_from_repo(root: Path, path: Path) -> Path:
    """Resolve a relative path from the repository root."""

    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_json(path: Path, optional: bool = False) -> dict[str, Any] | None:
    """Read a JSON object from ``path``.

    An optional file that is missing or blank yields None.  Every other
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
        raise GenerationFailure(f"Input could not be read: {path}: {error}") from error

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
        raise GenerationFailure(f"Input must contain a top-level object: {path}")

    return data


# ---------------------------------------------------------------------------
# Extractor validation
# ---------------------------------------------------------------------------


def validate_extracted(data: dict[str, Any]) -> list[Diagnostic]:
    """Validate the structure of the extractor output."""

    diagnostics: list[Diagnostic] = []

    if data.get("format_version") != EXTRACTOR_FORMAT_VERSION:
        diagnostics.append(
            make_diagnostic(
                ERROR, "UNSUPPORTED_FORMAT_VERSION", "Expected format_version 1."
            )
        )
    if data.get("extraction_stage") != EXTRACTOR_STAGE:
        diagnostics.append(
            make_diagnostic(
                ERROR,
                "UNEXPECTED_EXTRACTION_STAGE",
                f"Expected extraction_stage '{EXTRACTOR_STAGE}'.",
            )
        )
    if data.get("diagnostics") != []:
        diagnostics.append(
            make_diagnostic(
                ERROR,
                "EXTRACTOR_DIAGNOSTICS_PRESENT",
                "Extractor input contains diagnostics.",
            )
        )

    signals = data.get("signals")

    if not isinstance(signals, list):
        diagnostics.append(
            make_diagnostic(ERROR, "INVALID_SIGNALS", "signals must be an array.")
        )
        return diagnostics

    constraints = data.get("constraints")

    if not isinstance(constraints, list):
        diagnostics.append(
            make_diagnostic(
                ERROR,
                "INVALID_GLOBAL_CONSTRAINTS",
                "constraints must be an array.",
            )
        )
        constraints = []

    signal_names = {
        signal.get("name")
        for signal in signals
        if isinstance(signal, dict) and is_name(signal.get("name"))
    }
    diagnostics += validate_global_constraints(constraints, signal_names)

    seen_names: set[str] = set()
    for signal in signals:
        diagnostics += validate_signal(signal, seen_names)

    return diagnostics


def validate_global_constraints(
    constraints: list[Any],
    signal_names: set[str],
) -> list[Diagnostic]:
    """Validate global constraints and their input references."""

    diagnostics: list[Diagnostic] = []

    for constraint in constraints:
        if (
            not isinstance(constraint, dict)
            or constraint.get("kind") not in GLOBAL_CONSTRAINT_KINDS
        ):
            diagnostics.append(
                make_diagnostic(
                    ERROR,
                    "INVALID_GLOBAL_CONSTRAINT",
                    "Global constraint is invalid.",
                )
            )
            continue

        inputs = constraint.get("inputs")

        if not isinstance(inputs, list) or len(inputs) < 2:
            diagnostics.append(
                make_diagnostic(
                    ERROR,
                    "INVALID_GLOBAL_CONSTRAINT_INPUTS",
                    "Global constraint inputs are invalid.",
                )
            )
            continue

        diagnostics.extend(
            make_diagnostic(
                ERROR,
                "UNDEFINED_GLOBAL_CONSTRAINT_INPUT",
                f"Global constraint input {name!r} is undefined.",
                referenced_input=as_reference(name),
                source=constraint.get("source"),
            )
            for name in inputs
            if not isinstance(name, Hashable) or name not in signal_names
        )

    return diagnostics


def validate_signal(signal: Any, seen_names: set[str]) -> list[Diagnostic]:
    """Validate one extracted signal; record its name in ``seen_names``."""

    if not isinstance(signal, dict):
        return [make_diagnostic(ERROR, "INVALID_SIGNAL", "Signal must be an object.")]

    name = signal.get("name")
    source = signal.get("definition_source")

    if not is_name(name):
        return [
            make_diagnostic(
                ERROR,
                "INVALID_SIGNAL_NAME",
                "Signal name must be non-empty.",
                source=source,
            )
        ]

    diagnostics: list[Diagnostic] = []

    def report(code: str, message: str, location: Any = source) -> None:
        diagnostics.append(
            make_diagnostic(ERROR, code, message, input_name=name, source=location)
        )

    if name in seen_names:
        report("DUPLICATE_SIGNAL", f"Signal {name!r} appears more than once.")
    seen_names.add(name)

    if signal.get("extraction_status") != VALIDATED_STATUS:
        report("INVALID_EXTRACTION_STATUS", "Signal is not structure-validated.")

    bit_width = signal.get("bit_width")
    if not isinstance(bit_width, int) or bit_width <= 0:
        report("INVALID_BIT_WIDTH", "bit_width must be a positive integer.")

    values = signal.get("enumerated_values")
    if isinstance(values, list):
        seen_values: set[str] = set()
        for value in values:
            if not isinstance(value, dict) or not isinstance(value.get("value"), str):
                report(
                    "INVALID_ENUMERATED_VALUE",
                    "Enumerated value must be an object with a string value.",
                )
                continue
            if value["value"] in seen_values:
                report(
                    "DUPLICATE_ENUMERATED_VALUE",
                    f"Value {value['value']!r} appears more than once.",
                    value.get("source") or source,
                )
            seen_values.add(value["value"])
    else:
        report("INVALID_ENUMERATED_VALUES", "enumerated_values must be an array.")

    if not isinstance(signal.get("value_ranges"), list):
        report("INVALID_VALUE_RANGES", "value_ranges must be an array.")

    if not isinstance(signal.get("dependencies"), list):
        report("INVALID_DEPENDENCIES", "dependencies must be an array.")

    if not (
        isinstance(source, dict)
        and isinstance(source.get("path"), str)
        and isinstance(source.get("heading"), str)
        and isinstance(source.get("line"), int)
    ):
        report("INVALID_DEFINITION_SOURCE", "definition_source is invalid.", None)

    return diagnostics


# ---------------------------------------------------------------------------
# Maintained schema validation
# ---------------------------------------------------------------------------


def is_valid_control_uses(uses: Any) -> bool:
    """Return whether ``uses`` is a list of distinct known control uses."""

    return (
        isinstance(uses, list)
        and all(isinstance(use, str) and use in CONTROL_USES for use in uses)
        and len(uses) == len(set(uses))
    )


def validate_maintained(
    data: dict[str, Any] | None,
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the maintained schema and index its fields by name.

    A missing schema (None) is valid and has no fields.
    """

    if data is None:
        return [], {}

    diagnostics: list[Diagnostic] = []

    if data.get("specification_type") != SCHEMA_TYPE:
        diagnostics.append(
            make_diagnostic(
                ERROR, "INVALID_SCHEMA_TYPE", "Expected control-input-schema."
            )
        )
    if data.get("schema_version") != SCHEMA_VERSION:
        diagnostics.append(
            make_diagnostic(
                ERROR, "UNSUPPORTED_SCHEMA_VERSION", "Expected schema_version 1."
            )
        )
    if data.get("control_design_version") != CONTROL_DESIGN_VERSION:
        diagnostics.append(
            make_diagnostic(
                ERROR,
                "CONTROL_DESIGN_VERSION_MISMATCH",
                "Expected control_design_version v1.",
            )
        )

    fields = data.get("fields")

    if not isinstance(fields, list):
        diagnostics.append(
            make_diagnostic(ERROR, "INVALID_FIELDS", "fields must be an array.")
        )
        return diagnostics, {}

    fields_by_name: dict[str, dict[str, Any]] = {}

    for field in fields:
        if not isinstance(field, dict):
            diagnostics.append(
                make_diagnostic(
                    ERROR, "INVALID_FIELD", "Maintained field must be an object."
                )
            )
            continue

        name = field.get("name")

        if not is_name(name):
            diagnostics.append(
                make_diagnostic(
                    ERROR,
                    "INVALID_FIELD_NAME",
                    "Maintained field name must be non-empty.",
                )
            )
            continue

        if name in fields_by_name:
            diagnostics.append(
                make_diagnostic(
                    ERROR,
                    "DUPLICATE_MAINTAINED_FIELD",
                    f"Maintained field {name!r} appears more than once.",
                    input_name=name,
                )
            )
        fields_by_name[name] = field

        if not is_valid_control_uses(field.get("control_uses")):
            diagnostics.append(
                make_diagnostic(
                    ERROR,
                    "INVALID_CONTROL_USES",
                    "control_uses must contain unique predicate/value entries.",
                    input_name=name,
                )
            )

    return diagnostics, fields_by_name


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


def field_from_signal(signal: dict[str, Any], uses: list[str]) -> dict[str, Any]:
    """Build one candidate field from an extracted signal.

    Key order is part of the output format.
    """

    logic = signal.get("logic")
    if not isinstance(logic, dict):
        logic = {}

    # The first non-empty logic section in preference order; if none is
    # non-empty, the value of the last one.
    derivation = None
    for section in DERIVATION_SECTIONS:
        derivation = logic.get(section)
        if derivation:
            break

    return {
        "name": signal["name"],
        "category": signal.get("category"),
        "width": signal["bit_width"],
        "control_uses": list(uses),
        "attributes": signal.get("attributes", {}),
        "polarity": signal.get("polarity"),
        "domain": signal.get("domain"),
        "values": signal.get("enumerated_values", []),
        "ranges": signal.get("value_ranges", []),
        "dependencies": signal.get("dependencies", []),
        "derivation": derivation,
        "constraints": signal.get("constraints", []),
        "consumers": signal.get("consumers", []),
        "sources": {
            "index": signal.get("index_source"),
            "definition": signal.get("definition_source"),
        },
    }


def find_undefined_dependencies(
    signals: list[dict[str, Any]],
    signal_names: set[str],
) -> list[Diagnostic]:
    """Report structured dependencies that name no extracted signal."""

    return [
        make_diagnostic(
            ERROR,
            "UNDEFINED_DEPENDENCY",
            f"Dependency {dependency['name']!r} is undefined.",
            input_name=signal["name"],
            referenced_input=dependency["name"],
            source=dependency.get("source"),
        )
        for signal in signals
        for dependency in signal.get("dependencies", [])
        if isinstance(dependency, dict)
        and isinstance(dependency.get("name"), str)
        and dependency["name"] not in signal_names
    ]


def build_candidate(
    extracted: dict[str, Any],
    maintained: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Build the candidate schema.

    Returns ``(None, diagnostics)`` when either input is structurally
    invalid.  Otherwise returns the candidate, whose ``diagnostics`` lists
    every finding in the order it was made.  An undefined dependency is an
    error reported after construction; the caller must not write such a
    candidate.
    """

    diagnostics = validate_extracted(extracted)
    maintained_diagnostics, maintained_fields = validate_maintained(maintained)
    diagnostics += maintained_diagnostics

    if any(diagnostic.severity in FAILURE_SEVERITIES for diagnostic in diagnostics):
        return None, diagnostics

    signals = extracted["signals"]
    signal_names = {signal["name"] for signal in signals}
    fields = []

    for signal in signals:
        maintained_field = maintained_fields.get(signal["name"])
        uses = maintained_field.get("control_uses", []) if maintained_field else []

        if not uses:
            diagnostics.append(
                make_diagnostic(
                    WARNING,
                    "CONTROL_USES_UNRESOLVED",
                    "Input has no reviewed control-use classification.",
                    input_name=signal["name"],
                    source=signal.get("definition_source"),
                )
            )

        fields.append(field_from_signal(signal, uses))

    diagnostics.extend(
        make_diagnostic(
            WARNING,
            "STALE_MAINTAINED_FIELD",
            "Maintained field is absent from current extraction.",
            input_name=name,
        )
        for name in maintained_fields
        if name not in signal_names
    )
    diagnostics += find_undefined_dependencies(signals, signal_names)

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
        "constraints": extracted.get("constraints", []),
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


def write_json(data: dict[str, Any], path: Path) -> None:
    """Write deterministic JSON."""

    write_text(path, serialize_json(data))


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
    title = "Control-Input Schema Generation Report"
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
    lines += [
        f"{item.severity} {item.code} [{item.input_name or '-'}]: {item.message}"
        for item in diagnostics
    ] or ["No diagnostics."]
    return "\n".join(lines) + "\n"


def format_failure(diagnostic: Diagnostic) -> list[str]:
    """Format one failure diagnostic for the console."""

    location = diagnostic.source_path or "<unknown source>"
    if diagnostic.source_line is not None:
        location = f"{location}:{diagnostic.source_line}"

    name = f" [{diagnostic.input_name}]" if diagnostic.input_name else ""

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
        description="Generate a candidate control-input schema for review."
    )
    parser.add_argument(
        "--repo-root", required=True, type=Path, help="Path to the repository root."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Control-input extractor JSON.",
    )
    parser.add_argument(
        "--maintained-schema",
        type=Path,
        default=DEFAULT_MAINTAINED,
        help="Maintained control-input schema; may be absent.",
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

    diagnostics: list[Diagnostic] = []
    field_count = 0
    candidate_written = False

    try:
        extracted = read_json(input_path)
        maintained = read_json(maintained_path, optional=True)
        signals = extracted.get("signals")
        field_count = len(signals) if isinstance(signals, list) else 0
        candidate, diagnostics = build_candidate(extracted, maintained)

        if candidate is not None and not any(
            item.severity in FAILURE_SEVERITIES for item in diagnostics
        ):
            write_json(candidate, candidate_path)
            candidate_written = True
    except GenerationFailure as error:
        diagnostics = [make_diagnostic(FATAL, "GENERATION_FAILURE", str(error))]

    diagnostics = sorted(diagnostics, key=diagnostic_sort_key)
    write_text(report_path, build_report(diagnostics, field_count, candidate_written))

    failures = [item for item in diagnostics if item.severity in FAILURE_SEVERITIES]
    exit_code = 1 if failures else 0

    print("Control-input schema generation")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Control inputs: {field_count}")
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
