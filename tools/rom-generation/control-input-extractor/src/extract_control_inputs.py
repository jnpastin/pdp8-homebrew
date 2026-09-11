"""Extract structured control-input definitions from project documentation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import re
import json

@dataclass(frozen=True)
class IndexEntry:
    """One control input listed in the authoritative index."""

    name: str
    domain: str
    category: str | None
    source_path: str
    line: int


@dataclass(frozen=True)
class Diagnostic:
    """One extraction or validation finding."""

    severity: str
    code: str
    message: str
    source_path: str | None = None
    line: int | None = None
    signal_name: str | None = None
    
DEFAULT_JSON_OUTPUT = Path(
    "build"
    "/simulation_outputs"
    "/rom-generation"
    "/control-input-extractor"
    "/control-inputs.json"
)

DEFAULT_REPORT_OUTPUT = Path(
    "build"
    "/simulation_outputs"
    "/rom-generation"
    "/control-input-extractor"
    "/extraction-report.txt"
)

SOURCE_PATHS = (
    Path(
        "docs"
        "/04-control"
        "/10-control-input-definitions"
        "/00-index.md"
    ),
    Path(
        "docs"
        "/04-control"
        "/10-control-input-definitions"
        "/01-flags.md"
    ),
    Path(
        "docs"
        "/04-control"
        "/10-control-input-definitions"
        "/02-ir-derived-fields.md"
    ),
    Path(
        "docs"
        "/04-control"
        "/10-control-input-definitions"
        "/03-derived-flags.md"
    ),
    Path(
        "docs"
        "/04-control"
        "/10-control-input-definitions"
        "/04-external-inputs.md"
    ),
)


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
class DefinitionBlock:
    """Markdown content associated with one control-input definition."""

    signal_name: str
    heading: str
    source_path: str
    start_line: int
    lines: tuple[str, ...]

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
    """One source-traceable multiline definition section."""

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


CONSUMER_SECTION_LABELS = {
    "consumed by",
    "used by μops",
    "used by uops",
}



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


def resolve_from_repo_root(
    path: Path,
    repo_root: Path,
) -> Path:
    """Resolve a relative path from the repository root."""

    if path.is_absolute():
        return path.resolve()

    return (repo_root / path).resolve()


def resolve_tool_paths(
    arguments: argparse.Namespace,
) -> ToolPaths:
    """Resolve all maintained source and generated output paths."""

    repo_root = arguments.repo_root.resolve()

    source_paths = tuple(
        resolve_from_repo_root(path, repo_root)
        for path in SOURCE_PATHS
    )

    return ToolPaths(
        repo_root=repo_root,
        source_paths=source_paths,
        json_output=resolve_from_repo_root(
            arguments.json_output,
            repo_root,
        ),
        report_output=resolve_from_repo_root(
            arguments.report_output,
            repo_root,
        ),
    )


def validate_source_paths(
    source_paths: Sequence[Path],
) -> None:
    """Require every authoritative source path to be a file."""

    missing_paths = [
        path
        for path in source_paths
        if not path.is_file()
    ]

    if missing_paths:
        formatted_paths = "\n".join(
            f"- {path}"
            for path in missing_paths
        )

        raise FileNotFoundError(
            "Required control-input source files are missing:\n"
            f"{formatted_paths}"
        )


def repository_relative_path(
    path: Path,
    repo_root: Path,
) -> str:
    """Return a POSIX-style path for a source under the repository."""

    return path.relative_to(repo_root).as_posix()

def normalize_markdown_text(value: str) -> str:
    """Remove Markdown escaping and inline-code markers."""

    return (
        value.replace("\\_", "_")
        .replace("\\[", "[")
        .replace("\\]", "]")
        .replace("`", "")
        .strip()
    )

def load_source_documents(
    source_paths: Sequence[Path],
    repo_root: Path,
) -> tuple[SourceDocument, ...]:
    """Load authoritative source documents as UTF-8 text."""

    return tuple(
        SourceDocument(
            path=path,
            relative_path=repository_relative_path(
                path,
                repo_root,
            ),
            text=path.read_text(encoding="utf-8"),
        )
        for path in source_paths
    )

INDEX_DOMAINS = {
    "primitive flags": "Primitive Flags",
    "ir-derived signals": "IR-Derived Signals",
    "derived flags": "Derived Flags",
    "external inputs": "External Inputs",
}


def remove_section_number(heading: str) -> str:
    """Remove an optional numeric prefix from a Markdown heading."""

    return re.sub(
        r"^\d+(?:\.\d+)*\.?\s+",
        "",
        heading,
    ).strip()


def parse_index(
    document: SourceDocument,
) -> tuple[list[IndexEntry], list[Diagnostic]]:
    """Extract control inputs, domains, and categories from the index."""

    entries: list[IndexEntry] = []
    diagnostics: list[Diagnostic] = []

    current_domain: str | None = None
    current_domain_level: int | None = None
    current_category: str | None = None

    heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+?)\s*$"
    )
    entry_pattern = re.compile(
        r"^\s*-\s+\[(.+?)\]\(([^)]+)\)\s*(?:-\s*.*)?$"
    )

    seen_names: dict[str, int] = {}

    for line_number, line in enumerate(
        document.text.splitlines(),
        start=1,
    ):
        heading_match = heading_pattern.match(line)

        if heading_match:
            heading_level = len(heading_match.group(1))
            heading_text = normalize_markdown_text(
                remove_section_number(
                    heading_match.group(2)
                )
            )

            recognized_domain = INDEX_DOMAINS.get(
                heading_text.casefold()
            )

            if recognized_domain is not None:
                current_domain = recognized_domain
                current_domain_level = heading_level
                current_category = None
                continue

            if (
                current_domain is not None
                and current_domain_level is not None
                and heading_level > current_domain_level
            ):
                current_category = heading_text
                continue

            if (
                current_domain_level is not None
                and heading_level <= current_domain_level
            ):
                current_domain = None
                current_domain_level = None
                current_category = None

            continue

        entry_match = entry_pattern.match(line)

        if entry_match is None:
            continue

        link_text, link_target = entry_match.groups()

        if ".md#" not in link_target:
            continue

        signal_name = normalize_markdown_text(link_text)

        if current_domain is None:
            diagnostics.append(
                Diagnostic(
                    severity="WARNING",
                    code="INDEX_ENTRY_WITHOUT_DOMAIN",
                    message=(
                        "Indexed control input appears outside a "
                        "recognized input domain."
                    ),
                    source_path=document.relative_path,
                    line=line_number,
                    signal_name=signal_name,
                )
            )
            continue

        if signal_name in seen_names:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_INDEX_ENTRY",
                    message=(
                        "Control input is already indexed at line "
                        f"{seen_names[signal_name]}."
                    ),
                    source_path=document.relative_path,
                    line=line_number,
                    signal_name=signal_name,
                )
            )
            continue

        seen_names[signal_name] = line_number

        entries.append(
            IndexEntry(
                name=signal_name,
                domain=current_domain,
                category=current_category,
                source_path=document.relative_path,
                line=line_number,
            )
        )

    if not entries:
        diagnostics.append(
            Diagnostic(
                severity="ERROR",
                code="NO_INDEX_ENTRIES",
                message=(
                    "No control-input entries were extracted from "
                    "the authoritative index."
                ),
                source_path=document.relative_path,
            )
        )

    return entries, diagnostics
    
def find_signal_in_heading(
    heading: str,
    indexed_names: set[str],
) -> str | None:
    """Find the indexed signal represented by a definition heading."""

    normalized_heading = normalize_markdown_text(
        remove_section_number(heading)
    )

    if normalized_heading in indexed_names:
        return normalized_heading

    parenthesized_name = re.search(
        r"\(([^()]+)\)\s*$",
        normalized_heading,
    )

    if parenthesized_name is None:
        return None

    candidate = normalize_markdown_text(
        parenthesized_name.group(1)
    )

    if candidate in indexed_names:
        return candidate

    return None


def extract_definition_blocks(
    document: SourceDocument,
    indexed_names: set[str],
) -> list:
    """Extract indexed definitions beginning at level-three headings."""

    blocks: list[DefinitionBlock] = []
    heading_pattern = re.compile(
        r"^(#{1,6})\s+(.+?)\s*$"
    )

    current_signal: str | None = None
    current_heading: str | None = None
    current_start_line: int | None = None
    current_lines: list[str] = []

    def finish_current_block() -> None:
        if (
            current_signal is None
            or current_heading is None
            or current_start_line is None
        ):
            return

        blocks.append(
            DefinitionBlock(
                signal_name=current_signal,
                heading=current_heading,
                source_path=document.relative_path,
                start_line=current_start_line,
                lines=tuple(current_lines),
            )
        )

    for line_number, line in enumerate(
        document.text.splitlines(),
        start=1,
    ):
        heading_match = heading_pattern.match(line)

        if heading_match is None:
            if current_signal is not None:
                current_lines.append(line)

            continue

        heading_level = len(heading_match.group(1))
        heading_text = heading_match.group(2).strip()

        if heading_level <= 3:
            finish_current_block()
            current_signal = None
            current_heading = None
            current_start_line = None
            current_lines = []

        if heading_level != 3:
            continue

        signal_name = find_signal_in_heading(
            heading_text,
            indexed_names,
        )

        if signal_name is None:
            continue

        current_signal = signal_name
        current_heading = normalize_markdown_text(
            remove_section_number(heading_text)
        )
        current_start_line = line_number
        current_lines = []

    finish_current_block()

    return blocks

    
def match_definition_blocks(
    entries: Sequence[IndexEntry],
    blocks: Sequence[DefinitionBlock],
) -> tuple[dict[str, DefinitionBlock], list[Diagnostic]]:
    """Match definition blocks to indexed control inputs."""

    entry_by_name = {
        entry.name: entry
        for entry in entries
    }

    definitions: dict[str, DefinitionBlock] = {}
    diagnostics: list[Diagnostic] = []

    for block in blocks:
        signal_name = block.signal_name

        if signal_name not in entry_by_name:
            diagnostics.append(
                Diagnostic(
                    severity="WARNING",
                    code="UNINDEXED_DEFINITION",
                    message=(
                        "Definition does not match an indexed "
                        "control input."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=signal_name,
                )
            )
            continue

        if signal_name in definitions:
            first_block = definitions[signal_name]

            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_DEFINITION",
                    message=(
                        "Control input has more than one definition. "
                        f"The first definition is at "
                        f"{first_block.source_path}:"
                        f"{first_block.start_line}."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=signal_name,
                )
            )
            continue

        definitions[signal_name] = block

    for entry in entries:
        if entry.name in definitions:
            continue

        diagnostics.append(
            Diagnostic(
                severity="ERROR",
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
    
SCALAR_ATTRIBUTE_NAMES = {
    "mnemonic": "mnemonic",
    "name": "display_name",
    "type": "input_type",
    "bit width": "bit_width",
    "polarity": "polarity",
    "purpose": "purpose",
    "source register": "source_register",
}


def parse_scalar_attributes(
    block: DefinitionBlock,
) -> tuple[dict[str, str], list[Diagnostic]]:
    """Extract scalar attributes from one control-input definition."""

    attributes: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []

    label_pattern = re.compile(
        r"\*\*([^*]+?):?\*\*"
    )

    for offset, line in enumerate(block.lines, start=1):
        matches = list(label_pattern.finditer(line))

        for index, match in enumerate(matches):
            label = (
                match.group(1)
                .strip()
                .rstrip(":")
                .casefold()
            )

            attribute_name = SCALAR_ATTRIBUTE_NAMES.get(label)

            if attribute_name is None:
                continue

            value_start = match.end()

            if index + 1 < len(matches):
                value_end = matches[index + 1].start()
            else:
                value_end = len(line)

            value = normalize_markdown_text(
                line[value_start:value_end]
                .strip()
                .lstrip(":")
                .strip()
            )

            if not value:
                continue

            if attribute_name in attributes:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="DUPLICATE_ATTRIBUTE",
                        message=(
                            f"Attribute '{attribute_name}' is "
                            "defined more than once."
                        ),
                        source_path=block.source_path,
                        line=block.start_line + offset,
                        signal_name=block.signal_name,
                    )
                )
                continue

            attributes[attribute_name] = value

    return attributes, diagnostics


def extract_all_scalar_attributes(
    definitions: dict[str, DefinitionBlock],
) -> tuple[dict[str, dict[str, str]], list[Diagnostic]]:
    """Extract scalar attributes from all matched definitions."""

    extracted: dict[str, dict[str, str]] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        attributes, block_diagnostics = parse_scalar_attributes(block)
        extracted[signal_name] = attributes
        diagnostics.extend(block_diagnostics)

    return extracted, diagnostics

def parse_bit_width(value: str) -> int | None:
    """Parse a documented bit width into a positive integer."""

    match = re.fullmatch(
        r"\s*(\d+)(?:\s+bits?)?\s*",
        value,
        re.IGNORECASE,
    )

    if match is None:
        return None

    bit_width = int(match.group(1))

    if bit_width < 1:
        return None

    return bit_width


def normalize_bit_widths(
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
) -> tuple[dict[str, int], list[Diagnostic]]:
    """Normalize documented widths and default flag widths to one bit."""

    bit_widths: dict[str, int] = {}
    diagnostics: list[Diagnostic] = []

    files_with_default_width = {
        "01-flags.md",
        "03-derived-flags.md",
    }

    for signal_name, block in definitions.items():
        documented_width = attributes.get(
            signal_name,
            {},
        ).get("bit_width")

        source_file = Path(block.source_path).name

        if documented_width is None:
            if source_file in files_with_default_width:
                bit_widths[signal_name] = 1
                continue

            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="MISSING_BIT_WIDTH",
                    message="Definition does not specify a bit width.",
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=signal_name,
                )
            )
            continue

        bit_width = parse_bit_width(documented_width)

        if bit_width is None:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="INVALID_BIT_WIDTH",
                    message=(
                        "Bit width must be a positive integer, "
                        "optionally followed by 'bit' or 'bits': "
                        f"{documented_width}"
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=signal_name,
                )
            )
            continue

        bit_widths[signal_name] = bit_width

    return bit_widths, diagnostics


def normalize_polarities(
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
) -> tuple[dict[str, dict[str, str]], list[Diagnostic]]:
    """Normalize explicit, name-derived, and defaulted polarity."""

    polarities: dict[str, dict[str, str]] = {}
    diagnostics: list[Diagnostic] = []

    accepted_values = {
        "active-high": "active-high",
        "active high": "active-high",
        "active-low": "active-low",
        "active low": "active-low",
    }

    for signal_name, block in definitions.items():
        documented_polarity = attributes.get(
            signal_name,
            {},
        ).get("polarity")

        if documented_polarity is not None:
            normalized = accepted_values.get(
                documented_polarity.casefold()
            )

            if normalized is None:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="INVALID_POLARITY",
                        message=(
                            "Polarity must be active-high or "
                            f"active-low: {documented_polarity}"
                        ),
                        source_path=block.source_path,
                        line=block.start_line,
                        signal_name=signal_name,
                    )
                )
                continue

            polarities[signal_name] = {
                "value": normalized,
                "source": "explicit",
            }
            continue

        if signal_name.startswith("/"):
            polarities[signal_name] = {
                "value": "active-low",
                "source": "name-derived",
            }
        else:
            polarities[signal_name] = {
                "value": "active-high",
                "source": "defaulted",
            }

    return polarities, diagnostics

def parse_value_line(
    line: str,
) -> tuple[str, tuple[str, ...]] | None:
    """Parse an enumerated value or bounded value range."""

    text = normalize_markdown_text(line.strip())

    if text.startswith("- "):
        text = text[2:].strip()

    separator_match = re.search(
        r"\s*(?:->|→|:)\s*",
        text,
    )

    if separator_match is None:
        return None

    value_text = text[:separator_match.start()].strip()
    meaning = text[separator_match.end():].strip()

    if not value_text or not meaning:
        return None

    range_match = re.fullmatch(
        r"([0-9A-Fa-f]+)\s*[-–]\s*([0-9A-Fa-f]+)",
        value_text,
    )

    if range_match is not None:
        return (
            "range",
            (
                range_match.group(1),
                range_match.group(2),
                meaning,
            ),
        )

    if re.fullmatch(r"[0-9A-Fa-f]+", value_text) is not None:
        return (
            "enumerated",
            (
                value_text,
                meaning,
            ),
        )

    return None

def parse_value_line(
    line: str,
) -> tuple[str, tuple[str, ...]] | None:
    """Parse an enumerated value or bounded value range."""

    text = normalize_markdown_text(line.strip())

    if text.startswith("- "):
        text = text[2:].strip()

    separator_match = re.search(
        r"\s*(?:->|→|:)\s*",
        text,
    )

    if separator_match is None:
        return None

    value_text = text[:separator_match.start()].strip()
    meaning = text[separator_match.end():].strip()

    if not value_text or not meaning:
        return None

    range_match = re.fullmatch(
        r"([0-9A-Fa-f]+)\s*[-–]\s*([0-9A-Fa-f]+)",
        value_text,
    )

    if range_match is not None:
        return (
            "range",
            (
                range_match.group(1),
                range_match.group(2),
                meaning,
            ),
        )

    if re.fullmatch(r"[0-9A-Fa-f]+", value_text) is not None:
        return (
            "enumerated",
            (
                value_text,
                meaning,
            ),
        )

    return None


def parse_definition_values(
    block: DefinitionBlock,
) -> tuple[
    list[EnumeratedValue],
    list[ValueRange],
    list[Diagnostic],
]:
    """Extract enumerated values and ranges from one definition."""

    enumerated_values: list[EnumeratedValue] = []
    value_ranges: list[ValueRange] = []
    diagnostics: list[Diagnostic] = []

    label_marker = re.escape("**")
    label_pattern = re.compile(
        label_marker + r"([^*]+?):?" + label_marker
    )

    in_value_section = False
    seen_values: dict[str, int] = {}

    for offset, line in enumerate(block.lines, start=1):
        source_line = block.start_line + offset
        label_match = label_pattern.search(line)

        if label_match is not None:
            label = (
                label_match.group(1)
                .strip()
                .rstrip(":")
                .casefold()
            )

            if label == "value encoding":
                in_value_section = True
                continue

            if in_value_section:
                break

        if not in_value_section:
            continue

        stripped = line.strip()

        if not stripped or stripped == "---":
            continue

        if not stripped.startswith("- "):
            continue

        parsed = parse_value_line(stripped)

        if parsed is None:
            diagnostics.append(
                Diagnostic(
                    severity="WARNING",
                    code="MALFORMED_VALUE_ENCODING",
                    message=(
                        "Value encoding could not be parsed: "
                        f"{stripped}"
                    ),
                    source_path=block.source_path,
                    line=source_line,
                    signal_name=block.signal_name,
                )
            )
            continue

        value_kind, parts = parsed

        if value_kind == "enumerated":
            value, meaning = parts

            if value in seen_values:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="DUPLICATE_VALUE_ENCODING",
                        message=(
                            f"Value '{value}' was already defined "
                            f"at line {seen_values[value]}."
                        ),
                        source_path=block.source_path,
                        line=source_line,
                        signal_name=block.signal_name,
                    )
                )
                continue

            seen_values[value] = source_line
            enumerated_values.append(
                EnumeratedValue(
                    value=value,
                    meaning=meaning,
                    line=source_line,
                )
            )
            continue

        range_start, range_end, meaning = parts
        value_ranges.append(
            ValueRange(
                start=range_start,
                end=range_end,
                meaning=meaning,
                line=source_line,
            )
        )

    return enumerated_values, value_ranges, diagnostics


def extract_all_definition_values(
    definitions: dict[str, DefinitionBlock],
) -> tuple[
    dict[str, list[EnumeratedValue]],
    dict[str, list[ValueRange]],
    list[Diagnostic],
]:
    """Extract value declarations from all matched definitions."""

    enumerated_by_signal: dict[str, list[EnumeratedValue]] = {}
    ranges_by_signal: dict[str, list[ValueRange]] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        enumerated_values, value_ranges, block_diagnostics = (
            parse_definition_values(block)
        )

        enumerated_by_signal[signal_name] = enumerated_values
        ranges_by_signal[signal_name] = value_ranges
        diagnostics.extend(block_diagnostics)

    return enumerated_by_signal, ranges_by_signal, diagnostics

def parse_binary_value(value: str) -> int | None:
    """Parse a binary value without inferring another numeric base."""

    if re.fullmatch(r"[01]+", value) is None:
        return None

    return int(value, 2)


def validate_values_against_widths(
    definitions: dict[str, DefinitionBlock],
    bit_widths: dict[str, int],
    enumerated_values: dict[str, list[EnumeratedValue]],
    value_ranges: dict[str, list[ValueRange]],
) -> list[Diagnostic]:
    """Validate documented binary against bit widths."""

    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        bit_width = bit_widths.get(signal_name)

        if bit_width is None:
            continue

        maximum_value = (1 << bit_width) - 1

        for entry in enumerated_values.get(signal_name, []):
            numeric_value = parse_binary_value(entry.value)

            if numeric_value is None:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="INVALID_BINARY_VALUE",
                        message=(
                            "Enumerated value is not valid binary: "
                            f"{entry.value}"
                        ),
                        source_path=block.source_path,
                        line=entry.line,
                        signal_name=signal_name,
                    )
                )
                continue

            if numeric_value > maximum_value:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="VALUE_EXCEEDS_BIT_WIDTH",
                        message=(
                            f"Binary value {entry.value} does not fit "
                            f"in the documented {bit_width}-bit input."
                        ),
                        source_path=block.source_path,
                        line=entry.line,
                        signal_name=signal_name,
                    )
                )

        for entry in value_ranges.get(signal_name, []):
            range_start = parse_binary_value(entry.start)
            range_end = parse_binary_value(entry.end)

            if range_start is None or range_end is None:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="INVALID_BINARY_RANGE",
                        message=(
                            "Value range must use binary endpoints: "
                            f"{entry.start}-{entry.end}"
                        ),
                        source_path=block.source_path,
                        line=entry.line,
                        signal_name=signal_name,
                    )
                )
                continue

            if range_start > range_end:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="REVERSED_VALUE_RANGE",
                        message=(
                            "Value range start exceeds its end: "
                            f"{entry.start}-{entry.end}"
                        ),
                        source_path=block.source_path,
                        line=entry.line,
                        signal_name=signal_name,
                    )
                )
                continue

            if range_end > maximum_value:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="RANGE_EXCEEDS_BIT_WIDTH",
                        message=(
                            f"Binary range {entry.start}-{entry.end} "
                            f"does not fit in the documented "
                            f"{bit_width}-bit input."
                        ),
                        source_path=block.source_path,
                        line=entry.line,
                        signal_name=signal_name,
                    )
                )

    return diagnostics


def diagnostic_to_dict(
    diagnostic: Diagnostic,
) -> dict[str, object]:
    """Convert one diagnostic to a JSON-compatible dictionary."""

    return {
        "severity": diagnostic.severity,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "source_path": diagnostic.source_path,
        "line": diagnostic.line,
        "signal_name": diagnostic.signal_name,
    }


def build_json_result(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
    bit_widths: dict[str, int],
    polarities: dict[str, dict[str, str]],
    enumerated_values: dict[str, list[EnumeratedValue]],
    value_ranges: dict[str, list[ValueRange]],
    dependencies: dict[str, list[DependencyEntry]],
    logic_sections: dict[str, dict[str, TextSection]], 
    constraints: dict[str, list[ConstraintEntry]], 
    consumers: dict[str, list[ConsumerEntry]],
    diagnostics: Sequence[Diagnostic],
) -> dict[str, object]:
    """Build the current generated control-input representation."""

    signals: list[dict[str, object]] = []

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            signals.append(
                {
                    "name": entry.name,
                    "domain": entry.domain,
                    "category": entry.category,
                    "definition": None,
                    "index_source": {
                        "path": entry.source_path,
                        "line": entry.line,
                    },
                    "extraction_status": "definition-missing",
                }
            )
            continue

        signal_attributes = {
            key: value
            for key, value in attributes.get(
                entry.name,
                {},
            ).items()
            if key not in {
                "bit_width",
                "polarity",
            }
        }

        signals.append(
            {
                "name": entry.name,
                "domain": entry.domain,
                "category": entry.category,
                "attributes": signal_attributes,
                "bit_width": bit_widths.get(entry.name),
                "polarity": polarities.get(entry.name),
                "dependencies": [
                    {
                        "name": dependency.name,
                        "source": {
                            "path": block.source_path,
                            "line": dependency.line,
                        },
                    }
                    for dependency in dependencies.get(entry.name, [])
                ],
                "enumerated_values": [
                    {
                        "value": value.value,
                        "meaning": value.meaning,
                        "source": {
                            "path": block.source_path,
                            "line": value.line,
                        },
                    }
                    for value in enumerated_values.get(
                        entry.name,
                        [],
                    )
                ],
                "value_ranges": [
                    {
                        "start": value_range.start,
                        "end": value_range.end,
                        "meaning": value_range.meaning,
                        "source": {
                            "path": block.source_path,
                            "line": value_range.line,
                        },
                    }
                    for value_range in value_ranges.get(
                        entry.name,
                        [],
                    )
                ],
                "logic": {
                    section_name: {
                        "text": section.text,
                        "source": {
                            "path": block.source_path,
                            "line": section.line,
                        },
                    }
                    for section_name, section in logic_sections.get(
                        entry.name,
                        {},
                    ).items()
                },
                "constraints": [
                    {
                        "text": constraint.text,
                        "source": {
                            "path": block.source_path,
                            "line": constraint.line,
                        },
                    }
                    for constraint in constraints.get(
                        entry.name,
                        [],
                    )
                ],
                "consumers": [
                    {
                        "text": consumer.text,
                        "target": consumer.target,
                        "source": {
                            "path": block.source_path,
                            "line": consumer.line,
                        },
                    }
                    for consumer in consumers.get(
                        entry.name,
                        [],
                    )
                ],
                "definition_source": {
                    "path": block.source_path,
                    "line": block.start_line,
                    "heading": block.heading,
                },
                "index_source": {
                    "path": entry.source_path,
                    "line": entry.line,
                },
                "extraction_status": "structure-validated",
            }
        )

    return {
        "format_version": 1,
        "extraction_stage": "final-structure-validation",
        "sources": [
            path.as_posix()
            for path in SOURCE_PATHS
        ],
        "signals": signals,
        "diagnostics": [
            diagnostic_to_dict(diagnostic)
            for diagnostic in diagnostics
        ],
    }


def write_json_output(
    result: dict[str, object],
    output_path: Path,
) -> None:
    """Write deterministic and human-readable JSON output."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    serialized = json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )

    output_path.write_text(
        serialized + "\n",
        encoding="utf-8",
    )

REQUIRED_ATTRIBUTES_BY_DOMAIN = {
    "Primitive Flags": {
        "display_name",
        "purpose",
        "source_register",
    },
    "IR-Derived Signals": {
        "display_name",
        "input_type",
        "mnemonic",
        "purpose",
    },
    "Derived Flags": {
        "display_name",
        "mnemonic",
        "purpose",
    },
    "External Inputs": {
        "display_name",
        "input_type",
        "purpose",
    },
}


def validate_required_attributes(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
) -> list[Diagnostic]:
    """Validate scalar attributes required by each input domain."""

    diagnostics: list[Diagnostic] = []

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        required_attributes = REQUIRED_ATTRIBUTES_BY_DOMAIN.get(
            entry.domain,
        )

        if required_attributes is None:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="UNKNOWN_INPUT_DOMAIN",
                    message=(
                        "No required-attribute policy exists for "
                        f"input domain '{entry.domain}'."
                    ),
                    source_path=entry.source_path,
                    line=entry.line,
                    signal_name=entry.name,
                )
            )
            continue

        signal_attributes = attributes.get(entry.name, {})

        for attribute_name in sorted(required_attributes):
            attribute_value = signal_attributes.get(attribute_name)

            if attribute_value is not None and attribute_value.strip():
                continue

            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="MISSING_REQUIRED_ATTRIBUTE",
                    message=(
                        f"Domain '{entry.domain}' requires scalar "
                        f"attribute '{attribute_name}'."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

    return diagnostics

def parse_definition_dependencies(
    block: DefinitionBlock,
) -> tuple[list[DependencyEntry], list[Diagnostic]]:
    """Extract explicitly documented input dependencies."""

    dependencies: list[DependencyEntry] = []
    diagnostics: list[Diagnostic] = []
    in_inputs_section = False
    seen_dependencies: dict[str, int] = {}

    bold_marker = chr(42) + chr(42)
    label_pattern = re.compile(
        re.escape(bold_marker)
        + r"([^"
        + re.escape(chr(42))
        + r"]+?):?"
        + re.escape(bold_marker)
    )

    for offset, line in enumerate(block.lines, start=1):
        source_line = block.start_line + offset
        label_match = label_pattern.search(line)

        if label_match is not None:
            label = (
                label_match.group(1)
                .strip()
                .rstrip(":")
                .casefold()
            )

            if label == "inputs":
                in_inputs_section = True
                continue

            if in_inputs_section:
                break

        if not in_inputs_section:
            continue

        stripped = line.strip()

        if not stripped or stripped == "---":
            continue

        if not stripped.startswith("- "):
            continue

        dependency_name = normalize_markdown_text(
            stripped[2:].strip()
        )

        if not dependency_name:
            continue

        if dependency_name in seen_dependencies:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_DEPENDENCY",
                    message=(
                        f"Dependency '{dependency_name}' was already "
                        f"defined at line "
                        f"{seen_dependencies[dependency_name]}."
                    ),
                    source_path=block.source_path,
                    line=source_line,
                    signal_name=block.signal_name,
                )
            )
            continue

        seen_dependencies[dependency_name] = source_line
        dependencies.append(
            DependencyEntry(
                name=dependency_name,
                line=source_line,
            )
        )

    return dependencies, diagnostics


def extract_all_definition_dependencies(
    definitions: dict[str, DefinitionBlock],
) -> tuple[
    dict[str, list[DependencyEntry]],
    list[Diagnostic],
]:
    """Extract dependencies from all matched definitions."""

    dependencies_by_signal: dict[str, list[DependencyEntry]] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        dependencies, block_diagnostics = (
            parse_definition_dependencies(block)
        )

        dependencies_by_signal[signal_name] = dependencies
        diagnostics.extend(block_diagnostics)

    return dependencies_by_signal, diagnostics


def validate_derived_dependencies(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    dependencies: dict[str, list[DependencyEntry]],
) -> list[Diagnostic]:
    """Validate dependency lists required by derived flags."""

    diagnostics: list[Diagnostic] = []
    indexed_names = {entry.name for entry in entries}

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        signal_dependencies = dependencies.get(entry.name, [])

        if entry.domain == "Derived Flags" and not signal_dependencies:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="MISSING_DEPENDENCIES",
                    message=(
                        "A derived flag must document at least one "
                        "input dependency."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

        for dependency in signal_dependencies:
            if dependency.name in indexed_names:
                continue

            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="UNKNOWN_DEPENDENCY",
                    message=(
                        "Dependency does not match an indexed control "
                        f"input: {dependency.name}"
                    ),
                    source_path=block.source_path,
                    line=dependency.line,
                    signal_name=entry.name,
                )
            )

    return diagnostics


DERIVATION_SECTION_LABELS = {
    "derivation": "derivation",
    "expression": "expression",
    "internal composition (local to this definition)": "internal_composition",
}


def parse_definition_logic_sections(
    block: DefinitionBlock,
) -> tuple[dict[str, TextSection], list[Diagnostic]]:
    """Extract derivation, expression, and internal-composition text."""

    sections: dict[str, TextSection] = {}
    diagnostics: list[Diagnostic] = []

    bold_marker = chr(42) + chr(42)
    label_pattern = re.compile(
        re.escape(bold_marker)
        + r"([^"
        + re.escape(chr(42))
        + r"]+?):?"
        + re.escape(bold_marker)
    )

    active_name: str | None = None
    active_start_line: int | None = None
    active_lines: list[str] = []
    in_code_fence = False

    def finish_active_section() -> None:
        nonlocal active_name
        nonlocal active_start_line
        nonlocal active_lines

        if active_name is None or active_start_line is None:
            return

        cleaned_lines = list(active_lines)

        while cleaned_lines and not cleaned_lines[0].strip():
            cleaned_lines.pop(0)

        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        text = "\n".join(cleaned_lines).strip()

        if not text:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="EMPTY_LOGIC_SECTION",
                    message=(
                        f"Logic section '{active_name}' contains no text."
                    ),
                    source_path=block.source_path,
                    line=active_start_line,
                    signal_name=block.signal_name,
                )
            )
        elif active_name in sections:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_LOGIC_SECTION",
                    message=(
                        f"Logic section '{active_name}' is defined "
                        "more than once."
                    ),
                    source_path=block.source_path,
                    line=active_start_line,
                    signal_name=block.signal_name,
                )
            )
        else:
            sections[active_name] = TextSection(
                text=text,
                line=active_start_line,
            )

        active_name = None
        active_start_line = None
        active_lines = []

    for offset, line in enumerate(block.lines, start=1):
        source_line = block.start_line + offset
        stripped = line.strip()

        if stripped.startswith("```"):
            if active_name is not None:
                in_code_fence = not in_code_fence
            continue

        if not in_code_fence:
            label_match = label_pattern.search(line)

            if label_match is not None:
                label = (
                    label_match.group(1)
                    .strip()
                    .rstrip(":")
                    .casefold()
                )
                section_name = DERIVATION_SECTION_LABELS.get(label)

                if active_name is not None:
                    finish_active_section()

                if section_name is not None:
                    active_name = section_name
                    active_start_line = source_line
                    trailing_text = line[label_match.end():].strip()
                    trailing_text = trailing_text.lstrip(":").strip()

                    if trailing_text:
                        active_lines.append(
                            normalize_markdown_text(trailing_text)
                        )

                continue

            if active_name is not None and stripped == "---":
                finish_active_section()
                continue

        if active_name is not None:
            active_lines.append(normalize_markdown_text(line))

    finish_active_section()
    return sections, diagnostics


def extract_all_logic_sections(
    definitions: dict[str, DefinitionBlock],
) -> tuple[
    dict[str, dict[str, TextSection]],
    list[Diagnostic],
]:
    """Extract logic sections from all matched definitions."""

    sections_by_signal: dict[str, dict[str, TextSection]] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        sections, block_diagnostics = parse_definition_logic_sections(
            block
        )
        sections_by_signal[signal_name] = sections
        diagnostics.extend(block_diagnostics)

    return sections_by_signal, diagnostics


def validate_required_logic_sections(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    logic_sections: dict[str, dict[str, TextSection]],
) -> list[Diagnostic]:
    """Validate required derivation text by input domain."""

    diagnostics: list[Diagnostic] = []

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        sections = logic_sections.get(entry.name, {})

        if entry.domain == "IR-Derived Signals":
            if "derivation" not in sections:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="MISSING_DERIVATION",
                        message=(
                            "An IR-derived signal must document a derivation."
                        ),
                        source_path=block.source_path,
                        line=block.start_line,
                        signal_name=entry.name,
                    )
                )

        if entry.domain == "Derived Flags":
            has_expression = "expression" in sections
            has_internal_composition = "internal_composition" in sections

            if not has_expression and not has_internal_composition:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="MISSING_DERIVED_LOGIC",
                        message=(
                            "A derived flag must document an expression or "
                            "internal composition."
                        ),
                        source_path=block.source_path,
                        line=block.start_line,
                        signal_name=entry.name,
                    )
                )

    return diagnostics


def parse_definition_constraints(
    block: DefinitionBlock,
) -> tuple[list[ConstraintEntry], list[Diagnostic]]:
    """Extract Constraint and Constraints content from one definition."""

    constraints: list[ConstraintEntry] = []
    diagnostics: list[Diagnostic] = []
    in_constraints_section = False

    pending_lines: list[str] = []
    pending_start_line: int | None = None

    bold_marker = chr(42) + chr(42)
    label_pattern = re.compile(
        re.escape(bold_marker)
        + r"([^"
        + re.escape(chr(42))
        + r"]+?):?"
        + re.escape(bold_marker)
    )

    def finish_pending_constraint() -> None:
        nonlocal pending_lines
        nonlocal pending_start_line

        if pending_start_line is None:
            return

        text = " ".join(
            line
            for line in pending_lines
            if line
        ).strip()

        if text:
            constraints.append(
                ConstraintEntry(
                    text=text,
                    line=pending_start_line,
                )
            )

        pending_lines = []
        pending_start_line = None

    for offset, line in enumerate(block.lines, start=1):
        source_line = block.start_line + offset
        label_match = label_pattern.search(line)

        if label_match is not None:
            label = (
                label_match.group(1)
                .strip()
                .rstrip(":")
                .casefold()
            )

            if label in {"constraint", "constraints"}:
                finish_pending_constraint()
                in_constraints_section = True

                trailing_text = line[label_match.end():].strip()
                trailing_text = trailing_text.lstrip(":").strip()

                if trailing_text:
                    pending_start_line = source_line
                    pending_lines = [
                        normalize_markdown_text(trailing_text)
                    ]

                continue

            if in_constraints_section:
                finish_pending_constraint()
                break

        if not in_constraints_section:
            continue

        stripped = line.strip()

        if not stripped:
            continue

        if stripped == "---":
            finish_pending_constraint()
            in_constraints_section = False
            continue

        if stripped.startswith("- "):
            finish_pending_constraint()
            pending_start_line = source_line
            pending_lines = [
                normalize_markdown_text(
                    stripped[2:].strip()
                )
            ]
            continue

        normalized_line = normalize_markdown_text(stripped)

        if pending_start_line is None:
            pending_start_line = source_line

        pending_lines.append(normalized_line)

    finish_pending_constraint()

    return constraints, diagnostics

def extract_all_definition_constraints(
    definitions: dict[str, DefinitionBlock],
) -> tuple[
    dict[str, list[ConstraintEntry]],
    list[Diagnostic],
]:
    """Extract constraints from all matched definitions."""

    constraints_by_signal: dict[
        str,
        list[ConstraintEntry],
    ] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        constraints, block_diagnostics = (
            parse_definition_constraints(block)
        )

        constraints_by_signal[signal_name] = constraints
        diagnostics.extend(block_diagnostics)

    return constraints_by_signal, diagnostics



def parse_consumer_line(
    line: str,
) -> tuple[str, str | None] | None:
    """Parse one linked or plain-text consumer list item."""

    stripped = line.strip()

    if not stripped.startswith("- "):
        return None

    item_text = stripped[2:].strip()

    if not item_text:
        return None

    link_match = re.fullmatch(
        r"\[([^\]]+)\]\(([^)]+)\)",
        item_text,
    )

    if link_match is not None:
        return (
            normalize_markdown_text(link_match.group(1)),
            link_match.group(2).strip(),
        )

    return (
        normalize_markdown_text(item_text),
        None,
    )


def parse_definition_consumers(
    block: DefinitionBlock,
) -> tuple[list[ConsumerEntry], list[Diagnostic]]:
    """Extract linked and plain-text consumers from one definition."""

    consumers: list[ConsumerEntry] = []
    diagnostics: list[Diagnostic] = []
    in_consumer_section = False

    bold_marker = chr(42) + chr(42)
    label_pattern = re.compile(
        re.escape(bold_marker)
        + r"([^"
        + re.escape(chr(42))
        + r"]+?):?"
        + re.escape(bold_marker)
    )

    for offset, line in enumerate(block.lines, start=1):
        source_line = block.start_line + offset
        label_match = label_pattern.search(line)

        if label_match is not None:
            label = (
                label_match.group(1)
                .strip()
                .rstrip(":")
                .casefold()
            )

            if label in CONSUMER_SECTION_LABELS:
                in_consumer_section = True
                continue

            if in_consumer_section:
                break

        if not in_consumer_section:
            continue

        stripped = line.strip()

        if not stripped:
            continue

        if stripped == "---":
            in_consumer_section = False
            continue

        parsed_consumer = parse_consumer_line(stripped)

        if parsed_consumer is None:
            continue

        consumer_text, consumer_target = parsed_consumer

        consumers.append(
            ConsumerEntry(
                text=consumer_text,
                target=consumer_target,
                line=source_line,
            )
        )

    return consumers, diagnostics


def extract_all_definition_consumers(
    definitions: dict[str, DefinitionBlock],
) -> tuple[
    dict[str, list[ConsumerEntry]],
    list[Diagnostic],
]:
    """Extract consumers from all matched definitions."""

    consumers_by_signal: dict[
        str,
        list[ConsumerEntry],
    ] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        consumers, block_diagnostics = (
            parse_definition_consumers(block)
        )

        consumers_by_signal[signal_name] = consumers
        diagnostics.extend(block_diagnostics)

    return consumers_by_signal, diagnostics

def logic_assigns_signal(
    text: str,
    signal_name: str,
) -> bool:
    """Return whether logic assigns the specified signal."""

    pattern = (
        r"(?m)^\s*"
        + re.escape(signal_name)
        + r"\s*="
    )

    return re.search(pattern, text) is not None

def validate_final_structure(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
    enumerated_values: dict[str, list[EnumeratedValue]],
    value_ranges: dict[str, list[ValueRange]],
    polarities: dict[str, dict[str, str]],
    logic_sections: dict[str, dict[str, TextSection]],
) -> list[Diagnostic]:
    """Validate the final extracted control-input structure."""

    diagnostics: list[Diagnostic] = []

    domains_requiring_mnemonic = {
        "IR-Derived Signals",
        "Derived Flags",
    }

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        signal_attributes = attributes.get(entry.name, {})
        signal_values = enumerated_values.get(entry.name, [])
        signal_ranges = value_ranges.get(entry.name, [])
        signal_polarity = polarities.get(entry.name)
        signal_logic = logic_sections.get(entry.name, {})

        if not signal_values and not signal_ranges:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="MISSING_VALUE_ENCODING",
                    message=(
                        "Definition must contain enumerated values "
                        "or a bounded value range."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

        if signal_values and signal_ranges:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="MIXED_VALUE_ENCODING",
                    message=(
                        "Definition contains both enumerated values "
                        "and a bounded value range."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

        if entry.domain in domains_requiring_mnemonic:
            mnemonic = signal_attributes.get("mnemonic")

            if mnemonic is not None and mnemonic != entry.name:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="MNEMONIC_NAME_MISMATCH",
                        message=(
                            f"Documented mnemonic '{mnemonic}' does "
                            f"not match indexed name '{entry.name}'."
                        ),
                        source_path=block.source_path,
                        line=block.start_line,
                        signal_name=entry.name,
                    )
                )

        if entry.name.startswith("/"):
            if (
                signal_polarity is not None
                and signal_polarity.get("value") != "active-low"
            ):
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="ACTIVE_LOW_NAME_CONFLICT",
                        message=(
                            "A slash-prefixed signal must have "
                            "active-low polarity."
                        ),
                        source_path=block.source_path,
                        line=block.start_line,
                        signal_name=entry.name,
                    )
                )

        if entry.domain == "IR-Derived Signals":
            derivation = signal_logic.get("derivation")

            if derivation is not None:
                if not logic_assigns_signal(
                    derivation.text,
                    entry.name,
                ):
                    diagnostics.append(
                        Diagnostic(
                            severity="ERROR",
                            code="DERIVATION_RESULT_MISMATCH",
                            message=(
                                "Derivation does not assign the "
                                f"indexed signal '{entry.name}'."
                            ),
                            source_path=block.source_path,
                            line=derivation.line,
                            signal_name=entry.name,
                        )
                    )

        if entry.domain == "Derived Flags":
            logic_section = signal_logic.get("expression")

            if logic_section is None:
                logic_section = signal_logic.get(
                    "internal_composition"
                )

            if logic_section is not None:
                if not logic_assigns_signal(
                    logic_section.text,
                    entry.name,
                ):
                    diagnostics.append(
                        Diagnostic(
                            severity="ERROR",
                            code="DERIVED_RESULT_MISMATCH",
                            message=(
                                "Derived logic does not assign the "
                                f"indexed signal '{entry.name}'."
                            ),
                            source_path=block.source_path,
                            line=logic_section.line,
                            signal_name=entry.name,
                        )
                    )

    return diagnostics

def build_extraction_report(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
    bit_widths: dict[str, int],
    polarities: dict[str, dict[str, str]],
    enumerated_values: dict[str, list[EnumeratedValue]],
    value_ranges: dict[str, list[ValueRange]],
    dependencies: dict[str, list[DependencyEntry]],
    logic_sections: dict[str, dict[str, TextSection]],
    constraints: dict[str, list[ConstraintEntry]],
    consumers: dict[str, list[ConsumerEntry]],
    diagnostics: Sequence[Diagnostic],
) -> str:
    """Build the human-readable extraction report."""

    domain_counts: dict[str, int] = {}

    for entry in entries:
        domain_counts[entry.domain] = (
            domain_counts.get(entry.domain, 0) + 1
        )

    definitions_with_attributes = sum(
        bool(values)
        for values in attributes.values()
    )

    definitions_with_enumerated_values = sum(
        bool(values)
        for values in enumerated_values.values()
    )

    definitions_with_ranges = sum(
        bool(values)
        for values in value_ranges.values()
    )

    definitions_with_dependencies = sum(
        bool(values)
        for values in dependencies.values()
    )

    definitions_with_logic = sum(
        bool(values)
        for values in logic_sections.values()
    )

    definitions_with_constraints = sum(
        bool(values)
        for values in constraints.values()
    )

    definitions_with_consumers = sum(
        bool(values)
        for values in consumers.values()
    )

    enumerated_value_count = sum(
        len(values)
        for values in enumerated_values.values()
    )

    value_range_count = sum(
        len(values)
        for values in value_ranges.values()
    )

    dependency_count = sum(
        len(values)
        for values in dependencies.values()
    )

    logic_section_count = sum(
        len(values)
        for values in logic_sections.values()
    )

    constraint_count = sum(
        len(values)
        for values in constraints.values()
    )

    consumer_count = sum(
        len(values)
        for values in consumers.values()
    )

    linked_consumer_count = sum(
        consumer.target is not None
        for values in consumers.values()
        for consumer in values
    )

    severity_counts: dict[str, int] = {}

    for diagnostic in diagnostics:
        severity_counts[diagnostic.severity] = (
            severity_counts.get(
                diagnostic.severity,
                0,
            )
            + 1
        )

    lines = [
        "Control-Input Extraction Report",
        "===============================",
        "",
        "Summary",
        "-------",
        f"Indexed control inputs: {len(entries)}",
        f"Matched definitions: {len(definitions)}",
        (
            "Definitions with extracted attributes: "
            f"{definitions_with_attributes}"
        ),
        f"Normalized bit widths: {len(bit_widths)}",
        f"Normalized polarities: {len(polarities)}",
        (
            "Definitions with enumerated values: "
            f"{definitions_with_enumerated_values}"
        ),
        (
            "Definitions with value ranges: "
            f"{definitions_with_ranges}"
        ),
        f"Enumerated values: {enumerated_value_count}",
        f"Value ranges: {value_range_count}",
        (
            "Definitions with explicit dependencies: "
            f"{definitions_with_dependencies}"
        ),
        f"Dependencies: {dependency_count}",
        (
            "Definitions with logic sections: "
            f"{definitions_with_logic}"
        ),
        f"Logic sections: {logic_section_count}",
        (
            "Definitions with constraints: "
            f"{definitions_with_constraints}"
        ),
        f"Constraints: {constraint_count}",
        (
            "Definitions with consumers: "
            f"{definitions_with_consumers}"
        ),
        f"Consumers: {consumer_count}",
        f"Linked consumers: {linked_consumer_count}",
        f"Diagnostics: {len(diagnostics)}",
        "",
        "Inputs by Domain",
        "----------------",
    ]

    for domain_name in sorted(domain_counts):
        lines.append(
            f"{domain_name}: {domain_counts[domain_name]}"
        )

    lines.extend(
        [
            "",
            "Diagnostics by Severity",
            "-----------------------",
        ]
    )

    if severity_counts:
        for severity in sorted(severity_counts):
            lines.append(
                f"{severity}: {severity_counts[severity]}"
            )
    else:
        lines.append("None")

    lines.extend(
        [
            "",
            "Diagnostic Details",
            "------------------",
        ]
    )

    if not diagnostics:
        lines.append("No diagnostics.")
    else:
        for diagnostic in diagnostics:
            location = (
                diagnostic.source_path
                or "<unknown source>"
            )

            if diagnostic.line is not None:
                location = (
                    f"{location}:{diagnostic.line}"
                )

            signal_suffix = ""

            if diagnostic.signal_name:
                signal_suffix = (
                    f" [{diagnostic.signal_name}]"
                )

            lines.extend(
                [
                    (
                        f"{diagnostic.severity} "
                        f"{diagnostic.code}"
                        f"{signal_suffix}"
                    ),
                    f"  Source: {location}",
                    f"  {diagnostic.message}",
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def write_text_report(
    report: str,
    output_path: Path,
) -> None:
    """Write the human-readable extraction report."""

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        report,
        encoding="utf-8",
    )

def main(
    arguments: Sequence[str] | None = None,
) -> int:
    """Load sources and inspect index-to-definition coverage."""

    parsed_arguments = parse_arguments(arguments)
    paths = resolve_tool_paths(parsed_arguments)

    try:
        validate_source_paths(paths.source_paths)
        documents = load_source_documents(
            paths.source_paths,
            paths.repo_root,
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    entries, index_diagnostics = parse_index(documents[0])
    indexed_names = {entry.name for entry in entries}

    definition_blocks: list[DefinitionBlock] = []

    for document in documents[1:]:
        document_blocks = extract_definition_blocks(
            document,
            indexed_names,
        )
        definition_blocks.extend(document_blocks)

    definitions, definition_diagnostics = match_definition_blocks(
        entries,
        definition_blocks,
    )

    attributes, attribute_diagnostics = extract_all_scalar_attributes(
        definitions
    )

    required_attribute_diagnostics = validate_required_attributes(
        entries,
        definitions,
        attributes,
    )

    bit_widths, bit_width_diagnostics = normalize_bit_widths(
        definitions,
        attributes,
    )

    polarities, polarity_diagnostics = normalize_polarities(
        definitions,
        attributes,
    )
    
    enumerated_values, value_ranges, value_diagnostics = (
    extract_all_definition_values(definitions)
    )
    
    value_width_diagnostics = validate_values_against_widths(
        definitions,
        bit_widths,
        enumerated_values,
        value_ranges,
    )

    dependencies, dependency_extraction_diagnostics = (
        extract_all_definition_dependencies(definitions)
    )

    dependency_validation_diagnostics = validate_derived_dependencies(
        entries,
        definitions,
        dependencies,
    )

    logic_sections, logic_extraction_diagnostics = (
        extract_all_logic_sections(definitions)
    )

    logic_validation_diagnostics = validate_required_logic_sections(
        entries,
        definitions,
        logic_sections,
    )

    definitions_with_logic = sum(
        bool(sections)
        for sections in logic_sections.values()
    )

    logic_section_count = sum(
        len(sections)
        for sections in logic_sections.values()
    )

    constraints, constraint_diagnostics = (
        extract_all_definition_constraints(definitions)
    )
    
    consumers, consumer_diagnostics = (
        extract_all_definition_consumers(definitions)
    )
    
    final_structure_diagnostics = validate_final_structure(
        entries,
        definitions,
        attributes,
        enumerated_values,
        value_ranges,
        polarities,
        logic_sections,
    )
        
    diagnostics = index_diagnostics + definition_diagnostics
    diagnostics += attribute_diagnostics
    diagnostics += bit_width_diagnostics
    diagnostics += polarity_diagnostics
    diagnostics += value_diagnostics
    diagnostics += value_width_diagnostics
    diagnostics += required_attribute_diagnostics
    diagnostics += dependency_extraction_diagnostics
    diagnostics += dependency_validation_diagnostics
    diagnostics += logic_extraction_diagnostics
    diagnostics += logic_validation_diagnostics
    diagnostics += logic_extraction_diagnostics
    diagnostics += logic_validation_diagnostics
    diagnostics += constraint_diagnostics
    diagnostics += consumer_diagnostics
    diagnostics += final_structure_diagnostics
    
    result = build_json_result(
        entries,
        definitions,
        attributes,
        bit_widths,
        polarities,
        enumerated_values,
        value_ranges,
        dependencies,
        logic_sections,
        constraints,
        consumers,
        diagnostics,
    )

    write_json_output(
        result,
        paths.json_output,
    )

    report_output = paths.json_output.with_name(
        "extraction-report.txt"
    )

    report = build_extraction_report(
        entries,
        definitions,
        attributes,
        bit_widths,
        polarities,
        enumerated_values,
        value_ranges,
        dependencies,
        logic_sections,
        constraints,
        consumers,
        diagnostics,
    )

    write_text_report(
        report,
        report_output,
    )

    print(f"Repository root: {paths.repo_root}")
    print(f"Source documents loaded: {len(documents)}")
    print(f"Indexed control inputs: {len(entries)}")
    print()

    for document in documents[1:]:
        document_block_count = sum(
            block.source_path == document.relative_path
            for block in definition_blocks
        )

        print(
            f"{document.relative_path}: "
            f"{document_block_count} definition blocks"
        )

    print()
    print(f"Definition blocks found: {len(definition_blocks)}")
    print(f"Definitions matched: {len(definitions)}")
    definitions_with_attributes = sum(
        bool(values)
        for values in attributes.values()
    )

    print(
        "Definitions with extracted attributes: "
        f"{definitions_with_attributes}"
    )

    definitions_without_attributes = sorted(
        signal_name
        for signal_name, values in attributes.items()
        if not values
    )

    if definitions_without_attributes:
        print()
        print("Definitions without extracted scalar attributes:")

        for signal_name in definitions_without_attributes:
            print(f"  {signal_name}")

    print(f"Bit widths normalized: {len(bit_widths)}")
    print(f"Polarities normalized: {len(polarities)}")
    
    definitions_with_enumerated_values = sum(
        bool(values)
        for values in enumerated_values.values()
    )

    definitions_with_ranges = sum(
        bool(ranges)
        for ranges in value_ranges.values()
    )

    enumerated_value_count = sum(
        len(values)
        for values in enumerated_values.values()
    )

    value_range_count = sum(
        len(ranges)
        for ranges in value_ranges.values()
    )

    print(
        "Definitions with enumerated values: "
        f"{definitions_with_enumerated_values}"
    )
    print(
        "Definitions with value ranges: "
        f"{definitions_with_ranges}"
    )
    print(f"Enumerated values extracted: {enumerated_value_count}")
    print(f"Value ranges extracted: {value_range_count}")

    print(f"Diagnostics: {len(diagnostics)}")

    definitions_with_dependencies = sum(
        bool(values)
        for values in dependencies.values()
    )

    dependency_count = sum(
        len(values)
        for values in dependencies.values()
    )

    print(
        "Definitions with explicit dependencies: "
        f"{definitions_with_dependencies}"
    )
    print(f"Dependencies extracted: {dependency_count}")

    print(
        "Definitions with logic sections: "
        f"{definitions_with_logic}"
    )
    print(f"Logic sections extracted: {logic_section_count}")


    if diagnostics:
        print()
        print("Diagnostics")

        for diagnostic in diagnostics:
            location = diagnostic.source_path or "<unknown source>"

            if diagnostic.line is not None:
                location = f"{location}:{diagnostic.line}"

            signal_suffix = ""

            if diagnostic.signal_name:
                signal_suffix = f" [{diagnostic.signal_name}]"

            print(
                f"{diagnostic.severity} "
                f"{diagnostic.code}{signal_suffix}"
            )
            print(f"  Source: {location}")
            print(f"  {diagnostic.message}")

    definitions_with_constraints = sum(
        bool(values)
        for values in constraints.values()
    )

    constraint_count = sum(
        len(values)
        for values in constraints.values()
    )

    print(
        "Definitions with constraints: "
        f"{definitions_with_constraints}"
    )
    print(f"Constraints extracted: {constraint_count}")
    
    definitions_with_consumers = sum(
        bool(values)
        for values in consumers.values()
    )

    consumer_count = sum(
        len(values)
        for values in consumers.values()
    )

    linked_consumer_count = sum(
        consumer.target is not None
        for values in consumers.values()
        for consumer in values
    )

    print(
        "Definitions with consumers: "
        f"{definitions_with_consumers}"
    )
    print(f"Consumers extracted: {consumer_count}")
    print(f"Linked consumers extracted: {linked_consumer_count}")

    print(f"JSON output written: {paths.json_output}")
    print(f"Report output written: {report_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

