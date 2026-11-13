"""Tests for the control-word equivalence analyzer."""

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

from analyze_control_word_equivalence import (  # noqa: E402
    DEFAULT_ARTIFACT_DIRECTORY,
    INPUT_SPECS,
    Engine,
    Validator,
    analyze_case,
    build_analysis,
    main,
    read_json,
)

REPO_ROOT = Path(__file__).resolve().parents[4]

# ---------------------------------------------------------------------------
# Builders
#
# The default world has one-bit inputs A, B, C, R, W (R and W mutually
# exclusive), X1..X3 (exactly one), Y1, Y2 (at most one), and a 2-bit
# input K with values 00..11. Encoded fields are F and G (one bit), D
# (three bits, no listed values) and MS_NEXT, whose meanings FETCH and
# EXECUTE are the values of MS. Every field defaults to 0.
# ---------------------------------------------------------------------------

FLAGS = ("A", "B", "C", "R", "W", "X1", "X2", "X3", "Y1", "Y2")


def make_input(name, values=("0", "1"), width=1, constraints=(), derivation=None):
    return {
        "name": name,
        "width": width,
        "control_uses": ["predicate"],
        "values": [{"value": v} for v in values],
        "ranges": [],
        "constraints": [{"text": t} for t in constraints],
        "derivation": None if derivation is None else {"text": derivation},
    }


# IR decodes for the derivation tests: D_A and D_B are exclusive opcode
# decodes; D_C and D_E are independent low IR bits.
DECODES = (
    make_input("D_A", derivation="D_A = IR[11] == 1"),
    make_input("D_B", derivation="D_B = IR[11] == 0 AND IR[10] == 1"),
    make_input("D_C", derivation="D_C = IR[0]"),
    make_input("D_E", derivation="D_E = IR[1]"),
)


def make_documents(cases, timing=(), extra_inputs=()):
    inputs = [
        make_input(name, constraints=(
            ["Mutually exclusive with W."] if name == "R"
            else ["Mutually exclusive with R."] if name == "W" else []
        ))
        for name in FLAGS
    ]
    inputs.append(make_input("K", values=("00", "01", "10", "11"), width=2))
    inputs.append(
        {"name": "V", "width": 3, "control_uses": ["value"], "values": [],
         "ranges": [], "constraints": []}
    )
    inputs += list(extra_inputs)
    words = [
        {"name": "F", "width": 1, "control_word_role": "encoded",
         "default_value": "0", "values": []},
        {"name": "G", "width": 1, "control_word_role": "encoded",
         "default_value": "0", "values": []},
        {"name": "D", "width": 3, "control_word_role": "encoded",
         "default_value": "000", "values": []},
        {"name": "MS_NEXT", "width": 1, "control_word_role": "encoded",
         "default_value": "0",
         "values": [{"encoding": "0", "meaning": "FETCH"},
                    {"encoding": "1", "meaning": "EXECUTE"}]},
        {"name": "Z", "width": 1, "control_word_role": "derived"},
    ]
    return {
        "symbolic": {
            "artifact": "symbolic-control-words",
            "control_design_version": "v1",
            "cases": cases,
        },
        "inputs": {
            "specification_type": "control-input-schema",
            "control_design_version": "v1",
            "fields": inputs,
            "constraints": [
                {"kind": "exactly_one", "inputs": ["X1", "X2", "X3"],
                 "source": {"path": "doc", "line": 1}},
                {"kind": "at_most_one", "inputs": ["Y1", "Y2"],
                 "source": {"path": "doc", "line": 2}},
            ],
        },
        "words": {
            "specification_type": "control-word-schema",
            "control_design_version": "v1",
            "fields": words,
        },
        "timing": {
            "artifact": "timing-constraints",
            "control_design_version": "v1",
            "constraints": [
                {"id": i, "context": c, "requirement": r,
                 "source": {"path": "timing", "line": 1}}
                for i, c, r in timing
            ],
        },
    }


def assign(when, value=None, source="U", origin="micro-operation mapping",
           from_input=None):
    item = {}
    if from_input is not None:
        item["value_from_input"] = from_input
    else:
        item["value"] = value
    item.update({"when": when, "origin": origin, "source": source})
    return item


def make_case(case_id, base, **fields):
    assignments = {name: [] for name in ("F", "G", "D", "MS_NEXT")}
    assignments.update(fields)
    return {
        "execution_case_id": case_id,
        "source": {"path": "doc", "line": 10},
        "base_context": base,
        "defaults": {"F": "0", "G": "0", "D": "000", "MS_NEXT": "0"},
        "field_assignments": assignments,
    }


def run(cases, **options):
    return build_analysis(make_documents(cases, **options))


def analysis_of(cases, **options):
    analysis, diagnostics = run(cases, **options)
    if analysis is None:
        raise AssertionError(
            "analysis failed: " + "; ".join(d.message for d in diagnostics)
        )
    return analysis


def codes(diagnostics):
    return [d.code for d in diagnostics]


def case_entry(analysis, case_id):
    return next(c for c in analysis["cases"] if c["execution_case_id"] == case_id)


def classes_of(analysis, case_id):
    ids = case_entry(analysis, case_id)["component_classes"]
    return [c for c in analysis["component_classes"] if c["class_id"] in ids]


def aliases(analysis, kind):
    return [a for a in analysis["aliases"] if a["kind"] == kind]


def unreachable(analysis, kind):
    return [u for u in analysis["unreachable_regions"] if u["kind"] == kind]


# ---------------------------------------------------------------------------
# Equivalence and aliasing
# ---------------------------------------------------------------------------


class EquivalenceTests(unittest.TestCase):
    def test_cases_with_different_contexts_share_words(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[assign("MS = FETCH", "1")]),
            make_case("q", "MS = EXECUTE", F=[assign("MS = EXECUTE", "1")]),
        ])
        self.assertEqual(
            aliases(analysis, "cross_case"),
            [{"kind": "cross_case", "cases": ["p", "q"], "shared_word_count": 1}],
        )

    def test_one_field_difference_prevents_equivalence(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[assign("MS = FETCH", "1")]),
            make_case("q", "MS = EXECUTE", F=[assign("MS = EXECUTE", "1")],
                      G=[assign("MS = EXECUTE", "1")]),
        ])
        self.assertEqual(aliases(analysis, "cross_case"), [])

    def test_shared_word_count_is_exact_for_partial_overlap(self):
        # p produces F in {0, 1}; q produces only F = 1.
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[assign("A = 1", "1")]),
            make_case("q", "MS = EXECUTE", F=[assign("MS = EXECUTE", "1")]),
        ])
        self.assertEqual(case_entry(analysis, "p")["word_count"], 2)
        self.assertEqual(
            aliases(analysis, "cross_case")[0]["shared_word_count"], 1
        )

    def test_two_branches_in_one_case_produce_one_word(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[
                assign("A = 1", "1", source="U1"),
                assign("B = 1", "1", source="U2"),
            ]),
        ])
        (component,) = classes_of(analysis, "p")
        words = [b["word"] for b in component["branches"]]
        self.assertEqual(words, [{"F": "1"}, {"F": "0"}])
        within = aliases(analysis, "within_case")
        self.assertEqual(len(within), 1)
        self.assertEqual(within[0]["assignment_sets"], 3)  # U1, U2, both

    def test_default_only_equivalence(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[assign("A = 1", "0", source="U0")]),
        ])
        (component,) = classes_of(analysis, "p")
        self.assertEqual(len(component["branches"]), 1)
        self.assertEqual(component["branches"][0]["word"], {"F": "0"})
        self.assertEqual(len(aliases(analysis, "default_only")), 1)
        self.assertEqual(case_entry(analysis, "p")["significant_inputs"], [])
        entry = next(i for i in analysis["inputs"] if i["name"] == "A")
        self.assertEqual(entry["category"], "no_effect")

    def test_conditional_assignment_partitioning(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH",
                      F=[assign("MS = FETCH AND A = 1", "1")],
                      G=[assign("C = 1", "1")]),
        ])
        components = classes_of(analysis, "p")
        self.assertEqual([c["fields"] for c in components], [["F"], ["G"]])
        self.assertEqual(
            [b["condition"] for b in components[0]["branches"]],
            ["A = 1", "A = 0"],
        )
        self.assertEqual(case_entry(analysis, "p")["word_count"], 4)
        self.assertEqual(case_entry(analysis, "p")["significant_inputs"], ["A", "C"])

    def test_control_supplied_value_is_kept_distinct(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", D=[
                assign("A = 1", from_input="V", origin="control-supplied value"),
                assign("A = 0", "101"),
            ]),
        ])
        (component,) = classes_of(analysis, "p")
        self.assertEqual(
            [b["word"]["D"] for b in component["branches"]],
            ["101", {"from_input": "V"}],
        )
        supplied = aliases(analysis, "supplied_data")
        self.assertEqual(len(supplied), 1)
        self.assertEqual(supplied[0]["fields"], ["D"])
        entry = next(i for i in analysis["inputs"] if i["name"] == "V")
        self.assertEqual(entry["category"], "supplied_data")

    def test_alias_provenance_is_retained(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[
                assign("A = 1", "1", source="U1", origin="micro-operation mapping"),
                assign("B = 1", "1", source="D1", origin="direct-control definition"),
            ]),
        ])
        (component,) = classes_of(analysis, "p")
        branch = component["branches"][0]
        self.assertEqual(
            [(a["source"], a["origin"], a["in_every_region"]) for a in branch["assignments"]],
            [("U1", "micro-operation mapping", False),
             ("D1", "direct-control definition", False)],
        )
        self.assertEqual(component["cases"], ["p"])

    def test_identical_components_share_a_class(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", G=[assign("C = 1", "1")]),
            make_case("q", "MS = EXECUTE", G=[assign("C = 1", "1")]),
        ])
        self.assertEqual(len(analysis["component_classes"]), 1)
        self.assertEqual(analysis["component_classes"][0]["cases"], ["p", "q"])


# ---------------------------------------------------------------------------
# Constraints and reachability
# ---------------------------------------------------------------------------


class ReachabilityTests(unittest.TestCase):
    def test_exactly_one_eliminates_impossible_overlap(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH",
                      F=[assign("X1 = 1", "1")], G=[assign("X2 = 1", "1")]),
        ])
        # X1 and X2 are tied by the constraint into one component; F = G = 1
        # is impossible, and so is X1 = X2 = X3 = 0 (F = G = 0 needs X3).
        (component,) = classes_of(analysis, "p")
        words = [b["word"] for b in component["branches"]]
        self.assertNotIn({"F": "1", "G": "1"}, words)
        self.assertEqual(len(words), 3)
        regions = unreachable(analysis, "region")
        self.assertTrue(regions)
        self.assertTrue(
            all(r["conflicting_constraints"] == ["exactly_one:X1+X2+X3"] for r in regions)
        )
        self.assertTrue(all(r["assessment"] == "expected" for r in regions))

    def test_at_most_one_eliminates_impossible_overlap(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH",
                      F=[assign("Y1 = 1", "1")], G=[assign("Y2 = 1", "1")]),
        ])
        words = [b["word"] for b in classes_of(analysis, "p")[0]["branches"]]
        self.assertEqual(len(words), 3)
        self.assertNotIn({"F": "1", "G": "1"}, words)

    def test_mutual_exclusion_text_eliminates_overlap(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH",
                      F=[assign("R = 1", "1")], G=[assign("W = 1", "1")]),
        ])
        self.assertEqual(case_entry(analysis, "p")["word_count"], 3)
        ids = [c["id"] for c in analysis["constraints"]]
        self.assertIn("mutual_exclusion:R+W", ids)

    def test_timing_constraint_makes_branch_unreachable(self):
        analysis = analysis_of(
            [make_case("p", "MS = EXECUTE",
                       F=[assign("A = 1 AND B = 1", "1", source="U1")])],
            timing=[("timing:1", "MS = EXECUTE AND A = 1", "B != 1")],
        )
        (item,) = unreachable(analysis, "assignment")
        self.assertEqual(item["execution_case_id"], "p")
        self.assertEqual(item["assignment"]["source"], "U1")
        self.assertEqual(item["conflicting_constraints"], ["timing:1"])
        self.assertEqual(item["assessment"], "expected")
        self.assertEqual(item["condition"], "A = 1 AND B = 1")

    def test_contradictory_predicate_is_suspect(self):
        analysis, diagnostics = run([
            make_case("p", "MS = FETCH",
                      F=[assign("A = 1 AND A = 0", "1", source="U1")]),
        ])
        (item,) = unreachable(analysis, "assignment")
        self.assertEqual(item["assessment"], "suspect")
        self.assertEqual(item["conflicting_constraints"], ["predicate is contradictory"])
        self.assertIn("CONTRADICTORY_ASSIGNMENT_GUARD", codes(diagnostics))

    def test_contradictory_base_context_makes_case_unreachable(self):
        analysis, diagnostics = run([
            make_case("p", "MS = FETCH AND MS = EXECUTE", F=[assign("A = 1", "1")]),
        ])
        (item,) = unreachable(analysis, "case")
        self.assertEqual(item["assessment"], "suspect")
        self.assertFalse(case_entry(analysis, "p")["reachable"])
        self.assertEqual(case_entry(analysis, "p")["word_count"], 0)
        self.assertIn("UNREACHABLE_CASE", codes(diagnostics))

    def test_constraint_excluded_base_context_makes_case_unreachable(self):
        analysis, _ = run([make_case("p", "X1 = 0 AND X2 = 0 AND X3 = 0")])
        (item,) = unreachable(analysis, "case")
        self.assertEqual(item["conflicting_constraints"], ["exactly_one:X1+X2+X3"])

    def test_multi_valued_input_partitioning(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", D=[
                assign("K = 01", "001"),
                assign("K = 10 OR K = 11", "010"),
            ]),
        ])
        (component,) = classes_of(analysis, "p")
        self.assertEqual(
            [(b["word"]["D"], b["condition"]) for b in component["branches"]],
            [("001", "K = 01"), ("010", "(K = 10 OR K = 11)"), ("000", "K = 00")],
        )

    def test_overlapping_cases_and_uncovered_regions(self):
        analysis, diagnostics = run([
            make_case("p", "MS = FETCH"),
            make_case("q", "A = 1"),
        ])
        self.assertEqual(
            analysis["case_overlaps"],
            [{"cases": ["p", "q"], "condition": "MS = FETCH AND A = 1"}],
        )
        self.assertEqual(analysis["uncovered_regions"], ["MS = EXECUTE AND A = 0"])
        self.assertIn("CASE_OVERLAP", codes(diagnostics))
        self.assertIn("UNCOVERED_REGION", codes(diagnostics))


# ---------------------------------------------------------------------------
# IR derivations
# ---------------------------------------------------------------------------


class DerivationTests(unittest.TestCase):
    def test_exclusive_decodes_do_not_overlap(self):
        analysis, diagnostics = run(
            [make_case("p", "D_A = 1"), make_case("q", "D_B = 1")],
            extra_inputs=DECODES,
        )
        self.assertEqual(analysis["case_overlaps"], [])
        self.assertEqual(analysis["uncovered_regions"], ["D_A = 0 AND D_B = 0"])
        derivation = next(
            c for c in analysis["constraints"] if c["kind"] == "derivation"
        )
        self.assertEqual(derivation["inputs"], ["D_A", "D_B"])

    def test_impossible_decode_guard_is_expected_dead_space(self):
        analysis = analysis_of(
            [make_case("p", "D_A = 1", F=[assign("D_B = 1", "1", source="U")])],
            extra_inputs=DECODES,
        )
        (item,) = unreachable(analysis, "assignment")
        self.assertEqual(item["conflicting_constraints"], ["ir-derivation"])
        self.assertEqual(item["assessment"], "expected")
        self.assertEqual(case_entry(analysis, "p")["word_count"], 1)

    def test_independent_decode_bits_stay_separate(self):
        analysis = analysis_of(
            [make_case("p", "D_A = 1",
                       F=[assign("D_C = 1", "1")], G=[assign("D_E = 1", "1")])],
            extra_inputs=DECODES,
        )
        self.assertEqual(
            [c["fields"] for c in classes_of(analysis, "p")], [["F"], ["G"]]
        )
        entry = case_entry(analysis, "p")
        self.assertEqual(entry["significant_inputs"], ["D_C", "D_E"])
        self.assertEqual(entry["jointly_significant_inputs"], [])
        self.assertEqual(entry["word_count"], 4)

    def test_dependent_decodes_flip_together(self):
        # D_A and D_B are tied through IR[11]: from D_A = 1, D_B = 0 the
        # only neighbours change both, yet each still decides F.
        analysis = analysis_of(
            [make_case("p", "MS = FETCH", F=[assign("D_A = 1", "1")])],
            extra_inputs=DECODES,
        )
        self.assertEqual(case_entry(analysis, "p")["significant_inputs"], ["D_A"])

    def test_unusable_derivation_is_reported(self):
        broken = make_input("D_X", derivation="D_X = IR[0] (octal 1)")
        _, diagnostics = run([make_case("p", "MS = FETCH")], extra_inputs=[broken])
        self.assertIn("IR_DERIVATION_UNUSABLE", codes(diagnostics))


# ---------------------------------------------------------------------------
# Significance
# ---------------------------------------------------------------------------


class SignificanceTests(unittest.TestCase):
    def test_input_categories(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[assign("A = 1 OR B = 1", "1")],
                      D=[assign("C = 1", from_input="V")]),
        ])
        categories = {i["name"]: i["category"] for i in analysis["inputs"]}
        self.assertEqual(categories["A"], "behavioral")
        self.assertEqual(categories["C"], "behavioral")
        self.assertEqual(categories["V"], "supplied_data")
        self.assertEqual(categories["W"], "unreferenced")
        self.assertEqual(categories["MS"], "behavioral")  # selects the case
        ms = next(i for i in analysis["inputs"] if i["name"] == "MS")
        self.assertEqual(ms["selects_cases"], ["p"])
        self.assertEqual(ms["significant_in_cases"], [])

    def test_inputs_that_matter_only_together(self):
        # With X3 = 0, exactly one of X1 and X2 is 1, so no single flip of
        # X1 is reachable; yet F follows X1. Joint significance adds X1.
        analysis, diagnostics = run([
            make_case("p", "X3 = 0", F=[assign("X1 = 1", "1")]),
        ])
        entry = case_entry(analysis, "p")
        self.assertEqual(entry["significant_inputs"], ["X1"])
        self.assertEqual(entry["jointly_significant_inputs"], ["X1"])
        self.assertIn("JOINT_SIGNIFICANCE", codes(diagnostics))

    def test_single_flip_significance(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH", F=[assign("A = 1 AND B = 1", "1")]),
        ])
        entry = case_entry(analysis, "p")
        self.assertEqual(entry["significant_inputs"], ["A", "B"])
        self.assertEqual(entry["jointly_significant_inputs"], [])

    def test_control_word_field_compared_as_input_is_reported(self):
        analysis, diagnostics = run([
            make_case("p", "MS = FETCH", F=[assign("G = 1", "1")]),
        ])
        self.assertIn("CONTROL_FIELD_COMPARED_AS_INPUT", codes(diagnostics))
        entry = next(i for i in analysis["inputs"] if i["name"] == "G")
        self.assertEqual(entry["kind"], "control_word_field")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ValidationTests(unittest.TestCase):
    def test_unknown_input_and_malformed_predicate(self):
        analysis, diagnostics = run([
            make_case("p", "MS = FETCH", F=[assign("NOPE = 1", "1")],
                      G=[assign("A = = 1", "1")]),
        ])
        self.assertIsNone(analysis)
        self.assertIn("UNKNOWN_NAME", codes(diagnostics))
        self.assertIn("INVALID_EXPRESSION", codes(diagnostics))

    def test_invalid_compared_and_assigned_values(self):
        analysis, diagnostics = run([
            make_case("p", "MS = SOMEWHERE", F=[assign("K = 7", "2")]),
        ])
        self.assertIsNone(analysis)
        self.assertEqual(
            sorted(set(codes(diagnostics))),
            ["INVALID_COMPARED_VALUE", "INVALID_FIELD_VALUE"],
        )

    def test_unknown_or_mismatched_supplying_input(self):
        _, diagnostics = run([
            make_case("p", "MS = FETCH",
                      D=[assign("A = 1", from_input="NOPE")],
                      F=[assign("A = 1", from_input="V")]),
        ])
        self.assertIn("UNKNOWN_SUPPLYING_INPUT", codes(diagnostics))
        self.assertIn("SUPPLYING_INPUT_WIDTH_MISMATCH", codes(diagnostics))

    def test_complete_field_coverage(self):
        case = make_case("p", "MS = FETCH")
        del case["defaults"]["G"]
        case["field_assignments"]["EXTRA"] = []
        analysis, diagnostics = run([case])
        self.assertIsNone(analysis)
        self.assertIn("MISSING_CONTROL_FIELD", codes(diagnostics))
        self.assertIn("UNKNOWN_CONTROL_FIELD", codes(diagnostics))

    def test_every_branch_covers_every_component_field(self):
        analysis = analysis_of([
            make_case("p", "MS = FETCH",
                      F=[assign("A = 1", "1", source="U")],
                      G=[assign("A = 1", "1", source="U")]),
        ])
        (component,) = classes_of(analysis, "p")
        for branch in component["branches"]:
            self.assertEqual(list(branch["word"]), component["fields"])

    def test_conflicting_assignments_fail(self):
        analysis, diagnostics = run([
            make_case("p", "MS = FETCH",
                      F=[assign("A = 1", "1"), assign("B = 1", "0")]),
        ])
        self.assertIsNone(analysis)
        self.assertEqual(codes(diagnostics), ["CONFLICTING_ASSIGNMENTS"])
        self.assertIn("A = 1 AND B = 1", diagnostics[0].message)

    def test_non_conjunctive_base_is_rejected(self):
        _, diagnostics = run([make_case("p", "MS = FETCH OR A = 1")])
        self.assertEqual(codes(diagnostics), ["UNSUPPORTED_BASE_CONTEXT"])

    def test_artifact_identity_and_version(self):
        documents = make_documents([make_case("p", "MS = FETCH")])
        documents["timing"]["artifact"] = "other"
        documents["symbolic"]["control_design_version"] = "v2"
        _, diagnostics = build_analysis(documents)
        self.assertEqual(
            sorted(codes(diagnostics)),
            ["CONTROL_DESIGN_VERSION_MISMATCH", "UNEXPECTED_ARTIFACT_TYPE"],
        )


# ---------------------------------------------------------------------------
# Determinism and command line
# ---------------------------------------------------------------------------


class DeterminismTests(unittest.TestCase):
    def test_class_identifiers_and_ordering_are_deterministic(self):
        cases = [
            make_case("p", "MS = FETCH", F=[assign("A = 1", "1")],
                      G=[assign("C = 1", "1")]),
            make_case("q", "MS = EXECUTE", G=[assign("C = 1", "1")]),
        ]
        first = analysis_of(copy.deepcopy(cases))
        second = analysis_of(copy.deepcopy(cases))
        self.assertEqual(json.dumps(first), json.dumps(second))
        self.assertEqual(
            [c["class_id"] for c in first["component_classes"]],
            ["cc-0001", "cc-0002"],
        )
        self.assertEqual(case_entry(first, "q")["component_classes"], ["cc-0002"])
        self.assertEqual(
            [b["branch_id"] for b in first["component_classes"][0]["branches"]],
            ["cc-0001.b1", "cc-0001.b2"],
        )


class MainTests(unittest.TestCase):
    def write_inputs(self, directory, documents):
        for spec in INPUT_SPECS:
            (directory / spec.file_name).write_text(
                json.dumps(documents[spec.key]), encoding="utf-8"
            )

    def test_run_writes_analysis_and_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_inputs(root, make_documents([make_case("p", "MS = FETCH")]))
            with redirect_stdout(io.StringIO()):
                code = main(["--repo-root", temp, "--artifact-dir", ".",
                             "--analysis-output", "out/a.json",
                             "--report-output", "out/r.txt"])
            self.assertEqual(code, 0)
            text = (root / "out/a.json").read_bytes()
            self.assertTrue(text.endswith(b"}\n"))
            self.assertNotIn(b"\r\n", text)
            self.assertIn("Analysis written: yes", (root / "out/r.txt").read_text("utf-8"))

    def test_failed_run_removes_earlier_analysis(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "out").mkdir()
            (root / "out/a.json").write_text("stale", encoding="utf-8")
            self.write_inputs(
                root, make_documents([make_case("p", "MS = FETCH",
                                                F=[assign("NOPE = 1", "1")])])
            )
            with redirect_stdout(io.StringIO()):
                code = main(["--repo-root", temp, "--artifact-dir", ".",
                             "--analysis-output", "out/a.json",
                             "--report-output", "out/r.txt"])
            self.assertEqual(code, 1)
            self.assertFalse((root / "out/a.json").exists())
            self.assertIn("UNKNOWN_NAME", (root / "out/r.txt").read_text("utf-8"))

    def test_missing_input_is_fatal(self):
        with tempfile.TemporaryDirectory() as temp:
            with redirect_stdout(io.StringIO()):
                code = main(["--repo-root", temp, "--artifact-dir", ".",
                             "--report-output", "r.txt",
                             "--analysis-output", "a.json"])
            self.assertEqual(code, 1)
            self.assertIn("ANALYSIS_FAILURE", (Path(temp) / "r.txt").read_text("utf-8"))

    def test_output_that_is_an_input_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write_inputs(root, make_documents([make_case("p", "MS = FETCH")]))
            with redirect_stdout(io.StringIO()):
                code = main(["--repo-root", temp, "--artifact-dir", ".",
                             "--analysis-output", "timing-constraints.json"])
            self.assertEqual(code, 1)
            self.assertTrue((root / "timing-constraints.json").exists())


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class RepositoryTests(unittest.TestCase):
    """Analyze every promoted symbolic case."""

    @classmethod
    def setUpClass(cls):
        directory = REPO_ROOT / DEFAULT_ARTIFACT_DIRECTORY
        cls.documents = {
            spec.key: read_json(directory / spec.file_name) for spec in INPUT_SPECS
        }
        cls.analysis, cls.diagnostics = build_analysis(cls.documents)

    def test_every_promoted_case_is_analyzed(self):
        self.assertIsNotNone(self.analysis, [d.message for d in self.diagnostics])
        expected = [c["execution_case_id"] for c in self.documents["symbolic"]["cases"]]
        self.assertEqual(
            [c["execution_case_id"] for c in self.analysis["cases"]], expected
        )
        self.assertEqual(
            [d for d in self.diagnostics if d.severity in ("ERROR", "FATAL")], []
        )

    def test_every_schema_input_is_classified(self):
        names = [f["name"] for f in self.documents["inputs"]["fields"]]
        classified = [i["name"] for i in self.analysis["inputs"]][: len(names)]
        self.assertEqual(classified, names)

    def test_word_count_is_the_product_of_component_branches(self):
        model = Validator().build(self.documents)
        engine = Engine(model.full)
        classes = {c["class_id"]: c for c in self.analysis["component_classes"]}
        for entry in self.analysis["cases"][:10]:
            product = 1
            for class_id in entry["component_classes"]:
                product *= len(classes[class_id]["branches"])
            self.assertEqual(entry["word_count"], product)
        # A few concrete states land in a branch of every component.
        case = model.cases[0]
        result = analyze_case(model, engine, case)
        self.assertEqual(result.word_count, self.analysis["cases"][0]["word_count"])


if __name__ == "__main__":
    unittest.main()
