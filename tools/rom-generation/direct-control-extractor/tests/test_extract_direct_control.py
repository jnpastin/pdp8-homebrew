"""Tests for the direct-control extractor."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extract_direct_control import (  # noqa: E402
    CODE_FIELDS,
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    SOURCE_PATHS,
    Diagnostic,
    ExtractionFailure,
    build_report,
    collect_sections,
    extract_direct_control,
    extract_document,
    main,
    parse_arguments,
    parse_headings,
    read_source,
    resolve_from_repo,
)

PATH = "docs/01-example.md"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def code(text: str) -> str:
    return f"```text\n{text}\n```"


def case(
    number: str = "3.2.1",
    title: str = "Example",
    *sections: tuple[str, str],
    level: int = 4,
) -> str:
    """Return one definition built from ``(label, body)`` sections.

    Without sections, the definition has a single assignment.
    """

    if not sections:
        sections = (("Assignment", code("MS_NEXT = EXECUTE")),)
    body = "".join(f"{label}:\n\n{text}\n\n" for label, text in sections)
    return f"{'#' * level} {number} {title}\n\n{body}"


def document(*cases: str) -> str:
    return "## 3. Sequencing\n\n### 3.2 Cases\n\n" + "".join(cases)


def extract(*cases: str):
    return extract_document(document(*cases), PATH)


def only(*cases: str) -> dict:
    definitions, diagnostics = extract(*cases)
    assert diagnostics == [], diagnostics
    assert len(definitions) == 1, definitions
    return definitions[0]


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


# ---------------------------------------------------------------------------
# Arguments, paths, and reading
# ---------------------------------------------------------------------------


class ArgumentAndPathTests(unittest.TestCase):
    def test_default_outputs_are_used(self) -> None:
        options = parse_arguments(["--repo-root", "."])

        self.assertEqual(options.json_output, DEFAULT_JSON_OUTPUT)
        self.assertEqual(options.report_output, DEFAULT_REPORT_OUTPUT)

    def test_relative_path_is_resolved_from_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                resolve_from_repo(Path(directory), Path("x")),
                (Path(directory) / "x").resolve(),
            )

    def test_absolute_path_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = (Path(directory) / "x").resolve()
            self.assertEqual(resolve_from_repo(Path.cwd(), path), path)


class ReadSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def test_missing_source_fails(self) -> None:
        with self.assertRaisesRegex(ExtractionFailure, "does not exist"):
            read_source(self.root / "missing.md")

    def test_invalid_utf8_fails(self) -> None:
        path = self.root / "x.md"
        path.write_bytes(b"\xff")

        with self.assertRaisesRegex(ExtractionFailure, "not valid UTF-8"):
            read_source(path)

    def test_unreadable_source_fails(self) -> None:
        with self.assertRaisesRegex(ExtractionFailure, "Unable to read"):
            read_source(self.root)


# ---------------------------------------------------------------------------
# Headings and definition selection
# ---------------------------------------------------------------------------


class HeadingTests(unittest.TestCase):
    def test_numbered_and_unnumbered_headings(self) -> None:
        headings = parse_headings(
            ["# Title", "## 3. Sequencing", "### Appendix", "#### 3.2.1 Case"]
        )

        self.assertEqual(
            [(h.level, h.number, h.title, h.line) for h in headings],
            [
                (2, "3", "Sequencing", 2),
                (3, None, "Appendix", 3),
                (4, "3.2.1", "Case", 4),
            ],
        )
        self.assertEqual(headings[2].full_title, "3.2.1 Case")
        self.assertEqual(headings[1].full_title, "Appendix")

    def test_headings_in_code_blocks_are_ignored(self) -> None:
        headings = parse_headings(["```text", "## 9. Not", "```", "## 1. Yes"])

        self.assertEqual([h.title for h in headings], ["Yes"])

    def test_only_leaf_numbered_headings_are_definitions(self) -> None:
        definitions, _ = extract(
            case("3.2.1"),
            case("3.2.2", "Parent", ("Assignment", code("X = 1"))),
            case("3.2.2.1", "Child", level=4),
        )

        self.assertEqual(
            [item["id"] for item in definitions],
            ["01:3.2.1", "01:3.2.2", "01:3.2.2.1"],
        )

    def test_parent_with_nested_heading_is_skipped(self) -> None:
        definitions, _ = extract(
            case("3.3", "Parent", ("Assignment", code("X = 1")), level=3),
            case("3.3.1", "Child"),
        )

        self.assertEqual([item["id"] for item in definitions], ["01:3.3.1"])

    def test_level_five_and_six_headings_are_recognized(self) -> None:
        definitions, _ = extract(
            case("3.2.1", "Parent", ("Assignment", code("X = 1"))),
            case("3.2.1.1", "Child", ("Assignment", code("Y = 1")), level=5),
            case("3.2.1.1.1", "Leaf", ("Assignment", code("Z = 1")), level=6),
        )

        self.assertEqual(
            [(item["id"], item["group"]) for item in definitions],
            [("01:3.2.1.1.1", "3.2.1.1 Child")],
        )
        self.assertEqual(definitions[0]["direct_assignments"], ["Z = 1"])

    def test_group_is_the_enclosing_heading(self) -> None:
        self.assertEqual(only(case())["group"], "3.2 Cases")

    def test_top_level_definition_has_no_group(self) -> None:
        definitions, _ = extract_document(case("7", "Top", level=2), PATH)

        self.assertIsNone(definitions[0]["group"])

    def test_definition_requires_a_content_section(self) -> None:
        definitions, diagnostics = extract(
            case("3.2.1", "Example", ("Constraints", "- only a constraint")),
            "## 4. Purpose\n\nText only.\n",
        )

        self.assertEqual((definitions, diagnostics), ([], []))

    def test_definition_ends_at_next_same_level_heading(self) -> None:
        text = document(
            case(
                "3.2.1",
                "Example",
                ("Assignment", code("X = 1")),
                ("Sources", "- [A](a.md)"),
            )
        )

        definitions, _ = extract_document(
            text + "## 4. Related\n\n- [B](b.md)\n", PATH
        )

        self.assertEqual(
            definitions[0]["sources"], [{"label": "A", "target": "a.md"}]
        )


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


class SectionTests(unittest.TestCase):
    def test_labels_start_and_prose_ends_sections(self) -> None:
        sections = collect_sections(
            [
                "ignored",
                "Assignment:",
                "```text",
                "Label inside code:",
                "```",
                "Examples include:",
                "dropped",
                "Commit:",
                "kept",
                "Commit:",
                "again",
            ]
        )

        self.assertEqual(
            sections,
            {
                "direct_assignments": ["```text\nLabel inside code:\n```"],
                "state_commits": ["kept", "again"],
            },
        )

    def test_every_label_fills_its_field(self) -> None:
        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Applicable context", code("MS = FETCH")),
                ("Assignments", code("A = 1")),
                ("Logical control results", code("B = 1")),
                ("Micro-operation assignments", code("C = 1")),
                ("Control-supplied value", code("D_VAL = 0")),
                ("Value relationship", code("E = F")),
                ("Widths", code("E: 3")),
                ("Commits", code("G <- 1")),
                ("Constraint", "- one\n  - nested"),
                ("Source", "- [Doc]( ../doc.md ) and [Two](two.md#x)"),
                ("CPU behavior", code("holds")),
                ("CPU output-drive state", code("CPU DB driver = HIGH_Z")),
                ("External ownership", code("memory drives MDB")),
                ("Memory behavior", code("reads")),
                ("Related derived values", code("IOA = IR_IOA")),
            )
        )

        self.assertEqual(
            {key: value for key, value in definition.items() if value},
            {
                "id": "01:3.2.1",
                "title": "3.2.1 Example",
                "group": "3.2 Cases",
                "source": {"path": PATH, "line": 5},
                "applicable_context": ["MS = FETCH"],
                "direct_assignments": ["A = 1"],
                "micro_operation_assignments": ["B = 1", "C = 1"],
                "control_supplied_values": ["D_VAL = 0"],
                "value_relationships": ["E = F"],
                "widths": ["E: 3"],
                "state_commits": ["G <- 1"],
                "constraints": ["one", "nested"],
                "sources": [
                    {"label": "Doc", "target": "../doc.md"},
                    {"label": "Two", "target": "two.md#x"},
                ],
                "drive_states": ["holds", "CPU DB driver = HIGH_Z"],
                "external_ownership": ["memory drives MDB"],
                "memory_behavior": ["reads"],
                "derived_values": ["IOA = IR_IOA"],
            },
        )

    def test_definition_key_order(self) -> None:
        self.assertEqual(
            list(only(case())),
            [
                "id",
                "title",
                "group",
                "source",
                "applicable_context",
                "direct_assignments",
                "control_supplied_values",
                "micro_operation_assignments",
                "state_commits",
                "value_relationships",
                "widths",
                "constraints",
                "sources",
                "drive_states",
                "external_ownership",
                "memory_behavior",
                "derived_values",
            ],
        )

    def test_each_code_block_is_one_value(self) -> None:
        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Assignment", code("A = 1\nB  = 2") + "\n\n" + code("C = 3")),
            )
        )

        self.assertEqual(
            definition["direct_assignments"], ["A = 1\nB  = 2", "C = 3"]
        )

    def test_empty_section_is_ignored(self) -> None:
        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Applicable context", ""),
                ("Assignment", code("X = 1")),
            )
        )

        self.assertEqual(definition["applicable_context"], [])

    def test_or_separates_alternative_contexts(self) -> None:
        context = code("A = 1") + "\n\nor:\n\n" + code("A = 2") + "\n\nOr:\n\n"
        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Applicable context", context + code("A = 3")),
                ("Assignment", code("X = 1")),
            )
        )

        self.assertEqual(
            definition["applicable_context"], ["A = 1", "A = 2", "A = 3"]
        )

    def test_or_is_kept_in_a_prose_context(self) -> None:
        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Applicable context", "RUN = 1\n\nor:\n\nHLT = 1"),
                ("Assignment", code("X = 1")),
            )
        )

        self.assertEqual(
            definition["applicable_context"], ["RUN = 1\n\nor:\n\nHLT = 1"]
        )

    def test_or_ends_other_sections(self) -> None:
        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Assignment", code("X = 1") + "\n\nor:\n\n" + code("X = 2")),
            )
        )

        self.assertEqual(definition["direct_assignments"], ["X = 1"])

    def test_applicable_context_falls_back_to_prose(self) -> None:
        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Applicable context", "RUN = 1\nAND\nno halt applies"),
                ("Assignment", code("RUN_NEXT = 1")),
            )
        )

        self.assertEqual(
            definition["applicable_context"], ["RUN = 1\nAND\nno halt applies"]
        )

    def test_applicable_context_keeps_indentation(self) -> None:
        context = "RUN = 1\nNOT (\n    HLT_REQ = 1\n    AND TS = 4\n)"

        definition = only(
            case(
                "3.2.1",
                "Example",
                ("Applicable context", code(context)),
                ("Assignment", code("X = 1")),
            )
        )

        self.assertEqual(definition["applicable_context"], [context])


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationTests(unittest.TestCase):
    def test_section_without_text_code_block_is_an_error(self) -> None:
        for body in (
            "MS_NEXT = FETCH",
            "```python\nX = 1\n```",
            "```text\n```",
            "```text\n \n```",
        ):
            with self.subTest(body=body):
                definitions, diagnostics = extract(
                    case(
                        "3.2.1",
                        "Example",
                        ("Assignment", body),
                        ("Commit", code("MS <- FETCH")),
                    )
                )

                self.assertEqual(definitions[0]["direct_assignments"], [])
                self.assertEqual(codes(diagnostics), ["UNSTRUCTURED_FIELD"])
                self.assertEqual(
                    diagnostics[0].message,
                    "The 'direct_assignments' section must contain a text "
                    "code block.",
                )

    def test_definition_without_content_is_an_error(self) -> None:
        definitions, diagnostics = extract(
            case(
                "3.2.1",
                "Example",
                ("Assignment", "X = 1"),
                ("Widths", code("X: 1")),
            )
        )

        self.assertEqual(len(definitions), 1)
        self.assertEqual(
            [(d.code, d.line, d.definition_id) for d in diagnostics],
            [
                ("UNSTRUCTURED_FIELD", 5, "01:3.2.1"),
                ("EMPTY_DEFINITION", 5, "01:3.2.1"),
            ],
        )

    def test_duplicate_ids_are_reported_on_the_repeat(self) -> None:
        definitions, diagnostics = extract_direct_control(
            [
                (PATH, document(case(), case())),
                ("docs/02-other.md", document(case())),
            ]
        )

        self.assertEqual(
            [item["id"] for item in definitions],
            ["01:3.2.1", "01:3.2.1", "02:3.2.1"],
        )
        self.assertEqual(
            [(d.code, d.line) for d in diagnostics],
            [("DUPLICATE_DEFINITION_ID", definitions[1]["source"]["line"])],
        )

    def test_diagnostics_are_sorted(self) -> None:
        _, diagnostics = extract_direct_control(
            [
                (
                    PATH,
                    document(
                        case("3.2.2", "B", ("Assignment", "x")),
                        case("3.2.1", "A", ("Assignment", "y")),
                    ),
                )
            ]
        )

        self.assertEqual(
            [(d.code, d.definition_id) for d in diagnostics],
            [
                ("EMPTY_DEFINITION", "01:3.2.2"),
                ("EMPTY_DEFINITION", "01:3.2.1"),
                ("UNSTRUCTURED_FIELD", "01:3.2.2"),
                ("UNSTRUCTURED_FIELD", "01:3.2.1"),
            ],
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OutputTests(unittest.TestCase):
    def test_report(self) -> None:
        report = build_report(
            [
                Diagnostic("ERROR", "E", "Err.", PATH, 5, "01:1"),
                Diagnostic("FATAL", "F", "Fatal.", "<input>"),
            ],
            3,
        )

        self.assertEqual(
            report,
            "Direct-Control Extraction Report\n"
            "================================\n"
            "\n"
            "Definitions extracted: 3\n"
            "Information diagnostics: 0\n"
            "Warnings: 0\n"
            "Errors: 1\n"
            "Fatal errors: 1\n"
            "\n"
            "Diagnostics\n"
            "-----------\n"
            f"ERROR E [01:1] {PATH}:5: Err.\n"
            "FATAL F <input>: Fatal.\n",
        )

    def test_empty_report_says_no_diagnostics(self) -> None:
        self.assertTrue(build_report([], 0).endswith("No diagnostics.\n"))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

GOLDEN_DIRECTORY = Path(__file__).resolve().parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"

VALID_DOCUMENTS = (
    "# Sequencing and Internal Control\n\n"
    "## 1. Purpose\n\n"
    "This document defines direct-control results for:\n\n"
    "- sequencing\n\n"
    "## 3. Major-State Sequencing\n\n"
    "### 3.2 Major-State Transitions\n\n"
    + case(
        "3.2.1",
        "FETCH to EXECUTE",
        ("Applicable context", code("RUN = 1\nMS = FETCH\nTS = 4")),
        ("Assignment", code("MS_NEXT = EXECUTE")),
        ("Commit", code("MS <- EXECUTE at TP4")),
        ("Constraints", "- One transition per TS4."),
        (
            "Sources",
            "- [State Model](../../03-microarchitecture/00-state-model.md)",
        ),
    )
    + "---\n\n"
    + case(
        "3.2.2",
        "Continued Running",
        ("Applicable context", "RUN = 1\nAND\nno halt condition applies"),
        ("Assignment", code("RUN_NEXT = 1")),
    )
    + "Examples include:\n\n"
    + code("FETCH -> EXECUTE")
    + "\n\n### 3.3 Memory Reads\n\n"
    + case(
        "3.3.1",
        "MRI Read",
        (
            "Applicable context",
            code("MS = EXECUTE\nIR_MRI_OPCODE = 000")
            + "\n\nor:\n\n"
            + code("MS = EXECUTE\nIR_MRI_OPCODE = 001"),
        ),
        ("Assignment", code("AB_SRC = MA")),
    )
    + case("3.3.2", "Direct Access", ("Constraints", "- Never uses DF."))
    + case(
        "3.3.2.1",
        "Direct Read",
        ("Applicable context", code("TS = 2")),
        ("Assignment", code("MFB_SRC = IF")),
        level=5,
    )
    + "\n\n## 5. Value Bindings\n\n"
    + case(
        "5.1",
        "Data Field from Instruction",
        (
            "Micro-operation assignments",
            code("DF_LOAD = 1\nDF_SRC  = Control"),
        ),
        ("Control-supplied value", code("DF_VAL = IR_DF")),
        ("Widths", code("DF_VAL: 3")),
        level=3,
    ),
    "# Interface and Ownership Control\n\n"
    "## 4. Memory Interface\n\n"
    + case(
        "4.2",
        "Memory Read",
        ("Applicable context", code("MEM_READ_TO_MB is selected")),
        ("Micro-operation assignments", code("/RD = 0\n/WR = 1")),
        ("CPU output-drive states", code("CPU MDB driver = HIGH_Z")),
        ("Memory behavior", code("memory drives MDB")),
        level=3,
    )
    + "## 5. DMA Ownership\n\n"
    + case(
        "5.2",
        "DMA Ownership",
        ("Assignment", code("/DMA_GRANT = 0")),
        ("External ownership", code("DMA controller drives AB")),
        ("Related derived values", code("IOA = IR_IOA")),
        ("Value relationships", code("IOA = IR[8:3]")),
        level=3,
    ),
)

INVALID_DOCUMENTS = (
    document(
        case("3.2.1", "Prose", ("Assignment", "MS_NEXT = FETCH")),
        case("3.2.2", "Python", ("Commit", "```python\nMS <- FETCH\n```")),
        case("3.2.3"),
        case("3.2.3", "Repeat"),
    ),
    document(case("3.2.1", "Other file")),
)


class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.json_output = self.root / DEFAULT_JSON_OUTPUT
        self.report_output = self.root / DEFAULT_REPORT_OUTPUT

    def write_sources(self, texts) -> None:
        for path, text in zip(SOURCE_PATHS, texts, strict=False):
            source = self.root / path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(text, encoding="utf-8")

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
            "direct-control-definitions.json": self.json_output,
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
        self.write_sources(VALID_DOCUMENTS)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Definitions: 7", stdout)
        self.assert_outputs_match_golden("valid")

    def test_invalid_outputs_match_golden(self) -> None:
        self.write_sources(INVALID_DOCUMENTS)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "ERROR DUPLICATE_DEFINITION_ID\n"
            f"  Source: {SOURCE_PATHS[0].as_posix()}:",
            stdout,
        )
        self.assert_outputs_match_golden("invalid")

    def test_unreadable_source_is_fatal(self) -> None:
        self.write_sources(VALID_DOCUMENTS[:1])
        self.json_output.parent.mkdir(parents=True)
        self.json_output.write_text("stale\n", encoding="utf-8")

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.json_output.exists())
        report = self.report_output.read_text(encoding="utf-8")
        self.assertIn("Definitions extracted: 0", report)
        self.assertIn(
            "FATAL EXTRACTION_FAILURE <input>: Required source does not exist",
            report,
        )
        self.assertIn("Definitions: 0", stdout)

    def test_output_that_is_an_input_is_refused(self) -> None:
        self.write_sources(VALID_DOCUMENTS)

        exit_code, stdout = self.run_main(
            "--report-output", str(SOURCE_PATHS[0])
        )

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout)
        self.assertEqual(
            (self.root / SOURCE_PATHS[0]).read_text(encoding="utf-8"),
            VALID_DOCUMENTS[0],
        )

    def test_output_that_is_a_directory_is_refused(self) -> None:
        self.write_sources(VALID_DOCUMENTS)
        self.report_output.parent.mkdir(parents=True)
        self.report_output.write_text("earlier\n", encoding="utf-8")
        (self.root / "dir").mkdir()

        exit_code, stdout = self.run_main("--json-output", "dir")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout)
        self.assertTrue(self.report_output.exists())

    def test_code_fields_never_contain_fences(self) -> None:
        self.write_sources(VALID_DOCUMENTS)
        self.run_main()

        data = json.loads(self.json_output.read_text(encoding="utf-8"))

        for definition in data["definitions"]:
            for field in CODE_FIELDS:
                self.assertFalse(
                    any("```" in value for value in definition[field]),
                    (definition["id"], field),
                )


if __name__ == "__main__":
    unittest.main()
