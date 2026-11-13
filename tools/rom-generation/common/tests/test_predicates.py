"""Tests for the shared IR-derivation evaluator in predicates.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from predicates import (  # noqa: E402
    DerivationError,
    ir_derivation_table,
    parse_derivation,
    strip_derivation_comments,
)


def field(name: str, text: str | None, width: int = 1) -> dict:
    return {
        "name": name,
        "width": width,
        "derivation": None if text is None else {"text": text},
    }


def table(*fields: dict) -> tuple[dict, list]:
    return ir_derivation_table({f["name"]: f for f in fields})


class ParseTests(unittest.TestCase):
    def test_comments_are_ignored(self) -> None:
        self.assertEqual(
            strip_derivation_comments("A = IR[0] // note\nOR IR[1] // more"),
            "A = IR[0] \nOR IR[1] ",
        )
        name, expression = parse_derivation(
            "X =\n(IR[11:9] == 000) OR  // AND\n(IR[11:9] == 001)  // TAD"
        )
        self.assertEqual(name, "X")
        self.assertEqual(
            expression,
            ("or", ("eq", ("bits", 11, 9), "000"), ("eq", ("bits", 11, 9), "001")),
        )

    def test_precedence_and_forms(self) -> None:
        _, expression = parse_derivation("X = NOT IR[1] AND Y OR IR[2]==1")
        self.assertEqual(
            expression,
            (
                "or",
                ("and", ("not", ("bits", 1, 1)), ("name", "Y")),
                ("eq", ("bits", 2, 2), "1"),
            ),
        )
        self.assertEqual(parse_derivation("F = IR[8:3]")[1], ("bits", 8, 3))

    def test_malformed(self) -> None:
        for text in ("IR[0]", "X = IR[12]", "X = (IR[0]", "X = IR[0] ==", "X = IR[0] (octal 1)"):
            with self.subTest(text=text), self.assertRaises(DerivationError):
                parse_derivation(text)


class TableTests(unittest.TestCase):
    def test_pdp8_decodes(self) -> None:
        values, problems = table(
            field("IR_IS_IOT", "IR_IS_IOT = (IR[11:9] == 110)"),
            field("IR_IOA", "IR_IOA = IR[8:3]", width=6),
            field(
                "IR_WRITES_DF",
                "IR_WRITES_DF = (IR[11:6] == 110010 AND IR[2]==0 AND IR[0]==1)",
            ),
            field(
                "IR_IS_CAF",
                "IR_IS_CAF =\nIR_IS_IOT\nAND (IR_IOA == 000000)\nAND (IR[2:0] == 111)",
            ),
        )
        self.assertEqual(problems, [])
        self.assertEqual(values["IR_IS_IOT"][0o6213], "1")
        self.assertEqual(values["IR_IOA"][0o6213], "010001")
        self.assertEqual(values["IR_WRITES_DF"][0o6213], "1")
        self.assertEqual(values["IR_WRITES_DF"][0o6214], "0")
        self.assertEqual(values["IR_IS_CAF"][0o6007], "1")
        self.assertEqual(values["IR_IS_CAF"][0o6017], "0")
        self.assertEqual(len(values["IR_IOA"]), 4096)

    def test_non_ir_and_unusable_derivations(self) -> None:
        values, problems = table(
            field("PLAIN", None),
            field("STATE", "STATE = A AND B"),  # mentions no IR bits: ignored
            field("MIXED", "MIXED = IR[0] AND EAI"),
            field("BROKEN", "BROKEN = IR[0] (octal 1)"),
            field("WIDE", "WIDE = IR[1:0] == 1"),
            field("CONDITION", "CONDITION = IR[1:0] AND IR[2]"),
        )
        self.assertEqual(values, {})
        self.assertEqual(
            [name for name, _ in problems],
            ["BROKEN", "MIXED", "WIDE", "CONDITION"],
        )

    def test_domain_marks_derivations_built_from_other_decodes(self) -> None:
        iot = field("IR_IS_IOT", "IR_IS_IOT = (IR[11:9] == 110)")
        memext = field("MEMEXT", "MEMEXT = IR_IS_IOT AND (IR[8:6] == 010)")
        external = field("EXTERNAL", "EXTERNAL = IR_IS_IOT AND NOT MEMEXT")
        state = field("STATE", "STATE = IR_IS_IOT AND EAI")

        values, problems = table(iot, memext, external, state)
        self.assertNotIn("EXTERNAL", values)  # no domain, no IR bits: ignored
        self.assertEqual(problems, [])

        external["domain"] = "IR-Derived Signals"
        values, problems = table(iot, memext, external, state)
        self.assertEqual(problems, [])
        self.assertEqual(values["EXTERNAL"][0o6031], "1")
        self.assertEqual(values["EXTERNAL"][0o6213], "0")
        self.assertEqual(values["EXTERNAL"][0o1234], "0")
        self.assertNotIn("STATE", values)

        state["domain"] = "IR-Derived Signals"
        _, problems = table(iot, memext, external, state)
        self.assertEqual([name for name, _ in problems], ["STATE"])

    def test_value_must_fit_width(self) -> None:
        _, problems = table(field("F", "F = IR[2:0]", width=2))
        self.assertEqual(problems, [("F", "Derived value exceeds 2 bits.")])


if __name__ == "__main__":
    unittest.main()
