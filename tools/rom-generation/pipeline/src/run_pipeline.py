#!/usr/bin/env python3
"""Run the ROM-generation tools in order, with interactive promotion.

Each stage runs one tool. After every stage the runner prints the diagnostics
from the tool's report. A generator stage writes a candidate artifact; when
the candidate differs from the maintained artifact in ``rom/microcode/v1``,
the runner asks the user to accept the promotion before copying it there.
Later stages read the maintained artifacts, so a declined promotion stops the
pipeline.

Exit status: 0 when every stage succeeded and every needed promotion was
accepted, 1 when a tool failed, 2 when a promotion was declined.
"""

from __future__ import annotations

import argparse
import difflib
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

TOOLS = Path("tools/rom-generation")
BUILD = Path("build/simulation_outputs/rom-generation")
MAINTAINED = Path("rom/microcode/v1")

SEVERITIES = ("FATAL", "ERROR", "WARNING", "INFO")
DIAGNOSTIC_HEADINGS = ("Diagnostics", "Diagnostic Details")
NO_DIAGNOSTICS = {"", "none", "none.", "no diagnostics."}

EXIT_OK, EXIT_TOOL_FAILED, EXIT_DECLINED = 0, 1, 2


@dataclass(frozen=True)
class Stage:
    name: str
    script: Path                       # relative to the repository root
    report: Path                       # relative to the repository root
    candidate: Path | None = None      # generator stages only
    maintained: Path | None = None


def _stage(name: str, script: str, report: str, artifact: str | None = None) -> Stage:
    return Stage(
        name, TOOLS / name / "src" / script, BUILD / name / report,
        BUILD / name / f"{artifact}.candidate.json" if artifact else None,
        MAINTAINED / f"{artifact}.json" if artifact else None,
    )


# Run order: each generator reads the artifacts promoted before it.
STAGES: tuple[Stage, ...] = (
    _stage("control-input-extractor", "extract_control_inputs.py", "extraction-report.txt"),
    _stage("control-input-schema-generator", "generate_control_input_schema.py",
           "generation-report.txt", "control-input-schema"),
    _stage("control-output-extractor", "extract_control_outputs.py", "extraction-report.txt"),
    _stage("control-word-schema-generator", "generate_control_word_schema.py",
           "generation-report.txt", "control-word-schema"),
    _stage("micro-operation-extractor", "extract_micro_operations.py", "extraction-report.txt"),
    _stage("micro-operation-mapping-generator", "generate_micro_operation_mapping.py",
           "generation-report.txt", "micro-operation-mapping"),
    _stage("direct-control-extractor", "extract_direct_control.py", "extraction-report.txt"),
    _stage("direct-control-generator", "generate_direct_control.py",
           "generation-report.txt", "direct-control-definitions"),
    _stage("execution-definition-extractor", "extract_execution_definitions.py",
           "extraction-report.txt"),
    _stage("execution-definition-generator", "generate_execution_definitions.py",
           "generation-report.txt", "execution-definitions"),
    _stage("timing-constraint-extractor", "extract_timing_constraints.py", "extraction-report.txt"),
    _stage("timing-constraint-generator", "generate_timing_constraints.py",
           "generation-report.txt", "timing-constraints"),
    _stage("symbolic-control-word-generator", "generate_symbolic_control_words.py",
           "generation-report.txt", "symbolic-control-words"),
    _stage("control-word-equivalence-analyzer", "analyze_control_word_equivalence.py",
           "analysis-report.txt"),
    _stage("control-store-packer", "pack_control_store.py", "packing-report.txt"),
)


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


def _is_underline(line: str) -> bool:
    return len(set(line)) == 1 and line[0] in "-="


def diagnostics_section(report: str) -> list[str]:
    """Return the lines of the report's diagnostics section, without blank
    edges; an empty list when the section is absent or says there are none."""

    lines = report.splitlines()
    for i in range(len(lines) - 1):
        if lines[i].strip() in DIAGNOSTIC_HEADINGS and _is_underline(lines[i + 1].strip()):
            body: list[str] = []
            for j in range(i + 2, len(lines)):
                if j + 1 < len(lines) and lines[j].strip() and _is_underline(lines[j + 1].strip()):
                    break
                body.append(lines[j].rstrip())
            while body and not body[0].strip():
                body.pop(0)
            while body and not body[-1].strip():
                body.pop()
            if len(body) == 1 and body[0].strip().lower() in NO_DIAGNOSTICS:
                return []
            return body
    return []


def severity_counts(section: Sequence[str]) -> Counter:
    counts: Counter = Counter()
    for line in section:
        match = re.match(rf"({'|'.join(SEVERITIES)})\b", line)
        if match:
            counts[match.group(1)] += 1
    return counts


def format_counts(counts: Counter) -> str:
    parts = [f"{counts[s]} {s.lower()}" for s in SEVERITIES if counts[s]]
    return ", ".join(parts) if parts else "no diagnostics"


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n")


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    stage: str
    status: str
    counts: Counter


Runner = Callable[[Sequence[str], Path], "subprocess.CompletedProcess[str]"]


def run_tool(command: Sequence[str], cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def run_pipeline(
    root: Path,
    stages: Sequence[Stage] = STAGES,
    *,
    dry_run: bool = False,
    ask: Callable[[str], str] = input,
    out: Callable[[str], None] = print,
    runner: Runner = run_tool,
) -> tuple[int, list[Outcome]]:
    outcomes: list[Outcome] = []
    total = len(stages)
    for number, stage in enumerate(stages, 1):
        out("")
        out(f"[{number}/{total}] {stage.name}")
        result = runner([sys.executable, str(root / stage.script), "--repo-root", str(root)], root)
        report_path = root / stage.report
        report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        section = diagnostics_section(report)
        counts = severity_counts(section)
        out(f"  Diagnostics: {format_counts(counts)}")
        for line in section:
            out(f"    {line}" if line else "")

        if result.returncode != 0:
            out(f"  FAILED: the tool exited with status {result.returncode}.")
            if not report:
                tail = (result.stdout + result.stderr).strip().splitlines()[-15:]
                for line in tail:
                    out(f"    {line}")
            out(f"  Report: {stage.report.as_posix()}")
            outcomes.append(Outcome(stage.name, "failed", counts))
            return EXIT_TOOL_FAILED, outcomes

        if stage.candidate is None:
            outcomes.append(Outcome(stage.name, "ok", counts))
            continue

        candidate_path, maintained_path = root / stage.candidate, root / stage.maintained
        if not candidate_path.exists():
            out(f"  FAILED: no candidate was written to {stage.candidate.as_posix()}.")
            outcomes.append(Outcome(stage.name, "failed", counts))
            return EXIT_TOOL_FAILED, outcomes
        candidate = _normalized(candidate_path.read_text(encoding="utf-8"))
        maintained = (_normalized(maintained_path.read_text(encoding="utf-8"))
                      if maintained_path.exists() else None)
        if candidate == maintained:
            out(f"  Candidate matches {stage.maintained.as_posix()}; nothing to promote.")
            outcomes.append(Outcome(stage.name, "unchanged", counts))
            continue

        diff = list(difflib.unified_diff(
            (maintained or "").splitlines(), candidate.splitlines(),
            fromfile=stage.maintained.as_posix(), tofile=stage.candidate.as_posix(),
            lineterm=""))
        added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
        removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
        what = ("new artifact" if maintained is None
                else f"{added} line(s) added, {removed} removed")
        out(f"  Candidate differs from {stage.maintained.as_posix()}: {what}.")

        if dry_run:
            out("  Dry run: not promoted. Later stages read the current maintained artifact.")
            outcomes.append(Outcome(stage.name, "pending", counts))
            continue

        while True:
            try:
                answer = ask(f"  Promote {stage.candidate.name} to "
                             f"{stage.maintained.as_posix()}? [y]es / [n]o / [d]iff: ")
            except EOFError:
                answer = "n"
            answer = answer.strip().lower()
            if answer in ("d", "diff"):
                for line in diff:
                    out(line)
                continue
            if answer in ("y", "yes"):
                maintained_path.parent.mkdir(parents=True, exist_ok=True)
                maintained_path.write_text(candidate, encoding="utf-8", newline="\n")
                out("  Promoted.")
                outcomes.append(Outcome(stage.name, "promoted", counts))
                break
            if answer in ("n", "no"):
                out("  Not promoted. Later stages read the maintained artifacts, "
                    "so the pipeline stops here.")
                outcomes.append(Outcome(stage.name, "declined", counts))
                return EXIT_DECLINED, outcomes
            out("  Answer y, n, or d.")
    return EXIT_OK, outcomes


def summary(outcomes: Sequence[Outcome], total: int) -> list[str]:
    width = max((len(o.stage) for o in outcomes), default=0)
    lines = ["", "Summary", "-------"]
    for o in outcomes:
        lines.append(f"{o.stage:<{width}}  {o.status:<9}  {format_counts(o.counts)}")
    if len(outcomes) < total:
        lines.append(f"{total - len(outcomes)} later stage(s) not run.")
    return lines


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--repo-root", type=Path, default=Path("."),
                        help="repository root (default: current directory)")
    parser.add_argument("--from", dest="start", metavar="STAGE",
                        help="start at this stage instead of the first")
    parser.add_argument("--to", dest="stop", metavar="STAGE",
                        help="stop after this stage instead of the last")
    parser.add_argument("--dry-run", action="store_true",
                        help="run every stage and report pending promotions without promoting")
    parser.add_argument("--list", action="store_true", help="list the stages and exit")
    return parser.parse_args(arguments)


def select_stages(start: str | None, stop: str | None) -> tuple[Stage, ...]:
    names = [s.name for s in STAGES]
    for name in (start, stop):
        if name is not None and name not in names:
            raise SystemExit(f"Unknown stage {name!r}. Stages: {', '.join(names)}")
    first = names.index(start) if start else 0
    last = names.index(stop) if stop else len(names) - 1
    if first > last:
        raise SystemExit(f"--from {start} comes after --to {stop}.")
    return STAGES[first:last + 1]


def tolerate_unencodable_output() -> None:
    """Replace, rather than fail on, characters the console encoding cannot represent.

    Tool reports are UTF-8 and may contain characters such as the micro sign; a cp1252 console
    or pipe would otherwise raise UnicodeEncodeError partway through the run."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def main(arguments: Sequence[str] | None = None) -> int:
    tolerate_unencodable_output()
    options = parse_arguments(arguments)
    if options.list:
        for number, stage in enumerate(STAGES, 1):
            promotes = f"  -> {stage.maintained.as_posix()}" if stage.maintained else ""
            print(f"{number:2}. {stage.name}{promotes}")
        return EXIT_OK
    stages = select_stages(options.start, options.stop)
    root = options.repo_root.resolve()
    code, outcomes = run_pipeline(root, stages, dry_run=options.dry_run)
    for line in summary(outcomes, len(stages)):
        print(line)
    status = {EXIT_OK: "SUCCEEDED", EXIT_TOOL_FAILED: "FAILED", EXIT_DECLINED: "STOPPED"}[code]
    print(f"\nPipeline: {status}")
    return code


if __name__ == "__main__":
    sys.exit(main())
