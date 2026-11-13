"""Tests for the symbolic control-word generator."""

from __future__ import annotations

import copy
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from generate_symbolic_control_words import (
    DEFAULT_ARTIFACT_DIRECTORY,
    DEFAULT_CANDIDATE,
    DEFAULT_MAINTAINED,
    DEFAULT_REPORT,
    ENCODED_FIELD_CHECKS,
    ENTRY_CHECKS,
    INPUT_SPECS,
    SPECS_BY_KEY,
    Diagnostic,
    ExpressionError,
    GenerationFailure,
    build_candidate,
    build_report,
    canonical,
    check_fields,
    diagnostic_sort_key,
    encode,
    evaluate,
    main,
    parse_arguments,
    parse_assignments,
    parse_expression,
    read_json,
    resolve_from_repo,
    substitute_selected,
)

# ---------------------------------------------------------------------------
# Builders
#
# The default world has inputs A, B, R, W and V, where R and W are
# mutually exclusive; encoded fields F (one bit, OFF/ON) and D (two bits,
# no listed values); a derived field G; micro-operations U (F = 1),
# X (F = 0) and Z (D = 01); and one case "c" with context A = 0 in TS1.
# ---------------------------------------------------------------------------


def make_input(
    name: str,
    *exclusive_with: str,
    values: tuple[str, ...] = ("0", "1"),
    width: int = 1,
    ranges: tuple[tuple[str, str], ...] = (),
) -> dict:
    return {
        "name": name,
        "width": width,
        "values": [{"value": value} for value in values],
        "ranges": [{"start": start, "end": end} for start, end in ranges],
        "constraints": [
            {"text": f"Mutually exclusive with {other}."}
            for other in exclusive_with
        ],
    }


def make_word(
    name: str,
    width: int = 1,
    values: list | None = None,
    default: str = "0",
    role: str = "encoded",
) -> dict:
    return {
        "name": name,
        "width": width,
        "control_word_role": role,
        "default_value": default,
        "values": [
            {"encoding": "0", "meaning": "OFF"},
            {"encoding": "1", "meaning": "ON"},
        ]
        if values is None
        else values,
    }


WORDS_WITH_STATE = [
    make_word("F"),
    make_word("D", width=2, values=[]),
    make_word(
        "MS_NEXT",
        values=[
            {"encoding": "0", "meaning": "FETCH"},
            {"encoding": "1", "meaning": "DEFER"},
        ],
    ),
]


def make_mapping(name: str, *assignments: tuple[str, str]) -> dict:
    return {
        "micro_operation": name,
        "assignments": [
            {"field": field, "value": value} for field, value in assignments
        ],
    }


def make_case(case_id: str = "c", **fields) -> dict:
    case = {
        "id": case_id,
        "source": {"path": "docs/exec.md", "line": 1},
        "execution_model": "major-state",
        "context": ["A = 0"],
        "timing_state": 1,
        "micro_operations": [],
        "conditional_micro_operations": [],
    }
    case.update(fields)
    return case


def conditional(predicate: str, name: str) -> dict:
    return {"predicate": predicate, "micro_operation": name}


DIRECT_LIST_KEYS = (
    "micro_operation_assignments",
    "state_commits",
    "value_relationships",
    "widths",
    "constraints",
    "sources",
    "drive_states",
    "external_ownership",
    "memory_behavior",
    "derived_values",
)


def make_direct(
    definition_id: str = "d",
    context: list | None = None,
    assignments: list | None = None,
    supplied: list | None = None,
) -> dict:
    definition = {
        "id": definition_id,
        "title": "title",
        "group": "group",
        "source": {"path": "docs/direct.md", "line": 1},
        "applicable_context": ["A = 0"] if context is None else context,
        "direct_assignments": assignments or [],
        "control_supplied_values": supplied or [],
    }
    definition.update({key: [] for key in DIRECT_LIST_KEYS})
    return definition


def make_timing(constraint_id: str, context: str, requirement: str) -> dict:
    return {
        "id": constraint_id,
        "context": context,
        "requirement": requirement,
        "source": {"path": "docs/timing.md", "line": 1},
    }


def make_documents(
    inputs: list | None = None,
    words: list | None = None,
    mappings: list | None = None,
    cases: list | None = None,
    direct: list | None = None,
    timing: list | None = None,
    global_constraints: list | None = None,
) -> dict:
    def schema(kind: str, key: str, items: list, **extra) -> dict:
        return {
            "specification_type": kind,
            "control_design_version": "v1",
            key: items,
            **extra,
        }

    def artifact(kind: str, key: str, items: list) -> dict:
        return {
            "format_version": 1,
            "control_design_version": "v1",
            "artifact": kind,
            "generation_stage": "candidate-generation",
            key: items,
            "diagnostics": [],
        }

    return {
        "inputs": schema(
            "control-input-schema",
            "fields",
            inputs
            if inputs is not None
            else [
                make_input("A", values=("0", "1", "2", "3"), width=2),
                make_input("B", values=("0", "1", "2", "3"), width=2),
                make_input("R", "W"),
                make_input("W", "R"),
                make_input("V"),
                make_input("RUN"),
            ],
            constraints=global_constraints or [],
        ),
        "words": schema(
            "control-word-schema",
            "fields",
            words
            if words is not None
            else [
                make_word("F"),
                make_word("D", width=2, values=[]),
                make_word("G", role="derived"),
            ],
        ),
        "mappings": schema(
            "micro-operation-mapping",
            "mappings",
            mappings
            if mappings is not None
            else [
                make_mapping("U", ("F", "1")),
                make_mapping("X", ("F", "0")),
                make_mapping("Z", ("D", "01")),
            ],
        ),
        "execution": artifact(
            "execution-definitions",
            "cases",
            cases if cases is not None else [make_case()],
        ),
        "direct": artifact(
            "direct-control-definitions", "definitions", direct or []
        ),
        "timing": artifact("timing-constraints", "constraints", timing or []),
    }


def generate(**parts) -> tuple[dict | None, list[Diagnostic]]:
    return build_candidate(make_documents(**parts), None)


def first_case(**parts) -> dict:
    candidate, diagnostics = generate(**parts)
    errors = [d for d in diagnostics if d.severity != "WARNING"]
    assert candidate is not None and not errors, errors
    return candidate["cases"][0]


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


def located(diagnostics) -> list[tuple]:
    """Return ``(code, entry, field)`` in report order."""

    ordered = sorted(diagnostics, key=diagnostic_sort_key)
    return [(d.code, d.entry_id, d.field_name) for d in ordered]


def errors(**parts) -> list[tuple]:
    candidate, diagnostics = generate(**parts)
    assert candidate is None
    return located(diagnostics)


# ---------------------------------------------------------------------------
# Arguments and reading
# ---------------------------------------------------------------------------


class ArgumentAndReadTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_defaults_and_paths(self) -> None:
        options = parse_arguments(["--repo-root", "."])
        root = Path("repository").resolve()
        absolute = Path("elsewhere/x.json").resolve()

        self.assertEqual(options.artifact_dir, DEFAULT_ARTIFACT_DIRECTORY)
        self.assertEqual(
            options.maintained,
            Path("rom/microcode/v1/symbolic-control-words.json"),
        )
        self.assertEqual(options.candidate_output, DEFAULT_CANDIDATE)
        self.assertEqual(options.report_output, DEFAULT_REPORT)
        self.assertEqual(
            resolve_from_repo(root, Path("a.json")), root / "a.json"
        )
        self.assertEqual(resolve_from_repo(root, absolute), absolute)

    def test_optional_input_may_be_missing_or_blank(self) -> None:
        blank = self.directory / "blank.json"
        blank.write_text("\n", encoding="utf-8")

        self.assertIsNone(read_json(self.directory / "none", optional=True))
        self.assertIsNone(read_json(blank, optional=True))

    def test_unreadable_inputs_fail(self) -> None:
        cases = {
            "missing.json": (None, "does not exist"),
            "utf8.json": (b"\xff", "not valid UTF-8"),
            "json.json": (b"{", "not valid JSON"),
            "list.json": (b"[]", "must be a JSON object"),
        }
        for name, (content, message) in cases.items():
            with self.subTest(name=name):
                path = self.directory / name
                if content is not None:
                    path.write_bytes(content)
                with self.assertRaisesRegex(GenerationFailure, message):
                    read_json(path)

        with self.assertRaisesRegex(GenerationFailure, "Unable to read"):
            read_json(self.directory)


# ---------------------------------------------------------------------------
# Expressions
# ---------------------------------------------------------------------------


class ExpressionTests(unittest.TestCase):
    def test_canonical_form_and_precedence(self) -> None:
        cases = {
            "A = 1 AND (B != 2 OR NOT (U is selected))": (
                "(A = 1 AND (B != 2 OR NOT (U is selected)))"
            ),
            "A = 1 OR B = 1 AND C = 1": "(A = 1 OR (B = 1 AND C = 1))",
            "NOT A = 1 AND B = 1": "(NOT (A = 1) AND B = 1)",
            "a = 1 and U is not selected": "(a = 1 AND U is not selected)",
            "A = 1\nB = 0\n(C = 1 OR D = 1)": (
                "((A = 1 AND B = 0) AND (C = 1 OR D = 1))"
            ),
            "U is selected NOT B = 1": "(U is selected AND NOT (B = 1))",
            " A = 1 \n": "A = 1",
            "(A = 1) B = 0": "(A = 1 AND B = 0)",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(canonical(parse_expression(text)), expected)

        self.assertEqual(canonical(None), "always")
        self.assertEqual(canonical(("const", True)), "true")
        self.assertEqual(canonical(("const", False)), "false")

    def test_malformed_expressions(self) -> None:
        cases = {
            "": "Empty expression",
            "A = 1 B": "Missing operator after B",
            "A =": "Missing value after A =",
            "(A = 1": "Missing closing parenthesis",
            "A = 1)": "Unexpected token ')'",
            "AND A = 1": "Expected a field or micro-operation name",
            "A = 1 OR": "Expected a field or micro-operation name",
            "A = =": "Missing value after A =",
        }
        for text, message in cases.items():
            with (
                self.subTest(text=text),
                self.assertRaisesRegex(ExpressionError, re.escape(message)),
            ):
                parse_expression(text)

    def test_assignment_blocks(self) -> None:
        self.assertEqual(
            parse_assignments(["F = 1\n\n  D = 01  ", "G=ON"]),
            [("F", "1"), ("D", "01"), ("G", "ON")],
        )
        with self.assertRaisesRegex(ExpressionError, "Malformed assignment"):
            parse_assignments(["F = 1 2"])

    def test_selection_substitution(self) -> None:
        guard = parse_expression("A = 0")
        cases = {
            "U is selected": "A = 0",
            "U is not selected": "NOT (A = 0)",
            "X is selected": "false",
            "X is not selected": "true",
            "NOT (U is selected) OR B = 1": "(NOT (A = 0) OR B = 1)",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                expression = substitute_selected(
                    parse_expression(text), {"U": guard}
                )
                self.assertEqual(canonical(expression), expected)

        always = substitute_selected(
            parse_expression("U is selected"), {"U": None}
        )
        self.assertEqual(always, ("const", True))

    def test_three_valued_evaluation(self) -> None:
        cases = [
            ("A = 1", {}, None),
            ("A = 1", {"A": "1"}, True),
            ("A != 1", {"A": None}, True),
            ("NOT A = 1", {}, None),
            ("A = 1 AND B = 1", {"A": "0"}, False),
            ("A = 1 AND B = 1", {"A": "1"}, None),
            ("A = 1 AND B = 1", {"A": "1", "B": "1"}, True),
            ("A = 1 OR B = 1", {"A": "1"}, True),
            ("A = 1 OR B = 1", {"A": "0"}, None),
            ("A = 1 OR B = 1", {"A": "0", "B": "0"}, False),
        ]
        for text, values, expected in cases:
            with self.subTest(text=text, values=values):
                self.assertIs(
                    evaluate(parse_expression(text), values), expected
                )


class EncodingTests(unittest.TestCase):
    def test_encodings(self) -> None:
        listed = make_word("F", values=[{"encoding": "1", "meaning": "ON"}])
        free = make_word("D", width=3, values=[])
        cases = [
            (listed, "1", "1"),
            (listed, "ON", "1"),
            (free, "01", "001"),
            (free, "5", "101"),
            (free, "111", "111"),
        ]
        for field, value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(encode(field, value), expected)

        for field, value in (
            (listed, "OFF"),
            (listed, "0"),
            (free, "8"),
            (free, "1x"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "Unknown value"),
            ):
                encode(field, value)


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


class StructureTests(unittest.TestCase):
    def test_valid_inputs(self) -> None:
        candidate, diagnostics = generate()

        self.assertIsNotNone(candidate)
        self.assertEqual(codes(diagnostics), ["NEW_CASE"])

    def test_identity_and_version(self) -> None:
        for spec in INPUT_SPECS:
            with self.subTest(file=spec.file_name):
                documents = make_documents()
                documents[spec.key][spec.identity_key] = "other"
                documents[spec.key]["control_design_version"] = "v2"
                _, diagnostics = build_candidate(documents, None)
                # The word schema sets the version the others must match.
                if spec.key == "words":
                    mismatched = [
                        other.file_name
                        for other in INPUT_SPECS
                        if other is not spec
                    ]
                else:
                    mismatched = [spec.file_name]
                expected = [
                    ("CONTROL_DESIGN_VERSION_MISMATCH", None, name)
                    for name in sorted(mismatched)
                ]
                expected.append(
                    ("UNEXPECTED_ARTIFACT_TYPE", None, spec.file_name)
                )
                self.assertEqual(located(diagnostics), expected)

    def test_word_schema_version_is_required(self) -> None:
        documents = make_documents()
        for data in documents.values():
            del data["control_design_version"]

        candidate, diagnostics = build_candidate(documents, None)

        self.assertIsNone(candidate)
        self.assertEqual(
            located(diagnostics),
            [
                (
                    "INVALID_CONTROL_WORD_SCHEMA",
                    None,
                    "control_design_version",
                )
            ],
        )

    def test_entries_must_be_identified_objects(self) -> None:
        for spec in INPUT_SPECS:
            with self.subTest(file=spec.file_name):
                documents = make_documents(
                    direct=[make_direct()],
                    timing=[make_timing("t", "A = 0", "B = 0")],
                )
                entries = documents[spec.key][spec.list_key]
                entry = entries[0]
                entries[:] = [
                    entry,
                    "text",
                    {**entry, spec.id_key: ""},
                    copy.deepcopy(entry),
                ]
                _, diagnostics = build_candidate(documents, None)
                self.assertEqual(
                    located(diagnostics),
                    [(spec.code, None, None)] * 2
                    + [(spec.code, entry[spec.id_key], None)],
                )

                documents[spec.key][spec.list_key] = {}
                _, diagnostics = build_candidate(documents, None)
                self.assertEqual(
                    located(diagnostics), [(spec.code, None, None)]
                )

    def test_malformed_entry_fields(self) -> None:
        bad = {
            "constraints": [None, ["text"]],
            "width": [None, 0],
            "values": [None, [{"value": 1}]],
            "ranges": [None, [{"start": "0"}], [{"start": "0", "end": "2"}]],
            "control_word_role": [None, ""],
            "assignments": [
                None,
                [{"field": "F"}],
                [{"field": 1, "value": "1"}],
            ],
            "source": [None, {"path": "x"}, {"path": "x", "line": True}],
            ("execution", "context"): [None, [1]],
            ("timing", "context"): [None, "", 3],
            "timing_state": [0, 5, True, "1"],
            "micro_operations": [None, [1]],
            "conditional_micro_operations": [
                None,
                [{"predicate": "A = 1"}],
                [{"predicate": 1, "micro_operation": "U"}],
            ],
            "applicable_context": [None, [1]],
            "direct_assignments": [None, [1]],
            "control_supplied_values": [None],
            "requirement": [None, " "],
        }
        samples = {
            "inputs": make_input("A"),
            "words": make_word("F", role="derived"),
            "mappings": make_mapping("U"),
            "execution": make_case(),
            "direct": make_direct(),
            "timing": make_timing("t", "A = 0", "B = 0"),
        }
        checked = set()
        for key, checks in ENTRY_CHECKS.items():
            spec = SPECS_BY_KEY[key]
            for field, _, _ in checks:
                for value in bad.get((key, field)) or bad[field]:
                    with self.subTest(key=key, field=field, value=value):
                        entry = {**samples[key], field: value}
                        diagnostics = check_fields(
                            entry, "e", checks, spec.code
                        )
                        self.assertEqual(
                            located(diagnostics), [(spec.code, "e", field)]
                        )
                        checked.add((key, field))
        self.assertEqual(
            checked,
            {
                (key, f)
                for key, checks in ENTRY_CHECKS.items()
                for f, *_ in checks
            },
        )

    def test_entry_field_errors_reach_the_report(self) -> None:
        self.assertEqual(
            errors(cases=[make_case(timing_state=7)]),
            [("INVALID_EXECUTION_DEFINITIONS", "c", "timing_state")],
        )
        self.assertEqual(
            errors(inputs=[{**make_input("A"), "width": None}]),
            [("INVALID_CONTROL_INPUT_SCHEMA", "A", "width")],
        )

    def test_encoded_fields_are_checked(self) -> None:
        bad = {
            "width": [None, 0, True],
            "default_value": [None, ""],
            "values": [
                None,
                [{"encoding": "0"}],
                [{"encoding": 0, "meaning": "x"}],
            ],
        }
        for field, _, _ in ENCODED_FIELD_CHECKS:
            for value in bad[field]:
                with self.subTest(field=field, value=value):
                    word = {**make_word("F"), field: value}
                    self.assertEqual(
                        errors(words=[word]),
                        [("INVALID_CONTROL_WORD_SCHEMA", "F", field)],
                    )

        derived = {**make_word("G", role="derived"), "width": None}
        candidate, _ = generate(
            words=[make_word("F"), make_word("D", 2, []), derived]
        )
        self.assertIsNotNone(candidate)

    def test_global_constraints(self) -> None:
        code = "INVALID_CONTROL_INPUT_SCHEMA"
        documents = make_documents()
        documents["inputs"]["constraints"] = None
        _, diagnostics = build_candidate(documents, None)
        self.assertEqual(located(diagnostics), [(code, None, "constraints")])

        self.assertEqual(
            errors(
                global_constraints=[
                    {"kind": "exactly_one", "inputs": "A"},
                    {"kind": "at_most_one"},
                    {"kind": "other"},
                ]
            ),
            [(code, None, "constraints")] * 2,
        )


class MaintainedValidationTests(unittest.TestCase):
    def test_version_mismatch_blocks(self) -> None:
        maintained = {"control_design_version": "v2", "cases": []}

        candidate, diagnostics = build_candidate(make_documents(), maintained)

        self.assertIsNone(candidate)
        self.assertEqual(
            codes(diagnostics), ["CONTROL_DESIGN_VERSION_MISMATCH"]
        )

    def test_malformed_cases_block(self) -> None:
        case = {"execution_case_id": "c"}
        for cases, expected in (
            ({}, [("INVALID_MAINTAINED_CASES", None, None)]),
            (
                ["text", {"execution_case_id": ""}, case, case],
                [("INVALID_MAINTAINED_CASES", None, None)] * 2
                + [("INVALID_MAINTAINED_CASES", "c", None)],
            ),
        ):
            with self.subTest(cases=cases):
                maintained = {"control_design_version": "v1", "cases": cases}
                candidate, diagnostics = build_candidate(
                    make_documents(), maintained
                )
                self.assertIsNone(candidate)
                self.assertEqual(located(diagnostics), expected)


# ---------------------------------------------------------------------------
# Reference validation
# ---------------------------------------------------------------------------


class ReferenceTests(unittest.TestCase):
    def test_known_names(self) -> None:
        case = make_case(
            context=["A = 0", "F = 1", "MS = FETCH"],
            conditional_micro_operations=[conditional("TS = 1", "U")],
        )
        self.assertEqual(
            first_case(cases=[case], words=WORDS_WITH_STATE)[
                "execution_case_id"
            ],
            "c",
        )

    def test_compared_values(self) -> None:
        inputs = [
            make_input("A", values=("0", "1", "2", "3"), width=2),
            make_input("B"),
            make_input("N", width=3, values=(), ranges=(("001", "110"),)),
            make_input("P", width=2, values=()),
            make_input("RUN"),
        ]
        valid = (
            "A = 3 AND B != 0 AND N = 110 AND P = 11 AND F = 1 AND D = 10 "
            "AND TS = 4 AND MS != DEFER"
        )
        case = first_case(
            inputs=inputs,
            words=WORDS_WITH_STATE,
            cases=[make_case(context=[valid])],
        )
        self.assertEqual(case["execution_case_id"], "c")

        cases = {
            "A = 4": "4 is not a value of A, which takes one of 0, 1, 2, 3.",
            "N = 000": (
                "000 is not a value of N, which takes a 3-bit binary value "
                "from 001 to 110."
            ),
            "N = 11": (
                "11 is not a value of N, which takes a 3-bit binary value "
                "from 001 to 110."
            ),
            "P = 2x": "2x is not a value of P, which takes a 2-bit binary value.",
            "F = ON": "ON is not a value of F, which takes one of 0, 1.",
            "D = 1": "1 is not a value of D, which takes a 2-bit binary value.",
            "TS = 0": "0 is not a value of TS, which takes one of 1, 2, 3, 4.",
            "MS = HALT": (
                "HALT is not a value of MS, which takes one of FETCH, DEFER."
            ),
            "B = 2 OR NOT B = 2": (
                "2 is not a value of B, which takes one of 0, 1."
            ),
        }
        for text, message in cases.items():
            with self.subTest(text=text):
                _, diagnostics = generate(
                    inputs=inputs,
                    words=WORDS_WITH_STATE,
                    cases=[make_case(context=[text])],
                )
                self.assertEqual(
                    [(d.code, d.message) for d in diagnostics],
                    [("INVALID_COMPARED_VALUE", message)],
                )

    def test_major_state_needs_its_field(self) -> None:
        _, diagnostics = generate(cases=[make_case(context=["MS = FETCH"])])

        self.assertEqual(
            [d.message for d in diagnostics],
            [
                (
                    "FETCH is not a value of MS, which takes no documented "
                    "values; they come from MS_NEXT, which is not an encoded "
                    "control-word field."
                )
            ],
        )

    def test_unknown_names_everywhere(self) -> None:
        case = make_case(
            context=["BAD = 0", "G = 1"],
            conditional_micro_operations=[conditional("NOPE = 1", "U")],
        )
        self.assertEqual(
            errors(
                cases=[case],
                direct=[make_direct(context=["A = 0", "MISSING = 1"])],
                timing=[make_timing("t", "TS = 1 AND (Q = 1)", "P != 1")],
            ),
            [
                ("UNKNOWN_NAME", "c", "conditional_micro_operations"),
                ("UNKNOWN_NAME", "c", "context"),
                ("UNKNOWN_NAME", "c", "context"),
                ("UNKNOWN_NAME", "d", "applicable_context"),
                ("UNKNOWN_NAME", "t", "context"),
                ("UNKNOWN_NAME", "t", "requirement"),
            ],
        )

    def test_invalid_expressions(self) -> None:
        case = make_case(
            context=["A ="],
            conditional_micro_operations=[conditional("U is selected", "X")],
        )
        _, diagnostics = generate(
            cases=[case],
            direct=[make_direct(context=["(A = 0"])],
            timing=[make_timing("t", "U is selected", "A = 0")],
        )
        diagnostics.sort(key=diagnostic_sort_key)
        self.assertEqual(
            located(diagnostics),
            [
                ("INVALID_EXPRESSION", "c", "conditional_micro_operations"),
                ("INVALID_EXPRESSION", "c", "context"),
                ("INVALID_EXPRESSION", "d", "applicable_context"),
                ("INVALID_EXPRESSION", "t", "context"),
            ],
        )
        self.assertEqual(
            diagnostics[0].message,
            "'U is selected' is allowed only in direct-control contexts.",
        )
        self.assertEqual(
            diagnostics[1].message, "Missing value after A =. In 'A ='."
        )

    def test_unknown_micro_operations(self) -> None:
        case = make_case(
            micro_operations=["U", "NOPE"],
            conditional_micro_operations=[conditional("B = 1", "GONE")],
        )
        self.assertEqual(
            errors(
                cases=[case],
                direct=[make_direct(context=["ABSENT is selected"])],
            ),
            [
                (
                    "UNKNOWN_MICRO_OPERATION",
                    "c",
                    "conditional_micro_operations",
                ),
                ("UNKNOWN_MICRO_OPERATION", "c", "micro_operations"),
                ("UNKNOWN_MICRO_OPERATION", "d", "applicable_context"),
            ],
        )

    def test_direct_context_is_required(self) -> None:
        self.assertEqual(
            errors(direct=[make_direct(context=[])]),
            [("MISSING_APPLICABLE_CONTEXT", "d", "applicable_context")],
        )

    def test_duplicate_micro_operations(self) -> None:
        case = make_case(
            micro_operations=["U", "U"],
            conditional_micro_operations=[conditional("B = 1", "U")],
        )
        self.assertEqual(
            errors(cases=[case]),
            [
                (
                    "DUPLICATE_MICRO_OPERATION",
                    "c",
                    "conditional_micro_operations",
                ),
                ("DUPLICATE_MICRO_OPERATION", "c", "micro_operations"),
            ],
        )

    def test_assignment_references(self) -> None:
        self.assertEqual(
            errors(
                words=[
                    make_word("F", default="MAYBE"),
                    make_word("D", width=2, values=[]),
                ],
                mappings=[make_mapping("U", ("NOPE", "1"), ("F", "7"))],
                direct=[
                    make_direct(
                        assignments=["G = 1\nF = HALF"],
                        supplied=["D = 9", "H = V"],
                    ),
                    make_direct("e", assignments=["F = 1 = 2"]),
                    # Only control-supplied values may name an input.
                    make_direct("f", assignments=["D = V"]),
                ],
            ),
            [
                ("INVALID_FIELD_VALUE", "F", "default_value"),
                ("INVALID_FIELD_VALUE", "U", "F"),
                ("INVALID_FIELD_VALUE", "d", "D"),
                ("INVALID_FIELD_VALUE", "d", "F"),
                ("INVALID_FIELD_VALUE", "f", "D"),
                ("MALFORMED_ASSIGNMENT", "e", "direct_assignments"),
                ("UNKNOWN_CONTROL_FIELD", "U", "NOPE"),
                ("UNKNOWN_CONTROL_FIELD", "d", "G"),
                ("UNKNOWN_CONTROL_FIELD", "d", "H"),
            ],
        )


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


class GenerationTests(unittest.TestCase):
    def test_defaults_cover_encoded_fields(self) -> None:
        case = first_case()

        self.assertEqual(case["defaults"], {"F": "0", "D": "00"})
        self.assertEqual(case["field_assignments"], {"F": [], "D": []})
        self.assertEqual(case["base_context"], "((A = 0 AND TS = 1) AND RUN = 1)")

    def test_console_case_has_no_timing_state(self) -> None:
        case = first_case(cases=[make_case(timing_state=None, context=[])])

        self.assertEqual(case["base_context"], "RUN = 1")

    def test_micro_operations(self) -> None:
        case = first_case(
            cases=[
                make_case(
                    micro_operations=["Z"],
                    conditional_micro_operations=[conditional("B = 1", "U")],
                )
            ]
        )

        self.assertEqual(
            case["field_assignments"],
            {
                "F": [
                    {
                        "value": "1",
                        "when": "(((A = 0 AND TS = 1) AND RUN = 1) AND B = 1)",
                        "origin": "conditional micro-operation mapping",
                        "source": "U",
                    }
                ],
                "D": [
                    {
                        "value": "01",
                        "when": "((A = 0 AND TS = 1) AND RUN = 1)",
                        "origin": "micro-operation mapping",
                        "source": "Z",
                    }
                ],
            },
        )
        self.assertEqual(
            case["selected_micro_operations"],
            {
                "U": "(((A = 0 AND TS = 1) AND RUN = 1) AND B = 1)",
                "Z": "((A = 0 AND TS = 1) AND RUN = 1)",
            },
        )
        self.assertEqual(list(case["selected_micro_operations"]), ["U", "Z"])

    def test_direct_definitions(self) -> None:
        case = first_case(
            direct=[
                make_direct(
                    context=["A = 1", "A = 0\nB = 1"],
                    assignments=["F = ON"],
                ),
                make_direct("never", context=["A = 1"], assignments=["F = 0"]),
            ]
        )

        when = (
            "(((A = 0 AND TS = 1) AND RUN = 1) AND ((A = 1 AND RUN = 1) OR "
            "((A = 0 AND B = 1) AND RUN = 1)))"
        )
        self.assertEqual(case["applicable_direct_control_definitions"], ["d"])
        self.assertEqual(
            case["field_assignments"]["F"],
            [
                {
                    "value": "1",
                    "when": when,
                    "origin": "direct-control definition",
                    "source": "d",
                }
            ],
        )
        self.assertEqual(case["field_assignments"]["D"], [])

    def test_control_supplied_values(self) -> None:
        case = first_case(
            direct=[make_direct("v", supplied=["D = V"])],
        )
        self.assertEqual(
            case["field_assignments"]["D"],
            [
                {
                    "value_from_input": "V",
                    "when": "(((A = 0 AND TS = 1) AND RUN = 1) AND (A = 0 AND RUN = 1))",
                    "origin": "control-supplied value",
                    "source": "v",
                }
            ],
        )

        case = first_case(direct=[make_direct("n", supplied=["D = 2"])])
        self.assertEqual(case["field_assignments"]["D"][0]["value"], "10")

    def test_selected_micro_operations_in_direct_contexts(self) -> None:
        case = first_case(
            cases=[
                make_case(
                    conditional_micro_operations=[conditional("B = 1", "Z")]
                )
            ],
            direct=[
                make_direct("on", ["Z is selected"], ["F = 1"]),
                make_direct("off", ["U is selected"], ["F = 0"]),
                make_direct("not", ["U is not selected"], ["F = 1"]),
            ],
        )

        self.assertEqual(
            case["applicable_direct_control_definitions"], ["on", "not"]
        )
        self.assertEqual(
            [item["when"] for item in case["field_assignments"]["F"]],
            [
                "(((A = 0 AND TS = 1) AND RUN = 1) AND (((A = 0 AND TS = 1) AND RUN = 1) AND B = 1))",
                "(((A = 0 AND TS = 1) AND RUN = 1) AND true)",
            ],
        )

    def test_assignment_order(self) -> None:
        case = first_case(
            mappings=[
                make_mapping("U", ("F", "1"), ("D", "1")),
                make_mapping("Z", ("D", "1")),
            ],
            cases=[
                make_case(
                    micro_operations=["Z"],
                    conditional_micro_operations=[conditional("B = 1", "U")],
                )
            ],
            direct=[make_direct(assignments=["D = 1"])],
        )

        self.assertEqual(
            [item["source"] for item in case["field_assignments"]["D"]],
            ["Z", "U", "d"],
        )

    def test_search_retracts_abandoned_values(self) -> None:
        # Every B value fails under A = 1. A stale B left behind would
        # then wrongly rule out A = 3, which needs B = 1.
        case = first_case(
            cases=[
                make_case(
                    context=[
                        "(A = 1 AND B = 2 AND B = 1) OR (A = 3 AND B = 1)"
                    ],
                    timing_state=None,
                )
            ],
            direct=[make_direct(context=["V = 1"], assignments=["F = 1"])],
        )

        self.assertEqual(case["applicable_direct_control_definitions"], ["d"])

    def test_cases_keep_execution_order(self) -> None:
        candidate, _ = generate(
            cases=[make_case("z"), make_case("a", context=["B = 1"])]
        )

        self.assertEqual(
            [case["execution_case_id"] for case in candidate["cases"]],
            ["z", "a"],
        )


class ConflictTests(unittest.TestCase):
    def conflicts(self, **parts) -> list[tuple]:
        candidate, diagnostics = generate(**parts)
        found = [d for d in diagnostics if d.code == "CONFLICTING_ASSIGNMENTS"]
        self.assertEqual(candidate is None, bool(found))
        return located(found)

    def test_overlapping_micro_operations_conflict(self) -> None:
        candidate, diagnostics = generate(
            cases=[make_case(micro_operations=["U", "X"])]
        )

        self.assertIsNone(candidate)
        self.assertEqual(
            located(diagnostics), [("CONFLICTING_ASSIGNMENTS", "c", "F")]
        )
        self.assertEqual(
            diagnostics[0].message,
            "1 from micro-operation mapping U when ((A = 0 AND TS = 1) AND RUN = 1) "
            "conflicts with 0 from micro-operation mapping X when "
            "((A = 0 AND TS = 1) AND RUN = 1).",
        )

    def test_unconditional_guards_conflict(self) -> None:
        case = make_case(
            context=[], timing_state=None, micro_operations=["U", "X"]
        )
        candidate, diagnostics = generate(cases=[case])

        self.assertIsNone(candidate)
        self.assertEqual(
            diagnostics[0].message,
            "1 from micro-operation mapping U when RUN = 1 conflicts with "
            "0 from micro-operation mapping X when RUN = 1.",
        )

    def test_same_value_does_not_conflict(self) -> None:
        self.assertEqual(
            self.conflicts(
                cases=[make_case(micro_operations=["U"])],
                direct=[make_direct(assignments=["F = ON"])],
            ),
            [],
        )

    def test_disjoint_guards_do_not_conflict(self) -> None:
        case = make_case(
            conditional_micro_operations=[conditional("B = 0", "U")]
        )
        self.assertEqual(
            self.conflicts(
                cases=[case],
                direct=[make_direct(context=["B = 1"], assignments=["F = 0"])],
            ),
            [],
        )

    def test_exclusive_inputs_do_not_conflict(self) -> None:
        direct = [
            make_direct("read", ["R = 1"], ["F = 0"]),
            make_direct("write", ["W = 1"], ["F = 1"]),
        ]
        self.assertEqual(self.conflicts(direct=direct), [])
        self.assertEqual(
            self.conflicts(
                inputs=[make_input(name) for name in ("A", "B", "R", "W", "V", "RUN")],
                direct=direct,
            ),
            [("CONFLICTING_ASSIGNMENTS", "c", "F")],
        )

    def test_global_exclusion_constraints(self) -> None:
        for kind in ("exactly_one", "at_most_one"):
            with self.subTest(kind=kind):
                case = first_case(
                    global_constraints=[
                        {"kind": kind, "inputs": ["A", "B", "V"]}
                    ],
                    cases=[make_case(context=["A = 1"])],
                    direct=[make_direct("d", ["V = 1"], ["F = 1"])],
                )
                self.assertEqual(
                    case["applicable_direct_control_definitions"], []
                )

        case = first_case(
            global_constraints=[{"kind": "other", "inputs": ["A", "V"]}],
            cases=[make_case(context=["A = 1"])],
            direct=[make_direct("d", ["V = 1"], ["F = 1"])],
        )
        self.assertEqual(case["applicable_direct_control_definitions"], ["d"])

    def test_ir_derivations_exclude_states(self) -> None:
        def decode(name: str, text: str) -> dict:
            field = make_input(name)
            field["domain"] = "IR-Derived Signals"
            field["derivation"] = {"text": f"{name} = {text}"}
            return field

        inputs = [
            decode("WRITES", "IR[11:6] == 110010 AND IR[2] == 0"),
            decode("RESTORES", "IR[11:6] == 110010 AND IR[2:0] == 100"),
            decode("BOTH", "WRITES AND IR[0]"),
            make_input("A"),
            make_input("RUN"),
        ]

        def run(first: str, second: str) -> list[tuple]:
            return self.conflicts(
                inputs=inputs,
                cases=[
                    make_case(
                        conditional_micro_operations=[
                            conditional(first, "U"),
                            conditional(second, "X"),
                        ]
                    )
                ],
            )

        conflict = [("CONFLICTING_ASSIGNMENTS", "c", "F")]
        self.assertEqual(run("WRITES = 1", "RESTORES = 1"), [])
        self.assertEqual(run("BOTH = 1", "WRITES = 0"), [])
        self.assertEqual(run("BOTH = 1", "WRITES = 1"), conflict)
        self.assertEqual(run("RESTORES = 0", "WRITES = 0"), conflict)

    def test_unusable_ir_derivation_is_an_error(self) -> None:
        field = make_input("BAD")
        field["domain"] = "IR-Derived Signals"
        field["derivation"] = {"text": "BAD = IR[0] (octal 1)"}
        self.assertEqual(
            errors(inputs=[field, make_input("A"), make_input("RUN")]),
            [("IR_DERIVATION_UNUSABLE", "BAD", "derivation")],
        )

    def test_timing_constraints(self) -> None:
        def run(timing_context: str) -> list[tuple]:
            return self.conflicts(
                cases=[
                    make_case(
                        timing_state=4,
                        conditional_micro_operations=[
                            conditional("R = 1", "U")
                        ],
                    )
                ],
                direct=[make_direct(context=["B = 1"], assignments=["F = 0"])],
                timing=[make_timing("t", timing_context, "B != 1")],
            )

        conflict = [("CONFLICTING_ASSIGNMENTS", "c", "F")]
        self.assertEqual(run("TS = 4 AND (R = 1)"), [])
        self.assertEqual(run("TS = 3 AND (R = 1)"), conflict)
        self.assertEqual(run("TS = 4 AND (V = 1)"), conflict)
        self.assertEqual(run("TS = 4 AND (R = 1 OR V = 1)"), [])

    def test_input_supplied_values_conflict(self) -> None:
        self.assertEqual(
            self.conflicts(
                direct=[
                    make_direct("a", supplied=["D = V"]),
                    make_direct("b", supplied=["D = A"]),
                    make_direct("c", supplied=["D = 1"]),
                ]
            ),
            [("CONFLICTING_ASSIGNMENTS", "c", "D")],
        )
        self.assertEqual(
            self.conflicts(
                direct=[
                    make_direct("a", supplied=["D = V"]),
                    make_direct("b", supplied=["D = V"]),
                ]
            ),
            [],
        )

    def test_one_conflict_per_field(self) -> None:
        self.assertEqual(
            self.conflicts(
                cases=[make_case(micro_operations=["U", "X", "Z"])],
                direct=[make_direct(assignments=["F = 1\nD = 10"])],
            ),
            [
                ("CONFLICTING_ASSIGNMENTS", "c", "D"),
                ("CONFLICTING_ASSIGNMENTS", "c", "F"),
            ],
        )


# ---------------------------------------------------------------------------
# Review and candidate
# ---------------------------------------------------------------------------


class RunModeDefaultTests(unittest.TestCase):
    """Execution Model §2.3: contexts that do not compare RUN apply only
    while running."""

    HALTED = make_case("h", context=["RUN = 0", "A = 1"], timing_state=None)

    def test_case_context_that_compares_run_is_unchanged(self) -> None:
        case = first_case(cases=[self.HALTED])
        self.assertEqual(case["base_context"], "(RUN = 0 AND A = 1)")

        case = first_case(cases=[make_case(context=["NOT (RUN = 0 AND A = 1)"])])
        self.assertEqual(
            case["base_context"], "(NOT ((RUN = 0 AND A = 1)) AND TS = 1)"
        )

    def test_direct_context_without_run_applies_only_while_running(self) -> None:
        direct = [
            make_direct("running", ["A = 1"], ["F = 1"]),
            make_direct("halted", ["RUN = 0\nA = 1"], ["F = 0"]),
            make_direct("either", ["NOT (RUN = 1 AND B = 1)"], ["D = 10"]),
        ]
        case = first_case(cases=[self.HALTED], direct=direct)
        self.assertEqual(
            case["applicable_direct_control_definitions"], ["halted", "either"]
        )

        case = first_case(cases=[make_case(context=["A = 1"])], direct=direct)
        self.assertEqual(
            case["applicable_direct_control_definitions"], ["running", "either"]
        )

    def test_each_direct_context_alternative_gets_the_default(self) -> None:
        direct = [make_direct("d", ["RUN = 0\nB = 1", "A = 1"], ["F = 1"])]
        case = first_case(cases=[self.HALTED], direct=direct)
        self.assertEqual(
            case["field_assignments"]["F"][0]["when"],
            "((RUN = 0 AND A = 1) AND ((RUN = 0 AND B = 1) OR "
            "(A = 1 AND RUN = 1)))",
        )

    def test_selection_context_takes_run_mode_from_the_case(self) -> None:
        halted = make_case(
            "h", context=["RUN = 0"], timing_state=None, micro_operations=["Z"]
        )
        case = first_case(
            cases=[halted], direct=[make_direct("m", ["Z is selected"], ["F = 1"])]
        )
        self.assertEqual(case["applicable_direct_control_definitions"], ["m"])
        self.assertEqual(
            case["field_assignments"]["F"][0]["when"], "(RUN = 0 AND RUN = 0)"
        )

    def test_conditional_predicates(self) -> None:
        # Within a running case the base already holds RUN = 1.
        case = first_case(
            cases=[make_case(conditional_micro_operations=[conditional("B = 1", "U")])]
        )
        self.assertEqual(
            case["selected_micro_operations"]["U"],
            "(((A = 0 AND TS = 1) AND RUN = 1) AND B = 1)",
        )
        # Within a halted case the predicate gets the default itself.
        halted = make_case(
            "h",
            context=["RUN = 0"],
            timing_state=None,
            conditional_micro_operations=[
                conditional("B = 1", "U"),
                conditional("RUN = 0 AND B = 2", "Z"),
            ],
        )
        case = first_case(cases=[halted])
        self.assertEqual(
            case["selected_micro_operations"],
            {"U": "(RUN = 0 AND (B = 1 AND RUN = 1))",
             "Z": "(RUN = 0 AND (RUN = 0 AND B = 2))"},
        )

    def test_run_must_be_a_control_input(self) -> None:
        self.assertIn(
            ("RUN_INPUT_MISSING", "control-input-schema.json", "RUN"),
            errors(inputs=[make_input("A", values=("0", "1", "2", "3"), width=2)]),
        )


class ReviewTests(unittest.TestCase):
    def test_candidate_structure(self) -> None:
        candidate, _ = generate()

        self.assertEqual(
            list(candidate),
            [
                "format_version",
                "control_design_version",
                "artifact",
                "generation_stage",
                "representation",
                "sources",
                "cases",
                "diagnostics",
            ],
        )
        self.assertEqual(candidate["artifact"], "symbolic-control-words")
        self.assertEqual(candidate["representation"], "predicate-preserving")
        self.assertEqual(
            candidate["sources"],
            [
                "control-input-schema.json",
                "control-word-schema.json",
                "micro-operation-mapping.json",
                "execution-definitions.json",
                "direct-control-definitions.json",
                "timing-constraints.json",
            ],
        )
        self.assertEqual(
            list(candidate["cases"][0]),
            [
                "execution_case_id",
                "source",
                "base_context",
                "defaults",
                "field_assignments",
                "selected_micro_operations",
                "applicable_direct_control_definitions",
            ],
        )

    def test_promoted_candidate_reviews_clean(self) -> None:
        documents = make_documents()
        candidate, _ = build_candidate(documents, None)

        again, diagnostics = build_candidate(documents, candidate)

        self.assertEqual(diagnostics, [])
        self.assertEqual(again, candidate)

    def test_new_changed_and_stale(self) -> None:
        documents = make_documents(
            cases=[make_case("new"), make_case("changed"), make_case("same")]
        )
        maintained, _ = build_candidate(documents, None)
        maintained["cases"][0]["execution_case_id"] = "stale"
        maintained["cases"][1]["base_context"] = "always"
        maintained["cases"][1]["extra"] = 1

        _, diagnostics = build_candidate(documents, maintained)

        self.assertEqual(
            diagnostics,
            [
                Diagnostic(
                    "WARNING",
                    "NEW_CASE",
                    "Case is not present in the maintained artifact.",
                    "new",
                ),
                Diagnostic(
                    "WARNING",
                    "CHANGED_CASE",
                    "Generated case differs from the maintained artifact "
                    "in: base_context, extra.",
                    "changed",
                ),
                Diagnostic(
                    "WARNING",
                    "STALE_CASE",
                    "Maintained case is no longer generated.",
                    "stale",
                ),
            ],
        )


class ReportTests(unittest.TestCase):
    def test_report(self) -> None:
        diagnostics = [
            Diagnostic("WARNING", "NEW_CASE", "New.", "x"),
            Diagnostic("ERROR", "CONFLICTING_ASSIGNMENTS", "Bad.", "x", "F"),
            Diagnostic("FATAL", "GENERATION_FAILURE", "Broken."),
        ]

        self.assertEqual(
            build_report(diagnostics, 2, False),
            "Symbolic Control-Word Generation Report\n"
            "=======================================\n\n"
            "Cases generated: 2\n"
            "Candidate written: no\n"
            "Information diagnostics: 0\n"
            "Warnings: 1\n"
            "Errors: 1\n"
            "Fatal errors: 1\n\n"
            "Diagnostics\n"
            "-----------\n"
            "WARNING NEW_CASE [x]: New.\n"
            "ERROR CONFLICTING_ASSIGNMENTS [x] [F]: Bad.\n"
            "FATAL GENERATION_FAILURE: Broken.\n",
        )
        self.assertTrue(
            build_report([], 0, True).endswith("No diagnostics.\n")
        )


# ---------------------------------------------------------------------------
# Contract with the upstream extractors
# ---------------------------------------------------------------------------

TOOLS = Path(__file__).resolve().parents[2]
EXTRACTOR_GOLDEN = {
    "execution": TOOLS
    / "execution-definition-extractor/tests/golden/valid"
    / "execution-definitions.json",
    "direct": TOOLS
    / "direct-control-extractor/tests/golden/valid"
    / "direct-control-definitions.json",
    "timing": TOOLS
    / "timing-constraint-extractor/tests/golden/valid"
    / "timing-constraints.json",
}
BUILDERS = {
    "execution": make_case,
    "direct": make_direct,
    "timing": lambda: make_timing("t", "A = 0", "B = 0"),
}


class ExtractorContractTests(unittest.TestCase):
    """Keep the entry shapes in step with the upstream extractors.

    The execution, direct-control and timing generators promote extracted
    entries unchanged, so the extractors' golden outputs show the entries
    this tool reads. If these tests fail after an extractor change, update
    this tool (and its builders) to match.
    """

    def test_extracted_entries_pass_field_checks(self) -> None:
        for key, path in EXTRACTOR_GOLDEN.items():
            spec = SPECS_BY_KEY[key]
            entries = json.loads(path.read_text(encoding="utf-8"))[
                spec.list_key
            ]
            with self.subTest(key=key):
                self.assertTrue(entries)
                for entry in entries:
                    self.assertEqual(
                        check_fields(
                            entry, entry["id"], ENTRY_CHECKS[key], spec.code
                        ),
                        [],
                    )

    def test_builders_match_extractor_shapes(self) -> None:
        for key, path in EXTRACTOR_GOLDEN.items():
            spec = SPECS_BY_KEY[key]
            entry = json.loads(path.read_text(encoding="utf-8"))[
                spec.list_key
            ][0]
            with self.subTest(key=key):
                self.assertEqual(list(BUILDERS[key]()), list(entry))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

GOLDEN_DIRECTORY = Path(__file__).resolve().parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"


class MainTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.candidate = self.root / DEFAULT_CANDIDATE
        self.report = self.root / DEFAULT_REPORT

    def write_inputs(self, documents: dict) -> None:
        directory = self.root / DEFAULT_ARTIFACT_DIRECTORY
        directory.mkdir(parents=True, exist_ok=True)
        for spec in INPUT_SPECS:
            (directory / spec.file_name).write_text(
                json.dumps(documents[spec.key]), encoding="utf-8"
            )

    def run_main(self, *extra: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.root), *extra])
        return exit_code, stdout.getvalue()

    def assert_report_matches_golden(self, name: str) -> None:
        """Compare the report against ``golden/<name>/``.

        Run with ``UPDATE_GOLDEN=1`` to rewrite the expected file after an
        intended output change, then review the diff.
        """

        actual = self.report.read_bytes().decode("utf-8")
        golden_path = GOLDEN_DIRECTORY / name / "generation-report.txt"
        if UPDATE_GOLDEN:
            golden_path.parent.mkdir(parents=True, exist_ok=True)
            golden_path.write_text(actual, encoding="utf-8", newline="\n")
        self.assertEqual(actual, golden_path.read_text(encoding="utf-8"))

    def test_review_run_writes_candidate_and_report(self) -> None:
        documents = make_documents(
            cases=[
                make_case("new"),
                make_case("changed", micro_operations=["U"]),
                make_case("same"),
            ]
        )
        maintained, _ = build_candidate(
            make_documents(
                cases=[
                    make_case("stale"),
                    make_case("changed"),
                    make_case("same"),
                ]
            ),
            None,
        )
        self.write_inputs(documents)
        target = self.root / DEFAULT_MAINTAINED
        target.write_text(json.dumps(maintained), encoding="utf-8")

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Candidate written: yes", stdout)
        self.assertEqual(
            self.candidate.read_text(encoding="utf-8"),
            json.dumps(
                build_candidate(documents, None)[0],
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
        )
        self.assert_report_matches_golden("review")

    def test_failed_run_removes_earlier_candidate(self) -> None:
        self.write_inputs(
            make_documents(
                cases=[
                    make_case(
                        context=["A = 0", "BAD = 1"],
                        micro_operations=["U", "NOPE"],
                        conditional_micro_operations=[
                            conditional("U is selected", "X")
                        ],
                    )
                ],
                direct=[make_direct(context=["A = 0"], assignments=["F ="])],
                timing=[make_timing("t", "TS = 1", "Q != 1")],
            )
        )
        self.candidate.parent.mkdir(parents=True)
        self.candidate.write_text("stale\n", encoding="utf-8")

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.candidate.exists())
        self.assertIn(
            "ERROR UNKNOWN_NAME [c] [context]\n"
            "  BAD is not a control input, encoded control-word field, "
            "MS or TS.",
            stdout,
        )
        self.assert_report_matches_golden("invalid")

    def test_missing_input_is_fatal(self) -> None:
        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn("FATAL GENERATION_FAILURE", stdout)
        self.assertIn(
            "Cases generated: 0", self.report.read_text(encoding="utf-8")
        )

    def test_artifact_directory_option(self) -> None:
        self.write_inputs(make_documents())

        exit_code, _ = self.run_main(
            "--artifact-dir", str(self.root / DEFAULT_ARTIFACT_DIRECTORY)
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(self.candidate.exists())

    def test_output_that_is_an_input_is_refused(self) -> None:
        self.write_inputs(make_documents())
        target = DEFAULT_ARTIFACT_DIRECTORY / "timing-constraints.json"

        exit_code, stdout = self.run_main("--report-output", str(target))

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout)
        self.assertTrue((self.root / target).exists())

    def test_output_that_is_a_directory_is_refused(self) -> None:
        self.write_inputs(make_documents())
        self.report.parent.mkdir(parents=True)
        self.report.write_text("earlier\n", encoding="utf-8")
        (self.root / "dir").mkdir()

        exit_code, stdout = self.run_main("--candidate-output", "dir")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout)
        self.assertTrue(self.report.exists())


if __name__ == "__main__":
    unittest.main()
