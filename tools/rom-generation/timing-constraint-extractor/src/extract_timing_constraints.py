"""Extract machine-readable timing constraints from the timing document.

A timing constraint is a bullet that is entirely a code span of the form
``REQUIREMENT IF CONDITION``, under a timing-state heading such as
``#### 5.2.5 TS3``. It states that whenever its context holds, the
requirement must hold too.

Pipeline:

1. Read the major-state timing document.
2. Find the headings, and each heading's ``Applicable context:`` block.
3. For each constraint bullet, take its timing state from the enclosing
   heading and its scope from the nearest enclosing ``Applicable context``.
4. Report constraints that are malformed, outside a timing state, or
   without a scope, and repeated ids.
5. Write the JSON result and the extraction report.

See the tool README for the document conventions and output format.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SOURCE_PATH = Path("docs/09-timing/03-major-state-timing.md")

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/timing-constraint-extractor"
)
DEFAULT_JSON_OUTPUT = OUTPUT_DIRECTORY / "timing-constraints.json"
DEFAULT_REPORT_OUTPUT = OUTPUT_DIRECTORY / "extraction-report.txt"

# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

FORMAT_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"
ARTIFACT = "timing-constraints"
EXTRACTION_STAGE = "documentation-extraction"

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

# ---------------------------------------------------------------------------
# Document syntax
# ---------------------------------------------------------------------------

HEADING_PATTERN = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
NUMBERED_TITLE_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$")
TIMING_STATE_TITLE_PATTERN = re.compile(r"^TS([1-4])\b")
CODE_FENCE = "```"
SCOPE_LABEL = "Applicable context:"

# A bullet that is a single code span containing `` IF `` is a constraint.
CODE_SPAN_BULLET_PATTERN = re.compile(r"^\s*-\s+`([^`]*)`\s*$")
CONSTRAINT_SEPARATOR = " IF "
# Level-2 section whose constraints are state invariants: they hold in
# every timing state, so they need no TS heading and no scope.
INVARIANT_SECTION = "State Invariants"

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Diagnostic:
    """One extraction finding. Field order is the JSON key order."""

    severity: str
    code: str
    message: str
    source_path: str
    line: int | None = None
    constraint_id: str | None = None


@dataclass(frozen=True)
class Heading:
    """One Markdown heading; ``number`` is None for unnumbered headings."""

    level: int
    number: str | None
    title: str
    line: int


@dataclass
class Section:
    """A heading, its scope block if any, and its parent section."""

    heading: Heading
    parent: Section | None
    scope: list[str] | None = None
    constraint_count: int = 0


class ExtractionFailure(Exception):
    """The source document could not be read."""


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.source_path,
        diagnostic.line if diagnostic.line is not None else -1,
        diagnostic.constraint_id or "",
        diagnostic.message,
    )


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def parse_heading(line: str, line_number: int) -> Heading | None:
    match = HEADING_PATTERN.match(line)
    if match is None:
        return None
    title = match.group(2)
    numbered = NUMBERED_TITLE_PATTERN.match(title)
    return Heading(
        level=len(match.group(1)),
        number=numbered.group(1) if numbered else None,
        title=numbered.group(2) if numbered else title,
        line=line_number,
    )


def scope_of(section: Section | None) -> list[str] | None:
    """Return the nearest scope block of a section or its ancestors."""

    while section is not None:
        if section.scope is not None:
            return section.scope
        section = section.parent
    return None


def timing_state_of(section: Section | None) -> int | None:
    """Return the timing state of a ``TSn`` heading, else None."""

    if section is None:
        return None
    match = TIMING_STATE_TITLE_PATTERN.match(section.heading.title)
    return int(match.group(1)) if match else None


def invariant_section_of(section: Section | None) -> Section | None:
    """Return the enclosing State Invariants section, if any."""

    while section is not None:
        if (
            section.heading.level == 2
            and section.heading.title == INVARIANT_SECTION
        ):
            return section
        section = section.parent
    return None


def extract_constraints(
    text: str, source_path: str
) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    """Extract every constraint in document order.

    Returns the constraints and the sorted diagnostics.
    """

    lines = text.splitlines()
    constraints: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    section: Section | None = None
    in_code_block = False
    scope_label_at: int | None = None
    scope_lines: list[str] = []

    def error(
        code: str, message: str, line: int, constraint_id: str | None = None
    ) -> None:
        diagnostics.append(
            Diagnostic(ERROR, code, message, source_path, line, constraint_id)
        )

    def missing_block() -> None:
        error(
            "MISSING_CODE_BLOCK",
            f"'{SCOPE_LABEL}' must be followed by a non-empty text code "
            "block.",
            scope_label_at,
        )

    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()

        if stripped.startswith(CODE_FENCE):
            if in_code_block and scope_label_at is not None:
                if scope_lines:
                    section.scope = scope_lines
                else:
                    missing_block()
                scope_label_at = None
            in_code_block = not in_code_block
            scope_lines = []
            continue
        if in_code_block:
            if stripped:
                scope_lines.append(stripped)
            continue
        if scope_label_at is not None and stripped:
            missing_block()
            scope_label_at = None

        if heading := parse_heading(line, line_number):
            while (
                section is not None and section.heading.level >= heading.level
            ):
                section = section.parent
            section = Section(heading, section)
            continue

        if stripped == SCOPE_LABEL and section is not None:
            if section.scope is not None:
                error(
                    "DUPLICATE_SCOPE",
                    f"A section may have only one '{SCOPE_LABEL}' block.",
                    line_number,
                )
            scope_label_at = line_number
            continue

        bullet = CODE_SPAN_BULLET_PATTERN.match(line)
        if bullet is None or CONSTRAINT_SEPARATOR not in bullet.group(1):
            continue
        requirement, condition = (
            part.strip()
            for part in bullet.group(1).split(CONSTRAINT_SEPARATOR, 1)
        )

        if invariant_section_of(section) is not None:
            section.constraint_count += 1
            constraint_id = (
                f"invariant:{section.heading.number}."
                f"{section.constraint_count}"
            )
            if not requirement or not condition:
                error(
                    "MALFORMED_CONSTRAINT",
                    "Constraint must be 'REQUIREMENT IF CONDITION'.",
                    line_number,
                    constraint_id,
                )
                continue
            scope = scope_of(section) or []
            constraints.append(
                {
                    "id": constraint_id,
                    "context": " AND ".join([*scope, f"({condition})"]),
                    "requirement": requirement,
                    "source": {"path": source_path, "line": line_number},
                }
            )
            continue

        timing_state = timing_state_of(section)
        if timing_state is None:
            error(
                "MISSING_TIMING_CONTEXT",
                "Constraint is not directly under a TS1 to TS4 heading.",
                line_number,
            )
            continue
        section.constraint_count += 1
        constraint_id = (
            f"timing:{section.heading.number}.{section.constraint_count}"
        )

        if not requirement or not condition:
            error(
                "MALFORMED_CONSTRAINT",
                "Constraint must be 'REQUIREMENT IF CONDITION'.",
                line_number,
                constraint_id,
            )
            continue
        scope = scope_of(section)
        if scope is None:
            error(
                "MISSING_SCOPE",
                f"No enclosing section has an '{SCOPE_LABEL}' block.",
                line_number,
                constraint_id,
            )
            continue

        constraints.append(
            {
                "id": constraint_id,
                "context": " AND ".join(
                    [*scope, f"TS = {timing_state}", f"({condition})"]
                ),
                "requirement": requirement,
                "source": {"path": source_path, "line": line_number},
            }
        )

    if scope_label_at is not None:
        missing_block()

    seen: set[str] = set()
    for constraint in constraints:
        if constraint["id"] in seen:
            error(
                "DUPLICATE_CONSTRAINT_ID",
                f"Duplicate constraint id: {constraint['id']}",
                constraint["source"]["line"],
                constraint["id"],
            )
        seen.add(constraint["id"])

    if not constraints and not diagnostics:
        diagnostics.append(
            Diagnostic(
                ERROR,
                "NO_CONSTRAINTS_FOUND",
                "No timing constraints found.",
                source_path,
            )
        )

    return constraints, sorted(diagnostics, key=diagnostic_sort_key)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def build_json_result(
    constraints: Sequence[dict[str, Any]],
    diagnostics: Sequence[Diagnostic],
) -> dict[str, Any]:
    """Return the complete JSON document."""

    return {
        "format_version": FORMAT_VERSION,
        "control_design_version": CONTROL_DESIGN_VERSION,
        "artifact": ARTIFACT,
        "extraction_stage": EXTRACTION_STAGE,
        "sources": [SOURCE_PATH.as_posix()],
        "constraints": list(constraints),
        "diagnostics": [asdict(item) for item in diagnostics],
    }


def serialize_json(data: dict[str, Any]) -> str:
    """Serialize JSON preserving key order, with a trailing newline."""

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def format_location(diagnostic: Diagnostic) -> str:
    if diagnostic.line is None:
        return diagnostic.source_path
    return f"{diagnostic.source_path}:{diagnostic.line}"


def format_heading(diagnostic: Diagnostic) -> str:
    identifier = (
        f" [{diagnostic.constraint_id}]" if diagnostic.constraint_id else ""
    )
    return f"{diagnostic.severity} {diagnostic.code}{identifier}"


def build_report(
    diagnostics: Sequence[Diagnostic], constraint_count: int
) -> str:
    """Build the human-readable extraction report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Timing-Constraint Extraction Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Constraints extracted: {constraint_count}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    lines += [
        f"{format_heading(item)} {format_location(item)}: {item.message}"
        for item in diagnostics
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
        description="Extract timing constraints from the timing document."
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Path to the repository root.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="Extracted JSON output path.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help="Extraction report output path.",
    )
    return parser.parse_args(arguments)


def resolve_from_repo(root: Path, path: Path) -> Path:
    """Resolve a relative path from the repository root."""

    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_source(path: Path) -> str:
    """Read the source document, raising ``ExtractionFailure`` on failure."""

    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ExtractionFailure(
            f"Required source does not exist: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise ExtractionFailure(
            f"Source is not valid UTF-8: {path}"
        ) from error
    except OSError as error:
        raise ExtractionFailure(
            f"Unable to read source {path}: {error}"
        ) from error


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


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the extractor; return 1 if any error-level diagnostic exists.

    Relative paths are resolved from the repository root.
    """

    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    source = resolve_from_repo(root, SOURCE_PATH)
    json_output = resolve_from_repo(root, options.json_output)
    report_output = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs((json_output, report_output), (source,))
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    constraints: list[dict[str, Any]] = []

    try:
        text = read_source(source)
    except ExtractionFailure as error:
        diagnostics = [
            Diagnostic(FATAL, "EXTRACTION_FAILURE", str(error), "<input>")
        ]
    else:
        constraints, diagnostics = extract_constraints(
            text, SOURCE_PATH.as_posix()
        )
        write_text(
            json_output,
            serialize_json(build_json_result(constraints, diagnostics)),
        )

    write_text(report_output, build_report(diagnostics, len(constraints)))

    failures = [
        item for item in diagnostics if item.severity in FAILURE_SEVERITIES
    ]
    exit_code = 1 if failures else 0

    print("Timing-constraint extraction")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Constraints: {len(constraints)}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"JSON output: {json_output}")
    print(f"Report output: {report_output}")

    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            print(format_heading(item))
            print(f"  Source: {format_location(item)}")
            print(f"  {item.message}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
