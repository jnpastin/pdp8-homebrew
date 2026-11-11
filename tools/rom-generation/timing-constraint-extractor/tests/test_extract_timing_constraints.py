"""Tests for the timing-constraint extractor."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extract_timing_constraints import (
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    SOURCE_PATH,
    Diagnostic,
    ExtractionFailure,
    build_report,
    extract_constraints,
    main,
    parse_arguments,
    read_source,
    resolve_from_repo,
)

PATH = "docs/timing.md"
SCOPE = "Applicable context:\n\n```text\nMS = EXECUTE\nIOT_ACTIVE = 1\n```\n\n"


def extract(text: str):
    return extract_constraints(text, PATH)


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


def contexts(text: str) -> list[str]:
    constraints, diagnostics = extract(text)
    assert diagnostics == [], diagnostics
    return [constraint["context"] for constraint in constraints]


# ---------------------------------------------------------------------------
# Arguments and reading
# ---------------------------------------------------------------------------


class ArgumentAndReadTests(unittest.TestCase):
    def test_defaults_and_paths(self) -> None:
        options = parse_arguments(["--repo-root", "."])
        root = Path("repository").resolve()
        absolute = Path("elsewhere/x.json").resolve()

        self.assertEqual(options.json_output, DEFAULT_JSON_OUTPUT)
        self.assertEqual(options.report_output, DEFAULT_REPORT_OUTPUT)
        self.assertEqual(resolve_from_repo(root, Path("a.md")), root / "a.md")
        self.assertEqual(resolve_from_repo(root, absolute), absolute)

    def test_unreadable_sources_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            bad = folder / "bad.md"
            bad.write_bytes(b"\xff")

            with self.assertRaisesRegex(ExtractionFailure, "does not exist"):
                read_source(folder / "missing.md")
            with self.assertRaisesRegex(ExtractionFailure, "not valid UTF-8"):
                read_source(bad)
            with self.assertRaisesRegex(ExtractionFailure, "Unable to read"):
                read_source(folder)


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


class ConstraintTests(unittest.TestCase):
    def test_constraint(self) -> None:
        text = (
            "## 5. EXECUTE\n\n### 5.2 External IOT\n\n"
            + SCOPE
            + "#### 5.2.5 TS3\n\n"
            "- Rule:\n"
            "  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1 OR X = 1`\n"
        )

        constraints, diagnostics = extract(text)

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            constraints,
            [
                {
                    "id": "timing:5.2.5.1",
                    "context": "MS = EXECUTE AND IOT_ACTIVE = 1 AND TS = 3 "
                    "AND (IOT_READ_PENDING = 1 OR X = 1)",
                    "requirement": "IO_CLEAR_AC_REQ != 1",
                    "source": {"path": PATH, "line": 15},
                }
            ],
        )

    def test_ids_number_constraints_within_their_heading(self) -> None:
        constraints, _ = extract(
            "## 5. A\n\n" + SCOPE + "### 5.1 TS4\n\n- `A IF B`\n- `C IF D`\n"
            "### 5.2 TS1\n\n- `E IF F`\n"
        )

        self.assertEqual(
            [item["id"] for item in constraints],
            ["timing:5.1.1", "timing:5.1.2", "timing:5.2.1"],
        )

    def test_nearest_scope_applies(self) -> None:
        text = (
            "## 5. A\n\n" + SCOPE + "### 5.1 B\n\nApplicable context:\n\n"
            "```text\nMS = FETCH\n```\n\n#### 5.1.1 TS2\n\n- `A IF B`\n"
            "### 5.2 C\n\n#### 5.2.1 TS1\n\n- `C IF D`\n"
        )

        self.assertEqual(
            contexts(text),
            [
                "MS = FETCH AND TS = 2 AND (B)",
                "MS = EXECUTE AND IOT_ACTIVE = 1 AND TS = 1 AND (D)",
            ],
        )

    def test_other_bullets_and_code_are_ignored(self) -> None:
        text = (
            "## 5. A\n\n" + SCOPE + "### 5.1 TS3\n\n"
            "- `IOT_ACTIVE` is asserted.\n"
            "- `IOT_ACTIVE`\n"
            "- plain IF text\n"
            "- `A IF B` and prose\n"
            "```text\n- `X IF Y`\n### 9.9 TS1\n```\n"
            "- `C IF D`\n"
        )

        self.assertEqual(
            contexts(text),
            ["MS = EXECUTE AND IOT_ACTIVE = 1 AND TS = 3 AND (D)"],
        )

    def test_constraint_needs_a_timing_state_heading(self) -> None:
        text = (
            "## 5. A\n\n" + SCOPE + "- `A IF B`\n"
            "### 5.1 TS3\n\n#### 5.1.1 TP3\n\n- `C IF D`\n"
        )

        constraints, diagnostics = extract(text)

        self.assertEqual(constraints, [])
        self.assertEqual(
            [(d.code, d.line) for d in diagnostics],
            [("MISSING_TIMING_CONTEXT", 10), ("MISSING_TIMING_CONTEXT", 15)],
        )

    def test_constraint_needs_a_scope(self) -> None:
        constraints, diagnostics = extract(
            "## 5. A\n\n### 5.1 TS3\n\n- `A IF B`\n"
        )

        self.assertEqual(constraints, [])
        self.assertEqual(
            [(d.code, d.constraint_id) for d in diagnostics],
            [("MISSING_SCOPE", "timing:5.1.1")],
        )

    def test_malformed_constraint(self) -> None:
        constraints, diagnostics = extract(
            "## 5. A\n\n" + SCOPE + "### 5.1 TS3\n\n- ` IF B`\n- `A IF `\n"
        )

        self.assertEqual(constraints, [])
        self.assertEqual(
            [(d.code, d.constraint_id) for d in diagnostics],
            [
                ("MALFORMED_CONSTRAINT", "timing:5.1.1"),
                ("MALFORMED_CONSTRAINT", "timing:5.1.2"),
            ],
        )

    def test_scope_needs_a_nonempty_code_block(self) -> None:
        for text in (
            "## 5. A\n\nApplicable context:\n\nMS = EXECUTE\n",
            "## 5. A\n\nApplicable context:\n\n```text\n```\n",
            "## 5. A\n\nApplicable context:\n## 6. B\n",
            "## 5. A\n\nApplicable context:\n\nprose\n\n```text\nMS = X\n```\n",
        ):
            with self.subTest(text=text):
                _, diagnostics = extract(text + "### 5.1 TS1\n\n- `A IF B`\n")
                self.assertEqual(
                    codes(diagnostics), ["MISSING_CODE_BLOCK", "MISSING_SCOPE"]
                )
                self.assertEqual(diagnostics[0].line, 3)

    def test_scope_label_at_end_of_document_is_an_error(self) -> None:
        _, diagnostics = extract(
            "- `Z IF Y`\n## 5. A\n\n### 5.1 TS1\n\n- `A IF B`\n\n"
            "Applicable context:\n"
        )

        self.assertEqual(
            [(d.code, d.line) for d in diagnostics],
            [
                ("MISSING_CODE_BLOCK", 8),
                ("MISSING_SCOPE", 6),
                ("MISSING_TIMING_CONTEXT", 1),
            ],
        )

    def test_second_scope_in_a_section_is_an_error(self) -> None:
        _, diagnostics = extract(
            "## 5. A\n\n" + SCOPE + SCOPE + "### 5.1 TS1\n\n- `A IF B`\n"
        )

        self.assertEqual(codes(diagnostics), ["DUPLICATE_SCOPE"])

    def test_repeated_heading_number_repeats_ids(self) -> None:
        constraints, diagnostics = extract(
            "## 5. A\n\n" + SCOPE + "### 5.1 TS1\n\n- `A IF B`\n"
            "### 5.1 TS2\n\n- `C IF D`\n"
        )

        self.assertEqual(len(constraints), 2)
        self.assertEqual(
            [(d.code, d.line, d.constraint_id) for d in diagnostics],
            [("DUPLICATE_CONSTRAINT_ID", 15, "timing:5.1.1")],
        )

    def test_document_without_constraints_is_an_error(self) -> None:
        _, diagnostics = extract("## 5. A\n\n- prose\n")

        self.assertEqual(codes(diagnostics), ["NO_CONSTRAINTS_FOUND"])

    def test_diagnostics_are_sorted(self) -> None:
        _, diagnostics = extract(
            "## 5. A\n\n### 5.1 TS1\n\n- ` IF B`\n- `A IF B`\n"
            "## 6. B\n\n- `C IF D`\n"
        )

        self.assertEqual(
            codes(diagnostics),
            [
                "MALFORMED_CONSTRAINT",
                "MISSING_SCOPE",
                "MISSING_TIMING_CONTEXT",
            ],
        )


class ReportTests(unittest.TestCase):
    def test_report(self) -> None:
        diagnostics = [
            Diagnostic("ERROR", "A", "First.", PATH, 3, "timing:5.1.1"),
            Diagnostic("FATAL", "B", "Second.", "<input>"),
        ]

        self.assertEqual(
            build_report(diagnostics, 1),
            "Timing-Constraint Extraction Report\n"
            "===================================\n\n"
            "Constraints extracted: 1\n"
            "Information diagnostics: 0\n"
            "Warnings: 0\n"
            "Errors: 1\n"
            "Fatal errors: 1\n\n"
            "Diagnostics\n"
            "-----------\n"
            f"ERROR A [timing:5.1.1] {PATH}:3: First.\n"
            "FATAL B <input>: Second.\n",
        )
        self.assertTrue(build_report([], 0).endswith("No diagnostics.\n"))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

GOLDEN_DIRECTORY = Path(__file__).resolve().parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"

VALID_DOCUMENT = (
    "# Major State Timing\n\n"
    "## 3. FETCH\n\n### 3.1 TS1 — Address Setup\n\n- PC drives MA\n\n"
    "## 5. EXECUTE\n\n### 5.2 EXECUTE: External IOT\n\n"
    + SCOPE
    + "#### 5.2.5 TS3\n\n"
    "- `IOT_READ_PENDING` causes CPU control to assert `/DB_READ`.\n"
    "- The controller may assert `IO_CLEAR_AC_REQ` only when idle:\n"
    "  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1 OR "
    "IOT_WRITE_PENDING = 1`\n\n"
    "#### 5.2.6 TP3\n\n- A pending read commits.\n\n"
    "#### 5.2.7 TS4\n\n"
    "- The controller may assert `IO_CLEAR_AC_REQ` only when no skip:\n"
    "  - `IO_CLEAR_AC_REQ != 1 IF IOT_READ_PENDING = 1 OR IO_SKIP_REQ = 1`\n"
    "  - `IO_SKIP_REQ != 1 IF IOT_WRITE_PENDING = 1`\n"
)

INVALID_DOCUMENT = (
    "## 5. EXECUTE\n\n- `A IF B`\n\n"
    "### 5.2 External IOT\n\nApplicable context:\n\nMS = EXECUTE\n\n"
    "#### 5.2.5 TS3\n\n- ` IF B`\n- `C IF D`\n\n"
    "#### 5.2.6 TP3\n\n- `E IF F`\n"
)


class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.source = self.root / SOURCE_PATH
        self.json_output = self.root / DEFAULT_JSON_OUTPUT
        self.report_output = self.root / DEFAULT_REPORT_OUTPUT

    def write_source(self, text: str) -> None:
        self.source.parent.mkdir(parents=True, exist_ok=True)
        self.source.write_text(text, encoding="utf-8")

    def run_main(self, *extra: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.root), *extra])
        return exit_code, stdout.getvalue()

    def assert_outputs_match_golden(self, name: str) -> None:
        """Compare the JSON and report against ``golden/<name>/``.

        Run with ``UPDATE_GOLDEN=1`` to rewrite the expected files after an
        intended output change, then review the diff.
        """

        outputs = {
            "timing-constraints.json": self.json_output,
            "extraction-report.txt": self.report_output,
        }
        for file_name, output in outputs.items():
            with self.subTest(file=file_name):
                actual = output.read_bytes().decode("utf-8")
                golden_path = GOLDEN_DIRECTORY / name / file_name
                if UPDATE_GOLDEN:
                    golden_path.parent.mkdir(parents=True, exist_ok=True)
                    golden_path.write_text(
                        actual, encoding="utf-8", newline="\n"
                    )
                self.assertEqual(
                    actual, golden_path.read_text(encoding="utf-8")
                )

    def test_valid_outputs_match_golden(self) -> None:
        self.write_source(VALID_DOCUMENT)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Constraints: 3", stdout)
        self.assert_outputs_match_golden("valid")

    def test_invalid_outputs_match_golden(self) -> None:
        self.write_source(INVALID_DOCUMENT)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "ERROR MALFORMED_CONSTRAINT [timing:5.2.5.1]\n"
            f"  Source: {SOURCE_PATH.as_posix()}:13",
            stdout,
        )
        self.assert_outputs_match_golden("invalid")

    def test_missing_source_is_fatal_and_removes_earlier_json(self) -> None:
        self.json_output.parent.mkdir(parents=True)
        self.json_output.write_text("stale\n", encoding="utf-8")

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.json_output.exists())
        self.assertIn(
            "FATAL EXTRACTION_FAILURE <input>: Required source does not exist",
            self.report_output.read_text(encoding="utf-8"),
        )
        self.assertIn("Constraints: 0", stdout)

    def test_output_that_is_an_input_is_refused(self) -> None:
        self.write_source(VALID_DOCUMENT)

        exit_code, stdout = self.run_main("--json-output", str(SOURCE_PATH))

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout)
        self.assertEqual(
            self.source.read_text(encoding="utf-8"), VALID_DOCUMENT
        )

    def test_output_that_is_a_directory_is_refused(self) -> None:
        self.write_source(VALID_DOCUMENT)
        self.report_output.parent.mkdir(parents=True)
        self.report_output.write_text("earlier\n", encoding="utf-8")
        (self.root / "dir").mkdir()

        exit_code, stdout = self.run_main("--json-output", "dir")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout)
        self.assertTrue(self.report_output.exists())


if __name__ == "__main__":
    unittest.main()
