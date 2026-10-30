"""Generate a reviewable execution-definition candidate."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

DEFAULT_EXTRACTED = Path("build/simulation_outputs/rom-generation/execution-definition-extractor/execution-definitions.json")
DEFAULT_MAINTAINED = Path("rom/microcode/v1/execution-definitions.json")
DEFAULT_CANDIDATE = Path("build/simulation_outputs/rom-generation/execution-definition-generator/execution-definitions.candidate.json")
DEFAULT_REPORT = Path("build/simulation_outputs/rom-generation/execution-definition-generator/generation-report.txt")
FAILURE_SEVERITIES = {"ERROR", "FATAL"}
SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "FATAL": 3}
REQUIRED_TOP_LEVEL = {"format_version", "control_design_version", "artifact", "extraction_stage", "opr_bit_positions", "cases", "diagnostics"}
REQUIRED_CASE_FIELDS = {"id", "source", "execution_model", "context", "timing_state", "micro_operations", "conditional_micro_operations"}

@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    case_id: str | None = None

class GenerationFailure(Exception): pass

def resolve(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()

def read_json(path: Path, *, optional: bool = False) -> dict[str, Any] | None:
    if optional and not path.exists(): return None
    try: text = path.read_text(encoding="utf-8")
    except FileNotFoundError as e: raise GenerationFailure(f"Required input does not exist: {path}") from e
    except UnicodeDecodeError as e: raise GenerationFailure(f"Input is not valid UTF-8: {path}") from e
    except OSError as e: raise GenerationFailure(f"Unable to read input {path}: {e}") from e
    if optional and not text.strip(): return None
    try: data = json.loads(text)
    except json.JSONDecodeError as e: raise GenerationFailure(f"Input is not valid JSON: {path}: line {e.lineno}, column {e.colno}: {e.msg}") from e
    if not isinstance(data, dict): raise GenerationFailure(f"Input root must be an object: {path}")
    return data

def case_index(data: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    cases = data.get("cases")
    if not isinstance(cases, list): raise GenerationFailure(f"{name} must contain a cases array.")
    result = {}
    for position, item in enumerate(cases):
        if not isinstance(item, dict): raise GenerationFailure(f"{name} case {position} must be an object.")
        missing = REQUIRED_CASE_FIELDS - set(item)
        if missing: raise GenerationFailure(f"{name} case {position} is missing: {', '.join(sorted(missing))}.")
        case_id = item["id"]
        if not isinstance(case_id, str) or not case_id: raise GenerationFailure(f"{name} case {position} has no nonempty string id.")
        if case_id in result: raise GenerationFailure(f"{name} contains duplicate case id {case_id}.")
        result[case_id] = item
    return result

def validate_extracted(data: dict[str, Any]) -> list[Diagnostic]:
    diagnostics = []
    missing = REQUIRED_TOP_LEVEL - set(data)
    if missing: diagnostics.append(Diagnostic("ERROR", "MISSING_TOP_LEVEL_FIELDS", "Extracted artifact is missing: " + ", ".join(sorted(missing))))
    if data.get("artifact") != "execution-definitions": diagnostics.append(Diagnostic("ERROR", "UNEXPECTED_ARTIFACT_TYPE", "Expected artifact 'execution-definitions'."))
    extractor_diagnostics = data.get("diagnostics")
    if not isinstance(extractor_diagnostics, list): diagnostics.append(Diagnostic("ERROR", "INVALID_EXTRACTOR_DIAGNOSTICS", "Extracted diagnostics must be an array."))
    elif any(isinstance(item, dict) and item.get("severity") in FAILURE_SEVERITIES for item in extractor_diagnostics): diagnostics.append(Diagnostic("ERROR", "EXTRACTOR_FAILURE_DIAGNOSTICS", "Extracted artifact contains ERROR or FATAL diagnostics."))
    return diagnostics

def build_candidate(extracted: dict[str, Any], maintained: dict[str, Any] | None) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    diagnostics = validate_extracted(extracted)
    if any(item.severity in FAILURE_SEVERITIES for item in diagnostics):
        return None, diagnostics
    try: extracted_cases = case_index(extracted, "Extracted artifact")
    except GenerationFailure as e:
        diagnostics.append(Diagnostic("ERROR", "INVALID_EXTRACTED_CASES", str(e))); return None, diagnostics
    maintained_cases = {}
    if maintained is not None:
        if maintained.get("control_design_version") != extracted.get("control_design_version"):
            diagnostics.append(Diagnostic("ERROR", "CONTROL_DESIGN_VERSION_MISMATCH", "Maintained and extracted artifacts have different control_design_version values."))
        try: maintained_cases = case_index(maintained, "Maintained artifact")
        except GenerationFailure as e:
            diagnostics.append(Diagnostic("ERROR", "INVALID_MAINTAINED_CASES", str(e))); return None, diagnostics
    if any(item.severity in FAILURE_SEVERITIES for item in diagnostics): return None, diagnostics
    for case_id in sorted(extracted_cases):
        old = maintained_cases.get(case_id)
        if old is None: diagnostics.append(Diagnostic("WARNING", "NEW_CASE", "Case is not present in the maintained artifact.", case_id))
        elif old != extracted_cases[case_id]: diagnostics.append(Diagnostic("WARNING", "CHANGED_CASE", "Extracted case differs from the maintained artifact.", case_id))
    for case_id in sorted(set(maintained_cases) - set(extracted_cases)):
        diagnostics.append(Diagnostic("WARNING", "STALE_CASE", "Maintained case is absent from the extracted artifact.", case_id))
    candidate = {
        "format_version": extracted["format_version"],
        "control_design_version": extracted["control_design_version"],
        "artifact": "execution-definitions",
        "generation_stage": "candidate-generation",
        "opr_bit_positions": extracted["opr_bit_positions"],
        "cases": [extracted_cases[item["id"]] for item in extracted["cases"]],
        "diagnostics": [],
    }
    return candidate, diagnostics

def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

def write_report(diagnostics: Sequence[Diagnostic], path: Path, count: int, written: bool) -> None:
    counts = {s: sum(item.severity == s for item in diagnostics) for s in ("INFO", "WARNING", "ERROR", "FATAL")}
    lines = ["Execution-Definition Candidate Generation Report", "==============================================", "", f"Cases processed: {count}", f"Candidate written: {'yes' if written else 'no'}", f"Information diagnostics: {counts['INFO']}", f"Warnings: {counts['WARNING']}", f"Errors: {counts['ERROR']}", f"Fatal errors: {counts['FATAL']}", "", "Diagnostics", "-----------"]
    if diagnostics:
        for item in diagnostics:
            case = f" [{item.case_id}]" if item.case_id else ""
            lines.append(f"{item.severity} {item.code}{case}: {item.message}")
    else: lines.append("No diagnostics.")
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate a reviewable execution-definition candidate.")
    p.add_argument("--repo-root", required=True, type=Path); p.add_argument("--extracted", type=Path, default=DEFAULT_EXTRACTED); p.add_argument("--maintained", type=Path, default=DEFAULT_MAINTAINED); p.add_argument("--candidate-output", type=Path, default=DEFAULT_CANDIDATE); p.add_argument("--report-output", type=Path, default=DEFAULT_REPORT); return p.parse_args(arguments)

def run(arguments: Sequence[str] | None = None) -> int:
    a=parse_arguments(arguments); root=a.repo_root.resolve(); candidate_path=resolve(root,a.candidate_output); report_path=resolve(root,a.report_output); diagnostics=[]; count=0; written=False
    try:
        extracted=read_json(resolve(root,a.extracted)); assert extracted is not None
        maintained=read_json(resolve(root,a.maintained),optional=True)
        if isinstance(extracted.get("cases"),list): count=len(extracted["cases"])
        candidate,diagnostics=build_candidate(extracted,maintained)
        if candidate is not None and not any(item.severity in FAILURE_SEVERITIES for item in diagnostics): write_json(candidate,candidate_path);written=True
    except GenerationFailure as e: diagnostics=[Diagnostic("FATAL","GENERATION_FAILURE",str(e))]
    except OSError as e: diagnostics=[Diagnostic("FATAL","OUTPUT_WRITE_FAILURE",str(e))]
    diagnostics=sorted(diagnostics,key=lambda item:(SEVERITY_ORDER.get(item.severity,99),item.code,item.case_id or "",item.message))
    try: write_report(diagnostics,report_path,count,written)
    except OSError as e: print(f"Unable to write generation report: {e}",file=sys.stderr);return 1
    failed=any(item.severity in FAILURE_SEVERITIES for item in diagnostics)
    print("Execution-definition candidate generation");print(f"Status: {'FAILED' if failed else 'SUCCEEDED'}");print(f"Cases: {count}");print(f"Candidate written: {'yes' if written else 'no'}");print(f"Diagnostics: {len(diagnostics)}");print(f"Candidate output: {candidate_path}");print(f"Report output: {report_path}")
    if failed:
        print();print("Failure diagnostics");print("-------------------")
        for item in diagnostics:
            if item.severity in FAILURE_SEVERITIES: print(f"{item.severity} {item.code}: {item.message}")
    return 1 if failed else 0

def main(): raise SystemExit(run())
if __name__=="__main__":main()
