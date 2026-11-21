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
from unittest import mock  # noqa: E402

# The address-formation decodes outside EXECUTE come from the selected design
# (common/design.py). Most tests use the v1 form (VARIANT = 0, A2 = A1 = 0, no
# state-group RUN multiplexer) so that they do not depend on PDP8_DESIGN;
# V2AddressFormationTests and V2HaltAndSkipTests set them.
_PATCHES = [mock.patch.object(P, "NON_EXECUTE_VARIANT", None),
            mock.patch.object(P, "SEQ_A2", None),
            mock.patch.object(P, "SEQ_A1", None),
            mock.patch.object(P, "STATE_GROUP_RUN_MUX", False)]


def setUpModule():
    for patch in _PATCHES:
        patch.start()


def tearDownModule():
    for patch in _PATCHES:
        patch.stop()


# ---------------------------------------------------------------------------
# Fixture: a tiny machine
# ---------------------------------------------------------------------------


def make_input(name, derivation=None, domain="External Inputs", width=1):
    return {
        "name": name, "width": width, "domain": domain,
        "values": ([{"value": "0"}, {"value": "1"}] if width == 1 else []),
        "ranges": [], "constraints": [],
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


FETCH_TS4 = "(MS = FETCH AND RUN = 1) AND TS = 4"
DEFER_TS4 = "(MS = DEFER AND RUN = 1) AND TS = 4"


def sequencing(v2):
    """FETCH and DEFER TS4 next states, as a real machine sequences them; with
    v2, an IR_NO_EXECUTE instruction completes in FETCH (direct) or DEFER."""
    if not v2:
        return ({"MS_NEXT": [{"value": "1", "when": f"({FETCH_TS4} AND IR_INDIRECT = 1)"},
                             {"value": "2", "when": f"({FETCH_TS4} AND IR_INDIRECT = 0)"}]},
                {"MS_NEXT": [{"value": "2", "when": f"({DEFER_TS4})"}]})
    return ({"MS_NEXT": [{"value": "1", "when": f"({FETCH_TS4} AND IR_INDIRECT = 1)"},
                         {"value": "2", "when":
                          f"({FETCH_TS4} AND IR_INDIRECT = 0 AND IR_NO_EXECUTE = 0)"},
                         {"value": "0", "when":
                          f"({FETCH_TS4} AND IR_INDIRECT = 0 AND IR_NO_EXECUTE = 1)"}],
             "F": [{"value": "1", "when": "((MS = FETCH AND RUN = 1) AND TS = 3 AND IR_CLASS = 01)"}]},
            {"MS_NEXT": [{"value": "2", "when": f"({DEFER_TS4} AND IR_NO_EXECUTE = 0)"},
                         {"value": "0", "when": f"({DEFER_TS4} AND IR_NO_EXECUTE = 1)"}]})


def documents(execute_guards=None, extra_cases=(), timing=(), v2=False, fetch_extra=None):
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
    if v2:
        inputs += [make_input("IR_CLASS", "IR_CLASS = {IR[5], IR[4]}", ir, width=2),
                   make_input("IR_NO_EXECUTE", "IR_NO_EXECUTE = IR[4]", ir)]
    fetch, defer = sequencing(v2)
    if fetch_extra:
        fetch = {**fetch, **fetch_extra}
    words = [
        make_field("F"),
        make_field("G", 2, care="F=1"),
        make_field("MS_NEXT", 3, MS_VALUES),
        make_field("MS_LOAD"), make_field("RUN_NEXT", default="1"),
        make_field("HLT_REQ_NEXT"),
        make_field("/INITIALIZE", default="1"),
    ]
    cases = []
    for ms, assignments in (("FETCH", fetch), ("DEFER", defer), ("INTERRUPT", {}), ("DMA", {})):
        cases.append({"execution_case_id": ms.lower(),
                      "base_context": f"(MS = {ms} AND RUN = 1)",
                      "defaults": {}, "field_assignments": assignments})
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

    def test_place_group_renumbers(self):
        needs = [frozenset({"C", "D"}), frozenset({"E"}), frozenset()]
        groups, placement = P.pack_groups(needs)
        self.assertEqual(len(groups), 1)
        P.place_group(groups, placement, frozenset({"E"}), 1)
        # Both needs fit one group, which moves to code 1; an empty group
        # fills code 0. Placements follow their group, except the empty
        # need, which fits any group and stays at 0.
        self.assertEqual([g.code for g in groups], [0, 1])
        self.assertEqual(placement[frozenset({"E"})], 1)
        self.assertEqual(placement[frozenset({"C", "D"})], 1)
        self.assertEqual(groups[1].signals, ["C", "D", "E"])
        self.assertEqual(groups[0].signals, [])
        self.assertEqual(placement[frozenset()], 0)

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
        self.assertEqual(P.mapping_address(0o7777, 4), (0o7777 << 3) | (3 << 1))
        self.assertEqual([P.next_ts(t) for t in (1, 2, 3, 4)], [2, 3, 4, 1])
        self.assertEqual([P.previous_ts(t) for t in (1, 2, 3, 4)], [4, 1, 2, 3])
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
        self.assertEqual(packing.ir_seq_select[(0, 4)], "IR_INDIRECT")
        # FP commands change only RUN_NEXT, a sequencer field, so the
        # datapath overlay carries only A.
        signals = {s for g in packing.groups for s in g.signals}
        self.assertEqual(signals, {"A"})
        self.assertGreater(len(packing.groups), P.NON_EXECUTE_GROUP)

    def test_mapping_rom_holds_the_next_timing_state(self):
        model, _ = build()
        packing, _ = P.pack(model)
        mapping = packing.images["mapping"]
        for ir in (0, 1):  # X = IR[0] selects the variant
            for ts in (1, 2, 3, 4):
                target = P.next_ts(ts)
                entry = mapping[P.mapping_address(ir, ts)]
                self.assertEqual(entry & 0b11111, packing.variant_of[(target, ir)])
                hlt = (entry >> P.IR_SEQ_BIT) & 1
                # IR_OPR_HLT = IR[9] is presented for EXECUTE TS3 only.
                self.assertEqual(hlt, 0)
            hlt_ir = ir | (1 << 9)
            entry = mapping[P.mapping_address(hlt_ir, 2)]
            self.assertEqual((entry >> P.IR_SEQ_BIT) & 1, 1)
            self.assertEqual((mapping[P.mapping_address(hlt_ir, 3)] >> P.IR_SEQ_BIT) & 1, 0)

    def test_non_execute_selection_is_fixed(self):
        model, _ = build()
        packing, _ = P.pack(model)
        indirect = 1 << 8
        entry = P.slice_select(packing, False, indirect, 4)
        self.assertEqual(entry & 0b11111, 0)
        self.assertEqual((entry >> P.VARIANT_WIDTH) & 0b11, P.NON_EXECUTE_GROUP)
        self.assertEqual((entry >> P.IR_SEQ_BIT) & 1, 1)
        self.assertEqual(P.slice_select(packing, True, 1, 1),
                         packing.images["mapping"][P.mapping_address(1, 4)])

    def test_unshifted_mapping_image_is_detected(self):
        model, _ = build()
        packing, _ = P.pack(model)
        dp = P.behaviors(model, model.datapath_fields, [])
        seq = P.behaviors(model, model.sequencer_fields, [])
        mapping = packing.images["mapping"]
        # Write each TS's own entry instead of the next TS's.
        shifted = list(mapping)
        for ir in range(4096):
            for ts in (1, 2, 3, 4):
                mapping[P.mapping_address(ir, ts)] = shifted[
                    P.mapping_address(ir, P.previous_ts(ts))]
        diagnostics = []
        P.verify(packing, dp, seq, diagnostics)
        self.assertIn("VERIFICATION_MISMATCH", {d.code for d in diagnostics})

    def test_non_execute_ir_seq_must_be_ir_indirect(self):
        extra = ({
            "execution_case_id": "fetch-hlt",
            "base_context": "(MS = FETCH AND RUN = 1)",
            "defaults": {},
            "field_assignments": {"HLT_REQ_NEXT": [{"value": "1", "when":
                                  "((MS = FETCH AND RUN = 1) AND (TS = 4 AND IR_OPR_HLT = 1))"}]},
        },)
        documents_ = documents(extra_cases=extra)
        documents_["symbolic"]["cases"] = [c for c in documents_["symbolic"]["cases"]
                                           if c["execution_case_id"] != "fetch"]
        model, _ = P.build_model(documents_)
        _, diagnostics = P.pack(model)
        self.assertIn("NON_EXECUTE_IR_SEQ", {d.code for d in diagnostics})

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
            artifacts = root / P.DEFAULT_ARTIFACT_DIRECTORY   # the selected design's
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


class V2AddressFormationTests(unittest.TestCase):
    """Option 2 (Control Store Organization §5.4.2, §5.6, §9): outside
    EXECUTE, VARIANT = IR_CLASS and A2 = IR_NO_EXECUTE; INSTR_END agrees."""

    JMP, JMP_I, OTHER = 1 << 4, (1 << 4) | (1 << 8), 0     # fixture: IR[4] = no EXECUTE

    def setUp(self):
        patches = [mock.patch.object(P, "NON_EXECUTE_VARIANT", "IR_CLASS"),
                   mock.patch.object(P, "SEQ_A2", "IR_NO_EXECUTE")]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def pack(self, **kwargs):
        model, diagnostics = P.build_model(documents(v2=True, **kwargs))
        self.assertEqual([d.code for d in diagnostics], [])
        return P.pack(model)

    def test_packs_and_verifies(self):
        packing, diagnostics = self.pack()
        self.assertEqual([d.code for d in diagnostics], [])
        self.assertGreater(packing.checked, 0)

    def test_variant_is_the_class_outside_execute(self):
        packing, _ = self.pack()
        self.assertEqual(P.slice_select(packing, False, self.JMP, 3) & 0b11111, 0b01)
        self.assertEqual(P.slice_select(packing, False, self.OTHER, 3) & 0b11111, 0b00)
        fetch = packing.model.ms_codes["FETCH"]

        def f(variant):
            group = packing.groups[P.NON_EXECUTE_GROUP]
            word = packing.images["_datapath_words"][P.datapath_address(fetch, 3, variant, 0)]
            return P.unpack(packing, word, "F")
        self.assertEqual((f(0b01), f(0b00)), (1, 0))

    def test_a2_selects_completion(self):
        packing, _ = self.pack()
        fetch = packing.model.ms_codes["FETCH"]
        values = {"/DMA_REQ": "1"}

        def next_state(irseq, a2):
            word = packing.images["sequencer"][P.sequencer_address(fetch, 4, values, False,
                                                                   irseq, a2)]
            return P._seq_unpack(packing.model, word, "MS_NEXT")
        self.assertEqual(next_state("0", "0"), 2)   # EXECUTE
        self.assertEqual(next_state("0", "1"), 0)   # completes in FETCH
        self.assertEqual(next_state("1", "1"), 1)   # JMP I: DEFER

    def test_class_dependence_before_ir_loads_is_an_error(self):
        early = {"F": [{"value": "1", "when": "((MS = FETCH AND RUN = 1) AND TS = 1 AND IR_CLASS = 01)"}]}
        model, _ = P.build_model(documents(v2=True, fetch_extra=early))
        _, diagnostics = P.pack(model)
        self.assertIn("NON_EXECUTE_CLASS_DEPENDENCE", [d.code for d in diagnostics])

    def test_instr_end_disagreement_is_an_error(self):
        # A FETCH TS4 that completes without IR_NO_EXECUTE: the INSTR_END gates would miss it.
        wrong = {"MS_NEXT": [{"value": "0", "when": f"({FETCH_TS4})"}]}
        model, _ = P.build_model(documents(v2=True, fetch_extra=wrong))
        _, diagnostics = P.pack(model)
        self.assertIn("INSTR_END_DISAGREES", [d.code for d in diagnostics])

class V2HaltAndSkipTests(unittest.TestCase):
    """Slice C2 (Control Store Organization §5.6, §6.3): HLT is captured in FETCH TS3 through
    sequencer A1 = IR_OPR_HLT, and the state group's low bits are multiplexed by RUN so that
    SKIP reaches FETCH TS4 while FP_CMD reaches the halted words."""

    SKIP_F = {"F": [{"value": "1", "when": f"({FETCH_TS4} AND SKIP = 1)"}],
              "HLT_REQ_NEXT": [{"value": "1", "when":
                                "((MS = FETCH AND RUN = 1) AND TS = 3 AND IR_OPR_HLT = 1)"}]}
    HALTED_F = {"F": [{"value": "1", "when": "(RUN = 0 AND FP_START = 1)"}]}

    def setUp(self):
        patches = [mock.patch.object(P, "NON_EXECUTE_VARIANT", "IR_CLASS"),
                   mock.patch.object(P, "SEQ_A2", "IR_NO_EXECUTE"),
                   mock.patch.object(P, "SEQ_A1", "IR_OPR_HLT"),
                   mock.patch.object(P, "STATE_GROUP_RUN_MUX", True)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def documents(self):
        docs = documents(v2=True, fetch_extra=None)
        fetch = next(c for c in docs["symbolic"]["cases"] if c["execution_case_id"] == "fetch")
        fetch["field_assignments"] = {**fetch["field_assignments"], **self.SKIP_F}
        halted = next(c for c in docs["symbolic"]["cases"] if c["execution_case_id"] == "halted")
        halted["field_assignments"] = {**halted["field_assignments"], **self.HALTED_F}
        docs["inputs"]["fields"].append(make_input("SKIP"))
        return docs

    def pack(self):
        model, diagnostics = P.build_model(self.documents())
        self.assertEqual([d.code for d in diagnostics], [])
        packing, diagnostics = P.pack(model)
        self.assertEqual([d.code for d in diagnostics], [])
        return packing

    # -- units

    def test_state_group_faces(self):
        g = P.state_group(frozenset({"FP_CMD"}),
                          frozenset({"CIFP", "AUTO_INDEX_REQUIRED", "SKIP"}))
        self.assertEqual(g.running_bits, {"AUTO_INDEX_REQUIRED": 3, "CIFP": 4, "SKIP": 2})
        self.assertEqual(g.bits, {"FP_CMD": 0, "AUTO_INDEX_REQUIRED": 3, "CIFP": 4})
        self.assertEqual(g.face(True), g.bits)
        self.assertEqual(g.face(False), g.running_bits)

    def test_state_group_that_does_not_fit(self):
        six = frozenset({"A", "B", "C", "D", "E", "F"})
        self.assertIsNone(P.state_group(frozenset({"FP_CMD"}), six))
        self.assertIsNone(P.state_group(frozenset(), frozenset({"FP_CMD"})))

    def test_overlay_values_by_face(self):
        g = P.state_group(frozenset({"FP_CMD"}), frozenset({"SKIP"}))
        self.assertEqual(P.overlay_values(g, 0b00101, halted=True)["FP_CMD"], "5")
        self.assertEqual(P.overlay_values(g, 0b01000, halted=False), {"SKIP": "1"})   # bit 3

    def test_insert_group_renumbers(self):
        groups = [P.Group(0, ["A"], {"A": 0}), P.Group(1, ["B"], {"B": 0})]
        placement = {frozenset({"A"}): 0, frozenset({"B"}): 1, frozenset(): 0}
        state = P.Group(P.NON_EXECUTE_GROUP, ["SKIP"], {}, {"SKIP": 2})
        P.insert_group(groups, placement, state)
        self.assertEqual([g.code for g in groups], [0, 1, 2])
        self.assertIs(groups[1], state)
        self.assertEqual(placement, {frozenset({"A"}): 0, frozenset({"B"}): 2, frozenset(): 0})

    def test_a1_is_sequencer_address_bit_1(self):
        base = P.sequencer_address(0, 3, {}, False, "0", "0", "0")
        self.assertEqual(P.sequencer_address(0, 3, {}, False, "0", "0", "1") - base, 0b10)

    # -- packing

    def test_packs_and_verifies(self):
        packing = self.pack()
        state = packing.groups[P.NON_EXECUTE_GROUP]
        self.assertEqual(state.bits, {"FP_CMD": 0, "SKIP": 3})   # bit 3 is not multiplexed
        self.assertEqual(state.running_bits, {"SKIP": 3})       # first free unmultiplexed bit
        self.assertGreater(packing.checked, 0)

    def test_hlt_capture_reads_a1(self):
        packing = self.pack()
        fetch = packing.model.ms_codes["FETCH"]
        values = {"/DMA_REQ": "1"}

        def hlt_req_next(a1):
            word = packing.images["sequencer"][P.sequencer_address(fetch, 3, values, False,
                                                                   "0", "0", a1)]
            return P._seq_unpack(packing.model, word, "HLT_REQ_NEXT")
        self.assertEqual((hlt_req_next("0"), hlt_req_next("1")), (0, 1))

    def test_unreachable_a1_addresses_repeat_the_a1_0_word(self):
        # IR_OPR_HLT (IR[9]) with IR_INDIRECT (IR[8]) is a real IR value in this fixture, so use
        # FETCH TS1, whose word does not depend on IR: every A1 value must give the same word.
        packing = self.pack()
        fetch = packing.model.ms_codes["FETCH"]
        seq = packing.images["sequencer"]
        values = {"/DMA_REQ": "1"}
        for irseq in "01":
            for a2 in "01":
                words = {seq[P.sequencer_address(fetch, 1, values, False, irseq, a2, a1)]
                         for a1 in "01"}
                self.assertEqual(len(words), 1, (irseq, a2))

    def test_run_multiplexer_selects_the_face(self):
        packing = self.pack()
        state = packing.groups[P.NON_EXECUTE_GROUP]
        words = packing.images["_datapath_words"]
        fetch = packing.model.ms_codes["FETCH"]
        skip = 1 << state.running_bits["SKIP"]

        def f(ms_eff, ts, ovl):
            return P.unpack(packing, words[P.datapath_address(ms_eff, ts, 0, ovl)], "F")
        self.assertEqual((f(fetch, 4, 0), f(fetch, 4, skip)), (0, 1))
        self.assertEqual((f(P.HALTED_CODE, 1, 0), f(P.HALTED_CODE, 1, 1)), (0, 1))  # FP_START

    def test_hlt_capture_without_a1_is_an_error(self):
        with mock.patch.object(P, "SEQ_A1", None):
            model, _ = P.build_model(self.documents())
            _, diagnostics = P.pack(model)
        self.assertTrue({"NON_EXECUTE_IR_SEQ", "SEQUENCER_IR_DEPENDENCE"}
                        & {d.code for d in diagnostics})

    def test_json_describes_both_faces(self):
        data = P.packing_json(self.pack(), [])
        state = data["overlay_groups"][P.NON_EXECUTE_GROUP]
        self.assertEqual(state["bits"], [{"bit": 0, "signal": "FP_CMD", "width": 3},
                                         {"bit": 3, "signal": "SKIP", "width": 1}])
        self.assertEqual(state["running_bits"], [{"bit": 3, "signal": "SKIP", "width": 1}])
        self.assertEqual(data["sequencer_a1"], "IR_OPR_HLT")
        self.assertNotIn("running_bits", data["overlay_groups"][0])


if __name__ == "__main__":
    unittest.main()
