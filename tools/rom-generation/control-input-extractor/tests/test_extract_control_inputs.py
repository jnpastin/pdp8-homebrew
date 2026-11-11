"""Tests for the control-input extractor."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extract_control_inputs import (  # noqa: E402
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    DERIVED_FLAGS,
    EXTERNAL_INPUTS,
    IR_DERIVED_SIGNALS,
    PRIMITIVE_FLAGS,
    SOURCE_DIRECTORY,
    SOURCE_PATHS,
    ConstraintEntry,
    ConsumerEntry,
    DefinitionBlock,
    DependencyEntry,
    Diagnostic,
    EnumeratedValue,
    ExtractionResult,
    IndexEntry,
    Polarity,
    SignalDefinition,
    SourceDocument,
    TextSection,
    ValueRange,
    build_extraction_report,
    build_json_result,
    extract_control_inputs,
    extract_definition_blocks,
    extract_signal,
    find_labeled_sections,
    find_signal_in_heading,
    load_source_documents,
    logic_assigns_signal,
    main,
    match_definition_blocks,
    normalize_bit_width,
    normalize_markdown_text,
    normalize_polarity,
    parse_arguments,
    parse_binary_value,
    parse_bit_width,
    parse_consumer_line,
    parse_definition_constraints,
    parse_definition_consumers,
    parse_definition_dependencies,
    parse_definition_logic_sections,
    parse_definition_values,
    parse_global_constraints,
    parse_index,
    parse_opr_diagrams,
    parse_scalar_attributes,
    parse_value_line,
    remove_section_number,
    repository_relative_path,
    resolve_from_repo_root,
    resolve_tool_paths,
    validate_dependencies,
    validate_logic,
    validate_naming,
    validate_opr_bits,
    validate_required_attributes,
    validate_source_paths,
    validate_value_encoding,
    validate_values_against_width,
    write_text,
)

MICRO_OPS = "../../03-microarchitecture/02-micro-operations.md"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_document(text: str, relative_path: str = "docs/doc.md") -> SourceDocument:
    return SourceDocument(
        path=Path(relative_path), relative_path=relative_path, text=text
    )


def make_entry(
    name: str = "ACN",
    domain: str = PRIMITIVE_FLAGS,
    category: str | None = None,
    line: int = 10,
) -> IndexEntry:
    return IndexEntry(
        name=name,
        domain=domain,
        category=category,
        source_path="docs/index.md",
        line=line,
    )


def make_block(
    *lines: str,
    name: str = "ACN",
    source_path: str = "docs/definitions.md",
    start_line: int = 20,
) -> DefinitionBlock:
    """Build a block whose body lines follow its heading at ``start_line``."""

    return DefinitionBlock(
        signal_name=name,
        heading=name,
        source_path=source_path,
        start_line=start_line,
        lines=tuple(
            (start_line + offset, line)
            for offset, line in enumerate(lines, start=1)
        ),
    )


def make_signal(name: str = "ACN", **fields) -> SignalDefinition:
    return SignalDefinition(block=make_block(name=name), **fields)


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

    def test_relative_path_is_resolved_from_repo_root(self) -> None:
        self.assertEqual(
            resolve_from_repo_root(Path("build/output.json"), self.repo_root),
            (self.repo_root / "build/output.json").resolve(),
        )

    def test_absolute_path_is_preserved(self) -> None:
        absolute_path = (self.repo_root / "output.json").resolve()

        self.assertEqual(
            resolve_from_repo_root(absolute_path, Path.cwd()), absolute_path
        )

    def test_tool_paths_include_all_required_sources(self) -> None:
        paths = resolve_tool_paths(
            argparse.Namespace(
                repo_root=self.repo_root,
                json_output=DEFAULT_JSON_OUTPUT,
                report_output=DEFAULT_REPORT_OUTPUT,
            )
        )

        self.assertEqual(paths.repo_root, self.repo_root)
        self.assertEqual(
            paths.source_paths,
            tuple((self.repo_root / path).resolve() for path in SOURCE_PATHS),
        )
        self.assertEqual(
            paths.json_output, (self.repo_root / DEFAULT_JSON_OUTPUT).resolve()
        )
        self.assertEqual(
            paths.report_output,
            (self.repo_root / DEFAULT_REPORT_OUTPUT).resolve(),
        )

    def test_repository_relative_path_uses_forward_slashes(self) -> None:
        source_path = self.repo_root / "docs" / "04-control" / "input.md"

        self.assertEqual(
            repository_relative_path(source_path, self.repo_root),
            "docs/04-control/input.md",
        )


class SourceLoadingTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.repo_root = Path(temporary_directory.name).resolve()

    def test_missing_source_files_are_reported(self) -> None:
        source_paths = (
            self.repo_root / "first.md",
            self.repo_root / "second.md",
        )

        with self.assertRaises(FileNotFoundError) as context:
            validate_source_paths(source_paths)

        for path in source_paths:
            self.assertIn(str(path), str(context.exception))

    def test_existing_source_files_pass_validation(self) -> None:
        first = self.repo_root / "first.md"
        second = self.repo_root / "second.md"
        first.write_text("first", encoding="utf-8")
        second.write_text("second", encoding="utf-8")

        validate_source_paths((first, second))

    def test_documents_are_loaded_in_supplied_order(self) -> None:
        first = self.repo_root / "docs" / "first.md"
        second = self.repo_root / "docs" / "second.md"
        first.parent.mkdir(parents=True)
        first.write_text("first document", encoding="utf-8")
        second.write_text("second document", encoding="utf-8")

        documents = load_source_documents((second, first), self.repo_root)

        self.assertEqual(
            [(document.relative_path, document.text) for document in documents],
            [
                ("docs/second.md", "second document"),
                ("docs/first.md", "first document"),
            ],
        )

    def test_invalid_utf8_is_rejected(self) -> None:
        source_path = self.repo_root / "invalid.md"
        source_path.write_bytes(b"\xff\xfe\xfa")

        with self.assertRaises(UnicodeDecodeError):
            load_source_documents((source_path,), self.repo_root)


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------


class MarkdownHelperTests(unittest.TestCase):
    def test_section_number_is_removed(self) -> None:
        self.assertEqual(
            remove_section_number("3. Primitive Flags"), "Primitive Flags"
        )
        self.assertEqual(
            remove_section_number("3.2. IR Class Flags"), "IR Class Flags"
        )
        self.assertEqual(
            remove_section_number("External Inputs"), "External Inputs"
        )

    def test_markdown_identifiers_are_normalized(self) -> None:
        self.assertEqual(
            normalize_markdown_text(r"`IR\_ADDR\[6:0\]`"), "IR_ADDR[6:0]"
        )

    def test_labeled_section_ends_at_unrelated_label(self) -> None:
        block = make_block(
            "**Inputs:** trailing",
            "- A",
            "**Purpose:** something",
            "**Inputs:**",
            "- B",
        )

        sections = find_labeled_sections(
            block, {"inputs"}, ends_at_rule=False
        )

        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0].line, 21)
        self.assertEqual(sections[0].trailing_text, "trailing")
        self.assertEqual(sections[0].body, ((22, "- A"),))

    def test_labeled_section_may_end_at_rule_and_reopen(self) -> None:
        block = make_block(
            "**Consumed By:**",
            "- A",
            "---",
            "- ignored",
            "**Consumed By:**",
            "- B",
        )

        sections = find_labeled_sections(
            block, {"consumed by"}, ends_at_rule=True
        )

        self.assertEqual(
            [section.body for section in sections],
            [((22, "- A"),), ((26, "- B"),)],
        )


# ---------------------------------------------------------------------------
# Index and definition blocks
# ---------------------------------------------------------------------------


class IndexParsingTests(unittest.TestCase):
    def test_domain_and_category_are_preserved(self) -> None:
        path = "docs/04-control/10-control-input-definitions/00-index.md"
        document = make_document(
            "## 3. Primitive Flags\n"
            "\n"
            "### 3.1 Processor State Flags\n"
            "\n"
            "- [AC\\_ZERO](./01-flags.md#ac_zero)\n"
            "- [L](./01-flags.md#l)\n"
            "\n"
            "## 4. IR-Derived Signals\n"
            "\n"
            "### 4.1 Instruction Class\n"
            "\n"
            "- [IR\\_IS\\_MRI](./02-ir-derived-fields.md#ir_is_mri)\n",
            relative_path=path,
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(
            entries,
            [
                IndexEntry(
                    "AC_ZERO", PRIMITIVE_FLAGS, "Processor State Flags", path, 5
                ),
                IndexEntry(
                    "L", PRIMITIVE_FLAGS, "Processor State Flags", path, 6
                ),
                IndexEntry(
                    "IR_IS_MRI", IR_DERIVED_SIGNALS, "Instruction Class", path, 12
                ),
            ],
        )
        self.assertEqual(diagnostics, [])

    def test_shallower_heading_closes_domain(self) -> None:
        document = make_document(
            "## Primitive Flags\n"
            "- [ACN](./01-flags.md#acn)\n"
            "## Notes\n"
            "- [STRAY](./01-flags.md#stray)\n"
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual([entry.name for entry in entries], ["ACN"])
        self.assertEqual(codes(diagnostics), ["INDEX_ENTRY_WITHOUT_DOMAIN"])

    def test_entry_without_recognized_domain_is_reported(self) -> None:
        document = make_document(
            "## Other Signals\n- [UNKNOWN](./signals.md#unknown)\n"
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(entries, [])
        self.assertEqual(
            codes(diagnostics),
            ["INDEX_ENTRY_WITHOUT_DOMAIN", "NO_INDEX_ENTRIES"],
        )

    def test_duplicate_index_entry_is_reported(self) -> None:
        document = make_document(
            "## Primitive Flags\n"
            "- [AC\\_ZERO](./01-flags.md#l)\n"
            "- [AC\\_ZERO](./01-flags.md#l)\n"
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual([entry.name for entry in entries], ["AC_ZERO"])
        self.assertEqual(codes(diagnostics), ["DUPLICATE_INDEX_ENTRY"])

    def test_links_without_anchor_are_not_entries(self) -> None:
        document = make_document(
            "## Primitive Flags\n"
            "- [Primitive Flags](./01-flags.md)\n"
            "- [ACN](./01-flags.md#acn)\n"
        )

        entries, _ = parse_index(document)

        self.assertEqual([entry.name for entry in entries], ["ACN"])

    def test_bus_name_with_brackets_is_extracted(self) -> None:
        document = make_document(
            "## External Inputs\n"
            "### Front-Panel Data\n"
            "- [FP\\_IF\\[2:0\\]](./04-external-inputs.md#fp_if)\n"
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual([entry.name for entry in entries], ["FP_IF[2:0]"])
        self.assertEqual(diagnostics, [])


class DefinitionBlockTests(unittest.TestCase):
    def test_exact_signal_heading_is_matched(self) -> None:
        self.assertEqual(find_signal_in_heading("4.1 ACN", {"ACN", "ACZ"}), "ACN")

    def test_parenthesized_signal_heading_is_matched(self) -> None:
        self.assertEqual(
            find_signal_in_heading("4.1 AC Negative (ACN)", {"ACN", "ACZ"}),
            "ACN",
        )

    def test_category_heading_is_not_matched(self) -> None:
        self.assertIsNone(
            find_signal_in_heading("IR Class Flags", {"IR_IS_IOT", "IR_IS_MRI"})
        )

    def test_level_three_definitions_are_extracted(self) -> None:
        document = make_document(
            "# Primitive Flags\n"
            "\n"
            "## 4. Flag Definitions\n"
            "\n"
            "### 4.1 AC Negative (ACN)\n"
            "\n"
            "Definition of ACN.\n"
            "\n"
            "### 4.2 AC Zero (ACZ)\n"
            "\n"
            "Definition of ACZ.\n"
            "\n"
            "## 5. Constraints\n"
            "\n"
            "Not part of ACZ.\n"
        )

        blocks = extract_definition_blocks(document, {"ACN", "ACZ"})

        self.assertEqual([block.signal_name for block in blocks], ["ACN", "ACZ"])
        self.assertEqual([block.start_line for block in blocks], [5, 9])
        self.assertEqual(blocks[0].heading, "AC Negative (ACN)")
        self.assertIn((7, "Definition of ACN."), blocks[0].lines)
        self.assertNotIn(
            "Not part of ACZ.", [text for _, text in blocks[1].lines]
        )

    def test_deeper_headings_keep_source_line_numbers(self) -> None:
        document = make_document(
            "### ACN\n"
            "#### Details\n"
            "**Name:** AC Negative\n"
        )

        (block,) = extract_definition_blocks(document, {"ACN"})

        self.assertEqual(block.lines, ((3, "**Name:** AC Negative"),))

    def test_external_input_categories_do_not_require_special_handling(
        self,
    ) -> None:
        document = make_document(
            "# External Inputs\n"
            "\n"
            "## 4. Front-Panel Command Inputs\n"
            "\n"
            "### 4.1 Start Command (FP_START)\n"
            "\n"
            "Definition of FP_START.\n"
            "\n"
            "## 5. Front-Panel Mode Inputs\n"
            "\n"
            "### 5.1 Single Step (FP_SINGLE_STEP)\n"
            "\n"
            "Definition of FP_SINGLE_STEP.\n"
        )

        blocks = extract_definition_blocks(
            document, {"FP_START", "FP_SINGLE_STEP"}
        )

        self.assertEqual(
            [block.signal_name for block in blocks],
            ["FP_START", "FP_SINGLE_STEP"],
        )

    def test_definition_blocks_are_matched_to_index(self) -> None:
        entries = [make_entry("ACN"), make_entry("ACZ", line=11)]
        blocks = [make_block(name="ACN"), make_block(name="ACZ", start_line=30)]

        definitions, diagnostics = match_definition_blocks(entries, blocks)

        self.assertEqual(set(definitions), {"ACN", "ACZ"})
        self.assertEqual(diagnostics, [])

    def test_missing_definition_is_reported(self) -> None:
        definitions, diagnostics = match_definition_blocks([make_entry()], [])

        self.assertEqual(definitions, {})
        self.assertEqual(codes(diagnostics), ["MISSING_DEFINITION"])

    def test_duplicate_definition_is_reported(self) -> None:
        blocks = [
            make_block(source_path="docs/first.md", start_line=20),
            make_block(source_path="docs/second.md", start_line=30),
        ]

        definitions, diagnostics = match_definition_blocks([make_entry()], blocks)

        self.assertEqual(definitions["ACN"].source_path, "docs/first.md")
        self.assertEqual(codes(diagnostics), ["DUPLICATE_DEFINITION"])
        self.assertIn("docs/first.md:20", diagnostics[0].message)


# ---------------------------------------------------------------------------
# Scalar attributes, bit width, and polarity
# ---------------------------------------------------------------------------


class ScalarAttributeTests(unittest.TestCase):
    def test_scalar_attributes_are_extracted(self) -> None:
        block = make_block(
            "**Mnemonic:** IR_IS_MRI",
            "**Name:** Memory Reference Instruction Flag",
            "**Type:** IR Class",
            "**Bit Width:** 1",
            "**Purpose:** Indicates an MRI instruction.",
            name="IR_IS_MRI",
        )

        attributes, diagnostics = parse_scalar_attributes(block)

        self.assertEqual(
            attributes,
            {
                "mnemonic": "IR_IS_MRI",
                "display_name": "Memory Reference Instruction Flag",
                "input_type": "IR Class",
                "bit_width": "1",
                "purpose": "Indicates an MRI instruction.",
            },
        )
        self.assertEqual(diagnostics, [])

    def test_multiple_attributes_on_one_line_are_extracted(self) -> None:
        block = make_block(
            "**Mnemonic:** IR_ADDR"
            "**Name:** Memory Address Field"
            "**Type:** Field Extraction"
            "**Bit Width:** 7",
            name="IR_ADDR",
        )

        attributes, diagnostics = parse_scalar_attributes(block)

        self.assertEqual(
            attributes,
            {
                "mnemonic": "IR_ADDR",
                "display_name": "Memory Address Field",
                "input_type": "Field Extraction",
                "bit_width": "7",
            },
        )
        self.assertEqual(diagnostics, [])

    def test_source_register_is_extracted(self) -> None:
        block = make_block("**Name:** AC Negative", "**Source Register:** AC")

        attributes, diagnostics = parse_scalar_attributes(block)

        self.assertEqual(attributes["source_register"], "AC")
        self.assertEqual(diagnostics, [])

    def test_label_without_value_is_not_an_attribute(self) -> None:
        block = make_block("**Name:**", "**Purpose:** Indicates something.")

        attributes, diagnostics = parse_scalar_attributes(block)

        self.assertEqual(attributes, {"purpose": "Indicates something."})
        self.assertEqual(diagnostics, [])

    def test_duplicate_scalar_attribute_is_reported(self) -> None:
        block = make_block(
            "**Name:** AC Negative", "**Name:** Accumulator Negative"
        )

        attributes, diagnostics = parse_scalar_attributes(block)

        self.assertEqual(attributes["display_name"], "AC Negative")
        self.assertEqual(codes(diagnostics), ["DUPLICATE_ATTRIBUTE"])
        self.assertEqual(diagnostics[0].line, 22)


class BitWidthTests(unittest.TestCase):
    def test_bit_width_formats_are_normalized(self) -> None:
        self.assertEqual(parse_bit_width("1"), 1)
        self.assertEqual(parse_bit_width("1 bit"), 1)
        self.assertEqual(parse_bit_width("7 bits"), 7)
        self.assertIsNone(parse_bit_width("0"))
        self.assertIsNone(parse_bit_width("one"))

    def test_documented_width_is_used(self) -> None:
        self.assertEqual(
            normalize_bit_width(
                IR_DERIVED_SIGNALS, make_block(), {"bit_width": "7"}
            ),
            (7, []),
        )

    def test_flag_widths_default_to_one(self) -> None:
        for domain in (PRIMITIVE_FLAGS, DERIVED_FLAGS):
            with self.subTest(domain=domain):
                self.assertEqual(
                    normalize_bit_width(domain, make_block(), {}), (1, [])
                )

    def test_missing_width_in_other_domains_is_reported(self) -> None:
        for domain in (IR_DERIVED_SIGNALS, EXTERNAL_INPUTS):
            with self.subTest(domain=domain):
                width, diagnostics = normalize_bit_width(domain, make_block(), {})

                self.assertIsNone(width)
                self.assertEqual(codes(diagnostics), ["MISSING_BIT_WIDTH"])

    def test_invalid_width_is_reported(self) -> None:
        width, diagnostics = normalize_bit_width(
            EXTERNAL_INPUTS, make_block(), {"bit_width": "seven"}
        )

        self.assertIsNone(width)
        self.assertEqual(codes(diagnostics), ["INVALID_BIT_WIDTH"])


class PolarityTests(unittest.TestCase):
    def test_explicit_polarity_is_preserved(self) -> None:
        self.assertEqual(
            normalize_polarity(make_block(), {"polarity": "Active-high"}),
            (Polarity("active-high", "explicit"), []),
        )

    def test_active_low_name_derives_polarity(self) -> None:
        self.assertEqual(
            normalize_polarity(make_block(name="/INT_REQ"), {}),
            (Polarity("active-low", "name-derived"), []),
        )

    def test_unspecified_polarity_defaults_active_high(self) -> None:
        self.assertEqual(
            normalize_polarity(make_block(), {}),
            (Polarity("active-high", "defaulted"), []),
        )

    def test_invalid_polarity_is_reported(self) -> None:
        polarity, diagnostics = normalize_polarity(
            make_block(), {"polarity": "sideways"}
        )

        self.assertIsNone(polarity)
        self.assertEqual(codes(diagnostics), ["INVALID_POLARITY"])


# ---------------------------------------------------------------------------
# Value encodings
# ---------------------------------------------------------------------------


class ValueParsingTests(unittest.TestCase):
    def test_enumerated_value_line_is_parsed(self) -> None:
        self.assertEqual(
            parse_value_line("- `0` -> inactive", 5),
            EnumeratedValue("0", "inactive", 5),
        )
        self.assertEqual(
            parse_value_line("- 1: active", 6), EnumeratedValue("1", "active", 6)
        )

    def test_value_range_is_parsed(self) -> None:
        self.assertEqual(
            parse_value_line("- 000-111 -> field value", 5),
            ValueRange("000", "111", "field value", 5),
        )
        self.assertEqual(
            parse_value_line("- 0000000–1111111 → address field", 6),
            ValueRange("0000000", "1111111", "address field", 6),
        )

    def test_symbolic_description_is_not_numeric_value(self) -> None:
        self.assertIsNone(parse_value_line("external bus value"))

    def test_malformed_value_line_is_rejected(self) -> None:
        self.assertIsNone(parse_value_line(""))
        self.assertIsNone(parse_value_line("- 0"))
        self.assertIsNone(parse_value_line("- -> inactive"))

    def test_symbolic_value_is_rejected(self) -> None:
        self.assertIsNone(parse_value_line("- EXECUTE -> execute state"))

    def test_binary_values_are_parsed(self) -> None:
        self.assertEqual(parse_binary_value("0"), 0)
        self.assertEqual(parse_binary_value("1"), 1)
        self.assertEqual(parse_binary_value("111"), 7)
        self.assertIsNone(parse_binary_value("2"))
        self.assertIsNone(parse_binary_value("08"))


class DefinitionValueTests(unittest.TestCase):
    def test_enumerated_values_are_extracted(self) -> None:
        block = make_block(
            "**Purpose:** Indicates whether AC is negative.",
            "**Value Encoding:**",
            "- `0` -> AC is nonnegative",
            "- `1` -> AC is negative",
            "**Consumed By:**",
            "- skip logic",
        )

        values, ranges, diagnostics = parse_definition_values(block)

        self.assertEqual(
            values,
            [
                EnumeratedValue("0", "AC is nonnegative", 23),
                EnumeratedValue("1", "AC is negative", 24),
            ],
        )
        self.assertEqual(ranges, [])
        self.assertEqual(diagnostics, [])

    def test_value_range_is_extracted(self) -> None:
        block = make_block(
            "**Value Encoding:**",
            "- 0000000-1111111 -> address field",
            "**Consumed By:**",
            "- address generation",
            name="IR_ADDR",
        )

        values, ranges, diagnostics = parse_definition_values(block)

        self.assertEqual(values, [])
        self.assertEqual(
            ranges, [ValueRange("0000000", "1111111", "address field", 22)]
        )
        self.assertEqual(diagnostics, [])

    def test_duplicate_enumerated_value_is_reported(self) -> None:
        block = make_block(
            "**Value Encoding:**", "- 0 -> inactive", "- 0 -> nonnegative"
        )

        values, ranges, diagnostics = parse_definition_values(block)

        self.assertEqual(len(values), 1)
        self.assertEqual(ranges, [])
        self.assertEqual(codes(diagnostics), ["DUPLICATE_VALUE_ENCODING"])

    def test_malformed_value_is_reported_as_warning(self) -> None:
        block = make_block("**Value Encoding:**", "- garbage line")

        _, _, diagnostics = parse_definition_values(block)

        self.assertEqual(codes(diagnostics), ["MALFORMED_VALUE_ENCODING"])
        self.assertEqual(diagnostics[0].severity, "WARNING")


class ValueValidationTests(unittest.TestCase):
    def test_value_encoding_is_required(self) -> None:
        self.assertEqual(
            codes(validate_value_encoding(make_signal())),
            ["MISSING_VALUE_ENCODING"],
        )

    def test_mixed_value_encoding_is_reported(self) -> None:
        signal = make_signal(
            enumerated_values=(EnumeratedValue("0000000", "zero", 30),),
            value_ranges=(ValueRange("0000000", "1111111", "address", 31),),
        )

        self.assertEqual(
            codes(validate_value_encoding(signal)), ["MIXED_VALUE_ENCODING"]
        )

    def test_values_that_fit_width_are_accepted(self) -> None:
        signal = make_signal(
            bit_width=7,
            value_ranges=(ValueRange("0000000", "1111111", "address", 30),),
        )

        self.assertEqual(validate_values_against_width(signal), [])

    def test_value_exceeding_width_is_reported(self) -> None:
        signal = make_signal(
            bit_width=1,
            enumerated_values=(EnumeratedValue("10", "invalid", 30),),
        )

        self.assertEqual(
            codes(validate_values_against_width(signal)),
            ["VALUE_EXCEEDS_BIT_WIDTH"],
        )

    def test_non_binary_values_are_reported(self) -> None:
        signal = make_signal(
            bit_width=3,
            enumerated_values=(EnumeratedValue("7", "seven", 30),),
            value_ranges=(ValueRange("0", "F", "hex", 31),),
        )

        self.assertEqual(
            codes(validate_values_against_width(signal)),
            ["INVALID_BINARY_VALUE", "INVALID_BINARY_RANGE"],
        )

    def test_reversed_range_is_reported(self) -> None:
        signal = make_signal(
            bit_width=7,
            value_ranges=(ValueRange("1111111", "0000000", "reversed", 30),),
        )

        self.assertEqual(
            codes(validate_values_against_width(signal)),
            ["REVERSED_VALUE_RANGE"],
        )

    def test_range_exceeding_width_is_reported(self) -> None:
        signal = make_signal(
            bit_width=1,
            value_ranges=(ValueRange("0", "11", "too wide", 30),),
        )

        self.assertEqual(
            codes(validate_values_against_width(signal)),
            ["RANGE_EXCEEDS_BIT_WIDTH"],
        )

    def test_unknown_width_skips_value_checks(self) -> None:
        signal = make_signal(
            enumerated_values=(EnumeratedValue("10", "unchecked", 30),),
        )

        self.assertEqual(validate_values_against_width(signal), [])


# ---------------------------------------------------------------------------
# Required attributes and dependencies
# ---------------------------------------------------------------------------


class RequiredAttributeTests(unittest.TestCase):
    def test_required_attributes_are_accepted_by_domain(self) -> None:
        cases = {
            PRIMITIVE_FLAGS: {
                "display_name": "AC Is Negative",
                "purpose": "Indicates whether AC is negative.",
                "source_register": "AC",
            },
            IR_DERIVED_SIGNALS: {
                "display_name": "MRI Instruction Flag",
                "input_type": "IR Class",
                "mnemonic": "IR_IS_MRI",
                "purpose": "Indicates an MRI instruction.",
            },
            DERIVED_FLAGS: {
                "display_name": "Skip Taken",
                "mnemonic": "SKIP_TAKEN",
                "purpose": "Indicates whether a skip is taken.",
            },
            EXTERNAL_INPUTS: {
                "display_name": "Front Panel Start",
                "input_type": "External Command Input",
                "purpose": "Indicates a start request.",
            },
        }

        for domain, attributes in cases.items():
            with self.subTest(domain=domain):
                self.assertEqual(
                    validate_required_attributes(
                        make_entry(domain=domain),
                        make_signal(attributes=attributes),
                    ),
                    [],
                )

    def test_missing_required_attribute_is_reported(self) -> None:
        diagnostics = validate_required_attributes(
            make_entry("SKIP_TAKEN", DERIVED_FLAGS),
            make_signal(
                "SKIP_TAKEN",
                attributes={
                    "mnemonic": "SKIP_TAKEN",
                    "purpose": "Indicates whether a skip is taken.",
                },
            ),
        )

        self.assertEqual(codes(diagnostics), ["MISSING_REQUIRED_ATTRIBUTE"])
        self.assertIn("display_name", diagnostics[0].message)

    def test_blank_required_attribute_is_reported(self) -> None:
        diagnostics = validate_required_attributes(
            make_entry("FP_START", EXTERNAL_INPUTS),
            make_signal(
                "FP_START",
                attributes={
                    "display_name": "Front Panel Start",
                    "input_type": "   ",
                    "purpose": "Indicates a start request.",
                },
            ),
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertIn("input_type", diagnostics[0].message)

    def test_unknown_domain_is_reported(self) -> None:
        diagnostics = validate_required_attributes(
            make_entry("UNKNOWN", "Unknown Domain"), make_signal("UNKNOWN")
        )

        self.assertEqual(codes(diagnostics), ["UNKNOWN_INPUT_DOMAIN"])


class DependencyTests(unittest.TestCase):
    def test_dependencies_are_extracted(self) -> None:
        block = make_block(
            "**Inputs:**",
            "- IR_INDIRECT",
            "- EAI",
            "",
            "---",
            "",
            "**Purpose:**",
            "Determines whether auto-indexing is required.",
            name="AUTO_INDEX_REQUIRED",
        )

        dependencies, diagnostics = parse_definition_dependencies(block)

        self.assertEqual(
            dependencies,
            [DependencyEntry("IR_INDIRECT", 22), DependencyEntry("EAI", 23)],
        )
        self.assertEqual(diagnostics, [])

    def test_duplicate_dependency_is_reported(self) -> None:
        block = make_block("**Inputs:**", "- EAI", "- EAI")

        dependencies, diagnostics = parse_definition_dependencies(block)

        self.assertEqual([item.name for item in dependencies], ["EAI"])
        self.assertEqual(codes(diagnostics), ["DUPLICATE_DEPENDENCY"])

    def test_known_derived_dependencies_are_accepted(self) -> None:
        signal = make_signal(
            "AUTO_INDEX_REQUIRED",
            dependencies=(
                DependencyEntry("IR_INDIRECT", 22),
                DependencyEntry("EAI", 23),
            ),
        )

        diagnostics = validate_dependencies(
            make_entry("AUTO_INDEX_REQUIRED", DERIVED_FLAGS),
            signal,
            {"IR_INDIRECT", "EAI", "AUTO_INDEX_REQUIRED"},
        )

        self.assertEqual(diagnostics, [])

    def test_missing_derived_dependencies_are_reported(self) -> None:
        diagnostics = validate_dependencies(
            make_entry("AUTO_INDEX_REQUIRED", DERIVED_FLAGS),
            make_signal("AUTO_INDEX_REQUIRED"),
            {"AUTO_INDEX_REQUIRED"},
        )

        self.assertEqual(codes(diagnostics), ["MISSING_DEPENDENCIES"])

    def test_unknown_dependency_is_reported(self) -> None:
        diagnostics = validate_dependencies(
            make_entry("AUTO_INDEX_REQUIRED", DERIVED_FLAGS),
            make_signal(
                "AUTO_INDEX_REQUIRED",
                dependencies=(DependencyEntry("UNKNOWN_FLAG", 22),),
            ),
            {"AUTO_INDEX_REQUIRED"},
        )

        self.assertEqual(codes(diagnostics), ["UNKNOWN_DEPENDENCY"])
        self.assertEqual(diagnostics[0].line, 22)


# ---------------------------------------------------------------------------
# Logic sections
# ---------------------------------------------------------------------------


class LogicSectionTests(unittest.TestCase):
    def test_inline_derivation_is_extracted(self) -> None:
        block = make_block(
            "**Derivation:** IR_INDIRECT = IR_IS_MRI AND IR[8]",
            "**Value Encoding:**",
            "- 0 -> direct",
            "- 1 -> indirect",
            name="IR_INDIRECT",
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(
            sections,
            {"derivation": TextSection("IR_INDIRECT = IR_IS_MRI AND IR[8]", 21)},
        )
        self.assertEqual(diagnostics, [])

    def test_multiline_expression_in_code_fence_is_extracted(self) -> None:
        block = make_block(
            "**Expression:**",
            "",
            "```",
            "AUTO_INDEX_REQUIRED =",
            "    IR_INDIRECT",
            "AND EAI",
            "```",
            "",
            "---",
            "",
            "**Value Encoding:**",
            name="AUTO_INDEX_REQUIRED",
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(
            sections["expression"].text,
            "AUTO_INDEX_REQUIRED =\nIR_INDIRECT\nAND EAI",
        )
        self.assertEqual(diagnostics, [])

    def test_labels_inside_code_fence_are_text(self) -> None:
        block = make_block(
            "**Expression:**",
            "```",
            "X = **Bold:** Y",
            "---",
            "```",
            name="X",
        )

        sections, _ = parse_definition_logic_sections(block)

        self.assertEqual(sections["expression"].text, "X = **Bold:** Y\n---")

    def test_internal_composition_is_extracted(self) -> None:
        block = make_block(
            "**Internal Composition (local to this definition):**",
            "",
            "SMA_OR = IR_OPR_SMA AND ACN",
            "OR_ANY_TRUE = SMA_OR OR SZA_OR OR SNL_OR",
            "",
            "---",
            "",
            "**Value Encoding:**",
            name="SKIP_TAKEN",
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(
            sections["internal_composition"].text,
            "SMA_OR = IR_OPR_SMA AND ACN\n"
            "OR_ANY_TRUE = SMA_OR OR SZA_OR OR SNL_OR",
        )
        self.assertEqual(diagnostics, [])

    def test_empty_logic_section_is_reported(self) -> None:
        block = make_block(
            "**Derivation:**", "", "---", "", "**Value Encoding:**"
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(sections, {})
        self.assertEqual(codes(diagnostics), ["EMPTY_LOGIC_SECTION"])

    def test_duplicate_logic_section_is_reported(self) -> None:
        block = make_block("**Derivation:** A = 1", "**Derivation:** A = 2")

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(sections["derivation"].text, "A = 1")
        self.assertEqual(codes(diagnostics), ["DUPLICATE_LOGIC_SECTION"])

    def test_logic_assignment_is_detected(self) -> None:
        self.assertTrue(
            logic_assigns_signal("SKIP_TAKEN = LOCAL_VALUE", "SKIP_TAKEN")
        )
        self.assertTrue(
            logic_assigns_signal(
                "IR_OPR_GROUP1 = IR_IS_OPR AND (IR[8] == 0)", "IR_OPR_GROUP1"
            )
        )
        self.assertFalse(
            logic_assigns_signal(
                "IR_OPR_GROUP2 = IR_IS_OPR AND IR[8]", "IR_OPR_GROUP1"
            )
        )


class LogicValidationTests(unittest.TestCase):
    def test_ir_derived_signal_requires_derivation(self) -> None:
        self.assertEqual(
            codes(
                validate_logic(
                    make_entry("IR_INDIRECT", IR_DERIVED_SIGNALS),
                    make_signal("IR_INDIRECT"),
                )
            ),
            ["MISSING_DERIVATION"],
        )

    def test_ir_derivation_result_mismatch_is_reported(self) -> None:
        diagnostics = validate_logic(
            make_entry("IR_ADDR", IR_DERIVED_SIGNALS),
            make_signal(
                "IR_ADDR",
                logic={"derivation": TextSection("IR_ADDRESS = IR[6:0]", 25)},
            ),
        )

        self.assertEqual(codes(diagnostics), ["DERIVATION_RESULT_MISMATCH"])
        self.assertEqual(diagnostics[0].line, 25)

    def test_derived_flag_accepts_expression(self) -> None:
        signal = make_signal(
            "AUTO_INDEX_REQUIRED",
            logic={
                "expression": TextSection(
                    "AUTO_INDEX_REQUIRED = IR_INDIRECT AND EAI", 30
                )
            },
        )

        self.assertEqual(
            validate_logic(
                make_entry("AUTO_INDEX_REQUIRED", DERIVED_FLAGS), signal
            ),
            [],
        )

    def test_derived_flag_accepts_internal_composition(self) -> None:
        signal = make_signal(
            "SKIP_TAKEN",
            logic={
                "internal_composition": TextSection(
                    "LOCAL_SKIP = ACN OR ACZ\nSKIP_TAKEN = LOCAL_SKIP", 25
                )
            },
        )

        self.assertEqual(
            validate_logic(make_entry("SKIP_TAKEN", DERIVED_FLAGS), signal), []
        )

    def test_derived_flag_without_logic_is_reported(self) -> None:
        self.assertEqual(
            codes(
                validate_logic(
                    make_entry("SKIP_TAKEN", DERIVED_FLAGS),
                    make_signal("SKIP_TAKEN"),
                )
            ),
            ["MISSING_DERIVED_LOGIC"],
        )

    def test_derived_flag_result_mismatch_is_reported(self) -> None:
        signal = make_signal(
            "SKIP_TAKEN",
            logic={"expression": TextSection("SKIP_TAKE = ACN", 25)},
        )

        self.assertEqual(
            codes(validate_logic(make_entry("SKIP_TAKEN", DERIVED_FLAGS), signal)),
            ["DERIVED_RESULT_MISMATCH"],
        )

    def test_other_domains_have_no_logic_rule(self) -> None:
        self.assertEqual(validate_logic(make_entry(), make_signal()), [])


class NamingValidationTests(unittest.TestCase):
    def test_mnemonic_mismatch_is_reported(self) -> None:
        diagnostics = validate_naming(
            make_entry("IR_ADDR", IR_DERIVED_SIGNALS),
            make_signal("IR_ADDR", attributes={"mnemonic": "IR_ADDRESS"}),
        )

        self.assertEqual(codes(diagnostics), ["MNEMONIC_NAME_MISMATCH"])

    def test_mnemonic_is_not_checked_for_external_inputs(self) -> None:
        diagnostics = validate_naming(
            make_entry("FP_START", EXTERNAL_INPUTS),
            make_signal("FP_START", attributes={"mnemonic": "OTHER"}),
        )

        self.assertEqual(diagnostics, [])

    def test_active_low_name_conflict_is_reported(self) -> None:
        diagnostics = validate_naming(
            make_entry("/INT_REQ", EXTERNAL_INPUTS),
            make_signal(
                "/INT_REQ", polarity=Polarity("active-high", "explicit")
            ),
        )

        self.assertEqual(codes(diagnostics), ["ACTIVE_LOW_NAME_CONFLICT"])


# ---------------------------------------------------------------------------
# Constraints and consumers
# ---------------------------------------------------------------------------


class ConstraintTests(unittest.TestCase):
    def test_plural_constraints_are_extracted(self) -> None:
        block = make_block(
            "**Constraints:**",
            "- meaningful only when RUN = 0",
            "- must be treated as a momentary command input",
            "**Consumed By:**",
            "- run-state sequencing",
        )

        constraints, diagnostics = parse_definition_constraints(block)

        self.assertEqual(
            constraints,
            [
                ConstraintEntry("meaningful only when RUN = 0", 22),
                ConstraintEntry(
                    "must be treated as a momentary command input", 23
                ),
            ],
        )
        self.assertEqual(diagnostics, [])

    def test_singular_inline_constraint_is_extracted(self) -> None:
        block = make_block(
            "**Constraint:** IR_DF and IR_IF share the same bit positions.",
            "**Consumed By:**",
        )

        constraints, _ = parse_definition_constraints(block)

        self.assertEqual(
            constraints,
            [
                ConstraintEntry(
                    "IR_DF and IR_IF share the same bit positions.", 21
                )
            ],
        )

    def test_multiline_prose_constraint_is_extracted(self) -> None:
        block = make_block(
            "**Constraint:**",
            "IR_DF and IR_IF share the same bit positions",
            "but are interpreted in different instruction contexts.",
            "**Consumed By:**",
            "- field-transfer logic",
        )

        constraints, _ = parse_definition_constraints(block)

        self.assertEqual(
            constraints,
            [
                ConstraintEntry(
                    "IR_DF and IR_IF share the same bit positions "
                    "but are interpreted in different instruction contexts.",
                    22,
                )
            ],
        )

    def test_rule_ends_constraint_section(self) -> None:
        block = make_block(
            "**Constraints:**", "- first", "---", "- not a constraint"
        )

        constraints, _ = parse_definition_constraints(block)

        self.assertEqual([item.text for item in constraints], ["first"])

    def test_definition_without_constraints_returns_empty_list(self) -> None:
        block = make_block("**Purpose:** Indicates whether AC is negative.")

        self.assertEqual(parse_definition_constraints(block), ([], []))


class GlobalConstraintTests(unittest.TestCase):
    NAMES = {"IR_IS_MRI", "IR_IS_IOT", "IR_IS_OPR"}

    def test_global_constraints_are_extracted(self) -> None:
        document = make_document(
            "- Classes:\n  - `EXACTLY_ONE(IR_IS_MRI, IR_IS_IOT, IR_IS_OPR)`\n"
        )

        constraints, diagnostics = parse_global_constraints(
            [document], self.NAMES
        )

        self.assertEqual(
            [(item.kind, item.inputs, item.line) for item in constraints],
            [("exactly_one", ("IR_IS_MRI", "IR_IS_IOT", "IR_IS_OPR"), 2)],
        )
        self.assertEqual(diagnostics, [])

    def test_top_level_bullets_are_ignored(self) -> None:
        document = make_document("- `AT_MOST_ONE(IR_IS_MRI, IR_IS_IOT)`\n")

        self.assertEqual(
            parse_global_constraints([document], self.NAMES), ([], [])
        )

    def test_invalid_global_constraints_are_reported(self) -> None:
        document = make_document(
            "- Classes:\n"
            "  - `AT_MOST_ONE(IR_IS_MRI)`\n"
            "  - `AT_MOST_ONE(IR_IS_MRI, NOPE)`\n"
            "  - `AT_MOST_ONE(IR_IS_MRI, IR_IS_IOT)`\n"
            "  - `AT_MOST_ONE(IR_IS_MRI, IR_IS_IOT)`\n"
        )

        constraints, diagnostics = parse_global_constraints(
            [document], self.NAMES
        )

        self.assertEqual(len(constraints), 1)
        self.assertEqual(
            codes(diagnostics),
            [
                "INVALID_GLOBAL_CONSTRAINT",
                "UNKNOWN_GLOBAL_CONSTRAINT_INPUT",
                "DUPLICATE_GLOBAL_CONSTRAINT",
            ],
        )


class ConsumerTests(unittest.TestCase):
    def test_linked_consumer_line_is_parsed(self) -> None:
        self.assertEqual(
            parse_consumer_line(f"- [PC_INC]({MICRO_OPS}#pc_inc)", 7),
            ConsumerEntry("PC_INC", f"{MICRO_OPS}#pc_inc", 7),
        )

    def test_plain_text_consumer_line_is_parsed(self) -> None:
        self.assertEqual(
            parse_consumer_line("- run-state sequencing", 7),
            ConsumerEntry("run-state sequencing", None, 7),
        )

    def test_non_list_consumer_line_is_rejected(self) -> None:
        self.assertIsNone(parse_consumer_line("run-state sequencing"))

    def test_consumed_by_entries_are_extracted(self) -> None:
        block = make_block(
            "**Consumed By:**",
            "- Control decision:",
            "- run-state sequencing",
            "- console execution control",
            "**Constraints:**",
            "- meaningful only when RUN = 0",
        )

        consumers, diagnostics = parse_definition_consumers(block)

        self.assertEqual(
            consumers,
            [
                ConsumerEntry("Control decision:", None, 22),
                ConsumerEntry("run-state sequencing", None, 23),
                ConsumerEntry("console execution control", None, 24),
            ],
        )
        self.assertEqual(diagnostics, [])

    def test_used_by_micro_operations_are_extracted(self) -> None:
        block = make_block(
            "**Used By μops:**",
            f"- [MB_INC]({MICRO_OPS}#mb_inc)",
            f"- [MEM_WRITE_FROM_MB]({MICRO_OPS}#mem_write_from_mb)",
            "",
            "---",
        )

        consumers, _ = parse_definition_consumers(block)

        self.assertEqual(
            [(item.text, item.target) for item in consumers],
            [
                ("MB_INC", f"{MICRO_OPS}#mb_inc"),
                ("MEM_WRITE_FROM_MB", f"{MICRO_OPS}#mem_write_from_mb"),
            ],
        )

    def test_none_consumer_is_preserved_as_plain_text(self) -> None:
        block = make_block(
            "**Used By μops:**", "- (none - used for MS transition control)"
        )

        consumers, _ = parse_definition_consumers(block)

        self.assertEqual(
            [(item.text, item.target) for item in consumers],
            [("(none - used for MS transition control)", None)],
        )


# ---------------------------------------------------------------------------
# Signal extraction and outputs
# ---------------------------------------------------------------------------


class SignalExtractionTests(unittest.TestCase):
    def test_all_properties_are_extracted(self) -> None:
        block = make_block(
            "**Name:** Front Panel Start",
            "**Type:** External Command Input",
            "**Bit Width:** 1",
            "**Purpose:** Indicates a start request.",
            "**Value Encoding:**",
            "- 0 -> idle",
            "- 1 -> start",
            "**Constraints:**",
            "- meaningful only when RUN = 0",
            "**Consumed By:**",
            "- run-state sequencing",
            name="FP_START",
        )

        signal, diagnostics = extract_signal(
            make_entry("FP_START", EXTERNAL_INPUTS), block
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(signal.bit_width, 1)
        self.assertEqual(signal.polarity, Polarity("active-high", "defaulted"))
        self.assertEqual(signal.attributes["input_type"], "External Command Input")
        self.assertEqual(len(signal.enumerated_values), 2)
        self.assertEqual(len(signal.constraints), 1)
        self.assertEqual(len(signal.consumers), 1)


class ReportTests(unittest.TestCase):
    def test_extraction_report_contains_summary(self) -> None:
        signal = make_signal(
            attributes={"display_name": "AC Negative"},
            bit_width=1,
            polarity=Polarity("active-high", "defaulted"),
            enumerated_values=(
                EnumeratedValue("0", "not negative", 30),
                EnumeratedValue("1", "negative", 31),
            ),
        )
        result = ExtractionResult(
            entries=(make_entry(),),
            signals={"ACN": signal},
            global_constraints=(),
            diagnostics=(),
        )

        report = build_extraction_report(result)

        self.assertIn("Indexed control inputs: 1", report)
        self.assertIn("Matched definitions: 1", report)
        self.assertIn("Primitive Flags: 1", report)
        self.assertIn("Enumerated values: 2", report)
        self.assertIn("No diagnostics.", report)

    def test_extraction_report_contains_diagnostics(self) -> None:
        diagnostic = Diagnostic(
            severity="ERROR",
            code="TEST_ERROR",
            message="Test diagnostic message.",
            source_path="docs/test.md",
            line=42,
            signal_name="TEST_SIGNAL",
        )
        result = ExtractionResult((), {}, (), (diagnostic,))

        report = build_extraction_report(result)

        self.assertIn("ERROR: 1", report)
        self.assertIn("ERROR TEST_ERROR [TEST_SIGNAL]", report)
        self.assertIn("Source: docs/test.md:42", report)
        self.assertIn("Test diagnostic message.", report)

    def test_missing_definition_has_reduced_json_shape(self) -> None:
        result = ExtractionResult((make_entry(),), {}, (), ())

        (signal,) = build_json_result(result)["signals"]

        self.assertIsNone(signal["definition"])
        self.assertEqual(signal["extraction_status"], "definition-missing")

    def test_text_is_written_with_parent_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "nested" / "report.txt"

            write_text(output_path, "Test report\n")

            self.assertEqual(
                output_path.read_text(encoding="utf-8"), "Test report\n"
            )


# ---------------------------------------------------------------------------
# OPR bit positions
# ---------------------------------------------------------------------------


def opr_diagram(*labels: str) -> str:
    """An OPR diagram whose mnemonic row holds ``labels`` for bits 7 to 0."""

    cells = "".join(f" {label:^3} │" for label in labels)
    return (
        "┌────┬────┬─────┬────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┬─────┐\n"
        "│ 11 │ 10 │  9  │ 8  │  7  │  6  │  5  │  4  │  3  │  2  │  1  │  0  │\n"
        "├────┼────┼─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤\n"
        "│  1 │  1 │  1  │ 0  │     │     │     │     │     │     │     │     │\n"
        "├────┴────┴─────┼────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤\n"
        f"│      OPR      │    │{cells}\n"
        "└───────────────┴────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┴─────┘\n"
    )


GROUP1_DIAGRAM = opr_diagram("CLA", "CLL", "CMA", "CML", "RAR", "RAL", "BSW", "IAC")
GROUP2_DIAGRAM = opr_diagram("CLA", "SPA", "SNA", "SZL", "", "OSR", "HLT", "")
GROUP3_DIAGRAM = opr_diagram("CLA", "MQA", "", "MQL", "", "", "", "")


def diagram_document(group: int, *diagrams: str) -> SourceDocument:
    fenced = "".join(f"```\n{diagram}```\n\nText.\n\n" for diagram in diagrams)
    return make_document(
        f"# Group {group}\n\n{fenced}", f"docs/02-isa/0{group}-group.md"
    )


def opr_signal(name: str, derivation: str) -> SignalDefinition:
    return make_signal(name, logic={"derivation": TextSection(derivation, 30)})


class OprBitTests(unittest.TestCase):
    def test_diagram_positions_come_from_the_bit_row(self) -> None:
        positions, diagnostics = parse_opr_diagrams(
            diagram_document(2, GROUP2_DIAGRAM, GROUP3_DIAGRAM), 2
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            [(item.mnemonic, item.bit, item.group, item.line) for item in positions],
            [
                ("CLA", 7, 2, 9),
                ("SPA", 6, 2, 9),
                ("SNA", 5, 2, 9),
                ("SZL", 4, 2, 9),
                ("OSR", 2, 2, 9),
                ("HLT", 1, 2, 9),
                ("CLA", 7, 2, 21),
                ("MQA", 6, 2, 21),
                ("MQL", 4, 2, 21),
            ],
        )
        self.assertEqual(positions[0].source_path, "docs/02-isa/02-group.md")

    def test_document_without_a_diagram_is_an_error(self) -> None:
        positions, diagnostics = parse_opr_diagrams(diagram_document(1), 1)

        self.assertEqual(positions, [])
        self.assertEqual(codes(diagnostics), ["MISSING_OPR_DIAGRAM"])

    def test_malformed_diagrams_are_errors(self) -> None:
        unclosed = "┌──┐\n│ 1 │\n"
        no_numbers = GROUP1_DIAGRAM.replace("│ 11 │", "│ XX │")
        outside = GROUP1_DIAGRAM.replace("IAC │\n", "IAC │ ZZZ\n")

        for diagram in (unclosed, no_numbers, outside):
            with self.subTest(diagram=diagram.splitlines()[1][:12]):
                _, diagnostics = parse_opr_diagrams(
                    make_document(f"```\n{diagram}```\n"), 1
                )
                self.assertEqual(codes(diagnostics), ["MALFORMED_OPR_DIAGRAM"])

    def check(self, *signals: SignalDefinition) -> list[Diagnostic]:
        positions = [
            position
            for group, diagram in enumerate(
                (GROUP1_DIAGRAM, GROUP2_DIAGRAM, GROUP3_DIAGRAM), 1
            )
            for position in parse_opr_diagrams(
                diagram_document(group, diagram), group
            )[0]
        ]
        entries = [
            make_entry(signal.block.signal_name, IR_DERIVED_SIGNALS)
            for signal in signals
        ]
        return validate_opr_bits(
            entries,
            {signal.block.signal_name: signal for signal in signals},
            positions,
        )

    def test_matching_derivations_pass(self) -> None:
        self.assertEqual(
            self.check(
                opr_signal("IR_OPR_RAR", "IR_OPR_RAR = IR_OPR_GROUP1 AND IR[3]"),
                opr_signal("IR_OPR_CLA", "IR_OPR_CLA = IR_IS_OPR AND IR[7]"),
                opr_signal("IR_OPR_GROUP1", "IR_OPR_GROUP1 = anything"),
                opr_signal("IR_OPR_SKIP_MODE", "IR_OPR_SKIP_MODE = x"),
            ),
            [],
        )

    def test_wrong_bit_is_reported_per_diagram(self) -> None:
        diagnostics = self.check(
            opr_signal("IR_OPR_IAC", "IR_OPR_IAC = IR_OPR_GROUP1 AND IR[3]"),
            opr_signal("IR_OPR_CLA", "IR_OPR_CLA = IR_IS_OPR AND IR[6]"),
        )

        self.assertEqual(
            [(item.code, item.signal_name, item.line) for item in diagnostics],
            [
                ("OPR_BIT_MISMATCH", "IR_OPR_IAC", 30),
                ("OPR_BIT_MISMATCH", "IR_OPR_CLA", 30),
                ("OPR_BIT_MISMATCH", "IR_OPR_CLA", 30),
                ("OPR_BIT_MISMATCH", "IR_OPR_CLA", 30),
            ],
        )
        self.assertEqual(
            diagnostics[0].message,
            "Derivation uses IR[3], but the Group 1 ISA diagram "
            "(docs/02-isa/01-group.md:9) places IAC at bit 0.",
        )

    def test_mnemonic_outside_the_named_group_is_reported(self) -> None:
        diagnostics = self.check(
            opr_signal("IR_OPR_OSR", "IR_OPR_OSR = IR_OPR_GROUP1 AND IR[2]")
        )

        self.assertEqual(codes(diagnostics), ["OPR_BIT_MISMATCH"])
        self.assertEqual(
            diagnostics[0].message, "OSR is not in the Group 1 ISA diagram."
        )

    def test_other_derivation_forms_are_reported(self) -> None:
        for derivation in (
            "IR_OPR_CLA = IR[7]",
            "IR_OPR_CLA = IR_OPR_GROUP1 AND IR[7] AND RUN",
            "IR_OPR_CLL = IR_OPR_GROUP1 AND IR[7]",
        ):
            with self.subTest(derivation=derivation):
                self.assertEqual(
                    codes(self.check(opr_signal("IR_OPR_CLA", derivation))),
                    ["UNCHECKED_OPR_DERIVATION"],
                )

    def test_only_documented_ir_derived_inputs_are_checked(self) -> None:
        signal = opr_signal("IR_OPR_CLA", "IR_OPR_CLA = IR_IS_OPR AND IR[1]")
        positions, _ = parse_opr_diagrams(diagram_document(1, GROUP1_DIAGRAM), 1)

        for entries, signals in (
            ([make_entry("IR_OPR_CLA", DERIVED_FLAGS)], {"IR_OPR_CLA": signal}),
            ([make_entry("IR_OPR_CLA", IR_DERIVED_SIGNALS)], {}),
            (
                [make_entry("IR_OPR_CLA", IR_DERIVED_SIGNALS)],
                {"IR_OPR_CLA": make_signal("IR_OPR_CLA")},
            ),
        ):
            self.assertEqual(validate_opr_bits(entries, signals, positions), [])

    def test_extraction_checks_bits_only_with_diagrams(self) -> None:
        index = make_document(FIXTURE_DOCUMENTS["00-index.md"])
        definitions = [
            make_document(FIXTURE_DOCUMENTS[path.name], path.as_posix())
            for path in SOURCE_PATHS[1:5]
        ]
        diagrams = {
            group: make_document("# None\n", f"docs/02-isa/0{group}.md")
            for group in (1, 2, 3)
        }

        self.assertEqual(
            extract_control_inputs(index, definitions).diagnostics, ()
        )
        self.assertEqual(
            codes(extract_control_inputs(index, definitions, diagrams).diagnostics),
            ["MISSING_OPR_DIAGRAM"] * 3,
        )


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

FIXTURE_DOCUMENTS = {
    "00-index.md": """\
# Control Input Signal Index

## 3. Primitive Flags

- [ACN](./01-flags.md#acn)

## 4. IR-Derived Signals

### 4.1 Instruction Class

- [IR\\_IS\\_MRI](./02-ir-derived-fields.md#ir_is_mri)
- [IR\\_IS\\_OPR](./02-ir-derived-fields.md#ir_is_opr)

## 5. Derived Flags

- [MRI\\_OR\\_OPR](./03-derived-flags.md#mri_or_opr)

## 6. External Inputs

- [FP\\_START](./04-external-inputs.md#fp_start)
""",
    "01-flags.md": """\
# Primitive Flags

### ACN

**Name:** AC Negative
**Source Register:** AC
**Purpose:** Indicates whether AC is negative.

**Value Encoding:**
- `0` → non-negative
- `1` → negative
""",
    "02-ir-derived-fields.md": """\
# IR-Derived Fields

- Classes:
  - `AT_MOST_ONE(IR_IS_MRI, IR_IS_OPR)`

### IR_IS_MRI

**Mnemonic:** IR_IS_MRI
**Name:** MRI Flag
**Type:** IR Class
**Bit Width:** 1
**Purpose:** Indicates an MRI.

**Derivation:**
```text
IR_IS_MRI = IR[11:9] < 6
```

**Value Encoding:**
- 0 → not MRI
- 1 → MRI

### IR_IS_OPR

**Mnemonic:** IR_IS_OPR
**Name:** OPR Flag
**Type:** IR Class
**Bit Width:** 1
**Purpose:** Indicates an OPR.

**Derivation:** IR_IS_OPR = IR[11:9] == 7

**Value Encoding:**
- 0 → not OPR
- 1 → OPR
""",
    "03-derived-flags.md": """\
# Derived Flags

### MRI_OR_OPR

**Mnemonic:** MRI_OR_OPR
**Name:** MRI or OPR
**Purpose:** Combines two classes.

**Inputs:**
- IR_IS_MRI
- IR_IS_OPR

---

**Expression:**
```
MRI_OR_OPR = IR_IS_MRI OR IR_IS_OPR
```

**Value Encoding:**
- 0 → neither
- 1 → either
""",
    "04-external-inputs.md": """\
# External Inputs

### Start Command (FP_START)

**Name:** Front Panel Start
**Type:** External Command Input
**Bit Width:** 1
**Purpose:** Requests a start.

**Value Encoding:**
- 0 → idle
- 1 → start

**Constraints:**
- meaningful only when RUN = 0

**Consumed By:**
- [RUN_SET](../../03-microarchitecture/02-micro-operations.md#run_set)
""",
    "01-group-1.md": "# Group 1\n\n```\n" + GROUP1_DIAGRAM + "```\n",
    "02-group-2.md": "# Group 2\n\n```\n" + GROUP2_DIAGRAM + "```\n",
    "03-group-3.md": "# Group 3\n\n```\n" + GROUP3_DIAGRAM + "```\n",
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

    def test_valid_documents_extract_cleanly(self) -> None:
        exit_code, result, report, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(
            [(signal["name"], signal["domain"]) for signal in result["signals"]],
            [
                ("ACN", PRIMITIVE_FLAGS),
                ("IR_IS_MRI", IR_DERIVED_SIGNALS),
                ("IR_IS_OPR", IR_DERIVED_SIGNALS),
                ("MRI_OR_OPR", DERIVED_FLAGS),
                ("FP_START", EXTERNAL_INPUTS),
            ],
        )
        self.assertEqual(
            [item["kind"] for item in result["constraints"]], ["at_most_one"]
        )

        fp_start = result["signals"][-1]
        self.assertEqual(fp_start["category"], None)
        self.assertEqual(fp_start["bit_width"], 1)
        self.assertEqual(fp_start["consumers"][0]["text"], "RUN_SET")
        self.assertEqual(
            fp_start["definition_source"]["heading"], "Start Command (FP_START)"
        )

        self.assertIn("Indexed control inputs: 5", report)
        self.assertIn("Status: SUCCEEDED", stdout)

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
            "control-inputs.json": self.repo_root / DEFAULT_JSON_OUTPUT,
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
                self.assertEqual(actual, golden_path.read_text(encoding="utf-8"))

    def test_valid_outputs_match_golden(self) -> None:
        self.assert_outputs_match_golden("valid")

    def test_invalid_outputs_match_golden(self) -> None:
        # Diagnostics of both severities in several files, to fix their order.
        self.edit_source(
            "01-flags.md",
            "- `1` → negative",
            "- `1` → negative\n- `1` → again\n- EXECUTE → symbolic",
        )
        self.edit_source(
            "02-ir-derived-fields.md", "IR_IS_OPR = IR", "IR_IS_OP = IR"
        )
        self.edit_source(
            "03-derived-flags.md", "- IR_IS_OPR\n", "- IR_IS_OPR\n- GHOST\n"
        )
        self.edit_source("04-external-inputs.md", "**Bit Width:** 1\n", "")

        self.assert_outputs_match_golden("invalid")

    def test_missing_definition_fails_extraction(self) -> None:
        flags = self.repo_root / SOURCE_PATHS[1]
        flags.write_text("# Primitive Flags\n", encoding="utf-8")

        exit_code, result, _, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertEqual(codes_of(result), ["MISSING_DEFINITION"])
        self.assertEqual(
            result["signals"][0]["extraction_status"], "definition-missing"
        )
        self.assertIn("Status: FAILED", stdout)
        self.assertIn("ERROR MISSING_DEFINITION [ACN]", stdout)

    def test_missing_source_file_fails_before_extraction(self) -> None:
        (self.repo_root / SOURCE_PATHS[4]).unlink()
        outputs = [
            self.repo_root / DEFAULT_JSON_OUTPUT,
            self.repo_root / DEFAULT_REPORT_OUTPUT,
        ]
        for output in outputs:
            write_text(output, "stale\n")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.repo_root)])

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Required control-input source files", stdout.getvalue())
        self.assertEqual([output.exists() for output in outputs], [False, False])

    def test_output_that_is_an_input_is_refused(self) -> None:
        source = self.repo_root / SOURCE_PATHS[0]
        original = source.read_bytes()

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                ["--repo-root", str(self.repo_root), "--json-output", str(source)]
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout.getvalue())
        self.assertEqual(source.read_bytes(), original)

    def test_output_that_is_a_directory_is_refused(self) -> None:
        report = self.repo_root / DEFAULT_REPORT_OUTPUT
        write_text(report, "earlier\n")
        directory = self.repo_root / "out"
        directory.mkdir()

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                ["--repo-root", str(self.repo_root), "--json-output", str(directory)]
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout.getvalue())
        self.assertTrue(report.exists())


def codes_of(result: dict) -> list[str]:
    return [diagnostic["code"] for diagnostic in result["diagnostics"]]


if __name__ == "__main__":
    unittest.main()
