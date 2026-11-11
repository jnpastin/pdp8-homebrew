"""Tests for the micro-operation mapping generator."""

from __future__ import annotations

import copy
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_micro_operation_mapping import (  # noqa: E402
    DEFAULT_CANDIDATE_OUTPUT,
    DEFAULT_CONTROL_WORD_SCHEMA,
    DEFAULT_MAINTAINED_MAPPING,
    DEFAULT_MICRO_OPERATIONS,
    DEFAULT_REPORT_OUTPUT,
    Diagnostic,
    GenerationFailure,
    build_candidate,
    build_report,
    format_failure,
    legal_encodings,
    main,
    parse_arguments,
    read_json,
    resolve_from_repo,
    serialize_json,
    validate_maintained,
    validate_micro_operations,
    validate_schema,
)

UOPS = "docs/uops.md"
CONTROL = "docs/control.md"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_operation(name: str = "PC_INC", line: int = 10) -> dict:
    """Return a micro-operation in the micro-operation extractor's form."""

    return {
        "name": name,
        "category": "Control Flow",
        "description": "Increment PC.",
        "targets": ["PC"],
        "expression": ["PC ← PC + 1"],
        "sources": ["PC"],
        "preconditions": [],
        "constraints": [],
        "source": {"path": UOPS, "heading": name, "line": line},
        "extraction_status": "definition-validated",
    }


def make_micro_operations(*operations: dict) -> dict:
    return {
        "format_version": 1,
        "extraction_stage": "definition-validation",
        "source": {"path": UOPS},
        "micro_operations": list(operations) or [make_operation()],
        "diagnostics": [],
    }


def use(operation: str = "PC_INC", value: str | None = "1", line: int = 20) -> dict:
    """Return a Used-by entry in the control-word schema's form."""

    entry = {"micro_operation": operation}
    if value is not None:
        entry["value"] = value
    entry["source"] = {"document": CONTROL, "line": line}
    return entry


def make_field(
    name: str = "PC_INC",
    uses: list | None = None,
    role: str = "encoded",
    values: list | None = None,
    width: int = 1,
) -> dict:
    """Return a control field in the control-word schema's form."""

    return {
        "name": name,
        "category": "Enable Signals",
        "width": width,
        "control_word_role": role,
        "default_value": "0",
        "explicit_value_required": "Yes",
        "value_required_when": "Always",
        "attributes": {},
        "values": (
            values
            if values is not None
            else [
                {
                    "encoding": "0",
                    "meaning": "off",
                    "source": {"document": CONTROL, "line": 2},
                },
                {
                    "encoding": "1",
                    "meaning": "on",
                    "source": {"document": CONTROL, "line": 3},
                },
            ]
        ),
        "constraints": [],
        "used_by_micro_operations": [use()] if uses is None else uses,
        "sources": {
            "index": {"document": "docs/index.md", "line": 1},
            "definition": {"document": CONTROL, "section": name, "line": 1},
        },
    }


def make_schema(*fields: dict) -> dict:
    return {
        "specification_type": "control-word-schema",
        "schema_version": 1,
        "control_design_version": "v1",
        "description": "Schema.",
        "source": {},
        "fields": list(fields) or [make_field()],
    }


def make_mapping(
    name: str = "PC_INC",
    assignments: list | None = None,
    notes: list | None = None,
) -> dict:
    return {
        "micro_operation": name,
        "assignments": (
            [{"field": "PC_INC", "value": "1"}] if assignments is None else assignments
        ),
        "source": {"document": "old.md", "section": name, "line": 99},
        "notes": notes or [],
    }


def make_maintained(*mappings: dict) -> dict:
    return {
        "specification_type": "micro-operation-mapping",
        "schema_version": 1,
        "control_design_version": "v1",
        "mappings": list(mappings),
    }


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


def build(*fields: dict, operations: list | None = None, maintained=None):
    return build_candidate(
        make_micro_operations(*(operations or [])), make_schema(*fields), maintained
    )


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

        self.assertEqual(options.micro_operations, DEFAULT_MICRO_OPERATIONS)
        self.assertEqual(options.control_word_schema, DEFAULT_CONTROL_WORD_SCHEMA)
        self.assertEqual(options.maintained_mapping, DEFAULT_MAINTAINED_MAPPING)
        self.assertEqual(options.candidate_output, DEFAULT_CANDIDATE_OUTPUT)
        self.assertEqual(options.report_output, DEFAULT_REPORT_OUTPUT)


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

    def test_invalid_json_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "not valid JSON: .*line 1"):
            read_json(self.write("{"))

    def test_invalid_utf8_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "not valid UTF-8"):
            read_json(self.write(b"\xff{}"))

    def test_non_object_json_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "top-level JSON object"):
            read_json(self.write("[]"))

    def test_unreadable_path_fails(self) -> None:
        with self.assertRaisesRegex(GenerationFailure, "Unable to read input"):
            read_json(self.root, optional=True)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class MicroOperationValidationTests(unittest.TestCase):
    def test_valid_catalog_has_no_diagnostics(self) -> None:
        self.assertEqual(validate_micro_operations(make_micro_operations()), [])

    def test_header_is_validated(self) -> None:
        data = make_micro_operations()
        data.update(format_version=2, extraction_stage="x", diagnostics=[{}])

        self.assertEqual(
            sorted(codes(validate_micro_operations(data))),
            [
                "EXTRACTOR_DIAGNOSTICS_PRESENT",
                "UNSUPPORTED_EXTRACTION_STAGE",
                "UNSUPPORTED_MICRO_OPERATION_FORMAT",
            ],
        )

    def test_micro_operations_must_be_array(self) -> None:
        for value in (None, {}):
            with self.subTest(value=value):
                data = make_micro_operations()
                data["micro_operations"] = value

                self.assertEqual(
                    codes(validate_micro_operations(data)), ["INVALID_MICRO_OPERATIONS"]
                )

    def test_unusable_entries_stop_at_first_problem(self) -> None:
        nameless = make_operation()
        nameless["name"] = ""
        nameless["extraction_status"] = "x"

        diagnostics = validate_micro_operations(make_micro_operations(nameless, "x"))

        self.assertEqual(
            codes(diagnostics),
            ["INVALID_MICRO_OPERATION_NAME", "INVALID_MICRO_OPERATION"],
        )
        self.assertEqual(diagnostics[0].source_line, 10)

    def test_entries_are_validated(self) -> None:
        operation = make_operation()
        operation["extraction_status"] = "definition-error"
        del operation["targets"]
        operation["source"] = {"path": UOPS, "line": 10}

        diagnostics = validate_micro_operations(
            make_micro_operations(operation, make_operation())
        )

        self.assertEqual(
            sorted(codes(diagnostics)),
            [
                "DUPLICATE_MICRO_OPERATION",
                "INVALID_EXTRACTION_STATUS",
                "INVALID_MICRO_OPERATION_SOURCE",
                "MISSING_MICRO_OPERATION_PROPERTY",
            ],
        )


class SchemaValidationTests(unittest.TestCase):
    def test_valid_schema_is_indexed(self) -> None:
        diagnostics, fields = validate_schema(
            make_schema(make_field("A"), make_field("B"))
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(list(fields), ["A", "B"])

    def test_header_is_validated(self) -> None:
        schema = make_schema()
        schema.update(
            specification_type="x", schema_version=2, control_design_version="v2"
        )

        self.assertEqual(
            sorted(codes(validate_schema(schema)[0])),
            [
                "CONTROL_DESIGN_VERSION_MISMATCH",
                "INVALID_CONTROL_SCHEMA_TYPE",
                "UNSUPPORTED_CONTROL_SCHEMA_VERSION",
            ],
        )

    def test_fields_must_be_array(self) -> None:
        schema = make_schema()
        schema["fields"] = {}

        self.assertEqual(codes(validate_schema(schema)[0]), ["INVALID_CONTROL_FIELDS"])

    def test_invalid_fields_are_reported(self) -> None:
        bad = make_field("B")
        bad.update(
            control_word_role="x", explicit_value_required="x", value_required_when=None
        )

        diagnostics, _ = validate_schema(
            make_schema("x", {"name": ""}, make_field("A"), make_field("A"), bad)
        )

        self.assertEqual(
            codes(diagnostics),
            [
                "INVALID_CONTROL_FIELD",
                "INVALID_CONTROL_FIELD_NAME",
                "DUPLICATE_CONTROL_FIELD",
                "INVALID_CONTROL_WORD_ROLE",
                "INVALID_EXPLICIT_VALUE_REQUIREMENT",
                "INVALID_VALUE_REQUIRED_WHEN",
            ],
        )

    def test_used_by_must_be_array(self) -> None:
        for value in (None, "PC_INC"):
            with self.subTest(value=value):
                field = make_field()
                field["used_by_micro_operations"] = value

                self.assertEqual(
                    codes(validate_schema(make_schema(field))[0]),
                    ["INVALID_USED_BY_MICRO_OPERATIONS"],
                )

    def test_used_by_entries_are_validated(self) -> None:
        uses = [
            "PC_INC",
            {"micro_operation": ""},
            use("A", line=21),
            use("A", "0", line=22),
            use("B", "", line=23),
            {"micro_operation": "C", "value": 1},
        ]

        diagnostics, _ = validate_schema(make_schema(make_field(uses=uses)))

        self.assertEqual(
            codes(diagnostics),
            [
                "INVALID_USED_BY_MICRO_OPERATION",
                "INVALID_USED_BY_MICRO_OPERATION",
                "DUPLICATE_USED_BY_MICRO_OPERATION",
                "INVALID_USED_BY_VALUE",
                "INVALID_USED_BY_VALUE",
            ],
        )
        self.assertEqual(diagnostics[2].field_name, "PC_INC")


class MaintainedValidationTests(unittest.TestCase):
    def test_missing_mapping_is_allowed(self) -> None:
        self.assertEqual(validate_maintained(None), ([], {}))

    def test_mappings_are_indexed_by_name(self) -> None:
        diagnostics, mappings = validate_maintained(
            make_maintained(make_mapping("A"), make_mapping("B"))
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(list(mappings), ["A", "B"])

    def test_header_is_validated(self) -> None:
        data = make_maintained()
        data.update(
            specification_type="x", schema_version=2, control_design_version="v2"
        )

        self.assertEqual(
            sorted(codes(validate_maintained(data)[0])),
            [
                "INVALID_MAPPING_TYPE",
                "MAPPING_DESIGN_VERSION_MISMATCH",
                "UNSUPPORTED_MAPPING_VERSION",
            ],
        )

    def test_mappings_must_be_array(self) -> None:
        data = make_maintained()
        data["mappings"] = None

        self.assertEqual(codes(validate_maintained(data)[0]), ["INVALID_MAPPINGS"])

    def test_invalid_mappings_are_reported(self) -> None:
        bad = make_mapping("C", assignments=[{"field": "PC_INC", "value": None}])
        bad["notes"] = None

        diagnostics, _ = validate_maintained(
            make_maintained(
                1,
                {"micro_operation": ""},
                make_mapping("A"),
                make_mapping("A"),
                make_mapping("B", assignments={}),
                bad,
            )
        )

        self.assertEqual(
            codes(diagnostics),
            [
                "INVALID_MAPPING",
                "INVALID_MAPPING_NAME",
                "DUPLICATE_MAPPING",
                "INVALID_ASSIGNMENTS",
                "INVALID_MAINTAINED_ASSIGNMENT",
                "INVALID_NOTES",
            ],
        )
        self.assertEqual(
            [item.micro_operation for item in diagnostics][2:],
            ["A", "B", "C", "C"],
        )


# ---------------------------------------------------------------------------
# Candidate construction
# ---------------------------------------------------------------------------


class LegalEncodingTests(unittest.TestCase):
    def test_documented_encodings_exclude_reserved_and_invalid(self) -> None:
        values = [
            {"encoding": "0", "meaning": "off"},
            {"encoding": "1", "meaning": "Reserved"},
            {"encoding": "2", "meaning": "invalid"},
            {"encoding": 3},
        ]

        self.assertEqual(legal_encodings(make_field(values=values)), {"0"})

    def test_width_gives_all_octal_values(self) -> None:
        self.assertEqual(
            legal_encodings(make_field(values=[], width=3)),
            {"0", "1", "2", "3", "4", "5", "6", "7"},
        )

    def test_no_encodings_or_width_is_unchecked(self) -> None:
        self.assertIsNone(legal_encodings(make_field(values=[], width=0)))


class CandidateTests(unittest.TestCase):
    def test_candidate_structure(self) -> None:
        candidate, diagnostics = build(
            maintained=make_maintained(make_mapping(notes=["reviewed"]))
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            candidate,
            {
                "specification_type": "micro-operation-mapping",
                "schema_version": 1,
                "control_design_version": "v1",
                "description": (
                    "Maps documented micro-operations to symbolic control-field "
                    "assignments."
                ),
                "sources": {
                    "micro_operations": DEFAULT_MICRO_OPERATIONS.as_posix(),
                    "control_word_schema": DEFAULT_CONTROL_WORD_SCHEMA.as_posix(),
                },
                "mappings": [
                    {
                        "micro_operation": "PC_INC",
                        "assignments": [{"field": "PC_INC", "value": "1"}],
                        "source": {"document": UOPS, "section": "PC_INC", "line": 10},
                        "notes": ["reviewed"],
                    }
                ],
                "diagnostics": [],
            },
        )

    def test_assignments_follow_schema_field_order(self) -> None:
        candidate, _ = build(
            make_field("B", [use(value="0")]),
            make_field("NONE", []),
            make_field("A", [use(value="1")]),
        )

        self.assertEqual(
            candidate["mappings"][0]["assignments"],
            [{"field": "B", "value": "0"}, {"field": "A", "value": "1"}],
        )

    def test_mappings_follow_catalog_order(self) -> None:
        candidate, _ = build(
            make_field(uses=[use("A"), use("B")]),
            operations=[make_operation("B"), make_operation("A")],
        )

        self.assertEqual(
            [mapping["micro_operation"] for mapping in candidate["mappings"]],
            ["B", "A"],
        )

    def test_used_by_value_overrides_maintained_value(self) -> None:
        candidate, diagnostics = build(
            maintained=make_maintained(
                make_mapping(assignments=[{"field": "PC_INC", "value": "0"}])
            )
        )

        self.assertEqual(
            candidate["mappings"][0]["assignments"], [{"field": "PC_INC", "value": "1"}]
        )
        self.assertEqual(
            [(d.code, d.severity, d.field_name, d.message) for d in diagnostics],
            [
                (
                    "MAINTAINED_ASSIGNMENT_CHANGED",
                    "WARNING",
                    "PC_INC",
                    "Assignment PC_INC changes from '0' to '1'.",
                )
            ],
        )

    def test_maintained_differences_are_listed_in_order(self) -> None:
        _, diagnostics = build(
            make_field("NEW_B", [use(value="1")]),
            make_field("KEPT", [use(value="1")]),
            make_field("NEW_A", [use(value="0")]),
            make_field("CHANGED", [use(value="1")]),
            maintained=make_maintained(
                make_mapping(
                    assignments=[
                        {"field": "GONE", "value": "1"},
                        {"field": "CHANGED", "value": "0"},
                        {"field": "KEPT", "value": "1"},
                    ]
                )
            ),
        )

        self.assertEqual(
            [(d.code, d.field_name) for d in diagnostics],
            [
                ("MAINTAINED_ASSIGNMENT_REMOVED", "GONE"),
                ("MAINTAINED_ASSIGNMENT_CHANGED", "CHANGED"),
                ("MAINTAINED_ASSIGNMENT_ADDED", "NEW_B"),
                ("MAINTAINED_ASSIGNMENT_ADDED", "NEW_A"),
            ],
        )
        self.assertEqual(
            diagnostics[2].message,
            "Assignment NEW_B='1' is not in the maintained mapping.",
        )

    def test_new_micro_operation_reports_no_additions(self) -> None:
        _, diagnostics = build(maintained=make_maintained())

        self.assertEqual(diagnostics, [])

    def test_dropped_maintained_assignment_is_a_warning(self) -> None:
        candidate, diagnostics = build(
            maintained=make_maintained(
                make_mapping(
                    assignments=[
                        {"field": "PC_INC", "value": "1"},
                        {"field": "OLD_FIELD", "value": "2"},
                    ]
                )
            )
        )

        self.assertEqual(
            candidate["mappings"][0]["assignments"], [{"field": "PC_INC", "value": "1"}]
        )
        self.assertEqual(codes(diagnostics), ["MAINTAINED_ASSIGNMENT_REMOVED"])
        self.assertEqual(
            (diagnostics[0].micro_operation, diagnostics[0].field_name),
            ("PC_INC", "OLD_FIELD"),
        )
        self.assertEqual(diagnostics[0].source_line, 10)
        self.assertEqual(
            [item["code"] for item in candidate["diagnostics"]],
            ["MAINTAINED_ASSIGNMENT_REMOVED"],
        )

    def test_missing_used_by_value_uses_maintained_value(self) -> None:
        candidate, diagnostics = build(
            make_field(uses=[use(value=None)]),
            maintained=make_maintained(
                make_mapping(assignments=[{"field": "PC_INC", "value": "0"}])
            ),
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            candidate["mappings"][0]["assignments"], [{"field": "PC_INC", "value": "0"}]
        )

    def test_missing_value_without_reviewed_value_is_an_error(self) -> None:
        candidate, diagnostics = build(make_field(uses=[use(value=None, line=21)]))

        self.assertIsNone(candidate)
        self.assertEqual(
            codes(diagnostics), ["MAPPING_VALUE_UNRESOLVED", "MAPPING_UNRESOLVED"]
        )
        self.assertEqual(
            (diagnostics[0].micro_operation, diagnostics[0].field_name),
            ("PC_INC", "PC_INC"),
        )
        self.assertEqual(diagnostics[0].source_line, 21)

    def test_non_encoded_fields_cannot_be_assigned(self) -> None:
        for role in ("derived", "external_input"):
            with self.subTest(role=role):
                candidate, diagnostics = build(make_field(role=role))

                self.assertIsNone(candidate)
                self.assertEqual(codes(diagnostics), ["NON_ENCODED_ASSIGNMENT"])
                self.assertEqual(diagnostics[0].source_line, 10)

    def test_illegal_value_is_an_error(self) -> None:
        candidate, diagnostics = build(make_field(uses=[use(value="2")]))

        self.assertIsNone(candidate)
        self.assertEqual(codes(diagnostics), ["INVALID_ASSIGNED_VALUE"])

    def test_undefined_used_by_micro_operation_is_an_error(self) -> None:
        candidate, diagnostics = build(make_field(uses=[use(), use("GONE", line=22)]))

        self.assertIsNone(candidate)
        self.assertEqual(codes(diagnostics), ["UNDEFINED_USED_BY_MICRO_OPERATION"])
        self.assertEqual(
            (diagnostics[0].micro_operation, diagnostics[0].field_name),
            ("GONE", "PC_INC"),
        )

    def test_unresolved_and_stale_mappings_are_warnings(self) -> None:
        candidate, diagnostics = build(
            make_field(uses=[]), maintained=make_maintained(make_mapping("OLD"))
        )

        self.assertEqual(candidate["mappings"][0]["assignments"], [])
        self.assertEqual(
            codes(diagnostics), ["MAPPING_UNRESOLVED", "STALE_MAINTAINED_MAPPING"]
        )
        self.assertEqual(
            [item["code"] for item in candidate["diagnostics"]],
            ["MAPPING_UNRESOLVED", "STALE_MAINTAINED_MAPPING"],
        )

    def test_invalid_inputs_yield_no_candidate_and_are_all_reported(self) -> None:
        micro_operations = make_micro_operations()
        micro_operations["format_version"] = 2
        schema = make_schema()
        schema["schema_version"] = 2
        maintained = make_maintained()
        maintained["schema_version"] = 2

        candidate, diagnostics = build_candidate(micro_operations, schema, maintained)

        self.assertIsNone(candidate)
        self.assertEqual(
            sorted(codes(diagnostics)),
            [
                "UNSUPPORTED_CONTROL_SCHEMA_VERSION",
                "UNSUPPORTED_MAPPING_VERSION",
                "UNSUPPORTED_MICRO_OPERATION_FORMAT",
            ],
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OutputTests(unittest.TestCase):
    def test_json_is_unescaped_with_one_trailing_newline(self) -> None:
        text = serialize_json({"a": "μ"})

        self.assertEqual(text, '{\n  "a": "μ"\n}\n')

    def test_report(self) -> None:
        report = build_report(
            [
                Diagnostic("WARNING", "W", "Warn.", "A"),
                Diagnostic("ERROR", "E", "Err.", "B", "F", UOPS, 3),
                Diagnostic("FATAL", "X", "Fatal."),
            ],
            2,
            False,
        )

        self.assertEqual(
            report,
            "Micro-Operation Mapping Generation Report\n"
            "=========================================\n"
            "\n"
            "Mappings processed: 2\n"
            "Candidate written: no\n"
            "Information diagnostics: 0\n"
            "Warnings: 1\n"
            "Errors: 1\n"
            "Fatal errors: 1\n"
            "\n"
            "Diagnostics\n"
            "-----------\n"
            "WARNING W [A]: Warn.\n"
            "ERROR E [B] [F]: Err.\n"
            "FATAL X [-]: Fatal.\n",
        )

    def test_empty_report_says_no_diagnostics(self) -> None:
        self.assertTrue(build_report([], 0, True).endswith("No diagnostics.\n"))

    def test_failure_formatting(self) -> None:
        self.assertEqual(
            format_failure(Diagnostic("ERROR", "E", "Err.", "B", "F", UOPS, 3)),
            ["ERROR E [B] [F]", f"  Source: {UOPS}:3", "  Err."],
        )
        self.assertEqual(
            format_failure(Diagnostic("FATAL", "X", "Fatal.")),
            ["FATAL X", "  Source: <unknown source>", "  Fatal."],
        )


# ---------------------------------------------------------------------------
# Contracts with the upstream tools
# ---------------------------------------------------------------------------

TOOLS = Path(__file__).resolve().parents[2]
MICRO_OPERATION_GOLDEN = (
    TOOLS
    / "micro-operation-extractor"
    / "tests"
    / "golden"
    / "valid"
    / "micro-operations.json"
)
CONTROL_OUTPUT_GOLDEN = (
    TOOLS
    / "control-output-extractor"
    / "tests"
    / "golden"
    / "valid"
    / "control-outputs.json"
)
SCHEMA_GENERATOR = (
    TOOLS / "control-word-schema-generator" / "src" / "generate_control_word_schema.py"
)


def load_schema_generator():
    specification = importlib.util.spec_from_file_location(
        "contract_control_word_schema_generator", SCHEMA_GENERATOR
    )
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module  # dataclasses look it up here
    specification.loader.exec_module(module)
    return module


class UpstreamContractTests(unittest.TestCase):
    """Keep this tool's inputs in step with what the upstream tools produce.

    The micro-operation catalog is the micro-operation extractor's golden
    output. The schema is built by the real control-word schema generator
    from the control-output extractor's golden output, with every field's
    role set to ``encoded`` as a review would. If these tests fail after an
    upstream change, update this tool (and its test builders) to match.
    """

    def setUp(self) -> None:
        self.micro_operations = json.loads(
            MICRO_OPERATION_GOLDEN.read_text(encoding="utf-8")
        )
        outputs = json.loads(CONTROL_OUTPUT_GOLDEN.read_text(encoding="utf-8"))
        self.schema, _ = load_schema_generator().build_candidate(outputs, None)
        for field in self.schema["fields"]:
            field["control_word_role"] = "encoded"

    def test_upstream_outputs_pass_validation(self) -> None:
        self.assertEqual(validate_micro_operations(self.micro_operations), [])
        self.assertEqual(validate_schema(self.schema)[0], [])

    def test_upstream_outputs_build_a_candidate(self) -> None:
        operations = {op["name"] for op in self.micro_operations["micro_operations"]}
        schema = copy.deepcopy(self.schema)
        for field in schema["fields"]:
            field["used_by_micro_operations"] = [
                item
                for item in field["used_by_micro_operations"]
                if item["micro_operation"] in operations
            ]

        candidate, diagnostics = build_candidate(self.micro_operations, schema)

        self.assertIsNotNone(candidate)
        self.assertEqual(set(codes(diagnostics)), {"MAPPING_UNRESOLVED"})

    def test_builders_match_upstream_shapes(self) -> None:
        real_operation = self.micro_operations["micro_operations"][0]
        real_field = self.schema["fields"][0]
        real_use = next(
            item
            for field in self.schema["fields"]
            for item in field["used_by_micro_operations"]
            if "value" in item
        )

        self.assertEqual(list(make_operation()), list(real_operation))
        self.assertEqual(
            list(make_operation()["source"]), list(real_operation["source"])
        )
        self.assertEqual(list(make_micro_operations()), list(self.micro_operations))
        self.assertEqual(list(make_field()), list(real_field))
        self.assertEqual(list(use()), list(real_use))


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
        micro_operations: dict | None,
        schema: dict,
        maintained: dict | None,
    ) -> None:
        for name, data in (
            ("micro.json", micro_operations),
            ("schema.json", schema),
            ("maintained.json", maintained),
        ):
            if data is not None:
                (self.root / name).write_text(
                    json.dumps(data, ensure_ascii=False), encoding="utf-8"
                )

    def run_main(self, *extra: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(
                [
                    "--repo-root",
                    str(self.root),
                    "--micro-operations",
                    "micro.json",
                    "--control-word-schema",
                    "schema.json",
                    "--maintained-mapping",
                    "maintained.json",
                    "--candidate-output",
                    "out/candidate.json",
                    "--report-output",
                    "out/report.txt",
                    *extra,
                ]
            )
        return exit_code, stdout.getvalue()

    def test_successful_run_writes_candidate_and_report(self) -> None:
        self.write_inputs(make_micro_operations(), make_schema(), make_maintained())

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        expected, _ = build_candidate(make_micro_operations(), make_schema(), None)
        self.assertEqual(
            self.candidate.read_text(encoding="utf-8"), serialize_json(expected)
        )
        self.assertIn("No diagnostics.", self.report.read_text(encoding="utf-8"))
        self.assertIn("Status: SUCCEEDED", stdout)
        self.assertIn("Micro-operations: 1", stdout)

    def test_failed_run_removes_previous_candidate(self) -> None:
        self.write_inputs(make_micro_operations(), make_schema(), None)
        self.assertEqual(self.run_main()[0], 0)
        self.write_inputs(
            make_micro_operations(), make_schema(make_field(role="derived")), None
        )

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        self.assertIn("Candidate written: no", self.report.read_text(encoding="utf-8"))
        self.assertIn(
            f"ERROR NON_ENCODED_ASSIGNMENT [PC_INC] [PC_INC]\n  Source: {UOPS}:10\n",
            stdout,
        )

    def test_unreadable_input_is_fatal(self) -> None:
        self.write_inputs(None, make_schema(), None)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        report = self.report.read_text(encoding="utf-8")
        self.assertIn("Fatal errors: 1", report)
        self.assertIn(
            "FATAL GENERATION_FAILURE [-]: Required input does not exist", report
        )
        self.assertIn("Micro-operations: 0", stdout)

    def test_invalid_catalog_counts_no_mappings(self) -> None:
        micro_operations = make_micro_operations()
        micro_operations["micro_operations"] = {"a": 1}
        self.write_inputs(micro_operations, make_schema(), None)

        exit_code, _ = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Mappings processed: 0", self.report.read_text(encoding="utf-8"))

    def test_report_sorts_diagnostics(self) -> None:
        schema = make_schema(
            make_field("Z", [use(value="7", line=5)]),
            make_field("Y", [use("NOPE", line=4)]),
        )
        schema["schema_version"] = 1
        self.write_inputs(make_micro_operations(), schema, None)

        self.run_main()

        details = self.report.read_text(encoding="utf-8").split("-----------\n", 1)[1]
        self.assertEqual(
            [line.split(":")[0] for line in details.splitlines()],
            [
                "ERROR INVALID_ASSIGNED_VALUE [PC_INC] [Z]",
                "ERROR UNDEFINED_USED_BY_MICRO_OPERATION [NOPE] [Y]",
            ],
        )

    def test_output_that_is_an_input_is_refused(self) -> None:
        self.write_inputs(make_micro_operations(), make_schema(), make_maintained())
        maintained = (self.root / "maintained.json").read_bytes()

        exit_code, stdout = self.run_main("--candidate-output", "maintained.json")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout)
        self.assertEqual((self.root / "maintained.json").read_bytes(), maintained)
        self.assertFalse(self.report.exists())

    def test_output_that_is_a_directory_is_refused(self) -> None:
        self.write_inputs(make_micro_operations(), make_schema(), None)
        self.report.parent.mkdir()
        self.report.write_text("earlier\n", encoding="utf-8")
        (self.root / "dir").mkdir()

        exit_code, stdout = self.run_main("--candidate-output", "dir")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout)
        self.assertTrue(self.report.exists())


if __name__ == "__main__":
    unittest.main()
