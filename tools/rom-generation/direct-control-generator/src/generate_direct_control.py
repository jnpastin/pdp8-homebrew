"""Generate a reviewable direct-control candidate from extracted definitions."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from direct_control_validation import validate as validate_candidate

DEFAULT_EXTRACTED = Path(
    "build/simulation_outputs/rom-generation/"
    "direct-control-extractor/direct-control-definitions.json"
)
DEFAULT_MAINTAINED = Path("rom/microcode/v1/direct-control-definitions.json")
DEFAULT_CANDIDATE = Path(
    "build/simulation_outputs/rom-generation/"
    "direct-control-generator/direct-control-definitions.candidate.json"
)
DEFAULT_REPORT = Path(
    "build/simulation_outputs/rom-generation/"
    "direct-control-generator/generation-report.txt"
)
DEFAULT_INPUT_SCHEMA = Path("rom/microcode/v1/control-input-schema.json")
DEFAULT_WORD_SCHEMA = Path("rom/microcode/v1/control-word-schema.json")
DEFAULT_MAPPING = Path("rom/microcode/v1/micro-operation-mapping.json")
FAILURE_SEVERITIES = {"ERROR", "FATAL"}
SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "FATAL": 3}
REQUIRED_TOP_LEVEL = {
    "format_version",
    "control_design_version",
    "artifact",
    "extraction_stage",
    "sources",
    "definitions",
    "diagnostics",
}


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    definition_id: str | None = None


class GenerationFailure(Exception):
    """Raised when candidate generation cannot continue reliably."""


def resolve(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_json(path: Path, *, optional: bool = False) -> dict[str, Any] | None:
    if optional and not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise GenerationFailure(f"Required input does not exist: {path}") from error
    except UnicodeDecodeError as error:
        raise GenerationFailure(f"Input is not valid UTF-8: {path}") from error
    except OSError as error:
        raise GenerationFailure(f"Unable to read input {path}: {error}") from error
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


def definition_index(data: dict[str, Any], artifact_name: str) -> dict[str, dict[str, Any]]:
    definitions = data.get("definitions")
    if not isinstance(definitions, list):
        raise GenerationFailure(f"{artifact_name} must contain a definitions array.")
    result: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(definitions):
        if not isinstance(item, dict):
            raise GenerationFailure(
                f"{artifact_name} definition {position} must be an object."
            )
        definition_id = item.get("id")
        if not isinstance(definition_id, str) or not definition_id:
            raise GenerationFailure(
                f"{artifact_name} definition {position} has no nonempty string id."
            )
        if definition_id in result:
            raise GenerationFailure(
                f"{artifact_name} contains duplicate definition id {definition_id}."
            )
        result[definition_id] = item
    return result


def validate_extracted(data: dict[str, Any]) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        diagnostics.append(
            Diagnostic(
                "ERROR",
                "MISSING_TOP_LEVEL_FIELDS",
                "Extracted artifact is missing: " + ", ".join(missing),
            )
        )
    if data.get("artifact") != "direct-control-definitions":
        diagnostics.append(
            Diagnostic(
                "ERROR",
                "UNEXPECTED_ARTIFACT_TYPE",
                "Expected artifact 'direct-control-definitions'.",
            )
        )
    extracted_diagnostics = data.get("diagnostics")
    if not isinstance(extracted_diagnostics, list):
        diagnostics.append(
            Diagnostic(
                "ERROR",
                "INVALID_EXTRACTOR_DIAGNOSTICS",
                "Extracted artifact diagnostics must be an array.",
            )
        )
    elif any(
        isinstance(item, dict) and item.get("severity") in FAILURE_SEVERITIES
        for item in extracted_diagnostics
    ):
        diagnostics.append(
            Diagnostic(
                "ERROR",
                "EXTRACTOR_FAILURE_DIAGNOSTICS",
                "Extracted artifact contains ERROR or FATAL diagnostics.",
            )
        )
    return diagnostics


def comparable_definition(item: dict[str, Any]) -> dict[str, Any]:
    """Return the review-relevant definition content."""
    return item


def build_candidate(
    extracted: dict[str, Any],
    maintained: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    diagnostics = validate_extracted(extracted)
    try:
        extracted_by_id = definition_index(extracted, "Extracted artifact")
    except GenerationFailure as error:
        diagnostics.append(Diagnostic("ERROR", "INVALID_EXTRACTED_DEFINITIONS", str(error)))
        return None, diagnostics

    maintained_by_id: dict[str, dict[str, Any]] = {}
    if maintained is not None:
        if maintained.get("control_design_version") != extracted.get(
            "control_design_version"
        ):
            diagnostics.append(
                Diagnostic(
                    "ERROR",
                    "CONTROL_DESIGN_VERSION_MISMATCH",
                    "Maintained and extracted artifacts have different "
                    "control_design_version values.",
                )
            )
        try:
            maintained_by_id = definition_index(
                maintained, "Maintained artifact"
            )
        except GenerationFailure as error:
            diagnostics.append(
                Diagnostic("ERROR", "INVALID_MAINTAINED_DEFINITIONS", str(error))
            )
            return None, diagnostics

    if any(item.severity in FAILURE_SEVERITIES for item in diagnostics):
        return None, diagnostics

    for definition_id in sorted(extracted_by_id):
        maintained_item = maintained_by_id.get(definition_id)
        if maintained_item is None:
            diagnostics.append(
                Diagnostic(
                    "WARNING",
                    "NEW_DEFINITION",
                    "Definition is not present in the maintained artifact.",
                    definition_id,
                )
            )
        elif comparable_definition(maintained_item) != comparable_definition(
            extracted_by_id[definition_id]
        ):
            diagnostics.append(
                Diagnostic(
                    "WARNING",
                    "CHANGED_DEFINITION",
                    "Extracted definition differs from the maintained artifact.",
                    definition_id,
                )
            )

    for definition_id in sorted(set(maintained_by_id) - set(extracted_by_id)):
        diagnostics.append(
            Diagnostic(
                "WARNING",
                "STALE_DEFINITION",
                "Maintained definition is absent from the extracted artifact.",
                definition_id,
            )
        )

    candidate = {
        "format_version": extracted["format_version"],
        "control_design_version": extracted["control_design_version"],
        "artifact": "direct-control-definitions",
        "generation_stage": "candidate-generation",
        "sources": extracted["sources"],
        "definitions": [
            extracted_by_id[definition_id]
            for definition_id in sorted(
                extracted_by_id,
                key=lambda value: (
                    extracted_by_id[value]["source"]["path"],
                    extracted_by_id[value]["source"]["line"],
                ),
            )
        ],
        "diagnostics": [],
    }
    return candidate, diagnostics


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_report(
    diagnostics: Sequence[Diagnostic],
    path: Path,
    definition_count: int,
    candidate_written: bool,
) -> None:
    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in ("INFO", "WARNING", "ERROR", "FATAL")
    }
    lines = [
        "Direct-Control Candidate Generation Report",
        "==========================================",
        "",
        f"Definitions processed: {definition_count}",
        f"Candidate written: {'yes' if candidate_written else 'no'}",
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
            definition = f" [{item.definition_id}]" if item.definition_id else ""
            lines.append(
                f"{item.severity} {item.code}{definition}: {item.message}"
            )
    else:
        lines.append("No diagnostics.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a reviewable direct-control candidate."
    )
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED)
    parser.add_argument("--maintained", type=Path, default=DEFAULT_MAINTAINED)
    parser.add_argument("--candidate-output", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--control-input-schema", type=Path, default=DEFAULT_INPUT_SCHEMA)
    parser.add_argument("--control-word-schema", type=Path, default=DEFAULT_WORD_SCHEMA)
    parser.add_argument("--micro-operation-mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(arguments)


def run(arguments: Sequence[str] | None = None) -> int:
    args = parse_arguments(arguments)
    root = args.repo_root.resolve()
    candidate_output = resolve(root, args.candidate_output)
    report_output = resolve(root, args.report_output)
    diagnostics: list[Diagnostic] = []
    definition_count = 0
    candidate_written = False

    try:
        extracted = read_json(resolve(root, args.extracted))
        assert extracted is not None
        maintained = read_json(resolve(root, args.maintained), optional=True)
        definitions = extracted.get("definitions")
        if isinstance(definitions, list):
            definition_count = len(definitions)
        candidate, diagnostics = build_candidate(extracted, maintained)
        if candidate is not None and not any(
            item.severity in FAILURE_SEVERITIES for item in diagnostics
        ):
            input_schema = read_json(resolve(root, args.control_input_schema))
            word_schema = read_json(resolve(root, args.control_word_schema))
            mapping = read_json(resolve(root, args.micro_operation_mapping))
            assert input_schema is not None
            assert word_schema is not None
            assert mapping is not None
            validation_diagnostics = validate_candidate(
                candidate, input_schema, word_schema, mapping
            )
            diagnostics.extend(
                Diagnostic(
                    item.severity,
                    item.code,
                    item.message,
                    item.definition_id,
                )
                for item in validation_diagnostics
            )
            if not any(
                item.severity in FAILURE_SEVERITIES for item in diagnostics
            ):
                write_json(candidate, candidate_output)
                candidate_written = True
    except GenerationFailure as error:
        diagnostics = [Diagnostic("FATAL", "GENERATION_FAILURE", str(error))]
    except OSError as error:
        diagnostics = [Diagnostic("FATAL", "OUTPUT_WRITE_FAILURE", str(error))]

    diagnostics = sorted(
        diagnostics,
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 99),
            item.code,
            item.definition_id or "",
            item.message,
        ),
    )
    try:
        write_report(
            diagnostics,
            report_output,
            definition_count,
            candidate_written,
        )
    except OSError as error:
        print(f"Unable to write generation report: {error}", file=sys.stderr)
        return 1

    failures = [
        item for item in diagnostics if item.severity in FAILURE_SEVERITIES
    ]
    exit_code = 1 if failures else 0
    print("Direct-control candidate generation")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Definitions: {definition_count}")
    print(f"Candidate written: {'yes' if candidate_written else 'no'}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"Candidate output: {candidate_output}")
    print(f"Report output: {report_output}")
    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            definition = f" [{item.definition_id}]" if item.definition_id else ""
            print(f"{item.severity} {item.code}{definition}")
            print(f"  {item.message}")
    return exit_code


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
