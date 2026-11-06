"""Tests for the control-input schema generator."""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_control_input_schema import (  # noqa: E402
    DEFAULT_CANDIDATE,
    DEFAULT_INPUT,
    DEFAULT_MAINTAINED,
    DEFAULT_REPORT,
    Diagnostic,
    GenerationFailure,
    build_candidate,
    build_report,
    field_from_signal,
    main,
    parse_arguments,
    read_json,
    resolve_from_repo,
    validate_extracted,
    validate_maintained,
    write_json,
)

SOURCE = {"path": "docs/in.md", "line": 2, "heading": "A"}


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def source_at(line: int) -> dict:
    return {"path": "docs/in.md", "line": line}


def make_signal(name: str = "A", dependencies: list | None = None) -> dict:
    return {
        "name": name,
        "attributes": {"display_name": name, "purpose": "test"},
        "bit_width": 1,
        "category": "Test",
        "constraints": [],
        "consumers": [],
        "definition_source": {**SOURCE, "heading": name},
        "dependencies": dependencies or [],
        "domain": "Test",
        "enumerated_values": [
            {"value": "0", "meaning": "off", "source": source_at(3)},
            {"value": "1", "meaning": "on", "source": source_at(4)},
        ],
        "extraction_status": "structure-validated",
        "index_source": {"path": "docs/index.md", "line": 1},
        "logic": {},
        "polarity": {"source": "defaulted", "value": "active-high"},
        "value_ranges": [],
    }


def make_extracted(*signals: dict) -> dict:
    return {
        "constraints": [],
        "diagnostics": [],
        "extraction_stage": "final-structure-validation",
        "format_version": 1,
        "signals": list(signals) or [make_signal()],
        "sources": ["docs/in.md"],
    }


def make_maintained(*fields: dict) -> dict:
    return {
        "specification_type": "control-input-schema",
        "schema_version": 1,
        "control_design_version": "v1",
        "fields": list(fields),
    }


def make_field(name: str = "A", uses: list | None = None) -> dict:
    return {"name": name, "control_uses": ["predicate"] if uses is None else uses}


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


# ---------------------------------------------------------------------------
# Paths, arguments, and reading
# ---------------------------------------------------------------------------


class PathAndArgumentTests(unittest.TestCase):
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

    def test_default_paths_are_used(self) -> None:
        options = parse_arguments(["--repo-root", "."])

        self.assertEqual(options.input, DEFAULT_INPUT)
        self.assertEqual(options.maintained_schema, DEFAULT_MAINTAINED)
        self.assertEqual(options.candidate_output, DEFAULT_CANDIDATE)
        self.assertEqual(options.report_output, DEFAULT_REPORT)


class ReadJsonTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def write(self, content: str | bytes) -> Path:
        path = self.root / "input.json"
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        return path

    def test_missing_required_input_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "does not exist"):
            read_json(self.root / "missing.json")

    def test_missing_optional_input_is_none(self) -> None:
        self.assertIsNone(read_json(self.root / "missing.json", optional=True))

    def test_blank_optional_input_is_none(self) -> None:
        self.assertIsNone(read_json(self.write("  \n"), optional=True))

    def test_invalid_json_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "not valid JSON"):
            read_json(self.write("{"))

    def test_invalid_utf8_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "not valid UTF-8"):
            read_json(self.write(b"\xff\xfe{}"))

    def test_non_object_json_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "top-level object"):
            read_json(self.write("[]"))

    def test_unreadable_path_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "could not be read"):
            read_json(self.root)


# ---------------------------------------------------------------------------
# Extractor validation
# ---------------------------------------------------------------------------


class ExtractedValidationTests(unittest.TestCase):
    def test_valid_extracted_has_no_diagnostics(self) -> None:
        self.assertEqual(validate_extracted(make_extracted()), [])

    def test_header_is_validated(self) -> None:
        extracted = make_extracted()
        extracted.update(
            format_version=2, extraction_stage="other", diagnostics=[{"code": "X"}]
        )

        self.assertEqual(
            codes(validate_extracted(extracted)),
            [
                "UNSUPPORTED_FORMAT_VERSION",
                "UNEXPECTED_EXTRACTION_STAGE",
                "EXTRACTOR_DIAGNOSTICS_PRESENT",
            ],
        )

    def test_signals_must_be_array(self) -> None:
        for signals in (None, {"A": 1}):
            with self.subTest(signals=signals):
                extracted = make_extracted()
                extracted["signals"] = signals
                self.assertEqual(
                    codes(validate_extracted(extracted)), ["INVALID_SIGNALS"]
                )

    def test_duplicate_signal_is_reported(self) -> None:
        self.assertEqual(
            codes(validate_extracted(make_extracted(make_signal(), make_signal()))),
            ["DUPLICATE_SIGNAL"],
        )

    def test_invalid_signal_names_are_reported(self) -> None:
        extracted = make_extracted(make_signal(), "x", {"name": ""}, {"name": ["X"]})

        self.assertEqual(
            codes(validate_extracted(extracted)),
            ["INVALID_SIGNAL", "INVALID_SIGNAL_NAME", "INVALID_SIGNAL_NAME"],
        )

    def test_invalid_bit_widths_are_reported(self) -> None:
        for width in (0, -1, "1", None):
            with self.subTest(width=width):
                signal = make_signal()
                signal["bit_width"] = width
                self.assertEqual(
                    codes(validate_extracted(make_extracted(signal))),
                    ["INVALID_BIT_WIDTH"],
                )

    def test_signal_status_and_shapes_are_validated(self) -> None:
        signal = make_signal()
        signal.update(
            extraction_status="definition-missing",
            enumerated_values="x",
            value_ranges=None,
            dependencies={},
            definition_source={"path": "x"},
        )

        self.assertEqual(
            codes(validate_extracted(make_extracted(signal))),
            [
                "INVALID_EXTRACTION_STATUS",
                "INVALID_ENUMERATED_VALUES",
                "INVALID_VALUE_RANGES",
                "INVALID_DEPENDENCIES",
                "INVALID_DEFINITION_SOURCE",
            ],
        )

    def test_enumerated_values_are_validated(self) -> None:
        signal = make_signal()
        first = signal["enumerated_values"][0]
        signal["enumerated_values"] += [first, {"value": 1}, "x"]

        diagnostics = validate_extracted(make_extracted(signal))

        self.assertEqual(
            codes(diagnostics),
            [
                "DUPLICATE_ENUMERATED_VALUE",
                "INVALID_ENUMERATED_VALUE",
                "INVALID_ENUMERATED_VALUE",
            ],
        )
        self.assertEqual(diagnostics[0].source_line, 3)

    def test_global_constraints_are_validated(self) -> None:
        extracted = make_extracted(make_signal("A"), make_signal("B"))
        extracted["constraints"] = [
            {"kind": "exactly_one", "inputs": ["A", "B"]},
            "x",
            {"kind": "sometimes", "inputs": ["A", "B"]},
            {"kind": "at_most_one", "inputs": ["A"]},
            {
                "kind": "at_most_one",
                "inputs": ["A", "MISSING", ["A"]],
                "source": {"path": "docs/in.md", "line": 9},
            },
        ]

        diagnostics = validate_extracted(extracted)

        self.assertEqual(
            codes(diagnostics),
            [
                "INVALID_GLOBAL_CONSTRAINT",
                "INVALID_GLOBAL_CONSTRAINT",
                "INVALID_GLOBAL_CONSTRAINT_INPUTS",
                "UNDEFINED_GLOBAL_CONSTRAINT_INPUT",
                "UNDEFINED_GLOBAL_CONSTRAINT_INPUT",
            ],
        )
        self.assertEqual(diagnostics[3].referenced_input, "MISSING")
        self.assertEqual(diagnostics[3].source_line, 9)
        self.assertIsNone(diagnostics[4].referenced_input)

    def test_constraints_must_be_array(self) -> None:
        extracted = make_extracted()
        extracted["constraints"] = None

        self.assertEqual(
            codes(validate_extracted(extracted)), ["INVALID_GLOBAL_CONSTRAINTS"]
        )


# ---------------------------------------------------------------------------
# Maintained schema validation
# ---------------------------------------------------------------------------


class MaintainedValidationTests(unittest.TestCase):
    def test_missing_schema_is_allowed(self) -> None:
        self.assertEqual(validate_maintained(None), ([], {}))

    def test_fields_are_indexed_by_name(self) -> None:
        diagnostics, fields = validate_maintained(make_maintained(make_field("A")))

        self.assertEqual(diagnostics, [])
        self.assertEqual(list(fields), ["A"])

    def test_header_is_validated(self) -> None:
        maintained = make_maintained()
        maintained.update(
            specification_type="other", schema_version=2, control_design_version="v2"
        )

        self.assertEqual(
            codes(validate_maintained(maintained)[0]),
            [
                "INVALID_SCHEMA_TYPE",
                "UNSUPPORTED_SCHEMA_VERSION",
                "CONTROL_DESIGN_VERSION_MISMATCH",
            ],
        )

    def test_fields_must_be_array(self) -> None:
        maintained = make_maintained()
        maintained["fields"] = {}

        diagnostics, fields = validate_maintained(maintained)

        self.assertEqual(codes(diagnostics), ["INVALID_FIELDS"])
        self.assertEqual(fields, {})

    def test_invalid_fields_are_reported(self) -> None:
        maintained = make_maintained(
            make_field("A"), make_field("A"), "x", {"name": ""}
        )

        self.assertEqual(
            codes(validate_maintained(maintained)[0]),
            ["DUPLICATE_MAINTAINED_FIELD", "INVALID_FIELD", "INVALID_FIELD_NAME"],
        )

    def test_invalid_control_uses_are_reported(self) -> None:
        for uses in (["bad"], ["value", "value"], "predicate", None, [["value"]]):
            with self.subTest(uses=uses):
                field = {"name": "A"} if uses is None else make_field(uses=uses)
                self.assertEqual(
                    codes(validate_maintained(make_maintained(field))[0]),
                    ["INVALID_CONTROL_USES"],
                )

    def test_empty_control_uses_are_valid(self) -> None:
        self.assertEqual(
            validate_maintained(make_maintained(make_field(uses=[])))[0], []
        )


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


class CandidateTests(unittest.TestCase):
    def test_classification_is_preserved(self) -> None:
        candidate, diagnostics = build_candidate(
            make_extracted(),
            make_maintained(make_field(uses=["predicate", "value"])),
        )

        self.assertEqual(candidate["fields"][0]["control_uses"], ["predicate", "value"])
        self.assertEqual(diagnostics, [])

    def test_new_input_is_unresolved(self) -> None:
        candidate, diagnostics = build_candidate(make_extracted(), None)

        self.assertEqual(candidate["fields"][0]["control_uses"], [])
        self.assertEqual(codes(diagnostics), ["CONTROL_USES_UNRESOLVED"])
        self.assertEqual(
            candidate["diagnostics"],
            [
                {
                    "severity": "WARNING",
                    "code": "CONTROL_USES_UNRESOLVED",
                    "message": "Input has no reviewed control-use classification.",
                    "input_name": "A",
                    "source_path": "docs/in.md",
                    "source_line": 2,
                }
            ],
        )

    def test_empty_classification_is_unresolved(self) -> None:
        _, diagnostics = build_candidate(
            make_extracted(), make_maintained(make_field(uses=[]))
        )

        self.assertEqual(codes(diagnostics), ["CONTROL_USES_UNRESOLVED"])

    def test_stale_maintained_field_is_reported(self) -> None:
        candidate, diagnostics = build_candidate(
            make_extracted(), make_maintained(make_field("A"), make_field("OLD"))
        )

        self.assertEqual([field["name"] for field in candidate["fields"]], ["A"])
        self.assertEqual(codes(diagnostics), ["STALE_MAINTAINED_FIELD"])

    def test_fields_follow_extracted_order(self) -> None:
        candidate, _ = build_candidate(
            make_extracted(make_signal("B"), make_signal("A")), None
        )

        self.assertEqual([field["name"] for field in candidate["fields"]], ["B", "A"])

    def test_extracted_properties_are_refreshed(self) -> None:
        candidate, _ = build_candidate(make_extracted(), make_maintained(make_field()))

        field = candidate["fields"][0]
        self.assertEqual(field["sources"]["definition"]["path"], "docs/in.md")
        self.assertEqual(field["width"], 1)
        self.assertEqual(field["values"][1]["meaning"], "on")

    def test_global_constraints_are_preserved(self) -> None:
        extracted = make_extracted(make_signal("A"), make_signal("B"))
        extracted["constraints"] = [
            {
                "kind": "exactly_one",
                "inputs": ["A", "B"],
                "source": {"path": "docs/in.md", "line": 8},
            }
        ]

        candidate, diagnostics = build_candidate(
            extracted, make_maintained(make_field("A"), make_field("B"))
        )

        self.assertEqual(candidate["constraints"], extracted["constraints"])
        self.assertEqual(diagnostics, [])

    def test_undefined_dependency_is_reported(self) -> None:
        dependency = {"name": "B", "source": {"path": "docs/in.md", "line": 5}}

        candidate, diagnostics = build_candidate(
            make_extracted(make_signal("A", [dependency])),
            make_maintained(make_field()),
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(codes(diagnostics), ["UNDEFINED_DEPENDENCY"])
        self.assertEqual(diagnostics[0].referenced_input, "B")

    def test_invalid_input_yields_no_candidate(self) -> None:
        candidate, diagnostics = build_candidate(
            make_extracted(), make_maintained(make_field(uses=["bad"]))
        )

        self.assertIsNone(candidate)
        self.assertEqual(codes(diagnostics), ["INVALID_CONTROL_USES"])

    def test_field_key_order_is_stable(self) -> None:
        field = field_from_signal(make_signal(), ["value"])

        self.assertEqual(
            list(field),
            [
                "name", "category", "width", "control_uses", "attributes",
                "polarity", "domain", "values", "ranges", "dependencies",
                "derivation", "constraints", "consumers", "sources",
            ],
        )

    def test_derivation_prefers_derivation_then_expression(self) -> None:
        cases = [
            ({"derivation": "D", "expression": "E"}, "D"),
            ({"expression": "E", "internal_composition": "I"}, "E"),
            ({"internal_composition": "I"}, "I"),
            ({}, None),
        ]
        for logic, expected in cases:
            with self.subTest(logic=logic):
                signal = make_signal()
                signal["logic"] = logic
                self.assertEqual(field_from_signal(signal, [])["derivation"], expected)

    def test_non_object_logic_has_no_derivation(self) -> None:
        signal = make_signal()
        signal["logic"] = "x"

        self.assertIsNone(field_from_signal(signal, [])["derivation"])


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OutputTests(unittest.TestCase):
    def test_json_uses_lf_and_one_trailing_newline(self) -> None:
        candidate, _ = build_candidate(make_extracted(), None)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "candidate.json"
            write_json(candidate, path)
            content = path.read_bytes()

        self.assertTrue(content.endswith(b"}\n"))
        self.assertNotIn(b"\r\n", content)

    def test_report_lists_counts_and_diagnostics(self) -> None:
        report = build_report(
            [Diagnostic("WARNING", "CODE", "Message.", input_name="A")], 3, True
        )

        self.assertIn("Fields processed: 3", report)
        self.assertIn("Candidate written: yes", report)
        self.assertIn("Warnings: 1", report)
        self.assertIn("WARNING CODE [A]: Message.", report)

    def test_empty_report_says_no_diagnostics(self) -> None:
        report = build_report([], 0, False)

        self.assertIn("Candidate written: no", report)
        self.assertTrue(report.endswith("No diagnostics.\n"))


# ---------------------------------------------------------------------------
# Contract with the control-input extractor
# ---------------------------------------------------------------------------

EXTRACTOR_GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "control-input-extractor"
    / "tests"
    / "golden"
    / "valid"
    / "control-inputs.json"
)


class ExtractorContractTests(unittest.TestCase):
    """Keep this tool's inputs in step with the extractor's real output.

    The extractor's golden output is the reference.  If these tests fail
    after an extractor change, update this tool (and ``make_signal``) to
    match.
    """

    def setUp(self) -> None:
        self.extracted = json.loads(EXTRACTOR_GOLDEN.read_text(encoding="utf-8"))

    def test_extractor_output_builds_a_candidate(self) -> None:
        candidate, diagnostics = build_candidate(self.extracted, None)

        self.assertIsNotNone(candidate)
        self.assertEqual(
            set(codes(diagnostics)), {"CONTROL_USES_UNRESOLVED"}
        )
        self.assertEqual(
            [field["name"] for field in candidate["fields"]],
            [signal["name"] for signal in self.extracted["signals"]],
        )

    def test_test_signal_matches_extractor_signal_shape(self) -> None:
        real = self.extracted["signals"][0]
        test = make_signal()

        self.assertEqual(set(test), set(real))
        self.assertEqual(
            set(test["definition_source"]), set(real["definition_source"])
        )
        self.assertEqual(
            set(test["enumerated_values"][0]), set(real["enumerated_values"][0])
        )

    def test_test_extracted_matches_extractor_top_level_shape(self) -> None:
        self.assertEqual(set(make_extracted()), set(self.extracted))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


class MainTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.candidate = self.root / "out" / "candidate.json"
        self.report = self.root / "out" / "report.txt"

    def write_inputs(self, extracted: dict | None, maintained: dict | None) -> None:
        if extracted is not None:
            (self.root / "in.json").write_text(json.dumps(extracted), encoding="utf-8")
        if maintained is not None:
            (self.root / "maintained.json").write_text(
                json.dumps(maintained), encoding="utf-8"
            )

    def run_main(self) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "--repo-root", str(self.root),
                    "--input", "in.json",
                    "--maintained-schema", "maintained.json",
                    "--candidate-output", "out/candidate.json",
                    "--report-output", "out/report.txt",
                ]
            )
        return exit_code, stdout.getvalue()

    def test_successful_run_writes_candidate_and_report(self) -> None:
        self.write_inputs(make_extracted(), make_maintained(make_field()))

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            json.loads(self.candidate.read_text(encoding="utf-8"))["fields"][0]["name"],
            "A",
        )
        self.assertIn("No diagnostics.", self.report.read_text(encoding="utf-8"))
        self.assertIn("Status: SUCCEEDED", stdout)

    def test_missing_maintained_schema_succeeds_with_warnings(self) -> None:
        self.write_inputs(make_extracted(), None)

        exit_code, _ = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertTrue(self.candidate.exists())
        self.assertIn("Warnings: 1", self.report.read_text(encoding="utf-8"))

    def test_undefined_dependency_prevents_candidate(self) -> None:
        dependency = {"name": "B", "source": {"path": "docs/in.md", "line": 5}}
        self.write_inputs(
            make_extracted(make_signal("A", [dependency])),
            make_maintained(make_field()),
        )

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        self.assertIn("ERROR UNDEFINED_DEPENDENCY [A]", stdout)
        self.assertIn("Source: docs/in.md:5", stdout)

    def test_unreadable_input_is_fatal(self) -> None:
        self.write_inputs(None, make_maintained(make_field()))

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        report = self.report.read_text(encoding="utf-8")
        self.assertIn("Fatal errors: 1", report)
        self.assertIn(
            "FATAL GENERATION_FAILURE [-]: Required input does not exist", report
        )
        self.assertIn("Control inputs: 0", stdout)

    def test_report_sorts_diagnostics(self) -> None:
        maintained = make_maintained(
            make_field("B", ["bad"]), make_field("A", ["bad"])
        )
        maintained["schema_version"] = 2
        self.write_inputs(make_extracted(), maintained)

        self.run_main()

        report = self.report.read_text(encoding="utf-8")
        details = report.split("-----------\n", 1)[1].splitlines()
        self.assertEqual(
            [line.split(":")[0] for line in details],
            [
                "ERROR INVALID_CONTROL_USES [A]",
                "ERROR INVALID_CONTROL_USES [B]",
                "ERROR UNSUPPORTED_SCHEMA_VERSION [-]",
            ],
        )

    def test_null_signals_do_not_crash(self) -> None:
        extracted = make_extracted()
        extracted["signals"] = None
        self.write_inputs(extracted, None)

        exit_code, _ = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Fields processed: 0", self.report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
