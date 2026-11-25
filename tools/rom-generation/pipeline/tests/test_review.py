"""Tests for review.py: reviewed decisions against the run's evidence."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import review as R  # noqa: E402


def schema(*fields):
    return {"fields": list(fields), "diagnostics": [
        {"code": "CONTROL_USES_UNRESOLVED", "input_name": "NEW"},
        {"code": "OTHER", "input_name": "NEW"}]}


def field(name, uses, outside=None):
    f = {"name": name, "control_uses": uses}
    if outside is not None:
        f["outside_selection"] = outside
    return f


def analysis(**categories):
    return {"inputs": [{"name": n, "kind": "control_input", "category": c}
                       for n, c in categories.items()]}


WORDS = {"fields": [
    {"name": "DF_SRC", "control_word_role": "encoded",
     "values": [{"encoding": "0", "meaning": "IR_DF"}, {"encoding": "1", "meaning": "FP_DF"}]},
]}


class ControlUseItemTests(unittest.TestCase):
    def items(self, *fields, **categories):
        return {i.name: i for i in R.control_use_items(schema(*fields), analysis(**categories), WORDS)}

    def test_agreeing_inputs_are_not_items(self):
        items = self.items(field("A", ["predicate"], False), field("IR_DF", ["value"], True),
                           field("B", ["none"], True),
                           A="behavioral", IR_DF="supplied_data", B="unreferenced")
        self.assertEqual(items, {})

    def test_stale_predicate_listed_in_section_7_becomes_none(self):
        item = self.items(field("ACN", ["predicate"], True), ACN="unreferenced")["ACN"]
        self.assertEqual((item.current, item.proposed), (["predicate"], ["none"]))

    def test_unresolved_input_read_by_a_condition_becomes_predicate(self):
        item = self.items(field("SKIP", [], False), SKIP="behavioral")["SKIP"]
        self.assertEqual(item.proposed, ["predicate"])

    def test_an_encoding_is_value_evidence(self):
        item = self.items(field("FP_DF", [], True), FP_DF="unreferenced")["FP_DF"]
        self.assertEqual(item.proposed, ["value"])
        self.assertIn("DF_SRC = FP_DF", " ".join(item.evidence))

    def test_a_reviewed_value_is_kept(self):
        items = self.items(field("IR_ADDR", ["value"], True), IR_ADDR="unreferenced")
        self.assertEqual(items, {})

    def test_unlisted_and_unread_has_no_proposal(self):
        item = self.items(field("X", ["predicate"], False), X="unreferenced")["X"]
        self.assertIsNone(item.proposed)
        self.assertIn("specification gap", " ".join(item.evidence))

    def test_section_7_from_the_candidate_overrides_the_schema(self):
        items = R.control_use_items(schema(field("ACN", ["predicate"])),
                                    analysis(ACN="unreferenced"), WORDS, {"ACN": True})
        self.assertEqual(items[0].proposed, ["none"])


class RoleItemTests(unittest.TestCase):
    def test_unresolved_roles_follow_explicit_value_required(self):
        words = {"fields": [{"name": "A", "control_word_role": None, "explicit_value_required": "No"},
                            {"name": "B", "control_word_role": None, "explicit_value_required": "Yes"},
                            {"name": "C", "control_word_role": "encoded"}]}
        self.assertEqual([(i.name, i.proposed) for i in R.role_items(words)],
                         [("A", "derived"), ("B", "encoded")])


class AnswerTests(unittest.TestCase):
    def test_typed_classifications(self):
        uses = R.Item(R.INPUT_SCHEMA, "A", R.USES, [], None)
        self.assertEqual(R.parse_answer(uses, "Predicate, value"), ["predicate", "value"])
        self.assertEqual(R.parse_answer(uses, "none"), ["none"])
        for bad in ("none,value", "maybe", "", "value,value"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                R.parse_answer(uses, bad)
        role = R.Item(R.WORD_SCHEMA, "F", R.ROLE, None, None)
        self.assertEqual(R.parse_answer(role, "derived"), "derived")
        with self.assertRaises(ValueError):
            R.parse_answer(role, "value")


class RecordTests(unittest.TestCase):
    def test_answers_are_written_and_resolved_warnings_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = Path("schema.json")
            (root / path).write_text(json.dumps(schema(field("NEW", []), field("B", ["predicate"]))),
                                     encoding="utf-8")
            item = R.Item(R.INPUT_SCHEMA, "NEW", R.USES, [], ["predicate"])
            R.record(root, {R.INPUT_SCHEMA: path}, [(item, ["predicate"])])
            data = json.loads((root / path).read_text(encoding="utf-8"))
        self.assertEqual(data["fields"][0]["control_uses"], ["predicate"])
        self.assertEqual(data["fields"][1]["control_uses"], ["predicate"])
        self.assertEqual([d["code"] for d in data["diagnostics"]], ["OTHER"])


if __name__ == "__main__":
    unittest.main()
