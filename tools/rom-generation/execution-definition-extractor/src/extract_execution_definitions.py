"""Extract execution definitions from the microarchitecture documentation.

The extractor reads the execution documents and produces deterministic
JSON plus a human-readable report. Each output case is one major state and
timing state (or one console transaction) with the micro-operations it
selects, unconditionally and under documented predicates.

Pipeline:

1. Read the execution documents and the micro-operation catalog.
2. Parse each document with the parser for its layout: FETCH/DEFER timing
   states, MRI and IOT instruction sections, the external-IOT phase
   binding, INTERRUPT timing states, console operations, and the three OPR
   groups.
3. Report every place a document does not have the structure its parser
   expects, so a documentation change never silently drops a case.
4. Check case ids and micro-operation names.
5. Write the JSON result and the extraction report.

See the tool README for the document conventions and output format.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

MICROARCHITECTURE = Path("docs/03-microarchitecture")
FETCH_DEFER_SOURCE = MICROARCHITECTURE / "04-fetch-defer.md"
MRI_SOURCE = MICROARCHITECTURE / "05-mri-execution.md"
IOT_SOURCE = MICROARCHITECTURE / "06-iot-execution.md"
INTERRUPT_SOURCE = MICROARCHITECTURE / "08-interrupt-execution.md"
CONSOLE_SOURCE = MICROARCHITECTURE / "09-console-execution.md"
OPR_SOURCES = {
    1: MICROARCHITECTURE / "07-opr/01-group1-execution.md",
    2: MICROARCHITECTURE / "07-opr/02-group2-execution.md",
    3: MICROARCHITECTURE / "07-opr/03-group3-execution.md",
}
MICRO_OPERATION_SOURCE = MICROARCHITECTURE / "02-micro-operations.md"

SOURCE_PATHS = (
    FETCH_DEFER_SOURCE,
    MRI_SOURCE,
    IOT_SOURCE,
    INTERRUPT_SOURCE,
    CONSOLE_SOURCE,
    *OPR_SOURCES.values(),
    MICRO_OPERATION_SOURCE,
)

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/execution-definition-extractor"
)
DEFAULT_JSON_OUTPUT = OUTPUT_DIRECTORY / "execution-definitions.json"
DEFAULT_REPORT_OUTPUT = OUTPUT_DIRECTORY / "extraction-report.txt"

# ---------------------------------------------------------------------------
# Output format
# ---------------------------------------------------------------------------

FORMAT_VERSION = 1
CONTROL_DESIGN_VERSION = "v1"
ARTIFACT = "execution-definitions"
EXTRACTION_STAGE = "documentation-extraction"

MAJOR_STATE_MODEL = "major-state"
CONSOLE_MODEL = "console-transaction"

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

INFO = "INFO"
WARNING = "WARNING"
ERROR = "ERROR"
FATAL = "FATAL"

SEVERITIES = (INFO, WARNING, ERROR, FATAL)
SEVERITY_ORDER = {severity: rank for rank, severity in enumerate(SEVERITIES)}
FAILURE_SEVERITIES = frozenset({ERROR, FATAL})

# ---------------------------------------------------------------------------
# Document structure
# ---------------------------------------------------------------------------

TIMING_STATES = (1, 2, 3, 4)

MICRO_OPERATIONS_LABEL = "μops:"
CONDITIONAL_LABEL = "Conditional μops:"
CONTEXT_LABEL = "Applicable context:"
EXECUTION_MODEL_LABEL = "Execution model:"
SCOPE_LABEL = "Applies when:"

# Bullets that stand for "nothing here" rather than a micro-operation.
PLACEHOLDERS = frozenset({"(no μops)", "(no unconditional μops)"})

# FETCH/DEFER: level-2 section title -> major state.
FETCH_DEFER_SECTIONS = {
    "FETCH Execution": "FETCH",
    "DEFER Execution": "DEFER",
}

# MRI/IOT instruction headings are ``IR[...] = ... AND ...`` conditions.
# These rewrite heading terms as control inputs.
MRI_OPCODES = frozenset({"000", "001", "010", "011", "100", "101"})
IOT_OPCODE = "110"

# Memory-extension IOT headings select on raw IR bits that have decoded
# control inputs. Keyed by the full heading title, so a changed heading is
# reported instead of silently matched.
DECODED_IOT_CONTEXTS = {
    "IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2] = 0 AND IR[0] = 1": (
        "IR_IS_IOT = 1",
        "IR_WRITES_DF = 1",
    ),
    "IR[11:9] = 110 AND IOA = 2n AND IR[2] = 0 AND IR[1] = 1": (
        "IR_IS_IOT = 1",
        "IR_WRITES_IF = 1",
    ),
    "IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 001": (
        "IR_IS_IOT = 1",
        "IR_READS_DF = 1",
    ),
    "IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 010": (
        "IR_IS_IOT = 1",
        "IR_READS_IF = 1",
    ),
    "IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 011": (
        "IR_IS_IOT = 1",
        "IR_READS_IB = 1",
    ),
    "IR[11:9] = 110 AND IR[8:6] = 010 AND IR[2:0] = 100 AND IR[5:3] = 100": (
        "IR_IS_IOT = 1",
        "IR_RESTORES_IB = 1",
    ),
}

# External-IOT phase binding: the section title, the context of its cases,
# and the two documented bindings, each with the timing states it applies
# to and the conditional micro-operation it selects.
PHASE_BINDING_SECTION = "External IOT Phase Binding"
PHASE_BINDING_CONTEXT = ("MS = EXECUTE", "IOT_ACTIVE = 1")
PHASE_BINDINGS = (
    (
        (
            "- IO_CLEAR_AC_REQ selects AC_CLEAR during the TS in which the "
            "request is asserted."
        ),
        TIMING_STATES,
        {"predicate": "IO_CLEAR_AC_REQ = 1", "micro_operation": "AC_CLEAR"},
    ),
    (
        "- IO_SKIP_REQ selects PC_INC during TS4.",
        (4,),
        {"predicate": "IO_SKIP_REQ = 1", "micro_operation": "PC_INC"},
    ),
)

# Console operations are single transactions with no timing state.
CONSOLE_EXECUTION_MODEL = "single TS-equivalent console transaction"

# OPR: the section holding the per-TS operation bullets.
OPR_DEFINITION_SECTION = "Instruction Definition"

# ---------------------------------------------------------------------------
# Markdown syntax
# ---------------------------------------------------------------------------

HEADING_PATTERN = re.compile(r"^(#{2,6})\s+(.+?)\s*$")
NUMBERED_TITLE_PATTERN = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(.+?)\s*$")
CODE_FENCE = "```"
TS_TITLE_PATTERN = re.compile(r"^TS([1-4])\b")
TS_MARKER_PATTERN = re.compile(r"^TS([1-4]):$")
BULLET_PATTERN = re.compile(r"^\s*-\s+(.+?)\s*$")
TOP_LEVEL_BULLET_PATTERN = re.compile(r"^-\s+(.+?)\s*$")
CONDITIONAL_PATTERN = re.compile(r"^(\S.*?)\s*->\s*([A-Z][A-Z0-9_]*)$")
OPR_CONDITIONAL_PATTERN = re.compile(r"^if\s+(\S.*?):\s*([A-Z][A-Z0-9_]*)?$")
CONSOLE_TITLE_PATTERN = re.compile(r"^(.+) Operation$")
MRI_OPCODE_TERM = re.compile(r"IR\[11:9\] = ([01]{3})")
IOT_OPERATION_TERM = re.compile(r"IR\[2:0\] = ([01]{3})")
# Device addresses are written in octal in the documentation; IR_IOA is the
# 6-bit binary IR[8:3].
IOA_PREFIX = "IOA = "
IOA_TERM = re.compile(r"IOA = ([0-7]{2})")
IOA_WIDTH = 6
RAW_IR_REFERENCES = ("IR[", "bit(")
MICRO_OPERATION_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Diagnostic:
    """One extraction finding. Field order is the JSON key order."""

    severity: str
    code: str
    message: str
    source_path: str
    line: int | None = None
    case_id: str | None = None


@dataclass(frozen=True)
class Heading:
    """One Markdown heading; ``number`` is None for unnumbered headings."""

    level: int
    number: str | None
    title: str
    line: int


@dataclass(frozen=True)
class Block:
    """Consecutive document lines; ``start`` is the first line's number."""

    start: int
    lines: tuple[str, ...]

    def line_number(self, index: int) -> int:
        return self.start + index


class Document:
    """One source document: its path, lines, and headings."""

    def __init__(self, path: str, text: str) -> None:
        self.path = path
        self.lines = tuple(text.splitlines())
        self.headings = parse_headings(self.lines)

    def body(self, heading: Heading) -> Block:
        """Return the lines after a heading, up to the next heading at or
        above its level."""

        end = len(self.lines) + 1
        for later in self.headings:
            if later.line > heading.line and later.level <= heading.level:
                end = later.line
                break
        return Block(heading.line + 1, self.lines[heading.line : end - 1])

    def section(self, level: int, title: str) -> Heading | None:
        """Return the first heading with this level and title."""

        for heading in self.headings:
            if heading.level == level and heading.title == title:
                return heading
        return None

    def children(self, parent: Heading, level: int) -> list[Heading]:
        """Return the headings of ``level`` within ``parent``'s body."""

        body = self.body(parent)
        last = body.start + len(body.lines)
        return [
            heading
            for heading in self.headings
            if heading.level == level and body.start <= heading.line < last
        ]


class ExtractionFailure(Exception):
    """A source document could not be read."""


class Findings:
    """Collects the diagnostics for one document."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.diagnostics: list[Diagnostic] = []

    def error(
        self,
        code: str,
        message: str,
        line: int | None = None,
        case_id: str | None = None,
    ) -> None:
        self.diagnostics.append(
            Diagnostic(ERROR, code, message, self.path, line, case_id)
        )


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.source_path,
        diagnostic.line if diagnostic.line is not None else -1,
        diagnostic.case_id or "",
        diagnostic.message,
    )


def make_case(
    case_id: str,
    path: str,
    line: int,
    context: Sequence[str],
    timing_state: int | None,
    micro_operations: Sequence[str] = (),
    conditional: Sequence[dict[str, str]] = (),
    execution_model: str = MAJOR_STATE_MODEL,
) -> dict[str, Any]:
    """Build one case. Key order is the format."""

    return {
        "id": case_id,
        "source": {"path": path, "line": line},
        "execution_model": execution_model,
        "context": list(context),
        "timing_state": timing_state,
        "micro_operations": list(micro_operations),
        "conditional_micro_operations": [dict(item) for item in conditional],
    }


# ---------------------------------------------------------------------------
# Markdown reading
# ---------------------------------------------------------------------------


def clean(text: str) -> str:
    """Remove Markdown escapes and surrounding backticks and whitespace."""

    return (
        text.replace("\\_", "_")
        .replace("\\[", "[")
        .replace("\\]", "]")
        .strip()
        .strip("`")
        .strip()
    )


def parse_headings(lines: Sequence[str]) -> list[Heading]:
    """Return the level 2 to 6 headings outside code blocks."""

    headings = []
    in_code_block = False

    for line_number, line in enumerate(lines, 1):
        if line.startswith(CODE_FENCE):
            in_code_block = not in_code_block
            continue
        match = None if in_code_block else HEADING_PATTERN.match(line)
        if match is None:
            continue
        title = clean(match.group(2))
        numbered = NUMBERED_TITLE_PATTERN.match(title)
        headings.append(
            Heading(
                level=len(match.group(1)),
                number=numbered.group(1) if numbered else None,
                title=numbered.group(2) if numbered else title,
                line=line_number,
            )
        )

    return headings


def label_indexes(block: Block, label: str) -> list[int]:
    """Return the indexes of the lines that are exactly ``label``."""

    return [
        index
        for index, line in enumerate(block.lines)
        if line.strip() == label
    ]


def code_block_after(
    block: Block, index: int
) -> tuple[list[tuple[int, str]], bool]:
    """Return the non-blank lines of the code block after line ``index``,
    each with its line number, and whether a code block was found."""

    fence = index + 1
    while fence < len(block.lines) and not block.lines[fence].strip():
        fence += 1
    lines = block.lines
    if fence >= len(lines) or not lines[fence].strip().startswith(CODE_FENCE):
        return [], False

    values = []
    for position in range(fence + 1, len(block.lines)):
        line = block.lines[position].strip()
        if line.startswith(CODE_FENCE):
            break
        if line:
            values.append((block.line_number(position), clean(line)))
    return values, True


def bullets_after(block: Block, index: int) -> list[str]:
    """Return the bullets following line ``index``, without placeholders.

    Blank lines are skipped; any other non-bullet line ends the list.
    """

    items = []
    for line in block.lines[index + 1 :]:
        if not line.strip():
            continue
        match = BULLET_PATTERN.match(line)
        if match is None:
            break
        item = clean(match.group(1))
        if item not in PLACEHOLDERS:
            items.append(item)
    return items


def labeled_bullets(block: Block, label: str) -> list[str]:
    """Return the bullets after every occurrence of ``label``."""

    return [
        item
        for index in label_indexes(block, label)
        for item in bullets_after(block, index)
    ]


def conditionals_after(
    block: Block, index: int, findings: Findings, case_id: str
) -> list[dict[str, str]]:
    """Read the ``predicate -> MICRO_OPERATION`` code block after a
    ``Conditional μops:`` label."""

    values, found = code_block_after(block, index)
    if not found:
        findings.error(
            "MISSING_CODE_BLOCK",
            f"'{CONDITIONAL_LABEL}' must be followed by a text code block.",
            block.line_number(index),
            case_id,
        )

    conditional = []
    for line_number, value in values:
        match = CONDITIONAL_PATTERN.match(value)
        if match is None:
            findings.error(
                "MALFORMED_CONDITIONAL",
                f"Expected 'predicate -> MICRO_OPERATION': {value!r}",
                line_number,
                case_id,
            )
            continue
        conditional.append(
            {"predicate": match.group(1), "micro_operation": match.group(2)}
        )
    return conditional


def labeled_conditionals(
    block: Block, findings: Findings, case_id: str
) -> list[dict[str, str]]:
    """Return the conditionals after every ``Conditional μops:`` label."""

    return [
        item
        for index in label_indexes(block, CONDITIONAL_LABEL)
        for item in conditionals_after(block, index, findings, case_id)
    ]


def check_timing_states(
    found: Sequence[int], where: str, line: int | None, findings: Findings
) -> None:
    """Report each of TS1 to TS4 that ``found`` lacks or repeats."""

    for timing_state in TIMING_STATES:
        count = found.count(timing_state)
        if count == 0:
            findings.error(
                "MISSING_TIMING_STATE",
                f"{where} has no TS{timing_state}.",
                line,
            )
        elif count > 1:
            findings.error(
                "DUPLICATE_TIMING_STATE",
                f"{where} has TS{timing_state} {count} times.",
                line,
            )


def missing_section(findings: Findings, title: str) -> None:
    findings.error("MISSING_SECTION", f"No '{title}' section found.")


# ---------------------------------------------------------------------------
# FETCH and DEFER
# ---------------------------------------------------------------------------


def parse_fetch_defer(document: Document, findings: Findings) -> list[dict]:
    """One case per timing-state heading in the FETCH and DEFER sections.

    Each case's μops and conditional μops follow their labels.
    """

    cases = []
    for title, state in FETCH_DEFER_SECTIONS.items():
        section = document.section(2, title)
        if section is None:
            missing_section(findings, title)
            continue

        found = []
        for heading in document.children(section, 3):
            match = TS_TITLE_PATTERN.match(heading.title)
            if match is None:
                continue
            timing_state = int(match.group(1))
            found.append(timing_state)
            case_id = f"fetch-defer:{heading.number}"
            body = document.body(heading)
            cases.append(
                make_case(
                    case_id,
                    document.path,
                    heading.line,
                    [f"MS = {state}"],
                    timing_state,
                    labeled_bullets(body, MICRO_OPERATIONS_LABEL),
                    labeled_conditionals(body, findings, case_id),
                )
            )
        check_timing_states(found, title, section.line, findings)

    return cases


# ---------------------------------------------------------------------------
# MRI and IOT instruction sections
# ---------------------------------------------------------------------------


def normalize_context_term(term: str) -> str:
    """Rewrite one heading condition as a control input where one is
    defined; other terms are returned unchanged."""

    value = clean(term)
    if match := MRI_OPCODE_TERM.fullmatch(value):
        opcode = match.group(1)
        if opcode in MRI_OPCODES:
            return f"IR_MRI_OPCODE = {opcode}"
        if opcode == IOT_OPCODE:
            return "IR_IS_IOT = 1"
    if match := IOT_OPERATION_TERM.fullmatch(value):
        return f"IR_IOT_OP = {match.group(1)}"
    if match := IOA_TERM.fullmatch(value):
        address = int(match.group(1), 8)
        return f"IR_IOA = {address:0{IOA_WIDTH}b}"
    return value


def instruction_context(prefix: str, title: str) -> list[str]:
    """Return the context of an MRI or IOT instruction heading."""

    if prefix == "iot" and title in DECODED_IOT_CONTEXTS:
        return list(DECODED_IOT_CONTEXTS[title])
    context = [normalize_context_term(term) for term in title.split(" AND ")]
    if prefix == "mri":
        return ["IR_IS_MRI = 1", *context]
    return context


def parse_instructions(
    document: Document, prefix: str, findings: Findings
) -> list[dict]:
    """One case per timing state of each ``### n.m IR[...] = ...``
    instruction heading.

    Each ``TSn:`` marker is followed by its μop bullets, and optionally a
    ``Conditional μops:`` block before the next marker.
    """

    cases = []
    titles = set()
    for heading in document.headings:
        if (
            heading.level != 3
            or heading.number is None
            or "IR[" not in heading.title
        ):
            continue
        titles.add(heading.title)
        context = instruction_context(prefix, heading.title)
        for term in context:
            if term.startswith(IOA_PREFIX) or any(
                reference in term for reference in RAW_IR_REFERENCES
            ):
                findings.error(
                    "UNTRANSLATED_CONTEXT_TERM",
                    f"Heading term {term!r} has no control-input form.",
                    heading.line,
                )

        body = document.body(heading)
        markers = [
            (index, int(match.group(1)))
            for index, line in enumerate(body.lines)
            if (match := TS_MARKER_PATTERN.match(line.strip()))
        ]
        check_timing_states(
            [timing_state for _, timing_state in markers],
            f"Section {heading.number}",
            heading.line,
            findings,
        )

        for position, (index, timing_state) in enumerate(markers):
            end = (
                markers[position + 1][0]
                if position + 1 < len(markers)
                else len(body.lines)
            )
            region = Block(body.line_number(index), body.lines[index:end])
            case_id = f"{prefix}:{heading.number}:ts{timing_state}"
            cases.append(
                make_case(
                    case_id,
                    document.path,
                    heading.line,
                    ["MS = EXECUTE", *context],
                    timing_state,
                    bullets_after(region, 0),
                    labeled_conditionals(region, findings, case_id),
                )
            )

    if prefix == "iot":
        for title in DECODED_IOT_CONTEXTS:
            if title not in titles:
                findings.error(
                    "MISSING_SECTION",
                    f"No instruction heading '{title}' found for its "
                    "decoded context.",
                )

    return cases


def parse_phase_binding(document: Document, findings: Findings) -> list[dict]:
    """One case per timing state from the external-IOT phase binding.

    The section is prose, so the extractor requires each documented
    binding sentence verbatim and builds the cases from them.
    """

    section = document.section(2, PHASE_BINDING_SECTION)
    if section is None:
        missing_section(findings, PHASE_BINDING_SECTION)
        return []

    body = document.body(section)
    lines = {clean(line).replace("`", "") for line in body.lines}
    missing = [
        sentence for sentence, _, _ in PHASE_BINDINGS if sentence not in lines
    ]
    for sentence in missing:
        findings.error(
            "MISSING_PHASE_BINDING",
            f"Expected binding not found: {sentence!r}",
            section.line,
        )
    if missing:
        return []

    return [
        make_case(
            f"iot:external:ts{timing_state}",
            document.path,
            section.line,
            PHASE_BINDING_CONTEXT,
            timing_state,
            conditional=[
                selection
                for _, timing_states, selection in PHASE_BINDINGS
                if timing_state in timing_states
            ],
        )
        for timing_state in TIMING_STATES
    ]


# ---------------------------------------------------------------------------
# INTERRUPT
# ---------------------------------------------------------------------------


def parse_interrupt(document: Document, findings: Findings) -> list[dict]:
    """One case per ``### n.m TSn`` heading; its μops are the bullets
    directly under the heading."""

    cases = []
    found = []
    for heading in document.headings:
        match = TS_TITLE_PATTERN.match(heading.title)
        if heading.level != 3 or match is None:
            continue
        timing_state = int(match.group(1))
        found.append(timing_state)
        cases.append(
            make_case(
                f"interrupt:{heading.number}",
                document.path,
                heading.line,
                ["MS = INTERRUPT"],
                timing_state,
                bullets_after(document.body(heading), -1),
            )
        )
    check_timing_states(found, "INTERRUPT", None, findings)
    return cases


# ---------------------------------------------------------------------------
# Console
# ---------------------------------------------------------------------------


def parse_console(document: Document, findings: Findings) -> list[dict]:
    """One case per ``## n. ... Operation`` section with μops.

    Each needs an ``Applicable context:`` code block and the console
    execution model. Operation sections without ``μops:``, such as Clear
    and Continue, execute no micro-operations and produce no case.
    """

    cases = []
    for heading in document.headings:
        if heading.level != 2 or not CONSOLE_TITLE_PATTERN.match(
            heading.title
        ):
            continue
        body = document.body(heading)
        if not label_indexes(body, MICRO_OPERATIONS_LABEL):
            continue
        case_id = f"console:{heading.number}"

        context = []
        for index in label_indexes(body, CONTEXT_LABEL)[:1]:
            values, _ = code_block_after(body, index)
            context = [value for _, value in values]
        if not context:
            findings.error(
                "MISSING_CONTEXT",
                f"'{CONTEXT_LABEL}' with a text code block is required.",
                heading.line,
                case_id,
            )

        models = [
            " ".join(value for _, value in code_block_after(body, index)[0])
            for index in label_indexes(body, EXECUTION_MODEL_LABEL)
        ]
        if models != [CONSOLE_EXECUTION_MODEL]:
            findings.error(
                "UNEXPECTED_EXECUTION_MODEL",
                f"'{EXECUTION_MODEL_LABEL}' must be a code block reading "
                f"'{CONSOLE_EXECUTION_MODEL}'.",
                heading.line,
                case_id,
            )

        cases.append(
            make_case(
                case_id,
                document.path,
                heading.line,
                context,
                None,
                labeled_bullets(body, MICRO_OPERATIONS_LABEL),
                execution_model=CONSOLE_MODEL,
            )
        )
    return cases


# ---------------------------------------------------------------------------
# OPR
# ---------------------------------------------------------------------------


def opr_scope(document: Document, findings: Findings) -> list[str]:
    """Return the ``Applies when:`` code block of an OPR document."""

    block = Block(1, document.lines)
    for index in label_indexes(block, SCOPE_LABEL)[:1]:
        values, _ = code_block_after(block, index)
        if values:
            return [value for _, value in values]
    findings.error(
        "MISSING_CONTEXT",
        f"'{SCOPE_LABEL}' with a text code block is required.",
    )
    return []


def parse_opr(
    document: Document, group: int, findings: Findings
) -> list[dict]:
    """One case per timing state that selects conditional μops.

    Within the Instruction Definition section, a timing state starts at a
    ``TSn:`` line or a ``### n.m TSn`` heading. Its top-level bullets are
    ``if PREDICATE: MICRO_OPERATION``, ``if PREDICATE:`` (a control-level
    effect explained by nested bullets, with no μop), or a placeholder; a
    ``Conditional μops:`` block adds more.
    """

    context = ["MS = EXECUTE", *opr_scope(document, findings)]
    section = document.section(2, OPR_DEFINITION_SECTION)
    if section is None:
        missing_section(findings, OPR_DEFINITION_SECTION)
        return []

    body = document.body(section)
    heading_lines = {heading.line: heading for heading in document.headings}
    selections: dict[int, list[dict[str, str]]] = {}
    first_line: dict[int, int] = {}
    timing_state = None

    for index, line in enumerate(body.lines):
        line_number = body.line_number(index)
        stripped = line.strip()
        heading = heading_lines.get(line_number)
        marker = (
            TS_TITLE_PATTERN.match(heading.title)
            if heading
            else TS_MARKER_PATTERN.match(stripped)
        )
        if heading or marker:
            timing_state = int(marker.group(1)) if marker else None
            if timing_state is not None:
                first_line.setdefault(timing_state, line_number)
                selections.setdefault(timing_state, [])
            continue
        if timing_state is None:
            continue

        case_id = f"opr{group}:ts{timing_state}"
        if stripped == CONDITIONAL_LABEL:
            selections[timing_state] += conditionals_after(
                body, index, findings, case_id
            )
            continue
        bullet = TOP_LEVEL_BULLET_PATTERN.match(line)
        if bullet is None:
            continue
        text = clean(bullet.group(1))
        if text in PLACEHOLDERS:
            continue
        match = OPR_CONDITIONAL_PATTERN.match(text)
        if match is None:
            findings.error(
                "UNRECOGNIZED_OPR_LINE",
                "Expected 'if PREDICATE: MICRO_OPERATION' or a "
                f"placeholder: {text!r}",
                line_number,
                case_id,
            )
            continue
        predicate, micro_operation = match.groups()
        if any(reference in predicate for reference in RAW_IR_REFERENCES):
            findings.error(
                "RAW_IR_BIT",
                "OPR predicates must name IR-derived control inputs, not "
                f"IR bits: {predicate!r}",
                line_number,
                case_id,
            )
        if micro_operation:
            selections[timing_state].append(
                {"predicate": predicate, "micro_operation": micro_operation}
            )

    check_timing_states(
        list(first_line), OPR_DEFINITION_SECTION, section.line, findings
    )
    return [
        make_case(
            f"opr{group}:ts{timing_state}",
            document.path,
            first_line[timing_state],
            context,
            timing_state,
            conditional=selections[timing_state],
        )
        for timing_state in TIMING_STATES
        if selections.get(timing_state)
    ]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def micro_operation_catalog(document: Document) -> set[str]:
    """Return the micro-operation names: the level-3 headings that are
    names."""

    return {
        heading.title
        for heading in document.headings
        if heading.level == 3 and MICRO_OPERATION_NAME.match(heading.title)
    }


def validate_cases(
    cases: Sequence[dict[str, Any]], known: set[str]
) -> list[Diagnostic]:
    """Report repeated case ids and malformed or unknown micro-operations."""

    diagnostics = []
    seen: set[str] = set()

    for case in cases:
        case_id = case["id"]
        if case_id in seen:
            diagnostics.append(
                case_error(
                    case, "DUPLICATE_CASE_ID", f"Duplicate case id: {case_id}"
                )
            )
        seen.add(case_id)

        operations = case["micro_operations"] + [
            item["micro_operation"]
            for item in case["conditional_micro_operations"]
        ]
        for operation in operations:
            if not MICRO_OPERATION_NAME.match(operation):
                diagnostics.append(
                    case_error(
                        case,
                        "MALFORMED_MICRO_OPERATION",
                        f"Malformed micro-operation: {operation!r}",
                    )
                )
            elif operation not in known:
                diagnostics.append(
                    case_error(
                        case,
                        "UNKNOWN_MICRO_OPERATION",
                        f"Unknown micro-operation: {operation}",
                    )
                )

    return diagnostics


def case_error(case: dict[str, Any], code: str, message: str) -> Diagnostic:
    """Return an error located at a case's source."""

    source = case["source"]
    return Diagnostic(
        ERROR, code, message, source["path"], source["line"], case["id"]
    )


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_execution_definitions(
    texts: dict[Path, str],
) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    """Extract every case from the source texts, keyed by source path.

    Returns the cases in output order and the sorted diagnostics.
    """

    documents = {
        path: Document(path.as_posix(), text) for path, text in texts.items()
    }
    parsers = [
        (FETCH_DEFER_SOURCE, parse_fetch_defer),
        (MRI_SOURCE, lambda d, f: parse_instructions(d, "mri", f)),
        (IOT_SOURCE, parse_phase_binding),
        (IOT_SOURCE, lambda d, f: parse_instructions(d, "iot", f)),
        (INTERRUPT_SOURCE, parse_interrupt),
        (CONSOLE_SOURCE, parse_console),
        *(
            (path, lambda d, f, g=group: parse_opr(d, g, f))
            for group, path in OPR_SOURCES.items()
        ),
    ]

    cases: list[dict[str, Any]] = []
    diagnostics: list[Diagnostic] = []
    for path, parser in parsers:
        findings = Findings(path.as_posix())
        found = parser(documents[path], findings)
        if not found and not findings.diagnostics:
            findings.error("NO_CASES_FOUND", "No execution cases found.")
        cases += found
        diagnostics += findings.diagnostics

    known = micro_operation_catalog(documents[MICRO_OPERATION_SOURCE])
    diagnostics += validate_cases(cases, known)
    return cases, sorted(diagnostics, key=diagnostic_sort_key)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def build_json_result(
    cases: Sequence[dict[str, Any]], diagnostics: Sequence[Diagnostic]
) -> dict[str, Any]:
    """Return the complete JSON document."""

    return {
        "format_version": FORMAT_VERSION,
        "control_design_version": CONTROL_DESIGN_VERSION,
        "artifact": ARTIFACT,
        "extraction_stage": EXTRACTION_STAGE,
        "cases": list(cases),
        "diagnostics": [asdict(item) for item in diagnostics],
    }


def serialize_json(data: dict[str, Any]) -> str:
    """Serialize JSON preserving key order, with a trailing newline."""

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def format_location(diagnostic: Diagnostic) -> str:
    if diagnostic.line is None:
        return diagnostic.source_path
    return f"{diagnostic.source_path}:{diagnostic.line}"


def build_report(diagnostics: Sequence[Diagnostic], case_count: int) -> str:
    """Build the human-readable extraction report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Execution-Definition Extraction Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Cases extracted: {case_count}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    for item in diagnostics:
        identifier = f" [{item.case_id}]" if item.case_id else ""
        lines.append(
            f"{item.severity} {item.code}{identifier} "
            f"{format_location(item)}: {item.message}"
        )
    if not diagnostics:
        lines.append("No diagnostics.")
    return "\n".join(lines) + "\n"


def format_failure(diagnostic: Diagnostic) -> list[str]:
    """Format one failure diagnostic for the console."""

    identifier = f" [{diagnostic.case_id}]" if diagnostic.case_id else ""
    return [
        f"{diagnostic.severity} {diagnostic.code}{identifier}",
        f"  Source: {format_location(diagnostic)}",
        f"  {diagnostic.message}",
    ]


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Extract execution definitions from the microarchitecture "
            "documentation."
        )
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Path to the repository root.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=DEFAULT_JSON_OUTPUT,
        help="Extracted JSON output path.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT_OUTPUT,
        help="Extraction report output path.",
    )
    return parser.parse_args(arguments)


def resolve_from_repo(root: Path, path: Path) -> Path:
    """Resolve a relative path from the repository root."""

    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_source(path: Path) -> str:
    """Read a source document, raising ``ExtractionFailure`` on failure."""

    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise ExtractionFailure(
            f"Required source does not exist: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise ExtractionFailure(
            f"Source is not valid UTF-8: {path}"
        ) from error
    except OSError as error:
        raise ExtractionFailure(
            f"Unable to read source {path}: {error}"
        ) from error


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings, creating parent directories."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def remove_previous_outputs(
    outputs: Sequence[Path],
    inputs: Sequence[Path],
) -> None:
    """Delete earlier output files, so no output outlives the run.

    Raises ``ValueError``, deleting nothing, if an output path is also an
    input or is a directory.
    """

    for path in outputs:
        if path in inputs:
            raise ValueError(f"Output path is also an input: {path}")
        if path.is_dir():
            raise ValueError(f"Output path is a directory: {path}")

    for path in outputs:
        path.unlink(missing_ok=True)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the extractor; return 1 if any error-level diagnostic exists.

    Relative paths are resolved from the repository root.
    """

    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    sources = [resolve_from_repo(root, path) for path in SOURCE_PATHS]
    json_output = resolve_from_repo(root, options.json_output)
    report_output = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs((json_output, report_output), sources)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    cases: list[dict[str, Any]] = []

    try:
        texts = {
            path: read_source(source)
            for path, source in zip(SOURCE_PATHS, sources, strict=True)
        }
    except ExtractionFailure as error:
        diagnostics = [
            Diagnostic(FATAL, "EXTRACTION_FAILURE", str(error), "<input>")
        ]
    else:
        cases, diagnostics = extract_execution_definitions(texts)
        write_text(
            json_output, serialize_json(build_json_result(cases, diagnostics))
        )

    write_text(report_output, build_report(diagnostics, len(cases)))

    failures = [
        item for item in diagnostics if item.severity in FAILURE_SEVERITIES
    ]
    exit_code = 1 if failures else 0

    print("Execution-definition extraction")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Cases: {len(cases)}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"JSON output: {json_output}")
    print(f"Report output: {report_output}")

    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            print("\n".join(format_failure(item)))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
