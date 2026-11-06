"""Tests for the control-output extractor."""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extract_control_outputs import (  # noqa: E402
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    ENCODING_LABELS,
    SOURCE_DIRECTORY,
    SOURCE_PATHS,
    ConstraintEntry,
    DefinitionBlock,
    EncodingEntry,
    IndexEntry,
    MicroOperationUse,
    SignalDefinition,
    SourceDocument,
    extract_definition_blocks,
    extract_signal,
    find_labeled_section,
    find_signal_in_heading,
    load_source_documents,
    main,
    match_definition_blocks,
    normalize_bit_width,
    normalize_default_value,
    normalize_explicit_value_required,
    normalize_markdown_text,
    output_attributes,
    parse_arguments,
    parse_bit_width,
    parse_definition_attributes,
    parse_definition_constraints,
    parse_definition_encodings,
    parse_definition_micro_operation_uses,
    parse_encoding_line,
    parse_index,
    parse_micro_operation_use,
    parse_octal,
    remove_section_number,
    resolve_tool_paths,
    signal_to_dict,
    validate_category_requirements,
    validate_control_word_attributes,
    validate_encoding_widths,
    validate_mnemonic,
    validate_required_attributes,
    validate_source_paths,
    write_text,
)

MICRO_OPS = "../../03-microarchitecture/02-micro-operations.md"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_document(
    text: str,
    relative_path: str = "docs/doc.md",
) -> SourceDocument:
    return SourceDocument(
        path=Path(relative_path), relative_path=relative_path, text=text
    )


def make_entry(
    name: str = "AC_SRC",
    category: str = "Select Signals",
    line: int = 10,
) -> IndexEntry:
    return IndexEntry(
        name=name, category=category, source_path="docs/index.md", line=line
    )


def make_block(
    *lines: str,
    heading: str = "AC_SRC",
    source_path: str = "docs/definitions.md",
    start_line: int = 20,
) -> DefinitionBlock:
    """Build a block whose body lines follow its heading at ``start_line``."""

    return DefinitionBlock(
        heading=heading,
        source_path=source_path,
        start_line=start_line,
        lines=tuple(
            (start_line + offset, line)
            for offset, line in enumerate(lines, start=1)
        ),
    )


def make_signal(
    name: str = "AC_SRC",
    category: str = "Select Signals",
    *,
    attributes: dict[str, str] | None = None,
    bit_width: int | None = 3,
    encodings: tuple[EncodingEntry, ...] = (),
) -> SignalDefinition:
    return SignalDefinition(
        entry=make_entry(name, category),
        block=make_block(heading=name),
        attributes={} if attributes is None else attributes,
        bit_width=bit_width,
        encodings=encodings,
        constraints=(),
        micro_operation_uses=(),
    )


def encoding(value: str, line: int = 30) -> EncodingEntry:
    return EncodingEntry(value=value, meaning="meaning", line=line)


def control_word_attributes(**overrides: str) -> dict[str, str]:
    """Valid control-word attributes for a conditionally assigned field."""

    attributes = {
        "default_value": "0",
        "explicit_value_required": "Conditionally",
        "value_required_when": "AC_LOAD=1",
    }
    attributes.update(overrides)
    return attributes


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


# ---------------------------------------------------------------------------
# Command line, paths, and loading
# ---------------------------------------------------------------------------


class ArgumentParsingTests(unittest.TestCase):
    def test_repo_root_is_required(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parse_arguments([])

    def test_default_output_paths_are_used(self) -> None:
        arguments = parse_arguments(["--repo-root", "."])

        self.assertEqual(arguments.json_output, DEFAULT_JSON_OUTPUT)
        self.assertEqual(arguments.report_output, DEFAULT_REPORT_OUTPUT)


class PathResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.repo_root = Path(temporary_directory.name).resolve()

    def test_paths_are_resolved_from_repo_root(self) -> None:
        paths = resolve_tool_paths(
            parse_arguments(["--repo-root", str(self.repo_root)])
        )

        self.assertEqual(paths.repo_root, self.repo_root)
        self.assertEqual(
            paths.source_paths,
            tuple(self.repo_root / path for path in SOURCE_PATHS),
        )
        self.assertEqual(
            paths.json_output, self.repo_root / DEFAULT_JSON_OUTPUT
        )

    def test_absolute_output_path_is_preserved(self) -> None:
        output = self.repo_root / "elsewhere" / "outputs.json"

        paths = resolve_tool_paths(
            parse_arguments(
                [
                    "--repo-root",
                    str(self.repo_root),
                    "--json-output",
                    str(output),
                ]
            )
        )

        self.assertEqual(paths.json_output, output)


class SourceLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name).resolve()

    def test_missing_repository_root_is_reported(self) -> None:
        with self.assertRaisesRegex(
            FileNotFoundError, "Repository root does not exist"
        ):
            validate_source_paths(self.root / "missing", ())

    def test_missing_source_files_are_reported(self) -> None:
        missing = self.root / "missing.md"

        with self.assertRaisesRegex(
            FileNotFoundError, "source files are missing"
        ) as context:
            validate_source_paths(self.root, (missing,))

        self.assertIn(str(missing), str(context.exception))

    def test_documents_are_loaded_in_supplied_order(self) -> None:
        first = self.root / "docs" / "first.md"
        second = self.root / "second.md"
        first.parent.mkdir()
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")

        documents = load_source_documents((second, first), self.root)

        self.assertEqual(
            [(item.relative_path, item.text) for item in documents],
            [("second.md", "second"), ("docs/first.md", "first")],
        )

    def test_invalid_utf8_is_rejected(self) -> None:
        source = self.root / "source.md"
        source.write_bytes(b"\xff\xfe\xfa")

        with self.assertRaisesRegex(ValueError, "not valid UTF-8"):
            load_source_documents((source,), self.root)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


class MarkdownHelperTests(unittest.TestCase):
    def test_section_number_is_removed(self) -> None:
        self.assertEqual(remove_section_number("4.1 MS_NEXT"), "MS_NEXT")
        self.assertEqual(
            remove_section_number("5. Signal Definitions"),
            "Signal Definitions",
        )
        self.assertEqual(remove_section_number("AC_LOAD"), "AC_LOAD")

    def test_markdown_identifiers_are_normalized(self) -> None:
        self.assertEqual(
            normalize_markdown_text(r" `IOT\_TRANSFER\_VAL` "),
            "IOT_TRANSFER_VAL",
        )
        self.assertEqual(normalize_markdown_text(r"IOP\[2:0\]"), "IOP[2:0]")

    def test_labeled_section_runs_to_unrelated_label(self) -> None:
        block = make_block(
            "**Purpose:** before",
            "**Encoding:** 0 -> off",
            "1 -> on",
            "**Value Encoding:**",
            "2 -> also",
            "**Constraints:**",
            "**Encoding:**",
            "3 -> never read",
        )

        section = find_labeled_section(block, ENCODING_LABELS)

        self.assertEqual(
            [(item.line, item.text, item.is_label) for item in section],
            [
                (22, "0 -> off", True),
                (23, "1 -> on", False),
                (24, "", True),
                (25, "2 -> also", False),
            ],
        )

    def test_missing_label_gives_empty_section(self) -> None:
        block = make_block("**Purpose:** text")

        self.assertEqual(find_labeled_section(block, ENCODING_LABELS), [])


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


class IndexParsingTests(unittest.TestCase):
    def test_entries_take_category_from_level_three_heading(self) -> None:
        document = make_document(
            "## 3. Microarchitectural Control Signals\n"
            "- [Overview](./01-microarchitectural-control-signals.md)\n"
            "- [AC\\_LOAD]"
            "(./01-microarchitectural-control-signals.md#ac_load)  \n"
            "### 3.1 Enable Signals\n"
            "- [PC\\_INC](./01-microarchitectural-control-signals.md#pc_inc)\n"
            "#### Notes\n"
            "### 4.1 Memory Interface\n"
            "- [/RD](./02-architectural-control-signals.md#41-read-rd)\n"
            "- [Elsewhere](./other.md#anchor)\n",
            relative_path="docs/index.md",
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(
            [(entry.name, entry.category, entry.line) for entry in entries],
            [
                ("AC_LOAD", "uncategorized", 3),
                ("PC_INC", "Enable Signals", 5),
                ("/RD", "Memory Interface", 8),
            ],
        )
        self.assertEqual(entries[0].source_path, "docs/index.md")
        self.assertEqual(diagnostics, [])

    def test_bus_names_with_brackets_are_extracted(self) -> None:
        document = make_document(
            "- [IOA\\[5:0\\]](./02-architectural-control-signals.md#ioa)\n"
            "- [IOP[2:0]](./02-architectural-control-signals.md#iop )\n"
        )

        entries, _ = parse_index(document)

        self.assertEqual(
            [entry.name for entry in entries], ["IOA[5:0]", "IOP[2:0]"]
        )

    def test_duplicate_index_entry_is_reported(self) -> None:
        document = make_document(
            "- [AC_LOAD](./01-microarchitectural-control-signals.md#a)\n"
            "- [AC\\_LOAD](./01-microarchitectural-control-signals.md#b)\n"
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(len(entries), 1)
        self.assertEqual(codes(diagnostics), ["DUPLICATE_INDEX_ENTRY"])
        self.assertEqual(diagnostics[0].line, 2)
        self.assertIn("line 1", diagnostics[0].message)

    def test_index_without_entries_is_reported(self) -> None:
        _, diagnostics = parse_index(make_document("# Index\n"))

        self.assertEqual(codes(diagnostics), ["NO_INDEX_ENTRIES"])


# ---------------------------------------------------------------------------
# Definition blocks
# ---------------------------------------------------------------------------


class DefinitionBlockTests(unittest.TestCase):
    def test_signal_definitions_section_is_split_into_blocks(self) -> None:
        document = make_document(
            "## 4. Global Properties\n"
            "### 4.1 Not A Definition\n"
            "## 5. Signal Definitions\n"
            "### 5.1 Accumulator Load (AC\\_LOAD)\n"
            "**Bit Width:** 1\n"
            "#### Detail\n"
            "### `PC_LOAD`\n"
            "**Bit Width:** 12\n"
            "## 6. Interaction Rules\n"
            "### 6.1 Not A Definition\n",
            relative_path="docs/signals.md",
        )

        blocks = extract_definition_blocks(document)

        self.assertEqual(
            [(block.heading, block.start_line) for block in blocks],
            [("Accumulator Load (AC_LOAD)", 4), ("PC_LOAD", 7)],
        )
        self.assertEqual(
            blocks[0].lines, ((5, "**Bit Width:** 1"), (6, "#### Detail"))
        )
        self.assertEqual(blocks[1].lines, ((8, "**Bit Width:** 12"),))
        self.assertEqual(blocks[0].source_path, "docs/signals.md")

    def test_document_without_definitions_section_has_no_blocks(self) -> None:
        document = make_document("## Purpose\n### AC_LOAD\n")

        self.assertEqual(extract_definition_blocks(document), [])

    def test_heading_names_signal_exactly_or_in_final_parentheses(
        self,
    ) -> None:
        names = {"AC_LOAD", "/RD"}

        self.assertEqual(find_signal_in_heading("AC_LOAD", names), "AC_LOAD")
        self.assertEqual(
            find_signal_in_heading("Memory Read ( /RD )", names), "/RD"
        )
        self.assertIsNone(
            find_signal_in_heading("Behavior of AC_LOAD in FETCH", names)
        )
        self.assertIsNone(find_signal_in_heading("Unknown (OTHER)", names))

    def test_blocks_are_matched_to_index_entries(self) -> None:
        block = make_block(heading="Accumulator Load (AC_LOAD)")

        definitions, diagnostics = match_definition_blocks(
            [make_entry("AC_LOAD")], [block]
        )

        self.assertEqual(definitions, {"AC_LOAD": block})
        self.assertEqual(diagnostics, [])

    def test_missing_definition_is_reported_at_index_entry(self) -> None:
        definitions, diagnostics = match_definition_blocks(
            [make_entry("AC_LOAD", line=12)], []
        )

        self.assertEqual(definitions, {})
        self.assertEqual(codes(diagnostics), ["MISSING_DEFINITION"])
        self.assertEqual(
            (diagnostics[0].source_path, diagnostics[0].line),
            ("docs/index.md", 12),
        )

    def test_duplicate_definition_keeps_first_block(self) -> None:
        first = make_block(heading="AC_LOAD", start_line=20)
        second = make_block(heading="Load (AC_LOAD)", start_line=40)

        definitions, diagnostics = match_definition_blocks(
            [make_entry("AC_LOAD")], [first, second]
        )

        self.assertIs(definitions["AC_LOAD"], first)
        self.assertEqual(codes(diagnostics), ["DUPLICATE_DEFINITION"])
        self.assertEqual(diagnostics[0].line, 40)
        self.assertIn("docs/definitions.md:20", diagnostics[0].message)

    def test_unindexed_definition_is_a_warning(self) -> None:
        _, diagnostics = match_definition_blocks(
            [], [make_block(heading="Unknown (UNKNOWN)")]
        )

        self.assertEqual(codes(diagnostics), ["UNINDEXED_DEFINITION"])
        self.assertEqual(diagnostics[0].severity, "WARNING")
        self.assertIsNone(diagnostics[0].signal_name)


# ---------------------------------------------------------------------------
# Scalar attributes, bit width, and value normalization
# ---------------------------------------------------------------------------


class AttributeTests(unittest.TestCase):
    def test_recognized_attributes_are_extracted_in_source_order(self) -> None:
        block = make_block(
            "**Mnemonic:** `AC\\_SRC`  ",
            "**Name** Accumulator Source",
            "**Class**: Select",
            "**Bit Width:** 3",
            "**Default Value:** 0",
            "**Timing:** not an attribute",
            "Prose mentioning **Purpose:** mid-line.",
            "**Purpose:** Selects the AC input.",
        )

        attributes, diagnostics = parse_definition_attributes("AC_SRC", block)

        self.assertEqual(
            list(attributes.items()),
            [
                ("mnemonic", "AC_SRC"),
                ("display_name", "Accumulator Source"),
                ("signal_class", "Select"),
                ("bit_width", "3"),
                ("default_value", "0"),
                ("purpose", "Selects the AC input."),
            ],
        )
        self.assertEqual(diagnostics, [])

    def test_label_with_value_on_next_line_is_not_an_attribute(self) -> None:
        block = make_block("**Name**  ", "IOA[5:0]")

        attributes, _ = parse_definition_attributes("IOA[5:0]", block)

        self.assertEqual(attributes, {})

    def test_duplicate_attribute_keeps_first_value(self) -> None:
        block = make_block("**Bit Width:** 3", "**Width** 4 bits")

        attributes, diagnostics = parse_definition_attributes("AC_SRC", block)

        self.assertEqual(attributes, {"bit_width": "3"})
        self.assertEqual(codes(diagnostics), ["DUPLICATE_ATTRIBUTE"])
        self.assertEqual(diagnostics[0].line, 22)


class BitWidthTests(unittest.TestCase):
    def test_bit_width_formats_are_parsed(self) -> None:
        for text, expected in [
            ("1", 1),
            ("1 bit", 1),
            ("3 Bits", 3),
            (" 12 bits ", 12),
            ("0", None),
            ("one", None),
            ("3 bytes", None),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_bit_width(text), expected)

    def test_documented_width_is_normalized(self) -> None:
        bit_width, diagnostics = normalize_bit_width(
            "MS_NEXT", make_block(), {"bit_width": "3 bits"}
        )

        self.assertEqual((bit_width, diagnostics), (3, []))

    def test_missing_width_is_left_to_required_attribute_check(self) -> None:
        self.assertEqual(
            normalize_bit_width("X", make_block(), {}), (None, [])
        )

    def test_invalid_width_is_reported(self) -> None:
        bit_width, diagnostics = normalize_bit_width(
            "X", make_block(), {"bit_width": "wide"}
        )

        self.assertIsNone(bit_width)
        self.assertEqual(codes(diagnostics), ["INVALID_BIT_WIDTH"])


class ValueNormalizationTests(unittest.TestCase):
    def test_octal_values_are_parsed(self) -> None:
        self.assertEqual(parse_octal("17"), 15)
        self.assertEqual(parse_octal("07"), 7)

        for text in ("8", "1A", "", "-1"):
            with self.subTest(text=text):
                self.assertIsNone(parse_octal(text))

    def test_explicit_value_requirement_is_normalized(self) -> None:
        self.assertEqual(normalize_explicit_value_required(" yes "), "Yes")
        self.assertEqual(normalize_explicit_value_required("NO"), "No")
        self.assertEqual(
            normalize_explicit_value_required("conditionally"),
            "Conditionally",
        )
        self.assertIsNone(normalize_explicit_value_required("sometimes"))

    def test_default_value_must_be_na_or_fitting_octal(self) -> None:
        self.assertEqual(normalize_default_value("n/a", 12), "N/A")
        self.assertEqual(normalize_default_value("17", 4), "17")
        self.assertIsNone(normalize_default_value("20", 4))
        self.assertIsNone(normalize_default_value("9", 4))


# ---------------------------------------------------------------------------
# Encodings
# ---------------------------------------------------------------------------


class EncodingTests(unittest.TestCase):
    def test_encoding_line_formats_are_parsed(self) -> None:
        for text, expected in [
            ("0 -> no load", ("0", "no load")),
            ("- 1: load", ("1", "load")),
            ("2 → `EXECUTE`", ("2", "EXECUTE")),
            ("3 = invalid", ("3", "invalid")),
            ("no separator", None),
            ("4 -> ``", None),
            ("0 - 7 (octal)", None),
        ]:
            with self.subTest(text=text):
                self.assertEqual(parse_encoding_line(text), expected)

    def test_encodings_are_extracted_with_source_lines(self) -> None:
        block = make_block(
            "**Encoding:** 0 → IDB",
            "```",
            "1 → DB",
            "",
            "- 2 → MQ",
            "```",
            "**Constraints:**",
            "3 → not an encoding",
        )

        encodings, diagnostics = parse_definition_encodings("AC_SRC", block)

        self.assertEqual(
            encodings,
            [
                EncodingEntry("0", "IDB", 21),
                EncodingEntry("1", "DB", 23),
                EncodingEntry("2", "MQ", 25),
            ],
        )
        self.assertEqual(diagnostics, [])

    def test_value_descriptions_are_not_malformed(self) -> None:
        block = make_block(
            "**Value Encoding:**",
            "0-7777 (octal)",
            "external bus value",
            "WHERE:",
            "IF_DF[2:0]=DF and",
        )

        encodings, diagnostics = parse_definition_encodings("X", block)

        self.assertEqual((encodings, diagnostics), ([], []))

    def test_malformed_encodings_are_warnings(self) -> None:
        block = make_block("**Encoding:** none", "unparsable line")

        _, diagnostics = parse_definition_encodings("X", block)

        self.assertEqual(
            [(item.code, item.severity, item.line) for item in diagnostics],
            [
                ("MALFORMED_ENCODING", "WARNING", 21),
                ("MALFORMED_ENCODING", "WARNING", 22),
            ],
        )

    def test_heading_or_bold_text_ends_encodings(self) -> None:
        for terminator in ("#### Notes", "**Bold text without label"):
            with self.subTest(terminator=terminator):
                block = make_block(
                    "**Encoding:**", "0 -> off", terminator, "1 -> on"
                )

                encodings, diagnostics = parse_definition_encodings("X", block)

                self.assertEqual([item.value for item in encodings], ["0"])
                self.assertEqual(diagnostics, [])

    def test_duplicate_encoding_value_is_reported(self) -> None:
        block = make_block("**Encoding:**", "0 -> off", "0 -> inactive")

        encodings, diagnostics = parse_definition_encodings("X", block)

        self.assertEqual(len(encodings), 2)
        self.assertEqual(codes(diagnostics), ["DUPLICATE_ENCODING_VALUE"])
        self.assertEqual(diagnostics[0].line, 23)
        self.assertIn("line 22", diagnostics[0].message)


# ---------------------------------------------------------------------------
# Constraints and micro-operation uses
# ---------------------------------------------------------------------------


class ConstraintTests(unittest.TestCase):
    def test_constraint_list_items_are_extracted(self) -> None:
        block = make_block(
            "**Constraints:** - label text is not a list item",
            "",
            "- Must not be asserted with `PC\\_INC`.",
            "- Field merges:",
            "  - IF → AC[5:3]",
            "Prose is ignored.",
            "**Used by μops:**",
            "- AC_CLEAR = 0",
        )

        self.assertEqual(
            parse_definition_constraints(block),
            [
                ConstraintEntry("Must not be asserted with PC_INC.", 23),
                ConstraintEntry("Field merges:", 24),
                ConstraintEntry("IF → AC[5:3]", 25),
            ],
        )

    def test_definition_without_constraints_has_none(self) -> None:
        self.assertEqual(parse_definition_constraints(make_block("- x")), [])


class MicroOperationUseTests(unittest.TestCase):
    def test_use_forms_are_parsed(self) -> None:
        for text, expected in [
            (f"[AC\\_CLEAR]({MICRO_OPS}#ac_clear) = 0", ("AC_CLEAR", "0")),
            (f"[DF_TO_AC]({MICRO_OPS}#df_to_ac)", ("DF_TO_AC", None)),
            ("RUN_SET = 1", ("RUN_SET", "1")),
            ("external device", ("external device", None)),
        ]:
            with self.subTest(text=text):
                use = parse_micro_operation_use(text, 30)
                self.assertEqual((use.micro_operation, use.value), expected)

    def test_text_with_spaced_value_is_rejected(self) -> None:
        self.assertIsNone(parse_micro_operation_use("A = 1 or 2", 30))

    def test_used_by_list_items_are_extracted(self) -> None:
        block = make_block(
            "**Used by uops:**",
            f"- [AC_CLEAR]({MICRO_OPS}#ac_clear) = 0",
            "- A = 1 or 2",
            "Prose is ignored.",
            "- RUN_SET",
        )

        self.assertEqual(
            parse_definition_micro_operation_uses(block),
            [
                MicroOperationUse("AC_CLEAR", "0", 22),
                MicroOperationUse("RUN_SET", None, 25),
            ],
        )


class SignalExtractionTests(unittest.TestCase):
    def test_all_properties_are_extracted(self) -> None:
        block = make_block(
            "**Bit Width:** 3",
            "**Bit Width:** 4",
            "**Encoding:**",
            "0 → IDB",
            "nonsense",
            "**Constraints:**",
            "- Requires a valid source.",
            "**Used by μops:**",
            "- AC_CLEAR = 0",
        )

        signal, diagnostics = extract_signal(make_entry(), block)

        self.assertEqual(signal.attributes, {"bit_width": "3"})
        self.assertEqual(signal.bit_width, 3)
        self.assertEqual([item.value for item in signal.encodings], ["0"])
        self.assertEqual(len(signal.constraints), 1)
        self.assertEqual(len(signal.micro_operation_uses), 1)
        self.assertEqual(
            codes(diagnostics), ["DUPLICATE_ATTRIBUTE", "MALFORMED_ENCODING"]
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class RequiredAttributeTests(unittest.TestCase):
    def test_missing_width_and_description_are_warnings(self) -> None:
        diagnostics = validate_required_attributes(make_signal())

        self.assertEqual(
            [(item.code, item.severity) for item in diagnostics],
            [
                ("MISSING_BIT_WIDTH", "WARNING"),
                ("MISSING_DESCRIPTION", "WARNING"),
            ],
        )

    def test_purpose_or_description_is_accepted(self) -> None:
        for label in ("purpose", "description"):
            with self.subTest(label=label):
                signal = make_signal(
                    attributes={"bit_width": "3", label: "text"}
                )
                self.assertEqual(validate_required_attributes(signal), [])


class MnemonicTests(unittest.TestCase):
    def test_mnemonic_must_match_indexed_name(self) -> None:
        for mnemonic, expected in [
            (None, []),
            ("AC_SRC", []),
            ("PC_SRC", ["MNEMONIC_MISMATCH"]),
        ]:
            with self.subTest(mnemonic=mnemonic):
                attributes = {} if mnemonic is None else {"mnemonic": mnemonic}
                signal = make_signal(attributes=attributes)
                self.assertEqual(codes(validate_mnemonic(signal)), expected)


class ControlWordAttributeTests(unittest.TestCase):
    def validate(self, bit_width: int | None = 3, **overrides: str):
        attributes = control_word_attributes(**overrides)
        attributes = {
            key: value for key, value in attributes.items() if value != "-"
        }
        return codes(
            validate_control_word_attributes(
                make_signal(attributes=attributes, bit_width=bit_width)
            )
        )

    def test_valid_attributes_are_accepted(self) -> None:
        self.assertEqual(self.validate(), [])
        self.assertEqual(
            self.validate(
                bit_width=12,
                default_value="N/A",
                explicit_value_required="No",
                value_required_when="AC_LOAD=1 AND AC_SRC=6",
            ),
            [],
        )

    def test_missing_attributes_are_reported(self) -> None:
        self.assertEqual(
            self.validate(
                default_value="-",
                explicit_value_required="-",
                value_required_when="-",
            ),
            [
                "MISSING_DEFAULT_VALUE",
                "MISSING_EXPLICIT_VALUE_REQUIRED",
                "MISSING_VALUE_REQUIRED_WHEN",
            ],
        )

    def test_invalid_values_are_reported(self) -> None:
        self.assertEqual(
            self.validate(default_value="10"), ["INVALID_DEFAULT_VALUE"]
        )
        self.assertEqual(
            self.validate(explicit_value_required="Maybe"),
            ["INVALID_EXPLICIT_VALUE_REQUIRED"],
        )
        self.assertEqual(
            self.validate(value_required_when=""),
            ["EMPTY_VALUE_REQUIRED_WHEN"],
        )

    def test_default_value_is_not_checked_without_width(self) -> None:
        self.assertEqual(self.validate(bit_width=None, default_value="99"), [])

    def test_conditional_requirement_needs_a_condition(self) -> None:
        for condition in ("Always", "n/a"):
            with self.subTest(condition=condition):
                self.assertEqual(
                    self.validate(value_required_when=condition),
                    ["INVALID_CONDITIONAL_REQUIREMENT"],
                )

    def test_explicit_field_needs_encoded_default(self) -> None:
        for requirement in ("Yes", "Conditionally"):
            with self.subTest(requirement=requirement):
                self.assertEqual(
                    self.validate(
                        default_value="N/A",
                        explicit_value_required=requirement,
                        value_required_when="TS=4",
                    ),
                    ["EXPLICIT_FIELD_HAS_NO_DEFAULT"],
                )

    def test_explicit_field_default_is_checked_without_condition(
        self,
    ) -> None:
        self.assertEqual(
            self.validate(
                default_value="N/A",
                explicit_value_required="Yes",
                value_required_when="-",
            ),
            ["MISSING_VALUE_REQUIRED_WHEN", "EXPLICIT_FIELD_HAS_NO_DEFAULT"],
        )


class EncodingWidthTests(unittest.TestCase):
    def test_encodings_must_be_octal_and_fit_width(self) -> None:
        signal = make_signal(
            bit_width=4,
            encodings=(encoding("17"), encoding("20"), encoding("8")),
        )

        self.assertEqual(
            codes(validate_encoding_widths(signal)),
            ["ENCODING_EXCEEDS_BIT_WIDTH", "INVALID_OCTAL_ENCODING"],
        )

    def test_unknown_width_skips_encoding_checks(self) -> None:
        signal = make_signal(bit_width=None, encodings=(encoding("X"),))

        self.assertEqual(validate_encoding_widths(signal), [])


class CategoryRequirementTests(unittest.TestCase):
    def test_enable_signal_needs_one_bit_and_encodings(self) -> None:
        for bit_width in (2, None):
            with self.subTest(bit_width=bit_width):
                signal = make_signal(
                    "AC_LOAD", "Enable Signals", bit_width=bit_width
                )
                self.assertEqual(
                    codes(validate_category_requirements(signal)),
                    ["INVALID_ENABLE_WIDTH", "MISSING_ENUMERATED_ENCODINGS"],
                )

    def test_encodings_are_required_by_category(self) -> None:
        for category, expected in [
            ("Select Signals", ["MISSING_ENUMERATED_ENCODINGS"]),
            ("Control Flow", ["MISSING_ENUMERATED_ENCODINGS"]),
            ("Data Value Signals", []),
            ("Memory Interface", []),
        ]:
            with self.subTest(category=category):
                signal = make_signal(category=category)
                self.assertEqual(
                    codes(validate_category_requirements(signal)), expected
                )


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class JsonOutputTests(unittest.TestCase):
    def test_output_attributes_are_normalized(self) -> None:
        signal = make_signal(
            attributes={
                "bit_width": "3",
                "explicit_value_required": "yes",
                "default_value": "n/a",
                "purpose": "text",
            }
        )

        self.assertEqual(
            list(output_attributes(signal).items()),
            [
                ("explicit_value_required", "Yes"),
                ("default_value", "N/A"),
                ("purpose", "text"),
            ],
        )

    def test_invalid_normalized_attributes_become_null(self) -> None:
        signal = make_signal(
            attributes={"explicit_value_required": "x", "default_value": "9"}
        )

        self.assertEqual(
            output_attributes(signal),
            {"explicit_value_required": None, "default_value": None},
        )

    def test_default_value_is_kept_as_written_without_width(self) -> None:
        signal = make_signal(
            attributes={"default_value": "n/a"}, bit_width=None
        )

        self.assertEqual(output_attributes(signal), {"default_value": "n/a"})

    def test_missing_definition_has_null_definition(self) -> None:
        self.assertEqual(
            signal_to_dict(make_entry(), None),
            {
                "name": "AC_SRC",
                "category": "Select Signals",
                "definition": None,
                "source": {"path": "docs/index.md", "line": 10},
                "extraction_status": "definition-missing",
            },
        )

    def test_text_is_written_with_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "nested" / "out.txt"

            write_text(output_path, "line\n")

            self.assertEqual(output_path.read_bytes(), b"line\n")


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

FIXTURE_DOCUMENTS = {
    "00-index.md": """\
# Control Output Signal Index

## 3. Microarchitectural Control Signals

- [Microarchitectural Control Signals](./01-microarchitectural-control-signals.md)

### 3.1 Enable Signals

- [AC\\_LOAD](./01-microarchitectural-control-signals.md#ac_load)

### 3.2 Select Signals

- [AC\\_SRC](./01-microarchitectural-control-signals.md#ac_src)

### 3.3 Data Value Signals

- [PC\\_VAL](./01-microarchitectural-control-signals.md#pc_val)

## 4. Architectural Control Signals

### 4.1 Memory Interface

- [/RD](./02-architectural-control-signals.md#41-memory-read-rd)

## 5. Sequencing Control Signals

### 5.1 Control Flow

- [MS\\_NEXT](./03-sequencing-control-signals.md#41-next-major-state-ms_next)
""",
    "01-microarchitectural-control-signals.md": """\
# Microarchitectural Control Signals

## 4. Signal Index

### 4.1 Enable Signals

## 5. Signal Definitions

### AC_LOAD

**Mnemonic:** AC_LOAD
**Name:** Accumulator Load
**Class:** Enable
**Bit Width:** 1
**Default Value:** 0
**Explicit Value Required:** Yes
**Value Required When:** Always

**Purpose:** Loads AC.

**Encoding:**
```
0 → no load
1 → load
```

**Used by μops:**
- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear) = 1

---

### AC_SRC

**Mnemonic:** AC_SRC
**Bit Width:** 3
**Default Value:** 0
**Explicit Value Required:** Conditionally
**Value Required When:** AC_LOAD=1

**Purpose:** Selects the AC input.

**Encoding:**
```
0 → IDB
1 → DB
7 → reserved
```

**Constraints:**
- Field-merge encodings preserve other AC bits:
  - IF → AC[5:3]
- MQ replaces AC in full.

**Used by μops:**
- [AC_CLEAR](../../03-microarchitecture/02-micro-operations.md#ac_clear) = 0
- [DB_READ_TO_AC](../../03-microarchitecture/02-micro-operations.md#db_read_to_ac) = 1

---

### PC_VAL

**Mnemonic:** PC_VAL
**Bit Width:** 12
**Default Value:** N/A
**Explicit Value Required:** No
**Value Required When:** PC_LOAD=1 AND PC_SRC=2

**Purpose:** Supplies a PC value.

**Encoding:**
```
0-7777 (octal)
```

## 6. Interaction Rules

### 6.1 Exclusivity
""",
    "02-architectural-control-signals.md": """\
# Architectural Control Signals

## 4. Signal Definitions

### 4.1 Memory Read (/RD)

**Name**
/RD

**Polarity**
Active-low

**Bit Width:** 1

**Default Value:** N/A
**Explicit Value Required:** No
**Value Required When:** Memory read cycle

**Description:** Requests a memory read.

**Constraints:**

- Must not be asserted with `/WR`.
""",
    "03-sequencing-control-signals.md": """\
# Sequencing Control Signals

## 4. Signal Definitions

### 4.1 Next Major State (MS_NEXT)

**Name**
MS_NEXT

**Width** 3 bits

**Default Value:** 0
**Explicit Value Required:** Yes
**Value Required When:** TS=4

**Description:** Specifies the next Major State.

**Value Encoding:**
```text
0 → FETCH
1 → DEFER
2 → EXECUTE
```

**Behavior**

- committed at TP4
""",
}


GOLDEN_DIRECTORY = Path(__file__).resolve().parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"


class EndToEndTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.repo_root = Path(temporary_directory.name)

        for source_path in SOURCE_PATHS:
            path = self.repo_root / source_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(FIXTURE_DOCUMENTS[path.name], encoding="utf-8")

    def run_main(self) -> tuple[int, dict, str, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.repo_root)])

        json_path = self.repo_root / DEFAULT_JSON_OUTPUT
        report_path = self.repo_root / DEFAULT_REPORT_OUTPUT
        return (
            exit_code,
            json.loads(json_path.read_text(encoding="utf-8")),
            report_path.read_text(encoding="utf-8"),
            stdout.getvalue(),
        )

    def edit_source(self, file_name: str, old: str, new: str) -> None:
        path = self.repo_root / SOURCE_DIRECTORY / file_name
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def assert_outputs_match_golden(self, name: str) -> None:
        """Compare the full JSON and report against ``golden/<name>/``.

        Run with ``UPDATE_GOLDEN=1`` to rewrite the expected files after an
        intentional output change, then review the diff.
        """

        self.run_main()
        outputs = {
            "control-outputs.json": self.repo_root / DEFAULT_JSON_OUTPUT,
            "extraction-report.txt": self.repo_root / DEFAULT_REPORT_OUTPUT,
        }

        for file_name, output_path in outputs.items():
            golden_path = GOLDEN_DIRECTORY / name / file_name
            actual = output_path.read_text(encoding="utf-8")

            if UPDATE_GOLDEN:
                golden_path.parent.mkdir(parents=True, exist_ok=True)
                golden_path.write_text(actual, encoding="utf-8", newline="\n")
                continue

            with self.subTest(file=file_name):
                self.assertEqual(
                    actual, golden_path.read_text(encoding="utf-8")
                )

    def test_valid_documents_extract_cleanly(self) -> None:
        exit_code, result, report, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(
            [
                (signal["name"], signal["category"])
                for signal in result["signals"]
            ],
            [
                ("AC_LOAD", "Enable Signals"),
                ("AC_SRC", "Select Signals"),
                ("PC_VAL", "Data Value Signals"),
                ("/RD", "Memory Interface"),
                ("MS_NEXT", "Control Flow"),
            ],
        )
        self.assertIn("Indexed signals: 5", report)
        self.assertIn("Status: SUCCEEDED", stdout)

    def test_valid_outputs_match_golden(self) -> None:
        self.assert_outputs_match_golden("valid")

    def test_invalid_outputs_match_golden(self) -> None:
        # Diagnostics of both severities in several files, to fix their order.
        micro = "01-microarchitectural-control-signals.md"
        self.edit_source(micro, "1 → load\n", "1 → load\n1 → again\n")
        self.edit_source(
            micro, "7 → reserved", "10 → too wide\nunparsable"
        )
        self.edit_source(micro, "**Mnemonic:** PC_VAL", "**Mnemonic:** PC")
        self.edit_source(
            "02-architectural-control-signals.md",
            "**Description:** Requests a memory read.\n",
            "",
        )
        self.edit_source(
            "03-sequencing-control-signals.md",
            "**Behavior**",
            "### 4.2 Unindexed Signal (GHOST)\n\n**Behavior**",
        )

        self.assert_outputs_match_golden("invalid")

    def test_missing_definition_fails_extraction(self) -> None:
        self.edit_source(
            "03-sequencing-control-signals.md",
            "(MS_NEXT)",
            "(MS_NEXT_STATE)",
        )

        exit_code, result, _, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(
            codes_of(result), ["UNINDEXED_DEFINITION", "MISSING_DEFINITION"]
        )
        self.assertEqual(result["signals"][-1]["definition"], None)
        self.assertIn("Status: FAILED", stdout)
        self.assertIn("ERROR MISSING_DEFINITION [MS_NEXT]", stdout)
        self.assertNotIn("UNINDEXED_DEFINITION", stdout)

    def test_missing_source_file_fails_before_extraction(self) -> None:
        (self.repo_root / SOURCE_PATHS[-1]).unlink()

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.repo_root)])

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "ERROR: Required control-output source files", stdout.getvalue()
        )
        self.assertFalse((self.repo_root / DEFAULT_JSON_OUTPUT).exists())


def codes_of(result: dict) -> list[str]:
    return [diagnostic["code"] for diagnostic in result["diagnostics"]]


if __name__ == "__main__":
    unittest.main()
