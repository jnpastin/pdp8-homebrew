"""Extract micro-operation definitions from project documentation.

The extractor reads the authoritative micro-operation catalog and produces
deterministic JSON plus a human-readable report.

Pipeline:

1. Read the catalog document.
2. Find the definition section and split it into one block per heading.
3. Group each block's lines under their bold labels.
4. Read each micro-operation's attributes and lists from those groups,
   reporting missing, empty, and duplicated attributes.
5. Write the JSON result and the extraction report.

See the tool README for the extraction and validation boundary.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SOURCE_PATH = Path("docs/03-microarchitecture/02-micro-operations.md")

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/micro-operation-extractor"
)
DEFAULT_JSON_OUTPUT = OUTPUT_DIRECTORY / "micro-operations.json"
DEFAULT_REPORT_OUTPUT = OUTPUT_DIRECTORY / "extraction-report.txt"

# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

FORMAT_VERSION = 1
EXTRACTION_STAGE = "definition-validation"
STATUS_VALIDATED = "definition-validated"
STATUS_ERROR = "definition-error"

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

# Heading text of the definition section, without its section number.
DEFINITION_SECTION_TITLE = "μop Definitions (Alphabetical)"

# Single-valued attributes, all required, in the order they are checked.
SCALAR_LABELS = ("category", "description", "target", "expression", "sources")

# Attributes holding a list of text entries; optional and repeatable.
LIST_LABELS = ("preconditions", "constraints")

# Sources values that document an empty source list.
EMPTY_SOURCE_VALUES = frozenset({"none", "(none)"})

HORIZONTAL_RULE = "---"

# ---------------------------------------------------------------------------
# Markdown syntax
# ---------------------------------------------------------------------------

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SECTION_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
CODE_FENCE_PATTERN = re.compile(r"\s*`{3,}[A-Za-z0-9_-]*\s*")
LABEL_PATTERN = re.compile(r"^\s*\*\*([^*]+):\*\*\s*(.*)$")
LIST_ITEM_PATTERN = re.compile(r"^\s*-\s+(.+?)\s*$")
INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
MARKDOWN_ESCAPES = (("\\_", "_"), ("\\<", "<"), ("\\>", ">"))

# Splits a line before each recognized label, so that several labels may
# share one line.
LABEL_START_PATTERN = re.compile(
    r"(?=\*\*(?:"
    + "|".join(re.escape(label) for label in SCALAR_LABELS + LIST_LABELS)
    + r"):\*\*)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Diagnostic:
    """One extraction finding."""

    severity: str
    code: str
    message: str
    source_path: str
    line: int | None = None
    micro_operation: str | None = None


@dataclass(frozen=True)
class DefinitionBlock:
    """The lines under one micro-operation heading.

    ``lines`` holds ``(source_line, text)`` pairs, excluding the heading.
    """

    name: str
    source_path: str
    start_line: int
    lines: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class LabeledSection:
    """The lines following one bold label, up to the next recognized label.

    ``inline`` is the text after the label on the label's own line.
    """

    label: str
    line: int
    inline: str
    lines: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class TextEntry:
    """One precondition or constraint."""

    text: str
    line: int


@dataclass(frozen=True)
class MicroOperation:
    """One extracted micro-operation."""

    name: str
    source_path: str
    line: int
    category: str
    description: str
    targets: list[str]
    expression: list[str]
    sources: list[str]
    preconditions: list[TextEntry]
    constraints: list[TextEntry]
    status: str = STATUS_VALIDATED


@dataclass(frozen=True)
class ExtractionResult:
    """Everything extracted from the catalog, with sorted diagnostics."""

    source_path: str
    micro_operations: list[MicroOperation]
    diagnostics: list[Diagnostic]

    @property
    def failed(self) -> bool:
        return any(
            item.severity in FAILURE_SEVERITIES for item in self.diagnostics
        )


class ExtractionFailure(Exception):
    """The source document could not be read."""


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.source_path,
        diagnostic.line if diagnostic.line is not None else -1,
        diagnostic.micro_operation or "",
        diagnostic.message,
    )


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def normalize_markdown_text(value: str) -> str:
    """Remove Markdown escapes and inline-code markers."""

    for escaped, plain in MARKDOWN_ESCAPES:
        value = value.replace(escaped, plain)
    return INLINE_CODE_PATTERN.sub(r"\1", value)


def is_code_fence(line: str) -> bool:
    """Return whether ``line`` opens or closes a fenced code block."""

    return CODE_FENCE_PATTERN.fullmatch(line) is not None


def remove_section_number(heading: str) -> str:
    """Remove an optional numeric prefix such as ``5.`` or ``5.1``."""

    return SECTION_NUMBER_PATTERN.sub("", heading)


def find_headings(lines: Sequence[str]) -> list[tuple[int, int, str]]:
    """Return ``(index, level, text)`` for each heading outside code fences."""

    headings = []
    in_fence = False

    for index, line in enumerate(lines):
        if is_code_fence(line):
            in_fence = not in_fence
            continue
        match = None if in_fence else HEADING_PATTERN.match(line)
        if match is not None:
            text = normalize_markdown_text(match.group(2))
            headings.append((index, len(match.group(1)), text))

    return headings


# ---------------------------------------------------------------------------
# Definition blocks
# ---------------------------------------------------------------------------


def extract_definition_blocks(
    text: str,
    source_path: str,
) -> tuple[list[DefinitionBlock], list[Diagnostic]]:
    """Split the definition section into one block per heading.

    Definitions are the headings one level below the section heading. The
    section ends at the next heading at or above its own level.
    """

    lines = text.splitlines()
    headings = find_headings(lines)

    section = next(
        (
            position
            for position, (_, _, title) in enumerate(headings)
            if remove_section_number(title) == DEFINITION_SECTION_TITLE
        ),
        None,
    )
    if section is None:
        return [], [
            Diagnostic(
                ERROR,
                "MISSING_DEFINITION_SECTION",
                f"Section {DEFINITION_SECTION_TITLE!r} was not found.",
                source_path,
            )
        ]

    section_level = headings[section][1]
    section_end = len(lines)
    definitions = []

    for index, level, title in headings[section + 1:]:
        if level <= section_level:
            section_end = index
            break
        if level == section_level + 1:
            definitions.append((index, title))

    blocks = []
    for position, (index, name) in enumerate(definitions):
        end = (
            definitions[position + 1][0]
            if position + 1 < len(definitions)
            else section_end
        )
        blocks.append(
            DefinitionBlock(
                name=name,
                source_path=source_path,
                start_line=index + 1,
                lines=tuple(
                    (line_index + 1, lines[line_index])
                    for line_index in range(index + 1, end)
                ),
            )
        )

    if not blocks:
        return [], [
            Diagnostic(
                ERROR,
                "NO_MICRO_OPERATIONS",
                "No micro-operation definitions were found.",
                source_path,
            )
        ]

    return blocks, []


# ---------------------------------------------------------------------------
# Labeled sections
# ---------------------------------------------------------------------------


def parse_label(text: str) -> tuple[str, str] | None:
    """Return ``(label, inline_text)`` for a recognized bold label line."""

    match = LABEL_PATTERN.match(text)
    if match is None:
        return None

    label = match.group(1).strip().casefold()
    if label not in SCALAR_LABELS + LIST_LABELS:
        return None

    return label, normalize_markdown_text(match.group(2).strip())


def group_labeled_sections(
    block: DefinitionBlock,
) -> tuple[list[LabeledSection], list[tuple[int, str]]]:
    """Group a block's lines under the recognized label that precedes them.

    A line holding several labels is split before each one. Lines before
    the first label are ignored. Code blocks, including their fence lines,
    are always content.

    Returns the sections, and ``(line, label)`` for each unrecognized bold
    label outside code blocks; such a label is kept as ordinary text.
    """

    sections: list[LabeledSection] = []
    unrecognized: list[tuple[int, str]] = []
    current: tuple[str, int, str] | None = None
    content: list[tuple[int, str]] = []
    in_fence = False

    def close() -> None:
        if current is not None:
            sections.append(LabeledSection(*current, tuple(content)))

    for line, text in block.lines:
        if is_code_fence(text):
            in_fence = not in_fence
            content.append((line, text))
            continue
        if in_fence:
            content.append((line, text))
            continue

        parts = [part for part in LABEL_START_PATTERN.split(text) if part]
        for part in parts or [text]:
            label = parse_label(part)
            if label is None:
                other = LABEL_PATTERN.match(part)
                if other is not None:
                    unrecognized.append((line, other.group(1).strip()))
                content.append((line, part))
                continue
            close()
            current = (label[0], line, label[1])
            content = []

    close()
    return sections, unrecognized


def scalar_values(section: LabeledSection) -> list[str]:
    """Return the non-empty text lines of a single-valued attribute.

    Lines are stripped, except that indentation inside code blocks is kept.
    Code-fence lines and horizontal rules are dropped. A ``- `` list marker
    is removed from Sources lines.
    """

    values = [section.inline] if section.inline else []
    in_fence = False

    for _, text in section.lines:
        if is_code_fence(text):
            in_fence = not in_fence
            continue
        if in_fence:
            value = normalize_markdown_text(text.rstrip())
            if value.strip():
                values.append(value)
            continue
        value = normalize_markdown_text(text.strip())
        if not value or value == HORIZONTAL_RULE:
            continue
        item = LIST_ITEM_PATTERN.match(value)
        if section.label == "sources" and item is not None:
            value = item.group(1)
        values.append(value)

    return values


def list_entries(
    section: LabeledSection,
    block: DefinitionBlock,
) -> tuple[list[TextEntry], list[Diagnostic]]:
    """Return the entries of a Preconditions or Constraints section.

    The inline text and each ``- `` list item are entries. Blank lines and
    horizontal rules are skipped. Any other line, and any code block, is
    reported once and skipped; an unrecognized label line is skipped
    without a report here, because it is reported as UNRECOGNIZED_LABEL.
    """

    entries = []
    diagnostics = []
    in_fence = False

    def skip(line: int, what: str) -> None:
        diagnostics.append(
            Diagnostic(
                WARNING,
                "UNEXPECTED_LIST_TEXT",
                f"Skipped {what} in {section.label}; only list items are "
                "extracted.",
                block.source_path,
                line,
                block.name,
            )
        )

    if section.inline:
        entries.append(TextEntry(section.inline, section.line))

    for line, text in section.lines:
        if is_code_fence(text):
            in_fence = not in_fence
            if in_fence:
                skip(line, "a code block")
            continue
        stripped = text.strip()
        if in_fence or not stripped or stripped == HORIZONTAL_RULE:
            continue
        item = LIST_ITEM_PATTERN.match(text)
        if item is None:
            if LABEL_PATTERN.match(text) is None:
                skip(line, repr(stripped))
            continue
        entries.append(TextEntry(normalize_markdown_text(item.group(1)), line))

    return entries, diagnostics


def split_comma_list(value: str) -> list[str]:
    """Split a comma-separated value into its non-empty items."""

    return [
        normalize_markdown_text(item.strip())
        for item in value.split(",")
        if item.strip()
    ]


def parse_sources(values: list[str]) -> list[str]:
    """Return the source names, or none for a documented empty list."""

    if len(values) == 1 and values[0].casefold() in EMPTY_SOURCE_VALUES:
        return []
    return [item for value in values for item in split_comma_list(value)]


# ---------------------------------------------------------------------------
# Micro-operations
# ---------------------------------------------------------------------------


def extract_micro_operation(
    block: DefinitionBlock,
) -> tuple[MicroOperation, list[Diagnostic]]:
    """Read one micro-operation and report problems with its attributes."""

    diagnostics: list[Diagnostic] = []
    scalars: dict[str, list[str]] = {}
    lists: dict[str, list[TextEntry]] = {label: [] for label in LIST_LABELS}

    def report(code: str, message: str, line: int, severity: str = ERROR):
        diagnostics.append(
            Diagnostic(
                severity, code, message, block.source_path, line, block.name
            )
        )

    sections, unrecognized = group_labeled_sections(block)

    for line, label in unrecognized:
        report(
            "UNRECOGNIZED_LABEL",
            f"Label {label!r} is not recognized; its line is read as "
            "ordinary text of the preceding section.",
            line,
            WARNING,
        )

    for section in sections:
        if section.label in lists:
            entries, list_diagnostics = list_entries(section, block)
            lists[section.label] += entries
            diagnostics += list_diagnostics
            continue
        if section.label in scalars:
            report(
                "DUPLICATE_ATTRIBUTE",
                f"Attribute {section.label!r} occurs more than once.",
                section.line,
            )
        scalars[section.label] = scalar_values(section)

    for label in SCALAR_LABELS:
        if label not in scalars:
            report(
                "MISSING_REQUIRED_ATTRIBUTE",
                f"Definition does not specify {label}.",
                block.start_line,
            )
        elif not scalars[label]:
            report(
                "EMPTY_REQUIRED_ATTRIBUTE",
                f"Definition {label} is empty.",
                block.start_line,
            )

    micro_operation = MicroOperation(
        name=block.name,
        source_path=block.source_path,
        line=block.start_line,
        category=" ".join(scalars.get("category", [])),
        description=" ".join(scalars.get("description", [])),
        targets=split_comma_list(" ".join(scalars.get("target", []))),
        expression=scalars.get("expression", []),
        sources=parse_sources(scalars.get("sources", [])),
        preconditions=lists["preconditions"],
        constraints=lists["constraints"],
    )
    return micro_operation, diagnostics


def extract_micro_operations(text: str, source_path: str) -> ExtractionResult:
    """Extract every micro-operation in the catalog document."""

    blocks, diagnostics = extract_definition_blocks(text, source_path)
    micro_operations = []
    seen_names: set[str] = set()

    for block in blocks:
        micro_operation, block_diagnostics = extract_micro_operation(block)

        if block.name in seen_names:
            block_diagnostics.append(
                Diagnostic(
                    ERROR,
                    "DUPLICATE_MICRO_OPERATION",
                    f"Micro-operation {block.name!r} is defined more than "
                    "once.",
                    source_path,
                    block.start_line,
                    block.name,
                )
            )
        seen_names.add(block.name)

        if any(item.severity == ERROR for item in block_diagnostics):
            micro_operation = replace(micro_operation, status=STATUS_ERROR)

        micro_operations.append(micro_operation)
        diagnostics += block_diagnostics

    return ExtractionResult(
        source_path=source_path,
        micro_operations=micro_operations,
        diagnostics=sorted(diagnostics, key=diagnostic_sort_key),
    )


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def text_entry_to_dict(entry: TextEntry, source_path: str) -> dict[str, Any]:
    """Return the JSON form of a precondition or constraint."""

    return {
        "text": entry.text,
        "source": {"path": source_path, "line": entry.line},
    }


def micro_operation_to_dict(micro_operation: MicroOperation) -> dict[str, Any]:
    """Return the JSON form of a micro-operation. Key order is the format."""

    path = micro_operation.source_path
    return {
        "name": micro_operation.name,
        "category": micro_operation.category,
        "description": micro_operation.description,
        "targets": micro_operation.targets,
        "expression": micro_operation.expression,
        "sources": micro_operation.sources,
        "preconditions": [
            text_entry_to_dict(entry, path)
            for entry in micro_operation.preconditions
        ],
        "constraints": [
            text_entry_to_dict(entry, path)
            for entry in micro_operation.constraints
        ],
        "source": {
            "path": path,
            "heading": micro_operation.name,
            "line": micro_operation.line,
        },
        "extraction_status": micro_operation.status,
    }


def diagnostic_to_dict(diagnostic: Diagnostic) -> dict[str, Any]:
    """Return the JSON form of a diagnostic, omitting empty fields."""

    result: dict[str, Any] = {
        "severity": diagnostic.severity,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "source_path": diagnostic.source_path,
    }
    if diagnostic.line is not None:
        result["line"] = diagnostic.line
    if diagnostic.micro_operation:
        result["micro_operation"] = diagnostic.micro_operation
    return result


def build_json_result(result: ExtractionResult) -> dict[str, Any]:
    """Return the complete JSON document."""

    return {
        "format_version": FORMAT_VERSION,
        "extraction_stage": EXTRACTION_STAGE,
        "source": {"path": result.source_path},
        "micro_operations": [
            micro_operation_to_dict(item) for item in result.micro_operations
        ],
        "diagnostics": [
            diagnostic_to_dict(item) for item in result.diagnostics
        ],
    }


def serialize_json(data: dict[str, Any]) -> str:
    """Serialize JSON preserving key order, with a trailing newline."""

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def format_diagnostic(diagnostic: Diagnostic) -> str:
    """Format one diagnostic as a report line."""

    location = diagnostic.source_path
    if diagnostic.line is not None:
        location = f"{location}:{diagnostic.line}"
    name = diagnostic.micro_operation or "-"
    return (
        f"{diagnostic.severity} {diagnostic.code} [{name}] {location}: "
        f"{diagnostic.message}"
    )


def format_failure(diagnostic: Diagnostic) -> list[str]:
    """Format one failure diagnostic for the console."""

    location = diagnostic.source_path
    if diagnostic.line is not None:
        location = f"{location}:{diagnostic.line}"
    name = diagnostic.micro_operation
    name = f" [{name}]" if name else ""
    return [
        f"{diagnostic.severity} {diagnostic.code}{name}",
        f"  Source: {location}",
        f"  {diagnostic.message}",
    ]


def build_report(
    diagnostics: Sequence[Diagnostic],
    micro_operation_count: int,
    json_written: bool,
) -> str:
    """Build the human-readable extraction report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Micro-Operation Extraction Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Micro-operations processed: {micro_operation_count}",
        f"JSON written: {'yes' if json_written else 'no'}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    lines += [format_diagnostic(item) for item in diagnostics] or [
        "No diagnostics."
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Extract micro-operation definitions from the catalog."
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
            f"Source file does not exist: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise ExtractionFailure(
            f"Source file is not valid UTF-8: {path}"
        ) from error
    except OSError as error:
        raise ExtractionFailure(
            f"Source file could not be read: {path}: {error}"
        ) from error


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings, creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the extractor; return 1 if any error-level diagnostic exists.

    Relative paths are resolved from the repository root.
    """

    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    json_output = resolve_from_repo(root, options.json_output)
    report_output = resolve_from_repo(root, options.report_output)
    source_path = SOURCE_PATH.as_posix()

    try:
        text = read_source(resolve_from_repo(root, SOURCE_PATH))
    except ExtractionFailure as error:
        diagnostics = [
            Diagnostic(FATAL, "EXTRACTION_FAILURE", str(error), source_path)
        ]
        count = 0
        json_written = False
    else:
        result = extract_micro_operations(text, source_path)
        write_text(json_output, serialize_json(build_json_result(result)))
        diagnostics = result.diagnostics
        count = len(result.micro_operations)
        json_written = True

    write_text(report_output, build_report(diagnostics, count, json_written))

    failures = [
        item for item in diagnostics if item.severity in FAILURE_SEVERITIES
    ]
    exit_code = 1 if failures else 0

    print("Micro-operation extraction")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Micro-operations: {count}")
    print(f"JSON written: {'yes' if json_written else 'no'}")
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
