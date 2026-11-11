"""Extract candidate control-output definitions from project documentation.

The extractor reads the four authoritative control-output documents and
produces deterministic JSON plus a human-readable report.

Pipeline:

1. Load the authoritative documents.
2. Parse the index into signal names and categories.
3. Split the definition documents into heading blocks and match each block
   to an indexed signal.
4. Extract each block's attributes, bit width, encodings, constraints, and
   micro-operation uses into a ``SignalDefinition``.
5. Validate each signal's attributes, encodings, and category rules.
6. Write the JSON result and the extraction report.

See the tool README for the extraction and validation boundary.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SOURCE_DIRECTORY = Path("docs/04-control/20-control-output-definitions")
INDEX_SOURCE_PATH = SOURCE_DIRECTORY / "00-index.md"
DEFINITION_SOURCE_PATHS = (
    SOURCE_DIRECTORY / "01-microarchitectural-control-signals.md",
    SOURCE_DIRECTORY / "02-architectural-control-signals.md",
    SOURCE_DIRECTORY / "03-sequencing-control-signals.md",
)
SOURCE_PATHS = (INDEX_SOURCE_PATH, *DEFINITION_SOURCE_PATHS)

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/control-output-extractor"
)
DEFAULT_JSON_OUTPUT = OUTPUT_DIRECTORY / "control-outputs.json"
DEFAULT_REPORT_OUTPUT = OUTPUT_DIRECTORY / "extraction-report.txt"

# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

FORMAT_VERSION = 1
EXTRACTION_STAGE = "category-validation"
STATUS_VALIDATED = "category-validated"
STATUS_DEFINITION_MISSING = "definition-missing"

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
FATAL = "FATAL"

SEVERITY_ORDER = {INFO: 0, WARNING: 1, ERROR: 2, FATAL: 3}
FAILURE_SEVERITIES = frozenset({ERROR, FATAL})

# ---------------------------------------------------------------------------
# Index categories
# ---------------------------------------------------------------------------

UNCATEGORIZED = "uncategorized"
ENABLE_SIGNALS = "Enable Signals"

# Categories whose signals must document enumerated encodings.
CATEGORIES_REQUIRING_ENCODINGS = frozenset(
    {ENABLE_SIGNALS, "Select Signals", "Control Flow"}
)

# ---------------------------------------------------------------------------
# Recognized definition labels
# ---------------------------------------------------------------------------

# Bold labels read as scalar attributes, keyed by their comparison form.
ATTRIBUTE_LABELS = {
    "mnemonic": "mnemonic",
    "name": "display_name",
    "class": "signal_class",
    "type": "signal_type",
    "domain": "domain",
    "bit width": "bit_width",
    "width": "bit_width",
    "polarity": "polarity",
    "purpose": "purpose",
    "description": "description",
    "default value": "default_value",
    "explicit value required": "explicit_value_required",
    "value required when": "value_required_when",
}

ENCODING_LABELS = frozenset({"encoding", "value encoding"})
CONSTRAINT_LABELS = frozenset({"constraints"})
MICRO_OPERATION_USE_LABELS = frozenset({"used by μops", "used by uops"})

# ---------------------------------------------------------------------------
# Control-word attribute values
# ---------------------------------------------------------------------------

YES = "Yes"
CONDITIONALLY = "Conditionally"
NOT_APPLICABLE = "N/A"

EXPLICIT_VALUE_REQUIRED_VALUES = {
    "yes": YES,
    "no": "No",
    "conditionally": CONDITIONALLY,
}

# Value Required When texts that are not conditions.
UNCONDITIONAL_REQUIREMENTS = frozenset({"always", "n/a"})

# ---------------------------------------------------------------------------
# Encoding-section text that documents values without listing encodings
# ---------------------------------------------------------------------------

VALUE_SOURCE_DESCRIPTIONS = frozenset(
    {"external bus value", "memory bus value"}
)
EXPLANATORY_LABEL = "where:"

# ---------------------------------------------------------------------------
# Markdown syntax
# ---------------------------------------------------------------------------

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SECTION_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
LABEL_PATTERN = re.compile(r"^\s*\*\*(.+?):?\*\*\s*:?\s*(.*?)\s*$")
INDEX_ENTRY_PATTERN = re.compile(r"^\s*-\s+\[(.+?)\]\(([^)]+)\)\s*$")
TRAILING_PARENTHESIZED_PATTERN = re.compile(r"\(([^()]+)\)\s*$")
BIT_WIDTH_PATTERN = re.compile(r"\s*(\d+)(?:\s+bits?)?\s*", re.IGNORECASE)
ENCODING_PATTERN = re.compile(r"^([A-Za-z0-9]+)\s*(?:->|→|=|:)\s*(.+?)\s*$")
VALUE_RANGE_PATTERN = re.compile(r"^[0-9A-Fa-f]+\s*-\s*[0-9A-Fa-f]+")
OCTAL_PATTERN = re.compile(r"[0-7]+")
MICRO_OPERATION_USE_PATTERN = re.compile(
    r"(?:\[([^]]+)\]\([^)]*\)|([^=]+?))(?:\s*=\s*(\S+))?"
)

DEFINITION_SECTION_HEADING = "signal definitions"
DEFINITION_SECTION_LEVEL = 2
DEFINITION_HEADING_LEVEL = 3
INDEX_CATEGORY_LEVEL = 3
LIST_ITEM_PREFIX = "- "
CODE_FENCE = "```"

# Index links into these documents are signal entries; other links in the
# index give document context only.
INDEX_ENTRY_TARGET_PREFIXES = tuple(
    f"./{path.name}#" for path in DEFINITION_SOURCE_PATHS
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Diagnostic:
    """One extraction or validation finding."""

    severity: str
    code: str
    message: str
    source_path: str | None = None
    line: int | None = None
    signal_name: str | None = None


@dataclass(frozen=True)
class ToolPaths:
    """Resolved input and output paths used by the extractor."""

    repo_root: Path
    source_paths: tuple[Path, ...]
    json_output: Path
    report_output: Path


@dataclass(frozen=True)
class SourceDocument:
    """One loaded authoritative source document."""

    path: Path
    relative_path: str
    text: str


@dataclass(frozen=True)
class IndexEntry:
    """One control output listed in the authoritative index."""

    name: str
    category: str
    source_path: str
    line: int


@dataclass(frozen=True)
class DefinitionBlock:
    """Markdown content under one level-three definition heading.

    ``lines`` holds ``(source_line_number, text)`` pairs for the body
    following the heading.
    """

    heading: str
    source_path: str
    start_line: int
    lines: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class EncodingEntry:
    """One documented control-output encoding."""

    value: str
    meaning: str
    line: int


@dataclass(frozen=True)
class ConstraintEntry:
    """One documented control-output constraint."""

    text: str
    line: int


@dataclass(frozen=True)
class MicroOperationUse:
    """One micro-operation listed under a definition's Used by μops label."""

    micro_operation: str
    value: str | None
    line: int


@dataclass(frozen=True)
class SignalDefinition:
    """Everything extracted from one matched definition block.

    ``attributes`` holds documented scalar attribute values as written,
    after Markdown normalization, in source order.
    """

    entry: IndexEntry
    block: DefinitionBlock
    attributes: dict[str, str]
    bit_width: int | None
    encodings: tuple[EncodingEntry, ...]
    constraints: tuple[ConstraintEntry, ...]
    micro_operation_uses: tuple[MicroOperationUse, ...]

    @property
    def name(self) -> str:
        return self.entry.name


@dataclass(frozen=True)
class ExtractionResult:
    """Complete extraction and validation result.

    ``signals`` contains only indexed signals with a matched definition.
    """

    entries: tuple[IndexEntry, ...]
    signals: dict[str, SignalDefinition]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def failed(self) -> bool:
        return any(
            diagnostic.severity in FAILURE_SEVERITIES
            for diagnostic in self.diagnostics
        )


# ---------------------------------------------------------------------------
# Diagnostic helpers
# ---------------------------------------------------------------------------


def block_diagnostic(
    block: DefinitionBlock,
    signal_name: str,
    code: str,
    message: str,
    *,
    line: int | None = None,
    severity: str = ERROR,
) -> Diagnostic:
    """Build a diagnostic located in a definition block.

    The location defaults to the block's heading line.
    """

    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        source_path=block.source_path,
        line=block.start_line if line is None else line,
        signal_name=signal_name,
    )


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.source_path or "",
        diagnostic.line if diagnostic.line is not None else -1,
        diagnostic.signal_name or "",
        diagnostic.message,
    )


def format_diagnostic(diagnostic: Diagnostic) -> list[str]:
    """Format one diagnostic as report lines."""

    location = diagnostic.source_path or "<unknown source>"
    if diagnostic.line is not None:
        location = f"{location}:{diagnostic.line}"

    signal = f" [{diagnostic.signal_name}]" if diagnostic.signal_name else ""

    return [
        f"{diagnostic.severity} {diagnostic.code}{signal}",
        f"  Source: {location}",
        f"  {diagnostic.message}",
    ]


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


def normalize_markdown_text(value: str) -> str:
    """Remove Markdown escaping and inline-code markers."""

    return (
        value.replace("\\_", "_")
        .replace("\\[", "[")
        .replace("\\]", "]")
        .replace("`", "")
        .strip()
    )


def remove_section_number(heading: str) -> str:
    """Remove an optional numeric prefix such as ``4.`` or ``4.1``."""

    return SECTION_NUMBER_PATTERN.sub("", heading).strip()


def normalize_label(label: str) -> str:
    """Return the comparison form of a bold definition label."""

    return label.strip().rstrip(":").casefold()


def list_item_text(stripped_line: str) -> str | None:
    """Return the text of a ``- `` list item, or None for other lines."""

    if not stripped_line.startswith(LIST_ITEM_PREFIX):
        return None

    return stripped_line[len(LIST_ITEM_PREFIX):].strip()


@dataclass(frozen=True)
class SectionLine:
    """One line of a labeled section.

    For a label line, ``text`` is the text following the label.
    """

    line: int
    text: str
    is_label: bool = False


def find_labeled_section(
    block: DefinitionBlock,
    labels: Iterable[str],
) -> list[SectionLine]:
    """Return the lines of the section introduced by any of ``labels``.

    A bold label must begin its line. The section runs from the first
    matching label to the next bold label that does not match; a repeated
    matching label continues the section. Later occurrences of the label
    after the section has ended are not read.
    """

    labels = frozenset(labels)
    section: list[SectionLine] = []

    for source_line, line in block.lines:
        label_match = LABEL_PATTERN.match(line)

        if label_match is not None:
            if normalize_label(label_match.group(1)) in labels:
                section.append(
                    SectionLine(
                        source_line, label_match.group(2).strip(), True
                    )
                )
                continue

            if section:
                break

        if section:
            section.append(SectionLine(source_line, line))

    return section


def section_list_items(
    section: Iterable[SectionLine],
) -> list[tuple[int, str]]:
    """Return ``(source_line, item_text)`` for each list item in a section."""

    items = []

    for item in section:
        if item.is_label:
            continue

        text = list_item_text(item.text.strip())

        if text is not None:
            items.append((item.line, text))

    return items


# ---------------------------------------------------------------------------
# Paths and source loading
# ---------------------------------------------------------------------------


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract candidate control-output definitions from the "
            "authoritative Markdown documentation."
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
        help=(
            "JSON output path. Relative paths are resolved from "
            "the repository root."
        ),
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help=(
            "Diagnostic report output path. Relative paths are "
            "resolved from the repository root."
        ),
    )
    return parser.parse_args(arguments)


def resolve_from_repo_root(path: Path, repo_root: Path) -> Path:
    """Resolve a relative path from the repository root."""

    if path.is_absolute():
        return path.resolve()

    return (repo_root / path).resolve()


def resolve_tool_paths(arguments: argparse.Namespace) -> ToolPaths:
    """Resolve all maintained source and generated output paths."""

    repo_root = arguments.repo_root.expanduser().resolve()

    return ToolPaths(
        repo_root=repo_root,
        source_paths=tuple(
            resolve_from_repo_root(path, repo_root) for path in SOURCE_PATHS
        ),
        json_output=resolve_from_repo_root(arguments.json_output, repo_root),
        report_output=resolve_from_repo_root(
            arguments.report_output, repo_root
        ),
    )


def validate_source_paths(
    repo_root: Path,
    source_paths: Sequence[Path],
) -> None:
    """Require the repository root and every authoritative source to exist."""

    if not repo_root.is_dir():
        raise FileNotFoundError(
            "Repository root does not exist or is not a directory: "
            f"{repo_root}"
        )

    missing_paths = [path for path in source_paths if not path.is_file()]

    if missing_paths:
        formatted_paths = "\n".join(f"  - {path}" for path in missing_paths)
        raise FileNotFoundError(
            "Required control-output source files are missing:\n"
            f"{formatted_paths}"
        )


def repository_relative_path(path: Path, repo_root: Path) -> str:
    """Return a POSIX-style path for a source under the repository."""

    return path.relative_to(repo_root).as_posix()


def read_source_document(path: Path, repo_root: Path) -> SourceDocument:
    """Read one authoritative source document as UTF-8 text."""

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Source file is not valid UTF-8: {path}") from error

    return SourceDocument(
        path=path,
        relative_path=repository_relative_path(path, repo_root),
        text=text,
    )


def load_source_documents(
    source_paths: Sequence[Path],
    repo_root: Path,
) -> tuple[SourceDocument, ...]:
    """Load authoritative source documents in the supplied order."""

    return tuple(
        read_source_document(path, repo_root) for path in source_paths
    )


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


def parse_index(
    document: SourceDocument,
) -> tuple[list[IndexEntry], list[Diagnostic]]:
    """Extract linked signal entries and their categories from the index.

    Each level-three heading names the category of the entries below it.
    """

    entries: list[IndexEntry] = []
    diagnostics: list[Diagnostic] = []
    first_lines: dict[str, int] = {}
    category = UNCATEGORIZED

    for line_number, line in enumerate(document.text.splitlines(), start=1):
        heading_match = HEADING_PATTERN.match(line)

        if heading_match is not None:
            if len(heading_match.group(1)) == INDEX_CATEGORY_LEVEL:
                category = remove_section_number(heading_match.group(2))
            continue

        entry_match = INDEX_ENTRY_PATTERN.match(line)

        if entry_match is None:
            continue

        link_text, link_target = entry_match.groups()

        if not link_target.startswith(INDEX_ENTRY_TARGET_PREFIXES):
            continue

        name = normalize_markdown_text(link_text)

        if name in first_lines:
            diagnostics.append(
                Diagnostic(
                    severity=ERROR,
                    code="DUPLICATE_INDEX_ENTRY",
                    message=(
                        f"Signal is already indexed at line "
                        f"{first_lines[name]}."
                    ),
                    source_path=document.relative_path,
                    line=line_number,
                    signal_name=name,
                )
            )
            continue

        first_lines[name] = line_number
        entries.append(
            IndexEntry(
                name=name,
                category=category,
                source_path=document.relative_path,
                line=line_number,
            )
        )

    if not entries:
        diagnostics.append(
            Diagnostic(
                severity=ERROR,
                code="NO_INDEX_ENTRIES",
                message="No control-output signal entries were found.",
                source_path=document.relative_path,
            )
        )

    return entries, diagnostics


# ---------------------------------------------------------------------------
# Definition blocks
# ---------------------------------------------------------------------------


def extract_definition_blocks(
    document: SourceDocument,
) -> list[DefinitionBlock]:
    """Split a document's Signal Definitions section into heading blocks.

    The section runs from a level-two "Signal Definitions" heading to the
    next level-two heading. Each level-three heading inside it starts a
    block; deeper headings are part of the block's content.
    """

    blocks: list[DefinitionBlock] = []
    in_section = False
    heading: str | None = None
    start_line = 0
    lines: list[tuple[int, str]] = []

    def finish_block() -> None:
        if heading is not None:
            blocks.append(
                DefinitionBlock(
                    heading=heading,
                    source_path=document.relative_path,
                    start_line=start_line,
                    lines=tuple(lines),
                )
            )

    for line_number, line in enumerate(document.text.splitlines(), start=1):
        heading_match = HEADING_PATTERN.match(line)

        if heading_match is not None:
            level = len(heading_match.group(1))
            text = remove_section_number(heading_match.group(2))

            if level == DEFINITION_SECTION_LEVEL:
                in_section = text.casefold() == DEFINITION_SECTION_HEADING
                continue

            if in_section and level == DEFINITION_HEADING_LEVEL:
                finish_block()
                heading = normalize_markdown_text(text)
                start_line = line_number
                lines = []
                continue

        if in_section and heading is not None:
            lines.append((line_number, line))

    finish_block()
    return blocks


def find_signal_in_heading(
    heading: str,
    indexed_names: set[str],
) -> str | None:
    """Return the indexed signal a definition heading names, if any.

    A heading names a signal when it is the signal name or ends with the
    signal name in parentheses.
    """

    if heading in indexed_names:
        return heading

    parenthesized = TRAILING_PARENTHESIZED_PATTERN.search(heading)

    if parenthesized is None:
        return None

    candidate = parenthesized.group(1).strip()
    return candidate if candidate in indexed_names else None


def match_definition_blocks(
    entries: Sequence[IndexEntry],
    blocks: Sequence[DefinitionBlock],
) -> tuple[dict[str, DefinitionBlock], list[Diagnostic]]:
    """Match definition blocks to indexed signals and report mismatches."""

    indexed_names = {entry.name for entry in entries}
    matched: dict[str, DefinitionBlock] = {}
    diagnostics: list[Diagnostic] = []

    for block in blocks:
        name = find_signal_in_heading(block.heading, indexed_names)

        if name is None:
            diagnostics.append(
                Diagnostic(
                    severity=WARNING,
                    code="UNINDEXED_DEFINITION",
                    message=(
                        "Definition heading does not identify an indexed "
                        f"control-output signal: {block.heading}"
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                )
            )
            continue

        if name in matched:
            first = matched[name]
            diagnostics.append(
                block_diagnostic(
                    block,
                    name,
                    "DUPLICATE_DEFINITION",
                    "Signal has more than one definition block. "
                    f"The first definition is at "
                    f"{first.source_path}:{first.start_line}.",
                )
            )
            continue

        matched[name] = block

    for entry in entries:
        if entry.name not in matched:
            diagnostics.append(
                Diagnostic(
                    severity=ERROR,
                    code="MISSING_DEFINITION",
                    message="Indexed signal has no matching definition block.",
                    source_path=entry.source_path,
                    line=entry.line,
                    signal_name=entry.name,
                )
            )

    return matched, diagnostics


# ---------------------------------------------------------------------------
# Scalar attributes and bit width
# ---------------------------------------------------------------------------


def parse_definition_attributes(
    signal_name: str,
    block: DefinitionBlock,
) -> tuple[dict[str, str], list[Diagnostic]]:
    """Extract recognized scalar attributes from one definition block.

    An attribute is a line-leading bold label with its value on the same
    line. Labels without a same-line value are ignored.
    """

    attributes: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []

    for source_line, line in block.lines:
        label_match = LABEL_PATTERN.match(line)

        if label_match is None:
            continue

        attribute = ATTRIBUTE_LABELS.get(normalize_label(label_match.group(1)))
        value = label_match.group(2).strip()

        if attribute is None or not value:
            continue

        if attribute in attributes:
            diagnostics.append(
                block_diagnostic(
                    block,
                    signal_name,
                    "DUPLICATE_ATTRIBUTE",
                    f"Attribute '{attribute}' is defined more than once.",
                    line=source_line,
                )
            )
            continue

        attributes[attribute] = normalize_markdown_text(value)

    return attributes, diagnostics


def parse_bit_width(value: str) -> int | None:
    """Parse a positive bit width, optionally followed by ``bit``/``bits``."""

    match = BIT_WIDTH_PATTERN.fullmatch(value)

    if match is None:
        return None

    bit_width = int(match.group(1))
    return bit_width if bit_width >= 1 else None


def normalize_bit_width(
    signal_name: str,
    block: DefinitionBlock,
    attributes: dict[str, str],
) -> tuple[int | None, list[Diagnostic]]:
    """Return the documented bit width, reporting an invalid value.

    A missing width is reported by ``validate_required_attributes``.
    """

    documented = attributes.get("bit_width")

    if documented is None:
        return None, []

    bit_width = parse_bit_width(documented)

    if bit_width is None:
        return None, [
            block_diagnostic(
                block,
                signal_name,
                "INVALID_BIT_WIDTH",
                "Bit width must be a positive integer, optionally "
                f"followed by 'bit' or 'bits': {documented}",
            )
        ]

    return bit_width, []


def parse_octal(value: str) -> int | None:
    """Parse an unsigned octal digit string."""

    if OCTAL_PATTERN.fullmatch(value) is None:
        return None

    return int(value, 8)


def normalize_explicit_value_required(value: str) -> str | None:
    """Return ``Yes``, ``No``, or ``Conditionally``, or None if invalid."""

    return EXPLICIT_VALUE_REQUIRED_VALUES.get(value.strip().casefold())


def normalize_default_value(value: str, bit_width: int) -> str | None:
    """Return ``N/A`` or an octal value that fits ``bit_width``, else None."""

    stripped = value.strip()

    if stripped.casefold() == NOT_APPLICABLE.casefold():
        return NOT_APPLICABLE

    numeric_value = parse_octal(stripped)

    if numeric_value is None or numeric_value >= 1 << bit_width:
        return None

    return stripped


# ---------------------------------------------------------------------------
# Encodings
# ---------------------------------------------------------------------------


def parse_encoding_line(line: str) -> tuple[str, str] | None:
    """Parse ``value SEPARATOR meaning``, optionally as a list item.

    The separator is ``->``, ``→``, ``=``, or ``:``.
    """

    stripped = line.strip()
    item_text = list_item_text(stripped)

    if item_text is not None:
        stripped = item_text

    match = ENCODING_PATTERN.match(stripped)

    if match is None:
        return None

    meaning = normalize_markdown_text(match.group(2))

    if not meaning:
        return None

    return match.group(1), meaning


def is_encoding_description(stripped_line: str) -> bool:
    """Recognize encoding-section text that describes values in prose.

    Value ranges, bus-value descriptions, ``where:`` labels, and bit-slice
    expressions document a field without enumerating its encodings.
    """

    return (
        VALUE_RANGE_PATTERN.match(stripped_line) is not None
        or stripped_line.casefold() in VALUE_SOURCE_DESCRIPTIONS
        or stripped_line.casefold() == EXPLANATORY_LABEL
        or "[" in stripped_line
    )


def parse_definition_encodings(
    signal_name: str,
    block: DefinitionBlock,
) -> tuple[list[EncodingEntry], list[Diagnostic]]:
    """Extract enumerated encodings from one definition block.

    An encoding may follow the label on the same line. Code-fence markers
    and blank lines are skipped. A heading or bold line that is not an
    encoding ends the section.
    """

    encodings: list[EncodingEntry] = []
    diagnostics: list[Diagnostic] = []

    def malformed(line: int, message: str) -> None:
        diagnostics.append(
            block_diagnostic(
                block,
                signal_name,
                "MALFORMED_ENCODING",
                message,
                line=line,
                severity=WARNING,
            )
        )

    for item in find_labeled_section(block, ENCODING_LABELS):
        if item.is_label:
            if not item.text:
                continue

            parsed = parse_encoding_line(item.text)

            if parsed is None:
                malformed(
                    item.line,
                    f"Encoding text could not be parsed: {item.text}",
                )
            else:
                encodings.append(EncodingEntry(*parsed, item.line))
            continue

        stripped = item.text.strip()

        if not stripped or stripped.startswith(CODE_FENCE):
            continue

        parsed = parse_encoding_line(stripped)

        if parsed is not None:
            encodings.append(EncodingEntry(*parsed, item.line))
            continue

        if stripped.startswith(("#", "**")):
            break

        if not is_encoding_description(stripped):
            malformed(
                item.line, f"Encoding line could not be parsed: {stripped}"
            )

    first_lines: dict[str, int] = {}

    for encoding in encodings:
        if encoding.value in first_lines:
            diagnostics.append(
                block_diagnostic(
                    block,
                    signal_name,
                    "DUPLICATE_ENCODING_VALUE",
                    f"Encoding value '{encoding.value}' is already "
                    f"defined at line {first_lines[encoding.value]}.",
                    line=encoding.line,
                )
            )
            continue

        first_lines[encoding.value] = encoding.line

    return encodings, diagnostics


# ---------------------------------------------------------------------------
# Constraints and micro-operation uses
# ---------------------------------------------------------------------------


def parse_definition_constraints(
    block: DefinitionBlock,
) -> list[ConstraintEntry]:
    """Extract list items, including nested items, from Constraints."""

    return [
        ConstraintEntry(text=normalize_markdown_text(text), line=line)
        for line, text in section_list_items(
            find_labeled_section(block, CONSTRAINT_LABELS)
        )
    ]


def parse_micro_operation_use(
    item_text: str,
    line: int,
) -> MicroOperationUse | None:
    """Parse ``[NAME](target) = value`` or ``NAME = value``.

    The link and the ``= value`` part are both optional.
    """

    match = MICRO_OPERATION_USE_PATTERN.fullmatch(item_text)

    if match is None:
        return None

    linked_name, plain_name, value = match.groups()

    return MicroOperationUse(
        micro_operation=normalize_markdown_text(linked_name or plain_name),
        value=None if value is None else normalize_markdown_text(value),
        line=line,
    )


def parse_definition_micro_operation_uses(
    block: DefinitionBlock,
) -> list[MicroOperationUse]:
    """Extract list items from a definition's Used by μops section."""

    uses = []

    for line, text in section_list_items(
        find_labeled_section(block, MICRO_OPERATION_USE_LABELS)
    ):
        use = parse_micro_operation_use(text, line)

        if use is not None:
            uses.append(use)

    return uses


# ---------------------------------------------------------------------------
# Per-signal extraction
# ---------------------------------------------------------------------------


def extract_signal(
    entry: IndexEntry,
    block: DefinitionBlock,
) -> tuple[SignalDefinition, list[Diagnostic]]:
    """Extract every property of one matched definition block."""

    attributes, diagnostics = parse_definition_attributes(entry.name, block)

    bit_width, found = normalize_bit_width(entry.name, block, attributes)
    diagnostics += found

    encodings, found = parse_definition_encodings(entry.name, block)
    diagnostics += found

    signal = SignalDefinition(
        entry=entry,
        block=block,
        attributes=attributes,
        bit_width=bit_width,
        encodings=tuple(encodings),
        constraints=tuple(parse_definition_constraints(block)),
        micro_operation_uses=tuple(
            parse_definition_micro_operation_uses(block)
        ),
    )
    return signal, diagnostics


# ---------------------------------------------------------------------------
# Per-signal validation
# ---------------------------------------------------------------------------


def signal_diagnostic(
    signal: SignalDefinition,
    code: str,
    message: str,
    *,
    line: int | None = None,
    severity: str = ERROR,
) -> Diagnostic:
    """Build a diagnostic located in a signal's definition block."""

    return block_diagnostic(
        signal.block,
        signal.name,
        code,
        message,
        line=line,
        severity=severity,
    )


def validate_required_attributes(signal: SignalDefinition) -> list[Diagnostic]:
    """Warn when a definition lacks a bit width or a description."""

    diagnostics = []

    if "bit_width" not in signal.attributes:
        diagnostics.append(
            signal_diagnostic(
                signal,
                "MISSING_BIT_WIDTH",
                "Definition does not specify a bit width.",
                severity=WARNING,
            )
        )

    if not {"purpose", "description"} & signal.attributes.keys():
        diagnostics.append(
            signal_diagnostic(
                signal,
                "MISSING_DESCRIPTION",
                "Definition does not specify a purpose or description.",
                severity=WARNING,
            )
        )

    return diagnostics


def validate_mnemonic(signal: SignalDefinition) -> list[Diagnostic]:
    """Report a documented mnemonic that differs from the indexed name."""

    mnemonic = signal.attributes.get("mnemonic")

    if mnemonic is None or mnemonic == signal.name:
        return []

    return [
        signal_diagnostic(
            signal,
            "MNEMONIC_MISMATCH",
            f"Documented mnemonic '{mnemonic}' does not match indexed "
            f"signal '{signal.name}'.",
        )
    ]


def validate_control_word_attributes(
    signal: SignalDefinition,
) -> list[Diagnostic]:
    """Validate the attributes that govern control-word value assignment.

    These are Default Value, Explicit Value Required, and Value Required
    When.
    """

    diagnostics = []
    attributes = signal.attributes

    default_value = attributes.get("default_value")
    normalized_default = None

    if default_value is None:
        diagnostics.append(
            signal_diagnostic(
                signal,
                "MISSING_DEFAULT_VALUE",
                "Definition does not specify Default Value.",
            )
        )
    elif signal.bit_width is not None:
        normalized_default = normalize_default_value(
            default_value, signal.bit_width
        )

        if normalized_default is None:
            diagnostics.append(
                signal_diagnostic(
                    signal,
                    "INVALID_DEFAULT_VALUE",
                    "Default Value must be N/A or an octal value that fits "
                    f"the documented {signal.bit_width}-bit width: "
                    f"{default_value}",
                )
            )

    explicit_required = attributes.get("explicit_value_required")
    requirement = None

    if explicit_required is None:
        diagnostics.append(
            signal_diagnostic(
                signal,
                "MISSING_EXPLICIT_VALUE_REQUIRED",
                "Definition does not specify Explicit Value Required.",
            )
        )
    else:
        requirement = normalize_explicit_value_required(explicit_required)

        if requirement is None:
            diagnostics.append(
                signal_diagnostic(
                    signal,
                    "INVALID_EXPLICIT_VALUE_REQUIRED",
                    "Explicit Value Required must be Yes, No, or "
                    f"Conditionally: {explicit_required}",
                )
            )

    condition = attributes.get("value_required_when")

    if condition is None:
        diagnostics.append(
            signal_diagnostic(
                signal,
                "MISSING_VALUE_REQUIRED_WHEN",
                "Definition does not specify Value Required When.",
            )
        )
    elif not condition:
        # Only possible when the value is Markdown markup alone, such as ``.
        diagnostics.append(
            signal_diagnostic(
                signal,
                "EMPTY_VALUE_REQUIRED_WHEN",
                "Value Required When must not be empty.",
            )
        )
    elif (
        requirement == CONDITIONALLY
        and condition.casefold() in UNCONDITIONAL_REQUIREMENTS
    ):
        diagnostics.append(
            signal_diagnostic(
                signal,
                "INVALID_CONDITIONAL_REQUIREMENT",
                "A conditionally explicit field must specify a conditional "
                "Value Required When expression.",
            )
        )

    if (
        requirement in {YES, CONDITIONALLY}
        and normalized_default == NOT_APPLICABLE
    ):
        diagnostics.append(
            signal_diagnostic(
                signal,
                "EXPLICIT_FIELD_HAS_NO_DEFAULT",
                "A field explicitly assigned by control must define an "
                "encoded Default Value.",
            )
        )

    return diagnostics


def validate_encoding_widths(signal: SignalDefinition) -> list[Diagnostic]:
    """Require encodings to be octal values that fit the bit width."""

    if signal.bit_width is None:
        return []

    diagnostics = []
    maximum_value = (1 << signal.bit_width) - 1

    for encoding in signal.encodings:
        numeric_value = parse_octal(encoding.value)

        if numeric_value is None:
            diagnostics.append(
                signal_diagnostic(
                    signal,
                    "INVALID_OCTAL_ENCODING",
                    f"Encoding value is not valid octal: {encoding.value}",
                    line=encoding.line,
                )
            )
        elif numeric_value > maximum_value:
            diagnostics.append(
                signal_diagnostic(
                    signal,
                    "ENCODING_EXCEEDS_BIT_WIDTH",
                    f"Octal encoding {encoding.value} has numeric value "
                    f"{numeric_value}, which does not fit in the documented "
                    f"{signal.bit_width}-bit field.",
                    line=encoding.line,
                )
            )

    return diagnostics


def validate_category_requirements(
    signal: SignalDefinition,
) -> list[Diagnostic]:
    """Apply the structural rules of the signal's index category."""

    diagnostics = []
    category = signal.entry.category

    if category == ENABLE_SIGNALS and signal.bit_width != 1:
        found = (
            "none is specified"
            if signal.bit_width is None
            else f"found {signal.bit_width}"
        )
        diagnostics.append(
            signal_diagnostic(
                signal,
                "INVALID_ENABLE_WIDTH",
                f"An enable signal must have a bit width of 1; {found}.",
            )
        )

    if category in CATEGORIES_REQUIRING_ENCODINGS and not signal.encodings:
        diagnostics.append(
            signal_diagnostic(
                signal,
                "MISSING_ENUMERATED_ENCODINGS",
                f"Signals in category '{category}' must define enumerated "
                "encodings.",
            )
        )

    return diagnostics


def validate_signal(signal: SignalDefinition) -> list[Diagnostic]:
    """Run every per-signal validation."""

    return [
        *validate_required_attributes(signal),
        *validate_mnemonic(signal),
        *validate_control_word_attributes(signal),
        *validate_encoding_widths(signal),
        *validate_category_requirements(signal),
    ]


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_control_outputs(
    index_document: SourceDocument,
    definition_documents: Sequence[SourceDocument],
) -> ExtractionResult:
    """Run the full extraction and validation over loaded documents."""

    entries, diagnostics = parse_index(index_document)

    blocks = [
        block
        for document in definition_documents
        for block in extract_definition_blocks(document)
    ]
    definitions, found = match_definition_blocks(entries, blocks)
    diagnostics += found

    signals: dict[str, SignalDefinition] = {}

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        signal, found = extract_signal(entry, block)
        diagnostics += found
        diagnostics += validate_signal(signal)
        signals[entry.name] = signal

    return ExtractionResult(
        entries=tuple(entries),
        signals=signals,
        diagnostics=tuple(sorted(diagnostics, key=diagnostic_sort_key)),
    )


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def source_reference(path: str, line: int) -> dict[str, object]:
    """Return the JSON form of a source location."""

    return {"path": path, "line": line}


def diagnostic_to_dict(diagnostic: Diagnostic) -> dict[str, object]:
    """Convert one diagnostic to a JSON-compatible dictionary."""

    return {
        "severity": diagnostic.severity,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "source_path": diagnostic.source_path,
        "line": diagnostic.line,
        "signal_name": diagnostic.signal_name,
    }


def output_attributes(signal: SignalDefinition) -> dict[str, str | None]:
    """Return the JSON attributes, excluding the bit width.

    Explicit Value Required is normalized, and Default Value is normalized
    when the bit width is known. Either becomes None if invalid.
    """

    attributes: dict[str, str | None] = {}

    for key, value in signal.attributes.items():
        if key == "bit_width":
            continue

        if key == "explicit_value_required":
            attributes[key] = normalize_explicit_value_required(value)
        elif key == "default_value" and signal.bit_width is not None:
            attributes[key] = normalize_default_value(value, signal.bit_width)
        else:
            attributes[key] = value

    return attributes


def micro_operation_use_to_dict(
    use: MicroOperationUse,
    source_path: str,
) -> dict[str, object]:
    """Convert one micro-operation use; ``value`` is omitted when absent."""

    result: dict[str, object] = {
        "micro_operation": use.micro_operation,
        "source": source_reference(source_path, use.line),
    }

    if use.value is not None:
        result["value"] = use.value

    return result


def definition_to_dict(signal: SignalDefinition) -> dict[str, object]:
    """Convert one matched definition to its JSON representation."""

    source_path = signal.block.source_path

    return {
        "heading": signal.block.heading,
        "attributes": output_attributes(signal),
        "bit_width": signal.bit_width,
        "encodings": [
            {
                "value": encoding.value,
                "meaning": encoding.meaning,
                "source": source_reference(source_path, encoding.line),
            }
            for encoding in signal.encodings
        ],
        "constraints": [
            {
                "text": constraint.text,
                "source": source_reference(source_path, constraint.line),
            }
            for constraint in signal.constraints
        ],
        "used_by_micro_operations": [
            micro_operation_use_to_dict(use, source_path)
            for use in signal.micro_operation_uses
        ],
        "source": source_reference(source_path, signal.block.start_line),
    }


def signal_to_dict(
    entry: IndexEntry,
    signal: SignalDefinition | None,
) -> dict[str, object]:
    """Convert one indexed signal to its JSON representation."""

    return {
        "name": entry.name,
        "category": entry.category,
        "definition": None if signal is None else definition_to_dict(signal),
        "source": source_reference(entry.source_path, entry.line),
        "extraction_status": (
            STATUS_DEFINITION_MISSING if signal is None else STATUS_VALIDATED
        ),
    }


def build_json_result(result: ExtractionResult) -> dict[str, object]:
    """Build the generated control-output representation."""

    return {
        "format_version": FORMAT_VERSION,
        "extraction_stage": EXTRACTION_STAGE,
        "signals": [
            signal_to_dict(entry, result.signals.get(entry.name))
            for entry in result.entries
        ],
        "diagnostics": [
            diagnostic_to_dict(diagnostic)
            for diagnostic in result.diagnostics
        ],
    }


def serialize_json(data: dict[str, object]) -> str:
    """Serialize JSON in construction order, with a trailing newline."""

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------


def build_extraction_report(result: ExtractionResult) -> str:
    """Build the human-readable extraction report."""

    signals = list(result.signals.values())
    diagnostics = result.diagnostics

    def severity_count(severity: str) -> int:
        return sum(item.severity == severity for item in diagnostics)

    summary = [
        ("Indexed signals", len(result.entries)),
        ("Matched definitions", len(signals)),
        (
            "Definitions with extracted attributes",
            sum(bool(signal.attributes) for signal in signals),
        ),
        (
            "Definitions with normalized bit widths",
            sum(signal.bit_width is not None for signal in signals),
        ),
        (
            "Definitions with extracted encodings",
            sum(bool(signal.encodings) for signal in signals),
        ),
        (
            "Encoding entries extracted",
            sum(len(signal.encodings) for signal in signals),
        ),
        (
            "Definitions with extracted constraints",
            sum(bool(signal.constraints) for signal in signals),
        ),
        (
            "Constraint entries extracted",
            sum(len(signal.constraints) for signal in signals),
        ),
        ("Missing definitions", len(result.entries) - len(signals)),
        ("Informational diagnostics", severity_count(INFO)),
        ("Warnings", severity_count(WARNING)),
        ("Errors", severity_count(ERROR)),
        ("Fatal errors", severity_count(FATAL)),
    ]

    title = "Control Output Extraction Report"
    lines = [title, "=" * len(title), "", "Stage: category validation"]
    lines += [f"{label}: {count}" for label, count in summary]
    lines += ["", "Diagnostics", "-----------"]

    if not diagnostics:
        lines.append("None.")
    for diagnostic in diagnostics:
        lines += [*format_diagnostic(diagnostic), ""]

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings, creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def print_summary(result: ExtractionResult, paths: ToolPaths) -> None:
    """Print the run summary and any failure diagnostics."""

    print("Control-output extraction")
    print(f"Status: {'FAILED' if result.failed else 'SUCCEEDED'}")
    print(f"Control outputs: {len(result.entries)}")
    print(f"Definitions matched: {len(result.signals)}")
    print(f"Diagnostics: {len(result.diagnostics)}")
    print(f"JSON output: {paths.json_output}")
    print(f"Report output: {paths.report_output}")

    if not result.failed:
        return

    print()
    print("Failure diagnostics")
    print("-------------------")

    for diagnostic in result.diagnostics:
        if diagnostic.severity in FAILURE_SEVERITIES:
            print("\n".join(format_diagnostic(diagnostic)))


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the extractor; return 1 if any error-level diagnostic exists."""

    paths = resolve_tool_paths(parse_arguments(arguments))

    try:
        validate_source_paths(paths.repo_root, paths.source_paths)
        index_document, *definition_documents = load_source_documents(
            paths.source_paths, paths.repo_root
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    result = extract_control_outputs(index_document, definition_documents)

    write_text(paths.json_output, serialize_json(build_json_result(result)))
    write_text(paths.report_output, build_extraction_report(result))
    print_summary(result, paths)

    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
