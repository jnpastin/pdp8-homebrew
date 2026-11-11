"""Tests for the control-word schema generator."""

from __future__ import annotations

import copy
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_control_word_schema import (  # noqa: E402
    DEFAULT_CANDIDATE,
    DEFAULT_INPUT,
    DEFAULT_MAINTAINED,
    DEFAULT_REPORT,
    Diagnostic,
    GenerationFailure,
    build_candidate,
    build_report,
    field_from_signal,
    format_failure,
    main,
    parse_arguments,
    read_json,
    resolve_from_repo,
    validate_extracted,
    validate_maintained,
    write_json,
)

DOC = "docs/defs.md"
INDEX = "docs/index.md"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def source_at(line: int, path: str = DOC) -> dict:
    return {"path": path, "line": line}


def source_out(line: int) -> dict:
    """Return a source reference in the candidate's form."""

    return {"document": DOC, "line": line}


def make_signal(name: str = "A") -> dict:
    """Return a valid extracted signal with the extractor's key order."""

    return {
        "name": name,
        "category": "Enable Signals",
        "definition": {
            "heading": name,
            "attributes": {
                "mnemonic": name,
                "display_name": "Signal A",
                "signal_class": "Enable",
                "default_value": "0",
                "explicit_value_required": "Yes",
                "value_required_when": "Always",
                "purpose": "Test.",
            },
            "bit_width": 1,
            "encodings": [
                {"value": "0", "meaning": "off", "source": source_at(3)},
                {"value": "1", "meaning": "on", "source": source_at(4)},
            ],
            "constraints": [{"text": "Only at TP.", "source": source_at(6)}],
            "used_by_micro_operations": [
                {"micro_operation": "OP", "source": source_at(8), "value": "1"}
            ],
            "source": source_at(2),
        },
        "source": source_at(1, INDEX),
        "extraction_status": "category-validated",
    }


def make_extracted(*signals: dict) -> dict:
    return {
        "format_version": 1,
        "extraction_stage": "category-validation",
        "signals": list(signals) or [make_signal()],
        "diagnostics": [],
    }


def make_maintained(*fields: dict) -> dict:
    return {
        "specification_type": "control-word-schema",
        "schema_version": 1,
        "control_design_version": "v1",
        "fields": list(fields),
    }


def make_field(name: str = "A", role: str | None = "encoded") -> dict:
    return {"name": name, "control_word_role": role}


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


def signal_codes(signal: dict) -> list[str]:
    """Return the codes from validating one signal on its own."""

    return codes(validate_extracted(make_extracted(signal)))


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

    def test_valid_object_is_loaded(self) -> None:
        self.assertEqual(read_json(self.write('{"a": 1}'), "Input file"), {"a": 1})

    def test_missing_required_input_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "Input file does not exist"):
            read_json(self.root / "missing.json", "Input file")

    def test_missing_optional_input_is_none(self) -> None:
        self.assertIsNone(read_json(self.root / "missing.json", "X", optional=True))

    def test_blank_optional_input_is_none(self) -> None:
        self.assertIsNone(read_json(self.write("  \n"), "X", optional=True))

    def test_invalid_json_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "not valid JSON: .*line 1"):
            read_json(self.write("{"), "X")

    def test_invalid_utf8_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "not valid UTF-8"):
            read_json(self.write(b"\xff\xfe{}"), "X")

    def test_non_object_json_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "top-level JSON object"):
            read_json(self.write("[]"), "X")

    def test_unreadable_path_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "Unable to read maintained"):
            read_json(self.root, "Maintained schema", optional=True)


# ---------------------------------------------------------------------------
# Extractor validation
# ---------------------------------------------------------------------------


class ExtractedValidationTests(unittest.TestCase):
    def test_valid_extracted_has_no_diagnostics(self) -> None:
        self.assertEqual(validate_extracted(make_extracted()), [])

    def test_header_is_validated(self) -> None:
        extracted = make_extracted()
        extracted.update(format_version=2, extraction_stage="x", diagnostics=[{}])

        self.assertEqual(
            sorted(codes(validate_extracted(extracted))),
            [
                "EXTRACTOR_DIAGNOSTICS_PRESENT",
                "UNSUPPORTED_EXTRACTION_STAGE",
                "UNSUPPORTED_FORMAT_VERSION",
            ],
        )

    def test_extractor_diagnostics_must_be_array(self) -> None:
        extracted = make_extracted()
        extracted["diagnostics"] = None

        self.assertEqual(
            codes(validate_extracted(extracted)), ["INVALID_INPUT_DIAGNOSTICS"]
        )

    def test_signals_must_be_array(self) -> None:
        extracted = make_extracted()
        del extracted["signals"]

        self.assertEqual(codes(validate_extracted(extracted)), ["INVALID_SIGNALS"])

    def test_signals_are_validated_despite_header_errors(self) -> None:
        signal = make_signal()
        signal["category"] = ""
        extracted = make_extracted(signal)
        extracted["format_version"] = 2

        self.assertEqual(
            sorted(codes(validate_extracted(extracted))),
            ["INVALID_CATEGORY", "UNSUPPORTED_FORMAT_VERSION"],
        )

    def test_unusable_signals_stop_at_first_problem(self) -> None:
        nameless = make_signal()
        nameless["name"] = ""
        nameless["category"] = ""

        diagnostics = validate_extracted(make_extracted(nameless, "x"))

        self.assertEqual(codes(diagnostics), ["INVALID_SIGNAL_NAME", "INVALID_SIGNAL"])
        self.assertEqual(diagnostics[0].source_path, INDEX)

    def test_duplicate_signal_is_reported(self) -> None:
        diagnostics = validate_extracted(make_extracted(make_signal(), make_signal()))

        self.assertEqual(codes(diagnostics), ["DUPLICATE_SIGNAL_NAME"])
        self.assertEqual(diagnostics[0].field_name, "A")

    def test_signal_properties_are_validated(self) -> None:
        signal = make_signal()
        signal.update(category=None, extraction_status="x", source=None)

        self.assertEqual(
            sorted(signal_codes(signal)),
            ["INVALID_CATEGORY", "INVALID_EXTRACTION_STATUS", "INVALID_SOURCE"],
        )

    def test_definition_must_be_object(self) -> None:
        signal = make_signal()
        signal["definition"] = []

        self.assertEqual(signal_codes(signal), ["INVALID_DEFINITION"])

    def test_source_references_are_validated(self) -> None:
        signal = make_signal()
        signal["source"] = {"path": "", "line": 0}
        signal["definition"]["source"] = {"path": DOC, "line": True}

        diagnostics = validate_extracted(make_extracted(signal))

        self.assertEqual(
            sorted(codes(diagnostics)),
            ["INVALID_SOURCE_LINE", "INVALID_SOURCE_LINE", "MISSING_SOURCE_PATH"],
        )
        self.assertIn(
            "Index source does not contain a valid path.",
            [item.message for item in diagnostics],
        )

    def test_malformed_location_is_left_out_of_diagnostics(self) -> None:
        signal = make_signal()
        signal["source"] = {"path": 5, "line": "1"}

        diagnostics = validate_extracted(make_extracted(signal))

        self.assertEqual(
            {(item.source_path, item.source_line) for item in diagnostics},
            {(None, None)},
        )

    def test_definition_properties_are_validated(self) -> None:
        signal = make_signal()
        signal["definition"].update(
            heading="",
            attributes=[],
            encodings={},
            used_by_micro_operations=None,
            constraints="x",
        )

        diagnostics = validate_extracted(make_extracted(signal))

        self.assertEqual(
            sorted(codes(diagnostics)),
            [
                "INVALID_ATTRIBUTES",
                "INVALID_CONSTRAINTS",
                "INVALID_DEFINITION_HEADING",
                "INVALID_ENCODINGS",
                "INVALID_USED_BY_MICRO_OPERATIONS",
            ],
        )
        self.assertEqual({item.source_line for item in diagnostics}, {2})

    def test_control_word_attributes_are_validated(self) -> None:
        signal = make_signal()
        signal["definition"]["attributes"].update(
            default_value="", explicit_value_required="Maybe"
        )
        del signal["definition"]["attributes"]["value_required_when"]

        self.assertEqual(
            sorted(signal_codes(signal)),
            [
                "INVALID_EXTRACTED_DEFAULT_VALUE",
                "INVALID_EXTRACTED_EXPLICIT_REQUIREMENT",
                "INVALID_EXTRACTED_VALUE_CONDITION",
            ],
        )

    def test_bit_width_must_be_positive_integer(self) -> None:
        for width in (0, True, "1", None):
            with self.subTest(width=width):
                signal = make_signal()
                signal["definition"]["bit_width"] = width

                self.assertEqual(signal_codes(signal), ["INVALID_BIT_WIDTH"])

    def test_encoding_values_are_validated(self) -> None:
        cases = {
            "": "INVALID_ENCODING_VALUE",
            7: "INVALID_ENCODING_VALUE",
            "8": "NON_OCTAL_ENCODING",
            "0o1": "NON_OCTAL_ENCODING",
            "2": "ENCODING_EXCEEDS_WIDTH",
        }
        for value, code in cases.items():
            with self.subTest(value=value):
                signal = make_signal()
                signal["definition"]["encodings"][0]["value"] = value

                diagnostics = validate_extracted(make_extracted(signal))

                self.assertEqual(codes(diagnostics), [code])
                self.assertEqual(diagnostics[0].source_line, 3)

    def test_duplicate_encoding_is_reported_at_repeat(self) -> None:
        signal = make_signal()
        signal["definition"]["encodings"][0]["value"] = "1"

        diagnostics = validate_extracted(make_extracted(signal))

        self.assertEqual(codes(diagnostics), ["DUPLICATE_ENCODING_VALUE"])
        self.assertEqual(diagnostics[0].source_line, 4)

    def test_wide_encoding_fits_wide_field(self) -> None:
        signal = make_signal()
        signal["definition"]["bit_width"] = 3
        signal["definition"]["encodings"][0]["value"] = "7"

        self.assertEqual(signal_codes(signal), [])

    def test_octal_is_checked_when_width_is_invalid(self) -> None:
        signal = make_signal()
        signal["definition"]["bit_width"] = 0
        signal["definition"]["encodings"][0]["value"] = "9"

        self.assertEqual(
            sorted(signal_codes(signal)), ["INVALID_BIT_WIDTH", "NON_OCTAL_ENCODING"]
        )

    def test_encoding_entries_are_validated(self) -> None:
        signal = make_signal()
        signal["definition"]["encodings"][0].update(meaning="", source=None)
        signal["definition"]["encodings"].append("x")

        self.assertEqual(
            sorted(signal_codes(signal)),
            ["INVALID_ENCODING", "INVALID_ENCODING_MEANING", "INVALID_SOURCE"],
        )

    def test_micro_operation_uses_are_validated(self) -> None:
        cases = [
            ("x", "INVALID_USED_BY_MICRO_OPERATION", 2),
            ({"micro_operation": "", "source": source_at(9)},
             "INVALID_USED_BY_MICRO_OPERATION", 9),
            ({"micro_operation": "OP", "source": source_at(9), "value": ""},
             "INVALID_USED_BY_VALUE", 9),
            ({"micro_operation": "OP", "source": {"path": DOC}},
             "INVALID_SOURCE_LINE", None),
        ]
        for use, code, line in cases:
            with self.subTest(use=use):
                signal = make_signal()
                signal["definition"]["used_by_micro_operations"] = [use]

                diagnostics = validate_extracted(make_extracted(signal))

                self.assertEqual(codes(diagnostics), [code])
                self.assertEqual(diagnostics[0].source_line, line)

    def test_micro_operation_use_value_is_optional(self) -> None:
        signal = make_signal()
        del signal["definition"]["used_by_micro_operations"][0]["value"]

        self.assertEqual(signal_codes(signal), [])

    def test_constraints_are_validated(self) -> None:
        signal = make_signal()
        signal["definition"]["constraints"] = [
            "x",
            {"text": "", "source": source_at(7)},
        ]

        diagnostics = validate_extracted(make_extracted(signal))

        self.assertEqual(
            codes(diagnostics), ["INVALID_CONSTRAINT", "INVALID_CONSTRAINT_TEXT"]
        )
        self.assertEqual([item.source_line for item in diagnostics], [2, 7])


# ---------------------------------------------------------------------------
# Maintained schema validation
# ---------------------------------------------------------------------------


class MaintainedValidationTests(unittest.TestCase):
    def test_missing_schema_is_allowed(self) -> None:
        self.assertEqual(validate_maintained(None), ([], {}))

    def test_roles_are_indexed_by_name(self) -> None:
        maintained = make_maintained(
            make_field("A"),
            make_field("B", "derived"),
            make_field("C", "external_input"),
        )

        self.assertEqual(
            validate_maintained(maintained),
            ([], {"A": "encoded", "B": "derived", "C": "external_input"}),
        )

    def test_header_is_validated(self) -> None:
        maintained = make_maintained()
        maintained.update(
            specification_type="x", schema_version=2, control_design_version="v2"
        )

        diagnostics, _ = validate_maintained(maintained)

        self.assertEqual(
            sorted(codes(diagnostics)),
            [
                "INVALID_MAINTAINED_DESIGN_VERSION",
                "INVALID_MAINTAINED_SPECIFICATION_TYPE",
                "UNSUPPORTED_MAINTAINED_SCHEMA_VERSION",
            ],
        )

    def test_fields_must_be_array(self) -> None:
        maintained = make_maintained()
        maintained["fields"] = {}

        self.assertEqual(
            validate_maintained(maintained)[0][0].code, "INVALID_MAINTAINED_FIELDS"
        )

    def test_invalid_fields_are_reported(self) -> None:
        maintained = make_maintained(
            "x",
            {"name": ""},
            make_field("A"),
            make_field("A"),
            {"name": "B"},
            make_field("C", "bad"),
            make_field("D", None),
        )

        diagnostics, _ = validate_maintained(maintained)

        self.assertEqual(
            codes(diagnostics),
            [
                "INVALID_MAINTAINED_FIELD",
                "INVALID_MAINTAINED_FIELD_NAME",
                "DUPLICATE_MAINTAINED_FIELD",
                "MISSING_CONTROL_WORD_ROLE",
                "INVALID_CONTROL_WORD_ROLE",
                "INVALID_CONTROL_WORD_ROLE",
            ],
        )
        self.assertEqual(
            [item.field_name for item in diagnostics],
            [None, None, "A", "B", "C", "D"],
        )


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


class CandidateTests(unittest.TestCase):
    def test_field_structure(self) -> None:
        """The full field, including key order, is part of the output format."""

        field = field_from_signal(make_signal(), "encoded")

        expected = {
            "name": "A",
            "category": "Enable Signals",
            "width": 1,
            "control_word_role": "encoded",
            "default_value": "0",
            "explicit_value_required": "Yes",
            "value_required_when": "Always",
            "attributes": {
                "mnemonic": "A",
                "display_name": "Signal A",
                "signal_class": "Enable",
                "purpose": "Test.",
            },
            "values": [
                {"encoding": "0", "meaning": "off", "source": source_out(3)},
                {"encoding": "1", "meaning": "on", "source": source_out(4)},
            ],
            "constraints": [{"text": "Only at TP.", "source": source_out(6)}],
            "used_by_micro_operations": [
                {
                    "micro_operation": "OP",
                    "value": "1",
                    "source": source_out(8),
                }
            ],
            "sources": {
                "index": {"document": INDEX, "line": 1},
                "definition": {"document": DOC, "section": "A", "line": 2},
            },
        }
        self.assertEqual(field, expected)
        self.assertEqual(json.dumps(field), json.dumps(expected))

    def test_micro_operation_use_without_value_omits_it(self) -> None:
        signal = make_signal()
        del signal["definition"]["used_by_micro_operations"][0]["value"]

        use = field_from_signal(signal, None)["used_by_micro_operations"][0]

        self.assertEqual(list(use), ["micro_operation", "source"])

    def test_not_applicable_default_becomes_null(self) -> None:
        signal = make_signal()
        signal["definition"]["attributes"]["default_value"] = "N/A"

        self.assertIsNone(field_from_signal(signal, None)["default_value"])

    def test_candidate_header(self) -> None:
        candidate, _ = build_candidate(make_extracted(), make_maintained(make_field()))

        self.assertEqual(
            {key: value for key, value in candidate.items() if key != "fields"},
            {
                "specification_type": "control-word-schema",
                "schema_version": 1,
                "control_design_version": "v1",
                "description": (
                    "Logical symbolic control-word schema for version 1 CPU control."
                ),
                "source": {
                    "specification_type": "control-output-extractor",
                    "format_version": 1,
                    "extraction_stage": "category-validation",
                },
            },
        )

    def test_maintained_role_is_preserved(self) -> None:
        candidate, diagnostics = build_candidate(
            make_extracted(), make_maintained(make_field("A", "derived"))
        )

        self.assertEqual(candidate["fields"][0]["control_word_role"], "derived")
        self.assertEqual(diagnostics, [])

    def test_unreviewed_field_is_unresolved(self) -> None:
        candidate, diagnostics = build_candidate(make_extracted(), None)

        self.assertIsNone(candidate["fields"][0]["control_word_role"])
        self.assertEqual(codes(diagnostics), ["CONTROL_WORD_ROLE_UNRESOLVED"])
        self.assertEqual(diagnostics[0].severity, "WARNING")
        self.assertEqual(diagnostics[0].field_name, "A")
        self.assertEqual(diagnostics[0].source_line, 2)

    def test_stale_maintained_field_is_reported(self) -> None:
        _, diagnostics = build_candidate(
            make_extracted(), make_maintained(make_field("A"), make_field("GONE"))
        )

        self.assertEqual(codes(diagnostics), ["STALE_MAINTAINED_FIELD"])
        self.assertEqual(diagnostics[0].field_name, "GONE")

    def test_fields_follow_extracted_order(self) -> None:
        candidate, _ = build_candidate(
            make_extracted(make_signal("B"), make_signal("A")), None
        )

        self.assertEqual([field["name"] for field in candidate["fields"]], ["B", "A"])

    def test_invalid_input_yields_no_candidate(self) -> None:
        for extracted, maintained in (
            ({**make_extracted(), "format_version": 2}, None),
            (make_extracted(), make_maintained(make_field("A", "bad"))),
        ):
            with self.subTest(maintained=maintained):
                candidate, diagnostics = build_candidate(extracted, maintained)

                self.assertIsNone(candidate)
                self.assertEqual(len(diagnostics), 1)


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
            [
                Diagnostic("WARNING", "CODE", "Message.", "A", DOC, 5),
                Diagnostic("ERROR", "OTHER", "Other.", source_line=7),
                Diagnostic("FATAL", "LAST", "Last."),
            ],
            3,
            False,
        )

        self.assertEqual(
            report,
            "Control-Word Schema Generation Report\n"
            "=====================================\n"
            "\n"
            "Fields processed: 3\n"
            "Candidate written: no\n"
            "Information diagnostics: 0\n"
            "Warnings: 1\n"
            "Errors: 1\n"
            "Fatal errors: 1\n"
            "\n"
            "Diagnostics\n"
            "-----------\n"
            f"WARNING CODE [A] {DOC}:5: Message.\n"
            "ERROR OTHER [-] 7: Other.\n"
            "FATAL LAST [-]: Last.\n",
        )

    def test_empty_report_says_no_diagnostics(self) -> None:
        report = build_report([], 0, True)

        self.assertIn("Candidate written: yes", report)
        self.assertTrue(report.endswith("No diagnostics.\n"))

    def test_failure_without_source_is_unknown(self) -> None:
        self.assertEqual(
            format_failure(Diagnostic("ERROR", "CODE", "Message.")),
            ["ERROR CODE", "  Source: <unknown source>", "  Message."],
        )


# ---------------------------------------------------------------------------
# Contract with the control-output extractor
# ---------------------------------------------------------------------------

EXTRACTOR_GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "control-output-extractor"
    / "tests"
    / "golden"
    / "valid"
    / "control-outputs.json"
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
        self.assertEqual(set(codes(diagnostics)), {"CONTROL_WORD_ROLE_UNRESOLVED"})
        self.assertEqual(
            [field["name"] for field in candidate["fields"]],
            [signal["name"] for signal in self.extracted["signals"]],
        )

    def test_test_signal_matches_extractor_signal_shape(self) -> None:
        real = self.extracted["signals"][0]
        test = make_signal()

        self.assertEqual(list(test), list(real))
        self.assertEqual(list(test["definition"]), list(real["definition"]))
        self.assertEqual(
            list(test["definition"]["attributes"]),
            list(real["definition"]["attributes"]),
        )
        for key in ("encodings", "constraints", "used_by_micro_operations"):
            with self.subTest(key=key):
                real_entries = [
                    entry
                    for signal in self.extracted["signals"]
                    for entry in signal["definition"][key]
                ]
                self.assertIn(
                    list(test["definition"][key][0]),
                    [list(entry) for entry in real_entries],
                )

    def test_test_extracted_matches_extractor_top_level_shape(self) -> None:
        self.assertEqual(list(make_extracted()), list(self.extracted))


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
        candidate, _ = build_candidate(make_extracted(), make_maintained(make_field()))
        self.assertEqual(
            self.candidate.read_text(encoding="utf-8"),
            json.dumps(candidate, indent=2, ensure_ascii=False) + "\n",
        )
        self.assertIn("No diagnostics.", self.report.read_text(encoding="utf-8"))
        self.assertIn("Status: SUCCEEDED", stdout)
        self.assertIn("Control outputs: 1", stdout)

    def test_missing_maintained_schema_succeeds_with_warnings(self) -> None:
        self.write_inputs(make_extracted(), None)

        exit_code, _ = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertTrue(self.candidate.exists())
        self.assertIn("Warnings: 1", self.report.read_text(encoding="utf-8"))

    def test_validation_error_prevents_candidate(self) -> None:
        signal = make_signal()
        signal["definition"]["bit_width"] = 0
        self.write_inputs(make_extracted(signal), make_maintained(make_field()))

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        self.assertIn("Candidate written: no", self.report.read_text(encoding="utf-8"))
        self.assertIn(
            f"ERROR INVALID_BIT_WIDTH [A]\n  Source: {DOC}:2\n"
            "  Definition bit_width must be a positive integer.\n",
            stdout,
        )

    def test_unreadable_input_is_fatal(self) -> None:
        self.write_inputs(None, make_maintained(make_field()))

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        report = self.report.read_text(encoding="utf-8")
        self.assertIn("Fatal errors: 1", report)
        self.assertIn("FATAL GENERATION_FAILURE [-]: Input file does not exist", report)
        self.assertIn("Control outputs: 0", stdout)

    def test_report_sorts_diagnostics(self) -> None:
        first = make_signal("Z")
        first["definition"]["source"] = source_at(1)
        first["definition"]["bit_width"] = 0
        second = copy.deepcopy(first)
        second["name"] = "Y"
        second["definition"]["source"] = source_at(9)
        maintained = make_maintained(make_field("Z", "bad"))
        maintained["schema_version"] = 2
        self.write_inputs(make_extracted(second, first), maintained)

        self.run_main()

        report = self.report.read_text(encoding="utf-8")
        details = report.split("-----------\n", 1)[1].splitlines()
        self.assertEqual(
            [line.split(": ")[0] for line in details],
            [
                "ERROR INVALID_BIT_WIDTH [Z] docs/defs.md:1",
                "ERROR INVALID_BIT_WIDTH [Y] docs/defs.md:9",
                "ERROR INVALID_CONTROL_WORD_ROLE [Z]",
                "ERROR UNSUPPORTED_MAINTAINED_SCHEMA_VERSION [-]",
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
