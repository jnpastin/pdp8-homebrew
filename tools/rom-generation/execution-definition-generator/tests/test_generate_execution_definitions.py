"""Tests for the execution-definition generator."""

from __future__ import annotations

import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_execution_definitions import (
    DEFAULT_CANDIDATE,
    DEFAULT_EXTRACTED,
    DEFAULT_MAINTAINED,
    DEFAULT_REPORT,
    REQUIRED_TOP_LEVEL,
    Diagnostic,
    GenerationFailure,
    build_candidate,
    build_report,
    main,
    parse_arguments,
    read_json,
    resolve_from_repo,
    validate_extracted,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_case(case_id: str = "mri:3.1:ts1", **fields) -> dict:
    case = {
        "id": case_id,
        "source": {"path": "docs/example.md", "line": 3},
        "execution_model": "major-state",
        "context": ["MS = EXECUTE", "IR_IS_MRI = 1"],
        "timing_state": 1,
        "micro_operations": ["EA_ADDR_TO_MA"],
        "conditional_micro_operations": [
            {"predicate": "CIFP = 0", "micro_operation": "II_CLEAR"}
        ],
    }
    case.update(fields)
    return case


def make_extracted(*cases: dict, **fields) -> dict:
    data = {
        "format_version": 1,
        "control_design_version": "v1",
        "artifact": "execution-definitions",
        "extraction_stage": "documentation-extraction",
        "cases": list(cases) if cases else [make_case()],
        "diagnostics": [],
    }
    data.update(fields)
    return data


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


def build(extracted: dict, maintained: dict | None = None):
    return build_candidate(extracted, maintained)


# ---------------------------------------------------------------------------
# Arguments and reading
# ---------------------------------------------------------------------------


class ArgumentAndReadTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_defaults(self) -> None:
        options = parse_arguments(["--repo-root", "."])

        self.assertEqual(options.extracted, DEFAULT_EXTRACTED)
        self.assertEqual(
            options.maintained,
            Path("rom/microcode/v1/execution-definitions.json"),
        )
        self.assertEqual(options.candidate_output, DEFAULT_CANDIDATE)
        self.assertEqual(options.report_output, DEFAULT_REPORT)

    def test_paths_resolve_from_repo_root(self) -> None:
        root = Path("repository").resolve()
        absolute = Path("elsewhere/x.json").resolve()

        self.assertEqual(
            resolve_from_repo(root, Path("a/b.json")), root / "a" / "b.json"
        )
        self.assertEqual(resolve_from_repo(root, absolute), absolute)

    def test_optional_input_may_be_missing_or_blank(self) -> None:
        blank = self.directory / "blank.json"
        blank.write_text(" \n", encoding="utf-8")

        self.assertIsNone(read_json(self.directory / "none", optional=True))
        self.assertIsNone(read_json(blank, optional=True))

    def test_unreadable_inputs_fail(self) -> None:
        cases = {
            "missing.json": (None, "does not exist"),
            "utf8.json": (b"\xff", "not valid UTF-8"),
            "json.json": (b"{", "not valid JSON"),
            "list.json": (b"[]", "must be a JSON object"),
            "blank.json": (b"", "not valid JSON"),
        }
        for name, (content, message) in cases.items():
            with self.subTest(name=name):
                path = self.directory / name
                if content is not None:
                    path.write_bytes(content)
                with self.assertRaisesRegex(GenerationFailure, message):
                    read_json(path)

        with self.assertRaisesRegex(GenerationFailure, "Unable to read"):
            read_json(self.directory)


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


class ExtractedValidationTests(unittest.TestCase):
    def test_valid_artifact(self) -> None:
        diagnostics, cases = validate_extracted(make_extracted())

        self.assertEqual(diagnostics, [])
        self.assertEqual(list(cases), ["mri:3.1:ts1"])

    def test_missing_top_level_fields(self) -> None:
        for field in REQUIRED_TOP_LEVEL:
            with self.subTest(field=field):
                data = make_extracted()
                del data[field]
                diagnostics, _ = validate_extracted(data)
                self.assertIn("MISSING_TOP_LEVEL_FIELDS", codes(diagnostics))

    def test_unsupported_header_values(self) -> None:
        cases = {
            "artifact": ("other", "UNEXPECTED_ARTIFACT_TYPE"),
            "format_version": (2, "UNSUPPORTED_FORMAT_VERSION"),
            "extraction_stage": ("other", "UNSUPPORTED_EXTRACTION_STAGE"),
            "diagnostics": ({}, "INVALID_EXTRACTOR_DIAGNOSTICS"),
        }
        for field, (value, code) in cases.items():
            with self.subTest(field=field):
                diagnostics, _ = validate_extracted(
                    make_extracted(**{field: value})
                )
                self.assertEqual(codes(diagnostics), [code])

    def test_extractor_failures_block(self) -> None:
        for severity, expected in (
            ("WARNING", []),
            ("ERROR", ["EXTRACTOR_FAILURE_DIAGNOSTICS"]),
            ("FATAL", ["EXTRACTOR_FAILURE_DIAGNOSTICS"]),
        ):
            with self.subTest(severity=severity):
                diagnostics, _ = validate_extracted(
                    make_extracted(diagnostics=[{"severity": severity}])
                )
                self.assertEqual(codes(diagnostics), expected)

    def test_cases_must_be_identified_objects(self) -> None:
        diagnostics, _ = validate_extracted(
            make_extracted(
                make_case(),
                "text",
                make_case(None),
                make_case(""),
                make_case(),
            )
        )

        self.assertEqual(
            [(d.code, d.case_id) for d in diagnostics],
            [("INVALID_EXTRACTED_CASES", None)] * 3
            + [("INVALID_EXTRACTED_CASES", "mri:3.1:ts1")],
        )
        self.assertEqual(
            diagnostics[3].message,
            "Extracted artifact contains duplicate case id mri:3.1:ts1.",
        )

    def test_cases_must_be_an_array(self) -> None:
        diagnostics, cases = validate_extracted(make_extracted(cases={}))

        self.assertEqual(codes(diagnostics), ["INVALID_EXTRACTED_CASES"])
        self.assertEqual(cases, {})

    def test_malformed_case_fields(self) -> None:
        cases = {
            "source": [None, {"path": "x"}, {"path": "x", "line": "3"}],
            "execution_model": ["console", None],
            "context": ["MS = EXECUTE", [1]],
            "timing_state": [0, 5, None, True, "1"],
            "micro_operations": [None, [None]],
            "conditional_micro_operations": [
                None,
                ["X"],
                [{"predicate": "A"}],
                [{"predicate": "A", "micro_operation": 1}],
                [{"micro_operation": "X", "predicate": "A"}],
            ],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    diagnostics, _ = validate_extracted(
                        make_extracted(make_case(**{field: value}))
                    )
                    self.assertEqual(
                        [
                            (d.code, d.case_id, d.field_name)
                            for d in diagnostics
                        ],
                        [("INVALID_CASE_FIELD", "mri:3.1:ts1", field)],
                    )

    def test_console_transactions_have_no_timing_state(self) -> None:
        console = make_case(
            "console:6",
            execution_model="console-transaction",
            timing_state=None,
        )
        timed = make_case(
            "console:7", execution_model="console-transaction", timing_state=1
        )

        diagnostics, _ = validate_extracted(make_extracted(console, timed))

        self.assertEqual(
            [(d.case_id, d.message) for d in diagnostics],
            [
                (
                    "console:7",
                    (
                        "Case timing_state must be null for a console "
                        "transaction."
                    ),
                )
            ],
        )


class MaintainedValidationTests(unittest.TestCase):
    def test_missing_maintained_is_first_generation(self) -> None:
        candidate, diagnostics = build(make_extracted())

        self.assertIsNotNone(candidate)
        self.assertEqual(codes(diagnostics), ["NEW_CASE"])

    def test_version_mismatch_blocks(self) -> None:
        maintained = make_extracted(control_design_version="v2")

        candidate, diagnostics = build(make_extracted(), maintained)

        self.assertIsNone(candidate)
        self.assertEqual(
            codes(diagnostics), ["CONTROL_DESIGN_VERSION_MISMATCH"]
        )

    def test_malformed_maintained_cases_block(self) -> None:
        maintained = make_extracted("text", make_case(), make_case())

        candidate, diagnostics = build(make_extracted(), maintained)

        self.assertIsNone(candidate)
        self.assertEqual(codes(diagnostics), ["INVALID_MAINTAINED_CASES"] * 2)
        self.assertIn("Maintained artifact", diagnostics[0].message)

    def test_maintained_case_fields_are_not_checked(self) -> None:
        maintained = make_extracted(make_case(timing_state=9))

        candidate, diagnostics = build(make_extracted(), maintained)

        self.assertIsNotNone(candidate)
        self.assertEqual(codes(diagnostics), ["CHANGED_CASE"])


# ---------------------------------------------------------------------------
# Review and candidate
# ---------------------------------------------------------------------------


class ReviewTests(unittest.TestCase):
    def test_unchanged_has_no_diagnostics(self) -> None:
        extracted = make_extracted()

        candidate, diagnostics = build(extracted, copy.deepcopy(extracted))

        self.assertIsNotNone(candidate)
        self.assertEqual(diagnostics, [])

    def test_new_changed_and_stale(self) -> None:
        extracted = make_extracted(
            make_case("changed"), make_case("new"), make_case("same")
        )
        maintained = make_extracted(
            make_case("stale"),
            make_case("changed", micro_operations=["MB_INC"]),
            make_case("same"),
        )

        _, diagnostics = build(extracted, maintained)

        self.assertEqual(
            diagnostics,
            [
                Diagnostic(
                    "WARNING",
                    "CHANGED_CASE",
                    "Extracted case differs from the maintained artifact.",
                    "changed",
                ),
                Diagnostic(
                    "WARNING",
                    "NEW_CASE",
                    "Case is not present in the maintained artifact.",
                    "new",
                ),
                Diagnostic(
                    "WARNING",
                    "STALE_CASE",
                    "Maintained case is absent from the extracted artifact.",
                    "stale",
                ),
            ],
        )

    def test_candidate_keeps_cases_and_order(self) -> None:
        cases = [make_case("z"), make_case("a", context=["MS = FETCH"])]
        extracted = make_extracted(*cases)

        candidate, _ = build(extracted)

        self.assertEqual(
            candidate,
            {
                "format_version": 1,
                "control_design_version": "v1",
                "artifact": "execution-definitions",
                "generation_stage": "candidate-generation",
                "cases": cases,
                "diagnostics": [],
            },
        )

    def test_promoted_candidate_reviews_clean(self) -> None:
        extracted = make_extracted(make_case("a"), make_case("b"))
        candidate, _ = build(extracted)

        again, diagnostics = build(extracted, candidate)

        self.assertEqual(diagnostics, [])
        self.assertEqual(again, candidate)

    def test_any_error_blocks_the_candidate(self) -> None:
        candidate, diagnostics = build(make_extracted(make_case(context=None)))

        self.assertIsNone(candidate)
        self.assertEqual(codes(diagnostics), ["INVALID_CASE_FIELD"])


class ReportTests(unittest.TestCase):
    def test_report(self) -> None:
        diagnostics = [
            Diagnostic("WARNING", "NEW_CASE", "New.", "x"),
            Diagnostic("ERROR", "INVALID_CASE_FIELD", "Bad.", "x", "context"),
            Diagnostic("FATAL", "GENERATION_FAILURE", "Broken."),
        ]

        self.assertEqual(
            build_report(diagnostics, 2, False),
            "Execution-Definition Candidate Generation Report\n"
            "================================================\n\n"
            "Cases processed: 2\n"
            "Candidate written: no\n"
            "Information diagnostics: 0\n"
            "Warnings: 1\n"
            "Errors: 1\n"
            "Fatal errors: 1\n\n"
            "Diagnostics\n"
            "-----------\n"
            "WARNING NEW_CASE [x]: New.\n"
            "ERROR INVALID_CASE_FIELD [x] [context]: Bad.\n"
            "FATAL GENERATION_FAILURE: Broken.\n",
        )

    def test_empty_report(self) -> None:
        self.assertTrue(
            build_report([], 0, True).endswith(
                "Candidate written: yes\n"
                "Information diagnostics: 0\n"
                "Warnings: 0\n"
                "Errors: 0\n"
                "Fatal errors: 0\n\n"
                "Diagnostics\n"
                "-----------\n"
                "No diagnostics.\n"
            )
        )


# ---------------------------------------------------------------------------
# Contract with the execution-definition extractor
# ---------------------------------------------------------------------------

EXTRACTOR_GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "execution-definition-extractor"
    / "tests"
    / "golden"
    / "valid"
    / "execution-definitions.json"
)


class ExtractorContractTests(unittest.TestCase):
    """Keep this tool's input in step with the extractor's real output.

    The extractor's golden output is the reference. If these tests fail
    after an extractor change, update this tool (and its builders) to match.
    """

    def setUp(self) -> None:
        self.extracted = json.loads(
            EXTRACTOR_GOLDEN.read_text(encoding="utf-8")
        )

    def test_extractor_output_passes_structural_validation(self) -> None:
        self.assertEqual(validate_extracted(self.extracted)[0], [])

    def test_extractor_output_covers_both_execution_models(self) -> None:
        models = {case["execution_model"] for case in self.extracted["cases"]}

        self.assertEqual(models, {"major-state", "console-transaction"})

    def test_builders_match_extractor_shapes(self) -> None:
        self.assertEqual(list(make_extracted()), list(self.extracted))
        self.assertEqual(list(make_case()), list(self.extracted["cases"][0]))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

GOLDEN_DIRECTORY = Path(__file__).resolve().parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"


class MainTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.candidate = self.root / DEFAULT_CANDIDATE
        self.report = self.root / DEFAULT_REPORT

    def write(self, path: Path, data: dict | None) -> None:
        if data is not None:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data), encoding="utf-8")

    def run_main(self, *extra: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.root), *extra])
        return exit_code, stdout.getvalue()

    def assert_report_matches_golden(self, name: str) -> None:
        """Compare the report against ``golden/<name>/``.

        Run with ``UPDATE_GOLDEN=1`` to rewrite the expected file after an
        intended output change, then review the diff.
        """

        actual = self.report.read_bytes().decode("utf-8")
        golden_path = GOLDEN_DIRECTORY / name / "generation-report.txt"
        if UPDATE_GOLDEN:
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(actual, encoding="utf-8", newline="\n")
        self.assertEqual(actual, golden_path.read_text(encoding="utf-8"))

    def test_review_run_writes_candidate_and_report(self) -> None:
        extracted = make_extracted(
            make_case("new"),
            make_case("changed"),
            make_case(
                "console:6",
                execution_model="console-transaction",
                timing_state=None,
                context=["RUN = 0", "FP_START = 1"],
                micro_operations=["AC_CLEAR"],
                conditional_micro_operations=[],
            ),
        )
        maintained = make_extracted(
            make_case("changed", timing_state=2), make_case("stale")
        )
        maintained["cases"].append(extracted["cases"][2])
        self.write(DEFAULT_EXTRACTED, extracted)
        self.write(DEFAULT_MAINTAINED, maintained)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Candidate written: yes", stdout)
        self.assertEqual(
            self.candidate.read_text(encoding="utf-8"),
            json.dumps(build(extracted)[0], indent=2, ensure_ascii=False)
            + "\n",
        )
        self.assert_report_matches_golden("review")

    def test_failed_run_removes_earlier_candidate(self) -> None:
        extracted = make_extracted(
            make_case(timing_state=7),
            make_case("x", context="MS = FETCH"),
            diagnostics=[{"severity": "ERROR"}],
        )
        self.write(DEFAULT_EXTRACTED, extracted)
        self.candidate.parent.mkdir(parents=True)
        self.candidate.write_text("stale\n", encoding="utf-8")

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        self.assertIn(
            "ERROR INVALID_CASE_FIELD [mri:3.1:ts1] [timing_state]\n"
            "  Case timing_state must be 1 to 4.",
            stdout,
        )
        self.assert_report_matches_golden("invalid")

    def test_missing_extracted_is_fatal(self) -> None:
        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn("FATAL GENERATION_FAILURE", stdout)
        self.assertIn(
            "Cases processed: 0", self.report.read_text(encoding="utf-8")
        )
        self.assertFalse(self.candidate.exists())

    def test_output_that_is_an_input_is_refused(self) -> None:
        self.write(DEFAULT_EXTRACTED, make_extracted())

        exit_code, stdout = self.run_main(
            "--report-output", str(DEFAULT_EXTRACTED)
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout)
        self.assertTrue((self.root / DEFAULT_EXTRACTED).exists())

    def test_output_that_is_a_directory_is_refused(self) -> None:
        self.write(DEFAULT_EXTRACTED, make_extracted())
        self.report.parent.mkdir(parents=True)
        self.report.write_text("earlier\n", encoding="utf-8")
        (self.root / "dir").mkdir()

        exit_code, stdout = self.run_main("--candidate-output", "dir")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout)
        self.assertTrue(self.report.exists())


if __name__ == "__main__":
    unittest.main()
