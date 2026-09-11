"""Tests for the control-word schema generator."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from typing import Any


GENERATOR_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "generate_control_word_schema.py"
)


def load_generator_module() -> ModuleType:
    """Load the generator source without requiring a Python package."""

    specification = importlib.util.spec_from_file_location(
        "generate_control_word_schema",
        GENERATOR_PATH,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError(
            f"Unable to load generator module from {GENERATOR_PATH}"
        )

    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)

    return module


generator = load_generator_module()


def source(path: str, line: int) -> dict[str, Any]:
    """Create one representative extractor source reference."""

    return {
        "path": path,
        "line": line,
    }


def encoding(
    value: str,
    meaning: str,
    line: int,
) -> dict[str, Any]:
    """Create one representative extractor encoding."""

    return {
        "value": value,
        "meaning": meaning,
        "source": source(
            "docs/04-control/20-control-output-definitions/"
            "01-microarchitectural-control-signals.md",
            line,
        ),
    }


def representative_signal(
    *,
    name: str = "AC_LOAD",
    category: str = "Enable Signals",
    bit_width: int = 1,
) -> dict[str, Any]:
    """Create one representative validated extractor signal."""

    return {
        "name": name,
        "category": category,
        "source": source(
            "docs/04-control/20-control-output-definitions/00-index.md",
            36,
        ),
        "extraction_status": "category-validated",
        "definition": {
            "heading": name,
            "attributes": {
                "display_name": "Accumulator Load",
                "mnemonic": name,
                "purpose": "Load AC at TP.",
                "signal_class": "Enable",
                "default_value": "0",
                "explicit_value_required": "Yes",
                "value_required_when": "Always",                
            },
            "bit_width": bit_width,
            "encodings": [
                encoding("0", "no load", 361),
                encoding("1", "load", 362),
            ],
            "constraints": [
                {
                    "text": "Representative constraint",
                    "source": source(
                        "docs/04-control/20-control-output-definitions/"
                        "01-microarchitectural-control-signals.md",
                        365,
                    ),
                }
            ],
            "source": source(
                "docs/04-control/20-control-output-definitions/"
                "01-microarchitectural-control-signals.md",
                350,
            ),
        },
    }


def representative_input(
    signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create one representative extractor result."""

    return {
        "format_version": 1,
        "extraction_stage": "category-validation",
        "diagnostics": [],
        "signals": (
            signals
            if signals is not None
            else [representative_signal()]
        ),
    }

def representative_maintained_schema(
    fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Create one representative maintained control-word schema."""

    return {
        "specification_type": "control-word-schema",
        "schema_version": 1,
        "control_design_version": "v1",
        "fields": (
            fields
            if fields is not None
            else [
                {
                    "name": "AC_LOAD",
                    "control_word_role": "encoded",
                }
            ]
        ),
    }

class PathResolutionTests(unittest.TestCase):
    """Tests for repository-relative path handling."""

    def test_relative_path_is_resolved_from_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()
            relative_path = Path("build/input.json")

            self.assertEqual(
                generator.resolve_from_repo(repo_root, relative_path),
                (repo_root / relative_path).resolve(),
            )

    def test_absolute_path_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            absolute_path = (
                Path(temporary_directory).resolve()
                / "control-outputs.json"
            )

            self.assertEqual(
                generator.resolve_from_repo(
                    Path("/unused"),
                    absolute_path,
                ),
                absolute_path,
            )


class InputLoadingTests(unittest.TestCase):
    """Tests for loading extractor JSON."""

    def test_valid_json_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "input.json"
            expected = representative_input()

            input_path.write_text(
                json.dumps(expected),
                encoding="utf-8",
            )

            self.assertEqual(
                generator.read_json_input(input_path),
                expected,
            )

    def test_missing_input_raises_generation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "missing.json"

            with self.assertRaises(generator.GenerationFailure):
                generator.read_json_input(input_path)

    def test_invalid_json_raises_generation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "input.json"
            input_path.write_text("{", encoding="utf-8")

            with self.assertRaises(generator.GenerationFailure):
                generator.read_json_input(input_path)

    def test_non_object_json_raises_generation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = Path(temporary_directory) / "input.json"
            input_path.write_text("[]", encoding="utf-8")

            with self.assertRaises(generator.GenerationFailure):
                generator.read_json_input(input_path)

class MaintainedSchemaLoadingTests(unittest.TestCase):
    """Tests for optional maintained-schema loading."""

    def test_missing_schema_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            schema_path = Path(temporary_directory) / "missing.json"

            self.assertIsNone(
                generator.read_maintained_schema(schema_path)
            )

    def test_empty_schema_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            schema_path = Path(temporary_directory) / "schema.json"
            schema_path.write_text("", encoding="utf-8")

            self.assertIsNone(
                generator.read_maintained_schema(schema_path)
            )

    def test_whitespace_only_schema_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            schema_path = Path(temporary_directory) / "schema.json"
            schema_path.write_text(
                "  \n\t",
                encoding="utf-8",
            )

            self.assertIsNone(
                generator.read_maintained_schema(schema_path)
            )

    def test_valid_schema_is_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            schema_path = Path(temporary_directory) / "schema.json"
            expected = representative_maintained_schema()

            schema_path.write_text(
                json.dumps(expected),
                encoding="utf-8",
            )

            self.assertEqual(
                generator.read_maintained_schema(schema_path),
                expected,
            )

    def test_invalid_json_raises_generation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            schema_path = Path(temporary_directory) / "schema.json"
            schema_path.write_text("{", encoding="utf-8")

            with self.assertRaises(generator.GenerationFailure):
                generator.read_maintained_schema(schema_path)

class TopLevelValidationTests(unittest.TestCase):
    """Tests for extractor-result validation."""

    def test_representative_input_has_no_top_level_errors(self) -> None:
        diagnostics = generator.validate_top_level(
            representative_input()
        )

        self.assertEqual(diagnostics, [])

    def test_unsupported_format_version_is_reported(self) -> None:
        input_data = representative_input()
        input_data["format_version"] = 2

        diagnostics = generator.validate_top_level(input_data)

        self.assertIn(
            "UNSUPPORTED_FORMAT_VERSION",
            [item.code for item in diagnostics],
        )

    def test_wrong_extraction_stage_is_reported(self) -> None:
        input_data = representative_input()
        input_data["extraction_stage"] = "definition-extraction"

        diagnostics = generator.validate_top_level(input_data)

        self.assertIn(
            "UNSUPPORTED_EXTRACTION_STAGE",
            [item.code for item in diagnostics],
        )

    def test_extractor_diagnostics_are_rejected(self) -> None:
        input_data = representative_input()
        input_data["diagnostics"] = [
            {
                "severity": "ERROR",
                "code": "EXAMPLE",
                "message": "Representative extractor error.",
            }
        ]

        diagnostics = generator.validate_top_level(input_data)

        self.assertIn(
            "EXTRACTOR_DIAGNOSTICS_PRESENT",
            [item.code for item in diagnostics],
        )

    def test_missing_signals_array_is_reported(self) -> None:
        input_data = representative_input()
        del input_data["signals"]

        diagnostics = generator.validate_top_level(input_data)

        self.assertIn(
            "INVALID_SIGNALS",
            [item.code for item in diagnostics],
        )

class MaintainedSchemaValidationTests(unittest.TestCase):
    """Tests for maintained control-word role validation."""

    def test_missing_schema_is_valid(self) -> None:
        self.assertEqual(
            generator.validate_maintained_schema(None),
            [],
        )

    def test_representative_schema_is_valid(self) -> None:
        diagnostics = generator.validate_maintained_schema(
            representative_maintained_schema()
        )
        self.assertEqual(diagnostics, [])

    def test_duplicate_field_name_is_reported(self) -> None:
        schema = representative_maintained_schema(
            [
                {
                    "name": "AC_LOAD",
                    "control_word_role": "encoded",
                },
                {
                    "name": "AC_LOAD",
                    "control_word_role": "encoded",
                },
            ]
        )
        diagnostics = generator.validate_maintained_schema(schema)
        self.assertIn(
            "DUPLICATE_MAINTAINED_FIELD",
            [item.code for item in diagnostics],
        )

    def test_missing_control_word_role_is_reported(self) -> None:
        schema = representative_maintained_schema(
            [{"name": "AC_LOAD"}]
        )
        diagnostics = generator.validate_maintained_schema(schema)
        self.assertIn(
            "MISSING_CONTROL_WORD_ROLE",
            [item.code for item in diagnostics],
        )

    def test_invalid_control_word_role_is_reported(self) -> None:
        schema = representative_maintained_schema(
            [
                {
                    "name": "AC_LOAD",
                    "control_word_role": "invalid",
                }
            ]
        )
        diagnostics = generator.validate_maintained_schema(schema)
        self.assertIn(
            "INVALID_CONTROL_WORD_ROLE",
            [item.code for item in diagnostics],
        )

    def test_non_encoded_role_is_valid(self) -> None:
        schema = representative_maintained_schema(
            [
                {
                    "name": "DB_INPUT",
                    "control_word_role": "external_input",
                }
            ]
        )
        diagnostics = generator.validate_maintained_schema(schema)
        self.assertEqual(diagnostics, [])


class SignalValidationTests(unittest.TestCase):
    """Tests for extracted signal validation."""

    def test_representative_signal_is_valid(self) -> None:
        diagnostics = generator.validate_signals(
            representative_input()
        )

        self.assertEqual(diagnostics, [])

    def test_duplicate_signal_name_is_reported(self) -> None:
        input_data = representative_input(
            [
                representative_signal(),
                representative_signal(),
            ]
        )

        diagnostics = generator.validate_signals(input_data)

        self.assertIn(
            "DUPLICATE_SIGNAL_NAME",
            [item.code for item in diagnostics],
        )

    def test_invalid_bit_width_is_reported(self) -> None:
        signal = representative_signal()
        signal["definition"]["bit_width"] = 0

        diagnostics = generator.validate_signals(
            representative_input([signal])
        )

        self.assertIn(
            "INVALID_BIT_WIDTH",
            [item.code for item in diagnostics],
        )

    def test_duplicate_encoding_is_reported(self) -> None:
        signal = representative_signal()
        signal["definition"]["encodings"].append(
            encoding("1", "duplicate load", 363)
        )

        diagnostics = generator.validate_signals(
            representative_input([signal])
        )

        self.assertIn(
            "DUPLICATE_ENCODING_VALUE",
            [item.code for item in diagnostics],
        )

    def test_encoding_that_exceeds_width_is_reported(self) -> None:
        signal = representative_signal()
        signal["definition"]["encodings"] = [
            encoding("2", "invalid for one bit", 361)
        ]

        diagnostics = generator.validate_signals(
            representative_input([signal])
        )

        self.assertIn(
            "ENCODING_EXCEEDS_WIDTH",
            [item.code for item in diagnostics],
        )


class CandidateGenerationTests(unittest.TestCase):
    """Tests for candidate-schema construction."""

    def test_candidate_preserves_field_order(self) -> None:
        first = representative_signal(name="FIRST")
        second = representative_signal(name="SECOND")
        candidate, _ = generator.build_candidate(
            representative_input([first, second])
        )
        self.assertEqual(
            [field["name"] for field in candidate["fields"]],
            ["FIRST", "SECOND"],
        )

    def test_candidate_preserves_field_properties(self) -> None:
        candidate, _ = generator.build_candidate(
            representative_input()
        )
        field = candidate["fields"][0]
        self.assertEqual(field["name"], "AC_LOAD")
        self.assertEqual(field["category"], "Enable Signals")
        self.assertEqual(field["width"], 1)
        self.assertEqual(
            field["attributes"]["signal_class"],
            "Enable",
        )

    def test_encodings_are_preserved(self) -> None:
        candidate, _ = generator.build_candidate(
            representative_input()
        )
        values = candidate["fields"][0]["values"]
        self.assertEqual(
            values,
            [
                {
                    "encoding": "0",
                    "meaning": "no load",
                    "source": {
                        "document": (
                            "docs/04-control/"
                            "20-control-output-definitions/"
                            "01-microarchitectural-control-signals.md"
                        ),
                        "line": 361,
                    },
                },
                {
                    "encoding": "1",
                    "meaning": "load",
                    "source": {
                        "document": (
                            "docs/04-control/"
                            "20-control-output-definitions/"
                            "01-microarchitectural-control-signals.md"
                        ),
                        "line": 362,
                    },
                },
            ],
        )

    def test_constraints_preserve_source_traceability(self) -> None:
        candidate, _ = generator.build_candidate(
            representative_input()
        )
        constraint = candidate["fields"][0]["constraints"][0]
        self.assertEqual(
            constraint["text"],
            "Representative constraint",
        )
        self.assertEqual(constraint["source"]["line"], 365)

    def test_index_and_definition_sources_are_preserved(self) -> None:
        candidate, _ = generator.build_candidate(
            representative_input()
        )
        sources = candidate["fields"][0]["sources"]
        self.assertEqual(sources["index"]["line"], 36)
        self.assertEqual(sources["definition"]["line"], 350)
        self.assertEqual(
            sources["definition"]["section"],
            "AC_LOAD",
        )

    def test_unresolved_role_warning_is_generated(self) -> None:
        _, diagnostics = generator.build_candidate(
            representative_input()
        )
        self.assertEqual(len(diagnostics), 1)
        self.assertEqual(
            [item.code for item in diagnostics],
            ["CONTROL_WORD_ROLE_UNRESOLVED"],
        )
        self.assertEqual(diagnostics[0].field_name, "AC_LOAD")

    def test_documented_control_metadata_is_copied(self) -> None:
        candidate, diagnostics = generator.build_candidate(
            representative_input(),
            representative_maintained_schema(),
        )
        field = candidate["fields"][0]
        self.assertEqual(field["default_value"], "0")
        self.assertEqual(field["explicit_value_required"], "Yes")
        self.assertEqual(field["value_required_when"], "Always")
        self.assertNotIn("inactive_value", field)
        self.assertNotIn("default_value", field["attributes"])
        self.assertNotIn(
            "explicit_value_required",
            field["attributes"],
        )
        self.assertNotIn(
            "value_required_when",
            field["attributes"],
        )
        self.assertEqual(diagnostics, [])

    def test_documented_na_default_becomes_null(self) -> None:
        signal = representative_signal(name="DB_INPUT")
        signal["definition"]["attributes"].update(
            {
                "default_value": "N/A",
                "explicit_value_required": "No",
                "value_required_when": "AC_LOAD=1 AND AC_SRC=1",
            }
        )
        maintained_schema = representative_maintained_schema(
            [
                {
                    "name": "DB_INPUT",
                    "control_word_role": "external_input",
                }
            ]
        )
        candidate, diagnostics = generator.build_candidate(
            representative_input([signal]),
            maintained_schema,
        )
        field = candidate["fields"][0]
        self.assertIsNone(field["default_value"])
        self.assertEqual(
            field["control_word_role"],
            "external_input",
        )
        self.assertEqual(field["explicit_value_required"], "No")
        self.assertEqual(
            field["value_required_when"],
            "AC_LOAD=1 AND AC_SRC=1",
        )
        self.assertEqual(diagnostics, [])

    def test_new_field_preserves_extracted_metadata(self) -> None:
        candidate, diagnostics = generator.build_candidate(
            representative_input(
                [representative_signal(name="NEW_SIGNAL")]
            ),
            representative_maintained_schema(),
        )
        field = candidate["fields"][0]
        diagnostic_codes = [item.code for item in diagnostics]
        self.assertEqual(field["default_value"], "0")
        self.assertEqual(field["explicit_value_required"], "Yes")
        self.assertEqual(field["value_required_when"], "Always")
        self.assertIsNone(field["control_word_role"])
        self.assertIn(
            "CONTROL_WORD_ROLE_UNRESOLVED",
            diagnostic_codes,
        )

    def test_stale_maintained_field_is_reported(self) -> None:
        _, diagnostics = generator.build_candidate(
            representative_input(
                [representative_signal(name="CURRENT_SIGNAL")]
            ),
            representative_maintained_schema(
                [
                    {
                        "name": "REMOVED_SIGNAL",
                        "control_word_role": "encoded",
                    }
                ]
            ),
        )
        stale = [
            item
            for item in diagnostics
            if item.code == "STALE_MAINTAINED_FIELD"
        ]
        self.assertEqual(len(stale), 1)
        self.assertEqual(stale[0].field_name, "REMOVED_SIGNAL")


class OutputTests(unittest.TestCase):
    """Tests for deterministic file output."""

    def test_json_output_is_deterministic(self) -> None:
        candidate, _ = generator.build_candidate(
            representative_input()
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            first_path = Path(temporary_directory) / "first.json"
            second_path = Path(temporary_directory) / "second.json"

            generator.write_json_output(candidate, first_path)
            generator.write_json_output(candidate, second_path)

            self.assertEqual(
                first_path.read_bytes(),
                second_path.read_bytes(),
            )

    def test_json_output_ends_with_one_newline(self) -> None:
        candidate, _ = generator.build_candidate(
            representative_input()
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "candidate.json"

            generator.write_json_output(candidate, output_path)

            output = output_path.read_text(encoding="utf-8")
            self.assertTrue(output.endswith("\n"))
            self.assertFalse(output.endswith("\n\n"))


class CommandLineExecutionTests(unittest.TestCase):
    """Tests for one complete generator execution."""

    def test_complete_generation_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()
            input_path = repo_root / "input.json"
            candidate_path = repo_root / "candidate.json"
            report_path = repo_root / "report.txt"
            input_path.write_text(
                json.dumps(representative_input()),
                encoding="utf-8",
            )
            exit_status = generator.run(
                [
                    "--repo-root",
                    str(repo_root),
                    "--input",
                    str(input_path),
                    "--candidate-output",
                    str(candidate_path),
                    "--report-output",
                    str(report_path),
                ]
            )
            self.assertEqual(exit_status, 0)
            self.assertTrue(candidate_path.is_file())
            self.assertTrue(report_path.is_file())
            candidate = json.loads(
                candidate_path.read_text(encoding="utf-8")
            )
            field = candidate["fields"][0]
            self.assertEqual(
                candidate["specification_type"],
                "control-word-schema",
            )
            self.assertEqual(field["name"], "AC_LOAD")
            self.assertEqual(field["default_value"], "0")
            self.assertEqual(field["explicit_value_required"], "Yes")
            self.assertEqual(field["value_required_when"], "Always")
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Fields processed: 1", report)
            self.assertIn("Candidate written: yes", report)
            self.assertIn("Warnings: 1", report)
            self.assertIn(
                "CONTROL_WORD_ROLE_UNRESOLVED",
                report,
            )
            self.assertNotIn(
                "DEFAULT_VALUE_UNRESOLVED",
                report,
            )

    def test_complete_run_preserves_maintained_role(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory).resolve()
            input_path = repo_root / "input.json"
            maintained_path = repo_root / "maintained.json"
            candidate_path = repo_root / "candidate.json"
            report_path = repo_root / "report.txt"
            input_path.write_text(
                json.dumps(representative_input()),
                encoding="utf-8",
            )
            maintained_path.write_text(
                json.dumps(representative_maintained_schema()),
                encoding="utf-8",
            )
            exit_status = generator.run(
                [
                    "--repo-root",
                    str(repo_root),
                    "--input",
                    str(input_path),
                    "--maintained-schema",
                    str(maintained_path),
                    "--candidate-output",
                    str(candidate_path),
                    "--report-output",
                    str(report_path),
                ]
            )
            self.assertEqual(exit_status, 0)
            candidate = json.loads(
                candidate_path.read_text(encoding="utf-8")
            )
            field = candidate["fields"][0]
            self.assertEqual(field["control_word_role"], "encoded")
            self.assertEqual(field["default_value"], "0")
            self.assertEqual(field["explicit_value_required"], "Yes")
            self.assertEqual(field["value_required_when"], "Always")
            report = report_path.read_text(encoding="utf-8")
            self.assertIn("Warnings: 0", report)


if __name__ == "__main__":
    unittest.main()