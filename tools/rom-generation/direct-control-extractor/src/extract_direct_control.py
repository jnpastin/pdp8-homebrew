"""Extract direct-control definitions from the authoritative documentation.

The extractor reads the two direct-control documents and produces
deterministic JSON plus a human-readable report.

Pipeline:

1. Read both documents.
2. Find the numbered headings. Each numbered heading without a deeper
   heading under it is a candidate definition.
3. Split the candidate's text into labeled sections, such as
   ``Applicable context:`` and ``Assignment:``.
4. Keep the candidates that have a control or ownership section, reading
   each section's code blocks, bullets, or links.
5. Report unstructured, empty, and duplicated definitions.
6. Write the JSON result and the extraction report.

See the tool README for the document conventions and output format.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SOURCE_DIRECTORY = Path("docs/04-control/30-direct-control-definitions")
SOURCE_PATHS = (
    SOURCE_DIRECTORY / "01-sequencing-and-internal-control.md",
    SOURCE_DIRECTORY / "02-interface-and-ownership-control.md",
)

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/direct-control-extractor"
)
DEFAULT_JSON_OUTPUT = OUTPUT_DIRECTORY / "direct-control-definitions.json"
DEFAULT_REPORT_OUTPUT = OUTPUT_DIRECTORY / "extraction-report.txt"

# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

FORMAT_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"
ARTIFACT = "direct-control-definitions"
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
# Document structure
# ---------------------------------------------------------------------------

# Section labels, each alone on a line ending in a colon, and the output
# field each fills.
SECTION_LABELS = {
    "Applicable context": "applicable_context",
    "Assignment": "direct_assignments",
    "Assignments": "direct_assignments",
    "Micro-operation assignments": "micro_operation_assignments",
    "Logical control results": "micro_operation_assignments",
    "Control-supplied value": "control_supplied_values",
    "Control-supplied values": "control_supplied_values",
    "Value relationship": "value_relationships",
    "Value relationships": "value_relationships",
    "Widths": "widths",
    "Commit": "state_commits",
    "Commits": "state_commits",
    "Constraint": "constraints",
    "Constraints": "constraints",
    "Source": "sources",
    "Sources": "sources",
    "CPU output-drive state": "drive_states",
    "CPU output-drive states": "drive_states",
    "CPU behavior": "drive_states",
    "External ownership": "external_ownership",
    "Memory behavior": "memory_behavior",
    "Related derived values": "derived_values",
}

# Within an applicable context, this label separates alternative context
# blocks instead of ending the section.
CONTEXT_SEPARATOR = "or"

# Fields read from text code blocks; a section without one is an error,
# except that applicable context falls back to its prose.
CODE_FIELDS = (
    "applicable_context",
    "direct_assignments",
    "control_supplied_values",
    "micro_operation_assignments",
    "state_commits",
    "value_relationships",
    "widths",
    "drive_states",
    "external_ownership",
    "memory_behavior",
    "derived_values",
)

# A heading is a definition only if it has at least one of these sections,
# and must then produce at least one non-empty value from them.
CONTENT_FIELDS = (
    "direct_assignments",
    "control_supplied_values",
    "micro_operation_assignments",
    "state_commits",
    "drive_states",
    "external_ownership",
    "memory_behavior",
    "derived_values",
)

# Output fields of a definition, in output order.
DEFINITION_FIELDS = (
    "applicable_context",
    "direct_assignments",
    "control_supplied_values",
    "micro_operation_assignments",
    "state_commits",
    "value_relationships",
    "widths",
    "constraints",
    "sources",
    "drive_states",
    "external_ownership",
    "memory_behavior",
    "derived_values",
)

# ---------------------------------------------------------------------------
# Markdown syntax
# ---------------------------------------------------------------------------

HEADING_PATTERN = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
NUMBERED_TITLE_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$")
LABEL_PATTERN = re.compile(r"^([^#`|].*?):\s*$")
CODE_FENCE = "```"
CODE_BLOCK_PATTERN = re.compile(r"```(?:text)?\s*\n(.*?)\n```", re.DOTALL)
LINK_PATTERN = re.compile(r"\[([^]]+)\]\(([^)]+)\)")
BULLET_PATTERN = re.compile(r"^\s*-\s+(.+?)\s*$")

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
    definition_id: str | None = None


@dataclass(frozen=True)
class Heading:
    """One Markdown heading; ``number`` is None for unnumbered headings."""

    level: int
    number: str | None
    title: str
    line: int

    @property
    def full_title(self) -> str:
        if self.number is None:
            return self.title
        return f"{self.number} {self.title}"


class ExtractionFailure(Exception):
    """A source document could not be read."""


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.source_path,
        diagnostic.line if diagnostic.line is not None else -1,
        diagnostic.definition_id or "",
        diagnostic.message,
    )


# ---------------------------------------------------------------------------
# Headings
# ---------------------------------------------------------------------------


def parse_headings(lines: Sequence[str]) -> list[Heading]:
    """Return the level 2 to 6 headings outside code blocks."""

    headings = []
    in_code_block = False

    for line_number, line in enumerate(lines, 1):
        if line.startswith(CODE_FENCE):
            in_code_block = not in_code_block
            continue
        match = None if in_code_block else HEADING_PATTERN.match(line)
        if match is None:
            continue
        title = match.group(2)
        numbered = NUMBERED_TITLE_PATTERN.match(title)
        headings.append(
            Heading(
                level=len(match.group(1)),
                number=numbered.group(1) if numbered else None,
                title=numbered.group(2) if numbered else title,
                line=line_number,
            )
        )

    return headings


def heading_body(
    lines: Sequence[str], headings: Sequence[Heading], index: int
) -> list[str]:
    """Return the lines after a heading, up to the next heading at or above
    its level."""

    heading = headings[index]
    end = len(lines) + 1
    for later in headings[index + 1 :]:
        if later.level <= heading.level:
            end = later.line
            break
    return list(lines[heading.line : end - 1])


def has_child_heading(headings: Sequence[Heading], index: int) -> bool:
    """Return whether the next heading is nested under this one."""

    following = headings[index + 1 : index + 2]
    return bool(following) and following[0].level > headings[index].level


def parent_title(headings: Sequence[Heading], index: int) -> str | None:
    """Return the full title of the nearest enclosing heading."""

    level = headings[index].level
    for earlier in reversed(headings[:index]):
        if earlier.level < level:
            return earlier.full_title
    return None


def definition_id(source_path: str, heading: Heading) -> str:
    """Return the id of a numbered heading: the file's numeric prefix and
    the heading number, such as ``01:3.2.1``."""

    prefix = Path(source_path).stem.split("-", 1)[0]
    return f"{prefix}:{heading.number}"


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def collect_sections(lines: Sequence[str]) -> dict[str, list[str]]:
    """Group a definition's lines into labeled sections.

    A section starts at a recognized label line and runs to the next line
    that looks like a label: any line outside a code block that ends in a
    colon. An unrecognized label, usually explanatory prose, ends the
    section without starting another. The exception is ``or:``, which
    separates alternative context blocks within an applicable context.
    Each occurrence of a label adds one text to its field.
    """

    sections: dict[str, list[str]] = {}
    current: str | None = None
    buffer: list[str] = []
    in_code_block = False

    def close() -> None:
        text = "\n".join(buffer).strip()
        if current is not None and text:
            sections.setdefault(current, []).append(text)
        buffer.clear()

    for line in lines:
        if line.startswith(CODE_FENCE):
            in_code_block = not in_code_block
        elif not in_code_block and (label := LABEL_PATTERN.match(line)):
            separator = label.group(1).strip().casefold() == CONTEXT_SEPARATOR
            if not (current == "applicable_context" and separator):
                close()
                current = SECTION_LABELS.get(label.group(1))
                continue
        if current is not None:
            buffer.append(line)

    close()
    return sections


def code_blocks(texts: Iterable[str]) -> list[str]:
    """Return the non-empty text code blocks in ``texts``."""

    return [
        block.strip()
        for text in texts
        for block in CODE_BLOCK_PATTERN.findall(text)
        if block.strip()
    ]


def bullet_items(texts: Iterable[str]) -> list[str]:
    """Return the text of every ``- `` bullet, including nested ones."""

    return [
        match.group(1)
        for text in texts
        for line in text.splitlines()
        if (match := BULLET_PATTERN.match(line))
    ]


def markdown_links(texts: Iterable[str]) -> list[dict[str, str]]:
    """Return every Markdown link as ``{"label", "target"}``."""

    return [
        {"label": label, "target": target.strip()}
        for text in texts
        for label, target in LINK_PATTERN.findall(text)
    ]


# ---------------------------------------------------------------------------
# Definitions
# ---------------------------------------------------------------------------


def extract_definition(
    heading: Heading,
    group: str | None,
    sections: dict[str, list[str]],
    source_path: str,
) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Build one definition from its sections. Key order is the format."""

    identifier = definition_id(source_path, heading)
    values: dict[str, list] = {}
    diagnostics = []

    for field in CODE_FIELDS:
        texts = sections.get(field, [])
        values[field] = code_blocks(texts)
        if not texts or values[field]:
            continue
        if field == "applicable_context":
            values[field] = ["\n".join(texts).strip()]
            continue
        diagnostics.append(
            Diagnostic(
                ERROR,
                "UNSTRUCTURED_FIELD",
                f"The '{field}' section must contain a text code block.",
                source_path,
                heading.line,
                identifier,
            )
        )

    values["constraints"] = bullet_items(sections.get("constraints", []))
    values["sources"] = markdown_links(sections.get("sources", []))

    definition = {
        "id": identifier,
        "title": heading.full_title,
        "group": group,
        "source": {"path": source_path, "line": heading.line},
        **{field: values[field] for field in DEFINITION_FIELDS},
    }

    if not any(definition[field] for field in CONTENT_FIELDS):
        diagnostics.append(
            Diagnostic(
                ERROR,
                "EMPTY_DEFINITION",
                "Definition contains no extractable control or ownership "
                "result.",
                source_path,
                heading.line,
                identifier,
            )
        )

    return definition, diagnostics


def extract_document(
    text: str, source_path: str
) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    """Extract every definition in one document, in document order."""

    lines = text.splitlines()
    headings = parse_headings(lines)
    definitions = []
    diagnostics = []

    for index, heading in enumerate(headings):
        if heading.number is None or has_child_heading(headings, index):
            continue
        sections = collect_sections(heading_body(lines, headings, index))
        if not any(field in sections for field in CONTENT_FIELDS):
            continue
        definition, found = extract_definition(
            heading, parent_title(headings, index), sections, source_path
        )
        definitions.append(definition)
        diagnostics += found

    return definitions, diagnostics


def find_duplicate_ids(
    definitions: Sequence[dict[str, Any]],
) -> list[Diagnostic]:
    """Report each definition whose id was already used."""

    diagnostics = []
    seen: set[str] = set()

    for definition in definitions:
        identifier = definition["id"]
        if identifier in seen:
            diagnostics.append(
                Diagnostic(
                    ERROR,
                    "DUPLICATE_DEFINITION_ID",
                    f"Duplicate definition id: {identifier}",
                    definition["source"]["path"],
                    definition["source"]["line"],
                    identifier,
                )
            )
        seen.add(identifier)

    return diagnostics


def extract_direct_control(
    documents: Sequence[tuple[str, str]],
) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    """Extract all documents, given as ``(source_path, text)`` pairs.

    Returns the definitions in document order and the sorted diagnostics.
    """

    definitions: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []

    for source_path, text in documents:
        found_definitions, found = extract_document(text, source_path)
        definitions += found_definitions
        diagnostics += found

    diagnostics += find_duplicate_ids(definitions)
    return definitions, sorted(diagnostics, key=diagnostic_sort_key)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def build_json_result(
    source_paths: Sequence[str],
    definitions: Sequence[dict[str, Any]],
    diagnostics: Sequence[Diagnostic],
) -> dict[str, Any]:
    """Return the complete JSON document."""

    return {
        "format_version": FORMAT_VERSION,
        "control_design_version": CONTROL_DESIGN_VERSION,
        "artifact": ARTIFACT,
        "extraction_stage": EXTRACTION_STAGE,
        "sources": list(source_paths),
        "definitions": list(definitions),
        "diagnostics": [asdict(item) for item in diagnostics],
    }


def serialize_json(data: dict[str, Any]) -> str:
    """Serialize JSON preserving key order, with a trailing newline."""

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def format_location(diagnostic: Diagnostic) -> str:
    if diagnostic.line is None:
        return diagnostic.source_path
    return f"{diagnostic.source_path}:{diagnostic.line}"


def build_report(
    diagnostics: Sequence[Diagnostic], definition_count: int
) -> str:
    """Build the human-readable extraction report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Direct-Control Extraction Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Definitions extracted: {definition_count}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    for item in diagnostics:
        identifier = f" [{item.definition_id}]" if item.definition_id else ""
        lines.append(
            f"{item.severity} {item.code}{identifier} "
            f"{format_location(item)}: {item.message}"
        )
    if not diagnostics:
        lines.append("No diagnostics.")
    return "\n".join(lines) + "\n"


def format_failure(diagnostic: Diagnostic) -> list[str]:
    """Format one failure diagnostic for the console."""

    return [
        f"{diagnostic.severity} {diagnostic.code}",
        f"  Source: {format_location(diagnostic)}",
        f"  {diagnostic.message}",
    ]


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract direct-control definitions from authoritative "
            "documentation."
        )
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
    """Read a source document, raising ``ExtractionFailure`` on failure."""

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
    source_paths = [path.as_posix() for path in SOURCE_PATHS]
    sources = [resolve_from_repo(root, path) for path in SOURCE_PATHS]
    json_output = resolve_from_repo(root, options.json_output)
    report_output = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs((json_output, report_output), sources)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    definitions: list[dict[str, Any]] = []

    try:
        texts = [read_source(path) for path in sources]
    except ExtractionFailure as error:
        diagnostics = [
            Diagnostic(FATAL, "EXTRACTION_FAILURE", str(error), "<input>")
        ]
    else:
        definitions, diagnostics = extract_direct_control(
            list(zip(source_paths, texts, strict=True))
        )
        write_text(
            json_output,
            serialize_json(
                build_json_result(source_paths, definitions, diagnostics)
            ),
        )

    write_text(report_output, build_report(diagnostics, len(definitions)))

    failures = [
        item for item in diagnostics if item.severity in FAILURE_SEVERITIES
    ]
    exit_code = 1 if failures else 0

    print("Direct-control extraction")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Definitions: {len(definitions)}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"JSON output: {json_output}")
    print(f"Report output: {report_output}")

    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            print("\n".join(format_failure(item)))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
