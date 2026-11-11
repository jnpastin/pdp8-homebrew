"""Tests for the direct-control generator."""

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

from generate_direct_control import (  # noqa: E402
    DEFAULT_CANDIDATE,
    DEFAULT_EXTRACTED,
    DEFAULT_INPUT_SCHEMA,
    DEFAULT_MAINTAINED,
    DEFAULT_MAPPING,
    DEFAULT_REPORT,
    DEFAULT_WORD_SCHEMA,
    Diagnostic,
    GenerationFailure,
    References,
    build_candidate,
    build_report,
    index_fields,
    index_mappings,
    legal_encodings,
    main,
    parse_arguments,
    read_json,
    resolve_constant,
    resolve_from_repo,
    resolve_symbol,
    review_changes,
    serialize_json,
    validate_definition,
    validate_extracted,
    validate_maintained,
    validate_references,
)

DOC = "docs/01-example.md"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_definition(identifier: str = "01:1.1", **fields) -> dict:
    """Return a definition in the direct-control extractor's form."""

    definition = {
        "id": identifier,
        "title": f"{identifier[3:]} Example",
        "group": "1 Group",
        "source": {"path": DOC, "line": 10},
        "applicable_context": ["MS = FETCH\nRUN = 1"],
        "direct_assignments": ["RUN_NEXT = 1"],
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
    definition.update(fields)
    return definition


def make_extracted(*definitions: dict) -> dict:
    return {
        "format_version": 1,
        "control_design_version": "v1",
        "artifact": "direct-control-definitions",
        "extraction_stage": "documentation-extraction",
        "sources": [DOC],
        "definitions": list(definitions),
        "diagnostics": [],
    }


def make_field(
    name: str,
    width: int = 1,
    role: str = "encoded",
    default: str = "0",
    meanings: tuple = ("off", "on"),
) -> dict:
    """Return a control-word field; ``meanings`` gives encodings 0, 1, ..."""

    return {
        "name": name,
        "width": width,
        "control_word_role": role,
        "default_value": default,
        "values": [
            {"encoding": str(number), "meaning": meaning}
            for number, meaning in enumerate(meanings)
        ],
    }


def make_input(name: str, width: int = 3, uses: tuple = ("value",)) -> dict:
    return {"name": name, "width": width, "control_uses": list(uses)}


def make_references(
    fields: list | None = None,
    inputs: list | None = None,
    mappings: dict | None = None,
) -> dict:
    """Return the three reference specifications."""

    fields = fields or [
        make_field("RUN_NEXT"),
        make_field("MS_NEXT", 3, meanings=("FETCH", "DEFER", "EXECUTE")),
        make_field("DF_VAL", 3, meanings=()),
        make_field("/RD", default="1"),
        make_field("GTF", role="derived"),
    ]
    inputs = inputs or [make_input("RUN", 1, ("predicate",)), make_input("IR_DF")]
    mappings = mappings or {"OP": [{"field": "/RD", "value": "0"}]}
    return {
        "inputs": {
            "specification_type": "control-input-schema",
            "control_design_version": "v1",
            "fields": inputs,
        },
        "word": {
            "specification_type": "control-word-schema",
            "control_design_version": "v1",
            "fields": fields,
        },
        "mapping": {
            "specification_type": "micro-operation-mapping",
            "control_design_version": "v1",
            "mappings": [
                {"micro_operation": name, "assignments": assignments}
                for name, assignments in mappings.items()
            ],
        },
    }


def indexed(references: dict | None = None) -> References:
    references = references or make_references()
    return References(
        fields=index_fields(references["word"]),
        inputs=index_fields(references["inputs"]),
        mappings=index_mappings(references["mapping"]),
    )


def check(**fields) -> list[tuple[str, str | None]]:
    """Return ``(code, field)`` for each finding in one definition."""

    return [
        (item.code, item.field_name)
        for item in validate_definition(make_definition(**fields), indexed())
    ]


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

        self.assertEqual(
            (
                options.extracted,
                options.maintained,
                options.control_input_schema,
                options.control_word_schema,
                options.micro_operation_mapping,
                options.candidate_output,
                options.report_output,
            ),
            (
                DEFAULT_EXTRACTED,
                DEFAULT_MAINTAINED,
                DEFAULT_INPUT_SCHEMA,
                DEFAULT_WORD_SCHEMA,
                DEFAULT_MAPPING,
                DEFAULT_CANDIDATE,
                DEFAULT_REPORT,
            ),
        )


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
        self.assertEqual(read_json(self.write('{"a": 1}')), {"a": 1})

    def test_missing_required_input_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "does not exist"):
            read_json(self.root / "missing.json")

    def test_missing_or_blank_optional_input_is_none(self) -> None:
        self.assertIsNone(read_json(self.root / "missing.json", optional=True))
        self.assertIsNone(read_json(self.write(" \n"), optional=True))

    def test_invalid_inputs_fail(self) -> None:
        for content, message in (
            ("{", "not valid JSON"),
            (b"\xff{}", "not valid UTF-8"),
            ("[]", "must be a JSON object"),
        ):
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(GenerationFailure, message),
            ):
                read_json(self.write(content))

    def test_unreadable_path_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "Unable to read input"):
            read_json(self.root, optional=True)


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


class ExtractedValidationTests(unittest.TestCase):
    def test_valid_artifact_is_indexed(self) -> None:
        diagnostics, definitions = validate_extracted(
            make_extracted(make_definition("01:1.2"), make_definition("01:1.1"))
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(list(definitions), ["01:1.2", "01:1.1"])

    def test_header_is_validated(self) -> None:
        data = make_extracted()
        del data["sources"]
        data.update(artifact="x", format_version=2, extraction_stage="x")

        diagnostics, _ = validate_extracted(data)

        self.assertEqual(
            codes(diagnostics),
            [
                "MISSING_TOP_LEVEL_FIELDS",
                "UNEXPECTED_ARTIFACT_TYPE",
                "UNSUPPORTED_FORMAT_VERSION",
                "UNSUPPORTED_EXTRACTION_STAGE",
            ],
        )
        self.assertEqual(
            diagnostics[0].message, "Extracted artifact is missing: sources"
        )

    def test_extractor_diagnostics_are_checked(self) -> None:
        for value, expected in (
            (None, ["INVALID_EXTRACTOR_DIAGNOSTICS"]),
            ([{"severity": "ERROR"}], ["EXTRACTOR_FAILURE_DIAGNOSTICS"]),
            ([{"severity": "WARNING"}], []),
        ):
            with self.subTest(value=value):
                data = make_extracted()
                data["diagnostics"] = value

                self.assertEqual(codes(validate_extracted(data)[0]), expected)

    def test_definitions_are_validated(self) -> None:
        bad_field = make_definition("01:1.3", direct_assignments="X = 1")
        data = make_extracted(
            1,
            make_definition(""),
            make_definition("01:1.1"),
            make_definition("01:1.1"),
            bad_field,
        )

        diagnostics, _ = validate_extracted(data)

        self.assertEqual(
            [(d.code, d.definition_id) for d in diagnostics],
            [
                ("INVALID_EXTRACTED_DEFINITIONS", None),
                ("INVALID_EXTRACTED_DEFINITIONS", None),
                ("INVALID_EXTRACTED_DEFINITIONS", "01:1.1"),
                ("INVALID_DEFINITION_FIELD", "01:1.3"),
            ],
        )

    def test_definitions_must_be_array(self) -> None:
        data = make_extracted()
        data["definitions"] = None

        self.assertEqual(
            codes(validate_extracted(data)[0]), ["INVALID_EXTRACTED_DEFINITIONS"]
        )


class MaintainedAndReferenceValidationTests(unittest.TestCase):
    def test_missing_maintained_artifact_is_allowed(self) -> None:
        self.assertEqual(validate_maintained(None, make_extracted()), ([], {}))

    def test_maintained_artifact_is_validated(self) -> None:
        maintained = make_extracted(make_definition(), make_definition())
        maintained["control_design_version"] = "v2"

        diagnostics, _ = validate_maintained(maintained, make_extracted())

        self.assertEqual(
            codes(diagnostics),
            ["CONTROL_DESIGN_VERSION_MISMATCH", "INVALID_MAINTAINED_DEFINITIONS"],
        )

    def test_reference_types_and_versions_are_checked(self) -> None:
        references = make_references()
        references["word"]["specification_type"] = "x"
        references["mapping"]["control_design_version"] = "v2"

        diagnostics = validate_references(make_extracted(), references)

        self.assertEqual(
            [(d.code, d.message) for d in diagnostics],
            [
                (
                    "INVALID_SPECIFICATION_TYPE",
                    "Expected word specification_type 'control-word-schema', "
                    "found 'x'.",
                ),
                (
                    "CONTROL_DESIGN_VERSION_MISMATCH",
                    "definitions='v1', inputs='v1', word='v1', mapping='v2'",
                ),
            ],
        )


# ---------------------------------------------------------------------------
# Review against the maintained artifact
# ---------------------------------------------------------------------------


class ReviewTests(unittest.TestCase):
    def test_new_changed_and_stale_definitions(self) -> None:
        extracted = {
            "01:1.1": make_definition("01:1.1"),
            "01:1.2": make_definition("01:1.2"),
            "01:1.3": make_definition("01:1.3"),
        }
        maintained = {
            "01:1.1": make_definition("01:1.1"),
            "01:1.2": make_definition("01:1.2", title="Old"),
            "01:9.9": make_definition("01:9.9"),
        }

        diagnostics = review_changes(extracted, maintained)

        self.assertEqual(
            [(d.severity, d.code, d.definition_id) for d in diagnostics],
            [
                ("WARNING", "CHANGED_DEFINITION", "01:1.2"),
                ("WARNING", "NEW_DEFINITION", "01:1.3"),
                ("WARNING", "STALE_DEFINITION", "01:9.9"),
            ],
        )


# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


class IndexTests(unittest.TestCase):
    def test_malformed_reference_entries_are_skipped(self) -> None:
        mapping = {
            "mappings": [
                1,
                {"assignments": []},
                {"micro_operation": "A", "assignments": None},
                {
                    "micro_operation": "B",
                    "assignments": [1, {"field": "F"}, {"field": "G", "value": 1}],
                },
            ]
        }

        self.assertEqual(index_mappings(mapping), {"A": {}, "B": {"G": "1"}})
        self.assertEqual(index_mappings({}), {})
        self.assertEqual(
            index_fields({"fields": [1, {"width": 1}, {"name": "X"}]}),
            {"X": {"name": "X"}},
        )


class ValueTests(unittest.TestCase):
    def test_legal_encodings(self) -> None:
        field = make_field("F", 2, meanings=("off", "on", "Reserved", "invalid"))

        self.assertEqual(legal_encodings(field), {"0", "1"})
        self.assertEqual(
            legal_encodings(make_field("F", 2, meanings=())), {"0", "1", "2", "3"}
        )
        self.assertEqual(legal_encodings({"name": "F"}), set())

    def test_symbols_match_meanings_exactly(self) -> None:
        field = make_field("MS_NEXT", 3, meanings=("FETCH", "Fetch Two", "EXECUTE"))

        self.assertEqual(resolve_symbol(field, "fetch"), "0")
        self.assertEqual(resolve_symbol(field, "FETCH_TWO"), "1")
        self.assertIsNone(resolve_symbol(field, "EXEC"))
        self.assertIsNone(resolve_symbol(make_field("X", meanings=("A", "a")), "A"))

    def test_symbols_come_only_from_schema_meanings(self) -> None:
        symbolic = make_field(
            "IOT_TRANSFER_VAL", 2, meanings=("NONE", "READ", "WRITE", "invalid")
        )
        prose = make_field("IOT_TRANSFER_VAL", 2, meanings=("no pending transfer",))

        self.assertEqual(
            [resolve_symbol(symbolic, token) for token in ("NONE", "READ", "WRITE")],
            ["0", "1", "2"],
        )
        self.assertIsNone(resolve_symbol(prose, "NONE"))

    def test_constants_are_resolved_and_checked(self) -> None:
        on_off = make_field("RUN_NEXT")
        wide = make_field("DF_VAL", 3, meanings=())

        self.assertEqual(resolve_constant(on_off, "1", "x"), ("1", []))
        self.assertEqual(resolve_constant(on_off, "on", "x"), ("1", []))
        for field, token, code, message in (
            (
                on_off,
                "2",
                "VALUE_OUT_OF_RANGE",
                "RUN_NEXT value 2 is not a legal encoding.",
            ),
            (wide, "9", "VALUE_OUT_OF_RANGE", "DF_VAL value 9 does not fit width 3."),
            (
                on_off,
                "maybe",
                "UNKNOWN_CONTROL_VALUE",
                "Cannot resolve RUN_NEXT value 'maybe' against the control-word "
                "schema.",
            ),
        ):
            with self.subTest(token=token):
                value, diagnostics = resolve_constant(field, token, "x")

                self.assertIsNone(value)
                self.assertEqual(
                    [(d.code, d.message) for d in diagnostics], [(code, message)]
                )


# ---------------------------------------------------------------------------
# Definition validation
# ---------------------------------------------------------------------------


class DefinitionValidationTests(unittest.TestCase):
    def test_valid_definition_has_no_findings(self) -> None:
        self.assertEqual(check(), [])

    def test_assignments_are_checked(self) -> None:
        self.assertEqual(
            check(
                direct_assignments=[
                    "NOPE = 1\nGTF = 0\nMS_NEXT = EXECUTE\nRUN_NEXT = 0\n\n"
                    "RUN_NEXT = 1\nRUN_NEXT <- 1"
                ]
            ),
            [
                ("MALFORMED_ASSIGNMENT", None),
                ("UNKNOWN_CONTROL_FIELD", "NOPE"),
                ("NON_ENCODED_CONTROL_FIELD", "GTF"),
                ("CONFLICTING_ASSIGNMENT", "RUN_NEXT"),
            ],
        )

    def test_context_symbols_are_checked(self) -> None:
        self.assertEqual(
            check(
                applicable_context=[
                    "MS = FETCH\nTS = 4\nRUN = 1\n/RD = 0\nNOT (\nBOGUS != 1",
                    "OP is selected\nOTHER is selected",
                ]
            ),
            [
                ("UNKNOWN_CONTEXT_SYMBOL", "BOGUS"),
                ("UNKNOWN_MICRO_OPERATION", None),
            ],
        )

    def test_micro_operation_assignments_follow_selected_mappings(self) -> None:
        context = ["OP is selected\nOTHER is selected"]

        self.assertEqual(
            check(
                applicable_context=context,
                direct_assignments=[],
                micro_operation_assignments=["/RD = 0\nRUN_NEXT = 0"],
            ),
            [("UNKNOWN_MICRO_OPERATION", None)],
        )
        self.assertEqual(
            check(
                applicable_context=context,
                direct_assignments=[],
                micro_operation_assignments=["RUN_NEXT = 1"],
            ),
            [
                ("UNKNOWN_MICRO_OPERATION", None),
                ("MICRO_OPERATION_ASSIGNMENT_MISMATCH", "RUN_NEXT"),
            ],
        )

    def test_micro_operation_assignments_without_selection_are_unchecked(
        self,
    ) -> None:
        self.assertEqual(
            check(direct_assignments=[], micro_operation_assignments=["RUN_NEXT = 1"]),
            [],
        )

    def test_direct_and_micro_operation_assignments_must_agree(self) -> None:
        self.assertEqual(
            check(
                direct_assignments=["/RD = 1"],
                micro_operation_assignments=["/RD = 0"],
            ),
            [("CROSS_DOMAIN_ASSIGNMENT_CONFLICT", "/RD")],
        )

    def test_control_supplied_values(self) -> None:
        self.assertEqual(
            check(
                control_supplied_values=[
                    "DF_VAL = IR_DF\nDF_VAL = 7\nRUN_NEXT = on\n"
                    "DF_VAL = 8\nDF_VAL = IR_DFF\nNOPE = 1\nGTF = IR_DF\nDF_VAL = RUN"
                ]
            ),
            [
                ("VALUE_OUT_OF_RANGE", "DF_VAL"),
                ("UNKNOWN_VALUE_SOURCE", "DF_VAL"),
                ("UNKNOWN_CONTROL_FIELD", "NOPE"),
                ("NON_ENCODED_CONTROL_FIELD", "GTF"),
                ("INPUT_NOT_VALUE_CAPABLE", "DF_VAL"),
                ("VALUE_WIDTH_MISMATCH", "DF_VAL"),
            ],
        )


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


class CandidateTests(unittest.TestCase):
    def test_candidate_structure(self) -> None:
        definitions = [make_definition("01:1.2"), make_definition("01:1.1")]

        candidate, diagnostics = build_candidate(
            make_extracted(*definitions), None, make_references()
        )

        self.assertEqual(codes(diagnostics), ["NEW_DEFINITION", "NEW_DEFINITION"])
        self.assertEqual(
            candidate,
            {
                "format_version": 1,
                "control_design_version": "v1",
                "artifact": "direct-control-definitions",
                "generation_stage": "candidate-generation",
                "sources": [DOC],
                "definitions": definitions,
                "diagnostics": [],
            },
        )

    def test_unchanged_maintained_artifact_has_no_findings(self) -> None:
        extracted = make_extracted(make_definition())

        candidate, diagnostics = build_candidate(
            extracted, copy.deepcopy(extracted), make_references()
        )

        self.assertIsNotNone(candidate)
        self.assertEqual(diagnostics, [])

    def test_structural_errors_stop_before_review(self) -> None:
        extracted = make_extracted(make_definition())
        extracted["format_version"] = 2
        references = make_references()
        references["inputs"]["specification_type"] = "x"

        candidate, diagnostics = build_candidate(extracted, None, references)

        self.assertIsNone(candidate)
        self.assertEqual(
            codes(diagnostics),
            ["UNSUPPORTED_FORMAT_VERSION", "INVALID_SPECIFICATION_TYPE"],
        )

    def test_definition_errors_prevent_candidate(self) -> None:
        candidate, diagnostics = build_candidate(
            make_extracted(make_definition(direct_assignments=["NOPE = 1"])),
            None,
            make_references(),
        )

        self.assertIsNone(candidate)
        self.assertEqual(
            codes(diagnostics), ["NEW_DEFINITION", "UNKNOWN_CONTROL_FIELD"]
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OutputTests(unittest.TestCase):
    def test_report(self) -> None:
        report = build_report(
            [
                Diagnostic("WARNING", "W", "Warn.", "01:1"),
                Diagnostic("ERROR", "E", "Err.", "01:2", "F"),
                Diagnostic("FATAL", "X", "Fatal."),
            ],
            2,
            False,
        )

        self.assertEqual(
            report,
            "Direct-Control Candidate Generation Report\n"
            "==========================================\n"
            "\n"
            "Definitions processed: 2\n"
            "Candidate written: no\n"
            "Information diagnostics: 0\n"
            "Warnings: 1\n"
            "Errors: 1\n"
            "Fatal errors: 1\n"
            "\n"
            "Diagnostics\n"
            "-----------\n"
            "WARNING W [01:1]: Warn.\n"
            "ERROR E [01:2] [F]: Err.\n"
            "FATAL X: Fatal.\n",
        )

    def test_empty_report_says_no_diagnostics(self) -> None:
        self.assertTrue(build_report([], 0, True).endswith("No diagnostics.\n"))


# ---------------------------------------------------------------------------
# Contract with the direct-control extractor
# ---------------------------------------------------------------------------

EXTRACTOR_GOLDEN = (
    Path(__file__).resolve().parents[2]
    / "direct-control-extractor"
    / "tests"
    / "golden"
    / "valid"
    / "direct-control-definitions.json"
)


class ExtractorContractTests(unittest.TestCase):
    """Keep this tool's input in step with the extractor's real output.

    The extractor's golden output is the reference. If these tests fail
    after an extractor change, update this tool (and its builders) to match.
    """

    def setUp(self) -> None:
        self.extracted = json.loads(EXTRACTOR_GOLDEN.read_text(encoding="utf-8"))

    def test_extractor_output_passes_structural_validation(self) -> None:
        self.assertEqual(validate_extracted(self.extracted)[0], [])

    def test_builders_match_extractor_shapes(self) -> None:
        self.assertEqual(list(make_extracted()), list(self.extracted))
        self.assertEqual(
            list(make_definition()), list(self.extracted["definitions"][0])
        )


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

    def write_inputs(
        self,
        extracted: dict | None,
        maintained: dict | None = None,
        references: dict | None = None,
    ) -> None:
        references = references or make_references()
        files = {
            "extracted.json": extracted,
            "maintained.json": maintained,
            "inputs.json": references["inputs"],
            "word.json": references["word"],
            "mapping.json": references["mapping"],
        }
        for name, data in files.items():
            if data is not None:
                (self.root / name).write_text(json.dumps(data), encoding="utf-8")

    def run_main(self, *extra: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "--repo-root", str(self.root),
                    "--extracted", "extracted.json",
                    "--maintained", "maintained.json",
                    "--control-input-schema", "inputs.json",
                    "--control-word-schema", "word.json",
                    "--micro-operation-mapping", "mapping.json",
                    "--candidate-output", "out/candidate.json",
                    "--report-output", "out/report.txt",
                    *extra,
                ]
            )  # fmt: skip
        return exit_code, stdout.getvalue()

    def test_successful_run_writes_candidate_and_report(self) -> None:
        extracted = make_extracted(make_definition())
        self.write_inputs(extracted, extracted)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        expected, _ = build_candidate(extracted, None, make_references())
        self.assertEqual(
            self.candidate.read_text(encoding="utf-8"), serialize_json(expected)
        )
        self.assertIn("No diagnostics.", self.report.read_text(encoding="utf-8"))
        self.assertIn("Status: SUCCEEDED", stdout)
        self.assertIn("Definitions: 1", stdout)

    def test_failed_run_removes_previous_candidate(self) -> None:
        self.write_inputs(make_extracted(make_definition()))
        self.assertEqual(self.run_main()[0], 0)
        self.write_inputs(
            make_extracted(make_definition(direct_assignments=["RUN_NEXT = 5"]))
        )

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        self.assertIn(
            "ERROR VALUE_OUT_OF_RANGE [01:1.1] [RUN_NEXT]\n"
            "  RUN_NEXT value 5 is not a legal encoding.\n",
            stdout,
        )

    def test_unreadable_input_is_fatal(self) -> None:
        self.write_inputs(None)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        report = self.report.read_text(encoding="utf-8")
        self.assertIn("FATAL GENERATION_FAILURE: Required input does not exist", report)
        self.assertIn("Definitions: 0", stdout)

    def test_report_sorts_diagnostics(self) -> None:
        self.write_inputs(
            make_extracted(
                make_definition("01:1.2", direct_assignments=["NOPE = 1"]),
                make_definition("01:1.1", direct_assignments=["RUN_NEXT = 2"]),
            )
        )

        self.run_main()

        details = self.report.read_text(encoding="utf-8").split("-----------\n", 1)[1]
        self.assertEqual(
            [line.split(": ")[0] for line in details.splitlines()],
            [
                "WARNING NEW_DEFINITION [01:1.1]",
                "WARNING NEW_DEFINITION [01:1.2]",
                "ERROR UNKNOWN_CONTROL_FIELD [01:1.2] [NOPE]",
                "ERROR VALUE_OUT_OF_RANGE [01:1.1] [RUN_NEXT]",
            ],
        )

    def test_output_that_is_an_input_is_refused(self) -> None:
        self.write_inputs(make_extracted(make_definition()))
        word = (self.root / "word.json").read_bytes()

        exit_code, stdout = self.run_main("--candidate-output", "word.json")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout)
        self.assertEqual((self.root / "word.json").read_bytes(), word)
        self.assertFalse(self.report.exists())

    def test_output_that_is_a_directory_is_refused(self) -> None:
        self.write_inputs(make_extracted(make_definition()))
        self.report.parent.mkdir()
        self.report.write_text("earlier\n", encoding="utf-8")
        (self.root / "dir").mkdir()

        exit_code, stdout = self.run_main("--candidate-output", "dir")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout)
        self.assertTrue(self.report.exists())


if __name__ == "__main__":
    unittest.main()
