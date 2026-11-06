"""Extract structured control-input definitions from project documentation.

The extractor reads the five authoritative control-input documents and
produces deterministic JSON plus a human-readable report.

Pipeline:

1. Load the authoritative documents.
2. Parse the index into signal names, domains, and categories.
3. Split the definition documents into one block per indexed signal.
4. Extract each block's attributes, values, dependencies, logic,
   constraints, and consumers into a ``SignalDefinition``.
5. Validate each signal against its domain's structural rules.
6. Write the JSON result and the extraction report.

See the tool README for the extraction and validation boundary.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Sequence

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SOURCE_DIRECTORY = Path("docs/04-control/10-control-input-definitions")
INDEX_SOURCE_PATH = SOURCE_DIRECTORY / "00-index.md"
DEFINITION_SOURCE_PATHS = (
    SOURCE_DIRECTORY / "01-flags.md",
    SOURCE_DIRECTORY / "02-ir-derived-fields.md",
    SOURCE_DIRECTORY / "03-derived-flags.md",
    SOURCE_DIRECTORY / "04-external-inputs.md",
)
SOURCE_PATHS = (INDEX_SOURCE_PATH, *DEFINITION_SOURCE_PATHS)

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/control-input-extractor"
)
DEFAULT_JSON_OUTPUT = OUTPUT_DIRECTORY / "control-inputs.json"
DEFAULT_REPORT_OUTPUT = OUTPUT_DIRECTORY / "extraction-report.txt"

# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

FORMAT_VERSION = 1
EXTRACTION_STAGE = "final-structure-validation"
STATUS_VALIDATED = "structure-validated"
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
# Input domains and per-domain rules
# ---------------------------------------------------------------------------

PRIMITIVE_FLAGS = "Primitive Flags"
IR_DERIVED_SIGNALS = "IR-Derived Signals"
DERIVED_FLAGS = "Derived Flags"
EXTERNAL_INPUTS = "External Inputs"

# Index heading text (casefolded, unnumbered) -> domain.
INDEX_DOMAINS = {
    "primitive flags": PRIMITIVE_FLAGS,
    "ir-derived signals": IR_DERIVED_SIGNALS,
    "derived flags": DERIVED_FLAGS,
    "external inputs": EXTERNAL_INPUTS,
}

REQUIRED_ATTRIBUTES_BY_DOMAIN = {
    PRIMITIVE_FLAGS: frozenset({"display_name", "purpose", "source_register"}),
    IR_DERIVED_SIGNALS: frozenset(
        {"display_name", "input_type", "mnemonic", "purpose"}
    ),
    DERIVED_FLAGS: frozenset({"display_name", "mnemonic", "purpose"}),
    EXTERNAL_INPUTS: frozenset({"display_name", "input_type", "purpose"}),
}

# Domains whose width defaults to one bit when not documented.
ONE_BIT_DEFAULT_DOMAINS = frozenset({PRIMITIVE_FLAGS, DERIVED_FLAGS})

# Domains whose documented mnemonic must equal the indexed name.
MNEMONIC_DOMAINS = frozenset({IR_DERIVED_SIGNALS, DERIVED_FLAGS})


@dataclass(frozen=True)
class LogicRule:
    """Logic a domain must document and the signal it must assign.

    ``sections`` lists acceptable logic sections in preference order.  At
    least one must be present; the first present one must assign the
    signal.
    """

    sections: tuple[str, ...]
    missing_code: str
    missing_message: str
    mismatch_code: str
    mismatch_message: str


LOGIC_RULES_BY_DOMAIN = {
    IR_DERIVED_SIGNALS: LogicRule(
        sections=("derivation",),
        missing_code="MISSING_DERIVATION",
        missing_message="An IR-derived signal must document a derivation.",
        mismatch_code="DERIVATION_RESULT_MISMATCH",
        mismatch_message=(
            "Derivation does not assign the indexed signal '{name}'."
        ),
    ),
    DERIVED_FLAGS: LogicRule(
        sections=("expression", "internal_composition"),
        missing_code="MISSING_DERIVED_LOGIC",
        missing_message=(
            "A derived flag must document an expression or "
            "internal composition."
        ),
        mismatch_code="DERIVED_RESULT_MISMATCH",
        mismatch_message=(
            "Derived logic does not assign the indexed signal '{name}'."
        ),
    ),
}

# ---------------------------------------------------------------------------
# Definition labels
# ---------------------------------------------------------------------------

# Bold label -> attribute key.
SCALAR_ATTRIBUTE_LABELS = {
    "mnemonic": "mnemonic",
    "name": "display_name",
    "type": "input_type",
    "bit width": "bit_width",
    "polarity": "polarity",
    "purpose": "purpose",
    "source register": "source_register",
}
# Attributes normalized into dedicated output fields.
NORMALIZED_ATTRIBUTES = frozenset({"bit_width", "polarity"})

VALUE_LABELS = frozenset({"value encoding"})
DEPENDENCY_LABELS = frozenset({"inputs"})
CONSTRAINT_LABELS = frozenset({"constraint", "constraints"})
CONSUMER_LABELS = frozenset({"consumed by", "used by μops", "used by uops"})

# Bold label -> logic-section key.
LOGIC_SECTION_LABELS = {
    "derivation": "derivation",
    "expression": "expression",
    "internal composition (local to this definition)": "internal_composition",
}

POLARITY_VALUES = {
    "active-high": "active-high",
    "active high": "active-high",
    "active-low": "active-low",
    "active low": "active-low",
}

GLOBAL_CONSTRAINT_KINDS = {
    "EXACTLY_ONE": "exactly_one",
    "AT_MOST_ONE": "at_most_one",
}

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
SECTION_NUMBER_PATTERN = re.compile(r"^\d+(?:\.\d+)*\.?\s+")
LABEL_PATTERN = re.compile(r"\*\*([^*]+?):?\*\*")
INDEX_ENTRY_PATTERN = re.compile(
    r"^\s*-\s+\[(.+?)\]\(([^)]+)\)\s*(?:-\s*.*)?$"
)
TRAILING_PARENTHESIZED_PATTERN = re.compile(r"\(([^()]+)\)\s*$")
BIT_WIDTH_PATTERN = re.compile(r"\s*(\d+)(?:\s+bits?)?\s*", re.IGNORECASE)
VALUE_SEPARATOR_PATTERN = re.compile(r"\s*(?:->|→|:)\s*")
HEX_DIGITS_PATTERN = re.compile(r"[0-9A-Fa-f]+")
VALUE_RANGE_PATTERN = re.compile(r"([0-9A-Fa-f]+)\s*[-–]\s*([0-9A-Fa-f]+)")
BINARY_PATTERN = re.compile(r"[01]+")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
GLOBAL_CONSTRAINT_PATTERN = re.compile(
    r"^\s{2,}-\s+`?(EXACTLY_ONE|AT_MOST_ONE)\(([^)]+)\)`?\s*$"
)

DEFINITION_HEADING_LEVEL = 3
LIST_ITEM_PREFIX = "- "
HORIZONTAL_RULE = "---"
CODE_FENCE = "```"


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
    """One control input listed in the authoritative index."""

    name: str
    domain: str
    category: str | None
    source_path: str
    line: int


@dataclass(frozen=True)
class DefinitionBlock:
    """Markdown content of one control-input definition.

    ``lines`` holds ``(source_line_number, text)`` pairs for the body
    following the definition heading.
    """

    signal_name: str
    heading: str
    source_path: str
    start_line: int
    lines: tuple[tuple[int, str], ...]


@dataclass(frozen=True)
class Polarity:
    """Normalized polarity and how it was determined."""

    value: str
    source: str  # "explicit", "name-derived", or "defaulted"


@dataclass(frozen=True)
class EnumeratedValue:
    """One explicitly enumerated input value."""

    value: str
    meaning: str
    line: int


@dataclass(frozen=True)
class ValueRange:
    """One bounded input-value range."""

    start: str
    end: str
    meaning: str
    line: int


@dataclass(frozen=True)
class DependencyEntry:
    """One explicitly documented input dependency."""

    name: str
    line: int


@dataclass(frozen=True)
class TextSection:
    """One source-traceable multiline logic section."""

    text: str
    line: int


@dataclass(frozen=True)
class ConstraintEntry:
    """One source-traceable documented constraint."""

    text: str
    line: int


@dataclass(frozen=True)
class ConsumerEntry:
    """One source-traceable documented consumer."""

    text: str
    target: str | None
    line: int


@dataclass(frozen=True)
class GlobalConstraintEntry:
    """One machine-readable relationship spanning control inputs."""

    kind: str
    inputs: tuple[str, ...]
    source_path: str
    line: int


@dataclass(frozen=True)
class SignalDefinition:
    """Everything extracted from one matched definition block."""

    block: DefinitionBlock
    attributes: dict[str, str] = field(default_factory=dict)
    bit_width: int | None = None
    polarity: Polarity | None = None
    enumerated_values: tuple[EnumeratedValue, ...] = ()
    value_ranges: tuple[ValueRange, ...] = ()
    dependencies: tuple[DependencyEntry, ...] = ()
    logic: dict[str, TextSection] = field(default_factory=dict)
    constraints: tuple[ConstraintEntry, ...] = ()
    consumers: tuple[ConsumerEntry, ...] = ()


@dataclass(frozen=True)
class ExtractionResult:
    """Complete in-memory result of one extraction run."""

    entries: tuple[IndexEntry, ...]
    signals: dict[str, SignalDefinition]
    global_constraints: tuple[GlobalConstraintEntry, ...]
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
        signal_name=block.signal_name,
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
    """Remove an optional numeric prefix from a Markdown heading."""

    return SECTION_NUMBER_PATTERN.sub("", heading).strip()


def normalize_heading(heading: str) -> str:
    """Return heading text without its section number or Markdown markup."""

    return normalize_markdown_text(remove_section_number(heading))


def normalize_label(label: str) -> str:
    """Return the comparison form of a bold definition label."""

    return label.strip().rstrip(":").casefold()


def text_after_label(line: str, label_match: re.Match[str]) -> str:
    """Return the text following a label on the same line."""

    return line[label_match.end():].strip().lstrip(":").strip()


def list_item_text(stripped_line: str) -> str | None:
    """Return the text of a ``- `` list item, or None for other lines."""

    if not stripped_line.startswith(LIST_ITEM_PREFIX):
        return None

    return stripped_line[len(LIST_ITEM_PREFIX):].strip()


@dataclass(frozen=True)
class LabeledSection:
    """Lines following one bold label within a definition block."""

    label: str
    line: int
    trailing_text: str
    body: tuple[tuple[int, str], ...]


def find_labeled_sections(
    block: DefinitionBlock,
    labels: Iterable[str],
    *,
    ends_at_rule: bool,
) -> list[LabeledSection]:
    """Collect the sections introduced by any of ``labels``.

    A section runs from its label to the next bold label.  An unrelated
    label ends the search entirely; a repeated matching label starts a new
    section.  When ``ends_at_rule`` is set, a ``---`` line also closes the
    current section, and a later matching label may open another.
    """

    labels = frozenset(labels)
    sections: list[LabeledSection] = []
    current: tuple[str, int, str] | None = None
    body: list[tuple[int, str]] = []

    def close() -> None:
        nonlocal current, body
        if current is not None:
            sections.append(LabeledSection(*current, tuple(body)))
        current, body = None, []

    for source_line, line in block.lines:
        label_match = LABEL_PATTERN.search(line)

        if label_match is not None:
            label = normalize_label(label_match.group(1))

            if label in labels:
                close()
                current = (
                    label,
                    source_line,
                    text_after_label(line, label_match),
                )
                continue

            if current is not None:
                break

        if current is None:
            continue

        if ends_at_rule and line.strip() == HORIZONTAL_RULE:
            close()
            continue

        body.append((source_line, line))

    close()
    return sections


def iter_section_list_items(
    sections: Iterable[LabeledSection],
) -> Iterator[tuple[int, str]]:
    """Yield ``(source_line, stripped_line)`` for each list item."""

    for section in sections:
        for source_line, line in section.body:
            stripped = line.strip()
            if stripped.startswith(LIST_ITEM_PREFIX):
                yield source_line, stripped


# ---------------------------------------------------------------------------
# Paths and source loading
# ---------------------------------------------------------------------------


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract structured control-input definitions from "
            "the authoritative project documentation."
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

    repo_root = arguments.repo_root.resolve()

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


def validate_source_paths(source_paths: Sequence[Path]) -> None:
    """Require every authoritative source path to be a file."""

    missing_paths = [path for path in source_paths if not path.is_file()]

    if missing_paths:
        formatted_paths = "\n".join(f"- {path}" for path in missing_paths)
        raise FileNotFoundError(
            "Required control-input source files are missing:\n"
            f"{formatted_paths}"
        )


def repository_relative_path(path: Path, repo_root: Path) -> str:
    """Return a POSIX-style path for a source under the repository."""

    return path.relative_to(repo_root).as_posix()


def load_source_documents(
    source_paths: Sequence[Path],
    repo_root: Path,
) -> tuple[SourceDocument, ...]:
    """Load authoritative source documents as UTF-8 text."""

    return tuple(
        SourceDocument(
            path=path,
            relative_path=repository_relative_path(path, repo_root),
            text=path.read_text(encoding="utf-8"),
        )
        for path in source_paths
    )


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


def parse_index(
    document: SourceDocument,
) -> tuple[list[IndexEntry], list[Diagnostic]]:
    """Extract control inputs, domains, and categories from the index.

    A domain heading opens a domain; deeper headings name categories within
    it; a heading at the same or a shallower level closes it.
    """

    entries: list[IndexEntry] = []
    diagnostics: list[Diagnostic] = []
    first_line_by_name: dict[str, int] = {}

    domain: str | None = None
    domain_level = 0
    category: str | None = None

    for line_number, line in enumerate(document.text.splitlines(), start=1):
        heading_match = HEADING_PATTERN.match(line)

        if heading_match is not None:
            level = len(heading_match.group(1))
            heading = normalize_heading(heading_match.group(2))
            recognized_domain = INDEX_DOMAINS.get(heading.casefold())

            if recognized_domain is not None:
                domain, domain_level, category = recognized_domain, level, None
            elif domain is not None and level > domain_level:
                category = heading
            elif domain is not None:
                domain, category = None, None

            continue

        entry_match = INDEX_ENTRY_PATTERN.match(line)

        if entry_match is None:
            continue

        link_text, link_target = entry_match.groups()

        if ".md#" not in link_target:
            continue

        name = normalize_markdown_text(link_text)
        location = {
            "source_path": document.relative_path,
            "line": line_number,
            "signal_name": name,
        }

        if domain is None:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "INDEX_ENTRY_WITHOUT_DOMAIN",
                    "Indexed control input appears outside a "
                    "recognized input domain.",
                    **location,
                )
            )
            continue

        if name in first_line_by_name:
            diagnostics.append(
                Diagnostic(
                    ERROR,
                    "DUPLICATE_INDEX_ENTRY",
                    "Control input is already indexed at line "
                    f"{first_line_by_name[name]}.",
                    **location,
                )
            )
            continue

        first_line_by_name[name] = line_number
        entries.append(
            IndexEntry(
                name=name,
                domain=domain,
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
                message=(
                    "No control-input entries were extracted from "
                    "the authoritative index."
                ),
                source_path=document.relative_path,
            )
        )

    return entries, diagnostics


# ---------------------------------------------------------------------------
# Definition blocks
# ---------------------------------------------------------------------------


def find_signal_in_heading(
    heading: str,
    indexed_names: set[str],
) -> str | None:
    """Find the indexed signal named by a definition heading.

    The heading either is the signal name or ends with it in parentheses,
    e.g. ``AC Negative (ACN)``.
    """

    normalized = normalize_heading(heading)

    if normalized in indexed_names:
        return normalized

    parenthesized = TRAILING_PARENTHESIZED_PATTERN.search(normalized)

    if parenthesized is None:
        return None

    candidate = normalize_markdown_text(parenthesized.group(1))
    return candidate if candidate in indexed_names else None


def extract_definition_blocks(
    document: SourceDocument,
    indexed_names: set[str],
) -> list[DefinitionBlock]:
    """Extract indexed definitions introduced by level-three headings.

    A block ends at the next heading of level three or shallower.  Deeper
    headings inside a block are not part of its body.
    """

    blocks: list[DefinitionBlock] = []
    current: tuple[str, str, int] | None = None
    body: list[tuple[int, str]] = []

    def close() -> None:
        nonlocal current, body
        if current is not None:
            signal_name, heading, start_line = current
            blocks.append(
                DefinitionBlock(
                    signal_name=signal_name,
                    heading=heading,
                    source_path=document.relative_path,
                    start_line=start_line,
                    lines=tuple(body),
                )
            )
        current, body = None, []

    for line_number, line in enumerate(document.text.splitlines(), start=1):
        heading_match = HEADING_PATTERN.match(line)

        if heading_match is None:
            if current is not None:
                body.append((line_number, line))
            continue

        level = len(heading_match.group(1))

        if level > DEFINITION_HEADING_LEVEL:
            continue

        close()

        if level < DEFINITION_HEADING_LEVEL:
            continue

        heading = heading_match.group(2).strip()
        signal_name = find_signal_in_heading(heading, indexed_names)

        if signal_name is not None:
            current = (signal_name, normalize_heading(heading), line_number)

    close()
    return blocks


def match_definition_blocks(
    entries: Sequence[IndexEntry],
    blocks: Sequence[DefinitionBlock],
) -> tuple[dict[str, DefinitionBlock], list[Diagnostic]]:
    """Match definition blocks to indexed control inputs.

    Blocks come from ``extract_definition_blocks``, which only produces
    blocks for indexed names.
    """

    definitions: dict[str, DefinitionBlock] = {}
    diagnostics: list[Diagnostic] = []

    for block in blocks:
        first = definitions.get(block.signal_name)

        if first is not None:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "DUPLICATE_DEFINITION",
                    "Control input has more than one definition. "
                    "The first definition is at "
                    f"{first.source_path}:{first.start_line}.",
                )
            )
            continue

        definitions[block.signal_name] = block

    for entry in entries:
        if entry.name not in definitions:
            diagnostics.append(
                Diagnostic(
                    severity=ERROR,
                    code="MISSING_DEFINITION",
                    message=(
                        "Indexed control input has no matching "
                        "definition block."
                    ),
                    source_path=entry.source_path,
                    line=entry.line,
                    signal_name=entry.name,
                )
            )

    return definitions, diagnostics


# ---------------------------------------------------------------------------
# Scalar attributes, bit width, and polarity
# ---------------------------------------------------------------------------


def parse_scalar_attributes(
    block: DefinitionBlock,
) -> tuple[dict[str, str], list[Diagnostic]]:
    """Extract scalar attributes; one line may hold several labels."""

    attributes: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []

    for source_line, line in block.lines:
        matches = list(LABEL_PATTERN.finditer(line))

        for index, match in enumerate(matches):
            key = SCALAR_ATTRIBUTE_LABELS.get(normalize_label(match.group(1)))

            if key is None:
                continue

            value_end = (
                matches[index + 1].start()
                if index + 1 < len(matches)
                else len(line)
            )
            value = normalize_markdown_text(
                line[match.end():value_end].strip().lstrip(":").strip()
            )

            if not value:
                continue

            if key in attributes:
                diagnostics.append(
                    block_diagnostic(
                        block,
                        "DUPLICATE_ATTRIBUTE",
                        f"Attribute '{key}' is defined more than once.",
                        line=source_line,
                    )
                )
                continue

            attributes[key] = value

    return attributes, diagnostics


def parse_bit_width(value: str) -> int | None:
    """Parse a documented bit width into a positive integer."""

    match = BIT_WIDTH_PATTERN.fullmatch(value)

    if match is None:
        return None

    bit_width = int(match.group(1))
    return bit_width if bit_width >= 1 else None


def normalize_bit_width(
    domain: str,
    block: DefinitionBlock,
    attributes: dict[str, str],
) -> tuple[int | None, list[Diagnostic]]:
    """Normalize a documented width, defaulting flags to one bit."""

    documented = attributes.get("bit_width")

    if documented is None:
        if domain in ONE_BIT_DEFAULT_DOMAINS:
            return 1, []

        return None, [
            block_diagnostic(
                block,
                "MISSING_BIT_WIDTH",
                "Definition does not specify a bit width.",
            )
        ]

    bit_width = parse_bit_width(documented)

    if bit_width is None:
        return None, [
            block_diagnostic(
                block,
                "INVALID_BIT_WIDTH",
                "Bit width must be a positive integer, "
                f"optionally followed by 'bit' or 'bits': {documented}",
            )
        ]

    return bit_width, []


def normalize_polarity(
    block: DefinitionBlock,
    attributes: dict[str, str],
) -> tuple[Polarity | None, list[Diagnostic]]:
    """Normalize explicit, name-derived, or defaulted polarity."""

    documented = attributes.get("polarity")

    if documented is not None:
        value = POLARITY_VALUES.get(documented.casefold())

        if value is None:
            return None, [
                block_diagnostic(
                    block,
                    "INVALID_POLARITY",
                    "Polarity must be active-high or "
                    f"active-low: {documented}",
                )
            ]

        return Polarity(value, "explicit"), []

    if block.signal_name.startswith("/"):
        return Polarity("active-low", "name-derived"), []

    return Polarity("active-high", "defaulted"), []


# ---------------------------------------------------------------------------
# Value encodings
# ---------------------------------------------------------------------------


def parse_value_line(
    text: str,
    line: int = 0,
) -> EnumeratedValue | ValueRange | None:
    """Parse ``value -> meaning`` or ``start-end -> meaning``.

    ``->``, ``→``, and ``:`` are accepted separators.  Returns None when
    the line is not a well-formed value declaration.
    """

    text = normalize_markdown_text(text)

    if text.startswith(LIST_ITEM_PREFIX):
        text = text[len(LIST_ITEM_PREFIX):].strip()

    separator = VALUE_SEPARATOR_PATTERN.search(text)

    if separator is None:
        return None

    value_text = text[:separator.start()].strip()
    meaning = text[separator.end():].strip()

    if not value_text or not meaning:
        return None

    range_match = VALUE_RANGE_PATTERN.fullmatch(value_text)

    if range_match is not None:
        start, end = range_match.groups()
        return ValueRange(start=start, end=end, meaning=meaning, line=line)

    if HEX_DIGITS_PATTERN.fullmatch(value_text) is not None:
        return EnumeratedValue(value=value_text, meaning=meaning, line=line)

    return None


def parse_definition_values(
    block: DefinitionBlock,
) -> tuple[list[EnumeratedValue], list[ValueRange], list[Diagnostic]]:
    """Extract enumerated values and ranges from the value encoding."""

    values: list[EnumeratedValue] = []
    ranges: list[ValueRange] = []
    diagnostics: list[Diagnostic] = []
    first_line_by_value: dict[str, int] = {}

    sections = find_labeled_sections(block, VALUE_LABELS, ends_at_rule=False)

    for source_line, item in iter_section_list_items(sections):
        parsed = parse_value_line(item, source_line)

        if parsed is None:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "MALFORMED_VALUE_ENCODING",
                    f"Value encoding could not be parsed: {item}",
                    line=source_line,
                    severity=WARNING,
                )
            )
        elif isinstance(parsed, ValueRange):
            ranges.append(parsed)
        elif parsed.value in first_line_by_value:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "DUPLICATE_VALUE_ENCODING",
                    f"Value '{parsed.value}' was already defined "
                    f"at line {first_line_by_value[parsed.value]}.",
                    line=source_line,
                )
            )
        else:
            first_line_by_value[parsed.value] = source_line
            values.append(parsed)

    return values, ranges, diagnostics


def parse_binary_value(value: str) -> int | None:
    """Parse a binary value without inferring another numeric base."""

    if BINARY_PATTERN.fullmatch(value) is None:
        return None

    return int(value, 2)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def parse_definition_dependencies(
    block: DefinitionBlock,
) -> tuple[list[DependencyEntry], list[Diagnostic]]:
    """Extract the explicitly documented input dependencies."""

    dependencies: list[DependencyEntry] = []
    diagnostics: list[Diagnostic] = []
    first_line_by_name: dict[str, int] = {}

    sections = find_labeled_sections(
        block, DEPENDENCY_LABELS, ends_at_rule=False
    )

    for source_line, item in iter_section_list_items(sections):
        name = normalize_markdown_text(list_item_text(item) or "")

        if not name:
            continue

        if name in first_line_by_name:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "DUPLICATE_DEPENDENCY",
                    f"Dependency '{name}' was already defined at line "
                    f"{first_line_by_name[name]}.",
                    line=source_line,
                )
            )
            continue

        first_line_by_name[name] = source_line
        dependencies.append(DependencyEntry(name=name, line=source_line))

    return dependencies, diagnostics


# ---------------------------------------------------------------------------
# Logic sections
# ---------------------------------------------------------------------------


def parse_definition_logic_sections(
    block: DefinitionBlock,
) -> tuple[dict[str, TextSection], list[Diagnostic]]:
    """Extract derivation, expression, and internal-composition text.

    A logic section runs from its label to the next bold label or ``---``
    line.  Code-fence markers are dropped, and labels or rules inside a
    fence are treated as text.
    """

    sections: dict[str, TextSection] = {}
    diagnostics: list[Diagnostic] = []

    active_name: str | None = None
    active_line = 0
    active_lines: list[str] = []
    in_code_fence = False

    def close() -> None:
        nonlocal active_name, active_lines

        if active_name is None:
            return

        text = "\n".join(active_lines).strip()

        if not text:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "EMPTY_LOGIC_SECTION",
                    f"Logic section '{active_name}' contains no text.",
                    line=active_line,
                )
            )
        elif active_name in sections:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "DUPLICATE_LOGIC_SECTION",
                    f"Logic section '{active_name}' is defined "
                    "more than once.",
                    line=active_line,
                )
            )
        else:
            sections[active_name] = TextSection(text=text, line=active_line)

        active_name, active_lines = None, []

    for source_line, line in block.lines:
        stripped = line.strip()

        if stripped.startswith(CODE_FENCE):
            if active_name is not None:
                in_code_fence = not in_code_fence
            continue

        if not in_code_fence:
            label_match = LABEL_PATTERN.search(line)

            if label_match is not None:
                close()
                section_name = LOGIC_SECTION_LABELS.get(
                    normalize_label(label_match.group(1))
                )

                if section_name is not None:
                    active_name = section_name
                    active_line = source_line
                    trailing = text_after_label(line, label_match)
                    if trailing:
                        active_lines.append(normalize_markdown_text(trailing))

                continue

            if stripped == HORIZONTAL_RULE:
                close()
                continue

        if active_name is not None:
            active_lines.append(normalize_markdown_text(line))

    close()
    return sections, diagnostics


def logic_assigns_signal(text: str, signal_name: str) -> bool:
    """Return whether some line of ``text`` assigns ``signal_name``."""

    pattern = r"(?m)^\s*" + re.escape(signal_name) + r"\s*="
    return re.search(pattern, text) is not None


# ---------------------------------------------------------------------------
# Constraints and consumers
# ---------------------------------------------------------------------------


def parse_definition_constraints(
    block: DefinitionBlock,
) -> tuple[list[ConstraintEntry], list[Diagnostic]]:
    """Extract Constraint and Constraints content.

    Each list item is one constraint.  Prose (including text on the label
    line) forms a constraint of its own, and continuation lines are joined
    to the preceding constraint.
    """

    sections = find_labeled_sections(
        block, CONSTRAINT_LABELS, ends_at_rule=True
    )
    constraints = [
        constraint
        for section in sections
        for constraint in group_constraint_lines(section)
    ]
    return constraints, []


def group_constraint_lines(section: LabeledSection) -> list[ConstraintEntry]:
    """Group one constraint section's lines into individual constraints."""

    # Each group is (first source line, normalized text parts).
    groups: list[tuple[int, list[str]]] = []

    if section.trailing_text:
        groups.append(
            (section.line, [normalize_markdown_text(section.trailing_text)])
        )

    for source_line, line in section.body:
        stripped = line.strip()

        if not stripped:
            continue

        item = list_item_text(stripped)

        if item is not None:
            groups.append((source_line, [normalize_markdown_text(item)]))
        elif groups:
            groups[-1][1].append(normalize_markdown_text(stripped))
        else:
            groups.append((source_line, [normalize_markdown_text(stripped)]))

    entries = []
    for line, parts in groups:
        text = " ".join(part for part in parts if part).strip()
        if text:
            entries.append(ConstraintEntry(text=text, line=line))
    return entries


def parse_consumer_line(
    line: str,
    source_line: int = 0,
) -> ConsumerEntry | None:
    """Parse one linked or plain-text consumer list item."""

    item = list_item_text(line.strip())

    if not item:
        return None

    link_match = MARKDOWN_LINK_PATTERN.fullmatch(item)

    if link_match is not None:
        return ConsumerEntry(
            text=normalize_markdown_text(link_match.group(1)),
            target=link_match.group(2).strip(),
            line=source_line,
        )

    return ConsumerEntry(
        text=normalize_markdown_text(item),
        target=None,
        line=source_line,
    )


def parse_definition_consumers(
    block: DefinitionBlock,
) -> tuple[list[ConsumerEntry], list[Diagnostic]]:
    """Extract linked and plain-text consumers."""

    sections = find_labeled_sections(block, CONSUMER_LABELS, ends_at_rule=True)
    consumers = [
        consumer
        for source_line, item in iter_section_list_items(sections)
        if (consumer := parse_consumer_line(item, source_line)) is not None
    ]
    return consumers, []


def parse_global_constraints(
    documents: Sequence[SourceDocument],
    indexed_names: set[str],
) -> tuple[list[GlobalConstraintEntry], list[Diagnostic]]:
    """Extract nested ``EXACTLY_ONE(...)``/``AT_MOST_ONE(...)`` bullets."""

    constraints: list[GlobalConstraintEntry] = []
    diagnostics: list[Diagnostic] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    for document in documents:
        for line_number, line in enumerate(
            document.text.splitlines(), start=1
        ):
            match = GLOBAL_CONSTRAINT_PATTERN.match(line)

            if match is None:
                continue

            kind = GLOBAL_CONSTRAINT_KINDS[match.group(1)]
            names = map(normalize_markdown_text, match.group(2).split(","))
            inputs = tuple(name for name in names if name)
            unknown = [name for name in inputs if name not in indexed_names]

            if len(inputs) < 2:
                problem = (
                    "INVALID_GLOBAL_CONSTRAINT",
                    "A global constraint must name at least two inputs.",
                )
            elif unknown:
                problem = (
                    "UNKNOWN_GLOBAL_CONSTRAINT_INPUT",
                    "Global constraint references unknown input(s): "
                    + ", ".join(unknown),
                )
            elif (kind, inputs) in seen:
                problem = (
                    "DUPLICATE_GLOBAL_CONSTRAINT",
                    "Global constraint is defined more than once.",
                )
            else:
                problem = None

            if problem is not None:
                diagnostics.append(
                    Diagnostic(
                        ERROR,
                        *problem,
                        source_path=document.relative_path,
                        line=line_number,
                    )
                )
                continue

            seen.add((kind, inputs))
            constraints.append(
                GlobalConstraintEntry(
                    kind=kind,
                    inputs=inputs,
                    source_path=document.relative_path,
                    line=line_number,
                )
            )

    return constraints, diagnostics


# ---------------------------------------------------------------------------
# Per-signal extraction
# ---------------------------------------------------------------------------


def extract_signal(
    entry: IndexEntry,
    block: DefinitionBlock,
) -> tuple[SignalDefinition, list[Diagnostic]]:
    """Extract every documented property of one definition block."""

    diagnostics: list[Diagnostic] = []

    attributes, found = parse_scalar_attributes(block)
    diagnostics += found
    bit_width, found = normalize_bit_width(entry.domain, block, attributes)
    diagnostics += found
    polarity, found = normalize_polarity(block, attributes)
    diagnostics += found
    values, ranges, found = parse_definition_values(block)
    diagnostics += found
    dependencies, found = parse_definition_dependencies(block)
    diagnostics += found
    logic, found = parse_definition_logic_sections(block)
    diagnostics += found
    constraints, found = parse_definition_constraints(block)
    diagnostics += found
    consumers, found = parse_definition_consumers(block)
    diagnostics += found

    signal = SignalDefinition(
        block=block,
        attributes=attributes,
        bit_width=bit_width,
        polarity=polarity,
        enumerated_values=tuple(values),
        value_ranges=tuple(ranges),
        dependencies=tuple(dependencies),
        logic=logic,
        constraints=tuple(constraints),
        consumers=tuple(consumers),
    )
    return signal, diagnostics


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_required_attributes(
    entry: IndexEntry,
    signal: SignalDefinition,
) -> list[Diagnostic]:
    """Validate the scalar attributes required by the input domain."""

    required = REQUIRED_ATTRIBUTES_BY_DOMAIN.get(entry.domain)

    if required is None:
        return [
            Diagnostic(
                severity=ERROR,
                code="UNKNOWN_INPUT_DOMAIN",
                message=(
                    "No required-attribute policy exists for "
                    f"input domain '{entry.domain}'."
                ),
                source_path=entry.source_path,
                line=entry.line,
                signal_name=entry.name,
            )
        ]

    return [
        block_diagnostic(
            signal.block,
            "MISSING_REQUIRED_ATTRIBUTE",
            f"Domain '{entry.domain}' requires scalar "
            f"attribute '{name}'.",
        )
        for name in sorted(required)
        if not signal.attributes.get(name, "").strip()
    ]


def validate_value_encoding(signal: SignalDefinition) -> list[Diagnostic]:
    """Require exactly one value form: enumerated values or ranges."""

    has_values = bool(signal.enumerated_values)
    has_ranges = bool(signal.value_ranges)

    if not has_values and not has_ranges:
        return [
            block_diagnostic(
                signal.block,
                "MISSING_VALUE_ENCODING",
                "Definition must contain enumerated values "
                "or a bounded value range.",
            )
        ]

    if has_values and has_ranges:
        return [
            block_diagnostic(
                signal.block,
                "MIXED_VALUE_ENCODING",
                "Definition contains both enumerated values "
                "and a bounded value range.",
            )
        ]

    return []


def validate_values_against_width(
    signal: SignalDefinition,
) -> list[Diagnostic]:
    """Validate that documented binary values fit the bit width."""

    if signal.bit_width is None:
        return []

    block = signal.block
    width = signal.bit_width
    maximum = (1 << width) - 1
    diagnostics: list[Diagnostic] = []

    for entry in signal.enumerated_values:
        number = parse_binary_value(entry.value)

        if number is None:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "INVALID_BINARY_VALUE",
                    f"Enumerated value is not valid binary: {entry.value}",
                    line=entry.line,
                )
            )
        elif number > maximum:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "VALUE_EXCEEDS_BIT_WIDTH",
                    f"Binary value {entry.value} does not fit "
                    f"in the documented {width}-bit input.",
                    line=entry.line,
                )
            )

    for entry in signal.value_ranges:
        start = parse_binary_value(entry.start)
        end = parse_binary_value(entry.end)
        text = f"{entry.start}-{entry.end}"

        if start is None or end is None:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "INVALID_BINARY_RANGE",
                    f"Value range must use binary endpoints: {text}",
                    line=entry.line,
                )
            )
        elif start > end:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "REVERSED_VALUE_RANGE",
                    f"Value range start exceeds its end: {text}",
                    line=entry.line,
                )
            )
        elif end > maximum:
            diagnostics.append(
                block_diagnostic(
                    block,
                    "RANGE_EXCEEDS_BIT_WIDTH",
                    f"Binary range {text} does not fit in the documented "
                    f"{width}-bit input.",
                    line=entry.line,
                )
            )

    return diagnostics


def validate_dependencies(
    entry: IndexEntry,
    signal: SignalDefinition,
    indexed_names: set[str],
) -> list[Diagnostic]:
    """Require derived-flag dependencies and check they are indexed."""

    diagnostics: list[Diagnostic] = []

    if entry.domain == DERIVED_FLAGS and not signal.dependencies:
        diagnostics.append(
            block_diagnostic(
                signal.block,
                "MISSING_DEPENDENCIES",
                "A derived flag must document at least one "
                "input dependency.",
            )
        )

    diagnostics.extend(
        block_diagnostic(
            signal.block,
            "UNKNOWN_DEPENDENCY",
            "Dependency does not match an indexed control "
            f"input: {dependency.name}",
            line=dependency.line,
        )
        for dependency in signal.dependencies
        if dependency.name not in indexed_names
    )
    return diagnostics


def validate_logic(
    entry: IndexEntry,
    signal: SignalDefinition,
) -> list[Diagnostic]:
    """Require the domain's logic section and check it assigns the signal."""

    rule = LOGIC_RULES_BY_DOMAIN.get(entry.domain)

    if rule is None:
        return []

    section = next(
        (
            signal.logic[name]
            for name in rule.sections
            if name in signal.logic
        ),
        None,
    )

    if section is None:
        return [
            block_diagnostic(
                signal.block, rule.missing_code, rule.missing_message
            )
        ]

    if not logic_assigns_signal(section.text, entry.name):
        return [
            block_diagnostic(
                signal.block,
                rule.mismatch_code,
                rule.mismatch_message.format(name=entry.name),
                line=section.line,
            )
        ]

    return []


def validate_naming(
    entry: IndexEntry,
    signal: SignalDefinition,
) -> list[Diagnostic]:
    """Check the mnemonic and active-low name agree with the definition."""

    diagnostics: list[Diagnostic] = []
    mnemonic = signal.attributes.get("mnemonic")

    if (
        entry.domain in MNEMONIC_DOMAINS
        and mnemonic is not None
        and mnemonic != entry.name
    ):
        diagnostics.append(
            block_diagnostic(
                signal.block,
                "MNEMONIC_NAME_MISMATCH",
                f"Documented mnemonic '{mnemonic}' does "
                f"not match indexed name '{entry.name}'.",
            )
        )

    if (
        entry.name.startswith("/")
        and signal.polarity is not None
        and signal.polarity.value != "active-low"
    ):
        diagnostics.append(
            block_diagnostic(
                signal.block,
                "ACTIVE_LOW_NAME_CONFLICT",
                "A slash-prefixed signal must have active-low polarity.",
            )
        )

    return diagnostics


def validate_signal(
    entry: IndexEntry,
    signal: SignalDefinition,
    indexed_names: set[str],
) -> list[Diagnostic]:
    """Run every structural check on one extracted signal."""

    return [
        *validate_required_attributes(entry, signal),
        *validate_value_encoding(signal),
        *validate_values_against_width(signal),
        *validate_dependencies(entry, signal, indexed_names),
        *validate_logic(entry, signal),
        *validate_naming(entry, signal),
    ]


# ---------------------------------------------------------------------------
# Extraction pipeline
# ---------------------------------------------------------------------------


def extract_control_inputs(
    index_document: SourceDocument,
    definition_documents: Sequence[SourceDocument],
) -> ExtractionResult:
    """Run the full extraction and validation over loaded documents."""

    entries, diagnostics = parse_index(index_document)
    indexed_names = {entry.name for entry in entries}

    blocks = [
        block
        for document in definition_documents
        for block in extract_definition_blocks(document, indexed_names)
    ]
    definitions, found = match_definition_blocks(entries, blocks)
    diagnostics += found

    global_constraints, found = parse_global_constraints(
        (index_document, *definition_documents), indexed_names
    )
    diagnostics += found

    signals: dict[str, SignalDefinition] = {}

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        signal, found = extract_signal(entry, block)
        diagnostics += found
        diagnostics += validate_signal(entry, signal, indexed_names)
        signals[entry.name] = signal

    return ExtractionResult(
        entries=tuple(entries),
        signals=signals,
        global_constraints=tuple(global_constraints),
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


def signal_to_dict(
    entry: IndexEntry,
    signal: SignalDefinition | None,
) -> dict[str, object]:
    """Convert one indexed signal to its JSON representation."""

    index_source = source_reference(entry.source_path, entry.line)

    if signal is None:
        return {
            "name": entry.name,
            "domain": entry.domain,
            "category": entry.category,
            "definition": None,
            "index_source": index_source,
            "extraction_status": STATUS_DEFINITION_MISSING,
        }

    path = signal.block.source_path

    def source(line: int) -> dict[str, object]:
        return source_reference(path, line)

    polarity = signal.polarity

    return {
        "name": entry.name,
        "domain": entry.domain,
        "category": entry.category,
        "attributes": {
            key: value
            for key, value in signal.attributes.items()
            if key not in NORMALIZED_ATTRIBUTES
        },
        "bit_width": signal.bit_width,
        "polarity": (
            None
            if polarity is None
            else {"value": polarity.value, "source": polarity.source}
        ),
        "dependencies": [
            {"name": item.name, "source": source(item.line)}
            for item in signal.dependencies
        ],
        "enumerated_values": [
            {
                "value": item.value,
                "meaning": item.meaning,
                "source": source(item.line),
            }
            for item in signal.enumerated_values
        ],
        "value_ranges": [
            {
                "start": item.start,
                "end": item.end,
                "meaning": item.meaning,
                "source": source(item.line),
            }
            for item in signal.value_ranges
        ],
        "logic": {
            name: {"text": section.text, "source": source(section.line)}
            for name, section in signal.logic.items()
        },
        "constraints": [
            {"text": item.text, "source": source(item.line)}
            for item in signal.constraints
        ],
        "consumers": [
            {
                "text": item.text,
                "target": item.target,
                "source": source(item.line),
            }
            for item in signal.consumers
        ],
        "definition_source": {
            **source(signal.block.start_line),
            "heading": signal.block.heading,
        },
        "index_source": index_source,
        "extraction_status": STATUS_VALIDATED,
    }


def build_json_result(result: ExtractionResult) -> dict[str, object]:
    """Build the generated control-input representation."""

    return {
        "format_version": FORMAT_VERSION,
        "extraction_stage": EXTRACTION_STAGE,
        "sources": [path.as_posix() for path in SOURCE_PATHS],
        "signals": [
            signal_to_dict(entry, result.signals.get(entry.name))
            for entry in result.entries
        ],
        "constraints": [
            {
                "kind": item.kind,
                "inputs": list(item.inputs),
                "source": source_reference(item.source_path, item.line),
            }
            for item in result.global_constraints
        ],
        "diagnostics": [
            diagnostic_to_dict(diagnostic)
            for diagnostic in result.diagnostics
        ],
    }


def serialize_json(data: dict[str, object]) -> str:
    """Serialize deterministic, human-readable JSON."""

    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Text report
# ---------------------------------------------------------------------------


def _count_with(signals: Iterable[SignalDefinition], attribute: str) -> int:
    """Count signals whose ``attribute`` is non-empty."""

    return sum(bool(getattr(signal, attribute)) for signal in signals)


def _total(signals: Iterable[SignalDefinition], attribute: str) -> int:
    """Total the lengths of ``attribute`` across signals."""

    return sum(len(getattr(signal, attribute)) for signal in signals)


def _heading(title: str) -> list[str]:
    return [title, "-" * len(title)]


def build_extraction_report(result: ExtractionResult) -> str:
    """Build the human-readable extraction report."""

    signals = list(result.signals.values())
    diagnostics = result.diagnostics

    domain_counts: dict[str, int] = {}
    for entry in result.entries:
        domain_counts[entry.domain] = domain_counts.get(entry.domain, 0) + 1

    severity_counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        severity_counts[diagnostic.severity] = (
            severity_counts.get(diagnostic.severity, 0) + 1
        )

    linked_consumers = sum(
        consumer.target is not None
        for signal in signals
        for consumer in signal.consumers
    )

    summary = [
        ("Indexed control inputs", len(result.entries)),
        ("Matched definitions", len(signals)),
        (
            "Definitions with extracted attributes",
            _count_with(signals, "attributes"),
        ),
        (
            "Normalized bit widths",
            sum(signal.bit_width is not None for signal in signals),
        ),
        (
            "Normalized polarities",
            sum(signal.polarity is not None for signal in signals),
        ),
        (
            "Definitions with enumerated values",
            _count_with(signals, "enumerated_values"),
        ),
        ("Definitions with value ranges", _count_with(signals, "value_ranges")),
        ("Enumerated values", _total(signals, "enumerated_values")),
        ("Value ranges", _total(signals, "value_ranges")),
        (
            "Definitions with explicit dependencies",
            _count_with(signals, "dependencies"),
        ),
        ("Dependencies", _total(signals, "dependencies")),
        ("Definitions with logic sections", _count_with(signals, "logic")),
        ("Logic sections", _total(signals, "logic")),
        ("Definitions with constraints", _count_with(signals, "constraints")),
        ("Constraints", _total(signals, "constraints")),
        ("Global constraints", len(result.global_constraints)),
        ("Definitions with consumers", _count_with(signals, "consumers")),
        ("Consumers", _total(signals, "consumers")),
        ("Linked consumers", linked_consumers),
        ("Diagnostics", len(diagnostics)),
    ]

    title = "Control-Input Extraction Report"
    lines = [title, "=" * len(title), ""]

    lines += _heading("Summary")
    lines += [f"{label}: {count}" for label, count in summary]

    lines += ["", *_heading("Inputs by Domain")]
    lines += [
        f"{domain}: {domain_counts[domain]}" for domain in sorted(domain_counts)
    ]

    lines += ["", *_heading("Diagnostics by Severity")]
    lines += [
        f"{severity}: {severity_counts[severity]}"
        for severity in sorted(severity_counts)
    ] or ["None"]

    lines += ["", *_heading("Diagnostic Details")]
    if not diagnostics:
        lines.append("No diagnostics.")
    for diagnostic in diagnostics:
        lines += [*format_diagnostic(diagnostic), ""]

    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text, creating parent directories as needed."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def print_summary(result: ExtractionResult, paths: ToolPaths) -> None:
    """Print the run summary and any failure diagnostics."""

    print("Control-input extraction")
    print(f"Status: {'FAILED' if result.failed else 'SUCCEEDED'}")
    print(f"Control inputs: {len(result.entries)}")
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
        validate_source_paths(paths.source_paths)
        index_document, *definition_documents = load_source_documents(
            paths.source_paths, paths.repo_root
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    result = extract_control_inputs(index_document, definition_documents)

    write_text(paths.json_output, serialize_json(build_json_result(result)))
    write_text(paths.report_output, build_extraction_report(result))
    print_summary(result, paths)

    return 1 if result.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
