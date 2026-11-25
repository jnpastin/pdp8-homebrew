#!/usr/bin/env python3
"""Run the ROM-generation tools in order, with interactive promotion.

Each stage runs one tool. After every stage the runner prints the diagnostics
from the tool's report. A generator stage writes a candidate artifact; when
the candidate differs from the maintained artifact in ``rom/microcode/<design>``,
the runner asks the user to accept the promotion before copying it there.
Later stages read the maintained artifacts, so a declined promotion stops the
pipeline.

``--design`` selects the control design (tools/rom-generation/common/design.py); the
runner passes it to every tool. A frozen design is not regenerated from ``docs/``: only the
control-store packer runs, on the design's maintained artifacts.

Exit status: 0 when every stage succeeded and every needed promotion was
accepted, 1 when a tool failed, 2 when a promotion was declined.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from design import DESIGN, ENVIRONMENT_VARIABLE, Design, select  # noqa: E402  (common/design.py)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import review  # noqa: E402  (review.py: reviewed decisions the evidence disagrees with)
from artifact_changes import (  # noqa: E402  (common/artifact_changes.py)
    MOVED, RENAMED, compare_artifacts, describe, only_moved, strip_locations)

TOOLS = Path("tools/rom-generation")

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


def stages_for(design: Design) -> tuple[Stage, ...]:
    """Every tool stage, in run order, with `design`'s build and maintained paths."""
    build, maintained = Path(design.build), Path(design.maintained)

    def _stage(name: str, script: str, report: str, artifact: str | None = None) -> Stage:
        return Stage(
            name, TOOLS / name / "src" / script, build / name / report,
            build / name / f"{artifact}.candidate.json" if artifact else None,
            maintained / f"{artifact}.json" if artifact else None,
        )

    return _all_stages(_stage)


def runnable(design: Design, stages: tuple[Stage, ...]) -> tuple[Stage, ...]:
    """The stages a run of `design` executes: a frozen design is only packed."""
    return tuple(s for s in stages if s.name == "control-store-packer") if design.frozen else stages


# Run order: each generator reads the artifacts promoted before it.
def _all_stages(_stage) -> tuple[Stage, ...]:
    return (
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
        _stage("timing-rom-generator", "generate_timing_rom.py", "generation-report.txt"),
    )


STAGES: tuple[Stage, ...] = stages_for(DESIGN)


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


def condensed(section: Sequence[str]) -> list[str]:
    """The diagnostics section with every warning, error, and fatal error in full, and the
    INFO diagnostics only counted, by code. A diagnostic's continuation lines (those not
    starting with a severity) stay with it."""
    kept: list[str] = []
    info: Counter = Counter()
    current_info = False
    for line in section:
        match = re.match(rf"({'|'.join(SEVERITIES)})\s+([A-Z][A-Z0-9_]*)", line)
        if match:
            current_info = match.group(1) == "INFO"
            if current_info:
                info[match.group(2)] += 1
                continue
        if not current_info:
            kept.append(line)
    while kept and not kept[-1].strip():
        kept.pop()
    return kept + [f"INFO {code} x{n}" for code, n in info.items()]


def format_counts(counts: Counter) -> str:
    parts = [f"{counts[s]} {s.lower()}" for s in SEVERITIES if counts[s]]
    return ", ".join(parts) if parts else "no diagnostics"


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n")


def _parsed(text: str | None):
    """The artifact as JSON, or None when it is absent or not JSON."""
    if text is None:
        return None
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _unified(old: str, new: str, stage: "Stage") -> list[str]:
    return list(difflib.unified_diff(
        old.splitlines(), new.splitlines(), fromfile=stage.maintained.as_posix(),
        tofile=stage.candidate.as_posix(), lineterm=""))


def _without_locations(value) -> str:
    return json.dumps(strip_locations(value), indent=2, ensure_ascii=False) + "\n"


LISTED_CHANGES = 12


# ---------------------------------------------------------------------------
# Running
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    stage: str
    status: str
    counts: Counter
    decisions: int = 0                                  # the review only
    skipped: frozenset = frozenset()                    # the review only: (artifact, name)


Runner = Callable[[Sequence[str], Path], "subprocess.CompletedProcess[str]"]


def run_tool(command: Sequence[str], cwd: Path) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def run_pipeline(
    root: Path,
    stages: Sequence[Stage] = STAGES,
    *,
    dry_run: bool = False,
    accept_moved: bool = False,
    verbose: bool = False,
    review_decisions: bool = True,
    skip: frozenset = frozenset(),
    ask: Callable[[str], str] = input,
    out: Callable[[str], None] = print,
    runner: Runner = run_tool,
) -> tuple[int, list[Outcome]]:
    outcomes: list[Outcome] = []
    total = len(stages)
    for number, stage in enumerate(stages, 1):
        result = runner([sys.executable, str(root / stage.script), "--repo-root", str(root)], root)
        report_path = root / stage.report
        report = report_path.read_text(encoding="utf-8") if report_path.exists() else ""
        section = diagnostics_section(report)
        counts = severity_counts(section)
        if verbose:
            out("")
            out(f"[{number}/{total}] {stage.name}")
            out(f"  Diagnostics: {format_counts(counts)}")
            for line in section:
                out(f"    {line}" if line else "")
        else:
            out(f"[{number}/{total}] {stage.name}: {format_counts(counts)}")
            for line in condensed(section):
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
            if verbose:
                out(f"  Candidate matches {stage.maintained.as_posix()}; nothing to promote.")
            outcomes.append(Outcome(stage.name, "unchanged", counts))
            continue

        diff = _unified(maintained or "", candidate, stage)
        added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
        removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
        old_json, new_json = _parsed(maintained), _parsed(candidate)
        changes = (compare_artifacts(old_json, new_json)
                   if new_json is not None and (maintained is None or old_json is not None)
                   else None)
        lines_text = f"{added} line(s) added, {removed} removed"
        if maintained is None:
            what = "new artifact"
        elif changes is None:
            what = lines_text
        else:
            what = f"{describe(changes)}; {lines_text}"
        out(f"  Candidate differs from {stage.maintained.as_posix()}: {what}.")
        moved_only = changes is not None and maintained is not None and (
            only_moved(changes) or not changes)
        if moved_only:
            out("  Only source line numbers or formatting changed; the content is the same.")
        elif changes:
            listed = [c for c in changes if c.kind != MOVED]
            for c in listed[:LISTED_CHANGES]:
                note = f" (was {c.previous})" if c.kind == RENAMED else ""
                out(f"    {c.kind:<8}  {c.identifier}{note}")
            if len(listed) > LISTED_CHANGES:
                out(f"    ... and {len(listed) - LISTED_CHANGES} more")
        material_diff = (_unified(_without_locations(old_json), _without_locations(new_json), stage)
                         if changes is not None and old_json is not None else diff)

        if dry_run:
            note = " (source lines only)" if moved_only else ""
            out(f"  Dry run: not promoted{note}. Later stages read the current maintained "
                "artifact.")
            outcomes.append(Outcome(stage.name, "pending", counts))
            continue

        if moved_only and accept_moved:
            maintained_path.write_text(candidate, encoding="utf-8", newline="\n")
            out("  Promoted: source line numbers only (--accept-moved).")
            outcomes.append(Outcome(stage.name, "promoted", counts))
            continue

        while True:
            try:
                answer = ask(f"  Promote {stage.candidate.name} to "
                             f"{stage.maintained.as_posix()}? [y]es / [n]o / [d]iff / "
                             "[a]ll lines / [l]ist moved: ")
            except EOFError:
                answer = "n"
            answer = answer.strip().lower()
            if answer in ("d", "diff"):
                for line in material_diff or ["  (no difference other than source line numbers)"]:
                    out(line)
                continue
            if answer in ("a", "all"):
                for line in diff:
                    out(line)
                continue
            if answer in ("l", "list"):
                moved = [c.identifier for c in changes or () if c.kind == MOVED]
                for identifier in moved or ["(none)"]:
                    out(f"    moved     {identifier}")
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
            out("  Answer y, n, d, a, or l.")
    if review_decisions:
        reviewed = run_review(root, stages, dry_run=dry_run, skip=skip, ask=ask, out=out)
        if reviewed is not None:
            outcomes.append(reviewed)
    return EXIT_OK, outcomes


REVIEW = "review"


def review_paths(stages: Sequence[Stage]) -> tuple[Path, Path, Path, Path] | None:
    """The maintained schemas and the analysis the review reads, when this run made them."""
    by_name = {s.name: s for s in stages}
    names = ("control-input-schema-generator", "control-word-schema-generator",
             "control-word-equivalence-analyzer")
    if not all(n in by_name for n in names):
        return None
    inputs, words, analyzer = (by_name[n] for n in names)
    return (inputs.maintained, words.maintained,
            analyzer.report.parent / "control-word-equivalence.json", inputs.candidate)


def run_review(root: Path, stages: Sequence[Stage], *, dry_run: bool, skip: frozenset,
               ask: Callable[[str], str], out: Callable[[str], None]) -> Outcome | None:
    """Ask about each reviewed decision the evidence disagrees with (review.py), and record the
    answers in the maintained artifacts. None when there is nothing to review."""
    paths = review_paths(stages)
    if paths is None:
        return None
    items = review.collect(root, *paths[:3], skip=set(skip), input_candidate=paths[3])
    if not items:
        return None
    out("")
    out(f"Review: {len(items)} reviewed decision(s) disagree with the evidence.")
    if dry_run:
        for item in items:
            for line in review.describe(item):
                out(line)
        out("  Dry run: nothing recorded.")
        return Outcome(REVIEW, "pending", Counter(), decisions=len(items))
    answers, skipped, accept_rest = [], set(), False
    for number, item in enumerate(items, 1):
        out("")
        out(f"[{number}/{len(items)}]")
        for line in review.describe(item):
            out(line)
        while True:
            if accept_rest and item.proposed is not None:
                answers.append((item, item.proposed))
                out(f"  Recorded {item.proposed} (all).")
                break
            choices = "[y]es / [a]ll remaining / [s]kip / or type " + (
                "a role" if item.key == review.ROLE else "predicate,value or none")
            try:
                answer = ask(f"  Record the proposal? {choices}: ").strip()
            except EOFError:
                answer = "s"
                accept_rest = False
            lowered = answer.lower()
            if lowered in ("y", "yes", "a", "all"):
                if item.proposed is None:
                    out("  There is no proposal: type a classification, or s to skip.")
                    continue
                accept_rest = lowered in ("a", "all")
                answers.append((item, item.proposed))
                break
            if lowered in ("s", "skip", ""):
                skipped.add((item.artifact, item.name))
                break
            try:
                answers.append((item, review.parse_answer(item, answer)))
                break
            except ValueError as exc:
                out(f"  {exc}.")
    if answers:
        review.record(root, {review.INPUT_SCHEMA: paths[0], review.WORD_SCHEMA: paths[1]}, answers)
        out(f"  Recorded {len(answers)} decision(s) in the maintained schemas.")
    status = "recorded" if answers else "skipped"
    return Outcome(REVIEW, status, Counter(), decisions=len(answers) if answers else len(skipped),
                   skipped=frozenset(skipped))


def summary(outcomes: Sequence[Outcome], total: int) -> list[str]:
    width = max((len(o.stage) for o in outcomes), default=0)
    lines = ["", "Summary", "-------"]
    stage_outcomes = [o for o in outcomes if o.stage != REVIEW]
    reviews = [o for o in outcomes if o.stage == REVIEW]
    for o in outcomes:
        detail = (f"{o.decisions} decision(s)" if o.stage == REVIEW else format_counts(o.counts))
        lines.append(f"{o.stage:<{width}}  {o.status:<9}  {detail}")
    if len(stage_outcomes) < total:
        lines.append(f"{total - len(stage_outcomes)} later stage(s) not run.")
    warnings = sum(o.counts["WARNING"] + o.counts["ERROR"] + o.counts["FATAL"]
                   for o in stage_outcomes)
    pending = sum(1 for o in stage_outcomes if o.status == "pending")
    to_review = sum(o.decisions for o in reviews if o.status in ("pending", "skipped"))
    if len(stage_outcomes) == total and not warnings and not pending and not to_review and all(
            o.status in ("ok", "unchanged", "promoted") for o in stage_outcomes):
        lines += ["", "Clean: no warnings, nothing pending."]
    else:
        review_text = f", {to_review} decision(s) to review" if to_review else ""
        lines += ["", f"Not clean: {warnings} warning(s) or error(s), {pending} promotion(s) "
                      f"pending{review_text}."]
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
    parser.add_argument("--accept-moved", action="store_true",
                        help="promote, without asking, a candidate whose only change is in "
                             "source line numbers")
    parser.add_argument("--verbose", action="store_true",
                        help="list every INFO diagnostic and every unchanged candidate")
    parser.add_argument("--list", action="store_true", help="list the stages and exit")
    parser.add_argument("--design", help=f"control design to build (default: ${ENVIRONMENT_VARIABLE} "
                                         f"or {DESIGN.name})")
    return parser.parse_args(arguments)


def select_stages(start: str | None, stop: str | None,
                  stages: tuple[Stage, ...] = STAGES) -> tuple[Stage, ...]:
    names = [s.name for s in stages]
    for name in (start, stop):
        if name is not None and name not in names:
            raise SystemExit(f"Unknown stage {name!r}. Stages: {', '.join(names)}")
    first = names.index(start) if start else 0
    last = names.index(stop) if stop else len(names) - 1
    if first > last:
        raise SystemExit(f"--from {start} comes after --to {stop}.")
    return stages[first:last + 1]


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
    design = select(options.design)
    os.environ[ENVIRONMENT_VARIABLE] = design.name     # every tool the runner starts builds it
    all_stages = runnable(design, stages_for(design))
    print(f"Control design: {design.name}" + (" (frozen: packer only)" if design.frozen else ""))
    if options.list:
        for number, stage in enumerate(all_stages, 1):
            promotes = f"  -> {stage.maintained.as_posix()}" if stage.maintained else ""
            print(f"{number:2}. {stage.name}{promotes}")
        return EXIT_OK
    stages = select_stages(options.start, options.stop, all_stages)
    root = options.repo_root.resolve()
    code, outcomes = run_pipeline(root, stages, dry_run=options.dry_run,
                                  accept_moved=options.accept_moved, verbose=options.verbose)
    last = outcomes[-1] if outcomes else None
    if code == EXIT_OK and last is not None and last.stage == REVIEW and last.status == "recorded":
        print(f"\nRecorded {last.decisions} decision(s); running again to confirm.")
        code, outcomes = run_pipeline(root, stages, accept_moved=options.accept_moved,
                                      verbose=options.verbose, skip=last.skipped)
    for line in summary(outcomes, len(stages)):
        print(line)
    status = {EXIT_OK: "SUCCEEDED", EXIT_TOOL_FAILED: "FAILED", EXIT_DECLINED: "STOPPED"}[code]
    print(f"\nPipeline: {status}")
    return code


if __name__ == "__main__":
    sys.exit(main())
