"""Tests for the control-input extractor."""

from __future__ import annotations

import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr
import io

SOURCE_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "src"
)

sys.path.insert(
    0,
    str(SOURCE_DIRECTORY),
)

from extract_control_inputs import (  # noqa: E402
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    SOURCE_PATHS,
    load_source_documents,
    parse_arguments,
    repository_relative_path,
    resolve_from_repo_root,
    resolve_tool_paths,
    validate_source_paths,
    Diagnostic,
    IndexEntry,
    SourceDocument,
    normalize_markdown_text,
    parse_index,
    remove_section_number,
    DefinitionBlock,
    extract_definition_blocks,
    find_signal_in_heading,
    match_definition_blocks,
    extract_all_scalar_attributes,
    parse_scalar_attributes,
    normalize_bit_widths,
    normalize_polarities,
    parse_bit_width,
    EnumeratedValue,
    ValueRange,
    parse_value_line,
    EnumeratedValue,
    ValueRange,
    extract_all_definition_values,
    parse_definition_values,
    parse_value_line,
    parse_binary_value,
    validate_values_against_widths,
    validate_required_attributes,
    extract_all_definition_dependencies,
    parse_definition_dependencies,
    validate_derived_dependencies,
    DependencyEntry,
    extract_all_definition_dependencies,
    parse_definition_dependencies,
    validate_derived_dependencies,
    TextSection,
    extract_all_logic_sections,
    parse_definition_logic_sections,
    validate_required_logic_sections,
    ConstraintEntry,
    extract_all_definition_constraints,
    parse_definition_constraints,
    ConsumerEntry,
    extract_all_definition_consumers,
    parse_consumer_line,
    parse_definition_consumers,
    logic_assigns_signal,
    validate_final_structure,
    build_extraction_report,
    write_text_report,
)

class ArgumentParsingTests(unittest.TestCase):
    def test_repo_root_is_required(self) -> None:
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_arguments([])

    def test_default_output_paths_are_used(self) -> None:
        arguments = parse_arguments(
            [
                "--repo-root",
                ".",
            ]
        )

        self.assertEqual(
            arguments.json_output,
            DEFAULT_JSON_OUTPUT,
        )
        self.assertEqual(
            arguments.report_output,
            DEFAULT_REPORT_OUTPUT,
        )

    def test_output_paths_may_be_overridden(self) -> None:
        arguments = parse_arguments(
            [
                "--repo-root",
                ".",
                "--json-output",
                "alternate/control-inputs.json",
                "--report-output",
                "alternate/report.txt",
            ]
        )

        self.assertEqual(
            arguments.json_output,
            Path("alternate/control-inputs.json"),
        )
        self.assertEqual(
            arguments.report_output,
            Path("alternate/report.txt"),
        )


class PathResolutionTests(unittest.TestCase):
    def test_relative_path_is_resolved_from_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()

            resolved = resolve_from_repo_root(
                Path("build/output.json"),
                repo_root,
            )

            self.assertEqual(
                resolved,
                (repo_root / "build/output.json").resolve(),
            )

    def test_absolute_path_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            absolute_path = (
                Path(temporary_directory)
                / "output.json"
            ).resolve()

            resolved = resolve_from_repo_root(
                absolute_path,
                Path.cwd(),
            )

            self.assertEqual(
                resolved,
                absolute_path,
            )

    def test_tool_paths_include_all_required_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()

            arguments = argparse.Namespace(
                repo_root=repo_root,
                json_output=DEFAULT_JSON_OUTPUT,
                report_output=DEFAULT_REPORT_OUTPUT,
            )

            paths = resolve_tool_paths(arguments)

            self.assertEqual(
                paths.repo_root,
                repo_root,
            )
            self.assertEqual(
                paths.source_paths,
                tuple(
                    (repo_root / path).resolve()
                    for path in SOURCE_PATHS
                ),
            )
            self.assertEqual(
                paths.json_output,
                (repo_root / DEFAULT_JSON_OUTPUT).resolve(),
            )
            self.assertEqual(
                paths.report_output,
                (repo_root / DEFAULT_REPORT_OUTPUT).resolve(),
            )

    def test_repository_relative_path_uses_forward_slashes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()
            source_path = (
                repo_root
                / "docs"
                / "04-control"
                / "input.md"
            )

            self.assertEqual(
                repository_relative_path(
                    source_path,
                    repo_root,
                ),
                "docs/04-control/input.md",
            )


class SourceValidationTests(unittest.TestCase):
    def test_missing_source_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)

            source_paths = (
                repo_root / "first.md",
                repo_root / "second.md",
            )

            with self.assertRaises(FileNotFoundError) as context:
                validate_source_paths(source_paths)

            message = str(context.exception)

            self.assertIn(
                str(source_paths[0]),
                message,
            )
            self.assertIn(
                str(source_paths[1]),
                message,
            )

    def test_existing_source_files_pass_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)

            first_path = repo_root / "first.md"
            second_path = repo_root / "second.md"

            first_path.write_text(
                "first",
                encoding="utf-8",
            )
            second_path.write_text(
                "second",
                encoding="utf-8",
            )

            validate_source_paths(
                (
                    first_path,
                    second_path,
                )
            )


class DocumentLoadingTests(unittest.TestCase):
    def test_documents_are_loaded_in_supplied_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()

            first_path = repo_root / "docs" / "first.md"
            second_path = repo_root / "docs" / "second.md"

            first_path.parent.mkdir(parents=True)

            first_path.write_text(
                "first document",
                encoding="utf-8",
            )
            second_path.write_text(
                "second document",
                encoding="utf-8",
            )

            documents = load_source_documents(
                (
                    second_path,
                    first_path,
                ),
                repo_root,
            )

            self.assertEqual(
                [
                    document.relative_path
                    for document in documents
                ],
                [
                    "docs/second.md",
                    "docs/first.md",
                ],
            )
            self.assertEqual(
                [
                    document.text
                    for document in documents
                ],
                [
                    "second document",
                    "first document",
                ],
            )

    def test_invalid_utf8_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()
            source_path = repo_root / "invalid.md"

            source_path.write_bytes(
                b"\xff\xfe\xfa"
            )

            with self.assertRaises(UnicodeDecodeError):
                load_source_documents(
                    (source_path,),
                    repo_root,
                )

class IndexExtractionTests(unittest.TestCase):
    def test_section_number_is_removed(self) -> None:
        self.assertEqual(
            remove_section_number("3. Primitive Flags"),
            "Primitive Flags",
        )
        self.assertEqual(
            remove_section_number("3.2. IR Class Flags"),
            "IR Class Flags",
        )
        self.assertEqual(
            remove_section_number("External Inputs"),
            "External Inputs",
        )

    def test_markdown_identifiers_are_normalized(self) -> None:
        self.assertEqual(
            normalize_markdown_text(r"`IR\_ADDR\[6:0\]`"),
            "IR_ADDR[6:0]",
        )

    def test_domain_and_category_are_preserved(self) -> None:
        document = SourceDocument(
            path=Path("00-index.md"),
            relative_path=(
                "docs/04-control/"
                "10-control-input-definitions/00-index.md"
            ),
            text=(
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
                "- [IR\\_IS\\_MRI]"
                "(./02-ir-derived-fields.md#ir_is_mri)\n"
            ),
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(
            entries,
            [
                IndexEntry(
                    name="AC_ZERO",
                    domain="Primitive Flags",
                    category="Processor State Flags",
                    source_path=(
                        "docs/04-control/"
                        "10-control-input-definitions/00-index.md"
                    ),
                    line=5,
                ),
                IndexEntry(
                    name="L",
                    domain="Primitive Flags",
                    category="Processor State Flags",
                    source_path=(
                        "docs/04-control/"
                        "10-control-input-definitions/00-index.md"
                    ),
                    line=6,
                ),
                IndexEntry(
                    name="IR_IS_MRI",
                    domain="IR-Derived Signals",
                    category="Instruction Class",
                    source_path=(
                        "docs/04-control/"
                        "10-control-input-definitions/00-index.md"
                    ),
                    line=12,
                ),
            ],
        )
        self.assertEqual(diagnostics, [])

    def test_entry_without_recognized_domain_is_reported(
        self,
    ) -> None:
        document = SourceDocument(
            path=Path("00-index.md"),
            relative_path="docs/index.md",
            text=(
                "## Other Signals\n"
                "- [UNKNOWN" + "](./signals.md#unknown)\n"
            ),
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(entries, [])
        self.assertEqual(
            [
                diagnostic.code
                for diagnostic in diagnostics
            ],
            [
                "INDEX_ENTRY_WITHOUT_DOMAIN",
                "NO_INDEX_ENTRIES",
            ],
        )

    def test_duplicate_index_entry_is_reported(self) -> None:
        document = SourceDocument(
            path=Path("00-index.md"),
            relative_path="docs/index.md",
            text=(
                "## Primitive Flags\n"
                "- [AC\\_ZERO](./01-flags.md#l)\n"
                "- [AC\\_ZERO](./01-flags.md#l)\n"
            ),
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(
            [entry.name for entry in entries],
            ["AC_ZERO"],
        )
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "DUPLICATE_INDEX_ENTRY",
        )

    def test_bus_name_with_brackets_is_extracted(self) -> None:
        document = SourceDocument(
            path=Path("00-index.md"),
            relative_path="docs/index.md",
            text=(
                "## External Inputs\n"
                "### Front-Panel Data\n"
                "- [FP\\_IF\\[2:0\\]]"
                "(./04-external-inputs.md#fp_if)\n"
            ),
        )

        entries, diagnostics = parse_index(document)

        self.assertEqual(
            [entry.name for entry in entries],
            ["FP_IF[2:0]"],
        )
        self.assertEqual(diagnostics, [])

    def test_exact_signal_heading_is_matched(self) -> None:
        self.assertEqual(
            find_signal_in_heading(
                "4.1 ACN",
                {"ACN", "ACZ"},
            ),
            "ACN",
        )


    def test_parenthesized_signal_heading_is_matched(self) -> None:
        self.assertEqual(
            find_signal_in_heading(
                "4.1 AC Negative (ACN)",
                {"ACN", "ACZ"},
            ),
            "ACN",
        )


    def test_category_heading_is_not_matched(self) -> None:
        self.assertIsNone(
            find_signal_in_heading(
                "IR Class Flags",
                {"IR_IS_IOT", "IR_IS_MRI"},
            )
        )


    def test_level_three_definitions_are_extracted(self) -> None:
        document = SourceDocument(
            path=Path("01-flags.md"),
            relative_path="docs/inputs/01-flags.md",
            text=(
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
            ),
        )

        blocks = extract_definition_blocks(
            document,
            {"ACN", "ACZ"},
        )

        self.assertEqual(
            [block.signal_name for block in blocks],
            ["ACN", "ACZ"],
        )
        self.assertEqual(
            [block.start_line for block in blocks],
            [5, 9],
        )
        self.assertIn(
            "Definition of ACN.",
            blocks[0].lines,
        )
        self.assertNotIn(
            "Not part of ACZ.",
            blocks[1].lines,
        )


    def test_external_input_categories_do_not_require_special_handling(
        self,
    ) -> None:
        document = SourceDocument(
            path=Path("04-external-inputs.md"),
            relative_path="docs/inputs/04-external-inputs.md",
            text=(
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
            ),
        )

        blocks = extract_definition_blocks(
            document,
            {
                "FP_START",
                "FP_SINGLE_STEP",
            },
        )

        self.assertEqual(
            [block.signal_name for block in blocks],
            [
                "FP_START",
                "FP_SINGLE_STEP",
            ],
        )

    def test_definition_blocks_are_matched_to_index(self) -> None:
        entries = [
            IndexEntry(
                name="ACN",
                domain="Primitive Flags",
                category=None,
                source_path="docs/index.md",
                line=10,
            ),
            IndexEntry(
                name="ACZ",
                domain="Primitive Flags",
                category=None,
                source_path="docs/index.md",
                line=11,
            ),
        ]

        blocks = [
            DefinitionBlock(
                signal_name="ACN",
                heading="AC Negative (ACN)",
                source_path="docs/flags.md",
                start_line=20,
                lines=(),
            ),
            DefinitionBlock(
                signal_name="ACZ",
                heading="AC Zero (ACZ)",
                source_path="docs/flags.md",
                start_line=30,
                lines=(),
            ),
        ]

        definitions, diagnostics = match_definition_blocks(
            entries,
            blocks,
        )

        self.assertEqual(
            set(definitions),
            {
                "ACN",
                "ACZ",
            },
        )
        self.assertEqual(diagnostics, [])


    def test_missing_definition_is_reported(self) -> None:
        entries = [
            IndexEntry(
                name="ACN",
                domain="Primitive Flags",
                category=None,
                source_path="docs/index.md",
                line=10,
            ),
        ]

        definitions, diagnostics = match_definition_blocks(
            entries,
            [],
        )

        self.assertEqual(definitions, {})
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "MISSING_DEFINITION",
        )


    def test_duplicate_definition_is_reported(self) -> None:
        entries = [
            IndexEntry(
                name="ACN",
                domain="Primitive Flags",
                category=None,
                source_path="docs/index.md",
                line=10,
            ),
        ]

        blocks = [
            DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/first.md",
                start_line=20,
                lines=(),
            ),
            DefinitionBlock(
                signal_name="ACN",
                heading="AC Negative (ACN)",
                source_path="docs/second.md",
                start_line=30,
                lines=(),
            ),
        ]

        definitions, diagnostics = match_definition_blocks(
            entries,
            blocks,
        )

        self.assertEqual(set(definitions), {"ACN"})
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "DUPLICATE_DEFINITION",
        )
        

    def test_scalar_attributes_are_extracted(self) -> None:
        block = DefinitionBlock(
            signal_name="IR_IS_MRI",
            heading="IR_IS_MRI",
            source_path="docs/ir-fields.md",
            start_line=20,
            lines=(
                "**Mnemonic:** IR_IS_MRI",
                "**Name:** Memory Reference Instruction Flag",
                "**Type:** IR Class",
                "**Bit Width:** 1",
                "**Purpose:** Indicates an MRI instruction.",
            ),
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
        block = DefinitionBlock(
            signal_name="IR_ADDR",
            heading="IR_ADDR",
            source_path="docs/ir-fields.md",
            start_line=20,
            lines=(
                "**Mnemonic:** IR_ADDR"
                "**Name:** Memory Address Field"
                "**Type:** Field Extraction"
                "**Bit Width:** 7",
            ),
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
        block = DefinitionBlock(
            signal_name="ACN",
            heading="ACN",
            source_path="docs/flags.md",
            start_line=20,
            lines=(
                "**Name:** AC Negative",
                "**Source Register:** AC",
                "**Purpose:** Indicates that AC is negative.",
            ),
        )

        attributes, diagnostics = parse_scalar_attributes(block)

        self.assertEqual(attributes["source_register"], "AC")
        self.assertEqual(diagnostics, [])

    def test_duplicate_scalar_attribute_is_reported(self) -> None:
        block = DefinitionBlock(
            signal_name="ACN",
            heading="ACN",
            source_path="docs/flags.md",
            start_line=20,
            lines=(
                "**Name:** AC Negative",
                "**Name:** Accumulator Negative",
            ),
        )

        attributes, diagnostics = parse_scalar_attributes(block)

        self.assertEqual(attributes["display_name"], "AC Negative")
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "DUPLICATE_ATTRIBUTE",
        )

    def test_attributes_are_extracted_from_all_definitions(self) -> None:
        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=20,
                lines=(
                    "**Name:** AC Negative",
                    "**Source Register:** AC",
                ),
            ),
            "FP_START": DefinitionBlock(
                signal_name="FP_START",
                heading="FP_START",
                source_path="docs/external.md",
                start_line=40,
                lines=(
                    "**Name:** Front Panel Start Command",
                    "**Type:** External Command Input",
                ),
            ),
        }

        attributes, diagnostics = extract_all_scalar_attributes(
            definitions
        )

        self.assertEqual(
            attributes["ACN"]["source_register"],
            "AC",
        )
        self.assertEqual(
            attributes["FP_START"]["input_type"],
            "External Command Input",
        )
        self.assertEqual(diagnostics, [])


    def test_bit_width_formats_are_normalized(self) -> None:
        self.assertEqual(parse_bit_width("1"), 1)
        self.assertEqual(parse_bit_width("1 bit"), 1)
        self.assertEqual(parse_bit_width("7 bits"), 7)
        self.assertIsNone(parse_bit_width("0"))
        self.assertIsNone(parse_bit_width("one"))


    def test_bit_widths_are_normalized(self) -> None:
        definitions = {
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path="docs/ir-fields.md",
                start_line=20,
                lines=(),
            ),
        }

        bit_widths, diagnostics = normalize_bit_widths(
            definitions,
            {
                "IR_ADDR": {
                    "bit_width": "7",
                },
            },
        )

        self.assertEqual(bit_widths, {"IR_ADDR": 7})
        self.assertEqual(diagnostics, [])


    def test_primitive_flag_width_defaults_to_one(self) -> None:
        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path=(
                    "docs/04-control/10-control-input-definitions/"
                    "01-flags.md"
                ),
                start_line=20,
                lines=(),
            ),
        }

        bit_widths, diagnostics = normalize_bit_widths(
            definitions,
            {
                "ACN": {
                    "display_name": "AC Negative",
                },
            },
        )

        self.assertEqual(bit_widths, {"ACN": 1})
        self.assertEqual(diagnostics, [])


    def test_derived_flag_width_defaults_to_one(self) -> None:
        definitions = {
            "SKIP_TAKEN": DefinitionBlock(
                signal_name="SKIP_TAKEN",
                heading="SKIP_TAKEN",
                source_path=(
                    "docs/04-control/10-control-input-definitions/"
                    "03-derived-flags.md"
                ),
                start_line=20,
                lines=(),
            ),
        }

        bit_widths, diagnostics = normalize_bit_widths(
            definitions,
            {
                "SKIP_TAKEN": {
                    "purpose": "Indicates whether a skip is required.",
                },
            },
        )

        self.assertEqual(bit_widths, {"SKIP_TAKEN": 1})
        self.assertEqual(diagnostics, [])


    def test_missing_width_in_other_source_is_reported(self) -> None:
        definitions = {
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path=(
                    "docs/04-control/10-control-input-definitions/"
                    "02-ir-derived-fields.md"
                ),
                start_line=20,
                lines=(),
            ),
            "FP_IF": DefinitionBlock(
                signal_name="FP_IF",
                heading="FP_IF",
                source_path=(
                    "docs/04-control/10-control-input-definitions/"
                    "04-external-inputs.md"
                ),
                start_line=40,
                lines=(),
            ),
        }

        bit_widths, diagnostics = normalize_bit_widths(
            definitions,
            {
                "IR_ADDR": {},
                "FP_IF": {},
            },
        )

        self.assertEqual(bit_widths, {})
        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            [
                "MISSING_BIT_WIDTH",
                "MISSING_BIT_WIDTH",
            ],
        )


    def test_explicit_polarity_is_preserved(self) -> None:
        definitions = {
            "FP_START": DefinitionBlock(
                signal_name="FP_START",
                heading="FP_START",
                source_path="docs/external.md",
                start_line=20,
                lines=(),
            ),
        }

        polarities, diagnostics = normalize_polarities(
            definitions,
            {
                "FP_START": {
                    "polarity": "Active-high",
                },
            },
        )

        self.assertEqual(
            polarities["FP_START"],
            {
                "value": "active-high",
                "source": "explicit",
            },
        )
        self.assertEqual(diagnostics, [])


    def test_active_low_name_derives_polarity(self) -> None:
        definitions = {
            "/INT_REQ": DefinitionBlock(
                signal_name="/INT_REQ",
                heading="Interrupt Request (/INT_REQ)",
                source_path="docs/external.md",
                start_line=20,
                lines=(),
            ),
        }

        polarities, diagnostics = normalize_polarities(
            definitions,
            {
                "/INT_REQ": {},
            },
        )

        self.assertEqual(
            polarities["/INT_REQ"],
            {
                "value": "active-low",
                "source": "name-derived",
            },
        )
        self.assertEqual(diagnostics, [])


    def test_unspecified_polarity_defaults_active_high(self) -> None:
        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=20,
                lines=(),
            ),
        }

        polarities, diagnostics = normalize_polarities(
            definitions,
            {
                "ACN": {},
            },
        )

        self.assertEqual(
            polarities["ACN"],
            {
                "value": "active-high",
                "source": "defaulted",
            },
        )
        self.assertEqual(diagnostics, [])

    def test_enumerated_value_line_is_parsed(self) -> None:
        self.assertEqual(
            parse_value_line("- `0` -> inactive"),
            (
                "enumerated",
                (
                    "0",
                    "inactive",
                ),
            ),
        )

        self.assertEqual(
            parse_value_line("- 1: active"),
            (
                "enumerated",
                (
                    "1",
                    "active",
                ),
            ),
        )


    def test_value_range_is_parsed(self) -> None:
        self.assertEqual(
            parse_value_line("- 000-111 -> field value"),
            (
                "range",
                (
                    "000",
                    "111",
                    "field value",
                ),
            ),
        )

        self.assertEqual(
            parse_value_line("- 0000000–1111111 → address field"),
            (
                "range",
                (
                    "0000000",
                    "1111111",
                    "address field",
                ),
            ),
        )


    def test_symbolic_description_is_not_numeric_value(self) -> None:
        self.assertIsNone(
            parse_value_line("external bus value")
        )


    def test_malformed_value_line_is_rejected(self) -> None:
        self.assertIsNone(parse_value_line(""))
        self.assertIsNone(parse_value_line("- 0"))
        self.assertIsNone(parse_value_line("- -> inactive"))


    def test_enumerated_value_line_is_parsed(self) -> None:
        self.assertEqual(
            parse_value_line("- `0` -> inactive"),
            ("enumerated", ("0", "inactive")),
        )
        self.assertEqual(
            parse_value_line("- 1: active"),
            ("enumerated", ("1", "active")),
        )

    def test_value_range_is_parsed(self) -> None:
        self.assertEqual(
            parse_value_line("- 000-111 -> field value"),
            ("range", ("000", "111", "field value")),
        )
        self.assertEqual(
            parse_value_line("- 0000000–1111111 → address field"),
            (
                "range",
                ("0000000", "1111111", "address field"),
            ),
        )

    def test_symbolic_description_is_not_numeric_value(self) -> None:
        self.assertIsNone(parse_value_line("external bus value"))

    def test_malformed_value_line_is_rejected(self) -> None:
        self.assertIsNone(parse_value_line(""))
        self.assertIsNone(parse_value_line("- 0"))
        self.assertIsNone(parse_value_line("- -> inactive"))

    def test_definition_enumerated_values_are_extracted(self) -> None:
        block = DefinitionBlock(
            signal_name="ACN",
            heading="ACN",
            source_path="docs/flags.md",
            start_line=20,
            lines=(
                "**Purpose:** Indicates whether AC is negative.",
                "**Value Encoding:**",
                "- `0` -> AC is nonnegative",
                "- `1` -> AC is negative",
                "**Consumed By:**",
                "- skip logic",
            ),
        )

        values, ranges, diagnostics = parse_definition_values(block)

        self.assertEqual(
            [(value.value, value.meaning) for value in values],
            [
                ("0", "AC is nonnegative"),
                ("1", "AC is negative"),
            ],
        )
        self.assertEqual(ranges, [])
        self.assertEqual(diagnostics, [])

    def test_definition_value_range_is_extracted(self) -> None:
        block = DefinitionBlock(
            signal_name="IR_ADDR",
            heading="IR_ADDR",
            source_path="docs/ir-fields.md",
            start_line=20,
            lines=(
                "**Value Encoding:**",
                "- 0000000-1111111 -> address field",
                "**Consumed By:**",
                "- address generation",
            ),
        )

        values, ranges, diagnostics = parse_definition_values(block)

        self.assertEqual(values, [])
        self.assertEqual(len(ranges), 1)
        self.assertEqual(ranges[0].start, "0000000")
        self.assertEqual(ranges[0].end, "1111111")
        self.assertEqual(ranges[0].meaning, "address field")
        self.assertEqual(diagnostics, [])

    def test_duplicate_enumerated_value_is_reported(self) -> None:
        block = DefinitionBlock(
            signal_name="ACN",
            heading="ACN",
            source_path="docs/flags.md",
            start_line=20,
            lines=(
                "**Value Encoding:**",
                "- 0 -> inactive",
                "- 0 -> nonnegative",
            ),
        )

        values, ranges, diagnostics = parse_definition_values(block)

        self.assertEqual(len(values), 1)
        self.assertEqual(ranges, [])
        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["DUPLICATE_VALUE_ENCODING"],
        )

    def test_values_are_extracted_from_all_definitions(self) -> None:
        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=20,
                lines=(
                    "**Value Encoding:**",
                    "- 0 -> inactive",
                    "- 1 -> active",
                ),
            ),
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path="docs/ir-fields.md",
                start_line=40,
                lines=(
                    "**Value Encoding:**",
                    "- 0000000-1111111 -> address field",
                ),
            ),
        }

        values, ranges, diagnostics = extract_all_definition_values(
            definitions
        )

        self.assertEqual(len(values["ACN"]), 2)
        self.assertEqual(values["IR_ADDR"], [])
        self.assertEqual(len(ranges["IR_ADDR"]), 1)
        self.assertEqual(ranges["ACN"], [])
        self.assertEqual(diagnostics, [])

    def test_binary_values_are_parsed(self) -> None:
        self.assertEqual(parse_binary_value("0"), 0)
        self.assertEqual(parse_binary_value("1"), 1)
        self.assertEqual(parse_binary_value("111"), 7)
        self.assertIsNone(parse_binary_value("2"))
        self.assertIsNone(parse_binary_value("08"))


    def test_values_that_fit_width_are_accepted(self) -> None:
        definitions = {
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path="docs/ir-fields.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_values_against_widths(
            definitions,
            {"IR_ADDR": 7},
            {"IR_ADDR": []},
            {
                "IR_ADDR": [
                    ValueRange(
                        start="0000000",
                        end="1111111",
                        meaning="address field",
                        line=30,
                    ),
                ],
            },
        )

        self.assertEqual(diagnostics, [])


    def test_value_exceeding_width_is_reported(self) -> None:
        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_values_against_widths(
            definitions,
            {"ACN": 1},
            {
                "ACN": [
                    EnumeratedValue(
                        value="10",
                        meaning="invalid",
                        line=30,
                    ),
                ],
            },
            {"ACN": []},
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["VALUE_EXCEEDS_BIT_WIDTH"],
        )


    def test_reversed_range_is_reported(self) -> None:
        definitions = {
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path="docs/ir-fields.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_values_against_widths(
            definitions,
            {"IR_ADDR": 7},
            {"IR_ADDR": []},
            {
                "IR_ADDR": [
                    ValueRange(
                        start="1111111",
                        end="0000000",
                        meaning="invalid range",
                        line=30,
                    ),
                ],
            },
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["REVERSED_VALUE_RANGE"],
        )

    def test_required_attributes_are_accepted_by_domain(self) -> None:
        entries = [
            IndexEntry(
                name="ACN",
                domain="Primitive Flags",
                category=None,
                source_path="docs/index.md",
                line=10,
            ),
            IndexEntry(
                name="IR_IS_MRI",
                domain="IR-Derived Signals",
                category="IR Class Flags",
                source_path="docs/index.md",
                line=20,
            ),
            IndexEntry(
                name="SKIP_TAKEN",
                domain="Derived Flags",
                category=None,
                source_path="docs/index.md",
                line=30,
            ),
            IndexEntry(
                name="FP_START",
                domain="External Inputs",
                category="Front Panel Commands",
                source_path="docs/index.md",
                line=40,
            ),
        ]

        definitions = {
            entry.name: DefinitionBlock(
                signal_name=entry.name,
                heading=entry.name,
                source_path="docs/definitions.md",
                start_line=entry.line,
                lines=(),
            )
            for entry in entries
        }

        attributes = {
            "ACN": {
                "display_name": "AC Is Negative",
                "purpose": "Indicates whether AC is negative.",
                "source_register": "AC",
            },
            "IR_IS_MRI": {
                "display_name": "MRI Instruction Flag",
                "input_type": "IR Class",
                "mnemonic": "IR_IS_MRI",
                "purpose": "Indicates an MRI instruction.",
            },
            "SKIP_TAKEN": {
                "display_name": "Skip Taken",
                "mnemonic": "SKIP_TAKEN",
                "purpose": "Indicates whether a skip is taken.",
            },
            "FP_START": {
                "display_name": "Front Panel Start",
                "input_type": "External Command Input",
                "purpose": "Indicates a start request.",
            },
        }

        diagnostics = validate_required_attributes(
            entries,
            definitions,
            attributes,
        )

        self.assertEqual(diagnostics, [])

    def test_missing_required_attribute_is_reported(self) -> None:
        entry = IndexEntry(
            name="SKIP_TAKEN",
            domain="Derived Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "SKIP_TAKEN": DefinitionBlock(
                signal_name="SKIP_TAKEN",
                heading="SKIP_TAKEN",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_required_attributes(
            [entry],
            definitions,
            {
                "SKIP_TAKEN": {
                    "mnemonic": "SKIP_TAKEN",
                    "purpose": "Indicates whether a skip is taken.",
                },
            },
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "MISSING_REQUIRED_ATTRIBUTE",
        )
        self.assertIn("display_name", diagnostics[0].message)

    def test_blank_required_attribute_is_reported(self) -> None:
        entry = IndexEntry(
            name="FP_START",
            domain="External Inputs",
            category="Front Panel Commands",
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "FP_START": DefinitionBlock(
                signal_name="FP_START",
                heading="FP_START",
                source_path="docs/external-inputs.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_required_attributes(
            [entry],
            definitions,
            {
                "FP_START": {
                    "display_name": "Front Panel Start",
                    "input_type": "   ",
                    "purpose": "Indicates a start request.",
                },
            },
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertIn("input_type", diagnostics[0].message)

    def test_unknown_domain_is_reported(self) -> None:
        entry = IndexEntry(
            name="UNKNOWN",
            domain="Unknown Domain",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "UNKNOWN": DefinitionBlock(
                signal_name="UNKNOWN",
                heading="UNKNOWN",
                source_path="docs/unknown.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_required_attributes(
            [entry],
            definitions,
            {"UNKNOWN": {}},
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["UNKNOWN_INPUT_DOMAIN"],
        )

    def test_derived_dependencies_are_extracted(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="AUTO_INDEX_REQUIRED",
            heading="AUTO_INDEX_REQUIRED",
            source_path="docs/derived-flags.md",
            start_line=20,
            lines=(
                bold + "Inputs:" + bold,
                "- IR_INDIRECT",
                "- EAI",
                "",
                "---",
                "",
                bold + "Purpose:" + bold,
                "Determines whether auto-indexing is required.",
            ),
        )

        dependencies, diagnostics = parse_definition_dependencies(block)

        self.assertEqual(
            [dependency.name for dependency in dependencies],
            ["IR_INDIRECT", "EAI"],
        )
        self.assertEqual(
            [dependency.line for dependency in dependencies],
            [22, 23],
        )
        self.assertEqual(diagnostics, [])

    def test_duplicate_dependency_is_reported(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="AUTO_INDEX_REQUIRED",
            heading="AUTO_INDEX_REQUIRED",
            source_path="docs/derived-flags.md",
            start_line=20,
            lines=(
                bold + "Inputs:" + bold,
                "- EAI",
                "- EAI",
            ),
        )

        dependencies, diagnostics = parse_definition_dependencies(block)

        self.assertEqual(
            [dependency.name for dependency in dependencies],
            ["EAI"],
        )
        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["DUPLICATE_DEPENDENCY"],
        )

    def test_dependencies_are_extracted_from_all_definitions(self) -> None:
        bold = chr(42) + chr(42)

        definitions = {
            "AUTO_INDEX_REQUIRED": DefinitionBlock(
                signal_name="AUTO_INDEX_REQUIRED",
                heading="AUTO_INDEX_REQUIRED",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(
                    bold + "Inputs:" + bold,
                    "- IR_INDIRECT",
                    "- EAI",
                ),
            ),
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=40,
                lines=(),
            ),
        }

        dependencies, diagnostics = extract_all_definition_dependencies(
            definitions
        )

        self.assertEqual(
            [
                dependency.name
                for dependency in dependencies["AUTO_INDEX_REQUIRED"]
            ],
            ["IR_INDIRECT", "EAI"],
        )
        self.assertEqual(dependencies["ACN"], [])
        self.assertEqual(diagnostics, [])

    def test_known_derived_dependencies_are_accepted(self) -> None:
        entries = [
            IndexEntry(
                name="IR_INDIRECT",
                domain="IR-Derived Signals",
                category="Addressing Mode",
                source_path="docs/index.md",
                line=10,
            ),
            IndexEntry(
                name="EAI",
                domain="Primitive Flags",
                category=None,
                source_path="docs/index.md",
                line=11,
            ),
            IndexEntry(
                name="AUTO_INDEX_REQUIRED",
                domain="Derived Flags",
                category=None,
                source_path="docs/index.md",
                line=12,
            ),
        ]

        definitions = {
            "AUTO_INDEX_REQUIRED": DefinitionBlock(
                signal_name="AUTO_INDEX_REQUIRED",
                heading="AUTO_INDEX_REQUIRED",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        dependencies = {
            "AUTO_INDEX_REQUIRED": [
                DependencyEntry(name="IR_INDIRECT", line=22),
                DependencyEntry(name="EAI", line=23),
            ],
        }

        diagnostics = validate_derived_dependencies(
            entries,
            definitions,
            dependencies,
        )

        self.assertEqual(diagnostics, [])

    def test_missing_derived_dependencies_are_reported(self) -> None:
        entry = IndexEntry(
            name="AUTO_INDEX_REQUIRED",
            domain="Derived Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "AUTO_INDEX_REQUIRED": DefinitionBlock(
                signal_name="AUTO_INDEX_REQUIRED",
                heading="AUTO_INDEX_REQUIRED",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_derived_dependencies(
            [entry],
            definitions,
            {"AUTO_INDEX_REQUIRED": []},
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["MISSING_DEPENDENCIES"],
        )

    def test_unknown_derived_dependency_is_reported(self) -> None:
        entry = IndexEntry(
            name="AUTO_INDEX_REQUIRED",
            domain="Derived Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "AUTO_INDEX_REQUIRED": DefinitionBlock(
                signal_name="AUTO_INDEX_REQUIRED",
                heading="AUTO_INDEX_REQUIRED",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        dependencies = {
            "AUTO_INDEX_REQUIRED": [
                DependencyEntry(name="UNKNOWN_FLAG", line=22),
            ],
        }

        diagnostics = validate_derived_dependencies(
            [entry],
            definitions,
            dependencies,
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["UNKNOWN_DEPENDENCY"],
        )

    def test_inline_derivation_is_extracted(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="IR_INDIRECT",
            heading="IR_INDIRECT",
            source_path="docs/ir-derived-fields.md",
            start_line=20,
            lines=(
                bold + "Derivation:" + bold + " IR_INDIRECT = IR_IS_MRI AND IR[8]",
                bold + "Value Encoding:" + bold,
                "- 0 -> direct",
                "- 1 -> indirect",
            ),
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(
            sections["derivation"].text,
            "IR_INDIRECT = IR_IS_MRI AND IR[8]",
        )
        self.assertEqual(sections["derivation"].line, 21)
        self.assertEqual(diagnostics, [])

    def test_multiline_expression_in_code_fence_is_extracted(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="AUTO_INDEX_REQUIRED",
            heading="AUTO_INDEX_REQUIRED",
            source_path="docs/derived-flags.md",
            start_line=20,
            lines=(
                bold + "Expression:" + bold,
                "",
                "```",
                "AUTO_INDEX_REQUIRED =",
                "    IR_INDIRECT",
                "AND EAI",
                "```",
                "",
                "---",
                "",
                bold + "Value Encoding:" + bold,
            ),
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(
            sections["expression"].text,
            "\n".join(
                [
                    "AUTO_INDEX_REQUIRED =",
                    "IR_INDIRECT",
                    "AND EAI",
                ]
            ),
        )

    def test_internal_composition_is_extracted(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="SKIP_TAKEN",
            heading="SKIP_TAKEN",
            source_path="docs/derived-flags.md",
            start_line=20,
            lines=(
                bold
                + "Internal Composition (local to this definition):"
                + bold,
                "",
                "SMA_OR = IR_OPR_SMA AND ACN",
                "OR_ANY_TRUE = SMA_OR OR SZA_OR OR SNL_OR",
                "",
                "---",
                "",
                bold + "Value Encoding:" + bold,
            ),
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(
            sections["internal_composition"].text,
            (
                "SMA_OR = IR_OPR_SMA AND ACN\n"
                "OR_ANY_TRUE = SMA_OR OR SZA_OR OR SNL_OR"
            ),
        )
        self.assertEqual(diagnostics, [])

    def test_empty_logic_section_is_reported(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="IR_INDIRECT",
            heading="IR_INDIRECT",
            source_path="docs/ir-derived-fields.md",
            start_line=20,
            lines=(
                bold + "Derivation:" + bold,
                "",
                "---",
                "",
                bold + "Value Encoding:" + bold,
            ),
        )

        sections, diagnostics = parse_definition_logic_sections(block)

        self.assertEqual(sections, {})
        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["EMPTY_LOGIC_SECTION"],
        )

    def test_ir_derived_signal_requires_derivation(self) -> None:
        entry = IndexEntry(
            name="IR_INDIRECT",
            domain="IR-Derived Signals",
            category="Addressing Mode",
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "IR_INDIRECT": DefinitionBlock(
                signal_name="IR_INDIRECT",
                heading="IR_INDIRECT",
                source_path="docs/ir-derived-fields.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_required_logic_sections(
            [entry],
            definitions,
            {"IR_INDIRECT": {}},
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["MISSING_DERIVATION"],
        )

    def test_derived_flag_accepts_expression(self) -> None:
        entry = IndexEntry(
            name="AUTO_INDEX_REQUIRED",
            domain="Derived Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "AUTO_INDEX_REQUIRED": DefinitionBlock(
                signal_name="AUTO_INDEX_REQUIRED",
                heading="AUTO_INDEX_REQUIRED",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        logic_sections = {
            "AUTO_INDEX_REQUIRED": {
                "expression": TextSection(
                    text="AUTO_INDEX_REQUIRED = IR_INDIRECT AND EAI",
                    line=30,
                ),
            },
        }

        diagnostics = validate_required_logic_sections(
            [entry],
            definitions,
            logic_sections,
        )

        self.assertEqual(diagnostics, [])

    def test_derived_flag_accepts_internal_composition(self) -> None:
        entry = IndexEntry(
            name="SKIP_TAKEN",
            domain="Derived Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "SKIP_TAKEN": DefinitionBlock(
                signal_name="SKIP_TAKEN",
                heading="SKIP_TAKEN",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        logic_sections = {
            "SKIP_TAKEN": {
                "internal_composition": TextSection(
                    text="SKIP_TAKEN = OR_ANY_TRUE",
                    line=30,
                ),
            },
        }

        diagnostics = validate_required_logic_sections(
            [entry],
            definitions,
            logic_sections,
        )

        self.assertEqual(diagnostics, [])

    def test_derived_flag_without_logic_is_reported(self) -> None:
        entry = IndexEntry(
            name="SKIP_TAKEN",
            domain="Derived Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "SKIP_TAKEN": DefinitionBlock(
                signal_name="SKIP_TAKEN",
                heading="SKIP_TAKEN",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_required_logic_sections(
            [entry],
            definitions,
            {"SKIP_TAKEN": {}},
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["MISSING_DERIVED_LOGIC"],
        )

    def test_logic_sections_are_extracted_from_all_definitions(self) -> None:
        bold = chr(42) + chr(42)

        definitions = {
            "IR_INDIRECT": DefinitionBlock(
                signal_name="IR_INDIRECT",
                heading="IR_INDIRECT",
                source_path="docs/ir-derived-fields.md",
                start_line=20,
                lines=(
                    bold
                    + "Derivation:"
                    + bold
                    + " IR_INDIRECT = IR_IS_MRI AND IR[8]",
                ),
            ),
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=40,
                lines=(),
            ),
        }

        sections, diagnostics = extract_all_logic_sections(definitions)

        self.assertEqual(
            sections["IR_INDIRECT"]["derivation"].text,
            "IR_INDIRECT = IR_IS_MRI AND IR[8]",
        )
        self.assertEqual(sections["ACN"], {})
        self.assertEqual(diagnostics, [])

    def test_plural_constraints_are_extracted(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="FP_START",
            heading="FP_START",
            source_path="docs/external-inputs.md",
            start_line=20,
            lines=(
                bold + "Constraints:" + bold,
                "- meaningful only when RUN = 0",
                "- must be treated as a momentary command input",
                bold + "Consumed By:" + bold,
                "- run-state sequencing",
            ),
        )

        constraints, diagnostics = parse_definition_constraints(
            block
        )

        self.assertEqual(
            [constraint.text for constraint in constraints],
            [
                "meaningful only when RUN = 0",
                "must be treated as a momentary command input",
            ],
        )
        self.assertEqual(
            [constraint.line for constraint in constraints],
            [22, 23],
        )
        self.assertEqual(diagnostics, [])


    def test_singular_inline_constraint_is_extracted(
        self,
    ) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="IR_DF",
            heading="IR_DF",
            source_path="docs/ir-derived-fields.md",
            start_line=20,
            lines=(
                bold
                + "Constraint:"
                + bold
                + " IR_DF and IR_IF share the same bit positions.",
                bold + "Consumed By:" + bold,
            ),
        )

        constraints, diagnostics = parse_definition_constraints(
            block
        )

        self.assertEqual(
            [constraint.text for constraint in constraints],
            [
                "IR_DF and IR_IF share the same bit positions.",
            ],
        )
        self.assertEqual(constraints[0].line, 21)
        self.assertEqual(diagnostics, [])


    def test_definition_without_constraints_returns_empty_list(
        self,
    ) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="ACN",
            heading="ACN",
            source_path="docs/flags.md",
            start_line=20,
            lines=(
                bold
                + "Purpose:"
                + bold
                + " Indicates whether AC is negative.",
            ),
        )

        constraints, diagnostics = parse_definition_constraints(
            block
        )

        self.assertEqual(constraints, [])
        self.assertEqual(diagnostics, [])


    def test_constraints_are_extracted_from_all_definitions(
        self,
    ) -> None:
        bold = chr(42) + chr(42)

        definitions = {
            "FP_START": DefinitionBlock(
                signal_name="FP_START",
                heading="FP_START",
                source_path="docs/external-inputs.md",
                start_line=20,
                lines=(
                    bold + "Constraints:" + bold,
                    "- meaningful only when RUN = 0",
                ),
            ),
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=40,
                lines=(),
            ),
        }

        constraints, diagnostics = (
            extract_all_definition_constraints(
                definitions
            )
        )

        self.assertEqual(
            [
                constraint.text
                for constraint in constraints["FP_START"]
            ],
            [
                "meaningful only when RUN = 0",
            ],
        )
        self.assertEqual(constraints["ACN"], [])
        self.assertEqual(diagnostics, [])
        
    def test_multiline_prose_constraint_is_extracted(
        self,
    ) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="IR_DF",
            heading="IR_DF",
            source_path="docs/ir-derived-fields.md",
            start_line=20,
            lines=(
                bold + "Constraint:" + bold,
                "IR_DF and IR_IF share the same bit positions",
                "but are interpreted in different instruction contexts.",
                bold + "Consumed By:" + bold,
                "- field-transfer logic",
            ),
        )

        constraints, diagnostics = parse_definition_constraints(
            block
        )

        self.assertEqual(
            [constraint.text for constraint in constraints],
            [
                (
                    "IR_DF and IR_IF share the same bit positions "
                    "but are interpreted in different instruction "
                    "contexts."
                ),
            ],
        )
        self.assertEqual(constraints[0].line, 22)
        self.assertEqual(diagnostics, [])
    
    def test_linked_consumer_line_is_parsed(self) -> None:
        self.assertEqual(
            parse_consumer_line(
                "- [PC_INC]"
                "(../../03-microarchitecture/"
                "02-micro-operations.md#pc_inc)"
            ),
            (
                "PC_INC",
                (
                    "../../03-microarchitecture/"
                    "02-micro-operations.md#pc_inc"
                ),
            ),
        )


    def test_plain_text_consumer_line_is_parsed(self) -> None:
        self.assertEqual(
            parse_consumer_line(
                "- run-state sequencing"
            ),
            (
                "run-state sequencing",
                None,
            ),
        )


    def test_non_list_consumer_line_is_rejected(self) -> None:
        self.assertIsNone(
            parse_consumer_line(
                "run-state sequencing"
            )
        )


    def test_consumed_by_entries_are_extracted(self) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="FP_START",
            heading="FP_START",
            source_path="docs/external-inputs.md",
            start_line=20,
            lines=(
                bold + "Consumed By:" + bold,
                "- Control decision:",
                "- run-state sequencing",
                "- console execution control",
                bold + "Constraints:" + bold,
                "- meaningful only when RUN = 0",
            ),
        )

        consumers, diagnostics = parse_definition_consumers(
            block
        )

        self.assertEqual(
            [
                (consumer.text, consumer.target)
                for consumer in consumers
            ],
            [
                ("Control decision:", None),
                ("run-state sequencing", None),
                ("console execution control", None),
            ],
        )
        self.assertEqual(
            [consumer.line for consumer in consumers],
            [22, 23, 24],
        )
        self.assertEqual(diagnostics, [])


    def test_used_by_micro_operations_are_extracted(
        self,
    ) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="AUTO_INDEX_REQUIRED",
            heading="AUTO_INDEX_REQUIRED",
            source_path="docs/derived-flags.md",
            start_line=20,
            lines=(
                bold + "Used By μops:" + bold,
                (
                    "- [MB_INC]"
                    "(../../03-microarchitecture/"
                    "02-micro-operations.md#mb_inc)"
                ),
                (
                    "- [MEM_WRITE_FROM_MB]"
                    "(../../03-microarchitecture/"
                    "02-micro-operations.md#mem_write_from_mb)"
                ),
                "",
                "---",
            ),
        )

        consumers, diagnostics = parse_definition_consumers(
            block
        )

        self.assertEqual(
            [
                (consumer.text, consumer.target)
                for consumer in consumers
            ],
            [
                (
                    "MB_INC",
                    (
                        "../../03-microarchitecture/"
                        "02-micro-operations.md#mb_inc"
                    ),
                ),
                (
                    "MEM_WRITE_FROM_MB",
                    (
                        "../../03-microarchitecture/"
                        "02-micro-operations.md#mem_write_from_mb"
                    ),
                ),
            ],
        )
        self.assertEqual(diagnostics, [])


    def test_none_consumer_is_preserved_as_plain_text(
        self,
    ) -> None:
        bold = chr(42) + chr(42)

        block = DefinitionBlock(
            signal_name="INTERRUPT_REQUEST_VALID",
            heading="INTERRUPT_REQUEST_VALID",
            source_path="docs/derived-flags.md",
            start_line=20,
            lines=(
                bold + "Used By μops:" + bold,
                "- (none - used for MS transition control)",
            ),
        )

        consumers, diagnostics = parse_definition_consumers(
            block
        )

        self.assertEqual(
            [
                (consumer.text, consumer.target)
                for consumer in consumers
            ],
            [
                (
                    "(none - used for MS transition control)",
                    None,
                ),
            ],
        )
        self.assertEqual(diagnostics, [])


    def test_consumers_are_extracted_from_all_definitions(
        self,
    ) -> None:
        bold = chr(42) + chr(42)

        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=20,
                lines=(
                    bold + "Consumed By:" + bold,
                    "- skip logic",
                ),
            ),
            "FP_START": DefinitionBlock(
                signal_name="FP_START",
                heading="FP_START",
                source_path="docs/external-inputs.md",
                start_line=40,
                lines=(),
            ),
        }

        consumers, diagnostics = (
            extract_all_definition_consumers(
                definitions
            )
        )

        self.assertEqual(
            [
                consumer.text
                for consumer in consumers["ACN"]
            ],
            ["skip logic"],
        )
        self.assertEqual(consumers["FP_START"], [])
        self.assertEqual(diagnostics, [])
      
    def test_logic_assignment_is_detected(self) -> None:
        self.assertTrue(
            logic_assigns_signal(
                "SKIP_TAKEN = LOCAL_VALUE",
                "SKIP_TAKEN",
            )
        )


    def test_logic_assignment_accepts_identifiers_with_digits(
        self,
    ) -> None:
        self.assertTrue(
            logic_assigns_signal(
                (
                    "IR_OPR_GROUP1 = "
                    "IR_IS_OPR AND (IR[8] == 0)"
                ),
                "IR_OPR_GROUP1",
            )
        )


    def test_logic_assignment_rejects_different_result(
        self,
    ) -> None:
        self.assertFalse(
            logic_assigns_signal(
                "IR_OPR_GROUP2 = IR_IS_OPR AND IR[8]",
                "IR_OPR_GROUP1",
            )
        )


    def test_missing_value_encoding_is_reported(self) -> None:
        entry = IndexEntry(
            name="ACN",
            domain="Primitive Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_final_structure(
            [entry],
            definitions,
            {"ACN": {}},
            {"ACN": []},
            {"ACN": []},
            {
                "ACN": {
                    "value": "active-high",
                    "source": "defaulted",
                },
            },
            {"ACN": {}},
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["MISSING_VALUE_ENCODING"],
        )


    def test_mixed_value_encoding_is_reported(self) -> None:
        entry = IndexEntry(
            name="IR_ADDR",
            domain="IR-Derived Signals",
            category="Field Extraction Signals",
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path="docs/ir-derived-fields.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_final_structure(
            [entry],
            definitions,
            {
                "IR_ADDR": {
                    "mnemonic": "IR_ADDR",
                },
            },
            {
                "IR_ADDR": [
                    EnumeratedValue(
                        value="0000000",
                        meaning="zero",
                        line=30,
                    ),
                ],
            },
            {
                "IR_ADDR": [
                    ValueRange(
                        start="0000000",
                        end="1111111",
                        meaning="address field",
                        line=31,
                    ),
                ],
            },
            {
                "IR_ADDR": {
                    "value": "active-high",
                    "source": "defaulted",
                },
            },
            {
                "IR_ADDR": {
                    "derivation": TextSection(
                        text="IR_ADDR = IR[6:0]",
                        line=25,
                    ),
                },
            },
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["MIXED_VALUE_ENCODING"],
        )


    def test_mnemonic_mismatch_is_reported(self) -> None:
        entry = IndexEntry(
            name="IR_ADDR",
            domain="IR-Derived Signals",
            category="Field Extraction Signals",
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path="docs/ir-derived-fields.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_final_structure(
            [entry],
            definitions,
            {
                "IR_ADDR": {
                    "mnemonic": "IR_ADDRESS",
                },
            },
            {"IR_ADDR": []},
            {
                "IR_ADDR": [
                    ValueRange(
                        start="0000000",
                        end="1111111",
                        meaning="address field",
                        line=30,
                    ),
                ],
            },
            {
                "IR_ADDR": {
                    "value": "active-high",
                    "source": "defaulted",
                },
            },
            {
                "IR_ADDR": {
                    "derivation": TextSection(
                        text="IR_ADDR = IR[6:0]",
                        line=25,
                    ),
                },
            },
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["MNEMONIC_NAME_MISMATCH"],
        )


    def test_active_low_name_conflict_is_reported(self) -> None:
        entry = IndexEntry(
            name="/INT_REQ",
            domain="External Inputs",
            category="External Requests",
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "/INT_REQ": DefinitionBlock(
                signal_name="/INT_REQ",
                heading="/INT_REQ",
                source_path="docs/external-inputs.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_final_structure(
            [entry],
            definitions,
            {"/INT_REQ": {}},
            {
                "/INT_REQ": [
                    EnumeratedValue(
                        value="0",
                        meaning="request asserted",
                        line=30,
                    ),
                ],
            },
            {"/INT_REQ": []},
            {
                "/INT_REQ": {
                    "value": "active-high",
                    "source": "explicit",
                },
            },
            {"/INT_REQ": {}},
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["ACTIVE_LOW_NAME_CONFLICT"],
        )


    def test_ir_derivation_result_mismatch_is_reported(
        self,
    ) -> None:
        entry = IndexEntry(
            name="IR_ADDR",
            domain="IR-Derived Signals",
            category="Field Extraction Signals",
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "IR_ADDR": DefinitionBlock(
                signal_name="IR_ADDR",
                heading="IR_ADDR",
                source_path="docs/ir-derived-fields.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_final_structure(
            [entry],
            definitions,
            {
                "IR_ADDR": {
                    "mnemonic": "IR_ADDR",
                },
            },
            {"IR_ADDR": []},
            {
                "IR_ADDR": [
                    ValueRange(
                        start="0000000",
                        end="1111111",
                        meaning="address field",
                        line=30,
                    ),
                ],
            },
            {
                "IR_ADDR": {
                    "value": "active-high",
                    "source": "defaulted",
                },
            },
            {
                "IR_ADDR": {
                    "derivation": TextSection(
                        text="IR_ADDRESS = IR[6:0]",
                        line=25,
                    ),
                },
            },
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["DERIVATION_RESULT_MISMATCH"],
        )


    def test_internal_composition_final_result_is_accepted(
        self,
    ) -> None:
        entry = IndexEntry(
            name="SKIP_TAKEN",
            domain="Derived Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "SKIP_TAKEN": DefinitionBlock(
                signal_name="SKIP_TAKEN",
                heading="SKIP_TAKEN",
                source_path="docs/derived-flags.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_final_structure(
            [entry],
            definitions,
            {
                "SKIP_TAKEN": {
                    "mnemonic": "SKIP_TAKEN",
                },
            },
            {
                "SKIP_TAKEN": [
                    EnumeratedValue(
                        value="0",
                        meaning="no skip",
                        line=30,
                    ),
                    EnumeratedValue(
                        value="1",
                        meaning="skip",
                        line=31,
                    ),
                ],
            },
            {"SKIP_TAKEN": []},
            {
                "SKIP_TAKEN": {
                    "value": "active-high",
                    "source": "defaulted",
                },
            },
            {
                "SKIP_TAKEN": {
                    "internal_composition": TextSection(
                        text="\n".join(
                            [
                                "LOCAL_SKIP = ACN OR ACZ",
                                "SKIP_TAKEN = LOCAL_SKIP",
                            ]
                        ),
                        line=25,
                    ),
                },
            },
        )

        self.assertEqual(diagnostics, [])

    def test_extraction_report_contains_summary(
        self,
    ) -> None:
        entry = IndexEntry(
            name="ACN",
            domain="Primitive Flags",
            category=None,
            source_path="docs/index.md",
            line=10,
        )

        definitions = {
            "ACN": DefinitionBlock(
                signal_name="ACN",
                heading="ACN",
                source_path="docs/flags.md",
                start_line=20,
                lines=(),
            ),
        }

        report = build_extraction_report(
            entries=[entry],
            definitions=definitions,
            attributes={
                "ACN": {
                    "display_name": "AC Negative",
                    "purpose": "Indicates whether AC is negative.",
                    "source_register": "AC",
                },
            },
            bit_widths={
                "ACN": 1,
            },
            polarities={
                "ACN": {
                    "value": "active-high",
                    "source": "defaulted",
                },
            },
            enumerated_values={
                "ACN": [
                    EnumeratedValue(
                        value="0",
                        meaning="not negative",
                        line=30,
                    ),
                    EnumeratedValue(
                        value="1",
                        meaning="negative",
                        line=31,
                    ),
                ],
            },
            value_ranges={
                "ACN": [],
            },
            dependencies={
                "ACN": [],
            },
            logic_sections={
                "ACN": {},
            },
            constraints={
                "ACN": [],
            },
            consumers={
                "ACN": [],
            },
            diagnostics=[],
        )

        self.assertIn(
            "Indexed control inputs: 1",
            report,
        )
        self.assertIn(
            "Matched definitions: 1",
            report,
        )
        self.assertIn(
            "Primitive Flags: 1",
            report,
        )
        self.assertIn(
            "Enumerated values: 2",
            report,
        )
        self.assertIn(
            "No diagnostics.",
            report,
        )


    def test_extraction_report_contains_diagnostics(
        self,
    ) -> None:
        diagnostic = Diagnostic(
            severity="ERROR",
            code="TEST_ERROR",
            message="Test diagnostic message.",
            source_path="docs/test.md",
            line=42,
            signal_name="TEST_SIGNAL",
        )

        report = build_extraction_report(
            entries=[],
            definitions={},
            attributes={},
            bit_widths={},
            polarities={},
            enumerated_values={},
            value_ranges={},
            dependencies={},
            logic_sections={},
            constraints={},
            consumers={},
            diagnostics=[diagnostic],
        )

        self.assertIn(
            "ERROR: 1",
            report,
        )
        self.assertIn(
            "ERROR TEST_ERROR [TEST_SIGNAL]",
            report,
        )
        self.assertIn(
            "Source: docs/test.md:42",
            report,
        )
        self.assertIn(
            "Test diagnostic message.",
            report,
        )


    def test_text_report_is_written(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = (
                Path(temporary_directory)
                / "nested"
                / "extraction-report.txt"
            )

            write_text_report(
                "Test report\n",
                output_path,
            )

            self.assertEqual(
                output_path.read_text(
                    encoding="utf-8"
                ),
                "Test report\n",
            )
  
if __name__ == "__main__":
    unittest.main()