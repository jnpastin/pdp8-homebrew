"""Tests for the ROM-generation pipeline runner.

The tests use small fake tools in a temporary repository; they do not run
the real ROM-generation tools.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import run_pipeline as P  # noqa: E402

REPO = Path(__file__).resolve().parents[4]

GENERATION_REPORT = """\
Example Generation Report
=========================

Candidate written: yes
Warnings: 1

Diagnostics
-----------
WARNING CHANGED_CASE [a]: Generated case differs from the maintained artifact.
"""

MULTILINE_REPORT = """\
Extraction Report
=================

Diagnostics: 2

Inputs by Domain
----------------
External: 3

Diagnostic Details
------------------
ERROR MISSING_DEFINITION [X]
  Source: docs/a.md:12
  X has no definition.

INFO NOTE [Y]
  Source: docs/a.md:20
  Y is fine.
"""


def fake_tool(report: str, candidate: str | None = None, exit_code: int = 0) -> str:
    """Source of a fake tool that writes ``report`` and ``candidate``."""
    return (
        "import sys\nfrom pathlib import Path\n"
        "root = Path(sys.argv[sys.argv.index('--repo-root') + 1])\n"
        "here = Path(__file__).resolve().parent\n"
        f"(here / 'report.txt').write_text({report!r}, encoding='utf-8')\n"
        + (f"(here / 'out.candidate.json').write_text({candidate!r}, encoding='utf-8')\n"
           if candidate is not None else "")
        + f"sys.exit({exit_code})\n"
    )


class Repo:
    """A temporary repository with fake tools."""

    def __init__(self) -> None:
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)

    def close(self) -> None:
        self._dir.cleanup()

    def stage(self, name: str, report: str, candidate: str | None = None,
              maintained: str | None = None, exit_code: int = 0) -> P.Stage:
        directory = self.root / name
        directory.mkdir(parents=True)
        (directory / "tool.py").write_text(fake_tool(report, candidate, exit_code),
                                           encoding="utf-8")
        target = None
        if candidate is not None:
            target = Path("maintained") / f"{name}.json"
            if maintained is not None:
                (self.root / target).parent.mkdir(exist_ok=True)
                (self.root / target).write_bytes(maintained.encode("utf-8"))
        return P.Stage(name, Path(name) / "tool.py", Path(name) / "report.txt",
                       Path(name) / "out.candidate.json" if candidate is not None else None,
                       target)


def case(identifier: str, uop: str, line: int) -> dict:
    return {"id": identifier, "source": {"path": "docs/a.md", "line": line},
            "micro_operations": [uop]}


def run(repo: Repo, stages, answers=(), dry_run=False, accept_moved=False, verbose=False):
    lines: list[str] = []
    replies = list(answers)

    def ask(prompt: str) -> str:
        lines.append(prompt)
        if not replies:
            raise EOFError
        return replies.pop(0)

    code, outcomes = P.run_pipeline(repo.root, stages, dry_run=dry_run,
                                    accept_moved=accept_moved, verbose=verbose, ask=ask,
                                    out=lines.append)
    return code, outcomes, "\n".join(lines)


class ReportTests(unittest.TestCase):
    def test_single_line_diagnostics(self) -> None:
        section = P.diagnostics_section(GENERATION_REPORT)
        self.assertEqual(section, ["WARNING CHANGED_CASE [a]: Generated case differs "
                                   "from the maintained artifact."])
        self.assertEqual(P.severity_counts(section), {"WARNING": 1})

    def test_multiline_diagnostics_and_detail_heading(self) -> None:
        section = P.diagnostics_section(MULTILINE_REPORT)
        self.assertEqual(section[0], "ERROR MISSING_DEFINITION [X]")
        self.assertEqual(section[-1], "  Y is fine.")
        self.assertEqual(P.severity_counts(section), {"ERROR": 1, "INFO": 1})

    def test_section_ends_at_the_next_heading(self) -> None:
        report = "Diagnostics\n-----------\nINFO A: one\n\nLater\n-----\nINFO B: not a diagnostic\n"
        self.assertEqual(P.diagnostics_section(report), ["INFO A: one"])

    def test_condensed_keeps_warnings_and_counts_info(self) -> None:
        section = ["WARNING A [x]: one.", "  Source: a.md:1", "INFO MOVED_CASE [a]: m.",
                   "INFO MOVED_CASE [b]: m.", "  Source: b.md:2", "ERROR B [y]: two.",
                   "INFO NOTE [c]: n.", "INFO NOTE: no entry."]
        self.assertEqual(P.condensed(section),
                         ["WARNING A [x]: one.", "  Source: a.md:1", "ERROR B [y]: two.",
                          "INFO MOVED_CASE x2", "INFO NOTE x2"])

    def test_no_diagnostics(self) -> None:
        for body in ("No diagnostics.", "None.", "None"):
            self.assertEqual(P.diagnostics_section(f"Diagnostics\n-----------\n{body}\n"), [])
        self.assertEqual(P.diagnostics_section("Diagnostics: 0\n"), [])


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repo()

    def tearDown(self) -> None:
        self.repo.close()

    def test_accepted_promotion_copies_the_candidate(self) -> None:
        stage = self.repo.stage("gen", GENERATION_REPORT, '{"v": 2}\n', '{"v": 1}\n')
        code, outcomes, text = run(self.repo, [stage], ["y"])
        self.assertEqual(code, P.EXIT_OK)
        self.assertEqual((self.repo.root / stage.maintained).read_text(encoding="utf-8"),
                         '{"v": 2}\n')
        self.assertEqual(outcomes[0].status, "promoted")
        self.assertIn("WARNING CHANGED_CASE", text)
        self.assertIn("1 line(s) added, 1 removed", text)

    def test_declined_promotion_stops_the_pipeline(self) -> None:
        first = self.repo.stage("gen", GENERATION_REPORT, '{"v": 2}\n', '{"v": 1}\n')
        second = self.repo.stage("later", GENERATION_REPORT)
        code, outcomes, _ = run(self.repo, [first, second], ["n"])
        self.assertEqual(code, P.EXIT_DECLINED)
        self.assertEqual([o.status for o in outcomes], ["declined"])
        self.assertEqual((self.repo.root / first.maintained).read_text(encoding="utf-8"),
                         '{"v": 1}\n')

    def test_end_of_input_declines(self) -> None:
        stage = self.repo.stage("gen", GENERATION_REPORT, '{"v": 2}\n', '{"v": 1}\n')
        code, _, _ = run(self.repo, [stage], [])
        self.assertEqual(code, P.EXIT_DECLINED)

    def test_diff_is_shown_before_answering(self) -> None:
        stage = self.repo.stage("gen", GENERATION_REPORT, '{"v": 2}\n', '{"v": 1}\n')
        code, _, text = run(self.repo, [stage], ["d", "a", "maybe", "y"])
        self.assertEqual(code, P.EXIT_OK)
        self.assertIn('-  "v": 1', text)   # d: the material diff, re-indented
        self.assertIn('-{"v": 1}', text)    # a: the artifact's own lines
        self.assertIn('+{"v": 2}', text)
        self.assertIn("Answer y, n, d, a, or l.", text)

    def test_changes_are_classified(self) -> None:
        old = json.dumps({"cases": [case("a", "X", 1), case("b", "Y", 2)]})
        new = json.dumps({"cases": [case("a", "X", 5), case("b", "Z", 6)]})
        stage = self.repo.stage("gen", GENERATION_REPORT, new, old)
        code, _, text = run(self.repo, [stage], ["l", "d", "y"])
        self.assertEqual(code, P.EXIT_OK)
        self.assertIn("1 material, 1 moved (source lines only)", text)
        self.assertIn("material  cases:b", text)
        self.assertIn("moved     cases:a", text)
        material = text[text.index("moved     cases:a"):]
        self.assertIn('-        "Y"', material)
        self.assertNotIn('"line"', material[:material.index("Promoted")])

    def test_line_only_change_is_identified(self) -> None:
        old = json.dumps({"cases": [case("a", "X", 1)]})
        new = json.dumps({"cases": [case("a", "X", 9)]})
        stage = self.repo.stage("gen", GENERATION_REPORT, new, old)
        code, _, text = run(self.repo, [stage], ["d", "y"])
        self.assertEqual(code, P.EXIT_OK)
        self.assertIn("Only source line numbers or formatting changed", text)
        self.assertIn("no difference other than source line numbers", text)

    def test_accept_moved_promotes_line_only_changes_without_asking(self) -> None:
        old = json.dumps({"cases": [case("a", "X", 1)]})
        new = json.dumps({"cases": [case("a", "X", 9)]})
        stage = self.repo.stage("gen", GENERATION_REPORT, new, old)
        code, outcomes, text = run(self.repo, [stage], accept_moved=True)
        self.assertEqual((code, outcomes[0].status), (P.EXIT_OK, "promoted"))
        self.assertNotIn("Promote ", text)
        self.assertEqual((self.repo.root / stage.maintained).read_text(encoding="utf-8"), new)

    def test_accept_moved_still_asks_about_material_changes(self) -> None:
        old = json.dumps({"cases": [case("a", "X", 1)]})
        new = json.dumps({"cases": [case("a", "Y", 1)]})
        stage = self.repo.stage("gen", GENERATION_REPORT, new, old)
        code, _, text = run(self.repo, [stage], [], accept_moved=True)
        self.assertEqual(code, P.EXIT_DECLINED)
        self.assertIn("Promote ", text)

    def test_renamed_entry_names_its_old_identifier(self) -> None:
        old = json.dumps({"cases": [case("mri:3.1", "X", 1)]})
        new = json.dumps({"cases": [case("mri:3.2", "X", 4)]})
        stage = self.repo.stage("gen", GENERATION_REPORT, new, old)
        _, _, text = run(self.repo, [stage], ["y"])
        self.assertIn("renamed   cases:mri:3.2 (was cases:mri:3.1)", text)

    def test_quiet_output_counts_info_and_verbose_lists_it(self) -> None:
        stage = self.repo.stage("ext", MULTILINE_REPORT)
        _, _, quiet = run(self.repo, [stage])
        self.assertIn("[1/1] ext: 1 error, 1 info", quiet)
        self.assertIn("INFO NOTE x1", quiet)
        self.assertNotIn("Y is fine.", quiet)
        _, _, verbose = run(self.repo, [stage], verbose=True)
        self.assertIn("Y is fine.", verbose)

    def test_summary_says_whether_the_run_is_clean(self) -> None:
        clean = [P.Outcome("a", "ok", Counter({"INFO": 2})), P.Outcome("b", "unchanged", Counter())]
        self.assertEqual(P.summary(clean, 2)[-1], "Clean: no warnings, nothing pending.")
        dirty = [P.Outcome("a", "ok", Counter({"WARNING": 1})), P.Outcome("b", "pending", Counter())]
        self.assertEqual(P.summary(dirty, 2)[-1],
                         "Not clean: 1 warning(s) or error(s), 1 promotion(s) pending.")

    def test_unchanged_candidate_needs_no_promotion(self) -> None:
        stage = self.repo.stage("gen", GENERATION_REPORT, '{"v": 1}\n', '{"v": 1}\r\n')
        code, outcomes, text = run(self.repo, [stage])
        self.assertEqual(code, P.EXIT_OK)
        self.assertEqual(outcomes[0].status, "unchanged")
        self.assertNotIn("Promote", text)
        self.assertIn("WARNING CHANGED_CASE", text)

    def test_new_artifact_is_offered(self) -> None:
        stage = self.repo.stage("gen", GENERATION_REPORT, '{"v": 1}\n')
        code, _, text = run(self.repo, [stage], ["y"])
        self.assertEqual(code, P.EXIT_OK)
        self.assertIn("new artifact", text)
        self.assertTrue((self.repo.root / stage.maintained).exists())

    def test_failing_tool_stops_the_pipeline(self) -> None:
        first = self.repo.stage("bad", MULTILINE_REPORT, exit_code=1)
        second = self.repo.stage("later", GENERATION_REPORT)
        code, outcomes, text = run(self.repo, [first, second])
        self.assertEqual(code, P.EXIT_TOOL_FAILED)
        self.assertEqual([o.status for o in outcomes], ["failed"])
        self.assertIn("ERROR MISSING_DEFINITION [X]", text)
        self.assertIn("exited with status 1", text)

    def test_dry_run_never_asks_or_promotes(self) -> None:
        stage = self.repo.stage("gen", GENERATION_REPORT, '{"v": 2}\n', '{"v": 1}\n')
        code, outcomes, text = run(self.repo, [stage], dry_run=True)
        self.assertEqual(code, P.EXIT_OK)
        self.assertEqual(outcomes[0].status, "pending")
        self.assertNotIn("Promote", text)
        self.assertEqual((self.repo.root / stage.maintained).read_text(encoding="utf-8"),
                         '{"v": 1}\n')


class ReviewStepTests(unittest.TestCase):
    """The review after a run (review.py): asks only when the evidence disagrees."""

    def setUp(self) -> None:
        self.repo = Repo()
        root = self.repo.root
        (root / "m").mkdir()
        (root / "a").mkdir()
        schema = {"fields": [{"name": "ACN", "control_uses": ["predicate"], "outside_selection": True},
                             {"name": "SKIP", "control_uses": [], "outside_selection": False},
                             {"name": "OK", "control_uses": ["predicate"], "outside_selection": False}],
                  "diagnostics": [{"code": "CONTROL_USES_UNRESOLVED", "input_name": "SKIP"}]}
        (root / "m" / "inputs.json").write_text(json.dumps(schema), encoding="utf-8")
        (root / "m" / "words.json").write_text(json.dumps({"fields": []}), encoding="utf-8")
        analysis = {"inputs": [{"name": n, "kind": "control_input", "category": c} for n, c in
                               (("ACN", "unreferenced"), ("SKIP", "behavioral"), ("OK", "behavioral"))]}
        (root / "a" / "control-word-equivalence.json").write_text(json.dumps(analysis), encoding="utf-8")
        self.stages = [
            P.Stage("control-input-schema-generator", Path("x"), Path("x"), Path("none.json"),
                    Path("m/inputs.json")),
            P.Stage("control-word-schema-generator", Path("x"), Path("x"), None, Path("m/words.json")),
            P.Stage("control-word-equivalence-analyzer", Path("x"), Path("a/report.txt")),
        ]

    def tearDown(self) -> None:
        self.repo.close()

    def review(self, answers, dry_run=False):
        lines, replies = [], list(answers)

        def ask(prompt):
            lines.append(prompt)
            if not replies:
                raise EOFError
            return replies.pop(0)

        outcome = P.run_review(self.repo.root, self.stages, dry_run=dry_run, skip=frozenset(),
                               ask=ask, out=lines.append)
        data = json.loads((self.repo.root / "m" / "inputs.json").read_text(encoding="utf-8"))
        return outcome, {f["name"]: f["control_uses"] for f in data["fields"]}, "\n".join(lines)

    def test_accepting_records_and_removes_the_resolved_warning(self) -> None:
        outcome, uses, text = self.review(["y", "y"])
        self.assertEqual((outcome.status, outcome.decisions), ("recorded", 2))
        self.assertEqual(uses, {"ACN": ["none"], "SKIP": ["predicate"], "OK": ["predicate"]})
        self.assertIn("Review: 2 reviewed decision(s)", text)
        data = json.loads((self.repo.root / "m" / "inputs.json").read_text(encoding="utf-8"))
        self.assertEqual(data["diagnostics"], [])

    def test_typed_answer_and_skip(self) -> None:
        outcome, uses, text = self.review(["value", "s"])
        self.assertEqual(uses["ACN"], ["value"])
        self.assertEqual(uses["SKIP"], [])
        self.assertEqual(outcome.skipped, frozenset({("control-input-schema", "SKIP")}))

    def test_all_accepts_the_remaining_proposals(self) -> None:
        _, uses, _ = self.review(["a"])
        self.assertEqual((uses["ACN"], uses["SKIP"]), (["none"], ["predicate"]))

    def test_invalid_answer_asks_again(self) -> None:
        _, uses, text = self.review(["maybe", "y", "y"])
        self.assertIn("control uses are predicate and value, or none alone", text)
        self.assertEqual(uses["ACN"], ["none"])

    def test_dry_run_lists_without_asking_or_writing(self) -> None:
        outcome, uses, text = self.review([], dry_run=True)
        self.assertEqual((outcome.status, outcome.decisions), ("pending", 2))
        self.assertEqual(uses["ACN"], ["predicate"])
        self.assertNotIn("Record the proposal", text)

    def test_nothing_to_review_is_silent(self) -> None:
        self.review(["y", "y"])
        outcome, _, text = self.review([])
        self.assertIsNone(outcome)
        self.assertEqual(text, "")

    def test_a_partial_run_does_not_review(self) -> None:
        self.assertIsNone(P.review_paths(self.stages[:2]))

    def test_summary_counts_decisions_to_review(self) -> None:
        outcomes = [P.Outcome("a", "ok", Counter()), P.Outcome(P.REVIEW, "pending", Counter(), 3)]
        self.assertEqual(P.summary(outcomes, 1)[-1],
                         "Not clean: 0 warning(s) or error(s), 0 promotion(s) pending, "
                         "3 decision(s) to review.")


class StageTableTests(unittest.TestCase):
    def test_every_script_exists(self) -> None:
        for stage in P.STAGES:
            self.assertTrue((REPO / stage.script).is_file(), stage.script)

    def test_every_maintained_artifact_exists(self) -> None:
        maintained = [s.maintained for s in P.STAGES if s.maintained]
        self.assertEqual(len(maintained), 7)
        for path in maintained:
            self.assertTrue((REPO / path).is_file(), path)

    def test_stage_selection(self) -> None:
        stages = P.select_stages("timing-constraint-extractor", "symbolic-control-word-generator")
        self.assertEqual([s.name for s in stages], ["timing-constraint-extractor",
                                                    "timing-constraint-generator",
                                                    "symbolic-control-word-generator"])
        with self.assertRaises(SystemExit):
            P.select_stages("no-such-stage", None)
        with self.assertRaises(SystemExit):
            P.select_stages("control-store-packer", "control-input-extractor")

    def test_list(self) -> None:
        with mock.patch.dict(os.environ), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(P.main(["--list", "--design", "v2"]), P.EXIT_OK)
        self.assertIn("13. symbolic-control-word-generator  -> rom/microcode/v2/"
                      "symbolic-control-words.json", out.getvalue())

    def test_list_frozen_design_is_packer_only(self) -> None:  # V1-ONLY
        with mock.patch.dict(os.environ), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(P.main(["--list", "--design", "v1"]), P.EXIT_OK)
        self.assertIn("frozen", out.getvalue())
        self.assertIn(" 1. control-store-packer\n", out.getvalue())
        self.assertNotIn("control-input-extractor", out.getvalue())

    def test_stages_follow_the_design(self) -> None:
        stages = P.stages_for(P.select("v2"))
        self.assertEqual(len(stages), len(P.STAGES))
        self.assertTrue(all(Path(s.report).as_posix().startswith("build/simulation_outputs/rom-generation-v2/")
                            for s in stages))
        self.assertTrue(all(Path(s.maintained).as_posix().startswith("rom/microcode/v2/")
                            for s in stages if s.maintained))
        self.assertEqual(P.runnable(P.select("v2"), stages), stages)


class OutputEncodingTests(unittest.TestCase):
    def test_unencodable_report_text_does_not_crash(self) -> None:
        # A cp1252 console cannot encode the micro sign that tool reports may contain.
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="\n")
        saved = sys.stdout
        sys.stdout = stream
        try:
            P.tolerate_unencodable_output()
            print("ERROR UNRECOGNIZED_OPR_LINE: no μop")
            stream.flush()
        finally:
            sys.stdout = saved
        self.assertEqual(raw.getvalue(), b"ERROR UNRECOGNIZED_OPR_LINE: no ?op\n")

    def test_streams_without_reconfigure_are_left_alone(self) -> None:
        with redirect_stdout(io.StringIO()):
            P.tolerate_unencodable_output()


if __name__ == "__main__":
    unittest.main()
