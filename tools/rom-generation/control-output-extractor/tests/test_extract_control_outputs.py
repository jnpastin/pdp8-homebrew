"""Tests for command-line parsing and path resolution."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
import json



SRC_DIRECTORY = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIRECTORY))

from extract_control_outputs import (  # noqa: E402
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    SOURCE_PATHS,
    read_document,
    read_source_documents,
    resolve_tool_paths,
    validate_source_paths,
    SourceDocument,
    build_index_result,
    parse_index,
    write_json_output,
    write_report,
    extract_definition_blocks,
    DefinitionBlock,
    find_signal_in_heading,
    match_definition_blocks,
    IndexEntry,
    parse_definition_attributes,
    extract_all_definition_attributes,
    validate_definition_attributes,
    EncodingEntry,
    extract_all_definition_encodings,
    parse_definition_encodings,
    parse_encoding_line,
    normalize_bit_widths,
    parse_bit_width,
    parse_octal_encoding,
    validate_encoding_widths,
    extract_all_definition_constraints,
    parse_definition_constraints,
    ConstraintEntry,
    normalize_signal_name,
    validate_documented_mnemonics,
    validate_category_requirements,
    main,
)

class ResolveToolPathsTests(unittest.TestCase):
    def test_default_paths_are_resolved_from_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)

            paths = resolve_tool_paths(repo_root)

            self.assertEqual(paths.repo_root, repo_root.resolve())
            self.assertEqual(
                paths.json_output,
                (repo_root / DEFAULT_JSON_OUTPUT).resolve(),
            )
            self.assertEqual(
                paths.report_output,
                (repo_root / DEFAULT_REPORT_OUTPUT).resolve(),
            )
            self.assertEqual(
                paths.source_paths,
                tuple((repo_root / path).resolve() for path in SOURCE_PATHS),
            )

    def test_absolute_output_paths_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as repository_directory:
            with tempfile.TemporaryDirectory() as output_directory:
                repo_root = Path(repository_directory)
                output_root = Path(output_directory)

                json_output = output_root / "control-outputs.json"
                report_output = output_root / "extraction-report.txt"

                paths = resolve_tool_paths(
                    repo_root,
                    json_output=json_output,
                    report_output=report_output,
                )

                self.assertEqual(
                    paths.json_output,
                    json_output.resolve(),
                )
                self.assertEqual(
                    paths.report_output,
                    report_output.resolve(),
                )

    def test_missing_repository_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_root = Path(temporary_directory) / "missing"

            with self.assertRaisesRegex(
                ValueError,
                "Repository root does not exist",
            ):
                resolve_tool_paths(missing_root)

class SourceValidationTests(unittest.TestCase):
    def test_existing_source_files_are_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first_path = root / "first.md"
            second_path = root / "second.md"

            first_path.write_text("# First\n", encoding="utf-8")
            second_path.write_text("# Second\n", encoding="utf-8")

            validate_source_paths((first_path, second_path))

    def test_missing_source_files_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.md"

            with self.assertRaisesRegex(
                FileNotFoundError,
                "Required source files are missing",
            ):
                validate_source_paths((missing_path,))


class DocumentLoadingTests(unittest.TestCase):
    def test_utf8_document_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "source.md"
            source_text = "# Control Output\n\nPurpose: test\n"

            source_path.write_text(source_text, encoding="utf-8")

            document = read_document(source_path)

            self.assertEqual(document.path, source_path)
            self.assertEqual(document.text, source_text)

    def test_invalid_utf8_document_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = Path(temporary_directory) / "source.md"
            source_path.write_bytes(b"\xff\xfe\xfa")

            with self.assertRaisesRegex(
                ValueError,
                "Source file is not valid UTF-8",
            ):
                read_document(source_path)

    def test_source_documents_preserve_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first_path = root / "first.md"
            second_path = root / "second.md"

            first_path.write_text("first", encoding="utf-8")
            second_path.write_text("second", encoding="utf-8")

            documents = read_source_documents(
                (first_path, second_path)
            )

            self.assertEqual(
                tuple(document.path for document in documents),
                (first_path, second_path),
            )
            self.assertEqual(
                tuple(document.text for document in documents),
                ("first", "second"),
            )

class IndexExtractionTests(unittest.TestCase):
    def test_signal_entries_are_extracted_from_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            index_path = repo_root / "docs/index.md"
            index_path.parent.mkdir(parents=True)

            index_text = (
                "### 3.1 Enable Signals\n"
                "- [AC\\_LOAD](./01-microarchitectural-control-signals.md#ac_load)\n"
                "- [PC\\_INC](./01-microarchitectural-control-signals.md#pc_inc)\n"
            )

            document = SourceDocument(
                path=index_path,
                text=index_text,
            )

            entries, diagnostics = parse_index(document, repo_root)

            self.assertEqual(
                [entry.name for entry in entries],
                ["AC_LOAD", "PC_INC"],
            )
            self.assertEqual(
                [entry.category for entry in entries],
                ["Enable Signals", "Enable Signals"],
            )
            self.assertEqual(diagnostics, [])

    def test_duplicate_index_entry_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            index_path = repo_root / "docs/index.md"
            index_path.parent.mkdir(parents=True)

            index_text = (
                "### 3.1 Enable Signals\n"
                "- [AC\\_LOAD](./01-microarchitectural-control-signals.md#ac_load)\n"
                "- [AC\\_LOAD](./01-microarchitectural-control-signals.md#ac_load)\n"
            )

            document = SourceDocument(
                path=index_path,
                text=index_text,
            )

            entries, diagnostics = parse_index(document, repo_root)

            self.assertEqual(len(entries), 1)
            self.assertEqual(len(diagnostics), 1)
            self.assertEqual(
                diagnostics[0].code,
                "DUPLICATE_INDEX_ENTRY",
            )

    def test_generated_outputs_are_written(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_root = Path(temporary_directory)
            json_path = output_root / "nested/control-outputs.json"
            report_path = output_root / "nested/extraction-report.txt"

            result = build_index_result(
                [],
                {},
                {},
                {},
                {},
                {},
                [],
            )

            write_json_output(result, json_path)
            write_report(
                [],
                {},
                {},
                {},
                {},
                {},
                [],
                report_path,
            )

            self.assertTrue(json_path.is_file())
            self.assertTrue(report_path.is_file())
            self.assertIn(
                '"extraction_stage": "category-validation"',
                json_path.read_text(encoding="utf-8"),
            )
            self.assertIn(
                "Indexed signals: 0",
                report_path.read_text(encoding="utf-8"),
            )
            
    def test_numbered_category_headings_are_extracted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            index_path = repo_root / "docs/index.md"
            index_path.parent.mkdir(parents=True)

            index_text = (
                "### 3.1 Enable Signals\n"
                "- [AC\\_LOAD]"
                "(./01-microarchitectural-control-signals.md#ac_load)\n"
                "### 3.2 Select Signals\n"
                "- [AC\\_SRC]"
                "(./01-microarchitectural-control-signals.md#ac_src)\n"
            )

            document = SourceDocument(
                path=index_path,
                text=index_text,
            )

            entries, diagnostics = parse_index(document, repo_root)

            self.assertEqual(
                [entry.category for entry in entries],
                ["Enable Signals", "Select Signals"],
            )
            self.assertEqual(diagnostics, [])
        
    def test_definition_section_is_split_into_signal_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            source_path = repo_root / "docs/signals.md"
            source_path.parent.mkdir(parents=True)

            document = SourceDocument(
                path=source_path,
                text=(
                    "# Control Signals\n"
                    "\n"
                    "## 4. Signal Definitions\n"
                    "\n"
                    "### 4.1 Accumulator Load (AC\\_LOAD)\n"
                    "\n"
                    "**Name:** AC_LOAD\n"
                    "\n"
                    "### 4.2 Program Counter Load (PC\\_LOAD)\n"
                    "\n"
                    "**Name:** PC_LOAD\n"
                    "\n"
                    "## 5. Interaction Rules\n"
                    "\n"
                    "Not part of a signal definition.\n"
                ),
            )

            blocks = extract_definition_blocks(document, repo_root)

            self.assertEqual(len(blocks), 2)
            self.assertEqual(
                [block.heading for block in blocks],
                [
                    "Accumulator Load (AC_LOAD)",
                    "Program Counter Load (PC_LOAD)",
                ],
            )
            self.assertEqual(
                [block.start_line for block in blocks],
                [5, 9],
            )
            self.assertIn("**Name:** AC_LOAD", blocks[0].lines)
            self.assertNotIn(
                "Not part of a signal definition.",
                blocks[1].lines,
            )
        
    def test_signal_name_is_found_in_definition_heading(self) -> None:
        indexed_names = {"AC_LOAD", "PC_LOAD", "MS_NEXT"}

        self.assertEqual(
            find_signal_in_heading(
                "Accumulator Load (AC_LOAD)",
                indexed_names,
            ),
            "AC_LOAD",
        )

        self.assertEqual(
            find_signal_in_heading(
                "Next Major State (MS_NEXT)",
                indexed_names,
            ),
            "MS_NEXT",
        )


    def test_definition_blocks_are_matched_to_index_entries(self) -> None:
        entries = [
            IndexEntry(
                name="AC_LOAD",
                category="Enable Signals",
                source_path="docs/index.md",
                line=10,
            ),
            IndexEntry(
                name="PC_LOAD",
                category="Enable Signals",
                source_path="docs/index.md",
                line=11,
            ),
        ]

        blocks = [
            DefinitionBlock(
                heading="Accumulator Load (AC_LOAD)",
                source_path="docs/signals.md",
                start_line=20,
                lines=("**Name:** Accumulator Load",),
            ),
            DefinitionBlock(
                heading="Program Counter Load (PC_LOAD)",
                source_path="docs/signals.md",
                start_line=30,
                lines=("**Name:** Program Counter Load",),
            ),
        ]

        definitions, diagnostics = match_definition_blocks(
            entries,
            blocks,
        )

        self.assertEqual(
            set(definitions),
            {"AC_LOAD", "PC_LOAD"},
        )
        self.assertEqual(diagnostics, [])


    def test_missing_definition_is_reported(self) -> None:
        entries = [
            IndexEntry(
                name="AC_LOAD",
                category="Enable Signals",
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
        self.assertEqual(
            diagnostics[0].signal_name,
            "AC_LOAD",
        )


    def test_unindexed_definition_is_reported(self) -> None:
        blocks = [
            DefinitionBlock(
                heading="Unknown Signal (UNKNOWN_SIGNAL)",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        ]

        definitions, diagnostics = match_definition_blocks(
            [],
            blocks,
        )

        self.assertEqual(definitions, {})
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "UNINDEXED_DEFINITION",
        )


    def test_duplicate_definition_is_reported(self) -> None:
        entries = [
            IndexEntry(
                name="AC_LOAD",
                category="Enable Signals",
                source_path="docs/index.md",
                line=10,
            ),
        ]

        blocks = [
            DefinitionBlock(
                heading="Accumulator Load (AC_LOAD)",
                source_path="docs/first.md",
                start_line=20,
                lines=(),
            ),
            DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/second.md",
                start_line=30,
                lines=(),
            ),
        ]

        definitions, diagnostics = match_definition_blocks(
            entries,
            blocks,
        )

        self.assertEqual(set(definitions), {"AC_LOAD"})
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "DUPLICATE_DEFINITION",
        )
    
    def test_definition_section_accepts_numbered_and_unescaped_headings(self,) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            source_path = repo_root / "docs/signals.md"
            source_path.parent.mkdir(parents=True)

            document = SourceDocument(
                path=source_path,
                text=(
                    "## 5. Signal Definitions\n"
                    "\n"
                    "### 5.1 AC_LOAD\n"
                    "\n"
                    "**Name:** Accumulator Load\n"
                    "\n"
                    "### 5.2 Program Counter Load (PC_LOAD)\n"
                    "\n"
                    "**Name:** Program Counter Load\n"
                    "\n"
                    "## 6. Global Constraints\n"
                ),
            )

            blocks = extract_definition_blocks(document, repo_root)

            self.assertEqual(
                [block.heading for block in blocks],
                [
                    "AC_LOAD",
                    "Program Counter Load (PC_LOAD)",
                ],
            )
            
    def test_bus_names_with_brackets_are_extracted_from_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            index_path = repo_root / "docs/index.md"
            index_path.parent.mkdir(parents=True)

            document = SourceDocument(
                path=index_path,
                text=(
                    "### 4.2 I/O Interface\n"
                    "- [IOA\\[5:0\\]]"
                    "(./02-architectural-control-signals.md#ioa)\n"
                    "- [IOP\\[2:0\\]]"
                    "(./02-architectural-control-signals.md#iop)\n"
                ),
            )

            entries, diagnostics = parse_index(document, repo_root)

            self.assertEqual(
                [entry.name for entry in entries],
                ["IOA[5:0]", "IOP[2:0]"],
            )
            self.assertEqual(diagnostics, [])
            
    def test_bus_names_with_brackets_are_extracted_from_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            index_path = repo_root / "docs/index.md"
            index_path.parent.mkdir(parents=True)

            document = SourceDocument(
                path=index_path,
                text=(
                    "### 4.2 I/O Interface\n"
                    "- [IOA\\[5:0\\]]"
                    "(./02-architectural-control-signals.md#ioa)\n"
                    "- [IOP\\[2:0\\]]"
                    "(./02-architectural-control-signals.md#iop)\n"
                ),
            )

            entries, diagnostics = parse_index(document, repo_root)

            self.assertEqual(
                [entry.name for entry in entries],
                ["IOA[5:0]", "IOP[2:0]"],
            )
            self.assertEqual(diagnostics, [])    
    
    def test_scalar_definition_attributes_are_extracted(self) -> None:
        block = DefinitionBlock(
            heading="AC_LOAD",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "",
                "**Mnemonic:** AC_LOAD",
                "**Name:** Accumulator Load",
                "**Class:** Enable",
                "**Bit Width:** 1",
                "**Polarity:** Active-high",
                "**Purpose:** Loads the accumulator.",
            ),
        )

        attributes, diagnostics = parse_definition_attributes(
            "AC_LOAD",
            block,
        )

        self.assertEqual(
            attributes,
            {
                "mnemonic": "AC_LOAD",
                "display_name": "Accumulator Load",
                "signal_class": "Enable",
                "bit_width": "1",
                "polarity": "Active-high",
                "purpose": "Loads the accumulator.",
            },
        )
        self.assertEqual(diagnostics, [])


    def test_attribute_labels_without_colons_are_accepted(self) -> None:
        block = DefinitionBlock(
            heading="MS_NEXT",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "**Name** MS_NEXT",
                "**Type** Encoded field",
                "**Domain** Sequencing",
                "**Width** 3 bits",
            ),
        )

        attributes, diagnostics = parse_definition_attributes(
            "MS_NEXT",
            block,
        )

        self.assertEqual(
            attributes,
            {
                "display_name": "MS_NEXT",
                "signal_type": "Encoded field",
                "domain": "Sequencing",
                "bit_width": "3 bits",
            },
        )
        self.assertEqual(diagnostics, [])


    def test_duplicate_attribute_is_reported(self) -> None:
        block = DefinitionBlock(
            heading="AC_LOAD",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "**Name:** Accumulator Load",
                "**Name:** AC Load",
            ),
        )

        attributes, diagnostics = parse_definition_attributes(
            "AC_LOAD",
            block,
        )

        self.assertEqual(
            attributes["display_name"],
            "Accumulator Load",
        )
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "DUPLICATE_ATTRIBUTE",
        )
    
    def test_attributes_are_extracted_from_all_definitions(self) -> None:
        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(
                    "**Mnemonic:** AC_LOAD",
                    "**Class:** Enable",
                    "**Bit Width:** 1",
                ),
            ),
            "MS_NEXT": DefinitionBlock(
                heading="Next Major State (MS_NEXT)",
                source_path="docs/sequencing.md",
                start_line=40,
                lines=(
                    "**Name:** MS_NEXT",
                    "**Type:** Encoded field",
                    "**Width:** 3 bits",
                ),
            ),
        }

        attributes, diagnostics = extract_all_definition_attributes(
            definitions
        )

        self.assertEqual(
            attributes["AC_LOAD"],
            {
                "mnemonic": "AC_LOAD",
                "signal_class": "Enable",
                "bit_width": "1",
            },
        )
        self.assertEqual(
            attributes["MS_NEXT"],
            {
                "display_name": "MS_NEXT",
                "signal_type": "Encoded field",
                "bit_width": "3 bits",
            },
        )
        self.assertEqual(diagnostics, [])
    
    def test_missing_required_attributes_are_reported(self) -> None:
        entries = [
            IndexEntry(
                name="AC_LOAD",
                category="Enable Signals",
                source_path="docs/index.md",
                line=10,
            ),
        ]

        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_definition_attributes(
            entries,
            definitions,
            {"AC_LOAD": {}},
        )

        self.assertEqual(
            {diagnostic.code for diagnostic in diagnostics},
            {
                "MISSING_BIT_WIDTH",
                "MISSING_DESCRIPTION",
            },
        )


    def test_purpose_satisfies_description_requirement(self) -> None:
        entries = [
            IndexEntry(
                name="AC_LOAD",
                category="Enable Signals",
                source_path="docs/index.md",
                line=10,
            ),
        ]

        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_definition_attributes(
            entries,
            definitions,
            {
                "AC_LOAD": {
                    "bit_width": "1",
                    "purpose": "Loads the accumulator.",
                }
            },
        )

        self.assertEqual(diagnostics, [])
    
    def test_encoding_line_formats_are_parsed(self) -> None:
        self.assertEqual(
            parse_encoding_line("0 -> no load"),
            ("0", "no load"),
        )
        self.assertEqual(
            parse_encoding_line("- 1: load"),
            ("1", "load"),
        )
        self.assertEqual(
            parse_encoding_line("2 → EXECUTE"),
            ("2", "EXECUTE"),
        )


    def test_definition_encodings_are_extracted(self) -> None:
        block = DefinitionBlock(
            heading="AC_LOAD",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "**Mnemonic:** AC_LOAD",
                "**Encoding:**",
                "- 0: no load",
                "- 1: load",
                "**Constraints:**",
                "- Requires a valid source.",
            ),
        )

        encodings, diagnostics = parse_definition_encodings(
            "AC_LOAD",
            block,
        )

        self.assertEqual(
            [(entry.value, entry.meaning) for entry in encodings],
            [
                ("0", "no load"),
                ("1", "load"),
            ],
        )
        self.assertEqual(diagnostics, [])


    def test_value_encoding_label_is_accepted(self) -> None:
        block = DefinitionBlock(
            heading="MS_NEXT",
            source_path="docs/sequencing.md",
            start_line=40,
            lines=(
                "**Value Encoding:**",
                "0 -> FETCH",
                "1 -> DEFER",
                "2 -> EXECUTE",
                "**Behavior:**",
                "- Committed at TP4.",
            ),
        )

        encodings, diagnostics = parse_definition_encodings(
            "MS_NEXT",
            block,
        )

        self.assertEqual(
            [(entry.value, entry.meaning) for entry in encodings],
            [
                ("0", "FETCH"),
                ("1", "DEFER"),
                ("2", "EXECUTE"),
            ],
        )
        self.assertEqual(diagnostics, [])


    def test_duplicate_encoding_value_is_reported(self) -> None:
        block = DefinitionBlock(
            heading="AC_LOAD",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "**Encoding:**",
                "0 -> no load",
                "0 -> inactive",
            ),
        )

        encodings, diagnostics = parse_definition_encodings(
            "AC_LOAD",
            block,
        )

        self.assertEqual(len(encodings), 2)
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "DUPLICATE_ENCODING_VALUE",
        )
    
    def test_code_fences_and_equals_encodings_are_supported(self) -> None:
        block = DefinitionBlock(
            heading="IOT_TRANSFER_VAL",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "**Encoding:**",
                "```text",
                "00 = no pending transfer",
                "01 = pending read",
                "10 = pending write",
                "11 = invalid",
                "```",
                "**Constraints:**",
            ),
        )

        encodings, diagnostics = parse_definition_encodings(
            "IOT_TRANSFER_VAL",
            block,
        )

        self.assertEqual(
            [(entry.value, entry.meaning) for entry in encodings],
            [
                ("00", "no pending transfer"),
                ("01", "pending read"),
                ("10", "pending write"),
                ("11", "invalid"),
            ],
        )
        self.assertEqual(diagnostics, [])
        
    def test_bit_width_formats_are_normalized(self) -> None:
        self.assertEqual(parse_bit_width("1"), 1)
        self.assertEqual(parse_bit_width("1 bit"), 1)
        self.assertEqual(parse_bit_width("3 bits"), 3)
        self.assertEqual(parse_bit_width(" 12 bits "), 12)


    def test_invalid_bit_width_is_rejected(self) -> None:
        self.assertIsNone(parse_bit_width("zero"))
        self.assertIsNone(parse_bit_width("0"))
        self.assertIsNone(parse_bit_width("3 bytes"))


    def test_all_bit_widths_are_normalized(self) -> None:
        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
            "MS_NEXT": DefinitionBlock(
                heading="MS_NEXT",
                source_path="docs/sequencing.md",
                start_line=40,
                lines=(),
            ),
        }

        attributes = {
            "AC_LOAD": {
                "bit_width": "1",
            },
            "MS_NEXT": {
                "bit_width": "3 bits",
            },
        }

        bit_widths, diagnostics = normalize_bit_widths(
            definitions,
            attributes,
        )

        self.assertEqual(
            bit_widths,
            {
                "AC_LOAD": 1,
                "MS_NEXT": 3,
            },
        )
        self.assertEqual(diagnostics, [])


    def test_invalid_documented_bit_width_is_reported(self) -> None:
        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        attributes = {
            "AC_LOAD": {
                "bit_width": "one bit",
            },
        }

        bit_widths, diagnostics = normalize_bit_widths(
            definitions,
            attributes,
        )

        self.assertEqual(bit_widths, {})
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "INVALID_BIT_WIDTH",
        )
    
    def test_octal_encoding_values_are_parsed(self) -> None:
        self.assertEqual(parse_octal_encoding("0"), 0)
        self.assertEqual(parse_octal_encoding("07"), 7)
        self.assertEqual(parse_octal_encoding("10"), 8)
        self.assertEqual(parse_octal_encoding("17"), 15)


    def test_invalid_octal_encoding_is_rejected(self) -> None:
        self.assertIsNone(parse_octal_encoding("08"))
        self.assertIsNone(parse_octal_encoding("1A"))
        self.assertIsNone(parse_octal_encoding(""))
        self.assertIsNone(parse_octal_encoding("-1"))


    def test_encodings_that_fit_bit_width_are_accepted(self) -> None:
        definitions = {
            "ALU_OP": DefinitionBlock(
                heading="ALU_OP",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        bit_widths = {
            "ALU_OP": 4,
        }

        encodings = {
            "ALU_OP": [
                EncodingEntry(
                    value="00",
                    meaning="ADD",
                    line=30,
                ),
                EncodingEntry(
                    value="17",
                    meaning="reserved",
                    line=31,
                ),
            ],
        }

        diagnostics = validate_encoding_widths(
            definitions,
            bit_widths,
            encodings,
        )

        self.assertEqual(diagnostics, [])


    def test_encoding_that_exceeds_bit_width_is_reported(self) -> None:
        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        bit_widths = {
            "AC_LOAD": 1,
        }

        encodings = {
            "AC_LOAD": [
                EncodingEntry(
                    value="2",
                    meaning="invalid test value",
                    line=30,
                ),
            ],
        }

        diagnostics = validate_encoding_widths(
            definitions,
            bit_widths,
            encodings,
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "ENCODING_EXCEEDS_BIT_WIDTH",
        )


    def test_non_octal_encoding_is_reported(self) -> None:
        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        bit_widths = {
            "AC_LOAD": 1,
        }

        encodings = {
            "AC_LOAD": [
                EncodingEntry(
                    value="8",
                    meaning="invalid test value",
                    line=30,
                ),
            ],
        }

        diagnostics = validate_encoding_widths(
            definitions,
            bit_widths,
            encodings,
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "INVALID_OCTAL_ENCODING",
        )
        
    def test_definition_constraints_are_extracted(self) -> None:
        block = DefinitionBlock(
            heading="PC_LOAD",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "**Encoding:**",
                "0 = no load",
                "1 = load",
                "**Constraints:**",
                "- Must not be asserted with PC_INC.",
                "- Requires a valid source.",
                "**Used By:**",
                "- PC_LOAD_EA_ADDR",
            ),
        )

        constraints = parse_definition_constraints(block)

        self.assertEqual(
            [constraint.text for constraint in constraints],
            [
                "Must not be asserted with PC_INC.",
                "Requires a valid source.",
            ],
        )


    def test_missing_constraints_produce_an_empty_list(self) -> None:
        block = DefinitionBlock(
            heading="PC_LOAD",
            source_path="docs/signals.md",
            start_line=20,
            lines=(
                "**Encoding:**",
                "0 = no load",
                "1 = load",
            ),
        )

        self.assertEqual(
            parse_definition_constraints(block),
            [],
        )


    def test_constraints_are_extracted_from_all_definitions(self) -> None:
        definitions = {
            "PC_LOAD": DefinitionBlock(
                heading="PC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(
                    "**Constraints:**",
                    "- Must not be asserted with PC_INC.",
                ),
            ),
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=40,
                lines=(),
            ),
        }

        constraints = extract_all_definition_constraints(definitions)

        self.assertEqual(
            [constraint.text for constraint in constraints["PC_LOAD"]],
            ["Must not be asserted with PC_INC."],
        )
        self.assertEqual(constraints["AC_LOAD"], [])
    
    def test_markdown_signal_formatting_is_normalized(self) -> None:
        self.assertEqual(
            normalize_signal_name(r"`IOT\_TRANSFER\_VAL`"),
            "IOT_TRANSFER_VAL",
        )
        self.assertEqual(
            normalize_signal_name(r"`IOP\[2:0\]`"),
            "IOP[2:0]",
        )
    
    def test_matching_documented_mnemonic_is_accepted(self) -> None:
        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_documented_mnemonics(
            definitions,
            {
                "AC_LOAD": {
                    "mnemonic": "AC_LOAD",
                }
            },
        )

        self.assertEqual(diagnostics, [])


    def test_mismatched_documented_mnemonic_is_reported(self) -> None:
        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_documented_mnemonics(
            definitions,
            {
                "AC_LOAD": {
                    "mnemonic": "PC_LOAD",
                }
            },
        )

        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            diagnostics[0].code,
            "MNEMONIC_MISMATCH",
        )


    def test_missing_documented_mnemonic_is_allowed(self) -> None:
        definitions = {
            "/RD": DefinitionBlock(
                heading="Memory Read (/RD)",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_documented_mnemonics(
            definitions,
            {
                "/RD": {
                    "description": "Requests a memory read.",
                }
            },
        )

        self.assertEqual(diagnostics, [])
    
    def test_valid_category_requirements_are_accepted(self) -> None:
        entries = [
            IndexEntry(
                name="AC_LOAD",
                category="Enable Signals",
                source_path="docs/index.md",
                line=10,
            ),
        ]

        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        bit_widths = {
            "AC_LOAD": 1,
        }

        encodings = {
            "AC_LOAD": [
                EncodingEntry(
                    value="0",
                    meaning="no load",
                    line=30,
                ),
                EncodingEntry(
                    value="1",
                    meaning="load",
                    line=31,
                ),
            ],
        }

        diagnostics = validate_category_requirements(
            entries,
            definitions,
            bit_widths,
            encodings,
        )

        self.assertEqual(diagnostics, [])


    def test_invalid_enable_width_is_reported(self) -> None:
        entries = [
            IndexEntry(
                name="AC_LOAD",
                category="Enable Signals",
                source_path="docs/index.md",
                line=10,
            ),
        ]

        definitions = {
            "AC_LOAD": DefinitionBlock(
                heading="AC_LOAD",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        diagnostics = validate_category_requirements(
            entries,
            definitions,
            {"AC_LOAD": 2},
            {
                "AC_LOAD": [
                    EncodingEntry(
                        value="0",
                        meaning="no load",
                        line=30,
                    ),
                ],
            },
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["INVALID_ENABLE_WIDTH"],
        )


    def test_missing_required_encodings_are_reported(self) -> None:
        entries = [
            IndexEntry(
                name="AC_SRC",
                category="Select Signals",
                source_path="docs/index.md",
                line=10,
            ),
        ]

        definitions = {
            "AC_SRC": DefinitionBlock(
                heading="AC_SRC",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        bit_widths = {
            "AC_SRC": 3,
        }

        encodings = {
            "AC_SRC": [],
        }

        diagnostics = validate_category_requirements(
            entries,
            definitions,
            bit_widths,
            encodings,
        )

        self.assertEqual(
            [diagnostic.code for diagnostic in diagnostics],
            ["MISSING_ENUMERATED_ENCODINGS"],
        )
    
    def test_data_value_may_omit_enumerated_encodings(self) -> None:
        entries = [
            IndexEntry(
                name="PC_VAL",
                category="Data Value Signals",
                source_path="docs/index.md",
                line=10,
            ),
        ]

        definitions = {
            "PC_VAL": DefinitionBlock(
                heading="PC_VAL",
                source_path="docs/signals.md",
                start_line=20,
                lines=(),
            ),
        }

        bit_widths = {
            "PC_VAL": 12,
        }

        encodings = {
            "PC_VAL": [],
        }

        diagnostics = validate_category_requirements(
            entries,
            definitions,
            bit_widths,
            encodings,
        )

        self.assertEqual(diagnostics, [])
        
        
        
        
    class EndToEndTests(unittest.TestCase):
        def test_main_generates_json_and_report(self) -> None:
            with tempfile.TemporaryDirectory() as temporary_directory:
                repo_root = Path(temporary_directory)

                source_directory = (
                    repo_root
                    / "docs"
                    / "04-control"
                    / "20-control-output-definitions"
                )
                source_directory.mkdir(parents=True)

                index_path = source_directory / "00-index.md"
                microarchitecture_path = (
                    source_directory
                    / "01-microarchitectural-control-signals.md"
                )
                architecture_path = (
                    source_directory
                    / "02-architectural-control-signals.md"
                )
                sequencing_path = (
                    source_directory
                    / "03-sequencing-control-signals.md"
                )

                index_path.write_text(
                    "### 3.1 Enable Signals\n"
                    "- [AC\\_LOAD]"
                    "(./01-microarchitectural-control-signals.md#ac_load)\n",
                    encoding="utf-8",
                )

                microarchitecture_path.write_text(
                    "## 5. Signal Definitions\n"
                    "\n"
                    "### AC_LOAD\n"
                    "\n"
                    "**Mnemonic:** AC_LOAD\n"
                    "**Name:** Accumulator Load\n"
                    "**Class:** Enable\n"
                    "**Bit Width:** 1\n"
                    "**Purpose:** Loads the accumulator.\n"
                    "**Encoding:**\n"
                    "0 = no load\n"
                    "1 = load\n"
                    "**Constraints:**\n"
                    "- Requires a valid accumulator input.\n",
                    encoding="utf-8",
                )

                architecture_path.write_text(
                    "## 4. Signal Definitions\n",
                    encoding="utf-8",
                )

                sequencing_path.write_text(
                    "## 4. Signal Definitions\n",
                    encoding="utf-8",
                )

                exit_status = main(
                    [
                        "--repo-root",
                        str(repo_root),
                    ]
                )

                json_path = (
                    repo_root
                    / "build"
                    / "simulation_outputs"
                    / "rom-generation"
                    / "control-output-extractor"
                    / "control-outputs.json"
                )
                report_path = (
                    repo_root
                    / "build"
                    / "simulation_outputs"
                    / "rom-generation"
                    / "control-output-extractor"
                    / "extraction-report.txt"
                )

                self.assertEqual(exit_status, 0)
                self.assertTrue(json_path.is_file())
                self.assertTrue(report_path.is_file())

                generated_json = json.loads(
                    json_path.read_text(encoding="utf-8")
                )
                generated_report = report_path.read_text(
                    encoding="utf-8"
                )

                self.assertEqual(
                    generated_json["extraction_stage"],
                    "category-validation",
                )
                self.assertEqual(
                    len(generated_json["signals"]),
                    1,
                )
                self.assertEqual(
                    generated_json["signals"][0]["name"],
                    "AC_LOAD",
                )
                self.assertEqual(
                    generated_json["signals"][0]["definition"]["bit_width"],
                    1,
                )
                self.assertEqual(
                    generated_json["diagnostics"],
                    [],
                )
                self.assertIn(
                    "Indexed signals: 1",
                    generated_report,
                )
                self.assertIn(
                    "Errors: 0",
                    generated_report,
                )
            
if __name__ == "__main__":
    unittest.main()