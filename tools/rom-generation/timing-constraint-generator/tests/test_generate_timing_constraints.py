"""Tests for the timing-constraint generator."""

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

from generate_timing_constraints import (
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


def make_constraint(constraint_id: str = "timing:5.2.5.1", **fields) -> dict:
    constraint = {
        "id": constraint_id,
        "context": "MS = EXECUTE AND TS = 3 AND (IOT_READ_PENDING = 1)",
        "requirement": "IO_CLEAR_AC_REQ != 1",
        "source": {"path": "docs/timing.md", "line": 12},
    }
    constraint.update(fields)
    return constraint


def make_extracted(*constraints: dict, **fields) -> dict:
    data = {
        "format_version": 1,
        "control_design_version": "v1",
        "artifact": "timing-constraints",
        "extraction_stage": "documentation-extraction",
        "sources": ["docs/timing.md"],
        "constraints": list(constraints)
        if constraints
        else [make_constraint()],
        "diagnostics": [],
    }
    data.update(fields)
    return data


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


# ---------------------------------------------------------------------------
# Arguments and reading
# ---------------------------------------------------------------------------


class ArgumentAndReadTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_defaults_and_paths(self) -> None:
        options = parse_arguments(["--repo-root", "."])
        root = Path("repository").resolve()
        absolute = Path("elsewhere/x.json").resolve()

        self.assertEqual(options.extracted, DEFAULT_EXTRACTED)
        self.assertEqual(
            options.maintained,
            Path("rom/microcode/v1/timing-constraints.json"),
        )
        self.assertEqual(options.candidate_output, DEFAULT_CANDIDATE)
        self.assertEqual(options.report_output, DEFAULT_REPORT)
        self.assertEqual(
            resolve_from_repo(root, Path("a.json")), root / "a.json"
        )
        self.assertEqual(resolve_from_repo(root, absolute), absolute)

    def test_optional_input_may_be_missing_or_blank(self) -> None:
        blank = self.directory / "blank.json"
        blank.write_text("\n", encoding="utf-8")

        self.assertIsNone(read_json(self.directory / "none", optional=True))
        self.assertIsNone(read_json(blank, optional=True))

    def test_unreadable_inputs_fail(self) -> None:
        cases = {
            "missing.json": (None, "does not exist"),
            "utf8.json": (b"\xff", "not valid UTF-8"),
            "json.json": (b"{", "not valid JSON"),
            "list.json": (b"[]", "must be a JSON object"),
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
        diagnostics, constraints = validate_extracted(make_extracted())

        self.assertEqual(diagnostics, [])
        self.assertEqual(list(constraints), ["timing:5.2.5.1"])

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
            "extraction_stage": ("extraction", "UNSUPPORTED_EXTRACTION_STAGE"),
            "sources": ("docs/timing.md", "INVALID_SOURCES"),
            "diagnostics": ({}, "INVALID_EXTRACTOR_DIAGNOSTICS"),
        }
        for field, (value, code) in cases.items():
            with self.subTest(field=field):
                diagnostics, _ = validate_extracted(
                    make_extracted(**{field: value})
                )
                self.assertEqual(codes(diagnostics), [code])

        diagnostics, _ = validate_extracted(make_extracted(sources=[1]))
        self.assertEqual(codes(diagnostics), ["INVALID_SOURCES"])

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

    def test_constraints_must_be_identified_objects(self) -> None:
        diagnostics, _ = validate_extracted(
            make_extracted(
                make_constraint(),
                "text",
                make_constraint(None),
                make_constraint(""),
                make_constraint(),
            )
        )

        self.assertEqual(
            [(d.code, d.constraint_id) for d in diagnostics],
            [("INVALID_EXTRACTED_CONSTRAINTS", None)] * 3
            + [("INVALID_EXTRACTED_CONSTRAINTS", "timing:5.2.5.1")],
        )

    def test_constraints_must_be_an_array(self) -> None:
        diagnostics, constraints = validate_extracted(
            make_extracted(constraints={})
        )

        self.assertEqual(codes(diagnostics), ["INVALID_EXTRACTED_CONSTRAINTS"])
        self.assertEqual(constraints, {})

    def test_malformed_constraint_fields(self) -> None:
        cases = {
            "context": [None, "", "  ", 3],
            "requirement": [None, ""],
            "source": [
                None,
                {"path": "x"},
                {"path": "x", "line": True},
                {"path": 1, "line": 3},
            ],
        }
        for field, values in cases.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    diagnostics, _ = validate_extracted(
                        make_extracted(make_constraint(**{field: value}))
                    )
                    self.assertEqual(
                        [
                            (d.code, d.constraint_id, d.field_name)
                            for d in diagnostics
                        ],
                        [
                            (
                                "INVALID_CONSTRAINT_FIELD",
                                "timing:5.2.5.1",
                                field,
                            )
                        ],
                    )


class MaintainedValidationTests(unittest.TestCase):
    def test_missing_maintained_is_first_generation(self) -> None:
        candidate, diagnostics = build_candidate(make_extracted(), None)

        self.assertIsNotNone(candidate)
        self.assertEqual(codes(diagnostics), ["NEW_CONSTRAINT"])

    def test_version_mismatch_blocks(self) -> None:
        maintained = make_extracted(control_design_version="v2")

        candidate, diagnostics = build_candidate(make_extracted(), maintained)

        self.assertIsNone(candidate)
        self.assertEqual(
            codes(diagnostics), ["CONTROL_DESIGN_VERSION_MISMATCH"]
        )

    def test_malformed_maintained_constraints_block(self) -> None:
        maintained = make_extracted(
            "text", make_constraint(), make_constraint()
        )

        candidate, diagnostics = build_candidate(make_extracted(), maintained)

        self.assertIsNone(candidate)
        self.assertEqual(
            codes(diagnostics), ["INVALID_MAINTAINED_CONSTRAINTS"] * 2
        )
        self.assertIn("Maintained artifact", diagnostics[0].message)


# ---------------------------------------------------------------------------
# Review and candidate
# ---------------------------------------------------------------------------


class ReviewTests(unittest.TestCase):
    def test_unchanged_has_no_diagnostics(self) -> None:
        extracted = make_extracted()

        candidate, diagnostics = build_candidate(
            extracted, copy.deepcopy(extracted)
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(diagnostics, [])

    def test_new_changed_and_stale(self) -> None:
        extracted = make_extracted(
            make_constraint("changed"),
            make_constraint("new"),
            make_constraint("same"),
        )
        maintained = make_extracted(
            make_constraint("stale"),
            make_constraint("changed", requirement="X != 1"),
            make_constraint("same"),
        )

        _, diagnostics = build_candidate(extracted, maintained)

        self.assertEqual(
            diagnostics,
            [
                Diagnostic(
                    "WARNING",
                    "CHANGED_CONSTRAINT",
                    "Extracted constraint differs from the maintained artifact.",
                    "changed",
                ),
                Diagnostic(
                    "WARNING",
                    "NEW_CONSTRAINT",
                    "Constraint is not present in the maintained artifact.",
                    "new",
                ),
                Diagnostic(
                    "WARNING",
                    "STALE_CONSTRAINT",
                    "Maintained constraint is absent from the extracted artifact.",
                    "stale",
                ),
            ],
        )

    def test_candidate_keeps_constraints_and_order(self) -> None:
        constraints = [make_constraint("z"), make_constraint("a")]

        candidate, _ = build_candidate(make_extracted(*constraints), None)

        self.assertEqual(
            candidate,
            {
                "format_version": 1,
                "control_design_version": "v1",
                "artifact": "timing-constraints",
                "generation_stage": "candidate-generation",
                "sources": ["docs/timing.md"],
                "constraints": constraints,
                "diagnostics": [],
            },
        )

    def test_promoted_candidate_reviews_clean(self) -> None:
        extracted = make_extracted(make_constraint("a"), make_constraint("b"))
        candidate, _ = build_candidate(extracted, None)

        again, diagnostics = build_candidate(extracted, candidate)

        self.assertEqual(diagnostics, [])
        self.assertEqual(again, candidate)

    def test_any_error_blocks_the_candidate(self) -> None:
        candidate, diagnostics = build_candidate(
            make_extracted(make_constraint(context=None)), None
        )

        self.assertIsNone(candidate)
        self.assertEqual(codes(diagnostics), ["INVALID_CONSTRAINT_FIELD"])


class ReportTests(unittest.TestCase):
    def test_report(self) -> None:
        diagnostics = [
            Diagnostic("WARNING", "NEW_CONSTRAINT", "New.", "x"),
            Diagnostic(
                "ERROR", "INVALID_CONSTRAINT_FIELD", "Bad.", "x", "context"
            ),
            Diagnostic("FATAL", "GENERATION_FAILURE", "Broken."),
        ]

        self.assertEqual(
            build_report(diagnostics, 2, False),
            "Timing-Constraint Candidate Generation Report\n"
            "=============================================\n\n"
            "Constraints processed: 2\n"
            "Candidate written: no\n"
            "Information diagnostics: 0\n"
            "Warnings: 1\n"
            "Errors: 1\n"
            "Fatal errors: 1\n\n"
            "Diagnostics\n"
            "-----------\n"
            "WARNING NEW_CONSTRAINT [x]: New.\n"
            "ERROR INVALID_CONSTRAINT_FIELD [x] [context]: Bad.\n"
            "FATAL GENERATION_FAILURE: Broken.\n",
        )
        self.assertTrue(
            build_report([], 0, True).endswith("No diagnostics.\n")
        )


# ---------------------------------------------------------------------------
# Contract with the timing-constraint extractor
# ---------------------------------------------------------------------------

EXTRACTOR_GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "timing-constraint-extractor"
    / "tests"
    / "golden"
    / "valid"
    / "timing-constraints.json"
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
        diagnostics, constraints = validate_extracted(self.extracted)

        self.assertEqual(diagnostics, [])
        self.assertTrue(constraints)

    def test_builders_match_extractor_shapes(self) -> None:
        self.assertEqual(list(make_extracted()), list(self.extracted))
        self.assertEqual(
            list(make_constraint()), list(self.extracted["constraints"][0])
        )


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

    def write(self, path: Path, data: dict) -> None:
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
            make_constraint("new"),
            make_constraint("changed"),
            make_constraint("same"),
        )
        maintained = make_extracted(
            make_constraint("changed", context="TS = 3"),
            make_constraint("stale"),
            make_constraint("same"),
        )
        self.write(DEFAULT_EXTRACTED, extracted)
        self.write(DEFAULT_MAINTAINED, maintained)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Candidate written: yes", stdout)
        self.assertEqual(
            self.candidate.read_text(encoding="utf-8"),
            json.dumps(
                build_candidate(extracted, None)[0],
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
        )
        self.assert_report_matches_golden("review")

    def test_failed_run_removes_earlier_candidate(self) -> None:
        extracted = make_extracted(
            make_constraint(requirement=""),
            make_constraint("x", source=None),
            extraction_stage="extraction",
        )
        self.write(DEFAULT_EXTRACTED, extracted)
        self.candidate.parent.mkdir(parents=True)
        self.candidate.write_text("stale\n", encoding="utf-8")

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        self.assertIn(
            "ERROR INVALID_CONSTRAINT_FIELD [timing:5.2.5.1] [requirement]\n"
            "  Constraint requirement must be a nonempty string.",
            stdout,
        )
        self.assert_report_matches_golden("invalid")

    def test_missing_extracted_is_fatal(self) -> None:
        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn("FATAL GENERATION_FAILURE", stdout)
        self.assertIn(
            "Constraints processed: 0", self.report.read_text(encoding="utf-8")
        )

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
