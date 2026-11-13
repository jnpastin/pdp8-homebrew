"""Analyze equivalence, aliasing, reachability and input significance of
the promoted symbolic control words.

The analyzer reads the predicate-preserving symbolic control words and
partitions each execution case into legal concrete behavior without
enumerating the Cartesian product of its inputs:

1. Read and validate the four inputs. Any error stops here.
2. For each case, fix the names its base context pins, then split the
   case's guarded assignments into independent components: guards that
   share a free input, assign the same field, or are tied together by an
   input constraint belong to one component.
3. Partition each component with a decision tree that splits only on the
   names its undecided guards still compare, pruning regions that the
   input and timing constraints make unreachable. Each reachable leaf
   resolves the component's fields; leaves that fire the same assignments
   form one branch.
4. A case's complete control words are the product of its components'
   branch words. Identical components are shared across cases as
   component classes.
5. Derive input significance, aliases, unreachable assignments and
   regions, case overlaps and uncovered regions from the partitions.
6. Write the analysis (only when no errors were found) and the report.

See the tool README for the rules.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))

from predicates import (  # noqa: E402  (shared ROM-generation module)
    EXCLUSIVE_KINDS,
    MUTUAL_EXCLUSION,
    Expression,
    ExpressionError,
    ir_derivation_table,
    parse_expression,
    value_domains,
    walk,
)

# ---------------------------------------------------------------------------
# Paths and constants
# ---------------------------------------------------------------------------

DEFAULT_ARTIFACT_DIRECTORY = Path("rom/microcode/v1")
OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/control-word-equivalence-analyzer"
)
DEFAULT_ANALYSIS = OUTPUT_DIRECTORY / "control-word-equivalence.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "analysis-report.txt"


@dataclass(frozen=True)
class InputSpec:
    key: str
    file_name: str
    identity_key: str
    identity: str


INPUT_SPECS = (
    InputSpec(
        "symbolic",
        "symbolic-control-words.json",
        "artifact",
        "symbolic-control-words",
    ),
    InputSpec(
        "inputs",
        "control-input-schema.json",
        "specification_type",
        "control-input-schema",
    ),
    InputSpec(
        "words",
        "control-word-schema.json",
        "specification_type",
        "control-word-schema",
    ),
    InputSpec(
        "timing", "timing-constraints.json", "artifact", "timing-constraints"
    ),
)

ARTIFACT = "control-word-equivalence"
FORMAT_VERSION = 1
GENERATION_STAGE = "analysis"
REPRESENTATION = "factored"
ENCODED_ROLE = "encoded"

# A compared name whose domain has more values than this is not split.
MAX_DOMAIN_SIZE = 4096
# Largest number of combinations one cross-case join group may enumerate.
MAX_JOIN_COMBINATIONS = 200_000

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


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    entry_id: str | None = None
    field_name: str | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "entry_id": self.entry_id,
            "field_name": self.field_name,
        }


class AnalysisFailure(Exception):
    """An input could not be read; analysis cannot proceed."""


def has_failures(diagnostics: Sequence[Diagnostic]) -> bool:
    return any(item.severity in FAILURE_SEVERITIES for item in diagnostics)


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.entry_id or "",
        diagnostic.field_name or "",
        diagnostic.message,
    )


# ---------------------------------------------------------------------------
# Reading inputs
# ---------------------------------------------------------------------------


def resolve_from_repo(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_json(path: Path) -> dict[str, Any]:
    """Read a JSON object; every problem raises ``AnalysisFailure``."""

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise AnalysisFailure(f"Required input does not exist: {path}") from error
    except UnicodeDecodeError as error:
        raise AnalysisFailure(f"Input is not valid UTF-8: {path}") from error
    except OSError as error:
        raise AnalysisFailure(f"Unable to read input {path}: {error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise AnalysisFailure(
            f"Input is not valid JSON: {path}: line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from error
    if not isinstance(data, dict):
        raise AnalysisFailure(f"Input root must be a JSON object: {path}")
    return data


# ---------------------------------------------------------------------------
# Boxes
#
# A box is a region of the input space: a dict from name to the tuple of
# values the name may still take, in domain order. A name absent from the
# box takes its whole domain.
# ---------------------------------------------------------------------------

Box = dict[str, tuple[str, ...]]


def evaluate_box(
    expression: Expression, box: Box, full: dict[str, tuple[str, ...]]
) -> bool | None:
    """Evaluate over a box: True or False if the expression has that value
    everywhere in the box, None if it differs within it."""

    kind = expression[0]
    if kind == "const":
        return expression[1]
    if kind == "cmp":
        _, name, operator, literal = expression
        values = box.get(name, full[name])
        if literal not in values:
            result = False
        elif len(values) == 1:
            result = True
        else:
            return None
        return result if operator == "=" else not result
    if kind == "not":
        value = evaluate_box(expression[1], box, full)
        return None if value is None else not value
    left = evaluate_box(expression[1], box, full)
    right = evaluate_box(expression[2], box, full)
    if kind == "and":
        if left is False or right is False:
            return False
        return True if left and right else None
    if left or right:
        return True
    return False if left is False and right is False else None


def compared_literals(expression: Expression) -> list[tuple[str, str]]:
    return [
        (node[1], node[3]) for node in walk(expression) if node[0] == "cmp"
    ]


def ordered_unique(items: Iterable[Any]) -> list[Any]:
    return list(dict.fromkeys(items))


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Constraint:
    """One documented restriction on reachable input combinations.

    ``kind`` is ``exactly_one``, ``at_most_one``, ``mutual_exclusion``
    (from a field's "Mutually exclusive with X." constraint), ``timing``
    (a timing constraint's context with its requirement violated), or
    ``derivation`` (the combinations of IR-derived inputs that some IR value
    produces; ``masks[i][value]`` is the bit set of table rows in which
    ``names[i]`` has ``value``).
    """

    id: str
    kind: str
    names: tuple[str, ...]
    source: dict[str, Any] | None
    violation: Expression | None = None
    masks: tuple = field(default=(), compare=False)
    all_rows: int = field(default=0, compare=False)
    rows: tuple = field(default=(), compare=False)

    def violated(self, box: Box, full: dict[str, tuple[str, ...]]) -> bool:
        """Return whether every point of the box violates the constraint."""

        if self.kind == "derivation":
            rows = self.all_rows
            for index, name in enumerate(self.names):
                values = box.get(name)
                if values is None:
                    continue
                allowed = 0
                for value in values:
                    allowed |= self.masks[index].get(value, 0)
                rows &= allowed
                if not rows:
                    return True
            return False
        if self.kind == "timing":
            return evaluate_box(self.violation, box, full) is True
        asserted = sum(box.get(name, full[name]) == ("1",) for name in self.names)
        if asserted >= 2:
            return True
        if self.kind == "exactly_one":
            return all("1" not in box.get(name, full[name]) for name in self.names)
        return False

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "inputs": list(self.names),
            "source": self.source,
        }


def table_constraint(
    identifier: str,
    names: Sequence[str],
    rows: Sequence[tuple[str, ...]],
    source: Any = None,
) -> Constraint:
    """Build a ``derivation`` constraint allowing exactly ``rows``."""

    masks = []
    for index in range(len(names)):
        by_value: dict[str, int] = {}
        for row_number, row in enumerate(rows):
            by_value[row[index]] = by_value.get(row[index], 0) | (1 << row_number)
        masks.append(by_value)
    return Constraint(
        identifier,
        "derivation",
        tuple(names),
        source,
        masks=tuple(masks),
        all_rows=(1 << len(rows)) - 1,
        rows=tuple(rows),
    )


def rows_of(constraint: Constraint) -> list[tuple[str, ...]]:
    """Return the rows of a ``derivation`` constraint, in order."""

    return list(constraint.rows)


def split_derivation(
    constraint: Constraint,
    box: Box,
    full: dict[str, tuple[str, ...]],
    keep: set[str] | None = None,
) -> tuple[Box | None, list[Constraint]]:
    """Specialize a ``derivation`` constraint to a case's base box.

    Returns the base box tightened to the values the consistent rows allow
    (None when no row is consistent), and the constraint split into
    independent groups of the names that still vary. Groups come from
    pairwise dependence and are accepted only when their product reproduces
    the consistent rows exactly; otherwise one group holds every varying
    name. With ``keep``, the groups cover only those names: the others are
    projected out, since no undecided condition of the case compares them.
    """

    names = constraint.names
    rows = [
        row
        for row in rows_of(constraint)
        if all(row[i] in box.get(n, full[n]) for i, n in enumerate(names))
    ]
    if not rows:
        return None, []
    tight = dict(box)
    for index, name in enumerate(names):
        present = {row[index] for row in rows}
        allowed = tuple(v for v in box.get(name, full[name]) if v in present)
        if len(allowed) < len(box.get(name, full[name])):
            tight[name] = allowed
    varying = [
        i
        for i, n in enumerate(names)
        if len(tight.get(n, full[n])) > 1 and (keep is None or n in keep)
    ]

    links = UnionFind()
    for i in varying:
        links.find(i)
    for position, i in enumerate(varying):
        for j in varying[position + 1 :]:
            pairs = {(row[i], row[j]) for row in rows}
            if len(pairs) < len(tight.get(names[i], full[names[i]])) * len(
                tight.get(names[j], full[names[j]])
            ):
                links.union(i, j)
    groups: dict[int, list[int]] = {}
    for i in varying:
        groups.setdefault(links.find(i), []).append(i)
    projections = [
        ordered_unique(tuple(row[i] for i in group) for row in rows)
        for group in groups.values()
    ]
    whole = {tuple(row[i] for i in varying) for row in rows}
    product = 1
    for projection in projections:
        product *= len(projection)
    if product != len(whole):
        groups = {0: varying}
        projections = [
            ordered_unique(tuple(row[i] for i in varying) for row in rows)
        ]
    return tight, [
        table_constraint(
            constraint.id, [names[i] for i in group], projection, constraint.source
        )
        for group, projection in zip(groups.values(), projections)
    ]


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Guard:
    """One guarded assignment of a symbolic case."""

    position: int
    field: str
    token: tuple[str, str]  # ("value", encoding) or ("input", input name)
    expression: Expression
    item: dict[str, Any]


@dataclass
class CaseModel:
    id: str
    position: int
    source: Any
    base_text: str
    base_box: Box | None  # None: the base context is contradictory
    defaults: dict[str, str]
    guards: list[Guard]


@dataclass
class Model:
    version: str
    fields: list[str]  # encoded control-word fields, in schema order
    input_names: list[str]  # control inputs, in schema order
    input_fields: dict[str, dict[str, Any]]
    word_field_names: set[str]
    full: dict[str, tuple[str, ...]]
    constraints: list[Constraint]
    cases: list[CaseModel]
    notes: list[Diagnostic] = field(default_factory=list)


def enumerate_domain(domain: Any) -> tuple[str, ...] | None:
    """List every value of a domain, or None when it is too large."""

    if domain.width is None:
        return tuple(domain.values)
    if 2**domain.width > MAX_DOMAIN_SIZE:
        return None
    values = (format(i, f"0{domain.width}b") for i in range(2**domain.width))
    return tuple(value for value in values if domain.contains(value))


def build_constraints(
    input_fields: dict[str, dict[str, Any]],
    global_constraints: list[dict[str, Any]],
    timing: list[tuple[str, Expression, Any]],
) -> list[Constraint]:
    constraints: list[Constraint] = []
    for item in global_constraints:
        if item.get("kind") in EXCLUSIVE_KINDS:
            names = tuple(item["inputs"])
            constraints.append(
                Constraint(
                    f"{item['kind']}:{'+'.join(names)}",
                    item["kind"],
                    names,
                    item.get("source"),
                )
            )
    seen: set[tuple[str, str]] = set()
    for name, entry in input_fields.items():
        for item in entry.get("constraints", []):
            text = item.get("text")
            match = MUTUAL_EXCLUSION.fullmatch(
                text.strip() if isinstance(text, str) else ""
            )
            if not match:
                continue
            other = match.group(1).strip()
            pair = tuple(sorted((name, other)))
            if other == name or pair in seen:
                continue
            seen.add(pair)
            constraints.append(
                Constraint(
                    f"mutual_exclusion:{pair[0]}+{pair[1]}",
                    "mutual_exclusion",
                    pair,
                    item.get("source"),
                )
            )
    for identifier, violation, source in timing:
        names = tuple(
            ordered_unique(name for name, _ in compared_literals(violation))
        )
        constraints.append(
            Constraint(identifier, "timing", names, source, violation)
        )
    return constraints


def conjunctive_box(
    expression: Expression | None, full: dict[str, tuple[str, ...]]
) -> tuple[bool, Box | None]:
    """Turn a conjunction of comparisons into a box.

    Returns ``(supported, box)``; ``box`` is None when the conjunction is
    contradictory.
    """

    box: Box = {}
    terms = []
    stack = [expression] if expression is not None else []
    while stack:
        node = stack.pop()
        if node[0] == "and":
            stack += [node[2], node[1]]
        elif node[0] == "cmp":
            terms.append(node)
        elif node == ("const", True):
            continue
        else:
            return False, None
    for _, name, operator, literal in terms:
        current = box.get(name, full[name])
        allowed = tuple(
            value
            for value in current
            if (value == literal) == (operator == "=")
        )
        if not allowed:
            return True, None
        box[name] = allowed
    return True, box


class Validator:
    """Validates the inputs and builds the model."""

    def __init__(self) -> None:
        self.diagnostics: list[Diagnostic] = []

    def error(
        self,
        code: str,
        message: str,
        entry_id: str | None = None,
        field_name: str | None = None,
    ) -> None:
        self.diagnostics.append(
            Diagnostic(ERROR, code, message, entry_id, field_name)
        )

    def build(self, documents: dict[str, dict[str, Any]]) -> Model | None:
        words_document = documents["words"]
        version = words_document.get("control_design_version")
        for spec in INPUT_SPECS:
            data = documents[spec.key]
            if data.get(spec.identity_key) != spec.identity:
                self.error(
                    "UNEXPECTED_ARTIFACT_TYPE",
                    f"Expected {spec.identity_key} {spec.identity!r}.",
                    field_name=spec.file_name,
                )
            if data.get("control_design_version") != version:
                self.error(
                    "CONTROL_DESIGN_VERSION_MISMATCH",
                    "control_design_version differs from "
                    "control-word-schema.json.",
                    field_name=spec.file_name,
                )

        input_fields = self.indexed(
            documents["inputs"].get("fields"), "control-input-schema.json"
        )
        word_fields = self.indexed(
            words_document.get("fields"), "control-word-schema.json"
        )
        encoded = {
            name: entry
            for name, entry in word_fields.items()
            if entry.get("control_word_role") == ENCODED_ROLE
        }
        global_constraints = documents["inputs"].get("constraints", [])
        if not isinstance(global_constraints, list) or not all(
            isinstance(item, dict)
            and (
                item.get("kind") not in EXCLUSIVE_KINDS
                or (
                    isinstance(item.get("inputs"), list)
                    and all(isinstance(n, str) for n in item["inputs"])
                )
            )
            for item in global_constraints
        ):
            self.error(
                "INVALID_CONTROL_INPUT_SCHEMA",
                "constraints must be an array of objects whose exclusive "
                "kinds list their inputs.",
                field_name="constraints",
            )
            global_constraints = []
        if self.diagnostics:
            return None

        try:
            domains = value_domains(input_fields, encoded)
        except (KeyError, TypeError) as error:
            self.error(
                "INVALID_CONTROL_INPUT_SCHEMA",
                f"Input or word field is malformed: {error}.",
            )
            return None
        full: dict[str, tuple[str, ...]] = {}
        oversized: set[str] = set()
        for name, domain in domains.items():
            values = enumerate_domain(domain)
            if values is None:
                oversized.add(name)
            else:
                full[name] = values

        timing = []
        for position, item in enumerate(
            documents["timing"].get("constraints") or []
        ):
            identifier = (
                item.get("id") if isinstance(item, dict) else None
            ) or f"timing constraint {position}"
            context = self.expression(
                item.get("context") if isinstance(item, dict) else None,
                domains,
                oversized,
                identifier,
                "context",
            )
            requirement = self.expression(
                item.get("requirement") if isinstance(item, dict) else None,
                domains,
                oversized,
                identifier,
                "requirement",
            )
            if context is not None and requirement is not None:
                timing.append(
                    (
                        identifier,
                        ("and", context, ("not", requirement)),
                        item.get("source"),
                    )
                )

        cases = self.cases(
            documents["symbolic"], encoded, input_fields, domains, oversized, full
        )
        if self.diagnostics:
            return None
        constraints = build_constraints(input_fields, global_constraints, timing)
        notes: list[Diagnostic] = []
        derivation = self.derivation_constraint(input_fields, cases, timing, notes)
        if derivation is not None:
            constraints.append(derivation)
        return Model(
            version=version,
            fields=list(encoded),
            input_names=list(input_fields),
            input_fields=input_fields,
            word_field_names=set(encoded),
            full=full,
            constraints=constraints,
            cases=cases,
            notes=notes,
        )

    def derivation_constraint(
        self,
        input_fields: dict[str, dict[str, Any]],
        cases: list[CaseModel],
        timing: list[tuple[str, Expression, Any]],
        notes: list[Diagnostic],
    ) -> Constraint | None:
        """Relate the compared IR-derived inputs through their derivations.

        Only inputs that some condition compares take part; the others do
        not affect reachability.
        """

        try:
            table, problems = ir_derivation_table(input_fields)
        except (KeyError, TypeError, ValueError) as error:
            table, problems = {}, [("", f"Derivations are malformed: {error}.")]
        for name, message in problems:
            notes.append(
                Diagnostic(
                    WARNING, "IR_DERIVATION_UNUSABLE", message, field_name=name or None
                )
            )
        expressions = [parse_or_true(case.base_text) for case in cases]
        expressions += [g.expression for case in cases for g in case.guards]
        expressions += [violation for _, violation, _ in timing]
        compared = ordered_unique(
            name for e in expressions for name, _ in compared_literals(e)
        )
        names = [name for name in compared if name in table]
        if not names:
            return None
        rows = ordered_unique(
            tuple(table[name][ir] for name in names)
            for ir in range(len(table[names[0]]))
        )
        return table_constraint(
            "ir-derivation",
            names,
            rows,
            {"path": "docs/04-control/10-control-input-definitions/02-ir-derived-fields.md"},
        )

    def indexed(self, entries: Any, label: str) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        if not isinstance(entries, list):
            self.error("INVALID_SPECIFICATION", f"{label} must contain a fields array.")
            return index
        for position, entry in enumerate(entries):
            name = entry.get("name") if isinstance(entry, dict) else None
            if not isinstance(name, str) or not name:
                self.error(
                    "INVALID_SPECIFICATION",
                    f"{label} fields entry {position} has no name.",
                )
            elif name in index:
                self.error(
                    "INVALID_SPECIFICATION",
                    f"{label} contains duplicate field {name}.",
                    name,
                )
            else:
                index[name] = entry
        return index

    def expression(
        self,
        text: Any,
        domains: dict[str, Any],
        oversized: set[str],
        entry_id: str,
        field_name: str,
    ) -> Expression | None:
        """Parse an expression and check every name and value it uses."""

        if not isinstance(text, str) or not text.strip():
            self.error(
                "INVALID_EXPRESSION",
                "Expression must be a nonempty string.",
                entry_id,
                field_name,
            )
            return None
        if text.strip() == "always":
            return ("const", True)
        try:
            expression = parse_expression(text)
        except ExpressionError as error:
            self.error(
                "INVALID_EXPRESSION", f"{error} In {text!r}.", entry_id, field_name
            )
            return None
        valid = True
        for node in walk(expression):
            if node[0] == "sel":
                self.error(
                    "INVALID_EXPRESSION",
                    f"'{node[1]} is selected' must already be resolved in the "
                    "symbolic artifact.",
                    entry_id,
                    field_name,
                )
                valid = False
        for name, literal in ordered_unique(compared_literals(expression)):
            if name not in domains:
                self.error(
                    "UNKNOWN_NAME",
                    f"{name} is not a control input, encoded control-word "
                    "field, MS or TS.",
                    entry_id,
                    field_name,
                )
                valid = False
            elif name in oversized:
                self.error(
                    "DOMAIN_TOO_LARGE",
                    f"{name} has more than {MAX_DOMAIN_SIZE} values and "
                    "cannot be partitioned.",
                    entry_id,
                    field_name,
                )
                valid = False
            elif not domains[name].contains(literal):
                self.error(
                    "INVALID_COMPARED_VALUE",
                    f"{literal} is not a value of {name}, which takes "
                    f"{domains[name].describe()}.",
                    entry_id,
                    field_name,
                )
                valid = False
        return expression if valid else None

    def cases(
        self,
        symbolic: dict[str, Any],
        encoded: dict[str, dict[str, Any]],
        input_fields: dict[str, dict[str, Any]],
        domains: dict[str, Any],
        oversized: set[str],
        full: dict[str, tuple[str, ...]],
    ) -> list[CaseModel]:
        entries = symbolic.get("cases")
        if not isinstance(entries, list):
            self.error(
                "INVALID_SYMBOLIC_CONTROL_WORDS",
                "symbolic-control-words.json must contain a cases array.",
            )
            return []
        cases: list[CaseModel] = []
        seen: set[str] = set()
        for position, entry in enumerate(entries):
            identifier = (
                entry.get("execution_case_id") if isinstance(entry, dict) else None
            )
            if not isinstance(identifier, str) or not identifier:
                self.error(
                    "INVALID_SYMBOLIC_CONTROL_WORDS",
                    f"Case {position} has no execution_case_id.",
                )
                continue
            if identifier in seen:
                self.error(
                    "INVALID_SYMBOLIC_CONTROL_WORDS",
                    "Duplicate execution_case_id.",
                    identifier,
                )
                continue
            seen.add(identifier)
            case = self.case(
                entry, identifier, position, encoded, input_fields, domains,
                oversized, full,
            )
            if case is not None:
                cases.append(case)
        return cases

    def case(
        self,
        entry: dict[str, Any],
        identifier: str,
        position: int,
        encoded: dict[str, dict[str, Any]],
        input_fields: dict[str, dict[str, Any]],
        domains: dict[str, Any],
        oversized: set[str],
        full: dict[str, tuple[str, ...]],
    ) -> CaseModel | None:
        before = len(self.diagnostics)
        defaults = entry.get("defaults")
        assignments = entry.get("field_assignments")
        if not isinstance(defaults, dict) or not isinstance(assignments, dict):
            self.error(
                "INVALID_SYMBOLIC_CONTROL_WORDS",
                "Case must have defaults and field_assignments objects.",
                identifier,
            )
            return None
        for name in encoded:
            if name not in defaults:
                self.error(
                    "MISSING_CONTROL_FIELD",
                    "Encoded field has no default.",
                    identifier,
                    name,
                )
            elif not domains[name].contains(str(defaults[name])):
                self.error(
                    "INVALID_FIELD_VALUE",
                    f"Default {defaults[name]!r} is not a value of {name}.",
                    identifier,
                    name,
                )
        for name in list(defaults) + list(assignments):
            if name not in encoded:
                self.error(
                    "UNKNOWN_CONTROL_FIELD",
                    f"{name} is not an encoded control-word field.",
                    identifier,
                    name,
                )

        base_text = entry.get("base_context")
        base = self.expression(
            base_text, domains, oversized, identifier, "base_context"
        )
        guards: list[Guard] = []
        for name in encoded:
            items = assignments.get(name, [])
            if not isinstance(items, list):
                self.error(
                    "INVALID_SYMBOLIC_CONTROL_WORDS",
                    "Field assignments must be an array.",
                    identifier,
                    name,
                )
                continue
            for item in items:
                guard = self.guard(
                    item, name, len(guards), encoded[name], input_fields,
                    domains, oversized, identifier,
                )
                if guard is not None:
                    guards.append(guard)

        if len(self.diagnostics) > before or base is None:
            return None
        supported, box = conjunctive_box(base, full)
        if not supported:
            self.error(
                "UNSUPPORTED_BASE_CONTEXT",
                "Base context must be a conjunction of comparisons.",
                identifier,
                "base_context",
            )
            return None
        return CaseModel(
            identifier, position, entry.get("source"), base_text, box,
            {name: str(defaults[name]) for name in encoded}, guards,
        )

    def guard(
        self,
        item: Any,
        field_name: str,
        position: int,
        word_field: dict[str, Any],
        input_fields: dict[str, dict[str, Any]],
        domains: dict[str, Any],
        oversized: set[str],
        identifier: str,
    ) -> Guard | None:
        if not isinstance(item, dict):
            self.error(
                "INVALID_SYMBOLIC_CONTROL_WORDS",
                "Assignment must be an object.",
                identifier,
                field_name,
            )
            return None
        expression = self.expression(
            item.get("when"), domains, oversized, identifier, field_name
        )
        if "value" in item:
            value = item["value"]
            if not isinstance(value, str) or not domains[field_name].contains(value):
                self.error(
                    "INVALID_FIELD_VALUE",
                    f"{value!r} is not a value of {field_name}.",
                    identifier,
                    field_name,
                )
                return None
            token = ("value", value)
        elif "value_from_input" in item:
            source = item["value_from_input"]
            if source not in input_fields:
                self.error(
                    "UNKNOWN_SUPPLYING_INPUT",
                    f"{source!r} is not a control input.",
                    identifier,
                    field_name,
                )
                return None
            if input_fields[source].get("width") != word_field.get("width"):
                self.error(
                    "SUPPLYING_INPUT_WIDTH_MISMATCH",
                    f"{source} is {input_fields[source].get('width')} bits; "
                    f"{field_name} is {word_field.get('width')}.",
                    identifier,
                    field_name,
                )
                return None
            token = ("input", source)
        else:
            self.error(
                "INVALID_SYMBOLIC_CONTROL_WORDS",
                "Assignment has neither value nor value_from_input.",
                identifier,
                field_name,
            )
            return None
        if expression is None:
            return None
        return Guard(position, field_name, token, expression, item)


# ---------------------------------------------------------------------------
# Partitioning
# ---------------------------------------------------------------------------


@dataclass
class Partition:
    """The leaves of one decision tree."""

    leaves: list[tuple[Box, list[bool]]] = field(default_factory=list)
    pruned: list[tuple[Box, tuple[str, ...]]] = field(default_factory=list)


class Engine:
    """Decision-tree partitioning and satisfiability over boxes."""

    def __init__(self, full: dict[str, tuple[str, ...]]) -> None:
        self.full = full

    def values(self, box: Box, name: str) -> tuple[str, ...]:
        return box.get(name, self.full[name])

    def first_violations(
        self, box: Box, constraints: Sequence[Constraint]
    ) -> tuple[str, ...]:
        return tuple(c.id for c in constraints if c.violated(box, self.full))

    def satisfiable(self, box: Box, constraints: Sequence[Constraint]) -> bool:
        """Return whether some point of the box violates no constraint.

        Names constrained only by ``derivation`` tables are not enumerated:
        a table's check is exact for a whole box (some allowed row lies in
        it), so once every other constrained name is fixed the remaining
        table names are satisfiable exactly when no table rejects the box.
        """

        names = ordered_unique(
            name
            for constraint in constraints
            if constraint.kind != "derivation"
            for name in constraint.names
            if len(self.values(box, name)) > 1
        )

        def search(position: int, current: Box) -> bool:
            if any(c.violated(current, self.full) for c in constraints):
                return False
            if position == len(names):
                return True
            name = names[position]
            for value in self.values(current, name):
                trial = dict(current)
                trial[name] = (value,)
                if search(position + 1, trial):
                    return True
            return False

        return search(0, box)

    def core(
        self, box: Box, constraints: Sequence[Constraint]
    ) -> tuple[str, ...]:
        """Name the constraints that make a box unreachable.

        Those that alone exclude the box; otherwise every constraint that
        compares a name the box restricts.
        """

        alone = tuple(
            c.id for c in constraints if not self.satisfiable(box, [c])
        )
        if alone:
            return alone
        return tuple(
            c.id for c in constraints if any(name in box for name in c.names)
        )

    def partition(
        self,
        guards: Sequence[Expression],
        box: Box,
        constraints: Sequence[Constraint],
        order: Sequence[str],
        required: Sequence[int] = (),
    ) -> Partition:
        """Split the box until every guard is decided.

        Regions where a ``required`` guard is false are dropped silently
        (they lie outside the region of interest). Regions that the
        constraints exclude are kept as pruned, with the excluding
        constraints.
        """

        literals: dict[str, set[str]] = {}
        names_of: list[list[str]] = []
        for guard in guards:
            pairs = compared_literals(guard)
            names_of.append(ordered_unique(name for name, _ in pairs))
            for name, literal in pairs:
                literals.setdefault(name, set()).add(literal)
        rank = {name: index for index, name in enumerate(order)}
        required_set = set(required)
        constraints_on: dict[str, list[Constraint]] = {}
        for constraint in constraints:
            for name in constraint.names:
                constraints_on.setdefault(name, []).append(constraint)
        result = Partition()

        def visit(
            current: Box,
            decided: list[bool | None],
            undecided: list[int],
            checks: Sequence[Constraint],
        ) -> None:
            # Shrinking a box only decides guards and violates constraints;
            # so only undecided guards, and only constraints on the name
            # just split, need re-evaluating.
            violated = tuple(c.id for c in checks if c.violated(current, self.full))
            if violated:
                result.pruned.append((current, violated))
                return
            still_open = []
            for index in undecided:
                value = evaluate_box(guards[index], current, self.full)
                if value is False and index in required_set:
                    return
                decided[index] = value
                if value is None:
                    still_open.append(index)
            # A name can be split usefully only while it still has more
            # than one value and some of them are compared literals.
            open_names = [
                name
                for index in still_open
                for name in names_of[index]
                if len(self.values(current, name)) > 1
                and any(v in literals[name] for v in self.values(current, name))
            ]
            if not open_names:
                if not self.satisfiable(current, constraints):
                    result.pruned.append(
                        (current, self.core(current, constraints))
                    )
                    return
                result.leaves.append((current, [bool(v) for v in decided]))
                return
            name = min(open_names, key=lambda n: rank.get(n, len(rank)))
            values = self.values(current, name)
            parts = [(value,) for value in values if value in literals[name]]
            rest = tuple(value for value in values if value not in literals[name])
            if rest:
                parts.append(rest)
            for part in parts:
                child = dict(current)
                child[name] = part
                visit(child, list(decided), still_open, constraints_on.get(name, ()))

        visit(dict(box), [None] * len(guards), list(range(len(guards))), constraints)
        return result

    def jointly_reachable(
        self,
        box: Box,
        name: str,
        first: tuple[str, ...],
        second: tuple[str, ...],
        constraints: Sequence[Constraint],
    ) -> bool:
        """Return whether some point of the box (ignoring ``name``) is
        reachable with ``name`` in ``first`` and also with it in
        ``second``."""

        plain = [c for c in constraints if c.kind != "derivation"]
        tables = [c for c in constraints if c.kind == "derivation"]
        names = ordered_unique(
            other
            for constraint in plain
            for other in constraint.names
            if other != name and len(self.values(box, other)) > 1
        )

        def allowed(current: Box, values: tuple[str, ...]) -> tuple[str, ...]:
            return tuple(
                value
                for value in values
                if not any(
                    c.violated({**current, name: (value,)}, self.full)
                    for c in plain
                )
            )

        def tables_agree(
            current: Box, side_a: tuple[str, ...], side_b: tuple[str, ...]
        ) -> bool:
            """Some rows on each side agree on every name but ``name``."""

            for table in tables:
                if name not in table.names:
                    if table.violated(current, self.full):
                        return False
                    continue
                index = table.names.index(name)
                projections = []
                for side in (side_a, side_b):
                    projections.append(
                        {
                            row[:index] + row[index + 1 :]
                            for row in table.rows
                            if row[index] in side
                            and all(
                                row[i] in self.values(current, n)
                                for i, n in enumerate(table.names)
                                if i != index
                            )
                        }
                    )
                if not projections[0] & projections[1]:
                    return False
            return True

        def search(position: int, current: Box) -> bool:
            widened = {**current, name: first + second}
            if any(c.violated(widened, self.full) for c in constraints):
                return False
            if position == len(names):
                side_a = allowed(current, first)
                side_b = allowed(current, second)
                return bool(side_a and side_b) and tables_agree(
                    current, side_a, side_b
                )
            other = names[position]
            for value in self.values(current, other):
                if search(position + 1, {**current, other: (value,)}):
                    return True
            return False

        return search(0, dict(box))


def merge_boxes(
    boxes: Sequence[Box], names: Sequence[str], full: dict[str, tuple[str, ...]]
) -> list[tuple[tuple[str, ...], ...]]:
    """Merge boxes that differ in one name, until none do.

    Boxes are projected onto ``names``; the result keeps first-appearance
    order and covers exactly the union of the projections.
    """

    current = ordered_unique(
        tuple(box.get(name, full[name]) for name in names) for box in boxes
    )
    changed = True
    while changed:
        changed = False
        for index, name in enumerate(names):
            groups: dict[tuple, list[tuple]] = {}
            for item in current:
                key = item[:index] + item[index + 1 :]
                groups.setdefault(key, []).append(item)
            if all(len(group) == 1 for group in groups.values()):
                continue
            merged = []
            for key, group in groups.items():
                union = set().union(*(item[index] for item in group))
                values = tuple(v for v in full[name] if v in union)
                merged.append(key[:index] + (values,) + key[index:])
            current = ordered_unique(merged)
            changed = True
    return current


def render_box(
    projection: Sequence[tuple[str, ...]],
    names: Sequence[str],
    full: dict[str, tuple[str, ...]],
) -> str:
    terms = []
    for name, values in zip(names, projection):
        domain = full[name]
        if values == domain:
            continue
        if len(values) == 1:
            terms.append(f"{name} = {values[0]}")
        elif len(domain) - len(values) == 1:
            missing = next(v for v in domain if v not in values)
            terms.append(f"{name} != {missing}")
        else:
            terms.append(
                "(" + " OR ".join(f"{name} = {v}" for v in values) + ")"
            )
    return " AND ".join(terms) if terms else "always"


def render_region(
    boxes: Sequence[Box], names: Sequence[str], full: dict[str, tuple[str, ...]]
) -> str:
    return render_merged(merge_boxes(boxes, names, full), names, full)


def render_merged(
    merged: Sequence[tuple[tuple[str, ...], ...]],
    names: Sequence[str],
    full: dict[str, tuple[str, ...]],
) -> str:
    texts = [render_box(item, names, full) for item in merged]
    if "always" in texts:
        return "always"
    if len(texts) == 1:
        return texts[0]
    return " OR ".join(f"({text})" if " AND " in text else text for text in texts)


# ---------------------------------------------------------------------------
# Case analysis
# ---------------------------------------------------------------------------


def token_json(token: tuple[str, str]) -> Any:
    return token[1] if token[0] == "value" else {"from_input": token[1]}


@dataclass
class Branch:
    """The regions of a component that resolve to one partial word.

    ``fired_sets`` lists each distinct set of firing guard positions that
    produces the word; more than one means different assignments alias.
    """

    word: tuple[tuple[str, str], ...]  # token per component field
    fired_sets: list[tuple[int, ...]]
    boxes: list[Box]
    # The union of ``boxes``, merged and projected onto the component names.
    merged: list[tuple[tuple[str, ...], ...]] = field(default_factory=list)


@dataclass
class Component:
    fields: list[str]
    names: list[str]
    guards: list[Guard]
    constraints: list[Constraint]
    branches: list[Branch]
    pruned: list[tuple[Box, tuple[str, ...]]]
    never_fired: list[Guard]


@dataclass
class CaseResult:
    case: CaseModel
    reachable: bool
    unreachable_reason: tuple[str, ...]
    components: list[Component] = field(default_factory=list)
    significant: list[str] = field(default_factory=list)
    jointly_significant: list[str] = field(default_factory=list)
    box: Box | None = None  # base box tightened by the IR derivations
    referenced: list[str] = field(default_factory=list)
    conflicts: list[Diagnostic] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        count = 1
        for component in self.components:
            count *= len(component.branches)
        return count if self.reachable else 0


class UnionFind:
    def __init__(self) -> None:
        self.parent: dict[Any, Any] = {}

    def find(self, item: Any) -> Any:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: Any, second: Any) -> None:
        self.parent[self.find(first)] = self.find(second)


def free_names(expression: Expression, box: Box, full: dict) -> list[str]:
    return ordered_unique(
        name
        for name, _ in compared_literals(expression)
        if len(box.get(name, full[name])) > 1
    )


def analyze_case(model: Model, engine: Engine, case: CaseModel) -> CaseResult:
    full = model.full
    referenced = ordered_unique(
        [name for name, _ in compared_literals(parse_or_true(case.base_text))]
        + [
            name
            for guard in case.guards
            for name, _ in compared_literals(guard.expression)
        ]
    )
    if case.base_box is None:
        return CaseResult(case, False, ("base context is contradictory",), referenced=referenced)
    if not engine.satisfiable(case.base_box, model.constraints):
        return CaseResult(
            case, False, engine.core(case.base_box, model.constraints),
            referenced=referenced,
        )

    # Specialize the IR-derivation constraint to this case: tighten the
    # base box with the values it implies, and split it into independent
    # groups so unrelated decode bits stay in separate components.
    original = case
    box = case.base_box
    case_constraints: list[Constraint] = []
    for constraint in model.constraints:
        if constraint.kind != "derivation":
            case_constraints.append(constraint)
            continue
        tight, _ = split_derivation(constraint, box, full)
        # Never None: the case was found satisfiable above. Only names
        # that some still-undecided condition compares stay constrained.
        undecided = [parse_or_true(case.base_text)] + [
            g.expression for g in case.guards
        ]
        relevant = {
            name
            for expression in undecided
            if evaluate_box(expression, tight, full) is None
            for name in free_names(expression, tight, full)
        }
        box, groups = split_derivation(constraint, tight, full, keep=relevant)
        case_constraints += groups
    case = replace(case, base_box=box)
    links = UnionFind()
    guard_names = {g.position: free_names(g.expression, box, full) for g in case.guards}
    for guard in case.guards:
        links.union(("guard", guard.position), ("field", guard.field))
        for name in guard_names[guard.position]:
            links.union(("guard", guard.position), ("name", name))
    for constraint in case_constraints:
        names = [n for n in constraint.names if len(box.get(n, full[n])) > 1]
        for first, second in zip(names, names[1:]):
            links.union(("name", first), ("name", second))

    grouped: dict[Any, list[Guard]] = {}
    for guard in case.guards:
        grouped.setdefault(links.find(("guard", guard.position)), []).append(guard)

    result = CaseResult(original, True, (), referenced=referenced, box=box)
    significant: set[str] = set()
    for root, guards in grouped.items():
        names = ordered_unique(n for g in guards for n in guard_names[g.position])
        constraints = [
            c
            for c in case_constraints
            if any(
                len(box.get(n, full[n])) > 1 and links.find(("name", n)) == root
                for n in c.names
            )
        ]
        constraint_names = ordered_unique(
            n for c in constraints for n in c.names if len(box.get(n, full[n])) > 1
        )
        component = partition_component(
            model, engine, case, guards, names, constraints, constraint_names, result
        )
        result.components.append(component)
        alone = component_significance(engine, case, component, component.names)
        joint = joint_significance(engine, case, component, alone)
        significant |= alone | set(joint)
        result.jointly_significant += [n for n in joint if n not in alone]
    result.significant = [n for n in referenced if n in significant]
    result.jointly_significant = [
        n for n in referenced if n in result.jointly_significant
    ]
    return result


def parse_or_true(text: str) -> Expression:
    return ("const", True) if text.strip() == "always" else parse_expression(text)


def partition_component(
    model: Model,
    engine: Engine,
    case: CaseModel,
    guards: list[Guard],
    names: list[str],
    constraints: list[Constraint],
    constraint_names: list[str],
    result: CaseResult,
) -> Component:
    order = names + [n for n in constraint_names if n not in names]
    partition = engine.partition(
        [g.expression for g in guards], case.base_box, constraints, order
    )
    fields = ordered_unique(g.field for g in guards)
    fields = [f for f in model.fields if f in fields]
    branches: dict[tuple, Branch] = {}
    words_by_fired: dict[tuple[int, ...], tuple] = {}
    fired_any: set[int] = set()
    conflicted: set[str] = set()
    for leaf_box, decided in partition.leaves:
        fired = tuple(g.position for g, on in zip(guards, decided) if on)
        fired_any.update(fired)
        if fired in words_by_fired:
            branches[words_by_fired[fired]].boxes.append(leaf_box)
            continue
        word = []
        for name in fields:
            tokens = ordered_unique(
                g.token for g, on in zip(guards, decided) if on and g.field == name
            )
            if len(tokens) > 1 and name not in conflicted:
                conflicted.add(name)
                region = render_box(
                    tuple(leaf_box.get(n, model.full[n]) for n in order),
                    order,
                    model.full,
                )
                result.conflicts.append(
                    Diagnostic(
                        ERROR,
                        "CONFLICTING_ASSIGNMENTS",
                        f"{name} receives "
                        + ", ".join(str(token_json(t)) for t in tokens)
                        + f" when {region}.",
                        case.id,
                        name,
                    )
                )
            word.append(tokens[0] if tokens else ("value", case.defaults[name]))
        word = tuple(word)
        words_by_fired[fired] = word
        if word in branches:
            branches[word].fired_sets.append(fired)
            branches[word].boxes.append(leaf_box)
        else:
            branches[word] = Branch(word, [fired], [leaf_box])
    for branch in branches.values():
        branch.merged = merge_boxes(branch.boxes, order, model.full)
    return Component(
        fields=fields,
        names=order,
        guards=guards,
        constraints=constraints,
        branches=list(branches.values()),
        pruned=partition.pruned,
        never_fired=[g for g in guards if g.position not in fired_any],
    )


def component_significance(
    engine: Engine, case: CaseModel, component: Component, order: list[str]
) -> set[str]:
    """Return the names whose change alone changes some field's value.

    A word changes exactly when some field changes, so each field is
    partitioned over its own guards. A name is significant when two leaves
    with different values for the field differ only in that name, and some
    reachable point exists on both sides.
    """

    significant: set[str] = set()
    for name in component.fields:
        guards = [g for g in component.guards if g.field == name]
        partition = engine.partition(
            [g.expression for g in guards],
            case.base_box,
            component.constraints,
            order,
        )
        leaves = []
        for box, decided in partition.leaves:
            tokens = ordered_unique(g.token for g, on in zip(guards, decided) if on)
            leaves.append(
                (box, tokens[0] if tokens else ("value", case.defaults[name]))
            )
        for (first, value_a), (second, value_b) in itertools.combinations(leaves, 2):
            if value_a == value_b:
                continue
            disjoint = [
                n
                for n in ordered_unique([*first, *second])
                if not set(engine.values(first, n)) & set(engine.values(second, n))
            ]
            if len(disjoint) != 1 or disjoint[0] in significant:
                continue
            split = disjoint[0]
            common = {
                n: tuple(
                    v for v in engine.values(first, n) if v in engine.values(second, n)
                )
                for n in ordered_unique([*first, *second])
                if n != split
            }
            if engine.jointly_reachable(
                common,
                split,
                engine.values(first, split),
                engine.values(second, split),
                component.constraints,
            ):
                significant.add(split)
    return significant


def joint_significance(
    engine: Engine, case: CaseModel, component: Component, alone: set[str]
) -> list[str]:
    """Return the names that must join ``alone`` to determine the word.

    Single-input significance can miss names that matter only together,
    when constraints tie inputs so that no single flip is reachable (for
    example two members of an exactly-one group). The word is determined
    by a name set when no two reachable points with different words agree
    on every name in the set. While some pair does, the first name (in
    component order) on which the pair's regions differ is added.
    """

    names = component.names
    full = engine.full
    regions = [
        (index, projection)
        for index, branch in enumerate(component.branches)
        for projection in branch.merged
    ]
    constrained = {n for c in component.constraints for n in c.names}
    chosen = set(alone)
    added: list[str] = []

    def witness() -> tuple | None:
        positions = [i for i, n in enumerate(names) if n in chosen]
        for (branch_a, first), (branch_b, second) in itertools.combinations(regions, 2):
            if branch_a == branch_b:
                continue
            common = {}
            for i in positions:
                shared = tuple(v for v in first[i] if v in second[i])
                if not shared:
                    break
                common[names[i]] = shared
            else:
                if shared_reachable(first, second, common):
                    return first, second
        return None

    def shared_reachable(first, second, common) -> bool:
        varying = [n for n in common if n in constrained and len(common[n]) > 1]
        fixed = {n: v for n, v in common.items() if n not in varying}
        for values in itertools.product(*(common[n] for n in varying)):
            point = {**fixed, **{n: (v,) for n, v in zip(varying, values)}}
            boxes = [
                {**case.base_box, **dict(zip(names, region)), **point}
                for region in (first, second)
            ]
            if all(engine.satisfiable(b, component.constraints) for b in boxes):
                return True
        return False

    while (pair := witness()) is not None:
        first, second = pair
        candidates = [
            n
            for i, n in enumerate(names)
            if n not in chosen and not set(first[i]) & set(second[i])
        ]
        if not candidates:
            break  # cannot happen for disjoint branches; stop rather than loop
        chosen.add(candidates[0])
        added.append(candidates[0])
    return added


# ---------------------------------------------------------------------------
# Cross-case analysis
# ---------------------------------------------------------------------------


def case_coverage(
    model: Model, engine: Engine, results: list[CaseResult]
) -> tuple[dict[tuple[str, str], list[Box]], list[Box], list[str]]:
    """Partition the state space by which case bases hold.

    Returns overlapping case pairs with their regions, reachable regions
    no case covers, and the names split.
    """

    reachable = [r for r in results if r.reachable]
    bases = [parse_or_true(r.case.base_text) for r in reachable]
    order = ordered_unique(
        name for base in bases for name, _ in compared_literals(base)
    )
    partition = engine.partition(bases, {}, model.constraints, order)
    overlaps: dict[tuple[str, str], list[Box]] = {}
    uncovered: list[Box] = []
    for box, decided in partition.leaves:
        matched = [r.case.id for r, on in zip(reachable, decided) if on]
        if not matched:
            uncovered.append(box)
        for pair in itertools.combinations(matched, 2):
            overlaps.setdefault(pair, []).append(box)
    return overlaps, uncovered, order


def field_values(result: CaseResult, model: Model) -> dict[str, set]:
    values = {name: {("value", result.case.defaults[name])} for name in model.fields}
    for component in result.components:
        for index, name in enumerate(component.fields):
            values[name] = {branch.word[index] for branch in component.branches}
    return values


def shared_word_count(
    first: CaseResult, second: CaseResult, model: Model
) -> int | None:
    """Count the complete words two cases can both produce.

    Components of both cases that share a field are joined; every other
    field takes the case's fixed value. Returns None when a join group is
    too large to enumerate.
    """

    links = UnionFind()
    sides = [(0, first), (1, second)]
    for side, result in sides:
        for index, component in enumerate(result.components):
            for name in component.fields:
                links.union((side, index), ("field", name))
    groups: dict[Any, list[tuple[int, int]]] = {}
    for side, result in sides:
        for index in range(len(result.components)):
            groups.setdefault(links.find((side, index)), []).append((side, index))

    total = 1
    for members in groups.values():
        fields = [
            name
            for name in model.fields
            if any(
                name in sides[side][1].components[index].fields
                for side, index in members
            )
        ]
        combinations = []
        for side, result in sides:
            own = [result.components[i] for s, i in members if s == side]
            words_per = [ordered_unique(b.word for b in c.branches) for c in own]
            size = 1
            for words in words_per:
                size *= len(words)
            if size > MAX_JOIN_COMBINATIONS:
                return None
            restricted = set()
            for combo in itertools.product(*words_per):
                assigned: dict[str, tuple[str, str]] = {}
                for component, word in zip(own, combo):
                    assigned.update(zip(component.fields, word))
                restricted.add(
                    tuple(
                        assigned.get(name, ("value", result.case.defaults[name]))
                        for name in fields
                    )
                )
            combinations.append(restricted)
        common = len(combinations[0] & combinations[1])
        if not common:
            return 0
        total *= common
    return total


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def assignment_json(guard: Guard) -> dict[str, Any]:
    item = {"field": guard.field}
    item.update(
        {"value": guard.token[1]}
        if guard.token[0] == "value"
        else {"value_from_input": guard.token[1]}
    )
    item["origin"] = guard.item.get("origin")
    item["source"] = guard.item.get("source")
    return item


def analyze(model: Model) -> tuple[dict[str, Any], list[Diagnostic]]:
    engine = Engine(model.full)
    full = model.full
    diagnostics: list[Diagnostic] = list(model.notes)
    results = [analyze_case(model, engine, case) for case in model.cases]
    for result in results:
        diagnostics += result.conflicts
    if has_failures(diagnostics):
        return {}, diagnostics

    # -- Component classes -------------------------------------------------
    classes: dict[tuple, dict[str, Any]] = {}
    case_classes: dict[str, list[str]] = {}
    class_components: dict[str, Component] = {}
    class_defaults: dict[str, dict[str, str]] = {}
    for result in results:
        ids = []
        for component in result.components:
            branch_items = []
            for branch in component.branches:
                fired = set().union(*branch.fired_sets)
                always = set.intersection(*(set(s) for s in branch.fired_sets))
                assignments = []
                for guard in component.guards:
                    if guard.position in fired:
                        item = assignment_json(guard)
                        item["in_every_region"] = guard.position in always
                        assignments.append(item)
                branch_items.append(
                    {
                        "word": {
                            name: token_json(token)
                            for name, token in zip(component.fields, branch.word)
                        },
                        "condition": render_merged(branch.merged, component.names, full),
                        "assignment_sets": len(branch.fired_sets),
                        "assignments": assignments,
                    }
                )
            key = json.dumps([component.fields, branch_items], sort_keys=True)
            if key not in classes:
                class_id = f"cc-{len(classes) + 1:04d}"
                for number, item in enumerate(branch_items, 1):
                    item["branch_id"] = f"{class_id}.b{number}"
                classes[key] = {
                    "class_id": class_id,
                    "fields": component.fields,
                    "inputs": [
                        n
                        for n in component.names
                        if any(
                            n in free_names(g.expression, result.box, full)
                            for g in component.guards
                        )
                    ],
                    "branches": [
                        {"branch_id": item["branch_id"], **{k: v for k, v in item.items() if k != "branch_id"}}
                        for item in branch_items
                    ],
                    "cases": [],
                }
                class_components[class_id] = component
                class_defaults[class_id] = result.case.defaults
            classes[key]["cases"].append(result.case.id)
            ids.append(classes[key]["class_id"])
        case_classes[result.case.id] = ids
    class_list = list(classes.values())

    # -- Aliases -------------------------------------------------------------
    aliases: list[dict[str, Any]] = []
    for item in class_list:
        component = class_components[item["class_id"]]
        for branch, entry in zip(component.branches, item["branches"]):
            if len(branch.fired_sets) > 1:
                aliases.append(
                    {
                        "kind": "within_case",
                        "component_class": item["class_id"],
                        "branches": [entry["branch_id"]],
                        "assignment_sets": len(branch.fired_sets),
                        "cases": item["cases"],
                    }
                )
        case_defaults = class_defaults[item["class_id"]]
        defaults_word = tuple(("value", case_defaults[f]) for f in component.fields)
        for branch, entry in zip(component.branches, item["branches"]):
            if any(branch.fired_sets) and branch.word == defaults_word:
                aliases.append(
                    {
                        "kind": "default_only",
                        "component_class": item["class_id"],
                        "branches": [entry["branch_id"]],
                        "cases": item["cases"],
                    }
                )
    by_fields: dict[tuple, list[tuple[str, str, tuple]]] = {}
    for item in class_list:
        component = class_components[item["class_id"]]
        for branch, entry in zip(component.branches, item["branches"]):
            by_fields.setdefault(tuple(component.fields), []).append(
                (item["class_id"], entry["branch_id"], branch.word)
            )
    for fields, entries in by_fields.items():
        supplied = [e for e in entries if any(t[0] == "input" for t in e[2])]
        pairs = [
            (a, b)
            for a in supplied
            for b in entries
            if b is not a and not (b in supplied and entries.index(b) < entries.index(a))
        ]
        for (class_a, branch_a, word_a), (class_b, branch_b, word_b) in pairs:
            different = [
                name
                for name, a, b in zip(fields, word_a, word_b)
                if a != b
            ]
            if different and all(
                word_a[fields.index(n)][0] == "input"
                or word_b[fields.index(n)][0] == "input"
                for n in different
            ):
                aliases.append(
                    {
                        "kind": "supplied_data",
                        "branches": [branch_a, branch_b],
                        "fields": different,
                    }
                )
    reachable = [r for r in results if r.reachable]
    values = {r.case.id: field_values(r, model) for r in reachable}
    for first, second in itertools.combinations(reachable, 2):
        a, b = values[first.case.id], values[second.case.id]
        if any(not (a[name] & b[name]) for name in model.fields):
            continue
        count = shared_word_count(first, second, model)
        if count is None:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "ALIAS_NOT_COMPUTED",
                    f"Shared words with {second.case.id} were not counted: a "
                    f"join group exceeds {MAX_JOIN_COMBINATIONS} combinations.",
                    first.case.id,
                )
            )
        elif count:
            aliases.append(
                {
                    "kind": "cross_case",
                    "cases": [first.case.id, second.case.id],
                    "shared_word_count": count,
                }
            )

    # -- Unreachable ---------------------------------------------------------
    unreachable: list[dict[str, Any]] = []
    for result in results:
        case = result.case
        if not result.reachable:
            contradictory = case.base_box is None
            unreachable.append(
                {
                    "kind": "case",
                    "execution_case_id": case.id,
                    "condition": case.base_text,
                    "conflicting_constraints": list(result.unreachable_reason),
                    "source": case.source,
                    "assessment": "suspect",
                }
            )
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "UNREACHABLE_CASE",
                    "Base context "
                    + ("is contradictory." if contradictory else "cannot be reached under: " + ", ".join(result.unreachable_reason) + "."),
                    case.id,
                )
            )
            continue
        for component in result.components:
            for guard in component.never_fired:
                logical = engine.partition(
                    [guard.expression], case.base_box, [], component.names, required=(0,)
                )
                if not logical.leaves:
                    constraints, assessment = ["predicate is contradictory"], "suspect"
                else:
                    # Judge against every constraint: the case's own copies
                    # are specialized, and IR facts are already in its box.
                    reasons: list[str] = []
                    for leaf_box, _ in logical.leaves:
                        for c in model.constraints:
                            if not engine.satisfiable(leaf_box, [c]) and c.id not in reasons:
                                reasons.append(c.id)
                    if not reasons:
                        for leaf_box, _ in logical.leaves:
                            reasons += [
                                r
                                for r in engine.core(leaf_box, model.constraints)
                                if r not in reasons
                            ]
                    constraints = reasons
                    assessment = "expected"
                unreachable.append(
                    {
                        "kind": "assignment",
                        "execution_case_id": case.id,
                        "assignment": assignment_json(guard),
                        "condition": guard.item.get("when"),
                        "conflicting_constraints": constraints,
                        "source": case.source,
                        "assessment": assessment,
                    }
                )
                if assessment == "suspect":
                    diagnostics.append(
                        Diagnostic(
                            WARNING,
                            "CONTRADICTORY_ASSIGNMENT_GUARD",
                            f"Assignment from {guard.item.get('source')} can never "
                            "apply: its condition is contradictory.",
                            case.id,
                            guard.field,
                        )
                    )
            regions: dict[tuple[str, ...], list[Box]] = {}
            for box, reason in component.pruned:
                regions.setdefault(reason, []).append(box)
            for reason, boxes in regions.items():
                unreachable.append(
                    {
                        "kind": "region",
                        "execution_case_id": case.id,
                        "fields": component.fields,
                        "condition": render_region(boxes, component.names, full),
                        "conflicting_constraints": list(reason),
                        "source": case.source,
                        "assessment": "expected",
                    }
                )

    # -- Coverage ------------------------------------------------------------
    overlaps, uncovered, coverage_names = case_coverage(model, engine, results)
    overlap_list = [
        {"cases": list(pair), "condition": render_region(boxes, coverage_names, full)}
        for pair, boxes in overlaps.items()
    ]
    partners: dict[str, list[str]] = {}
    for first, second in overlaps:
        partners.setdefault(first, []).append(second)
        partners.setdefault(second, []).append(first)
    for result in results:
        others = partners.get(result.case.id)
        if others:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "CASE_OVERLAP",
                    f"Base context holds together with {len(others)} other "
                    "case(s): " + ", ".join(others) + ".",
                    result.case.id,
                )
            )
    uncovered_list = [
        render_box(item, coverage_names, full)
        for item in merge_boxes(uncovered, coverage_names, full)
    ]
    for text in uncovered_list:
        diagnostics.append(
            Diagnostic(
                WARNING,
                "UNCOVERED_REGION",
                f"No execution case applies when {text}.",
            )
        )

    # -- Inputs --------------------------------------------------------------
    significant_in: dict[str, list[str]] = {}
    referenced_in: dict[str, list[str]] = {}
    selects: dict[str, list[str]] = {}
    supplies: dict[str, list[str]] = {}
    for result in results:
        for name in result.significant:
            significant_in.setdefault(name, []).append(result.case.id)
        for name in result.referenced:
            referenced_in.setdefault(name, []).append(result.case.id)
        if result.reachable:
            for name in result.case.base_box:
                selects.setdefault(name, []).append(result.case.id)
        for guard in result.case.guards:
            if guard.token[0] == "input":
                cases = supplies.setdefault(guard.token[1], [])
                if result.case.id not in cases:
                    cases.append(result.case.id)
    names = (
        model.input_names
        + [n for n in ("MS", "TS") if n in referenced_in]
        + [n for n in model.fields if n in referenced_in]
    )
    inputs = []
    for name in names:
        kind = (
            "control_input"
            if name in model.input_fields
            else "state"
            if name in ("MS", "TS")
            else "control_word_field"
        )
        if significant_in.get(name) or selects.get(name):
            category = "behavioral"
        elif supplies.get(name):
            category = "supplied_data"
        elif referenced_in.get(name):
            category = "no_effect"
        else:
            category = "unreferenced"
        entry = {"name": name, "kind": kind, "category": category}
        if kind == "control_input":
            entry["control_uses"] = model.input_fields[name].get("control_uses")
        entry["significant_in_cases"] = significant_in.get(name, [])
        entry["selects_cases"] = selects.get(name, [])
        entry["supplies_values_in_cases"] = supplies.get(name, [])
        entry["referenced_in_case_count"] = len(referenced_in.get(name, []))
        inputs.append(entry)
        if kind == "control_word_field":
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "CONTROL_FIELD_COMPARED_AS_INPUT",
                    f"Encoded control-word field {name} is compared in "
                    f"{len(referenced_in[name])} case(s); its value as a "
                    "control input is not defined by the control-input schema.",
                    field_name=name,
                )
            )

    # -- Cases ---------------------------------------------------------------
    cases = []
    for result in results:
        if result.jointly_significant:
            diagnostics.append(
                Diagnostic(
                    INFO,
                    "JOINT_SIGNIFICANCE",
                    "No single change of "
                    + ", ".join(result.jointly_significant)
                    + " is reachable, but the word is not determined without "
                    "them.",
                    result.case.id,
                )
            )
        cases.append(
            {
                "execution_case_id": result.case.id,
                "source": result.case.source,
                "base_context": result.case.base_text,
                "reachable": result.reachable,
                "word_count": result.word_count,
                "component_classes": case_classes.get(result.case.id, []),
                "significant_inputs": result.significant,
                "jointly_significant_inputs": result.jointly_significant,
                "referenced_inputs": result.referenced,
            }
        )

    expected = sum(1 for item in unreachable if item["assessment"] == "expected")
    if expected:
        diagnostics.append(
            Diagnostic(
                INFO,
                "EXPECTED_UNREACHABLE",
                f"{expected} unreachable assignment(s) or region(s) are "
                "excluded by documented constraints.",
            )
        )
    summary = {
        "cases": len(results),
        "reachable_cases": sum(r.reachable for r in results),
        "complete_words": sum(r.word_count for r in results),
        "component_classes": len(class_list),
        "branches": sum(len(c["branches"]) for c in class_list),
        "inputs_by_category": {
            category: sum(1 for i in inputs if i["category"] == category)
            for category in ("behavioral", "supplied_data", "no_effect", "unreferenced")
        },
        "aliases_by_kind": {
            kind: sum(1 for a in aliases if a["kind"] == kind)
            for kind in ("cross_case", "within_case", "default_only", "supplied_data")
        },
        "overlapping_case_pairs": len(overlap_list),
        "uncovered_regions": len(uncovered_list),
        "unreachable": {
            kind: sum(1 for u in unreachable if u["kind"] == kind)
            for kind in ("case", "assignment", "region")
        },
    }
    analysis = {
        "format_version": FORMAT_VERSION,
        "control_design_version": model.version,
        "artifact": ARTIFACT,
        "generation_stage": GENERATION_STAGE,
        "representation": REPRESENTATION,
        "sources": [spec.file_name for spec in INPUT_SPECS],
        "summary": summary,
        "constraints": [c.to_json() for c in model.constraints],
        "inputs": inputs,
        "cases": cases,
        "component_classes": class_list,
        "aliases": aliases,
        "case_overlaps": overlap_list,
        "uncovered_regions": uncovered_list,
        "unreachable_regions": unreachable,
        "diagnostics": [],
    }
    return analysis, diagnostics


def build_analysis(
    documents: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    validator = Validator()
    model = validator.build(documents)
    if model is None:
        return None, validator.diagnostics
    analysis, diagnostics = analyze(model)
    diagnostics = sorted(diagnostics, key=diagnostic_sort_key)
    if has_failures(diagnostics):
        return None, diagnostics
    analysis["diagnostics"] = [d.to_json() for d in diagnostics]
    return analysis, diagnostics


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def serialize_json(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def remove_previous_outputs(outputs: Sequence[Path], inputs: Sequence[Path]) -> None:
    for path in outputs:
        if path in inputs:
            raise ValueError(f"Output path is also an input: {path}")
        if path.is_dir():
            raise ValueError(f"Output path is a directory: {path}")
    for path in outputs:
        path.unlink(missing_ok=True)


def format_heading(diagnostic: Diagnostic) -> str:
    text = f"{diagnostic.severity} {diagnostic.code}"
    if diagnostic.entry_id:
        text += f" [{diagnostic.entry_id}]"
    if diagnostic.field_name:
        text += f" [{diagnostic.field_name}]"
    return text


def build_report(
    analysis: dict[str, Any] | None,
    diagnostics: Sequence[Diagnostic],
    written: bool,
) -> str:
    counts = {s: sum(d.severity == s for d in diagnostics) for s in SEVERITIES}
    title = "Control-Word Equivalence Analysis Report"
    lines = [title, "=" * len(title), ""]
    lines.append(f"Analysis written: {'yes' if written else 'no'}")
    lines += [
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
    ]
    if analysis:
        summary = analysis["summary"]
        lines += [
            "Summary",
            "-------",
            f"Cases: {summary['cases']} ({summary['reachable_cases']} reachable)",
            f"Complete control words (sum over cases): {summary['complete_words']}",
            f"Component classes: {summary['component_classes']} "
            f"({summary['branches']} branches)",
            f"Overlapping case pairs: {summary['overlapping_case_pairs']}",
            f"Uncovered regions: {summary['uncovered_regions']}",
            "Unreachable: "
            + ", ".join(f"{k} {v}" for k, v in summary["unreachable"].items()),
            "Aliases: "
            + ", ".join(f"{k} {v}" for k, v in summary["aliases_by_kind"].items()),
            "",
            "Input significance",
            "------------------",
        ]
        for category in ("behavioral", "supplied_data", "no_effect", "unreferenced"):
            names = [i["name"] for i in analysis["inputs"] if i["category"] == category]
            lines.append(f"{category} ({len(names)}): " + (", ".join(names) or "none"))
        lines += ["", "Cases by word count", "-------------------"]
        for case in sorted(
            analysis["cases"], key=lambda c: (-c["word_count"], c["execution_case_id"])
        ):
            lines.append(
                f"{case['execution_case_id']}: {case['word_count']} word(s); "
                f"significant: {', '.join(case['significant_inputs']) or 'none'}"
            )
        lines += ["", "Unreachable assignments", "-----------------------"]
        assignments = [u for u in analysis["unreachable_regions"] if u["kind"] != "region"]
        for item in assignments:
            what = (
                f"{item['assignment']['field']} from {item['assignment']['source']}"
                if item["kind"] == "assignment"
                else "whole case"
            )
            lines.append(
                f"[{item['assessment']}] {item['execution_case_id']}: {what}; "
                f"blocked by {', '.join(item['conflicting_constraints'])}"
            )
        if not assignments:
            lines.append("None.")
        lines.append("")
    lines += ["Diagnostics", "-----------"]
    lines += [f"{format_heading(d)}: {d.message}" for d in diagnostics] or [
        "No diagnostics."
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze equivalence, aliasing, reachability and input "
        "significance of the symbolic control words."
    )
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument(
        "--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIRECTORY,
        help="Directory holding the four input specifications.",
    )
    parser.add_argument("--analysis-output", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    directory = resolve_from_repo(root, options.artifact_dir)
    input_paths = {spec.key: directory / spec.file_name for spec in INPUT_SPECS}
    analysis_path = resolve_from_repo(root, options.analysis_output)
    report_path = resolve_from_repo(root, options.report_output)
    try:
        remove_previous_outputs(
            (analysis_path, report_path), tuple(input_paths.values())
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    analysis = None
    written = False
    try:
        documents = {key: read_json(path) for key, path in input_paths.items()}
        analysis, diagnostics = build_analysis(documents)
        if analysis is not None:
            write_text(analysis_path, serialize_json(analysis))
            written = True
    except AnalysisFailure as error:
        diagnostics = [Diagnostic(FATAL, "ANALYSIS_FAILURE", str(error))]

    write_text(report_path, build_report(analysis, diagnostics, written))
    failures = [d for d in diagnostics if d.severity in FAILURE_SEVERITIES]
    exit_code = 1 if failures else 0
    print("Control-word equivalence analysis")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Analysis written: {'yes' if written else 'no'}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"Analysis output: {analysis_path}")
    print(f"Report output: {report_path}")
    for item in failures:
        print(format_heading(item))
        print(f"  {item.message}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
