"""Tests for the micro-operation extractor."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extract_micro_operations import (  # noqa: E402
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    SOURCE_PATH,
    Diagnostic,
    ExtractionFailure,
    build_json_result,
    build_report,
    extract_definition_blocks,
    extract_micro_operations,
    group_labeled_sections,
    main,
    normalize_markdown_text,
    parse_arguments,
    read_source,
    resolve_from_repo,
    serialize_json,
)

PATH = "docs/uops.md"

# The document preamble puts the first definition heading on line 9.
PREAMBLE = (
    "# Micro-Operations\n"
    "\n"
    "## 4. Index\n"
    "\n"
    "### NOT_A_DEFINITION\n"
    "\n"
    "## 5. μop Definitions (Alphabetical)\n"
    "\n"
)
CLOSING = "\n## 6. Notes\n\n### ALSO_NOT_A_DEFINITION\n"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def definition(name: str = "PC_INC", extra: str = "", **values: str) -> str:
    """Return a definition; keyword values replace or (if None) drop labels."""

    attributes = {
        "Category": "Control Flow",
        "Description": "Increment PC.",
        "Target": "PC",
        "Expression": "PC ← PC + 1",
        "Sources": "PC",
    }
    attributes.update(values)
    body = "".join(
        f"**{label}:** {value}\n"
        for label, value in attributes.items()
        if value is not None
    )
    return f"### {name}\n\n{body}{extra}\n---\n\n"


def document(*definitions: str) -> str:
    return PREAMBLE + "".join(definitions or [definition()]) + CLOSING


def extract(*definitions: str):
    return extract_micro_operations(document(*definitions), PATH)


def only(*definitions: str) -> dict:
    """Return the JSON form of the single extracted micro-operation."""

    result = extract(*definitions)
    return build_json_result(result)["micro_operations"][0]


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
        with self.assertRaisesRegex(ExtractionFailure, "could not be read"):
            read_source(self.root)


# ---------------------------------------------------------------------------
# Markdown and definition blocks
# ---------------------------------------------------------------------------


class MarkdownTests(unittest.TestCase):
    def test_escapes_and_inline_code_are_removed(self) -> None:
        self.assertEqual(
            normalize_markdown_text(r"`A\_B` \<x\> ``c``"), "A_B <x> `c`"
        )


class DefinitionBlockTests(unittest.TestCase):
    def test_blocks_follow_document_order(self) -> None:
        blocks, diagnostics = extract_definition_blocks(
            document(definition("B"), definition("A")), PATH
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual([block.name for block in blocks], ["B", "A"])
        self.assertEqual(blocks[0].start_line, 9)
        self.assertEqual(blocks[0].lines[0], (10, ""))

    def test_section_ends_at_same_level_heading(self) -> None:
        blocks, _ = extract_definition_blocks(document(), PATH)

        self.assertEqual([block.name for block in blocks], ["PC_INC"])
        self.assertNotIn("## 6. Notes", [text for _, text in blocks[0].lines])

    def test_section_number_is_optional(self) -> None:
        for title in (
            "## μop Definitions (Alphabetical)",
            "## 7.1 μop Definitions (Alphabetical)",
        ):
            with self.subTest(title=title):
                text = f"{title}\n\n{definition()}"

                blocks, diagnostics = extract_definition_blocks(text, PATH)

                self.assertEqual(diagnostics, [])
                self.assertEqual(len(blocks), 1)

    def test_section_may_be_nested(self) -> None:
        text = (
            "### 5. μop Definitions (Alphabetical)\n\n"
            "#### A\n### End\n#### B\n"
        )

        blocks, _ = extract_definition_blocks(text, PATH)

        self.assertEqual([block.name for block in blocks], ["A"])

    def test_deeper_headings_are_block_content(self) -> None:
        blocks, _ = extract_definition_blocks(
            document(definition(extra="#### Detail\n")), PATH
        )

        self.assertIn((16, "#### Detail"), blocks[0].lines)

    def test_headings_in_code_fences_are_ignored(self) -> None:
        fenced = definition(extra="```text\n### NOT_A_HEADING\n```\n")

        blocks, _ = extract_definition_blocks(document(fenced), PATH)

        self.assertEqual([block.name for block in blocks], ["PC_INC"])

    def test_heading_markup_is_normalized(self) -> None:
        blocks, _ = extract_definition_blocks(
            document(definition(r"`AC\_CLEAR`")), PATH
        )

        self.assertEqual(blocks[0].name, "AC_CLEAR")

    def test_missing_section_is_reported(self) -> None:
        blocks, diagnostics = extract_definition_blocks("# Other\n", PATH)

        self.assertEqual(blocks, [])
        self.assertEqual(codes(diagnostics), ["MISSING_DEFINITION_SECTION"])

    def test_empty_section_is_reported(self) -> None:
        _, diagnostics = extract_definition_blocks(PREAMBLE + CLOSING, PATH)

        self.assertEqual(codes(diagnostics), ["NO_MICRO_OPERATIONS"])


# ---------------------------------------------------------------------------
# Labeled sections and attributes
# ---------------------------------------------------------------------------


class LabeledSectionTests(unittest.TestCase):
    def sections(self, body: str):
        blocks, _ = extract_definition_blocks(
            document(f"### X\n\n{body}"), PATH
        )
        return group_labeled_sections(blocks[0])

    def test_lines_are_grouped_under_labels(self) -> None:
        sections = self.sections(
            "ignored\n**Category:** A\nmore\n**Target:**\nT\n"
        )

        self.assertEqual(
            [(s.label, s.line, s.inline, s.lines) for s in sections],
            [
                ("category", 12, "A", ((13, "more"),)),
                ("target", 14, "", ((15, "T"), (16, ""))),
            ],
        )

    def test_several_labels_may_share_a_line(self) -> None:
        sections = self.sections("**Category:** A **Target:** T\n")

        self.assertEqual(
            [(s.label, s.line, s.inline) for s in sections],
            [("category", 11, "A"), ("target", 11, "T")],
        )

    def test_labels_are_case_insensitive(self) -> None:
        sections = self.sections("**category :** A\n**CONSTRAINTS:**\n")

        self.assertEqual(
            [s.label for s in sections], ["category", "constraints"]
        )

    def test_unrecognized_labels_are_text(self) -> None:
        sections = self.sections("**Category:** A\n**Note:** B\n")

        self.assertEqual(sections[0].lines[0], (12, "**Note:** B"))


class AttributeTests(unittest.TestCase):
    def test_single_line_attributes(self) -> None:
        operation = only(definition())

        self.assertEqual(
            [
                operation[key]
                for key in (
                    "category",
                    "description",
                    "targets",
                    "expression",
                    "sources",
                )
            ],
            ["Control Flow", "Increment PC.", ["PC"], ["PC ← PC + 1"], ["PC"]],
        )

    def test_multiline_attributes(self) -> None:
        operation = only(
            definition(
                Category="\nRegister\nTransfer",
                Description="\nLine one.\nLine two.",
                Target="\nAC, `L`",
            )
        )

        self.assertEqual(operation["category"], "Register Transfer")
        self.assertEqual(operation["description"], "Line one. Line two.")
        self.assertEqual(operation["targets"], ["AC", "L"])

    def test_expression_lines_are_kept_in_order(self) -> None:
        expression = (
            "\n```text\nif X:\n    AC ← MQ\nelse:\n    MQ ← AC\n```\nWhere:"
        )

        operation = only(definition(Expression=expression))

        self.assertEqual(
            operation["expression"],
            ["if X:", "AC ← MQ", "else:", "MQ ← AC", "Where:"],
        )

    def test_sources_lists_and_commas_are_split(self) -> None:
        operation = only(definition(Sources="\n- `IO_READ_REQ`\n- A, B\nC"))

        self.assertEqual(operation["sources"], ["IO_READ_REQ", "A", "B", "C"])

    def test_list_markers_are_kept_outside_sources(self) -> None:
        operation = only(definition(Expression="\n- AC ← 0"))

        self.assertEqual(operation["expression"], ["- AC ← 0"])

    def test_documented_empty_sources(self) -> None:
        for value in ("none", "(None)", "\nNONE"):
            with self.subTest(value=value):
                self.assertEqual(
                    only(definition(Sources=value))["sources"], []
                )

    def test_none_among_other_sources_is_a_name(self) -> None:
        operation = only(definition(Sources="\nnone\nX"))

        self.assertEqual(operation["sources"], ["none", "X"])

    def test_source_traceability(self) -> None:
        operation = only(definition())

        self.assertEqual(
            operation["source"], {"path": PATH, "heading": "PC_INC", "line": 9}
        )
        self.assertEqual(
            operation["extraction_status"], "definition-validated"
        )


class ListTests(unittest.TestCase):
    def test_preconditions_and_constraints(self) -> None:
        extra = (
            "**Preconditions:** inline\n- `first`\n\n- second\n"
            "**Constraints:**\n- only\n"
        )

        result = extract(definition(extra=extra))
        operation = build_json_result(result)["micro_operations"][0]

        self.assertEqual(result.diagnostics, [])
        self.assertEqual(
            [
                (e["text"], e["source"]["line"])
                for e in operation["preconditions"]
            ],
            [("inline", 16), ("first", 17), ("second", 19)],
        )
        self.assertEqual(
            operation["constraints"],
            [{"text": "only", "source": {"path": PATH, "line": 21}}],
        )

    def test_repeated_list_labels_are_combined(self) -> None:
        extra = "**Constraints:**\n- a\n**Constraints:**\n- b\n"

        operation = only(definition(extra=extra))

        self.assertEqual(
            [e["text"] for e in operation["constraints"]], ["a", "b"]
        )

    def test_missing_lists_are_empty(self) -> None:
        operation = only(definition())

        self.assertEqual(
            (operation["preconditions"], operation["constraints"]), ([], [])
        )

    def test_other_text_is_reported_and_skipped(self) -> None:
        extra = "**Constraints:**\n- a\nprose\n```\n- fenced\n```\n- b\n"

        result = extract(definition(extra=extra))
        operation = build_json_result(result)["micro_operations"][0]

        self.assertEqual(
            [e["text"] for e in operation["constraints"]], ["a", "b"]
        )
        self.assertEqual(
            [(d.code, d.severity, d.line) for d in result.diagnostics],
            [
                ("UNEXPECTED_LIST_TEXT", "WARNING", 18),
                ("UNEXPECTED_LIST_TEXT", "WARNING", 19),
            ],
        )
        self.assertEqual(
            operation["extraction_status"], "definition-validated"
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationTests(unittest.TestCase):
    def assert_errors(self, result, expected: list[tuple[str, str]]) -> None:
        self.assertEqual(
            [(d.code, d.message) for d in result.diagnostics], expected
        )
        self.assertTrue(result.failed)
        self.assertEqual(
            result.micro_operations[-1].status, "definition-error"
        )

    def test_missing_attributes_are_reported(self) -> None:
        result = extract(definition(Description=None, Expression=None))

        self.assert_errors(
            result,
            [
                (
                    "MISSING_REQUIRED_ATTRIBUTE",
                    "Definition does not specify description.",
                ),
                (
                    "MISSING_REQUIRED_ATTRIBUTE",
                    "Definition does not specify expression.",
                ),
            ],
        )
        self.assertEqual(result.diagnostics[0].line, 9)

    def test_empty_attributes_are_reported(self) -> None:
        result = extract(definition(Target="", Sources=""))

        self.assert_errors(
            result,
            [
                ("EMPTY_REQUIRED_ATTRIBUTE", "Definition sources is empty."),
                ("EMPTY_REQUIRED_ATTRIBUTE", "Definition target is empty."),
            ],
        )

    def test_duplicate_attribute_is_reported_and_last_wins(self) -> None:
        result = extract(definition(extra="**Category:** Other\n"))

        self.assert_errors(
            result,
            [
                (
                    "DUPLICATE_ATTRIBUTE",
                    "Attribute 'category' occurs more than once.",
                )
            ],
        )
        self.assertEqual(result.diagnostics[0].line, 16)
        self.assertEqual(result.micro_operations[0].category, "Other")

    def test_duplicate_micro_operation_is_reported(self) -> None:
        result = extract(definition(), definition())

        self.assert_errors(
            result,
            [
                (
                    "DUPLICATE_MICRO_OPERATION",
                    "Micro-operation 'PC_INC' is defined more than once.",
                )
            ],
        )
        self.assertEqual(
            [item.status for item in result.micro_operations],
            ["definition-validated", "definition-error"],
        )

    def test_errors_in_one_definition_do_not_affect_others(self) -> None:
        result = extract(definition("A", Target=None), definition("B"))

        self.assertEqual(
            [item.status for item in result.micro_operations],
            ["definition-error", "definition-validated"],
        )

    def test_diagnostics_are_sorted(self) -> None:
        result = extract(
            definition("B", Target=None), definition("A", Category=None)
        )

        self.assertEqual(
            [(d.micro_operation, d.message) for d in result.diagnostics],
            [
                ("B", "Definition does not specify target."),
                ("A", "Definition does not specify category."),
            ],
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OutputTests(unittest.TestCase):
    def test_json_structure_and_key_order(self) -> None:
        result = extract(definition(Target=None))

        data = build_json_result(result)

        self.assertEqual(
            list(data),
            [
                "format_version",
                "extraction_stage",
                "source",
                "micro_operations",
                "diagnostics",
            ],
        )
        self.assertEqual(data["source"], {"path": PATH})
        self.assertEqual(
            list(data["micro_operations"][0]),
            [
                "name",
                "category",
                "description",
                "targets",
                "expression",
                "sources",
                "preconditions",
                "constraints",
                "source",
                "extraction_status",
            ],
        )
        self.assertEqual(
            data["diagnostics"],
            [
                {
                    "severity": "ERROR",
                    "code": "MISSING_REQUIRED_ATTRIBUTE",
                    "message": "Definition does not specify target.",
                    "source_path": PATH,
                    "line": 9,
                    "micro_operation": "PC_INC",
                }
            ],
        )

    def test_diagnostic_without_location_omits_it(self) -> None:
        data = build_json_result(extract_micro_operations("", PATH))

        self.assertEqual(
            data["diagnostics"],
            [
                {
                    "severity": "ERROR",
                    "code": "MISSING_DEFINITION_SECTION",
                    "message": (
                        "Section 'μop Definitions (Alphabetical)' was not "
                        "found."
                    ),
                    "source_path": PATH,
                }
            ],
        )

    def test_json_is_unescaped_with_one_trailing_newline(self) -> None:
        text = serialize_json(build_json_result(extract()))

        self.assertIn("PC ← PC + 1", text)
        self.assertTrue(text.endswith("}\n"))

    def test_report(self) -> None:
        report = build_report(
            [
                Diagnostic("WARNING", "W", "Warn.", PATH, 5, "A"),
                Diagnostic("ERROR", "E", "Err.", PATH),
            ],
            2,
            True,
        )

        self.assertEqual(
            report,
            "Micro-Operation Extraction Report\n"
            "=================================\n"
            "\n"
            "Micro-operations processed: 2\n"
            "JSON written: yes\n"
            "Information diagnostics: 0\n"
            "Warnings: 1\n"
            "Errors: 1\n"
            "Fatal errors: 0\n"
            "\n"
            "Diagnostics\n"
            "-----------\n"
            f"WARNING W [A] {PATH}:5: Warn.\n"
            f"ERROR E [-] {PATH}: Err.\n",
        )

    def test_empty_report_says_no_diagnostics(self) -> None:
        self.assertTrue(
            build_report([], 0, False).endswith("No diagnostics.\n")
        )


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

GOLDEN_DIRECTORY = Path(__file__).resolve().parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"

VALID_DOCUMENT = document(
    definition(
        "AC_MQ_SWAP",
        Category="\nRegister Transfer",
        Description="\nExchanges AC and MQ.",
        Target="\nAC, MQ",
        Expression="\nAC ← MQ\nMQ ← AC",
        Sources="\nAC, MQ",
    ),
    definition(
        "DB_READ_TO_AC",
        Category="I/O / External",
        Description="ORs the data bus into AC.",
        Target="AC",
        Expression="AC ← AC OR DB_input",
        Sources="AC, DB_input",
        extra=(
            "\n**Preconditions:**\n- A device is driving DB\n"
            "\n**Constraints:**\n- `AC` must not be written by another μop\n"
        ),
    ),
    definition(
        "IOT_TRANSFER_CAPTURE",
        Category="State Manipulation",
        Description="Captures the transfer direction.",
        Target="`IOT_TRANSFER`",
        Expression=(
            "\n\n```text\nif IO_READ_REQ = 1:\n    IOT_TRANSFER <- READ\n"
            "else:\n    IOT_TRANSFER <- NONE\n```"
        ),
        Sources="\n\n- `IO_READ_REQ`",
    ),
    definition(
        "PC_CLEAR",
        Description="Clears PC.",
        Expression="PC ← 0",
        Sources="(none)",
    ),
)

INVALID_DOCUMENT = document(
    definition("A", Category=None, Target=""),
    definition("A", extra="**Expression:** again\n**Constraints:**\nprose\n"),
)


class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.json_output = self.root / DEFAULT_JSON_OUTPUT
        self.report_output = self.root / DEFAULT_REPORT_OUTPUT

    def run_main(self, text: str | None) -> tuple[int, str]:
        if text is not None:
            source = self.root / SOURCE_PATH
            source.parent.mkdir(parents=True)
            source.write_text(text, encoding="utf-8")
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.root)])
        return exit_code, stdout.getvalue()

    def assert_outputs_match_golden(self, name: str) -> None:
        """Compare the JSON and report against ``golden/<name>/``.

        Run with ``UPDATE_GOLDEN=1`` to rewrite the expected files after an
        intended output change, then review the diff.
        """

        outputs = {
            "micro-operations.json": self.json_output,
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
        exit_code, stdout = self.run_main(VALID_DOCUMENT)

        self.assertEqual(exit_code, 0)
        self.assertIn("Status: SUCCEEDED", stdout)
        self.assertIn("Micro-operations: 4", stdout)
        self.assert_outputs_match_golden("valid")

    def test_invalid_outputs_match_golden(self) -> None:
        exit_code, stdout = self.run_main(INVALID_DOCUMENT)

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "ERROR DUPLICATE_MICRO_OPERATION [A]\n"
            f"  Source: {SOURCE_PATH.as_posix()}:18\n",
            stdout,
        )
        self.assertNotIn("UNEXPECTED_LIST_TEXT", stdout.split("Failure")[1])
        self.assert_outputs_match_golden("invalid")

    def test_unreadable_source_is_fatal(self) -> None:
        exit_code, stdout = self.run_main(None)

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.json_output.exists())
        report = self.report_output.read_text(encoding="utf-8")
        self.assertIn("JSON written: no", report)
        self.assertIn(
            f"FATAL EXTRACTION_FAILURE [-] {SOURCE_PATH.as_posix()}: "
            "Source file does not exist",
            report,
        )
        self.assertIn("Micro-operations: 0", stdout)

    def test_outputs_are_deterministic(self) -> None:
        self.run_main(VALID_DOCUMENT)
        first = self.json_output.read_bytes(), self.report_output.read_bytes()

        with redirect_stdout(io.StringIO()):
            main(["--repo-root", str(self.root)])

        self.assertEqual(
            (self.json_output.read_bytes(), self.report_output.read_bytes()),
            first,
        )
        self.assertNotIn(b"\r\n", first[0])


if __name__ == "__main__":
    unittest.main()
