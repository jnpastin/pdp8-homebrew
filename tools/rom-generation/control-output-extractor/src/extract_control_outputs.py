"""Extract candidate control-output definitions from project documentation."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
import json
import re


DEFAULT_JSON_OUTPUT = Path(
    "build/simulation_outputs/rom-generation/"
    "control-output-extractor/control-outputs.json"
)

DEFAULT_REPORT_OUTPUT = Path(
    "build/simulation_outputs/rom-generation/"
    "control-output-extractor/extraction-report.txt"
)

SOURCE_PATHS = (
    Path("docs/04-control/20-control-output-definitions/00-index.md"),
    Path(
        "docs/04-control/20-control-output-definitions/"
        "01-microarchitectural-control-signals.md"
    ),
    Path(
        "docs/04-control/20-control-output-definitions/"
        "02-architectural-control-signals.md"
    ),
    Path(
        "docs/04-control/20-control-output-definitions/"
        "03-sequencing-control-signals.md"
    ),
)


@dataclass(frozen=True)
class ToolPaths:
    """Resolved input and output paths used for one extraction run."""

    repo_root: Path
    source_paths: tuple[Path, ...]
    json_output: Path
    report_output: Path

@dataclass(frozen=True)
class SourceDocument:
    """Text loaded from one authoritative source document."""

    path: Path
    text: str
    
@dataclass(frozen=True)
class IndexEntry:
    """One control-output signal listed in the authoritative index."""

    name: str
    category: str
    source_path: str
    line: int


@dataclass(frozen=True)
class Diagnostic:
    """One informational, warning, or error condition."""

    severity: str
    code: str
    message: str
    source_path: str | None = None
    line: int | None = None
    signal_name: str | None = None
    
@dataclass(frozen=True)
class DefinitionBlock:
    """Markdown content associated with one signal-definition heading."""

    heading: str
    source_path: str
    start_line: int
    lines: tuple[str, ...]
    
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

def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line argument parser."""

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
        help="Path to the root of the pdp8-homebrew repository.",
    )

    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help=(
            "JSON output path. Relative paths are resolved from the "
            "repository root."
        ),
    )

    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help=(
            "Text report output path. Relative paths are resolved from the "
            "repository root."
        ),
    )

    return parser


def resolve_from_repo(repo_root: Path, path: Path) -> Path:
    """Resolve a path relative to the repository unless already absolute."""

    if path.is_absolute():
        return path.resolve()

    return (repo_root / path).resolve()


def resolve_tool_paths(
    repo_root: Path,
    json_output: Path = DEFAULT_JSON_OUTPUT,
    report_output: Path = DEFAULT_REPORT_OUTPUT,
) -> ToolPaths:
    """Resolve and validate paths needed by the extractor."""

    resolved_repo_root = repo_root.expanduser().resolve()

    if not resolved_repo_root.is_dir():
        raise ValueError(
            f"Repository root does not exist or is not a directory: "
            f"{resolved_repo_root}"
        )

    return ToolPaths(
        repo_root=resolved_repo_root,
        source_paths=tuple(
            resolve_from_repo(resolved_repo_root, path)
            for path in SOURCE_PATHS
        ),
        json_output=resolve_from_repo(resolved_repo_root, json_output),
        report_output=resolve_from_repo(resolved_repo_root, report_output),
    )

def validate_source_paths(source_paths: Sequence[Path]) -> None:
    """Verify that every required source exists and is a regular file."""

    missing_paths = [path for path in source_paths if not path.is_file()]

    if missing_paths:
        formatted_paths = "\n".join(
            f"  - {path}" for path in missing_paths
        )
        raise FileNotFoundError(
            "Required source files are missing:\n"
            f"{formatted_paths}"
        )


def read_document(path: Path) -> SourceDocument:
    """Read one source document as UTF-8 text."""

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            f"Source file is not valid UTF-8: {path}"
        ) from error
    except OSError as error:
        raise OSError(
            f"Unable to read source file: {path}"
        ) from error

    return SourceDocument(path=path, text=text)


def read_source_documents(
    source_paths: Sequence[Path],
) -> tuple[SourceDocument, ...]:
    """Validate and load all required source documents."""

    validate_source_paths(source_paths)
    return tuple(read_document(path) for path in source_paths)
    

def parse_arguments(arguments: Sequence[str] | None = None) -> ToolPaths:
    """Parse command-line arguments and return resolved tool paths."""

    parser = build_argument_parser()
    namespace = parser.parse_args(arguments)

    try:
        return resolve_tool_paths(
            repo_root=namespace.repo_root,
            json_output=namespace.json_output,
            report_output=namespace.report_output,
        )
    except ValueError as error:
        parser.error(str(error))

def repository_relative_path(path: Path, repo_root: Path) -> str:
    """Return a POSIX-style path for a source located under the repository"""

    return path.relative_to(repo_root).as_posix()


def extract_definition_blocks(
    document: SourceDocument,
    repo_root: Path,
) -> list[DefinitionBlock]:
    """Split a control-output document into signal-definition blocks."""

    lines = document.text.splitlines()
    source_path = repository_relative_path(document.path, repo_root)

    blocks: list[DefinitionBlock] = []
    in_definition_section = False
    current_heading: str | None = None
    current_start_line: int | None = None
    current_lines: list[str] = []

    def finish_current_block() -> None:
        if current_heading is None or current_start_line is None:
            return

        blocks.append(
            DefinitionBlock(
                heading=normalize_signal_name(current_heading),
                source_path=source_path,
                start_line=current_start_line,
                lines=tuple(current_lines),
            )
        )

    for line_number, line in enumerate(lines, start=1):
        heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)

        if heading_match:
            heading_level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()

            # Remove an optional numeric section prefix such as "4." or "4.1".
            normalized_heading = re.sub(
                r"^\d+(?:\.\d+)*\.?\s+",
                "",
                heading_text,
            )

            if heading_level == 2:
                if normalized_heading.casefold() == "signal definitions":
                    in_definition_section = True
                    continue

                if in_definition_section:
                    finish_current_block()
                    break

            if in_definition_section and heading_level == 3:
                finish_current_block()
                current_heading = normalized_heading
                current_start_line = line_number
                current_lines = []
                continue

        if in_definition_section and current_heading is not None:
            current_lines.append(line)

    else:
        finish_current_block()

    return blocks

def parse_index(
    document: SourceDocument,
    repo_root: Path,
) -> tuple[list[IndexEntry], list[Diagnostic]]:
    """Extract linked signal entries from the control-output index."""

    entries: list[IndexEntry] = []
    diagnostics: list[Diagnostic] = []
    category = "uncategorized"
    source_path = repository_relative_path(document.path, repo_root)

    category_pattern = re.compile(
        r"^#{3}\s+(?:\d+(?:\.\d+)*\s+)?(.+?)\s*$"
    )
    
    entry_pattern = re.compile(
        r"^\s*-\s+\[(.+?)\]\(([^)]+)\)\s*$"
    )

    seen_names: dict[str, int] = {}

    for line_number, line in enumerate(document.text.splitlines(), start=1):
        category_match = category_pattern.match(line)
        if category_match:
            category = category_match.group(1).strip()
            continue

        entry_match = entry_pattern.match(line)
        if not entry_match:
            continue

        link_text, link_target = entry_match.groups()

        # Only links to the three control-output definition documents are
        # signal index entries. Other links provide document context.
        if not link_target.startswith(
            (
                "./01-microarchitectural-control-signals.md#",
                "./02-architectural-control-signals.md#",
                "./03-sequencing-control-signals.md#",
            )
        ):
            continue

        signal_name = normalize_signal_name(link_text.strip())

        if signal_name in seen_names:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_INDEX_ENTRY",
                    message=(
                        f"Signal is already indexed at line "
                        f"{seen_names[signal_name]}."
                    ),
                    source_path=source_path,
                    line=line_number,
                    signal_name=signal_name,
                )
            )
            continue

        seen_names[signal_name] = line_number
        entries.append(
            IndexEntry(
                name=signal_name,
                category=category,
                source_path=source_path,
                line=line_number,
            )
        )

    if not entries:
        diagnostics.append(
            Diagnostic(
                severity="ERROR",
                code="NO_INDEX_ENTRIES",
                message="No control-output signal entries were found.",
                source_path=source_path,
            )
        )

    return entries, diagnostics


def diagnostic_to_dict(diagnostic: Diagnostic) -> dict[str, object]:
    """Convert a diagnostic into its JSON representation."""

    return {
        "severity": diagnostic.severity,
        "code": diagnostic.code,
        "message": diagnostic.message,
        "source_path": diagnostic.source_path,
        "line": diagnostic.line,
        "signal_name": diagnostic.signal_name,
    }


def build_index_result(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
    bit_widths: dict[str, int],
    encodings: dict[str, list[EncodingEntry]],
    constraints: dict[str, list[ConstraintEntry]],
    diagnostics: Sequence[Diagnostic],
) -> dict[str, object]:
    """Build the generated control-output extraction result."""

    signals = []

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            definition = None
            extraction_status = "definition-missing"
        else:
            definition = {
                "heading": block.heading,
                "attributes": {
                    key: value
                    for key, value in attributes.get(entry.name, {}).items()
                    if key != "bit_width"
                },
                "bit_width": bit_widths.get(entry.name),
                "encodings": [
                    {
                        "value": encoding.value,
                        "meaning": encoding.meaning,
                        "source": {
                            "path": block.source_path,
                            "line": encoding.line,
                        },
                    }
                    for encoding in encodings.get(entry.name, [])
                ],
                "constraints": [
                    {
                        "text": constraint.text,
                        "source": {
                            "path": block.source_path,
                            "line": constraint.line,
                        },
                    }
                    for constraint in constraints.get(entry.name, [])
                ],
                "source": {
                    "path": block.source_path,
                    "line": block.start_line,
                },
            }
            extraction_status = "category-validated"

        signals.append(
            {
                "name": entry.name,
                "category": entry.category,
                "definition": definition,
                "source": {
                    "path": entry.source_path,
                    "line": entry.line,
                },
                "extraction_status": extraction_status,
            }
        )

    return {
        "format_version": 1,
        "extraction_stage": "category-validation",
        "signals": signals,
        "diagnostics": [
            diagnostic_to_dict(diagnostic)
            for diagnostic in diagnostics
        ],
    }

def write_json_output(result: dict[str, object], path: Path) -> None:
    """Write deterministic, human-readable JSON output."""

    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )
    path.write_text(serialized + "\n", encoding="utf-8")


def write_report(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
    bit_widths: dict[str, int],
    encodings: dict[str, list[EncodingEntry]],
    constraints: dict[str, list[ConstraintEntry]],
    diagnostics: Sequence[Diagnostic],
    path: Path,
) -> None:
    """Write a readable extraction summary and diagnostic report."""

    path.parent.mkdir(parents=True, exist_ok=True)

    severity_counts = {
        severity: sum(
            diagnostic.severity == severity
            for diagnostic in diagnostics
        )
        for severity in ("INFO", "WARNING", "ERROR", "FATAL")
    }

    signals_with_attributes = sum(
        bool(signal_attributes)
        for signal_attributes in attributes.values()
    )
    
    signals_with_encodings = sum(
        bool(signal_encodings)
        for signal_encodings in encodings.values()
    )

    encoding_count = sum(
        len(signal_encodings)
        for signal_encodings in encodings.values()
    )
    
    signals_with_constraints = sum(
        bool(signal_constraints)
        for signal_constraints in constraints.values()
    )

    constraint_count = sum(
        len(signal_constraints)
        for signal_constraints in constraints.values()
    )
    
    lines = [
        "Control Output Extraction Report",
        "================================",
        "",
        "Stage: category validation",
        f"Indexed signals: {len(entries)}",
        f"Matched definitions: {len(definitions)}",
        f"Definitions with extracted attributes: {signals_with_attributes}",
        f"Definitions with normalized bit widths: {len(bit_widths)}",
        f"Definitions with extracted encodings: {signals_with_encodings}",
        f"Encoding entries extracted: {encoding_count}",
        f"Definitions with extracted constraints: {signals_with_constraints}",
        f"Constraint entries extracted: {constraint_count}",
        f"Missing definitions: {len(entries) - len(definitions)}",
        f"Informational diagnostics: {severity_counts['INFO']}",
        f"Warnings: {severity_counts['WARNING']}",
        f"Errors: {severity_counts['ERROR']}",
        f"Fatal errors: {severity_counts['FATAL']}",
        "",
        "Diagnostics",
        "-----------",
    ]
    
    if not diagnostics:
        lines.append("None.")
    else:
        for diagnostic in diagnostics:
            location = diagnostic.source_path or "<unknown source>"

            if diagnostic.line is not None:
                location = f"{location}:{diagnostic.line}"

            signal = (
                f" [{diagnostic.signal_name}]"
                if diagnostic.signal_name
                else ""
            )

            lines.append(
                f"{diagnostic.severity} {diagnostic.code}{signal}"
            )
            lines.append(f"  Source: {location}")
            lines.append(f"  {diagnostic.message}")
            lines.append("")

    path.write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )

def find_signal_in_heading(
    heading: str,
    indexed_names: set[str],
) -> str | None:
    """Find the indexed signal name represented by a definition heading."""

    normalized_heading = normalize_signal_name(heading)

    if normalized_heading in indexed_names:
        return normalized_heading

    parenthesized_name = re.search(
        r"\(([^()]+)\)\s*$",
        normalized_heading,
    )

    if parenthesized_name is None:
        return None

    candidate = parenthesized_name.group(1).strip()

    if candidate in indexed_names:
        return candidate

    return None


def match_definition_blocks(
    entries: Sequence[IndexEntry],
    blocks: Sequence[DefinitionBlock],
) -> tuple[dict[str, DefinitionBlock], list[Diagnostic]]:
    """Match definition blocks to indexed signals and report mismatches."""

    indexed_names = {entry.name for entry in entries}
    entry_by_name = {entry.name: entry for entry in entries}

    matched_blocks: dict[str, DefinitionBlock] = {}
    diagnostics: list[Diagnostic] = []

    for block in blocks:
        signal_name = find_signal_in_heading(
            block.heading,
            indexed_names,
        )

        if signal_name is None:
            diagnostics.append(
                Diagnostic(
                    severity="WARNING",
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

        if signal_name in matched_blocks:
            first_block = matched_blocks[signal_name]
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_DEFINITION",
                    message=(
                        "Signal has more than one definition block. "
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

        matched_blocks[signal_name] = block

    for signal_name in sorted(indexed_names - matched_blocks.keys()):
        entry = entry_by_name[signal_name]
        diagnostics.append(
            Diagnostic(
                severity="ERROR",
                code="MISSING_DEFINITION",
                message="Indexed signal has no matching definition block.",
                source_path=entry.source_path,
                line=entry.line,
                signal_name=signal_name,
            )
        )

    return matched_blocks, diagnostics
    
ATTRIBUTE_NAMES = {
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
}


def parse_definition_attributes(
    signal_name: str,
    block: DefinitionBlock,
) -> tuple[dict[str, str], list[Diagnostic]]:
    """Extract scalar attributes from one definition block."""

    attributes: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []

    attribute_pattern = re.compile(
        r"^\s*\*\*(.+?):?\*\*\s*:?\s*(.*?)\s*$"
    )

    for offset, line in enumerate(block.lines, start=1):
        match = attribute_pattern.match(line)

        if not match:
            continue

        documented_name = match.group(1).strip().rstrip(":").casefold()
        value = match.group(2).strip()
        attribute_name = ATTRIBUTE_NAMES.get(documented_name)

        if attribute_name is None or not value:
            continue

        if attribute_name in attributes:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_ATTRIBUTE",
                    message=(
                        f"Attribute '{attribute_name}' is defined more "
                        "than once."
                    ),
                    source_path=block.source_path,
                    line=block.start_line + offset,
                    signal_name=signal_name,
                )
            )
            continue

        attributes[attribute_name] = normalize_signal_name(value)

    return attributes, diagnostics

ENCODING_LABELS = {
    "encoding",
    "value encoding",
}


def parse_encoding_line(line: str) -> tuple[str, str] | None:
    """Parse one enumerated encoding entry."""

    stripped = line.strip()

    if stripped.startswith("- "):
        stripped = stripped[2:].strip()

    match = re.match(
        r"^([A-Za-z0-9]+)\s*(?:->|→|=|:)\s*(.+?)\s*$",
        stripped,
    )

    if not match:
        return None

    value = normalize_signal_name(match.group(1).strip())
    meaning = normalize_signal_name(match.group(2).strip())

    if not value or not meaning:
        return None

    return value, meaning


def parse_definition_encodings(
    signal_name: str,
    block: DefinitionBlock,
) -> tuple[list[EncodingEntry], list[Diagnostic]]:
    """Extract enumerated encodings from one definition block."""

    encodings: list[EncodingEntry] = []
    diagnostics: list[Diagnostic] = []
    in_encoding_section = False

    label_pattern = re.compile(
        r"^\s*\*\*(.+?):?\*\*\s*:?\s*(.*?)\s*$"
    )

    for offset, line in enumerate(block.lines, start=1):
        source_line = block.start_line + offset
        stripped = line.strip()

        if stripped.startswith("```"):
            continue

        label_match = label_pattern.match(line)

        if label_match:
            label = label_match.group(1).strip().rstrip(":").casefold()
            trailing_text = label_match.group(2).strip()

            if label in ENCODING_LABELS:
                in_encoding_section = True

                if trailing_text:
                    parsed = parse_encoding_line(trailing_text)

                    if parsed is None:
                        diagnostics.append(
                            Diagnostic(
                                severity="WARNING",
                                code="MALFORMED_ENCODING",
                                message=(
                                    "Encoding text could not be parsed: "
                                    f"{trailing_text}"
                                ),
                                source_path=block.source_path,
                                line=source_line,
                                signal_name=signal_name,
                            )
                        )
                    else:
                        value, meaning = parsed
                        encodings.append(
                            EncodingEntry(
                                value=value,
                                meaning=meaning,
                                line=source_line,
                            )
                        )

                continue

            if in_encoding_section:
                break

        if not in_encoding_section:
            continue

        if not stripped:
            continue

        parsed = parse_encoding_line(line)

        if parsed is not None:
            value, meaning = parsed
            encodings.append(
                EncodingEntry(
                    value=value,
                    meaning=meaning,
                    line=source_line,
                )
            )
            continue

        if stripped.startswith("#") or stripped.startswith("**"):
            break

        is_range = re.match(
            r"^[0-9A-Fa-f]+\s*-\s*[0-9A-Fa-f]+",
            stripped,
        )
        is_source_description = stripped.casefold() in {
            "external bus value",
            "memory bus value",
        }
        is_explanatory_label = stripped.casefold() == "where:"
        is_bit_slice_expression = "[" in stripped

        if (
            is_range
            or is_source_description
            or is_explanatory_label
            or is_bit_slice_expression
        ):
            continue

        diagnostics.append(
            Diagnostic(
                severity="WARNING",
                code="MALFORMED_ENCODING",
                message=f"Encoding line could not be parsed: {stripped}",
                source_path=block.source_path,
                line=source_line,
                signal_name=signal_name,
            )
        )

    seen_values: dict[str, int] = {}

    for encoding in encodings:
        if encoding.value in seen_values:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="DUPLICATE_ENCODING_VALUE",
                    message=(
                        f"Encoding value '{encoding.value}' is already "
                        f"defined at line {seen_values[encoding.value]}."
                    ),
                    source_path=block.source_path,
                    line=encoding.line,
                    signal_name=signal_name,
                )
            )
            continue

        seen_values[encoding.value] = encoding.line

    return encodings, diagnostics

def extract_all_definition_encodings(
    definitions: dict[str, DefinitionBlock],
) -> tuple[dict[str, list[EncodingEntry]], list[Diagnostic]]:
    """Extract encodings from all matched definitions."""

    extracted: dict[str, list[EncodingEntry]] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        encodings, block_diagnostics = parse_definition_encodings(
            signal_name,
            block,
        )

        extracted[signal_name] = encodings
        diagnostics.extend(block_diagnostics)

    return extracted, diagnostics

def parse_definition_constraints(
    block: DefinitionBlock,
) -> list[ConstraintEntry]:
    """Extract top-level items from a definition's Constraints section."""

    constraints: list[ConstraintEntry] = [] 
    in_constraints_section = False

    label_pattern = re.compile(
        r"^\s*\*\*(.+?):?\*\*\s*:?\s*(.*?)\s*$"
    )

    for offset, line in enumerate(block.lines, start=1):
        source_line = block.start_line + offset
        stripped = line.strip()
        label_match = label_pattern.match(line)

        if label_match:
            label = label_match.group(1).strip().rstrip(":").casefold()

            if label == "constraints":
                in_constraints_section = True
                continue

            if in_constraints_section:
                break

        if not in_constraints_section:
            continue

        if stripped.startswith("- "):
            constraints.append(
                ConstraintEntry(
                    text=normalize_signal_name(stripped[2:].strip()),
                    line=source_line,
                )
            )

    return constraints


def extract_all_definition_constraints(
    definitions: dict[str, DefinitionBlock],
) -> dict[str, list[ConstraintEntry]]:
    """Extract constraints from all matched definitions."""

    return {
        signal_name: parse_definition_constraints(block)
        for signal_name, block in definitions.items()
    }
    
    
def extract_all_definition_attributes(
    definitions: dict[str, DefinitionBlock],
) -> tuple[dict[str, dict[str, str]], list[Diagnostic]]:
    """Extract scalar attributes from all matched definitions."""

    extracted: dict[str, dict[str, str]] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        attributes, block_diagnostics = parse_definition_attributes(
            signal_name,
            block,
        )

        extracted[signal_name] = attributes
        diagnostics.extend(block_diagnostics)

    return extracted, diagnostics

def validate_definition_attributes(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
) -> list[Diagnostic]:
    """Report missing attributes required for usable signal definitions."""

    diagnostics = []

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        signal_attributes = attributes.get(entry.name, {})

        if "bit_width" not in signal_attributes:
            diagnostics.append(
                Diagnostic(
                    severity="WARNING",
                    code="MISSING_BIT_WIDTH",
                    message="Definition does not specify a bit width.",
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

        if not any(
            name in signal_attributes
            for name in ("purpose", "description")
        ):
            diagnostics.append(
                Diagnostic(
                    severity="WARNING",
                    code="MISSING_DESCRIPTION",
                    message=(
                        "Definition does not specify a purpose or "
                        "description."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

    return diagnostics

def validate_documented_mnemonics(
    definitions: dict[str, DefinitionBlock],
    attributes: dict[str, dict[str, str]],
) -> list[Diagnostic]:
    """Report documented mnemonics that differ from indexed signal names."""

    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        documented_mnemonic = attributes.get(
            signal_name,
            {},
        ).get("mnemonic")

        if documented_mnemonic is None:
            continue

        if documented_mnemonic != signal_name:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="MNEMONIC_MISMATCH",
                    message=(
                        f"Documented mnemonic '{documented_mnemonic}' "
                        f"does not match indexed signal '{signal_name}'."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=signal_name,
                )
            )

    return diagnostics

def validate_category_requirements(
    entries: Sequence[IndexEntry],
    definitions: dict[str, DefinitionBlock],
    bit_widths: dict[str, int],
    encodings: dict[str, list[EncodingEntry]],
) -> list[Diagnostic]:
    """Validate structural requirements associated with signal categories."""

    diagnostics: list[Diagnostic] = []

    categories_requiring_encodings = {
        "Enable Signals",
        "Select Signals",
        "Control Flow",
    }

    for entry in entries:
        block = definitions.get(entry.name)

        if block is None:
            continue

        bit_width = bit_widths.get(entry.name)
        signal_encodings = encodings.get(entry.name, [])

        if entry.category == "Enable Signals" and bit_width != 1:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="INVALID_ENABLE_WIDTH",
                    message=(
                        "An enable signal must have a bit width of 1."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

        if (
            entry.category in categories_requiring_encodings
            and not signal_encodings
        ):
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="MISSING_ENUMERATED_ENCODINGS",
                    message=(
                        f"Signals in category '{entry.category}' must "
                        "define enumerated encodings."
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=entry.name,
                )
            )

    return diagnostics

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
    """Normalize documented bit widths and report invalid values."""

    bit_widths: dict[str, int] = {}
    diagnostics: list[Diagnostic] = []

    for signal_name, block in definitions.items():
        documented_width = attributes.get(
            signal_name,
            {},
        ).get("bit_width")

        if documented_width is None:
            continue

        bit_width = parse_bit_width(documented_width)

        if bit_width is None:
            diagnostics.append(
                Diagnostic(
                    severity="ERROR",
                    code="INVALID_BIT_WIDTH",
                    message=(
                        "Bit width must be a positive integer, optionally "
                        f"followed by 'bit' or 'bits': {documented_width}"
                    ),
                    source_path=block.source_path,
                    line=block.start_line,
                    signal_name=signal_name,
                )
            )
            continue

        bit_widths[signal_name] = bit_width

    return bit_widths, diagnostics

def parse_octal_encoding(value: str) -> int | None:
    """Parse an octal encoding value."""

    if re.fullmatch(r"[0-7]+", value) is None:
        return None

    return int(value, 8)


def validate_encoding_widths(
    definitions: dict[str, DefinitionBlock],
    bit_widths: dict[str, int],
    encodings: dict[str, list[EncodingEntry]],
) -> list[Diagnostic]:
    """Validate octal encoding values against documented bit widths."""

    diagnostics: list[Diagnostic] = []
    for signal_name, signal_encodings in encodings.items():
        block = definitions.get(signal_name)
        bit_width = bit_widths.get(signal_name)

        if block is None or bit_width is None:
            continue

        maximum_value = (1 << bit_width) - 1

        for encoding in signal_encodings:
            numeric_value = parse_octal_encoding(encoding.value)

            if numeric_value is None:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="INVALID_OCTAL_ENCODING",
                        message=(
                            "Encoding value is not valid octal: "
                            f"{encoding.value}"
                        ),
                        source_path=block.source_path,
                        line=encoding.line,
                        signal_name=signal_name,
                    )
                )
                continue

            if numeric_value > maximum_value:
                diagnostics.append(
                    Diagnostic(
                        severity="ERROR",
                        code="ENCODING_EXCEEDS_BIT_WIDTH",
                        message=(
                            f"Octal encoding {encoding.value} has numeric "
                            f"value {numeric_value}, which does not fit in "
                            f"the documented {bit_width}-bit field."
                        ),
                        source_path=block.source_path,
                        line=encoding.line,
                        signal_name=signal_name,
                    )
                )

    return diagnostics

def normalize_signal_name(value: str) -> str:
    """Remove Markdown escaping and inline-code markers."""

    return (
        value.replace("\\_", "_")
        .replace("\\[", "[")
        .replace("\\]", "]")
        .replace("`", "")
        .strip()
    )

def main(arguments: Sequence[str] | None = None) -> int:
    """Match documented control-output definitions to the signal index."""

    paths = parse_arguments(arguments)

    try:
        documents = read_source_documents(paths.source_paths)

        index_entries, index_diagnostics = parse_index(
            documents[0],
            paths.repo_root,
        )

        definition_blocks: list[DefinitionBlock] = []

        for document in documents[1:]:
            definition_blocks.extend(
                extract_definition_blocks(
                    document,
                    paths.repo_root,
                )
            )

        definitions, definition_diagnostics = match_definition_blocks(
            index_entries,
            definition_blocks,
        )
        
        attributes, attribute_diagnostics = (
            extract_all_definition_attributes(definitions)
        )

        mnemonic_diagnostics = validate_documented_mnemonics(
            definitions,
            attributes,
        )
        
        attribute_validation_diagnostics = (
            validate_definition_attributes(
                index_entries,
                definitions,
                attributes,
            )
        )
        
        bit_widths, bit_width_diagnostics = normalize_bit_widths(
            definitions,
            attributes,
        )
 
        encodings, encoding_diagnostics = (
            extract_all_definition_encodings(definitions)
        )
        
        encoding_width_diagnostics = validate_encoding_widths(
            definitions,
            bit_widths,
            encodings,
        )
 
        category_diagnostics = validate_category_requirements(
            index_entries,
            definitions,
            bit_widths,
            encodings,
        )

        constraints = extract_all_definition_constraints(
            definitions
        )
        
        diagnostics = [
            *index_diagnostics,
            *definition_diagnostics,
            *attribute_diagnostics,
            *attribute_validation_diagnostics,
            *mnemonic_diagnostics,
            *bit_width_diagnostics,
            *encoding_diagnostics,
            *encoding_width_diagnostics,
            *category_diagnostics,
        ]

        result = build_index_result(
            index_entries,
            definitions,
            attributes,
            bit_widths,
            encodings,
            constraints,
            diagnostics,
        )

        write_json_output(result, paths.json_output)
        write_report(
            index_entries,
            definitions,
            attributes,
            bit_widths,
            encodings,
            constraints,
            diagnostics,
            paths.report_output,
        )
    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    print(f"Repository root: {paths.repo_root}")
    print(f"Source documents loaded: {len(documents)}")
    print(f"Indexed signals found: {len(index_entries)}")
    print(f"Definition blocks found: {len(definition_blocks)}")
    print(f"Definitions matched: {len(definitions)}")
    print(f"Bit widths normalized: {len(bit_widths)}")
    print(f"Definitions with attributes: {len(attributes)}")
    print(
        "Encoding entries extracted: "
        f"{sum(len(values) for values in encodings.values())}"
    )
    print(
        "Constraint entries extracted: "
        f"{sum(len(values) for values in constraints.values())}"
    )
    print(f"Diagnostics reported: {len(diagnostics)}")
    print(f"JSON output written: {paths.json_output}")
    print(f"Report output written: {paths.report_output}")

    return 0



if __name__ == "__main__":
    raise SystemExit(main())
