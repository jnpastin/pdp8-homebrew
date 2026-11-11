"""Generate a candidate execution-definition artifact for review.

The generator takes the execution-definition extractor's cases, validates
their structure, compares them with the maintained artifact, and writes a
candidate plus a report. It never modifies the maintained artifact.

Pipeline:

1. Read the extracted cases and the maintained artifact if present.
2. Validate their structure. Any error stops here.
3. Report cases that are new, changed, or no longer extracted.
4. Write the candidate (only when no errors were found) and the report.

See the tool README for the validation rules.
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

DEFAULT_EXTRACTED = Path(
    "build/simulation_outputs/rom-generation/execution-definition-extractor/"
    "execution-definitions.json"
)
DEFAULT_MAINTAINED = Path("rom/microcode/v1/execution-definitions.json")

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/execution-definition-generator"
)
DEFAULT_CANDIDATE = OUTPUT_DIRECTORY / "execution-definitions.candidate.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "generation-report.txt"

# ---------------------------------------------------------------------------
# Expected inputs
# ---------------------------------------------------------------------------

ARTIFACT = "execution-definitions"
FORMAT_VERSION = 1
EXTRACTION_STAGE = "documentation-extraction"
GENERATION_STAGE = "candidate-generation"
REQUIRED_TOP_LEVEL = (
    "format_version",
    "control_design_version",
    "artifact",
    "extraction_stage",
    "cases",
    "diagnostics",
)

MAJOR_STATE_MODEL = "major-state"
CONSOLE_MODEL = "console-transaction"
TIMING_STATES = (1, 2, 3, 4)

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
    case_id: str | None = None
    field_name: str | None = None


class GenerationFailure(Exception):
    """An input could not be read; generation cannot proceed."""


def make_error(
    code: str,
    message: str,
    case_id: str | None = None,
    field_name: str | None = None,
) -> Diagnostic:
    """Build an ERROR diagnostic."""

    return Diagnostic(ERROR, code, message, case_id, field_name)


def has_failures(diagnostics: Sequence[Diagnostic]) -> bool:
    """Return whether any diagnostic prevents a candidate from being
    written."""

    return any(item.severity in FAILURE_SEVERITIES for item in diagnostics)


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.case_id or "",
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
        raise GenerationFailure(
            f"Required input does not exist: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise GenerationFailure(f"Input is not valid UTF-8: {path}") from error
    except OSError as error:
        raise GenerationFailure(
            f"Unable to read input {path}: {error}"
        ) from error

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


def index_cases(
    data: dict[str, Any], label: str, code: str
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Index an artifact's cases by id.

    ``label`` names the artifact in messages; ``code`` is the code of every
    problem found. The index is only meaningful without diagnostics.
    """

    cases = data.get("cases")
    if not isinstance(cases, list):
        return [make_error(code, f"{label} must contain a cases array.")], {}

    diagnostics = []
    index: dict[str, dict[str, Any]] = {}

    for position, item in enumerate(cases):
        if not isinstance(item, dict):
            diagnostics.append(
                make_error(code, f"{label} case {position} must be an object.")
            )
            continue
        identifier = item.get("id")
        if not isinstance(identifier, str) or not identifier:
            diagnostics.append(
                make_error(
                    code, f"{label} case {position} has no nonempty string id."
                )
            )
            continue
        if identifier in index:
            diagnostics.append(
                make_error(
                    code,
                    f"{label} contains duplicate case id {identifier}.",
                    identifier,
                )
            )
        index[identifier] = item

    return diagnostics, index


def is_text_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def is_conditional_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict)
        and list(item) == ["predicate", "micro_operation"]
        and all(isinstance(text, str) for text in item.values())
        for item in value
    )


def is_source(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("path"), str)
        and isinstance(value.get("line"), int)
    )


def case_field_problems(case: dict[str, Any]) -> list[tuple[str, str]]:
    """Return ``(field, requirement)`` for each malformed case field."""

    model = case.get("execution_model")
    timing_state = case.get("timing_state")
    if model == CONSOLE_MODEL:
        timing_valid = timing_state is None
        timing_rule = "must be null for a console transaction"
    else:
        timing_valid = (
            type(timing_state) is int and timing_state in TIMING_STATES
        )
        timing_rule = "must be 1 to 4"

    checks = (
        ("source", is_source(case.get("source")), "must be {path, line}"),
        (
            "execution_model",
            model in (MAJOR_STATE_MODEL, CONSOLE_MODEL),
            f"must be {MAJOR_STATE_MODEL!r} or {CONSOLE_MODEL!r}",
        ),
        (
            "context",
            is_text_list(case.get("context")),
            "must be an array of strings",
        ),
        ("timing_state", timing_valid, timing_rule),
        (
            "micro_operations",
            is_text_list(case.get("micro_operations")),
            "must be an array of strings",
        ),
        (
            "conditional_micro_operations",
            is_conditional_list(case.get("conditional_micro_operations")),
            "must be an array of {predicate, micro_operation} strings",
        ),
    )
    return [(field, rule) for field, valid, rule in checks if not valid]


def validate_extracted(
    data: dict[str, Any],
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the extractor output and index its cases by id."""

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
            make_error(
                "UNEXPECTED_ARTIFACT_TYPE", f"Expected artifact {ARTIFACT!r}."
            )
        )
    if "format_version" in data and data["format_version"] != FORMAT_VERSION:
        diagnostics.append(
            make_error(
                "UNSUPPORTED_FORMAT_VERSION",
                f"Expected format_version {FORMAT_VERSION}.",
            )
        )
    if (
        "extraction_stage" in data
        and data["extraction_stage"] != EXTRACTION_STAGE
    ):
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

    index_diagnostics, cases = index_cases(
        data, "Extracted artifact", "INVALID_EXTRACTED_CASES"
    )
    diagnostics += index_diagnostics

    for identifier, case in cases.items():
        for field, rule in case_field_problems(case):
            diagnostics.append(
                make_error(
                    "INVALID_CASE_FIELD",
                    f"Case {field} {rule}.",
                    identifier,
                    field,
                )
            )

    return diagnostics, cases


def validate_maintained(
    data: dict[str, Any] | None,
    extracted: dict[str, Any],
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the maintained artifact and index its cases by id.

    A missing artifact (None) is valid and has no cases.
    """

    if data is None:
        return [], {}

    diagnostics: list[Diagnostic] = []

    if data.get("control_design_version") != extracted.get(
        "control_design_version"
    ):
        diagnostics.append(
            make_error(
                "CONTROL_DESIGN_VERSION_MISMATCH",
                "Maintained and extracted artifacts have different "
                "control_design_version values.",
            )
        )

    index_diagnostics, cases = index_cases(
        data, "Maintained artifact", "INVALID_MAINTAINED_CASES"
    )
    return diagnostics + index_diagnostics, cases


# ---------------------------------------------------------------------------
# Review against the maintained artifact
# ---------------------------------------------------------------------------


def review_changes(
    extracted: dict[str, dict[str, Any]],
    maintained: dict[str, dict[str, Any]],
) -> list[Diagnostic]:
    """Warn about new, changed, and stale cases."""

    diagnostics = []

    for identifier, case in extracted.items():
        previous = maintained.get(identifier)
        if previous is None:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "NEW_CASE",
                    "Case is not present in the maintained artifact.",
                    identifier,
                )
            )
        elif previous != case:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "CHANGED_CASE",
                    "Extracted case differs from the maintained artifact.",
                    identifier,
                )
            )

    diagnostics.extend(
        Diagnostic(
            WARNING,
            "STALE_CASE",
            "Maintained case is absent from the extracted artifact.",
            identifier,
        )
        for identifier in maintained
        if identifier not in extracted
    )

    return diagnostics


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


def build_candidate(
    extracted: dict[str, Any],
    maintained: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Validate the inputs and build the candidate artifact.

    Returns ``(None, diagnostics)`` when any error is found; otherwise the
    candidate and its warnings.
    """

    diagnostics, cases = validate_extracted(extracted)
    maintained_diagnostics, maintained_cases = validate_maintained(
        maintained, extracted
    )
    diagnostics += maintained_diagnostics

    if has_failures(diagnostics):
        return None, diagnostics

    diagnostics += review_changes(cases, maintained_cases)

    candidate = {
        "format_version": extracted["format_version"],
        "control_design_version": extracted["control_design_version"],
        "artifact": ARTIFACT,
        "generation_stage": GENERATION_STAGE,
        "cases": list(cases.values()),
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
    if diagnostic.case_id:
        text += f" [{diagnostic.case_id}]"
    if diagnostic.field_name:
        text += f" [{diagnostic.field_name}]"
    return text


def build_report(
    diagnostics: Sequence[Diagnostic],
    case_count: int,
    candidate_written: bool,
) -> str:
    """Build the human-readable generation report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Execution-Definition Candidate Generation Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Cases processed: {case_count}",
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
        f"{format_heading(item)}: {item.message}" for item in diagnostics
    ] or ["No diagnostics."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate a reviewable execution-definition candidate."
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Path to the repository root.",
    )
    parser.add_argument(
        "--extracted",
        type=Path,
        default=DEFAULT_EXTRACTED,
        help="Execution-definition extractor JSON.",
    )
    parser.add_argument(
        "--maintained",
        type=Path,
        default=DEFAULT_MAINTAINED,
        help="Maintained execution-definition artifact; may be absent.",
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
    candidate_path = resolve_from_repo(root, options.candidate_output)
    report_path = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs(
            (candidate_path, report_path), (extracted_path, maintained_path)
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    diagnostics: list[Diagnostic] = []
    case_count = 0
    candidate_written = False

    try:
        extracted = read_json(extracted_path)
        maintained = read_json(maintained_path, optional=True)
        cases = extracted.get("cases")
        case_count = len(cases) if isinstance(cases, list) else 0
        candidate, diagnostics = build_candidate(extracted, maintained)

        if candidate is not None:
            write_text(candidate_path, serialize_json(candidate))
            candidate_written = True
    except GenerationFailure as error:
        diagnostics = [Diagnostic(FATAL, "GENERATION_FAILURE", str(error))]

    diagnostics = sorted(diagnostics, key=diagnostic_sort_key)
    write_text(
        report_path, build_report(diagnostics, case_count, candidate_written)
    )

    failures = [
        item for item in diagnostics if item.severity in FAILURE_SEVERITIES
    ]
    exit_code = 1 if failures else 0

    print("Execution-definition candidate generation")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Cases: {case_count}")
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
