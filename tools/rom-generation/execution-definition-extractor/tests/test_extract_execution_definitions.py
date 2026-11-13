"""Tests for the execution-definition extractor."""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from extract_execution_definitions import (
    CONSOLE_SOURCE,
    DECODED_IOT_CONTEXTS,
    DEFAULT_JSON_OUTPUT,
    DEFAULT_REPORT_OUTPUT,
    DMA_SOURCE,
    FETCH_DEFER_SOURCE,
    INTERRUPT_SOURCE,
    IOT_SOURCE,
    MICRO_OPERATION_SOURCE,
    MRI_SOURCE,
    OPR_SOURCES,
    SOURCE_PATHS,
    Diagnostic,
    Document,
    ExtractionFailure,
    Findings,
    build_report,
    clean,
    extract_execution_definitions,
    main,
    make_case,
    micro_operation_catalog,
    normalize_context_term,
    parse_arguments,
    parse_console,
    parse_dma,
    parse_fetch_defer,
    parse_headings,
    parse_instructions,
    parse_interrupt,
    parse_opr,
    parse_phase_binding,
    read_source,
    resolve_from_repo,
    validate_cases,
)

PATH = "docs/example.md"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def code(*lines: str) -> str:
    return "```text\n" + "\n".join(lines) + "\n```\n"


def bullets(*items: str) -> str:
    return "".join(f"- {item}\n" for item in items) or "- (no μops)\n"


def timing_markers(**states: str) -> str:
    """``TSn:`` markers for TS1 to TS4; ``ts2="..."`` overrides a body."""

    return "".join(
        f"TS{n}:\n{states.get(f'ts{n}', bullets())}\n" for n in range(1, 5)
    )


def instruction(number: str, title: str, body: str | None = None) -> str:
    return f"### {number} {title}\n\n{body or timing_markers()}\n---\n\n"


def timing_headings(number: str, bodies: dict[int, str] | None = None) -> str:
    """``### n.k TSk`` headings, numbered from ``number``.1."""

    bodies = bodies or {}
    return "".join(
        f"### {number}.{n} TS{n}\n\n{bodies.get(n, '')}\n" for n in range(1, 5)
    )


def micro_operations(*items: str) -> str:
    return "μops:\n" + bullets(*items)


def conditional(*lines: str) -> str:
    return "Conditional μops:\n\n" + code(*lines)


def parse(parser, text: str, *arguments):
    """Run one parser on ``text``; return its cases and diagnostics."""

    findings = Findings(PATH)
    cases = parser(Document(PATH, text), *arguments, findings)
    return cases, findings.diagnostics


def codes(diagnostics) -> list[str]:
    return [diagnostic.code for diagnostic in diagnostics]


# ---------------------------------------------------------------------------
# Valid documents
# ---------------------------------------------------------------------------

FETCH_DEFER = (
    "# FETCH and DEFER\n\n"
    "## 3. FETCH Execution\n\n"
    + timing_headings(
        "3",
        {
            1: micro_operations("PC_TO_MA")
            + "\n"
            + conditional("CIFP = 0 -> II_CLEAR")
            + "\nDescription:\n- Places the address in MA.\n",
            2: micro_operations("MEM_READ_TO_MB"),
            3: micro_operations("MB_TO_IR"),
            4: micro_operations("PC_INC") + "\nControl Decisions:\n\n"
            "    if IR[INDIRECT] == 1:\n        MS_next ← DEFER\n",
        },
    )
    + "## 4. DEFER Execution\n\n"
    "### 4.1 Purpose\n\nResolves indirect addressing.\n\n"
    + timing_headings(
        "4.1",
        {
            1: micro_operations("EA_ADDR_TO_MA"),
            3: conditional("AUTO_INDEX_REQUIRED = 1 -> MB_INC"),
        },
    )
)

MRI = (
    "# MRI Execution\n\n"
    "## 3. Instruction Definitions\n\n"
    + instruction(
        "3.1",
        "IR[11:9] = 000",
        "**Mnemonic (non-normative):** AND\n\n"
        + timing_markers(
            ts1=bullets("EA_ADDR_TO_MA  "), ts3=bullets("`AC_AND_MB`")
        ),
    )
    + instruction(
        "3.6",
        "IR\\[11:9\\] = 101",
        timing_markers(
            ts4=conditional("IF_CHANGE_PENDING = 1 -> DIF_TO_IF"),
        ),
    )
    + "## 4. Summary\n\n- IR[11:9] selects behavior.\n"
)

DECODED_IOT_SECTIONS = "".join(
    instruction(f"10.{index}", title)
    for index, title in enumerate(DECODED_IOT_CONTEXTS, 1)
)

IOT = (
    "# IOT Execution\n\n"
    "## 7. External IOT Phase Binding\n\n"
    "- `IO_CLEAR_AC_REQ` selects `AC_CLEAR` during the TS in which the "
    "request is asserted.\n"
    "- `IO_SKIP_REQ` selects `PC_INC` during TS4.\n\n"
    "## 9. Instruction Definitions (CPU Control - Device 0)\n\n"
    + instruction(
        "9.3",
        "IR[11:9] = 110 AND IOA = 00 AND IR[2:0] = 000",
        "  TS1:\n- (no μops)\n\n"
        "TS2:\n- IE_CLEAR\n\n"
        + conditional("IE = 1 -> PC_INC")
        + "\n  TS3:\n- (no unconditional μops)\n\nTS4:\n- (no μops)\n\n"
        "Description:\n- Skips if interrupts are on.\n",
    )
    + "## 10. Instruction Definitions (Memory Extension Control)\n\n"
    + DECODED_IOT_SECTIONS
    + "## 11. Notes\n\n- None.\n"
)

INTERRUPT = (
    "# INTERRUPT Execution\n\n"
    "## 4. Execution Sequence\n\n"
    "### 4.1 TS1 — PC Capture\n  \n- PC_TO_MB  \n\nDescription:\n- Saves.\n\n"
    "### 4.2 TS2 — Address Formation\n\n- MA_CLEAR\n- IF_DF_TO_IB\n\n"
    "### 4.3 TS3\n\n- MEM_WRITE_FROM_MB\n\n"
    "### 4.4 TS4\n\n- PC_SET_1\n- IE_CLEAR\n\n"
    "## 7. Notes\n\n### 7.1 Device Interaction\n\n- None.\n"
)

CONSOLE = (
    "# Console Execution\n\n"
    "## 3. Console Operation Execution Model\n\nμops are not listed here.\n\n"
    "## 6. Load Address Operation\n\n"
    "Applicable context:\n\n" + code("RUN = 0", "FP_LOAD_ADDRESS = 1") + "\n"
    "Execution model:\n\n"
    + code("single TS-equivalent console transaction")
    + "\nμops:\n\n- CIFP_CLEAR\n- FP_SR_TO_PC\n\n\n"
    "Result:\n\n" + code("PC ← FP_SR") + "\n"
    "## 9. Clear Operation\n\nResult:\n- AC is cleared.\n\n"
)

OPR_GROUP1 = (
    "# Group 1 Execution\n\n"
    "## 2. Scope\n\nApplies when:\n\n"
    + code("IR_IS_OPR = 1", "IR_OPR_GROUP1 = 1")
    + "\n## 4. Instruction Definition\n\n"
    "### 4.1 IR[11:9] = 111 (Group 1)\n\n"
    "TS1:\n- if IR_OPR_CLA = 1: AC_CLEAR  \n- if IR_OPR_CLL = 1: L_CLEAR\n\n"
    "TS2:\n- (no μops)\n\n"
    "TS3:\n- if IR_OPR_IAC = 1: AC_INC\n\n"
    "TS4:\n- if IR_OPR_RAR = 1 AND IR_OPR_BSW = 0: AC_RAR\n\n"
    "## 5. Composition Rules\n\n"
    "- IR_OPR_RAR and IR_OPR_RAL must not both be 1\n"
)

OPR_GROUP2 = (
    "# Group 2 Execution\n\n"
    "## 2. Scope\n\nApplies when:\n\n"
    + code("IR_IS_OPR = 1", "IR_OPR_GROUP2 = 1")
    + "\n## 4. Instruction Definition\n\n"
    "### 4.1 IR[11:9] = 111 (Group 2)\n\n"
    "### 4.2 Sub-group selection\n\n- AND sub-group: IR[3] = 1\n\n"
    "### 4.3 TS1 — Skip Evaluation\n\n"
    + conditional("SKIP_TAKEN = 1 -> PC_INC")
    + "\nThe skip composition is defined elsewhere.\n\n"
    "### 4.4 TS2 — AC Modification\n\n- if IR_OPR_CLA = 1: AC_CLEAR\n\n"
    "### 4.5 TS3 — Control Operations\n\n"
    "- if IR_OPR_HLT = 1:\n  - HLT is a meta-instruction\n\n"
    "### 4.6 TS4\n\n- (no μops)\n\n"
    "## 5. Composition Rules\n\n### 5.1 Ordering\n- TS1 first\n"
)

OPR_GROUP3 = (
    "# Group 3 Execution\n\n"
    "## 2. Scope\n\nApplies when:\n\n"
    + code("IR_IS_OPR = 1", "IR_OPR_GROUP3 = 1")
    + "\n## 4. Instruction Definition\n\n"
    "### 4.2 TS1\n\n- if IR_OPR_CLA = 1: AC_CLEAR\n\n"
    "### 4.3 TS2\n\n"
    "- if IR_OPR_MQA = 1 AND IR_OPR_MQL = 1: AC_MQ_SWAP\n\n"
    "### 4.4 TS3\n\n- (no μops)\n\n### 4.5 TS4\n\n- (no μops)\n"
)

KNOWN_MICRO_OPERATIONS = [
    "AC_AND_MB",
    "AC_CLEAR",
    "AC_INC",
    "AC_MQ_SWAP",
    "AC_RAR",
    "CIFP_CLEAR",
    "DIF_TO_IF",
    "EA_ADDR_TO_MA",
    "FP_SR_TO_PC",
    "IE_CLEAR",
    "IF_DF_TO_IB",
    "II_CLEAR",
    "L_CLEAR",
    "MA_CLEAR",
    "MB_INC",
    "MB_TO_IR",
    "MEM_READ_TO_MB",
    "MEM_WRITE_FROM_MB",
    "PC_INC",
    "PC_SET_1",
    "PC_TO_MA",
    "PC_TO_MB",
]

MICRO_OPERATION_CATALOG = (
    "# Micro-Operations\n\n## 4. Categories\n\n### 4.1 Address Formation\n\n"
    "```text\n### NOT_A_HEADING\n```\n\n"
    + "".join(
        f"### {name}\n\nDefinition.\n\n" for name in KNOWN_MICRO_OPERATIONS
    )
)

DMA = (
    "# DMA Execution\n\n## 3. DMA Execution\n\n"
    + timing_headings(
        "3", {n: micro_operations("(no μops)") for n in range(1, 5)}
    )
    + "## 4. Halting Between DMA Cycles\n\n- prose\n"
)

VALID_DOCUMENTS = {
    FETCH_DEFER_SOURCE: FETCH_DEFER,
    DMA_SOURCE: DMA,
    MRI_SOURCE: MRI,
    IOT_SOURCE: IOT,
    INTERRUPT_SOURCE: INTERRUPT,
    CONSOLE_SOURCE: CONSOLE,
    OPR_SOURCES[1]: OPR_GROUP1,
    OPR_SOURCES[2]: OPR_GROUP2,
    OPR_SOURCES[3]: OPR_GROUP3,
    MICRO_OPERATION_SOURCE: MICRO_OPERATION_CATALOG,
}

# Every document breaks at least one expectation of its parser.
INVALID_DOCUMENTS = {
    FETCH_DEFER_SOURCE: "## 3. FETCH Execution\n\n"
    + timing_headings("3", {1: conditional("CIFP = 0")}).replace(
        "### 3.4 TS4", "### 3.4 TS3"
    ),
    MRI_SOURCE: "## 3. Instructions\n\n"
    + instruction("3.1", "IR[11:9] = 111", timing_markers(ts1="- NOPE\n"))
    + instruction("3.1", "IR[11:9] = 000", "TS1:\n- `bad uop`\n"),
    IOT_SOURCE: "## 7. External IOT Phase Binding\n\n"
    "- IO_SKIP_REQ selects PC_INC during TS4.\n",
    INTERRUPT_SOURCE: "# Nothing here\n",
    DMA_SOURCE: DMA.replace("3. DMA Execution", "3. Other"),
    CONSOLE_SOURCE: "## 6. Load Address Operation\n\n"
    "Execution model:\n\n" + code("multi-cycle") + "\nμops:\n- PC_INC\n",
    OPR_SOURCES[1]: OPR_GROUP1.replace(
        "IR_OPR_CLL = 1: L_CLEAR", "IR[6] = 1: L_CLEAR"
    ),
    OPR_SOURCES[2]: OPR_GROUP2.replace("Applies when:", "Scope:").replace(
        "- (no μops)", "- PC_INC"
    ),
    OPR_SOURCES[3]: "# Group 3\n",
    MICRO_OPERATION_SOURCE: MICRO_OPERATION_CATALOG,
}


# ---------------------------------------------------------------------------
# Arguments, paths, and reading
# ---------------------------------------------------------------------------


class ArgumentAndPathTests(unittest.TestCase):
    def test_default_outputs_are_used(self) -> None:
        options = parse_arguments(["--repo-root", "."])

        self.assertEqual(options.json_output, DEFAULT_JSON_OUTPUT)
        self.assertEqual(options.report_output, DEFAULT_REPORT_OUTPUT)

    def test_relative_path_is_resolved_from_repo_root(self) -> None:
        root = Path("repository").resolve()

        self.assertEqual(
            resolve_from_repo(root, Path("out/x.json")),
            root / "out" / "x.json",
        )

    def test_absolute_path_is_preserved(self) -> None:
        path = Path("elsewhere/x.json").resolve()

        self.assertEqual(resolve_from_repo(Path("repo"), path), path)


class ReadSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)

    def test_missing_source_fails(self) -> None:
        with self.assertRaisesRegex(ExtractionFailure, "does not exist"):
            read_source(self.directory / "missing.md")

    def test_invalid_utf8_fails(self) -> None:
        path = self.directory / "bad.md"
        path.write_bytes(b"\xff\xfe")

        with self.assertRaisesRegex(ExtractionFailure, "not valid UTF-8"):
            read_source(path)

    def test_unreadable_source_fails(self) -> None:
        with self.assertRaisesRegex(ExtractionFailure, "Unable to read"):
            read_source(self.directory)


# ---------------------------------------------------------------------------
# Markdown reading
# ---------------------------------------------------------------------------


class MarkdownTests(unittest.TestCase):
    def test_clean_removes_escapes_and_backticks(self) -> None:
        self.assertEqual(clean(" `IB\\_TO\\_DF` "), "IB_TO_DF")
        self.assertEqual(clean("IR\\[11:9\\]"), "IR[11:9]")

    def test_headings_are_numbered_cleaned_and_fence_aware(self) -> None:
        headings = parse_headings(
            [
                "# Title",
                "## 3. FETCH Execution",
                "```text",
                "### 9.9 Not a heading",
                "```",
                "### 3.1 IR\\[11:9\\] = 000",
                "#### Unnumbered",
            ]
        )

        self.assertEqual(
            [(h.level, h.number, h.title, h.line) for h in headings],
            [
                (2, "3", "FETCH Execution", 2),
                (3, "3.1", "IR[11:9] = 000", 6),
                (4, None, "Unnumbered", 7),
            ],
        )

    def test_catalog_reads_name_headings_only(self) -> None:
        catalog = micro_operation_catalog(
            Document(PATH, MICRO_OPERATION_CATALOG)
        )

        self.assertEqual(catalog, set(KNOWN_MICRO_OPERATIONS))


# ---------------------------------------------------------------------------
# FETCH and DEFER
# ---------------------------------------------------------------------------


class FetchDeferTests(unittest.TestCase):
    def test_cases(self) -> None:
        cases, diagnostics = parse(parse_fetch_defer, FETCH_DEFER)

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            [(c["id"], c["context"], c["timing_state"]) for c in cases],
            [
                ("fetch-defer:3.1", ["MS = FETCH"], 1),
                ("fetch-defer:3.2", ["MS = FETCH"], 2),
                ("fetch-defer:3.3", ["MS = FETCH"], 3),
                ("fetch-defer:3.4", ["MS = FETCH"], 4),
                ("fetch-defer:4.1.1", ["MS = DEFER"], 1),
                ("fetch-defer:4.1.2", ["MS = DEFER"], 2),
                ("fetch-defer:4.1.3", ["MS = DEFER"], 3),
                ("fetch-defer:4.1.4", ["MS = DEFER"], 4),
            ],
        )
        self.assertEqual(
            cases[0],
            make_case(
                "fetch-defer:3.1",
                PATH,
                5,
                ["MS = FETCH"],
                1,
                ["PC_TO_MA"],
                [{"predicate": "CIFP = 0", "micro_operation": "II_CLEAR"}],
            ),
        )
        self.assertEqual(cases[3]["micro_operations"], ["PC_INC"])
        self.assertEqual(cases[6]["micro_operations"], [])

    def test_missing_state_section_is_an_error(self) -> None:
        _, diagnostics = parse(
            parse_fetch_defer, FETCH_DEFER.replace("DEFER Execution", "Other")
        )

        self.assertEqual(codes(diagnostics), ["MISSING_SECTION"])
        self.assertIn("'DEFER Execution'", diagnostics[0].message)

    def test_missing_and_repeated_timing_states_are_errors(self) -> None:
        _, diagnostics = parse(
            parse_fetch_defer, FETCH_DEFER.replace("3.4 TS4", "3.4 TS3")
        )

        self.assertEqual(
            [(d.code, d.message) for d in diagnostics],
            [
                ("DUPLICATE_TIMING_STATE", "FETCH Execution has TS3 2 times."),
                ("MISSING_TIMING_STATE", "FETCH Execution has no TS4."),
            ],
        )


# ---------------------------------------------------------------------------
# MRI and IOT instructions
# ---------------------------------------------------------------------------


class InstructionTests(unittest.TestCase):
    def test_mri_cases(self) -> None:
        cases, diagnostics = parse(parse_instructions, MRI, "mri")

        self.assertEqual(diagnostics, [])
        self.assertEqual(len(cases), 8)
        self.assertEqual(
            cases[0],
            make_case(
                "mri:3.1:ts1",
                PATH,
                5,
                ["MS = EXECUTE", "IR_IS_MRI = 1", "IR_MRI_OPCODE = 000"],
                1,
                ["EA_ADDR_TO_MA"],
            ),
        )
        self.assertEqual(cases[2]["micro_operations"], ["AC_AND_MB"])
        self.assertEqual(
            cases[7]["conditional_micro_operations"],
            [
                {
                    "predicate": "IF_CHANGE_PENDING = 1",
                    "micro_operation": "DIF_TO_IF",
                }
            ],
        )
        self.assertEqual(cases[7]["micro_operations"], [])

    def test_iot_cases(self) -> None:
        cases, diagnostics = parse(parse_instructions, IOT, "iot")

        self.assertEqual(diagnostics, [])
        self.assertEqual(len(cases), 12)
        skon = cases[1]
        self.assertEqual(skon["id"], "iot:9.3:ts2")
        self.assertEqual(
            skon["context"],
            [
                "MS = EXECUTE",
                "IR_IS_IOT = 1",
                "IR_IOA = 000000",
                "IR_IOT_OP = 000",
            ],
        )
        self.assertEqual(skon["micro_operations"], ["IE_CLEAR"])
        self.assertEqual(
            skon["conditional_micro_operations"],
            [{"predicate": "IE = 1", "micro_operation": "PC_INC"}],
        )
        self.assertEqual(cases[2]["micro_operations"], [])

    def test_decoded_iot_contexts_replace_raw_bits(self) -> None:
        cases, _ = parse(parse_instructions, IOT, "iot")

        contexts = {
            case["id"].rsplit(":", 1)[0]: case["context"] for case in cases
        }
        for index, context in enumerate(DECODED_IOT_CONTEXTS.values(), 1):
            self.assertEqual(
                contexts[f"iot:10.{index}"], ["MS = EXECUTE", *context]
            )

    def test_context_terms(self) -> None:
        self.assertEqual(
            normalize_context_term("IR[11:9] = 011"), "IR_MRI_OPCODE = 011"
        )
        self.assertEqual(
            normalize_context_term("IR[11:9] = 110"), "IR_IS_IOT = 1"
        )
        self.assertEqual(
            normalize_context_term("IR[11:9] = 111"), "IR[11:9] = 111"
        )
        self.assertEqual(
            normalize_context_term("IR[2:0] = 101"), "IR_IOT_OP = 101"
        )
        self.assertEqual(normalize_context_term("IOA = 00"), "IR_IOA = 000000")
        self.assertEqual(normalize_context_term("IOA = 27"), "IR_IOA = 010111")
        self.assertEqual(normalize_context_term("IOA = 8"), "IOA = 8")
        self.assertEqual(normalize_context_term("RUN = 1"), "RUN = 1")

    def test_untranslated_heading_term_is_an_error(self) -> None:
        _, diagnostics = parse(
            parse_instructions,
            instruction("3.1", "IR[11:9] = 111 AND IR[8] = 1 AND IOA = 2n"),
            "mri",
        )

        self.assertEqual(
            [(d.code, d.message) for d in diagnostics],
            [
                (
                    "UNTRANSLATED_CONTEXT_TERM",
                    "Heading term 'IR[11:9] = 111' has no control-input form.",
                ),
                (
                    "UNTRANSLATED_CONTEXT_TERM",
                    "Heading term 'IR[8] = 1' has no control-input form.",
                ),
                (
                    "UNTRANSLATED_CONTEXT_TERM",
                    "Heading term 'IOA = 2n' has no control-input form.",
                ),
            ],
        )

    def test_changed_decoded_iot_heading_is_reported(self) -> None:
        title = next(iter(DECODED_IOT_CONTEXTS))
        _, diagnostics = parse(
            parse_instructions,
            IOT.replace(title, title + " AND IR[1] = 0"),
            "iot",
        )

        self.assertEqual(
            codes(diagnostics),
            [
                "UNTRANSLATED_CONTEXT_TERM",
                "MISSING_SECTION",
            ],
        )

    def test_missing_and_repeated_markers_are_errors(self) -> None:
        cases, diagnostics = parse(
            parse_instructions,
            instruction(
                "3.1", "IR[11:9] = 000", "TS1:\n- PC_INC\n\nTS1:\n- PC_INC\n"
            ),
            "mri",
        )

        self.assertEqual(len(cases), 2)
        self.assertEqual(
            codes(diagnostics),
            [
                "DUPLICATE_TIMING_STATE",
                "MISSING_TIMING_STATE",
                "MISSING_TIMING_STATE",
                "MISSING_TIMING_STATE",
            ],
        )
        self.assertEqual(
            diagnostics[0].message, "Section 3.1 has TS1 2 times."
        )

    def test_conditional_is_bounded_by_the_next_marker(self) -> None:
        cases, _ = parse(
            parse_instructions,
            instruction(
                "3.1",
                "IR[11:9] = 000",
                timing_markers(
                    ts3=bullets() + "\n" + conditional("A = 1 -> X")
                ),
            ),
            "mri",
        )

        self.assertEqual(
            [len(case["conditional_micro_operations"]) for case in cases],
            [0, 0, 1, 0],
        )

    def test_conditional_needs_a_code_block(self) -> None:
        cases, diagnostics = parse(
            parse_instructions,
            instruction(
                "3.1",
                "IR[11:9] = 000",
                timing_markers(ts1="Conditional μops:\n\n- A = 1 -> X\n"),
            ),
            "mri",
        )

        self.assertEqual(codes(diagnostics), ["MISSING_CODE_BLOCK"])
        self.assertEqual(diagnostics[0].case_id, "mri:3.1:ts1")
        self.assertEqual(diagnostics[0].line, 4)
        self.assertEqual(cases[0]["conditional_micro_operations"], [])

    def test_malformed_conditional_is_an_error(self) -> None:
        _, diagnostics = parse(
            parse_instructions,
            instruction(
                "3.1",
                "IR[11:9] = 000",
                timing_markers(ts1=conditional("A = 1 -> X", "A = 1 => Y")),
            ),
            "mri",
        )

        self.assertEqual(codes(diagnostics), ["MALFORMED_CONDITIONAL"])
        self.assertEqual(diagnostics[0].line, 8)
        self.assertIn("'A = 1 => Y'", diagnostics[0].message)

    def test_unnumbered_and_non_ir_headings_are_ignored(self) -> None:
        cases, _ = parse(
            parse_instructions,
            instruction("3.1", "Overview")
            + "### IR[11:9] = 000\n\nTS1:\n- PC_INC\n",
            "mri",
        )

        self.assertEqual(cases, [])


class PhaseBindingTests(unittest.TestCase):
    def test_cases(self) -> None:
        cases, diagnostics = parse(parse_phase_binding, IOT)

        self.assertEqual(diagnostics, [])
        clear = {
            "predicate": "IO_CLEAR_AC_REQ = 1",
            "micro_operation": "AC_CLEAR",
        }
        skip = {"predicate": "IO_SKIP_REQ = 1", "micro_operation": "PC_INC"}
        self.assertEqual(
            cases,
            [
                make_case(
                    f"iot:external:ts{n}",
                    PATH,
                    3,
                    ["MS = EXECUTE", "IR_IS_EXTERNAL_IOT = 1"],
                    n,
                    conditional=[clear, skip] if n == 4 else [clear],
                )
                for n in range(1, 5)
            ],
        )

    def test_missing_section_is_an_error(self) -> None:
        cases, diagnostics = parse(parse_phase_binding, MRI)

        self.assertEqual(cases, [])
        self.assertEqual(codes(diagnostics), ["MISSING_SECTION"])

    def test_changed_sentence_drops_cases_loudly(self) -> None:
        cases, diagnostics = parse(
            parse_phase_binding, IOT.replace("during TS4", "during TS3")
        )

        self.assertEqual(cases, [])
        self.assertEqual(codes(diagnostics), ["MISSING_PHASE_BINDING"])
        self.assertIn("IO_SKIP_REQ", diagnostics[0].message)


# ---------------------------------------------------------------------------
# INTERRUPT and console
# ---------------------------------------------------------------------------


class InterruptTests(unittest.TestCase):
    def test_cases(self) -> None:
        cases, diagnostics = parse(parse_interrupt, INTERRUPT)

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            [
                (c["id"], c["timing_state"], c["micro_operations"])
                for c in cases
            ],
            [
                ("interrupt:4.1", 1, ["PC_TO_MB"]),
                ("interrupt:4.2", 2, ["MA_CLEAR", "IF_DF_TO_IB"]),
                ("interrupt:4.3", 3, ["MEM_WRITE_FROM_MB"]),
                ("interrupt:4.4", 4, ["PC_SET_1", "IE_CLEAR"]),
            ],
        )
        self.assertTrue(all(c["context"] == ["MS = INTERRUPT"] for c in cases))

    def test_missing_timing_state_is_an_error(self) -> None:
        _, diagnostics = parse(
            parse_interrupt, INTERRUPT.replace("### 4.3 TS3", "### 4.3 Save")
        )

        self.assertEqual(codes(diagnostics), ["MISSING_TIMING_STATE"])
        self.assertEqual(diagnostics[0].message, "INTERRUPT has no TS3.")


class ConsoleTests(unittest.TestCase):
    def test_cases(self) -> None:
        cases, diagnostics = parse(parse_console, CONSOLE)

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            cases,
            [
                make_case(
                    "console:6",
                    PATH,
                    7,
                    ["RUN = 0", "FP_LOAD_ADDRESS = 1"],
                    None,
                    ["CIFP_CLEAR", "FP_SR_TO_PC"],
                    execution_model="console-transaction",
                )
            ],
        )

    def test_operation_needs_context_and_execution_model(self) -> None:
        _, diagnostics = parse(
            parse_console,
            "## 6. Load Address Operation\n\n"
            "Applicable context:\n\nRUN = 0\n\nμops:\n- PC_INC\n",
        )

        self.assertEqual(
            codes(diagnostics),
            ["MISSING_CONTEXT", "UNEXPECTED_EXECUTION_MODEL"],
        )

    def test_other_execution_model_is_an_error(self) -> None:
        _, diagnostics = parse(
            parse_console,
            CONSOLE.replace("single TS-equivalent", "multi-TS"),
        )

        self.assertEqual(codes(diagnostics), ["UNEXPECTED_EXECUTION_MODEL"])
        self.assertEqual(diagnostics[0].case_id, "console:6")


# ---------------------------------------------------------------------------
# OPR
# ---------------------------------------------------------------------------


class DmaTests(unittest.TestCase):
    def test_dma_cases(self) -> None:
        cases, diagnostics = parse(parse_dma, DMA)

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            [
                (c["id"], c["context"], c["timing_state"], c["micro_operations"])
                for c in cases
            ],
            [(f"dma:3.{n}", ["MS = DMA"], n, []) for n in range(1, 5)],
        )

    def test_missing_dma_section_is_an_error(self) -> None:
        cases, diagnostics = parse(parse_dma, "# DMA Execution\n")

        self.assertEqual(cases, [])
        self.assertEqual(codes(diagnostics), ["MISSING_SECTION"])


class OprTests(unittest.TestCase):
    def test_group1_cases(self) -> None:
        cases, diagnostics = parse(parse_opr, OPR_GROUP1, 1)

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            [(c["id"], c["source"]["line"]) for c in cases],
            [
                ("opr1:ts1", 16),
                ("opr1:ts2", 20),
                ("opr1:ts3", 23),
                ("opr1:ts4", 26),
            ],
        )
        self.assertEqual(
            cases[0]["context"],
            ["MS = EXECUTE", "IR_IS_OPR = 1", "IR_OPR_GROUP1 = 1"],
        )
        self.assertEqual(
            cases[0]["conditional_micro_operations"],
            [
                {"predicate": "IR_OPR_CLA = 1", "micro_operation": "AC_CLEAR"},
                {"predicate": "IR_OPR_CLL = 1", "micro_operation": "L_CLEAR"},
            ],
        )
        self.assertEqual(cases[1]["conditional_micro_operations"], [])
        self.assertEqual(
            cases[3]["conditional_micro_operations"][0]["predicate"],
            "IR_OPR_RAR = 1 AND IR_OPR_BSW = 0",
        )

    def test_group2_reads_headings_blocks_and_control_bullets(self) -> None:
        cases, diagnostics = parse(parse_opr, OPR_GROUP2, 2)

        self.assertEqual(diagnostics, [])
        self.assertEqual(
            [(c["id"], c["conditional_micro_operations"]) for c in cases],
            [
                (
                    "opr2:ts1",
                    [
                        {
                            "predicate": "SKIP_TAKEN = 1",
                            "micro_operation": "PC_INC",
                        }
                    ],
                ),
                (
                    "opr2:ts2",
                    [
                        {
                            "predicate": "IR_OPR_CLA = 1",
                            "micro_operation": "AC_CLEAR",
                        }
                    ],
                ),
                ("opr2:ts3", []),
                ("opr2:ts4", []),
            ],
        )

    def test_non_timing_heading_ends_a_timing_state(self) -> None:
        cases, diagnostics = parse(
            parse_opr,
            OPR_GROUP3.replace(
                "### 4.4 TS3", "### 4.35 Notes\n\n- anything\n\n### 4.4 TS3"
            ),
            3,
        )

        self.assertEqual(diagnostics, [])
        self.assertEqual(len(cases), 4)

    def test_raw_ir_bits_are_errors(self) -> None:
        cases, diagnostics = parse(
            parse_opr,
            OPR_GROUP3.replace("IR_OPR_CLA = 1", "IR[bit(CLA)] = 1"),
            3,
        )

        self.assertEqual(codes(diagnostics), ["RAW_IR_BIT"])
        self.assertEqual(diagnostics[0].case_id, "opr3:ts1")
        self.assertEqual(len(cases), 4)

    def test_unrecognized_bullet_is_an_error(self) -> None:
        _, diagnostics = parse(
            parse_opr, OPR_GROUP3.replace("- (no μops)", "- AC_CLEAR", 1), 3
        )

        self.assertEqual(codes(diagnostics), ["UNRECOGNIZED_OPR_LINE"])
        self.assertEqual(diagnostics[0].case_id, "opr3:ts3")

    def test_missing_scope_and_sections_are_errors(self) -> None:
        cases, diagnostics = parse(parse_opr, "# Group 3\n", 3)

        self.assertEqual(cases, [])
        self.assertEqual(
            codes(diagnostics), ["MISSING_CONTEXT", "MISSING_SECTION"]
        )

    def test_missing_timing_state_is_an_error(self) -> None:
        _, diagnostics = parse(
            parse_opr, OPR_GROUP3.replace("### 4.5 TS4", "### 4.5 Notes"), 3
        )

        self.assertEqual(codes(diagnostics), ["MISSING_TIMING_STATE"])


# ---------------------------------------------------------------------------
# Validation and extraction
# ---------------------------------------------------------------------------


class ValidationTests(unittest.TestCase):
    def test_duplicate_case_id_is_reported_on_the_repeat(self) -> None:
        case = make_case("x", PATH, 3, [], 1)

        diagnostics = validate_cases([case, case], set())

        self.assertEqual(
            diagnostics,
            [
                Diagnostic(
                    "ERROR",
                    "DUPLICATE_CASE_ID",
                    "Duplicate case id: x",
                    PATH,
                    3,
                    "x",
                )
            ],
        )

    def test_micro_operations_must_be_known_names(self) -> None:
        case = make_case(
            "x",
            PATH,
            3,
            [],
            1,
            ["bad uop", "NOPE"],
            [{"predicate": "A = 1", "micro_operation": "MISSING"}],
        )

        diagnostics = validate_cases([case], {"PC_INC"})

        self.assertEqual(
            codes(diagnostics),
            [
                "MALFORMED_MICRO_OPERATION",
                "UNKNOWN_MICRO_OPERATION",
                "UNKNOWN_MICRO_OPERATION",
            ],
        )

    def test_parser_without_cases_or_findings_is_an_error(self) -> None:
        documents = dict(VALID_DOCUMENTS)
        documents[CONSOLE_SOURCE] = "# Console\n"

        _, diagnostics = extract_execution_definitions(documents)

        self.assertEqual(
            [(d.code, d.source_path) for d in diagnostics],
            [("NO_CASES_FOUND", CONSOLE_SOURCE.as_posix())],
        )

    def test_valid_documents_extract_in_order(self) -> None:
        cases, diagnostics = extract_execution_definitions(VALID_DOCUMENTS)

        self.assertEqual(diagnostics, [])
        prefixes = []
        for case in cases:
            prefix = case["id"].split(":")[0]
            if prefix not in prefixes:
                prefixes.append(prefix)
        self.assertEqual(
            prefixes,
            [
                "fetch-defer",
                "mri",
                "iot",
                "interrupt",
                "dma",
                "console",
                "opr1",
                "opr2",
                "opr3",
            ],
        )
        iot = [case["id"] for case in cases if case["id"].startswith("iot:")]
        self.assertEqual(
            iot[:5],
            [*(f"iot:external:ts{n}" for n in range(1, 5)), "iot:9.3:ts1"],
        )


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


class OutputTests(unittest.TestCase):
    def test_report(self) -> None:
        diagnostics = [
            Diagnostic("ERROR", "A", "First.", PATH, 3, "x:1"),
            Diagnostic("FATAL", "B", "Second.", "<input>"),
        ]

        self.assertEqual(
            build_report(diagnostics, 2),
            "Execution-Definition Extraction Report\n"
            "======================================\n\n"
            "Cases extracted: 2\n"
            "Information diagnostics: 0\n"
            "Warnings: 0\n"
            "Errors: 1\n"
            "Fatal errors: 1\n\n"
            "Diagnostics\n"
            "-----------\n"
            f"ERROR A [x:1] {PATH}:3: First.\n"
            "FATAL B <input>: Second.\n",
        )

    def test_empty_report_says_no_diagnostics(self) -> None:
        self.assertTrue(build_report([], 0).endswith("No diagnostics.\n"))


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

GOLDEN_DIRECTORY = Path(__file__).resolve().parent / "golden"
UPDATE_GOLDEN = os.environ.get("UPDATE_GOLDEN") == "1"


class EndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.json_output = self.root / DEFAULT_JSON_OUTPUT
        self.report_output = self.root / DEFAULT_REPORT_OUTPUT

    def write_sources(self, documents) -> None:
        for path, text in documents.items():
            source = self.root / path
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text(text, encoding="utf-8")

    def run_main(self, *extra: str) -> tuple[int, str]:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--repo-root", str(self.root), *extra])
        return exit_code, stdout.getvalue()

    def assert_outputs_match_golden(self, name: str) -> None:
        """Compare the JSON and report against ``golden/<name>/``.

        Run with ``UPDATE_GOLDEN=1`` to rewrite the expected files after an
        intended output change, then review the diff.
        """

        outputs = {
            "execution-definitions.json": self.json_output,
            "extraction-report.txt": self.report_output,
        }
        for file_name, output in outputs.items():
            with self.subTest(file=file_name):
                actual = output.read_bytes().decode("utf-8")
                golden_path = GOLDEN_DIRECTORY / name / file_name
                if UPDATE_GOLDEN:
                    golden_path.parent.mkdir(parents=True, exist_ok=True)
                    golden_path.write_text(
                        actual, encoding="utf-8", newline="\n"
                    )
                self.assertEqual(
                    actual, golden_path.read_text(encoding="utf-8")
                )

    def test_valid_outputs_match_golden(self) -> None:
        self.write_sources(VALID_DOCUMENTS)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 0)
        self.assertIn("Cases: 53", stdout)
        self.assert_outputs_match_golden("valid")

    def test_invalid_outputs_match_golden(self) -> None:
        self.write_sources(INVALID_DOCUMENTS)

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertIn(
            "ERROR DUPLICATE_CASE_ID [mri:3.1:ts1]\n"
            f"  Source: {MRI_SOURCE.as_posix()}:",
            stdout,
        )
        self.assert_outputs_match_golden("invalid")

    def test_missing_source_is_fatal_and_removes_earlier_json(self) -> None:
        documents = dict(VALID_DOCUMENTS)
        del documents[MICRO_OPERATION_SOURCE]
        self.write_sources(documents)
        self.json_output.parent.mkdir(parents=True)
        self.json_output.write_text("stale\n", encoding="utf-8")

        exit_code, stdout = self.run_main()

        self.assertEqual(exit_code, 1)
        self.assertFalse(self.json_output.exists())
        report = self.report_output.read_text(encoding="utf-8")
        self.assertIn("Cases extracted: 0", report)
        self.assertIn(
            "FATAL EXTRACTION_FAILURE <input>: Required source does not exist",
            report,
        )
        self.assertIn("Cases: 0", stdout)

    def test_output_that_is_an_input_is_refused(self) -> None:
        self.write_sources(VALID_DOCUMENTS)

        exit_code, stdout = self.run_main("--report-output", str(MRI_SOURCE))

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is also an input", stdout)
        self.assertEqual(
            (self.root / MRI_SOURCE).read_text(encoding="utf-8"), MRI
        )

    def test_output_that_is_a_directory_is_refused(self) -> None:
        self.write_sources(VALID_DOCUMENTS)
        self.report_output.parent.mkdir(parents=True)
        self.report_output.write_text("earlier\n", encoding="utf-8")
        (self.root / "dir").mkdir()

        exit_code, stdout = self.run_main("--json-output", "dir")

        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: Output path is a directory", stdout)
        self.assertTrue(self.report_output.exists())

    def test_every_source_is_read(self) -> None:
        self.assertEqual(set(VALID_DOCUMENTS), set(SOURCE_PATHS))


if __name__ == "__main__":
    unittest.main()
