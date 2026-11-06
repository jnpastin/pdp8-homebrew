"""Tests for direct-control candidate generation."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

SOURCE_DIRECTORY = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE_DIRECTORY))

import generate_direct_control as generator  # noqa: E402


def definition(definition_id: str = "01:1.1", value: str = "1") -> dict:
    return {
        "id": definition_id,
        "title": "1.1 Example",
        "group": "1 Group",
        "source": {"path": "docs/example.md", "line": 10},
        "applicable_context": ["RUN = 1"],
        "direct_assignments": [f"RUN_NEXT = {value}"],
        "control_supplied_values": [],
        "micro_operation_assignments": [],
        "state_commits": [],
        "value_relationships": [],
        "widths": [],
        "constraints": [],
        "sources": [],
        "drive_states": [],
        "external_ownership": [],
        "memory_behavior": [],
        "derived_values": [],
    }


def artifact(definitions: list[dict]) -> dict:
    return {
        "format_version": 1,
        "control_design_version": "v1",
        "artifact": "direct-control-definitions",
        "extraction_stage": "documentation-extraction",
        "sources": ["docs/example.md"],
        "definitions": definitions,
        "diagnostics": [],
    }


class GenerationTests(unittest.TestCase):
    def test_default_paths_match_three_stage_workflow(self) -> None:
        self.assertEqual(
            generator.DEFAULT_EXTRACTED.name,
            "direct-control-definitions.json",
        )
        self.assertEqual(
            generator.DEFAULT_MAINTAINED,
            Path("rom/microcode/v1/direct-control-definitions.json"),
        )
        self.assertEqual(
            generator.DEFAULT_CANDIDATE.name,
            "direct-control-definitions.candidate.json",
        )
        self.assertEqual(
            generator.DEFAULT_INPUT_SCHEMA.name,
            "control-input-schema.json",
        )
        self.assertEqual(
            generator.DEFAULT_WORD_SCHEMA.name,
            "control-word-schema.json",
        )
        self.assertEqual(
            generator.DEFAULT_MAPPING.name,
            "micro-operation-mapping.json",
        )

    def test_first_generation_reports_new_definition(self) -> None:
        candidate, diagnostics = generator.build_candidate(
            artifact([definition()]), None
        )
        self.assertIsNotNone(candidate)
        self.assertEqual([item.code for item in diagnostics], ["NEW_DEFINITION"])

    def test_unchanged_maintained_definition_has_no_diagnostic(self) -> None:
        extracted = artifact([definition()])
        candidate, diagnostics = generator.build_candidate(
            extracted, copy.deepcopy(extracted)
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(diagnostics, [])

    def test_changed_definition_is_reported(self) -> None:
        extracted = artifact([definition(value="1")])
        maintained = artifact([definition(value="0")])
        _, diagnostics = generator.build_candidate(extracted, maintained)
        self.assertEqual(diagnostics[0].code, "CHANGED_DEFINITION")

    def test_stale_definition_is_reported(self) -> None:
        extracted = artifact([])
        maintained = artifact([definition()])
        _, diagnostics = generator.build_candidate(extracted, maintained)
        self.assertEqual(diagnostics[0].code, "STALE_DEFINITION")

    def test_candidate_uses_extracted_definition(self) -> None:
        extracted = artifact([definition(value="1")])
        maintained = artifact([definition(value="0")])
        candidate, _ = generator.build_candidate(extracted, maintained)
        assert candidate is not None
        self.assertEqual(
            candidate["definitions"][0]["direct_assignments"],
            ["RUN_NEXT = 1"],
        )

    def test_extractor_error_blocks_generation(self) -> None:
        extracted = artifact([definition()])
        extracted["diagnostics"] = [{"severity": "ERROR"}]
        candidate, diagnostics = generator.build_candidate(extracted, None)
        self.assertIsNone(candidate)
        self.assertEqual(diagnostics[0].code, "EXTRACTOR_FAILURE_DIAGNOSTICS")

    def test_version_mismatch_blocks_generation(self) -> None:
        extracted = artifact([definition()])
        maintained = artifact([definition()])
        maintained["control_design_version"] = "v2"
        candidate, diagnostics = generator.build_candidate(extracted, maintained)
        self.assertIsNone(candidate)
        self.assertEqual(diagnostics[0].code, "CONTROL_DESIGN_VERSION_MISMATCH")

    def test_duplicate_definition_id_blocks_generation(self) -> None:
        candidate, diagnostics = generator.build_candidate(
            artifact([definition(), definition()]), None
        )
        self.assertIsNone(candidate)
        self.assertEqual(diagnostics[0].code, "INVALID_EXTRACTED_DEFINITIONS")

    def test_missing_optional_maintained_artifact_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = generator.read_json(
                Path(directory) / "missing.json", optional=True
            )
            self.assertIsNone(result)

    def test_candidate_is_json_serializable(self) -> None:
        candidate, _ = generator.build_candidate(
            artifact([definition()]), None
        )
        json.dumps(candidate)


class RepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[4]
        cls.extracted = generator.read_json(
            cls.root / generator.DEFAULT_EXTRACTED
        )
        assert cls.extracted is not None
        cls.candidate, cls.diagnostics = generator.build_candidate(
            cls.extracted, None
        )

    def test_repository_definition_count(self) -> None:
        assert self.candidate is not None
        self.assertEqual(len(self.candidate["definitions"]), 65)

    def test_repository_first_generation_is_reviewable(self) -> None:
        self.assertTrue(self.diagnostics)
        self.assertTrue(
            all(item.code == "NEW_DEFINITION" for item in self.diagnostics)
        )
        self.assertFalse(
            any(
                item.severity in generator.FAILURE_SEVERITIES
                for item in self.diagnostics
            )
        )


if __name__ == "__main__":
    unittest.main()
