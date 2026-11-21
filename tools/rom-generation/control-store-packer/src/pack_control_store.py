"""Pack the promoted symbolic control words into the control store
organization and verify the result.

The control store organization (docs/04-control/08-control-store-
organization.md) realizes the control function with a mapping ROM, a
datapath slice, and a sequencer slice, each a 15-bit-address device set.
This tool:

1. Reads and validates the four promoted inputs.
2. For every control context (each running major state and timing state,
   and the halted pseudo-state) and every IR value, selects the applicable
   execution case and enumerates the runtime inputs its undecided guards
   still compare, recording each slice's required word and which of its
   fields require a value.
3. Finds the inputs each slice's word really depends on, groups identical
   EXECUTE behaviors into variants, and packs the datapath's runtime
   inputs into overlay groups.
4. Allocates datapath control bits, sharing bits between fields that never
   require a value in the same word.
5. Fills the logical images of every device.
6. Verifies end to end: for every IR value and reachable input
   combination, forms each address as the hardware does, reads the
   images, and compares every field that requires a value.
7. Writes the packing, the images, and a report.

The images are logical: they are written to the build directory for
review and are not promoted. See the tool README.
"""

from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
from collections import defaultdict
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from design import DESIGN  # noqa: E402  (control-design selection: common/design.py)

from predicates import (  # noqa: E402  (shared ROM-generation module)
    Expression,
    ExpressionError,
    compared_names,
    evaluate,
    exclusive_pairs,
    ir_derivation_table,
    parse_expression,
    value_domains,
    walk,
)

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

DEFAULT_ARTIFACT_DIRECTORY = Path(DESIGN.maintained)
OUTPUT_DIRECTORY = Path(f"{DESIGN.build}/control-store-packer")
DEFAULT_PACKING = OUTPUT_DIRECTORY / "control-store-packing.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "packing-report.txt"
DEFAULT_IMAGES = OUTPUT_DIRECTORY / "images"

INPUT_FILES = {
    "inputs": "control-input-schema.json",
    "words": "control-word-schema.json",
    "symbolic": "symbolic-control-words.json",
    "timing": "timing-constraints.json",
}

ARTIFACT = "control-store-packing"
FORMAT_VERSION = 1

# Control store organization (Control Store Organization sections 4-7).
ADDRESS_BITS = 15
DEVICE_WIDTH = 8
DATAPATH_DEVICES = 6
VARIANT_WIDTH = 5
DP_OVL_WIDTH = 5
DP_OVL_SEL_WIDTH = 2
IR_SEQ_WIDTH = 1
IR_SEQ_BIT = VARIANT_WIDTH + DP_OVL_SEL_WIDTH
HALTED_CODE = 7
EXECUTE = "EXECUTE"
SEQUENCER_FIELDS = (
    "MS_NEXT", "MS_LOAD", "RUN_NEXT", "HLT_REQ_NEXT", "/INITIALIZE",
)
FP_COMMANDS = (
    "FP_START", "FP_CONTINUE", "FP_CLEAR", "FP_LOAD_ADDRESS", "FP_EXAMINE",
    "FP_DEPOSIT",
)
FP_CMD = "FP_CMD"
FP_CMD_WIDTH = 3
SEQ_ALWAYS = ("HLT_REQ", "FP_STOP", "/DMA_REQ")
SEQ_RUNNING = ("FP_SINGLE_INSTRUCTION", "FP_SINGLE_STEP", "INTERRUPT_REQUEST_VALID")
IR_SEQ = ("IR_INDIRECT", "IR_OPR_HLT", "IR_IS_CAF")
# EXECUTE selection (Control Store Organization section 5.4.2): outside
# EXECUTE (MS_EFF_IS_EXECUTE = 0) the slices see VARIANT = 0, this wired
# overlay group, and IR_SEQ = IR_INDIRECT from predecode.
NON_EXECUTE_GROUP = 1
NON_EXECUTE_IR_SEQ = "IR_INDIRECT"
# Outside EXECUTE the datapath slice's VARIANT is the design's class decode
# (v2: IR_CLASS), and the sequencer slice's A2 the design's A2 decode (v2:
# IR_NO_EXECUTE); None means 0 (v1). Control Store Organization §5.4.2, §5.6.
NON_EXECUTE_VARIANT = DESIGN.non_execute_variant
SEQ_A2 = DESIGN.sequencer_a2
SEQ_A2_BIT = 2
SEQ_A1 = DESIGN.sequencer_a1
SEQ_A1_BIT = 1
# The wired state group's low FP_CMD_WIDTH bits are multiplexed by RUN (CSO §6.3).
STATE_GROUP_RUN_MUX = DESIGN.state_group_run_mux
# The non-EXECUTE contexts in which IR holds the current instruction (it loads
# at FETCH TP2), so the datapath word may depend on the class. In every other
# non-EXECUTE context the word must be the same for every class (§5.4.2).
CLASS_VALID_CONTEXTS = frozenset({"FETCH:TS3", "FETCH:TS4", "DEFER:TS1", "DEFER:TS2",
                                  "DEFER:TS3", "DEFER:TS4"})
# Instruction completion (Architectural Control Signals §4.10, INSTR_END): the
# major states an instruction can end in, and the next states that continue it.
COMPLETING_STATES = ("FETCH", "DEFER", "EXECUTE")
CONTINUING_STATES = ("DEFER", "EXECUTE")
STATE_NAMES = ("MS", "TS", "RUN")
OTHER = "~other"

# ---------------------------------------------------------------------------
# Diagnostics
# ---------------------------------------------------------------------------

INFO, WARNING, ERROR, FATAL = "INFO", "WARNING", "ERROR", "FATAL"
SEVERITY_ORDER = {s: i for i, s in enumerate((INFO, WARNING, ERROR, FATAL))}


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    entry_id: str | None = None


class PackingFailure(Exception):
    """An input could not be read; packing cannot proceed."""


def has_failures(diagnostics: Iterable[Diagnostic]) -> bool:
    return any(d.severity in (ERROR, FATAL) for d in diagnostics)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Guard:
    field: str
    value: int
    when: Expression


@dataclass
class Case:
    id: str
    base: Expression
    guards: tuple[Guard, ...]
    defaults: dict[str, int]


@dataclass(frozen=True)
class Context:
    """A control-store context: a running (MS, TS), or halted."""

    name: str
    ms_code: int
    values: tuple[tuple[str, str], ...]
    execute: bool
    halted: bool
    ts: int | None


@dataclass
class Model:
    fields: dict[str, dict[str, Any]]
    encoded: list[str]
    widths: dict[str, int]
    cares: dict[str, Expression | None]
    defaults: dict[str, int]
    cases: list[Case]
    exclusive: tuple[tuple[str, str], ...]
    violations: tuple[Expression, ...]
    domains: dict[str, Any]
    ir_table: dict[str, tuple[str, ...]]
    ms_codes: dict[str, int]
    contexts: list[Context]
    datapath_fields: list[str]
    sequencer_fields: list[str]


def octal_value(field: dict[str, Any], value: str) -> int:
    """Return the numeric encoding of ``value`` (Control Word section 2.1)."""

    values = field["values"]
    for item in values:
        if value in (item["encoding"], item["meaning"]):
            return int(item["encoding"], 8)
    if not values:
        if set(value) <= {"0", "1"} and len(value) <= field["width"]:
            return int(value, 2)
        if value.isdigit() and int(value) < 2 ** field["width"]:
            return int(value)
    raise ValueError(f"Unknown value {value!r} for {field['name']}.")


def canonical_literal(text: str) -> str:
    return text.lstrip("0") or "0"


def parse_care(text: str) -> Expression | None:
    """Parse a Value Required When condition; None means always."""

    text = text.strip()
    if text == "Always":
        return None
    normalized = re.sub(r"\s*(!?=)\s*", r" \1 ", text)
    return parse_expression(normalized)


def care_holds(expression: Expression | None, word: dict[str, int], ts: int | None) -> bool:
    if expression is None:
        return True
    values = {name: canonical_literal(format(v, "o")) for name, v in word.items()}
    if ts is not None:
        values["TS"] = str(ts)
    literalized = _canonical_literals(expression)
    result = evaluate(literalized, values)
    return True if result is None else result


_LITERAL_CACHE: dict[int, Expression] = {}


def _canonical_literals(expression: Expression) -> Expression:
    key = id(expression)
    if key not in _LITERAL_CACHE:
        def convert(node):
            if node[0] == "cmp":
                literal = node[3]
                if node[1] != "TS":
                    literal = canonical_literal(literal)
                return ("cmp", node[1], node[2], literal)
            if node[0] in ("and", "or"):
                return (node[0], convert(node[1]), convert(node[2]))
            if node[0] == "not":
                return ("not", convert(node[1]))
            return node
        _LITERAL_CACHE[key] = convert(expression)
    return _LITERAL_CACHE[key]


def build_model(documents: dict[str, dict[str, Any]]) -> tuple[Model | None, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []

    def error(code: str, message: str, entry: str | None = None) -> None:
        diagnostics.append(Diagnostic(ERROR, code, message, entry))

    inputs = {f["name"]: f for f in documents["inputs"]["fields"]}
    words = {f["name"]: f for f in documents["words"]["fields"]}
    encoded = [n for n, f in words.items() if f["control_word_role"] == "encoded"]
    widths = {n: int(words[n]["width"]) for n in encoded}

    cares: dict[str, Expression | None] = {}
    defaults: dict[str, int] = {}
    for name in encoded:
        f = words[name]
        try:
            cares[name] = parse_care(f["value_required_when"])
        except ExpressionError as exc:
            error("INVALID_CARE_CONDITION", f"{f['value_required_when']!r}: {exc}", name)
        try:
            defaults[name] = octal_value(f, str(f["default_value"]))
        except ValueError as exc:
            error("UNKNOWN_ENCODING", str(exc), name)

    cases = []
    for raw in documents["symbolic"]["cases"]:
        cid = raw["execution_case_id"]
        guards = []
        for fname, items in raw["field_assignments"].items():
            if fname not in widths:
                continue
            for item in items:
                if "value" not in item:
                    error("INPUT_SUPPLIED_VALUE",
                          "A control-store ROM cannot output an input's value "
                          "(Control Store Organization section 7.1).", f"{cid} {fname}")
                    continue
                try:
                    guards.append(Guard(fname, octal_value(words[fname], str(item["value"])),
                                        parse_expression(item["when"])))
                except (ValueError, ExpressionError) as exc:
                    error("INVALID_ASSIGNMENT", str(exc), f"{cid} {fname}")
        case_defaults = {}
        for fname, value in raw["defaults"].items():
            if fname in widths:
                case_defaults[fname] = octal_value(words[fname], str(value))
        cases.append(Case(cid, parse_expression(raw["base_context"]), tuple(guards),
                          {**defaults, **case_defaults}))

    violations = []
    for constraint in documents["timing"]["constraints"]:
        violations.append(("and", parse_expression(constraint["context"]),
                           ("not", parse_expression(constraint["requirement"]))))

    ir_table, problems = ir_derivation_table(inputs)
    for name, message in problems:
        error("IR_DERIVATION_UNUSABLE", message, name)

    ms_field = words["MS_NEXT"]
    ms_codes = {v["meaning"]: int(v["encoding"], 8) for v in ms_field["values"]}
    if max(ms_codes.values()) >= HALTED_CODE:
        error("MS_CODE_CONFLICT", "A major-state code collides with the halted code 7.")
    contexts = [
        Context(f"{ms}:TS{ts}", code,
                (("MS", ms), ("TS", str(ts)), ("RUN", "1")), ms == EXECUTE, False, ts)
        for ms, code in sorted(ms_codes.items(), key=lambda kv: kv[1])
        for ts in (1, 2, 3, 4)
    ]
    contexts.append(Context("HALTED", HALTED_CODE, (("RUN", "0"),), False, True, None))

    for name in SEQUENCER_FIELDS:
        if name not in widths:
            error("MISSING_SEQUENCER_FIELD", "Sequencer slice field is not an encoded field.", name)
    for name in (*FP_COMMANDS, *SEQ_ALWAYS, *SEQ_RUNNING):
        if name not in inputs:
            error("MISSING_INPUT", "Control store organization input is not defined.", name)
    for name in IR_SEQ:
        if name not in ir_table:
            error("MISSING_IR_DECODE", "IR_SEQ decode is not an evaluable IR-derived input.", name)
    for name, what in ((NON_EXECUTE_VARIANT, "non-EXECUTE VARIANT"), (SEQ_A2, "sequencer A2"),
                       (SEQ_A1, "sequencer A1")):
        if name is not None and name not in ir_table:
            error("MISSING_IR_DECODE", f"The {what} decode is not an evaluable IR-derived input.",
                  name)
    if NON_EXECUTE_VARIANT in ir_table and len(ir_table[NON_EXECUTE_VARIANT][0]) > VARIANT_WIDTH:
        error("VARIANT_OVERFLOW", f"{NON_EXECUTE_VARIANT} is wider than VARIANT.")
    if SEQ_A2 in ir_table and len(ir_table[SEQ_A2][0]) != 1:
        error("A2_NOT_ONE_BIT", "The sequencer A2 decode must be one bit.", SEQ_A2)
    if SEQ_A1 in ir_table and len(ir_table[SEQ_A1][0]) != 1:
        error("A1_NOT_ONE_BIT", "The sequencer A1 decode must be one bit.", SEQ_A1)

    if has_failures(diagnostics):
        return None, diagnostics
    domains = value_domains(inputs, words)
    model = Model(
        fields=words, encoded=encoded, widths=widths, cares=cares, defaults=defaults,
        cases=cases,
        exclusive=exclusive_pairs(inputs, documents["inputs"]["constraints"]),
        violations=tuple(violations), domains=domains, ir_table=ir_table,
        ms_codes=ms_codes, contexts=contexts,
        datapath_fields=[n for n in encoded if n not in SEQUENCER_FIELDS],
        sequencer_fields=[n for n in encoded if n in SEQUENCER_FIELDS],
    )
    return model, diagnostics


# ---------------------------------------------------------------------------
# Behavior: required words over the runtime inputs
# ---------------------------------------------------------------------------


@dataclass
class Record:
    """One reachable input combination and the slice word it requires."""

    values: dict[str, str]
    word: dict[str, int]
    care: frozenset[str]


@dataclass
class Behavior:
    """A slice's required words for one context and IR class."""

    context: Context
    irs: list[int]
    cases: tuple[str, ...]
    names: tuple[str, ...]
    records: list[Record]


def ir_values(model: Model, ir: int) -> dict[str, str]:
    return {name: column[ir] for name, column in model.ir_table.items()}


def domain_values(model: Model, name: str, literals: set[str]) -> list[str]:
    domain = model.domains.get(name)
    if domain is not None and domain.width is None and domain.values:
        return list(domain.values)
    return sorted(literals) + [OTHER]


def reachable(model: Model, values: dict[str, str]) -> bool:
    for left, right in model.exclusive:
        if values.get(left) == "1" and values.get(right) == "1":
            return False
    return not any(evaluate(v, values) is True for v in model.violations)


def behaviors(model: Model, slice_fields: Sequence[str], diagnostics: list[Diagnostic]
              ) -> list[Behavior]:
    """Compute every context's behaviors for one slice."""

    wanted = set(slice_fields)
    ir_cache = [ir_values(model, ir) for ir in range(4096)]
    # IR decodes that constraints mention decide reachability, so IR values
    # that differ in them must not share a behavior.
    constrained = {n for v in model.violations for n in compared_names(v)
                   if n in model.ir_table}
    constrained |= {n for pair in model.exclusive for n in pair if n in model.ir_table}
    result = []
    for context in model.contexts:
        known = dict(context.values)
        candidates = [c for c in model.cases if evaluate(c.base, known) is not False]
        groups: dict[tuple, list[int]] = defaultdict(list)
        selected_for: dict[tuple, list[Case]] = {}
        for ir in range(4096):
            values = {**known, **ir_cache[ir]}
            live = [c for c in candidates if evaluate(c.base, values) is not False]
            names = sorted({n for c in live for g in c.guards if g.field in wanted
                            for n in compared_names(g.when) if n in model.ir_table}
                           | {n for c in live for n in compared_names(c.base)
                              if n in model.ir_table}
                           | constrained)
            key = (tuple(c.id for c in live), tuple(values[n] for n in names))
            groups[key].append(ir)
            selected_for[key] = live
        reachable_states = 0
        for key, irs in groups.items():
            live = selected_for[key]
            base = {**known, **ir_cache[irs[0]]}
            behavior = _behavior(model, context, irs, live, base, wanted, diagnostics)
            reachable_states += len(behavior.records)
            result.append(behavior)
        if not reachable_states:
            diagnostics.append(Diagnostic(
                ERROR, "NO_REACHABLE_STATE",
                "No input state of this context is reachable.", context.name))
    return result


def _behavior(model, context, irs, live, base, wanted, diagnostics) -> Behavior:
    pending = []
    literals: dict[str, set[str]] = defaultdict(set)
    for case in live:
        for node in walk(case.base):
            if node[0] == "cmp" and node[1] not in base:
                literals[node[1]].add(node[3])
        for guard in case.guards:
            if guard.field in wanted and evaluate(guard.when, base) is not False:
                pending.append((case.id, guard))
                for node in walk(guard.when):
                    if node[0] == "cmp" and node[1] not in base:
                        literals[node[1]].add(node[3])
    if context.halted:
        for name in ("MS", "TS"):
            literals.setdefault(name, set())
    names = tuple(sorted(literals))
    choices = [domain_values(model, n, literals[n]) for n in names]
    records = []
    for combo in itertools.product(*choices):
        values = {**base, **dict(zip(names, combo))}
        if not reachable(model, values):
            continue
        chosen = [c for c in live if evaluate(c.base, values) is True]
        if len(chosen) != 1:
            if chosen:
                diagnostics.append(Diagnostic(
                    ERROR, "CASE_OVERLAP",
                    f"{len(chosen)} cases apply: {', '.join(c.id for c in chosen)}",
                    context.name))
            continue
        case = chosen[0]
        word = {f: case.defaults[f] for f in wanted}
        assigned: dict[str, int] = {}
        for cid, guard in pending:
            if cid == case.id and evaluate(guard.when, values) is True:
                if guard.field in assigned and assigned[guard.field] != guard.value:
                    diagnostics.append(Diagnostic(
                        ERROR, "CONFLICTING_ASSIGNMENTS",
                        f"{guard.field} has two values", f"{case.id} {context.name}"))
                assigned[guard.field] = guard.value
        word.update(assigned)
        care = frozenset(f for f in wanted if care_holds(model.cares[f], word, context.ts))
        records.append(Record({n: values[n] for n in names}, word, care))
    return Behavior(context, irs, tuple(sorted({c.id for c in live})), names, records)


# ---------------------------------------------------------------------------
# Dependence: which inputs a behavior really needs
# ---------------------------------------------------------------------------


def signal_of(name: str) -> str:
    return FP_CMD if name in FP_COMMANDS else name


def fp_code(values: dict[str, str]) -> int:
    for code, name in enumerate(FP_COMMANDS, 1):
        if values.get(name) == "1":
            return code
    return 0


def signal_value(signal: str, values: dict[str, str]) -> str:
    if signal == FP_CMD:
        return str(fp_code(values))
    return values.get(signal, OTHER)


def concrete_values(signal: str, values: dict[str, str]) -> list[str]:
    """Every value the hardware can present for ``signal`` that agrees with
    ``values``. An input the record does not compare can take any value, so
    an image must hold the record's word at all of them."""

    if signal == FP_CMD:
        codes = []
        for code in range(len(FP_COMMANDS) + 1):
            implied = {n: "1" if i + 1 == code else "0" for i, n in enumerate(FP_COMMANDS)}
            if all(values.get(n, implied[n]) in (implied[n], OTHER) for n in FP_COMMANDS):
                codes.append(str(code))
        return codes
    value = values.get(signal, OTHER)
    return ["0", "1"] if value == OTHER else [value]


def concrete_combinations(signals: Sequence[str], values: dict[str, str]
                          ) -> Iterator[tuple[str, ...]]:
    return itertools.product(*(concrete_values(s, values) for s in signals))


def projection(records: Sequence[Record], signals: Sequence[str]
               ) -> dict[tuple, dict[str, int]] | None:
    """Map each signal-value key to the required field values, or None
    when two records with the same key require different values."""

    table: dict[tuple, dict[str, int]] = {}
    for record in records:
        key = tuple(signal_value(s, record.values) for s in signals)
        required = table.setdefault(key, {})
        for f in record.care:
            value = record.word[f]
            if required.setdefault(f, value) != value:
                return None
    return table


def needed_signals(records: Sequence[Record], names: Sequence[str]) -> list[str] | None:
    """Greedily drop signals the required words do not depend on."""

    signals = sorted({signal_of(n) for n in names})
    if projection(records, signals) is None:
        return None
    for signal in list(signals):
        trial = [s for s in signals if s != signal]
        if projection(records, trial) is not None:
            signals = trial
    return signals


def signal_width(signal: str) -> int:
    return FP_CMD_WIDTH if signal == FP_CMD else 1


# ---------------------------------------------------------------------------
# Datapath: variants, overlay groups, bit allocation
# ---------------------------------------------------------------------------


@dataclass
class Signature:
    signals: tuple[str, ...]
    table: tuple

    def lookup(self) -> dict[tuple, dict[str, int]]:
        return dict(self.table)


def signature(records: Sequence[Record], signals: Sequence[str]) -> Signature:
    table = projection(records, signals)
    return Signature(tuple(signals),
                     tuple(sorted((k, tuple(sorted(v.items()))) for k, v in table.items())))


@dataclass
class Group:
    code: int
    signals: list[str]
    bits: dict[str, int] = field(default_factory=dict)
    # The state group behind the RUN multiplexer (CSO §6.3): `bits` is its halted face and
    # `running_bits` its running face. None: one face for both.
    running_bits: dict[str, int] | None = None

    def width(self) -> int:
        return sum(signal_width(s) for s in self.signals)

    def face(self, halted: bool) -> dict[str, int]:
        return self.bits if halted or self.running_bits is None else self.running_bits


def pack_groups(needs: Sequence[frozenset[str]]) -> tuple[list[Group], dict[frozenset, int]]:
    groups: list[Group] = []
    placement: dict[frozenset, int] = {}
    for need in sorted(set(needs), key=lambda n: (-sum(map(signal_width, n)), sorted(n))):
        if not need:
            continue
        for group in groups:
            union = set(group.signals) | need
            if sum(map(signal_width, union)) <= DP_OVL_WIDTH:
                group.signals = sorted(union)
                placement[need] = group.code
                break
        else:
            groups.append(Group(len(groups), sorted(need)))
            placement[need] = groups[-1].code
    for group in groups:
        bit = 0
        if FP_CMD in group.signals:
            group.bits[FP_CMD] = 0
            bit = FP_CMD_WIDTH
        for s in group.signals:
            if s != FP_CMD:
                group.bits[s] = bit
                bit += 1
    if not groups:
        groups.append(Group(0, []))
    for need in needs:
        if not need:
            placement[need] = 0
    return groups, placement


def place_group(groups: list[Group], placement: dict[frozenset, int], need: frozenset,
                code: int) -> None:
    """Renumber the groups so that the group holding ``need`` has ``code``.

    Used for the wired non-EXECUTE group. Empty groups are added when fewer
    groups exist; a need with no signals fits any group and keeps its
    placement."""

    while len(groups) <= code:
        groups.append(Group(len(groups), []))
    if not need:
        return
    current = placement[need]
    if current == code:
        return
    groups[current], groups[code] = groups[code], groups[current]
    groups[current].code, groups[code].code = current, code
    for key, value in placement.items():
        if not key:
            continue
        if value == current:
            placement[key] = code
        elif value == code:
            placement[key] = current


def state_group(halted_need: frozenset, running_need: frozenset) -> Group | None:
    """The wired state group behind the RUN multiplexer (CSO §6.3), or None if a face
    does not fit.

    Halted face: FP_CMD on bits 0..2, the other halted signals from bit 3 up. Running face:
    the halted face's unmultiplexed signals on the same bits, then the running signals on
    the free bits from 3 up, then on the multiplexed bits from 2 down. Bits 3 up are wired
    past the multiplexer, so the halted face shows the running signals placed there too."""

    halted = {FP_CMD: 0} if FP_CMD in halted_need else {}
    bit = FP_CMD_WIDTH
    for s in sorted(halted_need - {FP_CMD}):
        halted[s] = bit
        bit += signal_width(s)
    if bit > DP_OVL_WIDTH or FP_CMD in running_need:
        return None
    running = {s: b for s, b in halted.items() if s != FP_CMD}
    free = [b for b in range(FP_CMD_WIDTH, DP_OVL_WIDTH) if b not in running.values()]
    free += list(range(FP_CMD_WIDTH - 1, -1, -1))
    for s in sorted(running_need - set(running)):
        if signal_width(s) != 1 or not free:
            return None
        running[s] = free.pop(0)
    # Bits 3 up are not multiplexed: the hardware presents them in both faces.
    halted.update({s: b for s, b in running.items() if b >= FP_CMD_WIDTH})
    return Group(NON_EXECUTE_GROUP, sorted(halted_need | running_need), halted, running)


def insert_group(groups: list[Group], placement: dict[frozenset, int], state: Group) -> None:
    """Insert the state group at its wired code; the groups at and above it move up one."""

    code = state.code
    while len(groups) < code:
        groups.append(Group(len(groups), []))
    groups.insert(code, state)
    for index, group in enumerate(groups):
        group.code = index
    for key, value in placement.items():
        if key and value >= code:
            placement[key] = value + 1


def overlay_values(group: Group, ovl: int, halted: bool = True) -> dict[str, str]:
    out = {}
    for signal, bit in group.face(halted).items():
        if signal == FP_CMD:
            out[signal] = str((ovl >> bit) & 0b111)
        else:
            out[signal] = str((ovl >> bit) & 1)
    return out


def allocate_bits(records: Iterable[Record], fields: Sequence[str], widths: dict[str, int]
                  ) -> list[tuple[int, list[str]]]:
    conflict: dict[str, set[str]] = defaultdict(set)
    for record in records:
        for a, b in itertools.combinations(sorted(record.care & set(fields)), 2):
            conflict[a].add(b)
            conflict[b].add(a)
    slots: list[tuple[int, list[str]]] = []
    for name in sorted(fields, key=lambda n: (-widths[n], n)):
        for width, members in slots:
            if width >= widths[name] and not conflict[name] & set(members):
                members.append(name)
                break
        else:
            slots.append((widths[name], [name]))
    return slots


# ---------------------------------------------------------------------------
# Packing
# ---------------------------------------------------------------------------


@dataclass
class Packing:
    model: Model
    groups: list[Group]
    variants: dict[int, list[Signature]]
    variant_of: dict[tuple[int, int], int]          # (ts, ir) -> variant
    variant_group: dict[tuple[int, int], int]       # (ts, variant) -> group
    nonexec: dict[tuple[str, int], Signature]       # (context name, class) -> signature
    layout: dict[str, tuple[int, int]]              # field -> (offset, width)
    slots: list[tuple[int, list[str]]]
    sequencer_table: dict[tuple, dict[str, int]]
    # (MS_EFF_IS_EXECUTE, ts) -> decodes needed / decode presented on IR_SEQ
    ir_seq_needs: dict[tuple[int, int], list[str]]
    ir_seq_select: dict[tuple[int, int], str | None]
    images: dict[str, list[int]] = field(default_factory=dict)
    checked: int = 0


def pack(model: Model) -> tuple[Packing | None, list[Diagnostic]]:
    diagnostics: list[Diagnostic] = []

    def error(code, message, entry=None):
        diagnostics.append(Diagnostic(ERROR, code, message, entry))

    # ---------------- datapath
    dp = behaviors(model, model.datapath_fields, diagnostics)
    variants: dict[int, list[Signature]] = defaultdict(list)
    variant_of: dict[tuple[int, int], int] = {}
    nonexec_sigs: dict[tuple[str, int], set] = defaultdict(set)
    nonexec: dict[tuple[str, int], Signature] = {}
    needs: list[frozenset] = []
    non_execute_needs: set[str] = set()
    halted_needs: set[str] = set()
    for b in dp:
        if not b.records:
            continue  # unreachable IR values: any address content will do
        signals = needed_signals(b.records, b.names)
        if signals is None:
            error("INCONSISTENT_BEHAVIOR", "Records with equal inputs require different words.",
                  b.context.name)
            continue
        bad = [s for s in signals if s in STATE_NAMES]
        if bad:
            error("INVISIBLE_DEPENDENCY",
                  f"The datapath word depends on {', '.join(bad)}, which the address "
                  "does not carry in this context.", b.context.name)
            continue
        sig = signature(b.records, signals)
        if b.context.execute:
            codes = variants[b.context.ts]
            if sig not in codes:
                codes.append(sig)
            for ir in b.irs:
                variant_of[(b.context.ts, ir)] = codes.index(sig)
            needs.append(frozenset(signals))
        else:
            for cls in sorted({non_execute_class(model, ir) for ir in b.irs}):
                nonexec_sigs[(b.context.name, cls)].add((sig.signals, sig.table))
                nonexec[(b.context.name, cls)] = sig
            non_execute_needs |= set(signals)
            if b.context.halted:
                halted_needs |= set(signals)
    for (name, cls), sigs in nonexec_sigs.items():
        if len(sigs) > 1:
            error("NON_EXECUTE_IR_DEPENDENCE",
                  "The datapath word depends on IR outside EXECUTE beyond "
                  + (f"{NON_EXECUTE_VARIANT}" if NON_EXECUTE_VARIANT else "the wired VARIANT 0")
                  + ", the only instruction input there.", f"{name} class {cls}")
    by_context: dict[str, set] = defaultdict(set)
    for (name, cls), sigs in nonexec_sigs.items():
        by_context[name] |= sigs
    for name, sigs in by_context.items():
        if name not in CLASS_VALID_CONTEXTS and len(sigs) > 1:
            error("NON_EXECUTE_CLASS_DEPENDENCE",
                  "The datapath word depends on the instruction class in a context where IR "
                  "does not hold the current instruction.", name)
    for ts, codes in variants.items():
        if len(codes) > 2 ** VARIANT_WIDTH:
            error("VARIANT_OVERFLOW", f"{len(codes)} variants exceed {2 ** VARIANT_WIDTH}.",
                  f"EXECUTE:TS{ts}")
    # Every non-EXECUTE context shares the one wired overlay group.
    non_execute_need = frozenset(non_execute_needs)
    state = None
    if STATE_GROUP_RUN_MUX:
        # The state group has a halted and a running face (CSO §6.3); it is placed alone
        # at the wired code, and the EXECUTE needs share the other groups.
        halted_need = frozenset(halted_needs)
        running_need = frozenset(non_execute_needs - halted_needs)
        state = state_group(halted_need, running_need)
        if state is None:
            error("OVERLAY_TOO_WIDE",
                  f"halted {sorted(halted_need)} and running {sorted(running_need)} do not fit "
                  f"the {DP_OVL_WIDTH} state-group bits behind the RUN multiplexer.")
        all_needs = needs
    else:
        all_needs = needs + [non_execute_need]
    for need in all_needs:
        if sum(map(signal_width, need)) > DP_OVL_WIDTH:
            error("OVERLAY_TOO_WIDE",
                  f"{sorted(need)} need more than {DP_OVL_WIDTH} overlay bits"
                  + (" (the non-EXECUTE contexts share one wired group)."
                     if need == non_execute_need else "."))
    if has_failures(diagnostics):
        return None, diagnostics
    groups, placement = pack_groups(all_needs)
    if state is not None:
        insert_group(groups, placement, state)
    else:
        place_group(groups, placement, non_execute_need, NON_EXECUTE_GROUP)
    if len(groups) > 2 ** DP_OVL_SEL_WIDTH:
        error("OVERLAY_GROUP_OVERFLOW", f"{len(groups)} overlay groups exceed "
              f"{2 ** DP_OVL_SEL_WIDTH}.")
        return None, diagnostics
    variant_group = {(ts, v): placement[frozenset(sig.signals)]
                     for ts, codes in variants.items() for v, sig in enumerate(codes)}

    slots = allocate_bits((r for b in dp for r in b.records), model.datapath_fields,
                          model.widths)
    layout, offset = {}, 0
    for width, members in slots:
        for name in members:
            layout[name] = (offset, model.widths[name])
        offset += width
    if offset > DATAPATH_DEVICES * DEVICE_WIDTH:
        error("DATAPATH_TOO_WIDE", f"{offset} bits exceed {DATAPATH_DEVICES} devices.")
        return None, diagnostics

    # ---------------- sequencer
    seq = behaviors(model, model.sequencer_fields, diagnostics)
    seq_table: dict[tuple, dict[str, int]] = {}
    seq_records: dict[tuple, list] = defaultdict(list)
    for b in seq:
        visible = list(SEQ_ALWAYS) + ([FP_CMD] if b.context.halted else list(SEQ_RUNNING))
        allowed = set(visible)
        signals = needed_signals(b.records, b.names)
        if signals is None:
            error("INCONSISTENT_BEHAVIOR", "Sequencer records conflict.", b.context.name)
            continue
        hidden = [s for s in signals if s not in allowed]
        if hidden:
            error("INVISIBLE_DEPENDENCY",
                  f"The sequencer word depends on {', '.join(hidden)}, which its address "
                  "does not carry.", b.context.name)
            continue
        # Keys are concrete address values: an input the record does not
        # compare is expanded to every value, so that equal addresses with
        # different required words are found as conflicts below.
        for record in b.records:
            for ir_group in _split_by_irseq(model, b.irs):
                for concrete in concrete_combinations(visible, record.values):
                    seq_records[(b.context.name, ir_group, concrete)].append(record)
    for key, records in seq_records.items():
        if projection(records, []) is None:
            error("SEQUENCER_IR_DEPENDENCE",
                  "The sequencer word depends on IR beyond the IR_SEQ and A2 decodes.", key[0])
    if has_failures(diagnostics):
        return None, diagnostics
    ir_seq_needs = _ir_seq_needs(model, seq_records)
    ir_seq_select: dict[tuple[int, int], str | None] = {}
    for ts in (1, 2, 3, 4):
        # Outside EXECUTE, IR_SEQ is wired to IR_INDIRECT from predecode.
        ir_seq_select[(0, ts)] = NON_EXECUTE_IR_SEQ
    for (execute, ts), names in ir_seq_needs.items():
        if len(names) > IR_SEQ_WIDTH:
            error("IR_SEQ_TOO_WIDE",
                  f"The sequencer needs {', '.join(names)}, more than one IR_SEQ bit.",
                  context_label(execute, ts))
        elif not execute and names and names != [NON_EXECUTE_IR_SEQ]:
            error("NON_EXECUTE_IR_SEQ",
                  f"Outside EXECUTE, IR_SEQ carries only {NON_EXECUTE_IR_SEQ}; the "
                  f"sequencer needs {', '.join(names)}.", context_label(execute, ts))
        if execute:
            ir_seq_select[(execute, ts)] = names[0] if names else None
    if has_failures(diagnostics):
        return None, diagnostics

    # Project onto the single IR_SEQ bit: the decode presented for
    # (MS_EFF_IS_EXECUTE, TS).
    contexts = {c.name: c for c in model.contexts}
    seq_projected: dict[tuple, list] = defaultdict(list)
    for (ctx, irseq, visible), records in seq_records.items():
        context = contexts[ctx]
        execute = 1 if context.execute else 0
        for ts in ((context.ts,) if context.ts else (1, 2, 3, 4)):
            selected = ir_seq_select.get((execute, ts))
            bit = irseq[IR_SEQ.index(selected)] if selected else "0"
            seq_projected[(ctx, ts, bit, irseq[-2], irseq[-1], visible)].extend(records)
    for key, records in seq_projected.items():
        table = projection(records, [])
        if table is None:
            error("SEQUENCER_IR_DEPENDENCE",
                  "The sequencer word depends on an IR decode the IR_SEQ bit does not "
                  "carry in this timing state.", f"{key[0]} TS{key[1]}")
            continue
        seq_table[key] = table[()]
    if has_failures(diagnostics):
        return None, diagnostics
    check_instruction_end(model, seq_table, diagnostics)
    if has_failures(diagnostics):
        return None, diagnostics

    packing = Packing(model, groups, dict(variants), variant_of, variant_group, nonexec,
                      layout, slots, seq_table, ir_seq_needs, ir_seq_select)
    build_images(packing)
    verify(packing, dp, seq, diagnostics)
    return packing, diagnostics


def _split_by_irseq(model: Model, irs: Sequence[int]) -> list[tuple[str, ...]]:
    """The IR_SEQ decodes, then the A2 and A1 decodes, of each IR value."""
    return sorted({tuple(model.ir_table[n][ir] for n in IR_SEQ)
                   + (a2_value(model, ir), a1_value(model, ir)) for ir in irs})


def a2_value(model: Model, ir: int) -> str:
    """The sequencer slice's A2 for IR value `ir` (Control Store Organization §5.6)."""
    return model.ir_table[SEQ_A2][ir] if SEQ_A2 else "0"


def a1_value(model: Model, ir: int) -> str:
    """The sequencer slice's A1 for IR value `ir` (Control Store Organization §5.6)."""
    return model.ir_table[SEQ_A1][ir] if SEQ_A1 else "0"


def non_execute_class(model: Model, ir: int) -> int:
    """The datapath slice's VARIANT outside EXECUTE for IR value `ir` (§5.4.2)."""
    return int(model.ir_table[NON_EXECUTE_VARIANT][ir], 2) if NON_EXECUTE_VARIANT else 0


def context_label(execute: int, ts: int) -> str:
    return f"{'EXECUTE' if execute else 'NON_EXECUTE'}:TS{ts}"


def _ir_seq_needs(model, seq_records) -> dict[tuple[int, int], list[str]]:
    """For each (MS_EFF_IS_EXECUTE, TS), the IR_SEQ decodes the sequencer
    word depends on."""

    by_ctx: dict[str, dict[tuple, dict[tuple, set]]] = defaultdict(lambda: defaultdict(dict))
    for (ctx, irseq, visible), records in seq_records.items():
        by_ctx[ctx][visible][irseq] = records
    needs: dict[tuple[int, int], set] = defaultdict(set)
    contexts = {c.name: c for c in model.contexts}
    for ctx, per_visible in by_ctx.items():
        context = contexts[ctx]
        used = set()
        for index, name in enumerate(IR_SEQ):
            for per_ir in per_visible.values():
                seen: dict[tuple, dict] = {}
                for irseq, records in per_ir.items():
                    key = irseq[:index] + irseq[index + 1:]
                    word = projection(records, [])[()]
                    if key in seen and seen[key] != word:
                        used.add(name)
                    seen.setdefault(key, word)
        execute = 1 if context.execute else 0
        for ts in ((context.ts,) if context.ts else (1, 2, 3, 4)):
            needs[(execute, ts)] |= used
    return {k: sorted(v) for k, v in needs.items()}


# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------


def pack_word(packing: Packing, word: dict[str, int], care: set[str]) -> int:
    value = 0
    for width, members in packing.slots:
        owner = next((m for m in members if m in care), members[0])
        offset, w = packing.layout[owner]
        value |= (word.get(owner, packing.model.defaults[owner]) & ((1 << w) - 1)) << offset
    return value


def unpack(packing: Packing, value: int, name: str) -> int:
    offset, width = packing.layout[name]
    return (value >> offset) & ((1 << width) - 1)


def mapping_address(ir: int, ts: int) -> int:
    """Mapping ROM address; A0 is wired 0."""
    return (ir << 3) | ((ts - 1) << 1)


def next_ts(ts: int) -> int:
    return ts % 4 + 1


def previous_ts(ts: int) -> int:
    return (ts - 2) % 4 + 1


def mapping_entry(variant: int, group: int, irseq: int) -> int:
    return variant | (group << VARIANT_WIDTH) | (irseq << IR_SEQ_BIT)


def slice_select(packing: Packing, execute: bool, ir: int, ts: int) -> int:
    """The VARIANT, DP_OVL_SEL, and IR_SEQ the slices see, packed as a
    mapping entry. In EXECUTE TS n, MAPR holds the mapping ROM entry
    captured at TP n-1, which was addressed with TS n-1; outside EXECUTE
    the selection presents fixed values and IR_INDIRECT."""

    if execute:
        return packing.images["mapping"][mapping_address(ir, previous_ts(ts))]
    indirect = int(packing.model.ir_table[NON_EXECUTE_IR_SEQ][ir])
    return mapping_entry(non_execute_class(packing.model, ir), NON_EXECUTE_GROUP, indirect)


def datapath_address(ms_eff: int, ts: int, variant: int, ovl: int) -> int:
    return (ms_eff << 12) | ((ts - 1) << 10) | (variant << 5) | ovl


def sequencer_address(ms_eff: int, ts: int, values: dict[str, str], halted: bool,
                      irseq: str, a2: str = "0", a1: str = "0") -> int:
    def bit(name):
        return 1 if values.get(name) == "1" else 0
    ovl = fp_code(values) if halted else (
        bit(SEQ_RUNNING[0]) << 2 | bit(SEQ_RUNNING[1]) << 1 | bit(SEQ_RUNNING[2]))
    return ((ms_eff << 12) | ((ts - 1) << 10) | bit("HLT_REQ") << 9 | bit("FP_STOP") << 8
            | ovl << 5 | bit("/DMA_REQ") << 4 | int(irseq) << 3 | int(a2) << SEQ_A2_BIT
            | int(a1) << SEQ_A1_BIT)


def build_images(packing: Packing) -> None:
    model = packing.model
    default = pack_word(packing, model.defaults, set())
    seq_default = _seq_word(model, model.defaults)

    # The entry at TS n is the EXECUTE entry for TS n+1 (TS4 holds TS1).
    mapping = [0] * (1 << ADDRESS_BITS)
    for ir in range(4096):
        for ts in (1, 2, 3, 4):
            target = next_ts(ts)
            v = packing.variant_of.get((target, ir), 0)
            g = packing.variant_group.get((target, v), 0)
            selected = packing.ir_seq_select.get((1, target))
            irseq = int(model.ir_table[selected][ir]) if selected else 0
            mapping[mapping_address(ir, ts)] = mapping_entry(v, g, irseq)

    datapath = [default] * (1 << ADDRESS_BITS)
    contexts = {(c.ms_code, c.ts): c for c in model.contexts if not c.halted}
    for ms_eff in range(8):
        for ts in (1, 2, 3, 4):
            context = contexts.get((ms_eff, ts))
            for variant in range(1 << VARIANT_WIDTH):
                if ms_eff == HALTED_CODE:
                    sig, group = _class_independent(packing, "HALTED"), NON_EXECUTE_GROUP
                elif context is None:
                    continue
                elif context.execute:
                    codes = packing.variants.get(ts, [])
                    if variant >= len(codes):
                        continue
                    sig = codes[variant]
                    group = packing.variant_group[(ts, variant)]
                elif NON_EXECUTE_VARIANT and context.name in CLASS_VALID_CONTEXTS:
                    sig, group = packing.nonexec.get((context.name, variant)), NON_EXECUTE_GROUP
                    if sig is None:
                        continue                      # no instruction has this class
                else:
                    sig, group = _class_independent(packing, context.name), NON_EXECUTE_GROUP
                table = sig.lookup()
                g = packing.groups[group]
                for ovl in range(1 << DP_OVL_WIDTH):
                    values = overlay_values(g, ovl, ms_eff == HALTED_CODE)
                    key = tuple(values.get(s, OTHER) for s in sig.signals)
                    required = table.get(key)
                    if required is None:
                        continue
                    word = {**model.defaults, **dict(required)}
                    datapath[datapath_address(ms_eff, ts, variant, ovl)] = pack_word(
                        packing, word, set(dict(required)))

    sequencer = [seq_default] * (1 << ADDRESS_BITS)
    for (ctx, ts, irseq, a2, a1, visible), required in packing.sequencer_table.items():
        context = next(c for c in model.contexts if c.name == ctx)
        values = dict(zip(list(SEQ_ALWAYS) + ([FP_CMD] if context.halted else list(SEQ_RUNNING)),
                          visible))
        if context.halted:
            code = int(values.pop(FP_CMD))
            values.update({n: "1" if i + 1 == code else "0" for i, n in enumerate(FP_COMMANDS)})
        word = _seq_word(model, {**model.defaults, **required})
        ms_eff = HALTED_CODE if context.halted else context.ms_code
        sequencer[sequencer_address(ms_eff, ts, values, context.halted, irseq, a2, a1)] = word
        # A1 = 1 occurs only with the IR_SEQ and A2 values of the A1 decode's own IR values
        # (v2: a Group 2 HLT, so IR_INDIRECT = 0 and IR_NO_EXECUTE = 1). The other A1 = 1
        # addresses are unreachable from any IR value; they repeat the A1 = 0 word, so that a
        # word that does not depend on IR is the same at every address an undefined IR (power-on)
        # can form.
        if SEQ_A1 and a1 == "0" and (ctx, ts, irseq, a2, "1", visible) not in packing.sequencer_table:
            sequencer[sequencer_address(ms_eff, ts, values, context.halted, irseq, a2, "1")] = word

    packing.images = {"mapping": mapping, "sequencer": sequencer}
    for device in range(DATAPATH_DEVICES):
        packing.images[f"datapath-{device}"] = [
            (w >> (DEVICE_WIDTH * device)) & 0xFF for w in datapath]
    packing.images["_datapath_words"] = datapath


def _class_independent(packing: Packing, name: str) -> Signature:
    """The datapath signature of a non-EXECUTE context whose word does not
    depend on the class: it fills every VARIANT, so an undefined IR (power-on)
    selects the same word."""
    return next(sig for (ctx, _), sig in sorted(packing.nonexec.items(),
                                                 key=lambda kv: kv[0]) if ctx == name)


def check_instruction_end(model: Model, seq_table: dict, diagnostics: list[Diagnostic]) -> None:
    """INSTR_END (Architectural Control Signals §4.10) is decoded by gates from
    MS_EFF, TS, and the predecodes; it must hold exactly where a running TS4
    sequencer word completes an instruction, that is, where the word does not
    continue it into DEFER or EXECUTE (Control Store Organization §9)."""

    ms_names = {code: name for name, code in model.ms_codes.items()}
    continuing = {model.ms_codes[name] for name in CONTINUING_STATES}
    contexts = {c.name: c for c in model.contexts}
    bad = []
    for (ctx, ts, irseq, a2, _a1, visible), word in seq_table.items():
        context = contexts[ctx]
        if context.halted or ts != 4:
            continue
        ms = ms_names[context.ms_code]
        if ms not in COMPLETING_STATES:
            continue
        completes = word.get("MS_NEXT") not in continuing
        indirect = irseq == "1"            # outside EXECUTE, IR_SEQ is IR_INDIRECT
        gates = (ms == EXECUTE
                 or (ms == "FETCH" and a2 == "1" and not indirect)
                 or (ms == "DEFER" and a2 == "1"))
        if completes != gates:
            bad.append(f"{ctx} IR_SEQ={irseq} A2={a2}")
    for entry in sorted(set(bad))[:20]:
        diagnostics.append(Diagnostic(ERROR, "INSTR_END_DISAGREES",
                                      "The INSTR_END decode disagrees with the sequencer's "
                                      "instruction completion.", entry))


def _seq_word(model: Model, word: dict[str, int]) -> int:
    value, offset = 0, 0
    for name in model.sequencer_fields:
        value |= (word[name] & ((1 << model.widths[name]) - 1)) << offset
        offset += model.widths[name]
    return value


def _seq_unpack(model: Model, value: int, name: str) -> int:
    offset = 0
    for n in model.sequencer_fields:
        if n == name:
            return (value >> offset) & ((1 << model.widths[n]) - 1)
        offset += model.widths[n]
    raise KeyError(name)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify(packing: Packing, dp: Sequence[Behavior], seq: Sequence[Behavior],
           diagnostics: list[Diagnostic]) -> None:
    """Form every address as the hardware does and compare the images with
    every required field value.

    For each IR value the mapping register and EXECUTE selection give the
    entry the slices see; IR values with the same entry address the slices
    identically, so each distinct entry is checked once. An input a record
    does not compare can take any value in hardware, so every value of it
    is checked."""

    model = packing.model
    datapath = packing.images["_datapath_words"]
    sequencer = packing.images["sequencer"]
    mismatches: list[str] = []
    checked = 0

    def entries(b: Behavior, ts: int) -> dict[int, int]:
        found: dict[int, int] = {}
        for ir in b.irs:
            found.setdefault(slice_select(packing, b.context.execute, ir, ts), ir)
        return found

    for b in dp:
        context = b.context
        ms_eff = HALTED_CODE if context.halted else context.ms_code
        for ts in ((context.ts,) if context.ts else (1, 2, 3, 4)):
            for entry, ir in entries(b, ts).items():
                variant = entry & ((1 << VARIANT_WIDTH) - 1)
                group = packing.groups[(entry >> VARIANT_WIDTH) & ((1 << DP_OVL_SEL_WIDTH) - 1)]
                bits = group.face(context.halted)
                signals = list(bits)
                for record in b.records:
                    for concrete in concrete_combinations(signals, record.values):
                        ovl = 0
                        for s, v in zip(signals, concrete):
                            ovl |= int(v) << bits[s]
                        word = datapath[datapath_address(ms_eff, ts, variant, ovl)]
                        checked += 1
                        for f in record.care:
                            if unpack(packing, word, f) != record.word[f]:
                                mismatches.append(f"{context.name} TS{ts} IR={ir:04o} {f}")
                                break

    for b in seq:
        context = b.context
        ms_eff = HALTED_CODE if context.halted else context.ms_code
        visible = list(SEQ_ALWAYS) + ([FP_CMD] if context.halted else list(SEQ_RUNNING))
        for ts in ((context.ts,) if context.ts else (1, 2, 3, 4)):
            seen: dict[tuple, int] = {}
            for ir in b.irs:
                seen.setdefault((slice_select(packing, context.execute, ir, ts),
                                 a2_value(model, ir), a1_value(model, ir)), ir)
            for (entry, a2, a1), ir in seen.items():
                irseq = str((entry >> IR_SEQ_BIT) & 1)
                for record in b.records:
                    for concrete in concrete_combinations(visible, record.values):
                        values = dict(zip(visible, concrete))
                        if context.halted:
                            code = int(values.pop(FP_CMD))
                            values.update({n: "1" if i + 1 == code else "0"
                                           for i, n in enumerate(FP_COMMANDS)})
                        word = sequencer[sequencer_address(ms_eff, ts, values,
                                                           context.halted, irseq, a2, a1)]
                        checked += 1
                        for f in record.care:
                            if _seq_unpack(model, word, f) != record.word[f]:
                                mismatches.append(f"{context.name} TS{ts} IR={ir:04o} "
                                                  f"{f} at {values}")
                                break

    packing.checked = checked
    for m in mismatches[:20]:
        diagnostics.append(Diagnostic(ERROR, "VERIFICATION_MISMATCH",
                                      "Image word differs from the required value.", m))
    if len(mismatches) > 20:
        diagnostics.append(Diagnostic(ERROR, "VERIFICATION_MISMATCH",
                                      f"{len(mismatches) - 20} further mismatches."))


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def packing_json(packing: Packing, diagnostics: Sequence[Diagnostic]) -> dict[str, Any]:
    model = packing.model
    single_bit = all(len(v) <= 1 for v in packing.ir_seq_needs.values())
    variant_counts = {f"TS{ts}": len(codes) for ts, codes in sorted(packing.variants.items())}
    datapath_bits = sum(w for w, _ in packing.slots)
    return {
        "format_version": FORMAT_VERSION,
        "control_design_version": DESIGN.name,
        "artifact": ARTIFACT,
        "summary": {
            "datapath_bits": datapath_bits,
            "datapath_devices": DATAPATH_DEVICES,
            "execute_variants": variant_counts,
            "overlay_groups": len(packing.groups),
            "overlay_select_bits_needed": max(1, (len(packing.groups) - 1).bit_length()),
            "ir_seq_single_bit_feasible": single_bit,
            "verified_addresses": packing.checked,
        },
        "address_maps": {
            "mapping_rom": "A14..A3 = IR[11:0], A2..A1 = TS_CODE (TS-1), A0 = 0; "
                           "the entry at TS n is the EXECUTE entry for TS n+1",
            "datapath_slice": "A14..A12 = MS_EFF, A11..A10 = TS_CODE (TS-1), A9..A5 = VARIANT, "
                              "A4..A0 = DP_OVL",
            "sequencer_slice": "A14..A12 = MS_EFF, A11..A10 = TS_CODE (TS-1), A9 = HLT_REQ, "
                               "A8 = FP_STOP, A7..A5 = SEQ_OVL, A4 = /DMA_REQ, A3 = IR_SEQ, "
                               + (f"A2 = {SEQ_A2}, A1 = {SEQ_A1}, A0 = 0" if SEQ_A2 and SEQ_A1
                                  else f"A2 = {SEQ_A2}, A1..A0 = 0" if SEQ_A2 else "A2..A0 = 0"),
        },
        # Present only for a design that sets them (absent for v1), so v1 output is unchanged.
        **({"non_execute_variant": NON_EXECUTE_VARIANT} if NON_EXECUTE_VARIANT else {}),
        **({"sequencer_a2": SEQ_A2} if SEQ_A2 else {}),
        **({"sequencer_a1": SEQ_A1} if SEQ_A1 else {}),
        "mapping_rom": {
            "fields": {"VARIANT": [0, VARIANT_WIDTH],
                       "DP_OVL_SEL": [VARIANT_WIDTH, DP_OVL_SEL_WIDTH],
                       "IR_SEQ": [IR_SEQ_BIT, IR_SEQ_WIDTH]},
            "ir_seq_decode": {context_label(execute, ts): name for (execute, ts), name
                              in sorted(packing.ir_seq_select.items())},
        },
        "fp_cmd": {name: code for code, name in enumerate(FP_COMMANDS, 1)},
        "overlay_groups": [
            {"code": g.code,
             "bits": [{"bit": bit, "signal": s, "width": signal_width(s)}
                      for s, bit in sorted(g.bits.items(), key=lambda kv: kv[1])],
             # The state group's running face behind the RUN multiplexer (CSO §6.3); "bits"
             # is then its halted face. Absent for a group with one face (and for v1).
             **({"running_bits": [{"bit": bit, "signal": s, "width": signal_width(s)}
                                  for s, bit in sorted(g.running_bits.items(),
                                                       key=lambda kv: kv[1])]}
                if g.running_bits is not None else {})}
            for g in packing.groups
        ],
        "non_execute_overlay_group": NON_EXECUTE_GROUP,
        "execute_variants": {
            f"TS{ts}": [
                {"variant": v,
                 "overlay_group": packing.variant_group[(ts, v)],
                 "signals": list(sig.signals),
                 "ir_values": sum(1 for (t, _), x in packing.variant_of.items()
                                  if t == ts and x == v)}
                for v, sig in enumerate(codes)
            ]
            for ts, codes in sorted(packing.variants.items())
        },
        "datapath_layout": [
            {"offset": packing.layout[members[0]][0], "width": width, "fields": members}
            for width, members in packing.slots
        ],
        "sequencer_layout": _sequencer_layout(model),
        "ir_seq_needs": {context_label(execute, ts): names
                         for (execute, ts), names in sorted(packing.ir_seq_needs.items())},
        "diagnostics": [d.__dict__ for d in diagnostics],
    }


def _sequencer_layout(model: Model) -> list[dict[str, Any]]:
    out, offset = [], 0
    for name in model.sequencer_fields:
        out.append({"offset": offset, "width": model.widths[name], "field": name})
        offset += model.widths[name]
    return out


def build_report(packing: Packing | None, diagnostics: Sequence[Diagnostic]) -> str:
    lines = ["Control Store Packing Report", "============================", ""]
    errors = sum(1 for d in diagnostics if d.severity in (ERROR, FATAL))
    lines += [f"Status: {'FAILED' if errors else 'SUCCEEDED'}", f"Errors: {errors}", ""]
    if packing is not None:
        data = packing_json(packing, [])
        s = data["summary"]
        lines += [
            "Summary", "-------",
            f"Datapath bits: {s['datapath_bits']} of {DATAPATH_DEVICES * DEVICE_WIDTH}",
            "EXECUTE variants: " + ", ".join(f"{k}={v}" for k, v in s["execute_variants"].items()),
            f"Overlay groups: {s['overlay_groups']} "
            f"(select bits needed: {s['overlay_select_bits_needed']})",
            f"IR_SEQ as a single bit: {'feasible' if s['ir_seq_single_bit_feasible'] else 'not feasible'}",
            f"Verified address checks: {s['verified_addresses']}",
            "",
            "Overlay groups", "--------------",
        ]
        def face(bits):
            return ", ".join(
                f"[{b['bit']}{'..' + str(b['bit'] + b['width'] - 1) if b['width'] > 1 else ''}] "
                f"{b['signal']}" for b in bits)
        for g in data["overlay_groups"]:
            if "running_bits" in g:
                lines.append(f"{g['code']} (RUN = 0): {face(g['bits'])}")
                lines.append(f"{g['code']} (RUN = 1): {face(g['running_bits'])}")
            else:
                lines.append(f"{g['code']}: {face(g['bits'])}")
        lines.append(f"Non-EXECUTE group (wired): {data['non_execute_overlay_group']}")
        lines += ["", "EXECUTE variants", "----------------"]
        for ts, items in data["execute_variants"].items():
            for item in items:
                lines.append(f"{ts} v{item['variant']:02d}: group {item['overlay_group']}, "
                             f"{item['ir_values']} IR values, signals "
                             f"{', '.join(item['signals']) or 'none'}")
        lines += ["", "Datapath layout", "---------------"]
        for slot in data["datapath_layout"]:
            lines.append(f"bits {slot['offset']}..{slot['offset'] + slot['width'] - 1}: "
                         + ", ".join(slot["fields"]))
        lines += ["", "IR_SEQ decodes needed", "---------------------"]
        for k, v in data["ir_seq_needs"].items():
            lines.append(f"{k}: {', '.join(v) or 'none'}")
        lines.append("")
    if diagnostics:
        lines += ["Diagnostics", "-----------"]
        for d in sorted(diagnostics, key=lambda d: (SEVERITY_ORDER[d.severity], d.code)):
            lines.append(f"{d.severity} {d.code}" + (f" [{d.entry_id}]" if d.entry_id else "")
                         + f": {d.message}")
        lines.append("")
    return "\n".join(lines)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def write_images(packing: Packing, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, image in packing.images.items():
        if name.startswith("_"):
            continue
        write_text(directory / f"{name}.hex", "".join(f"{v:02X}\n" for v in image))


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACT_DIRECTORY)
    parser.add_argument("--packing-output", type=Path, default=DEFAULT_PACKING)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--images-output", type=Path, default=DEFAULT_IMAGES)
    return parser.parse_args(arguments)


def read_documents(directory: Path) -> dict[str, dict[str, Any]]:
    documents = {}
    for key, name in INPUT_FILES.items():
        path = directory / name
        try:
            documents[key] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PackingFailure(f"Cannot read {path}: {exc}") from exc
    return documents


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    packing_out = root / options.packing_output
    report_out = root / options.report_output
    images_out = root / options.images_output
    for path in (packing_out, report_out):
        if path.exists():
            path.unlink()
    if images_out.exists():
        for old in images_out.glob("*.hex"):
            old.unlink()

    try:
        documents = read_documents(root / options.artifacts)
    except PackingFailure as exc:
        diagnostics = [Diagnostic(FATAL, "PACKING_FAILURE", str(exc))]
        write_text(report_out, build_report(None, diagnostics))
        print(f"Control store packing\nStatus: FAILED\n{exc}")
        return 1

    model, diagnostics = build_model(documents)
    packing = None
    if model is not None:
        packing, more = pack(model)
        diagnostics += more
    failed = has_failures(diagnostics)
    if packing is not None and not failed:
        write_text(packing_out, json.dumps(packing_json(packing, diagnostics),
                                           indent=2, ensure_ascii=False) + "\n")
        write_images(packing, images_out)
    write_text(report_out, build_report(packing, diagnostics))
    print("Control store packing")
    print(f"Status: {'FAILED' if failed else 'SUCCEEDED'}")
    print(f"Diagnostics: {len(diagnostics)}")
    if not failed:
        print(f"Packing output: {packing_out}")
        print(f"Images: {images_out}")
    print(f"Report output: {report_out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
