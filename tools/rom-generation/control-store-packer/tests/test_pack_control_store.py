"""Tests for the control-store packer.

The tests build small specifications inline; they do not read the real
maintained artifacts.
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pack_control_store as P  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture: a tiny machine
# ---------------------------------------------------------------------------


def make_input(name, derivation=None, domain="External Inputs"):
    return {
        "name": name, "width": 1, "domain": domain,
        "values": [{"value": "0"}, {"value": "1"}], "ranges": [], "constraints": [],
        "derivation": {"text": derivation} if derivation else None,
    }


def make_field(name, width=1, values=None, default="0", care="Always"):
    return {
        "name": name, "width": width, "control_word_role": "encoded",
        "values": values if values is not None else
        [{"encoding": str(v), "meaning": str(v)} for v in range(2 ** width)],
        "default_value": default, "value_required_when": care,
    }


MS_VALUES = [{"encoding": str(i), "meaning": m}
             for i, m in enumerate(("FETCH", "DEFER", "EXECUTE", "INTERRUPT", "DMA"))]


def documents(execute_guards=None, extra_cases=(), timing=()):
    ir = "IR-Derived Signals"
    inputs = [
        make_input("X", "X = IR[0]", ir),
        make_input("Y", "Y = IR[1]", ir),
        make_input("IR_INDIRECT", "IR_INDIRECT = IR[8]", ir),
        make_input("IR_OPR_HLT", "IR_OPR_HLT = IR[9]", ir),
        make_input("IR_IS_CAF", "IR_IS_CAF = IR[10]", ir),
        make_input("A"), make_input("B"), make_input("RUN"),
        *[make_input(n) for n in P.FP_COMMANDS],
        *[make_input(n) for n in P.SEQ_ALWAYS],
        *[make_input(n) for n in P.SEQ_RUNNING],
    ]
    words = [
        make_field("F"),
        make_field("G", 2, care="F=1"),
        make_field("MS_NEXT", 3, MS_VALUES),
        make_field("MS_LOAD"), make_field("RUN_NEXT", default="1"),
        make_field("HLT_REQ_NEXT"), make_field("/DMA_GRANT", default="1"),
        make_field("/INITIALIZE", default="1"),
    ]
    cases = []
    for ms in ("FETCH", "DEFER", "INTERRUPT", "DMA"):
        cases.append({"execution_case_id": ms.lower(),
                      "base_context": f"(MS = {ms} AND RUN = 1)",
                      "defaults": {}, "field_assignments": {}})
    cases.append({
        "execution_case_id": "execute",
        "base_context": "(MS = EXECUTE AND RUN = 1)",
        "defaults": {},
        "field_assignments": execute_guards if execute_guards is not None else {
            "F": [{"value": "1", "when": "((MS = EXECUTE AND RUN = 1) AND X = 1)"}],
            "G": [{"value": "2", "when": "((MS = EXECUTE AND RUN = 1) AND (X = 1 AND A = 1))"},
                  {"value": "1", "when": "((MS = EXECUTE AND RUN = 1) AND (X = 1 AND A = 0))"}],
            "HLT_REQ_NEXT": [{"value": "1", "when":
                              "((MS = EXECUTE AND RUN = 1) AND (TS = 3 AND IR_OPR_HLT = 1))"}],
        },
    })
    cases.append({
        "execution_case_id": "halted",
        "base_context": "RUN = 0",
        "defaults": {},
        "field_assignments": {
            "RUN_NEXT": [{"value": "1", "when": "(RUN = 0 AND FP_START = 1)"},
                         {"value": "0", "when": "(RUN = 0 AND FP_START = 0)"}],
        },
    })
    cases.extend(extra_cases)
    return {
        "inputs": {"fields": inputs, "constraints": [
            {"kind": "at_most_one", "inputs": list(P.FP_COMMANDS)}]},
        "words": {"fields": words},
        "symbolic": {"cases": cases},
        "timing": {"constraints": list(timing)},
    }


def build(**kwargs):
    model, diagnostics = P.build_model(documents(**kwargs))
    return model, diagnostics


# ---------------------------------------------------------------------------
# Units
# ---------------------------------------------------------------------------


class EncodingTests(unittest.TestCase):
    def test_octal_encodings(self):
        field = make_field("ALU", 4)
        field["values"] = [{"encoding": "12", "meaning": "CLEAR"}]
        self.assertEqual(P.octal_value(field, "12"), 0o12)
        self.assertEqual(P.octal_value(field, "CLEAR"), 0o12)
        self.assertEqual(P.octal_value(make_field("B", 3, values=[]), "101"), 5)
        with self.assertRaises(ValueError):
            P.octal_value(field, "13")

    def test_care_conditions(self):
        care = P.parse_care("(IDB_DRIVE=1 AND IDB_SRC=7) OR PC_INC=1")
        self.assertTrue(P.care_holds(care, {"IDB_DRIVE": 1, "IDB_SRC": 7, "PC_INC": 0}, 1))
        self.assertFalse(P.care_holds(care, {"IDB_DRIVE": 1, "IDB_SRC": 6, "PC_INC": 0}, 1))
        self.assertIsNone(P.parse_care("Always"))
        self.assertTrue(P.care_holds(P.parse_care("TS=4"), {}, 4))
        self.assertFalse(P.care_holds(P.parse_care("TS=4"), {}, 3))
        self.assertTrue(P.care_holds(P.parse_care("ALU_OP=12"), {"ALU_OP": 0o12}, None))


class DependenceTests(unittest.TestCase):
    def records(self):
        R = P.Record
        return [
            R({"A": "0", "B": "0"}, {"F": 0}, frozenset({"F"})),
            R({"A": "1", "B": "0"}, {"F": 1}, frozenset({"F"})),
            R({"A": "0", "B": "1"}, {"F": 0}, frozenset({"F"})),
            R({"A": "1", "B": "1"}, {"F": 1}, frozenset({"F"})),
        ]

    def test_unneeded_signals_are_dropped(self):
        self.assertEqual(P.needed_signals(self.records(), ("A", "B")), ["A"])

    def test_values_that_do_not_matter_are_ignored(self):
        records = self.records()
        records[2] = P.Record({"A": "0", "B": "1"}, {"F": 1}, frozenset())
        self.assertEqual(P.needed_signals(records, ("A", "B")), ["A"])

    def test_front_panel_commands_are_one_signal(self):
        R = P.Record
        records = [R({"FP_START": "1", "FP_CLEAR": "0"}, {"F": 1}, frozenset({"F"})),
                   R({"FP_START": "0", "FP_CLEAR": "1"}, {"F": 0}, frozenset({"F"}))]
        self.assertEqual(P.needed_signals(records, ("FP_CLEAR", "FP_START")), [P.FP_CMD])


class GroupTests(unittest.TestCase):
    def test_bin_packing_and_positions(self):
        needs = [frozenset({P.FP_CMD, "C"}), frozenset({"D"}), frozenset({"E", "F", "G", "H"}),
                 frozenset()]
        groups, placement = P.pack_groups(needs)
        self.assertEqual(len(groups), 2)
        state = groups[placement[frozenset({P.FP_CMD, "C"})]]
        self.assertEqual(state.bits[P.FP_CMD], 0)
        self.assertLessEqual(max(g.width() for g in groups), P.DP_OVL_WIDTH)
        self.assertEqual(placement[frozenset()], 0)
        for need, code in placement.items():
            self.assertTrue(need <= set(groups[code].signals))

    def test_overlay_values(self):
        group = P.Group(0, [P.FP_CMD, "C"], {P.FP_CMD: 0, "C": 3})
        self.assertEqual(P.overlay_values(group, 0b01101), {P.FP_CMD: "5", "C": "1"})


class AllocationTests(unittest.TestCase):
    def test_fields_never_required_together_share_bits(self):
        R = P.Record
        records = [R({}, {}, frozenset({"L", "S"})), R({}, {}, frozenset({"L", "T"}))]
        slots = P.allocate_bits(records, ["L", "S", "T"], {"L": 1, "S": 2, "T": 2})
        self.assertIn((2, ["S", "T"]), slots)
        self.assertIn((1, ["L"]), slots)


class AddressTests(unittest.TestCase):
    def test_address_maps(self):
        self.assertEqual(P.mapping_address(0o7777, 4, 1), (0o7777 << 3) | (3 << 1) | 1)
        self.assertEqual(P.datapath_address(2, 3, 5, 9), (2 << 12) | (2 << 10) | (5 << 5) | 9)
        values = {"HLT_REQ": "1", "FP_STOP": "0", "/DMA_REQ": "1",
                  "FP_SINGLE_INSTRUCTION": "1", "FP_SINGLE_STEP": "0",
                  "INTERRUPT_REQUEST_VALID": "1"}
        self.assertEqual(P.sequencer_address(0, 1, values, False, "1"),
                         (1 << 9) | (0b101 << 5) | (1 << 4) | (1 << 3))
        halted = {"FP_EXAMINE": "1"}
        self.assertEqual(P.sequencer_address(7, 1, halted, True, "0"), (7 << 12) | (5 << 5))


# ---------------------------------------------------------------------------
# Packing
# ---------------------------------------------------------------------------


class PackTests(unittest.TestCase):
    def test_packs_and_verifies(self):
        model, diagnostics = build()
        self.assertEqual(diagnostics, [])
        packing, diagnostics = P.pack(model)
        self.assertEqual([d.code for d in diagnostics], [])
        self.assertGreater(packing.checked, 0)
        # X = 0 and X = 1 behave differently in every EXECUTE TS.
        self.assertEqual({ts: len(v) for ts, v in packing.variants.items()},
                         {1: 2, 2: 2, 3: 2, 4: 2})
        self.assertEqual(packing.ir_seq_select[(1, 3)], "IR_OPR_HLT")
        self.assertIsNone(packing.ir_seq_select[(1, 1)])
        # FP commands change only RUN_NEXT, a sequencer field, so the
        # datapath overlay carries only A.
        signals = {s for g in packing.groups for s in g.signals}
        self.assertEqual(signals, {"A"})

    def test_corrupted_image_is_detected(self):
        model, _ = build()
        packing, _ = P.pack(model)
        dp = P.behaviors(model, model.datapath_fields, [])
        seq = P.behaviors(model, model.sequencer_fields, [])
        offset, _ = packing.layout["F"]
        words = packing.images["_datapath_words"]
        for address in range(len(words)):
            words[address] ^= 1 << offset
        diagnostics = []
        P.verify(packing, dp, seq, diagnostics)
        self.assertIn("VERIFICATION_MISMATCH", {d.code for d in diagnostics})

    def hlt_capture_address(self, dma_req):
        # EXECUTE TS3 with IR_OPR_HLT on IR_SEQ; the word compares no
        # sequencer input, so the hardware may present any of them.
        values = {"HLT_REQ": "0", "FP_STOP": "0", "/DMA_REQ": dma_req,
                  "FP_SINGLE_INSTRUCTION": "0", "FP_SINGLE_STEP": "0",
                  "INTERRUPT_REQUEST_VALID": "0"}
        return P.sequencer_address(2, 3, values, False, "1")

    def test_ignored_inputs_hold_the_word_at_every_value(self):
        model, _ = build()
        packing, _ = P.pack(model)
        sequencer = packing.images["sequencer"]
        for bits in range(64):
            values = {n: str((bits >> i) & 1) for i, n in
                      enumerate((*P.SEQ_ALWAYS, *P.SEQ_RUNNING))}
            address = P.sequencer_address(2, 3, values, False, "1")
            self.assertEqual(P._seq_unpack(model, sequencer[address], "HLT_REQ_NEXT"), 1,
                             values)

    def test_corruption_at_an_ignored_input_value_is_detected(self):
        model, _ = build()
        packing, _ = P.pack(model)
        dp = P.behaviors(model, model.datapath_fields, [])
        seq = P.behaviors(model, model.sequencer_fields, [])
        offset = sum(model.widths[n] for n in model.sequencer_fields[
            :model.sequencer_fields.index("HLT_REQ_NEXT")])
        packing.images["sequencer"][self.hlt_capture_address("1")] ^= 1 << offset
        diagnostics = []
        P.verify(packing, dp, seq, diagnostics)
        self.assertIn("VERIFICATION_MISMATCH", {d.code for d in diagnostics})

    def test_input_supplied_value_is_an_error(self):
        guards = {"G": [{"value_from_input": "X", "when": "MS = EXECUTE"}]}
        _, diagnostics = build(execute_guards=guards)
        self.assertEqual([d.code for d in diagnostics], ["INPUT_SUPPLIED_VALUE"])

    def test_invisible_sequencer_dependence_is_an_error(self):
        guards = {"HLT_REQ_NEXT": [{"value": "1", "when":
                                    "((MS = EXECUTE AND RUN = 1) AND A = 1)"}]}
        model, _ = build(execute_guards=guards)
        _, diagnostics = P.pack(model)
        self.assertIn("INVISIBLE_DEPENDENCY", {d.code for d in diagnostics})

    def test_sequencer_needing_two_decodes_in_one_ts_is_an_error(self):
        guards = {"HLT_REQ_NEXT": [{"value": "1", "when":
                                    "((MS = EXECUTE AND RUN = 1) AND (TS = 3 AND "
                                    "(IR_OPR_HLT = 1 OR IR_IS_CAF = 1)))"}]}
        model, _ = build(execute_guards=guards)
        _, diagnostics = P.pack(model)
        self.assertIn("IR_SEQ_TOO_WIDE", {d.code for d in diagnostics})

    def test_unreachable_context_is_an_error(self):
        timing = [{"context": "MS = DMA", "requirement": "RUN = 0"}]
        model, _ = build(timing=timing)
        _, diagnostics = P.pack(model)
        self.assertIn("NO_REACHABLE_STATE", {d.code for d in diagnostics})

    def test_invariants_remove_unreachable_ir_values(self):
        # DEFER is reachable only with IR_INDIRECT = 1; the IR values
        # without it must not hide the reachable ones.
        timing = [{"context": "MS = DEFER", "requirement": "IR_INDIRECT = 1"}]
        model, _ = build(timing=timing)
        packing, diagnostics = P.pack(model)
        self.assertEqual([d.code for d in diagnostics], [])


class EndToEndTests(unittest.TestCase):
    def test_main_writes_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = root / "rom/microcode/v1"
            artifacts.mkdir(parents=True)
            for key, name in P.INPUT_FILES.items():
                (artifacts / name).write_text(json.dumps(documents()[key]), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out:
                code = P.main(["--repo-root", str(root)])
            self.assertEqual(code, 0, out.getvalue())
            images = sorted(p.name for p in (root / P.DEFAULT_IMAGES).glob("*.hex"))
            self.assertEqual(images, ["datapath-0.hex", "datapath-1.hex", "datapath-2.hex",
                                      "datapath-3.hex", "datapath-4.hex", "datapath-5.hex",
                                      "mapping.hex", "sequencer.hex"])
            lines = (root / P.DEFAULT_IMAGES / "mapping.hex").read_text().splitlines()
            self.assertEqual(len(lines), 1 << P.ADDRESS_BITS)
            report = (root / P.DEFAULT_REPORT).read_text(encoding="utf-8")
            self.assertIn("Status: SUCCEEDED", report)

    def test_missing_input_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            with redirect_stdout(io.StringIO()):
                code = P.main(["--repo-root", directory])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
