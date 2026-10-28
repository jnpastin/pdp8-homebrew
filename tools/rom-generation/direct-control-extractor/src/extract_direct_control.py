"""Extract direct-control case definitions from authoritative Markdown."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

SOURCE_PATHS = (
    Path("docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md"),
    Path("docs/04-control/30-direct-control-definitions/02-interface-and-ownership-control.md"),
)
DEFAULT_JSON_OUTPUT = Path(
    "build/simulation_outputs/rom-generation/"
    "direct-control-extractor/direct-control-definitions.json"
)
DEFAULT_REPORT_OUTPUT = Path(
    "build/simulation_outputs/rom-generation/"
    "direct-control-extractor/extraction-report.txt"
)
FORMAT_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"
FAILURE_SEVERITIES = {"ERROR", "FATAL"}
SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "FATAL": 3}

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
CODE_FIELDS = {
    "applicable_context",
    "direct_assignments",
    "control_supplied_values",
    "micro_operation_assignments",
    "state_commits",
    "drive_states",
    "external_ownership",
    "memory_behavior",
    "derived_values",
    "value_relationships",
    "widths",
}
NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$")
HEADING = re.compile(r"^(#{2,4})\s+(.+?)\s*$")
LABEL = re.compile(r"^([^#`|].*?):\s*$")
CODE_BLOCK = re.compile(r"```(?:text)?\s*\n(.*?)\n```", re.DOTALL)
MARKDOWN_LINK = re.compile(r"\[([^]]+)\]\(([^)]+)\)")
BULLET = re.compile(r"^\s*-\s+(.+?)\s*$")


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    source_path: str
    line: int | None = None
    definition_id: str | None = None


@dataclass(frozen=True)
class Heading:
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
    """Raised when extraction cannot produce a reliable artifact."""


def resolve_from_repo(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def repository_relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def read_source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ExtractionFailure(f"Required source does not exist: {path}") from error
    except UnicodeDecodeError as error:
        raise ExtractionFailure(f"Source is not valid UTF-8: {path}") from error
    except OSError as error:
        raise ExtractionFailure(f"Unable to read source {path}: {error}") from error


def parse_headings(lines: Sequence[str]) -> list[Heading]:
    headings: list[Heading] = []
    for line_number, line in enumerate(lines, 1):
        heading_match = HEADING.match(line)
        if not heading_match:
            continue
        raw_title = heading_match.group(2)
        title_match = NUMBERED_HEADING.match(raw_title)
        headings.append(
            Heading(
                level=len(heading_match.group(1)),
                number=title_match.group(1) if title_match else None,
                title=title_match.group(2) if title_match else raw_title,
                line=line_number,
            )
        )
    return headings


def heading_body(lines: Sequence[str], headings: Sequence[Heading], index: int) -> list[str]:
    heading = headings[index]
    end = len(lines) + 1
    for later in headings[index + 1 :]:
        if later.level <= heading.level:
            end = later.line
            break
    return list(lines[heading.line : end - 1])


def has_numbered_child(heading: Heading, headings: Sequence[Heading], index: int) -> bool:
    for later in headings[index + 1 :]:
        if later.level <= heading.level:
            return False
        return True
    return False


def parent_title(heading: Heading, headings: Sequence[Heading], index: int) -> str | None:
    for earlier in reversed(headings[:index]):
        if earlier.level < heading.level:
            return earlier.full_title
    return None


def collect_sections(lines: Sequence[str]) -> tuple[dict[str, list[str]], list[str]]:
    sections: dict[str, list[str]] = {}
    unknown_labels: list[str] = []
    current: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if current is not None:
            text = "\n".join(buffer).strip()
            if text:
                sections.setdefault(current, []).append(text)
        buffer = []

    in_code_block = False
    for line in lines:
        if line.startswith("```"):
            in_code_block = not in_code_block
            if current is not None:
                buffer.append(line)
            continue
        label_match = None if in_code_block else LABEL.match(line)
        if label_match:
            label = label_match.group(1)
            if label in SECTION_LABELS:
                flush()
                current = SECTION_LABELS[label]
                continue
            if current is not None:
                flush()
                current = None
            if label and not label.startswith(("http", "MS ", "RUN ", "HLT_REQ ")):
                unknown_labels.append(label)
            continue
        if current is not None:
            buffer.append(line)
    flush()
    return sections, unknown_labels


def code_blocks(texts: Iterable[str]) -> list[str]:
    return [
        match.strip()
        for text in texts
        for match in CODE_BLOCK.findall(text)
        if match.strip()
    ]


def bullet_items(texts: Iterable[str]) -> list[str]:
    return [
        match.group(1)
        for text in texts
        for line in text.splitlines()
        if (match := BULLET.match(line))
    ]


def markdown_links(texts: Iterable[str]) -> list[dict[str, str]]:
    return [
        {"label": label, "target": target.strip()}
        for text in texts
        for label, target in MARKDOWN_LINK.findall(text)
    ]


def extract_code_field(
    sections: dict[str, list[str]],
    field: str,
    source_path: str,
    heading: Heading,
    diagnostics: list[Diagnostic],
) -> list[str]:
    texts = sections.get(field, [])
    if not texts:
        return []
    values = code_blocks(texts)
    if values:
        return values
    diagnostics.append(
        Diagnostic(
            "ERROR",
            "UNSTRUCTURED_FIELD",
            f"The '{field}' section must contain a text code block.",
            source_path,
            heading.line,
            stable_id(source_path, heading),
        )
    )
    return []


def stable_id(source_path: str, heading: Heading) -> str:
    if heading.number is None:
        raise ValueError("Cannot create an id for an unnumbered heading.")
    prefix = Path(source_path).stem.split("-", 1)[0]
    return f"{prefix}:{heading.number}"


def extract_definition(
    heading: Heading,
    parent: str | None,
    sections: dict[str, list[str]],
    source_path: str,
    diagnostics: list[Diagnostic],
) -> dict:
    definition = {
        "id": stable_id(source_path, heading),
        "title": heading.full_title,
        "group": parent,
        "source": {"path": source_path, "line": heading.line},
        "applicable_context": [],
        "direct_assignments": [],
        "control_supplied_values": [],
        "micro_operation_assignments": [],
        "state_commits": [],
        "value_relationships": [],
        "widths": [],
        "constraints": bullet_items(sections.get("constraints", [])),
        "sources": markdown_links(sections.get("sources", [])),
        "drive_states": [],
        "external_ownership": [],
        "memory_behavior": [],
        "derived_values": [],
    }
    for field in CODE_FIELDS:
        if field == "applicable_context":
            texts = sections.get(field, [])
            definition[field] = code_blocks(texts)
            if texts and not definition[field]:
                definition[field] = ["\n".join(texts).strip()]
            continue
        definition[field] = extract_code_field(
            sections, field, source_path, heading, diagnostics
        )
    return definition


def extract_document(text: str, source_path: str) -> tuple[list[dict], list[Diagnostic]]:
    lines = text.splitlines()
    headings = parse_headings(lines)
    definitions: list[dict] = []
    diagnostics: list[Diagnostic] = []

    for index, heading in enumerate(headings):
        if heading.number is None:
            continue
        if has_numbered_child(heading, headings, index):
            continue
        sections, unknown_labels = collect_sections(heading_body(lines, headings, index))
        if unknown_labels and any(label in {"Assignment", "Assignments", "Commit"} for label in unknown_labels):
            diagnostics.append(
                Diagnostic(
                    "ERROR",
                    "UNKNOWN_SECTION_LABEL",
                    f"Unrecognized section label: {unknown_labels[0]}",
                    source_path,
                    heading.line,
                    stable_id(source_path, heading),
                )
            )
        if not set(sections).intersection(CONTENT_FIELDS):
            continue
        definition = extract_definition(
            heading,
            parent_title(heading, headings, index),
            sections,
            source_path,
            diagnostics,
        )
        if not any(definition[field] for field in CONTENT_FIELDS):
            diagnostics.append(
                Diagnostic(
                    "ERROR",
                    "EMPTY_DEFINITION",
                    "Definition contains no extractable control or ownership result.",
                    source_path,
                    heading.line,
                    definition["id"],
                )
            )
        definitions.append(definition)

    return definitions, diagnostics


def diagnostic_key(item: Diagnostic) -> tuple:
    return (
        SEVERITY_ORDER.get(item.severity, 99),
        item.code,
        item.source_path,
        item.line if item.line is not None else -1,
        item.definition_id or "",
        item.message,
    )


def build_result(root: Path, source_paths: Sequence[Path]) -> tuple[dict, list[Diagnostic]]:
    definitions: list[dict] = []
    diagnostics: list[Diagnostic] = []
    sources: list[str] = []

    for path in source_paths:
        relative = repository_relative(path, root)
        sources.append(relative)
        extracted, found = extract_document(read_source(path), relative)
        definitions.extend(extracted)
        diagnostics.extend(found)

    seen: set[str] = set()
    for definition in definitions:
        if definition["id"] in seen:
            diagnostics.append(
                Diagnostic(
                    "ERROR",
                    "DUPLICATE_DEFINITION_ID",
                    f"Duplicate definition id: {definition['id']}",
                    definition["source"]["path"],
                    definition["source"]["line"],
                    definition["id"],
                )
            )
        seen.add(definition["id"])

    definitions.sort(key=lambda item: (item["source"]["path"], item["source"]["line"]))
    diagnostics.sort(key=diagnostic_key)
    return {
        "format_version": FORMAT_VERSION,
        "control_design_version": CONTROL_DESIGN_VERSION,
        "artifact": "direct-control-definitions",
        "extraction_stage": "documentation-extraction",
        "sources": sources,
        "definitions": definitions,
        "diagnostics": [asdict(item) for item in diagnostics],
    }, diagnostics


def write_json(result: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_report(diagnostics: Sequence[Diagnostic], path: Path, count: int) -> None:
    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in ("INFO", "WARNING", "ERROR", "FATAL")
    }
    lines = [
        "Direct-Control Extraction Report",
        "================================",
        "",
        f"Definitions extracted: {count}",
        f"Information diagnostics: {counts['INFO']}",
        f"Warnings: {counts['WARNING']}",
        f"Errors: {counts['ERROR']}",
        f"Fatal errors: {counts['FATAL']}",
        "",
        "Diagnostics",
        "-----------",
    ]
    if diagnostics:
        for item in diagnostics:
            location = item.source_path
            if item.line is not None:
                location += f":{item.line}"
            definition = f" [{item.definition_id}]" if item.definition_id else ""
            lines.append(
                f"{item.severity} {item.code}{definition} {location}: {item.message}"
            )
    else:
        lines.append("No diagnostics.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract direct-control definitions from authoritative documentation."
    )
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    return parser.parse_args(arguments)


def run(arguments: Sequence[str] | None = None) -> int:
    args = parse_arguments(arguments)
    root = args.repo_root.resolve()
    source_paths = tuple(resolve_from_repo(root, path) for path in SOURCE_PATHS)
    json_output = resolve_from_repo(root, args.json_output)
    report_output = resolve_from_repo(root, args.report_output)
    result: dict = {"definitions": []}
    diagnostics: list[Diagnostic] = []

    try:
        result, diagnostics = build_result(root, source_paths)
        write_json(result, json_output)
    except ExtractionFailure as error:
        diagnostics = [Diagnostic("FATAL", "EXTRACTION_FAILURE", str(error), "<input>")]
    except OSError as error:
        diagnostics = [Diagnostic("FATAL", "OUTPUT_WRITE_FAILURE", str(error), "<output>")]

    try:
        write_report(diagnostics, report_output, len(result.get("definitions", [])))
    except OSError as error:
        print(f"Unable to write extraction report: {error}")
        return 1

    failures = [item for item in diagnostics if item.severity in FAILURE_SEVERITIES]
    exit_code = 1 if failures else 0
    print("Direct-control extraction")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Definitions: {len(result.get('definitions', []))}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"JSON output: {json_output}")
    print(f"Report output: {report_output}")
    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            location = item.source_path
            if item.line is not None:
                location += f":{item.line}"
            print(f"{item.severity} {item.code}")
            print(f"  Source: {location}")
            print(f"  {item.message}")
    return exit_code


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
