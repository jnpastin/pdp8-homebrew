"""Generate predicate-preserving symbolic control words for review.

The generator combines the maintained control specifications into one
symbolic control word per execution case: the default value of every
encoded control-word field, plus every guarded assignment that the case's
micro-operations and the applicable direct-control definitions make, with
its provenance. Conditions stay symbolic; no control-input combination is
enumerated into the output.

Pipeline:

1. Read the six maintained input specifications, and the maintained
   symbolic artifact if present.
2. Validate their structure. Any error stops here.
3. Parse every expression and check every name, micro-operation, field
   and value they use. Any error stops here.
4. Build each case's symbolic control word, reporting any field that two
   assignments can set to different values at the same time.
5. Report cases that are new, changed, or no longer generated.
6. Write the candidate (only when no errors were found) and the report.

See the tool README for the rules.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DEFAULT_ARTIFACT_DIRECTORY = Path("rom/microcode/v1")
DEFAULT_MAINTAINED = DEFAULT_ARTIFACT_DIRECTORY / "symbolic-control-words.json"

OUTPUT_DIRECTORY = Path(
    "build/simulation_outputs/rom-generation/symbolic-control-word-generator"
)
DEFAULT_CANDIDATE = OUTPUT_DIRECTORY / "symbolic-control-words.candidate.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "generation-report.txt"

# ---------------------------------------------------------------------------
# Expected inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InputSpec:
    """One maintained input specification."""

    key: str
    file_name: str
    identity_key: str
    identity: str
    list_key: str
    id_key: str
    code: str


INPUT_SPECS = (
    InputSpec(
        "inputs",
        "control-input-schema.json",
        "specification_type",
        "control-input-schema",
        "fields",
        "name",
        "INVALID_CONTROL_INPUT_SCHEMA",
    ),
    InputSpec(
        "words",
        "control-word-schema.json",
        "specification_type",
        "control-word-schema",
        "fields",
        "name",
        "INVALID_CONTROL_WORD_SCHEMA",
    ),
    InputSpec(
        "mappings",
        "micro-operation-mapping.json",
        "specification_type",
        "micro-operation-mapping",
        "mappings",
        "micro_operation",
        "INVALID_MICRO_OPERATION_MAPPING",
    ),
    InputSpec(
        "execution",
        "execution-definitions.json",
        "artifact",
        "execution-definitions",
        "cases",
        "id",
        "INVALID_EXECUTION_DEFINITIONS",
    ),
    InputSpec(
        "direct",
        "direct-control-definitions.json",
        "artifact",
        "direct-control-definitions",
        "definitions",
        "id",
        "INVALID_DIRECT_CONTROL_DEFINITIONS",
    ),
    InputSpec(
        "timing",
        "timing-constraints.json",
        "artifact",
        "timing-constraints",
        "constraints",
        "id",
        "INVALID_TIMING_CONSTRAINTS",
    ),
)
SPECS_BY_KEY = {spec.key: spec for spec in INPUT_SPECS}

ARTIFACT = "symbolic-control-words"
FORMAT_VERSION = 1
GENERATION_STAGE = "candidate-generation"
REPRESENTATION = "predicate-preserving"

ENCODED_ROLE = "encoded"
STATE_NAMES = ("MS", "TS")
TIMING_STATES = (1, 2, 3, 4)
# MS has no field of its own; its states are the meanings of the values of
# the field that loads it.
MAJOR_STATE_FIELD = "MS_NEXT"
EXCLUSIVE_KINDS = ("exactly_one", "at_most_one")
MUTUAL_EXCLUSION = re.compile(r"Mutually exclusive with ([^.`]+)\.?")

MAPPING_ORIGIN = "micro-operation mapping"
CONDITIONAL_ORIGIN = "conditional micro-operation mapping"
DIRECT_ORIGIN = "direct-control definition"
SUPPLIED_ORIGIN = "control-supplied value"

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
    """One validation or generation finding.

    ``entry_id`` names the case, definition, mapping or constraint;
    ``field_name`` the property or control-word field concerned.
    """

    severity: str
    code: str
    message: str
    entry_id: str | None = None
    field_name: str | None = None


class GenerationFailure(Exception):
    """An input could not be read; generation cannot proceed."""


class ExpressionError(Exception):
    """An expression or assignment could not be parsed."""


def make_error(
    code: str,
    message: str,
    entry_id: str | None = None,
    field_name: str | None = None,
) -> Diagnostic:
    """Build an ERROR diagnostic."""

    return Diagnostic(ERROR, code, message, entry_id, field_name)


def has_failures(diagnostics: Sequence[Diagnostic]) -> bool:
    """Return whether any diagnostic prevents a candidate from being
    written."""

    return any(item.severity in FAILURE_SEVERITIES for item in diagnostics)


def diagnostic_sort_key(diagnostic: Diagnostic) -> tuple:
    """Order diagnostics deterministically, least severe first."""

    return (
        SEVERITY_ORDER.get(diagnostic.severity, 99),
        diagnostic.code,
        diagnostic.entry_id or "",
        diagnostic.field_name or "",
        diagnostic.message,
    )


# ---------------------------------------------------------------------------
# Expressions
#
# An expression is a nested tuple:
#
#   ("const", bool)
#   ("cmp", name, "=" or "!=", value)
#   ("sel", micro_operation, True for "is selected", False for "is not")
#   ("not", expression)
#   ("and", left, right) / ("or", left, right)
#
# Adjacent terms with no operator between them, such as the lines of a
# context block, are joined by AND.
# ---------------------------------------------------------------------------

Expression = tuple

TOKEN_PATTERN = re.compile(
    r"\s*(?:(AND|OR|NOT)\b|(!=|=)|(is\s+not\s+selected|is\s+selected)\b"
    r"|([()])|([^\s()=]+))",
    re.IGNORECASE,
)
ASSIGNMENT_PATTERN = re.compile(r"\s*([^\s=]+)\s*=\s*(\S+)\s*")


def tokenize(text: str) -> list[tuple[str, str]]:
    """Split an expression into ``(kind, text)`` tokens.

    Every non-blank character starts some token, so tokenizing never
    fails; malformed text is reported by the parser.
    """

    tokens: list[tuple[str, str]] = []
    position = 0
    while text[position:].strip():
        match = TOKEN_PATTERN.match(text, position)
        position = match.end()
        logic, compare, selected, paren, name = match.groups()
        if logic:
            token = ("logic", logic.upper())
        elif compare:
            token = ("compare", compare)
        elif selected:
            token = ("selected", " ".join(selected.upper().split()))
        elif paren:
            token = ("paren", paren)
        else:
            token = ("name", name)

        if tokens and ends_term(tokens[-1]) and starts_term(token):
            tokens.append(("logic", "AND"))
        tokens.append(token)
    return tokens


def ends_term(token: tuple[str, str]) -> bool:
    return token[0] in ("name", "selected") or token == ("paren", ")")


def starts_term(token: tuple[str, str]) -> bool:
    return token[0] == "name" or token in (("paren", "("), ("logic", "NOT"))


class Parser:
    """Recursive-descent parser: OR binds loosest, then AND, then NOT."""

    def __init__(self, text: str) -> None:
        self.tokens = tokenize(text)
        self.position = 0

    def at(self, kind: str, text: str | None = None) -> bool:
        if self.position >= len(self.tokens):
            return False
        token = self.tokens[self.position]
        return token[0] == kind and (text is None or token[1] == text)

    def take(self) -> str:
        token = self.tokens[self.position]
        self.position += 1
        return token[1]

    def parse(self) -> Expression:
        if not self.tokens:
            raise ExpressionError("Empty expression.")
        expression = self.disjunction()
        if self.position != len(self.tokens):
            raise ExpressionError(
                f"Unexpected token {self.tokens[self.position][1]!r}."
            )
        return expression

    def disjunction(self) -> Expression:
        expression = self.conjunction()
        while self.at("logic", "OR"):
            self.take()
            expression = ("or", expression, self.conjunction())
        return expression

    def conjunction(self) -> Expression:
        expression = self.negation()
        while self.at("logic", "AND"):
            self.take()
            expression = ("and", expression, self.negation())
        return expression

    def negation(self) -> Expression:
        if self.at("logic", "NOT"):
            self.take()
            return ("not", self.negation())
        if self.at("paren", "("):
            self.take()
            expression = self.disjunction()
            if not self.at("paren", ")"):
                raise ExpressionError("Missing closing parenthesis.")
            self.take()
            return expression
        return self.term()

    def term(self) -> Expression:
        if not self.at("name"):
            raise ExpressionError("Expected a field or micro-operation name.")
        name = self.take()
        if self.at("compare"):
            operator = self.take()
            if not self.at("name"):
                raise ExpressionError(
                    f"Missing value after {name} {operator}."
                )
            return ("cmp", name, operator, self.take())
        if self.at("selected"):
            return ("sel", name, self.take() == "IS SELECTED")
        raise ExpressionError(f"Missing operator after {name}.")


def parse_expression(text: str) -> Expression:
    return Parser(text).parse()


def parse_assignments(blocks: Iterable[str]) -> list[tuple[str, str]]:
    """Parse ``FIELD = VALUE`` lines from assignment blocks."""

    assignments = []
    for block in blocks:
        for line in block.splitlines():
            if not line.strip():
                continue
            match = ASSIGNMENT_PATTERN.fullmatch(line)
            if not match:
                raise ExpressionError(f"Malformed assignment {line!r}.")
            assignments.append((match.group(1), match.group(2)))
    return assignments


def canonical(expression: Expression | None) -> str:
    """Render an expression with every binary operation parenthesized."""

    if expression is None:
        return "always"
    kind = expression[0]
    if kind == "const":
        return "true" if expression[1] else "false"
    if kind == "cmp":
        return " ".join(expression[1:])
    if kind == "sel":
        state = "selected" if expression[2] else "not selected"
        return f"{expression[1]} is {state}"
    if kind == "not":
        return f"NOT ({canonical(expression[1])})"
    left, right = canonical(expression[1]), canonical(expression[2])
    return f"({left} {kind.upper()} {right})"


def conjunction(items: Iterable[Expression | None]) -> Expression | None:
    """AND the expressions together, left to right; None means true."""

    result = None
    for item in items:
        if item is not None:
            result = item if result is None else ("and", result, item)
    return result


def disjunction(items: Sequence[Expression]) -> Expression:
    """OR one or more expressions together, left to right."""

    result = items[0]
    for item in items[1:]:
        result = ("or", result, item)
    return result


def walk(expression: Expression) -> Iterable[Expression]:
    """Yield every node of an expression."""

    yield expression
    if expression[0] == "not":
        yield from walk(expression[1])
    elif expression[0] in ("and", "or"):
        yield from walk(expression[1])
        yield from walk(expression[2])


def compared_names(expression: Expression) -> list[str]:
    """Return the names compared with a value, in first-use order."""

    names = (node[1] for node in walk(expression) if node[0] == "cmp")
    return list(dict.fromkeys(names))


def selected_names(expression: Expression) -> list[str]:
    """Return the micro-operations tested with ``is selected``."""

    names = (node[1] for node in walk(expression) if node[0] == "sel")
    return list(dict.fromkeys(names))


def substitute_selected(
    expression: Expression, selection: dict[str, Expression | None]
) -> Expression:
    """Replace each ``U is selected`` with the condition selecting ``U``.

    A micro-operation the case never selects makes the test false.
    """

    kind = expression[0]
    if kind == "sel":
        name, wanted = expression[1], expression[2]
        if name not in selection:
            return ("const", not wanted)
        guard = selection[name] or ("const", True)
        return guard if wanted else ("not", guard)
    if kind in ("cmp", "const"):
        return expression
    if kind == "not":
        return ("not", substitute_selected(expression[1], selection))
    return (
        kind,
        substitute_selected(expression[1], selection),
        substitute_selected(expression[2], selection),
    )


def evaluate(expression: Expression, values: dict[str, Any]) -> bool | None:
    """Evaluate in three-valued logic; None means not yet determined.

    A name absent from ``values`` is unknown. The expression must contain
    no ``is selected`` tests.
    """

    kind = expression[0]
    if kind == "const":
        return expression[1]
    if kind == "cmp":
        _, name, operator, literal = expression
        if name not in values:
            return None
        return (values[name] == literal) == (operator == "=")
    if kind == "not":
        value = evaluate(expression[1], values)
        return None if value is None else not value

    left = evaluate(expression[1], values)
    right = evaluate(expression[2], values)
    if kind == "and":
        if left is False or right is False:
            return False
        return True if left and right else None
    if left or right:
        return True
    return False if left is False and right is False else None


# ---------------------------------------------------------------------------
# Reading inputs
# ---------------------------------------------------------------------------


def resolve_from_repo(root: Path, path: Path) -> Path:
    """Resolve a relative path from the repository root."""

    return path.resolve() if path.is_absolute() else (root / path).resolve()


def read_json(path: Path, optional: bool = False) -> dict[str, Any] | None:
    """Read a JSON object from ``path``.

    An optional file that is missing or blank yields None. Every other
    problem raises ``GenerationFailure``.
    """

    if optional and not path.exists():
        return None

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise GenerationFailure(
            f"Required input does not exist: {path}"
        ) from error
    except UnicodeDecodeError as error:
        raise GenerationFailure(f"Input is not valid UTF-8: {path}") from error
    except OSError as error:
        raise GenerationFailure(
            f"Unable to read input {path}: {error}"
        ) from error

    if optional and not text.strip():
        return None

    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise GenerationFailure(
            f"Input is not valid JSON: {path}: line {error.lineno}, "
            f"column {error.colno}: {error.msg}"
        ) from error

    if not isinstance(data, dict):
        raise GenerationFailure(f"Input root must be a JSON object: {path}")

    return data


# ---------------------------------------------------------------------------
# Structural validation
# ---------------------------------------------------------------------------


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def is_text_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, str) for item in value
    )


def is_object_list(value: Any) -> bool:
    return isinstance(value, list) and all(
        isinstance(item, dict) for item in value
    )


def is_source(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("path"), str)
        and type(value.get("line")) is int
    )


def is_timing_state(value: Any) -> bool:
    return value is None or (type(value) is int and value in TIMING_STATES)


def is_assignment_list(value: Any) -> bool:
    return is_object_list(value) and all(
        isinstance(item.get("field"), str)
        and isinstance(item.get("value"), str)
        for item in value
    )


def is_conditional_list(value: Any) -> bool:
    return is_object_list(value) and all(
        isinstance(item.get("predicate"), str)
        and isinstance(item.get("micro_operation"), str)
        for item in value
    )


def is_value_list(value: Any) -> bool:
    return is_object_list(value) and all(
        isinstance(item.get("encoding"), str)
        and isinstance(item.get("meaning"), str)
        for item in value
    )


def is_width(value: Any) -> bool:
    return type(value) is int and value > 0


def is_input_value_list(value: Any) -> bool:
    return is_object_list(value) and all(
        isinstance(item.get("value"), str) for item in value
    )


def is_binary(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and set(value) <= {"0", "1"}


def is_range_list(value: Any) -> bool:
    return is_object_list(value) and all(
        is_binary(item.get("start")) and is_binary(item.get("end"))
        for item in value
    )


FieldCheck = tuple[str, Callable[[Any], bool], str]

ENTRY_CHECKS: dict[str, tuple[FieldCheck, ...]] = {
    "inputs": (
        ("width", is_width, "must be a positive integer"),
        ("values", is_input_value_list, "must be an array of {value}"),
        (
            "ranges",
            is_range_list,
            "must be an array of binary {start, end}",
        ),
        ("constraints", is_object_list, "must be an array of objects"),
    ),
    "words": (("control_word_role", is_text, "must be a nonempty string"),),
    "mappings": (
        (
            "assignments",
            is_assignment_list,
            "must be an array of {field, value} strings",
        ),
    ),
    "execution": (
        ("source", is_source, "must be {path, line}"),
        ("context", is_text_list, "must be an array of strings"),
        ("timing_state", is_timing_state, "must be 1 to 4 or null"),
        ("micro_operations", is_text_list, "must be an array of strings"),
        (
            "conditional_micro_operations",
            is_conditional_list,
            "must be an array of {predicate, micro_operation} strings",
        ),
    ),
    "direct": (
        (
            "applicable_context",
            is_text_list,
            "must be an array of strings",
        ),
        ("direct_assignments", is_text_list, "must be an array of strings"),
        (
            "control_supplied_values",
            is_text_list,
            "must be an array of strings",
        ),
    ),
    "timing": (
        ("context", is_text, "must be a nonempty string"),
        ("requirement", is_text, "must be a nonempty string"),
    ),
}

ENCODED_FIELD_CHECKS: tuple[FieldCheck, ...] = (
    ("width", is_width, "must be a positive integer"),
    ("default_value", is_text, "must be a nonempty string"),
    ("values", is_value_list, "must be an array of {encoding, meaning}"),
)


def index_entries(
    entries: Any, spec: InputSpec
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Index an input's entries by id, reporting malformed entries."""

    label = spec.file_name
    if not isinstance(entries, list):
        return [
            make_error(
                spec.code, f"{label} must contain a {spec.list_key} array."
            )
        ], {}

    diagnostics = []
    index: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(entries):
        if not isinstance(item, dict):
            diagnostics.append(
                make_error(
                    spec.code,
                    f"{label} {spec.list_key} entry {position} must be an "
                    "object.",
                )
            )
            continue
        identifier = item.get(spec.id_key)
        if not is_text(identifier):
            diagnostics.append(
                make_error(
                    spec.code,
                    f"{label} {spec.list_key} entry {position} has no "
                    f"nonempty string {spec.id_key}.",
                )
            )
            continue
        if identifier in index:
            diagnostics.append(
                make_error(
                    spec.code,
                    f"{label} contains duplicate {spec.id_key} {identifier}.",
                    identifier,
                )
            )
        index[identifier] = item
    return diagnostics, index


def check_fields(
    entry: dict[str, Any],
    identifier: str,
    checks: Sequence[FieldCheck],
    code: str,
) -> list[Diagnostic]:
    return [
        make_error(code, f"{field} {rule}.", identifier, field)
        for field, valid, rule in checks
        if not valid(entry.get(field))
    ]


def validate_global_constraints(data: dict[str, Any]) -> list[Diagnostic]:
    """Check the control-input schema's global constraints."""

    code = SPECS_BY_KEY["inputs"].code
    constraints = data.get("constraints")
    if not is_object_list(constraints):
        return [
            make_error(
                code,
                "control-input-schema.json constraints must be an array of "
                "objects.",
                field_name="constraints",
            )
        ]
    return [
        make_error(
            code,
            f"Global constraint {position} inputs must be an array of "
            "strings.",
            field_name="constraints",
        )
        for position, item in enumerate(constraints)
        if item.get("kind") in EXCLUSIVE_KINDS
        and not is_text_list(item.get("inputs"))
    ]


def validate_inputs(
    documents: dict[str, dict[str, Any]],
) -> tuple[list[Diagnostic], dict[str, dict[str, dict[str, Any]]]]:
    """Validate the six input specifications and index their entries."""

    diagnostics: list[Diagnostic] = []
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    version = documents["words"].get("control_design_version")
    if not is_text(version):
        diagnostics.append(
            make_error(
                SPECS_BY_KEY["words"].code,
                "control-word-schema.json control_design_version must be a "
                "nonempty string.",
                field_name="control_design_version",
            )
        )

    for spec in INPUT_SPECS:
        data = documents[spec.key]
        if data.get(spec.identity_key) != spec.identity:
            diagnostics.append(
                make_error(
                    "UNEXPECTED_ARTIFACT_TYPE",
                    f"Expected {spec.identity_key} {spec.identity!r}.",
                    field_name=spec.file_name,
                )
            )
        if data.get("control_design_version") != version:
            diagnostics.append(
                make_error(
                    "CONTROL_DESIGN_VERSION_MISMATCH",
                    "control_design_version differs from "
                    "control-word-schema.json.",
                    field_name=spec.file_name,
                )
            )

        index_diagnostics, index = index_entries(data.get(spec.list_key), spec)
        diagnostics += index_diagnostics
        indexes[spec.key] = index
        for identifier, entry in index.items():
            diagnostics += check_fields(
                entry, identifier, ENTRY_CHECKS[spec.key], spec.code
            )
            if (
                spec.key == "words"
                and entry.get("control_word_role") == ENCODED_ROLE
            ):
                diagnostics += check_fields(
                    entry, identifier, ENCODED_FIELD_CHECKS, spec.code
                )

    diagnostics += validate_global_constraints(documents["inputs"])
    return diagnostics, indexes


def validate_maintained(
    data: dict[str, Any] | None, version: Any
) -> tuple[list[Diagnostic], dict[str, dict[str, Any]]]:
    """Validate the maintained symbolic artifact and index its cases.

    A missing artifact (None) is valid and has no cases.
    """

    if data is None:
        return [], {}

    diagnostics: list[Diagnostic] = []
    if data.get("control_design_version") != version:
        diagnostics.append(
            make_error(
                "CONTROL_DESIGN_VERSION_MISMATCH",
                "Maintained artifact control_design_version differs from "
                "control-word-schema.json.",
            )
        )

    cases = data.get("cases")
    if not isinstance(cases, list):
        diagnostics.append(
            make_error(
                "INVALID_MAINTAINED_CASES",
                "Maintained artifact must contain a cases array.",
            )
        )
        return diagnostics, {}

    index: dict[str, dict[str, Any]] = {}
    for position, item in enumerate(cases):
        identifier = (
            item.get("execution_case_id") if isinstance(item, dict) else None
        )
        if not is_text(identifier):
            diagnostics.append(
                make_error(
                    "INVALID_MAINTAINED_CASES",
                    f"Maintained case {position} has no nonempty string "
                    "execution_case_id.",
                )
            )
        elif identifier in index:
            diagnostics.append(
                make_error(
                    "INVALID_MAINTAINED_CASES",
                    f"Maintained artifact contains duplicate case "
                    f"{identifier}.",
                    identifier,
                )
            )
        else:
            index[identifier] = item
    return diagnostics, index


# ---------------------------------------------------------------------------
# Reference validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Assignment:
    """One control-word field assignment.

    ``value`` is an encoding, or a control-input name when ``from_input``.
    """

    field: str
    value: str
    from_input: bool = False


@dataclass(frozen=True)
class DirectDefinition:
    id: str
    context: Expression
    assignments: tuple[tuple[Assignment, str], ...]  # with origin


@dataclass(frozen=True)
class Model:
    """The validated inputs, in the form generation uses."""

    version: str
    words: dict[str, dict[str, Any]]
    defaults: dict[str, str]
    mappings: dict[str, tuple[Assignment, ...]]
    exclusive_pairs: tuple[tuple[str, str], ...]
    timing_violations: tuple[Expression, ...]
    direct: tuple[DirectDefinition, ...]
    cases: tuple[tuple[dict[str, Any], Expression | None, dict], ...]


def encode(field: dict[str, Any], value: str) -> str:
    """Return the encoding of ``value``, given as an encoding or meaning.

    A field with no listed values takes a binary string of at most its
    width, or a decimal number, and is zero-filled to its width.
    """

    values = field["values"]
    for item in values:
        if value == item["encoding"]:
            return item["encoding"]
    for item in values:
        if value == item["meaning"]:
            return item["encoding"]
    if not values:
        width = field["width"]
        if set(value) <= {"0", "1"} and len(value) <= width:
            return value.zfill(width)
        if value.isdigit() and int(value) < 2**width:
            return format(int(value), f"0{width}b")
    raise ValueError(f"Unknown value {value!r} for {field['name']}.")


@dataclass(frozen=True)
class Domain:
    """The values a compared name can take.

    Either the listed ``values``, or, when ``width`` is set, binary strings
    of exactly that width, within one of ``ranges`` if any are given.
    """

    values: tuple[str, ...] = ()
    width: int | None = None
    ranges: tuple[tuple[str, str], ...] = ()
    note: str = ""

    def contains(self, value: str) -> bool:
        if self.width is None:
            return value in self.values
        if len(value) != self.width or not is_binary(value):
            return False
        return not self.ranges or any(
            int(start, 2) <= int(value, 2) <= int(end, 2)
            for start, end in self.ranges
        )

    def describe(self) -> str:
        if self.width is None:
            if not self.values:
                return f"no documented values{self.note}"
            return "one of " + ", ".join(self.values)
        text = f"a {self.width}-bit binary value"
        if self.ranges:
            text += " from " + " or ".join(
                f"{start} to {end}" for start, end in self.ranges
            )
        return text


def value_domains(
    inputs: dict[str, dict[str, Any]],
    words: dict[str, dict[str, Any]],
) -> dict[str, Domain]:
    """Return the domain of every name a comparison may use.

    A control input takes its listed values, or else a binary value of its
    width within its ranges. An encoded control-word field takes its
    encodings, or else a binary value of its width. TS takes 1 to 4, and
    MS the meanings of the major-state field's values.
    """

    domains = {}
    for name, field in words.items():
        encodings = tuple(item["encoding"] for item in field["values"])
        domains[name] = (
            Domain(encodings) if encodings else Domain(width=field["width"])
        )
    for name, field in inputs.items():
        values = tuple(item["value"] for item in field["values"])
        domains[name] = (
            Domain(values)
            if values
            else Domain(
                width=field["width"],
                ranges=tuple(
                    (item["start"], item["end"]) for item in field["ranges"]
                ),
            )
        )

    major_state = words.get(MAJOR_STATE_FIELD)
    domains["MS"] = Domain(
        tuple(item["meaning"] for item in major_state["values"])
        if major_state
        else (),
        note=f"; they come from {MAJOR_STATE_FIELD}, which is not an "
        "encoded control-word field",
    )
    domains["TS"] = Domain(tuple(str(state) for state in TIMING_STATES))
    return domains


class Checker:
    """Collects reference diagnostics while resolving the inputs."""

    def __init__(self, indexes: dict[str, dict[str, dict[str, Any]]]):
        self.diagnostics: list[Diagnostic] = []
        self.input_names = set(indexes["inputs"])
        self.words = {
            name: field
            for name, field in indexes["words"].items()
            if field["control_word_role"] == ENCODED_ROLE
        }
        self.domains = value_domains(indexes["inputs"], self.words)
        self.known_names = set(self.domains)
        self.micro_operations = set(indexes["mappings"])

    def error(
        self, code: str, message: str, entry_id: str, field_name: str
    ) -> None:
        self.diagnostics.append(
            make_error(code, message, entry_id, field_name)
        )

    def expression(
        self,
        text: str,
        entry_id: str,
        field_name: str,
        allow_selection: bool = False,
    ) -> Expression | None:
        """Parse ``text`` and check every name it uses."""

        try:
            expression = parse_expression(text)
        except ExpressionError as error:
            self.error(
                "INVALID_EXPRESSION",
                f"{error} In {text!r}.",
                entry_id,
                field_name,
            )
            return None

        for name in compared_names(expression):
            if name not in self.known_names:
                self.error(
                    "UNKNOWN_NAME",
                    f"{name} is not a control input, encoded control-word "
                    "field, MS or TS.",
                    entry_id,
                    field_name,
                )
        compared = {
            node[1:4:2]: None
            for node in walk(expression)
            if node[0] == "cmp" and node[1] in self.domains
        }
        for name, value in compared:
            domain = self.domains[name]
            if not domain.contains(value):
                self.error(
                    "INVALID_COMPARED_VALUE",
                    f"{value} is not a value of {name}, which takes "
                    f"{domain.describe()}.",
                    entry_id,
                    field_name,
                )
        for name in selected_names(expression):
            if not allow_selection:
                self.error(
                    "INVALID_EXPRESSION",
                    f"'{name} is selected' is allowed only in direct-control "
                    "contexts.",
                    entry_id,
                    field_name,
                )
            elif name not in self.micro_operations:
                self.micro_operation(name, entry_id, field_name)
        return expression

    def micro_operation(
        self, name: str, entry_id: str, field_name: str
    ) -> bool:
        if name in self.micro_operations:
            return True
        self.error(
            "UNKNOWN_MICRO_OPERATION",
            f"{name} has no micro-operation mapping.",
            entry_id,
            field_name,
        )
        return False

    def assignment(
        self,
        field: str,
        value: str,
        entry_id: str,
        allow_input: bool = False,
    ) -> Assignment | None:
        """Check a field assignment and return it with its encoding."""

        if field not in self.words:
            self.error(
                "UNKNOWN_CONTROL_FIELD",
                f"{field} is not an encoded control-word field.",
                entry_id,
                field,
            )
            return None
        if allow_input and value in self.input_names:
            return Assignment(field, value, from_input=True)
        try:
            return Assignment(field, encode(self.words[field], value))
        except ValueError as error:
            self.error("INVALID_FIELD_VALUE", str(error), entry_id, field)
            return None

    def assignment_blocks(
        self,
        definition: dict[str, Any],
        key: str,
        origin: str,
        allow_input: bool,
    ) -> list[tuple[Assignment, str]]:
        try:
            pairs = parse_assignments(definition[key])
        except ExpressionError as error:
            self.error(
                "MALFORMED_ASSIGNMENT", str(error), definition["id"], key
            )
            return []
        resolved = []
        for field, value in pairs:
            assignment = self.assignment(
                field, value, definition["id"], allow_input
            )
            if assignment is not None:
                resolved.append((assignment, origin))
        return resolved


def exclusive_pairs(
    indexes: dict[str, dict[str, dict[str, Any]]],
    global_constraints: list[dict[str, Any]],
) -> tuple[tuple[str, str], ...]:
    """Return the pairs of inputs that are never both 1.

    They come from field constraints reading ``Mutually exclusive with X.``
    and from ``exactly_one`` and ``at_most_one`` global constraints.
    """

    pairs: dict[tuple[str, str], None] = {}

    def add(left: str, right: str) -> None:
        if left != right:
            pairs[tuple(sorted((left, right)))] = None

    for name, field in indexes["inputs"].items():
        for constraint in field["constraints"]:
            text = constraint.get("text")
            match = MUTUAL_EXCLUSION.fullmatch(
                text.strip() if isinstance(text, str) else ""
            )
            if match:
                add(name, match.group(1).strip())

    for constraint in global_constraints:
        if constraint.get("kind") in EXCLUSIVE_KINDS:
            names = constraint["inputs"]
            for position, left in enumerate(names):
                for right in names[position + 1 :]:
                    add(left, right)

    return tuple(pairs)


def resolve_inputs(
    documents: dict[str, dict[str, Any]],
    indexes: dict[str, dict[str, dict[str, Any]]],
) -> tuple[Model | None, list[Diagnostic]]:
    """Check every reference in the inputs and build the model."""

    check = Checker(indexes)

    defaults = {}
    for name, field in check.words.items():
        try:
            defaults[name] = encode(field, field["default_value"])
        except ValueError as error:
            check.error(
                "INVALID_FIELD_VALUE", str(error), name, "default_value"
            )

    mappings = {}
    for name, mapping in indexes["mappings"].items():
        resolved = [
            check.assignment(item["field"], item["value"], name)
            for item in mapping["assignments"]
        ]
        mappings[name] = tuple(item for item in resolved if item)

    violations = []
    for identifier, constraint in indexes["timing"].items():
        context = check.expression(
            constraint["context"], identifier, "context"
        )
        requirement = check.expression(
            constraint["requirement"], identifier, "requirement"
        )
        violations.append(conjunction([context, ("not", requirement)]))

    direct = []
    for identifier, definition in indexes["direct"].items():
        contexts = [
            check.expression(text, identifier, "applicable_context", True)
            for text in definition["applicable_context"]
        ]
        if not contexts:
            check.error(
                "MISSING_APPLICABLE_CONTEXT",
                "Definition has no applicable context.",
                identifier,
                "applicable_context",
            )
        assignments = check.assignment_blocks(
            definition, "direct_assignments", DIRECT_ORIGIN, False
        ) + check.assignment_blocks(
            definition, "control_supplied_values", SUPPLIED_ORIGIN, True
        )
        if contexts and all(contexts):
            direct.append(
                DirectDefinition(
                    identifier, disjunction(contexts), tuple(assignments)
                )
            )

    cases = []
    for identifier, case in indexes["execution"].items():
        cases.append(resolve_case(check, identifier, case))

    if check.diagnostics:
        return None, check.diagnostics

    model = Model(
        version=documents["words"]["control_design_version"],
        words=check.words,
        defaults=defaults,
        mappings=mappings,
        exclusive_pairs=exclusive_pairs(
            indexes, documents["inputs"]["constraints"]
        ),
        timing_violations=tuple(violations),
        direct=tuple(direct),
        cases=tuple(cases),
    )
    return model, []


def resolve_case(
    check: Checker, identifier: str, case: dict[str, Any]
) -> tuple[dict[str, Any], Expression | None, dict]:
    """Return the case, its base condition, and its selection.

    The selection maps each micro-operation to ``(guard, origin)``, where
    the guard is the condition under which the case selects it.
    """

    parts = [
        check.expression(text, identifier, "context")
        for text in case["context"]
    ]
    if case["timing_state"] is not None:
        parts.append(("cmp", "TS", "=", str(case["timing_state"])))
    base = conjunction(parts)

    selection: dict[str, tuple[Expression | None, str]] = {}

    def select(
        name: str, guard: Expression | None, origin: str, field: str
    ) -> None:
        if not check.micro_operation(name, identifier, field):
            return
        if name in selection:
            check.error(
                "DUPLICATE_MICRO_OPERATION",
                f"{name} is listed more than once.",
                identifier,
                field,
            )
            return
        selection[name] = (guard, origin)

    for name in case["micro_operations"]:
        select(name, base, MAPPING_ORIGIN, "micro_operations")
    for item in case["conditional_micro_operations"]:
        predicate = check.expression(
            item["predicate"], identifier, "conditional_micro_operations"
        )
        select(
            item["micro_operation"],
            conjunction([base, predicate]),
            CONDITIONAL_ORIGIN,
            "conditional_micro_operations",
        )
    return case, base, selection


# ---------------------------------------------------------------------------
# Overlap
# ---------------------------------------------------------------------------


def can_hold_together(
    first: Expression | None,
    second: Expression | None,
    model: Model,
) -> bool:
    """Return whether both conditions can hold in one reachable state.

    A state is unreachable when it sets both inputs of an exclusive pair to
    1 or violates a timing constraint. Each compared name ranges over the
    values it is compared with plus one other value; a name compared with
    nothing is unconstrained. The search assigns the condition's names
    first and abandons a partial state as soon as the condition is false or
    the state is unreachable.
    """

    condition = conjunction([first, second])
    if condition is None:
        condition = ("const", True)

    domains: dict[str, dict[str, None]] = {}
    for expression in (condition, *model.timing_violations):
        for node in walk(expression):
            if node[0] == "cmp":
                domains.setdefault(node[1], {})[node[3]] = None
    own = compared_names(condition)
    names = own + sorted(set(domains) - set(own))
    choices = [[*domains[name], None] for name in names]  # None: other

    def unreachable(values: dict[str, Any]) -> bool:
        return any(
            values.get(left) == "1" and values.get(right) == "1"
            for left, right in model.exclusive_pairs
        ) or any(
            evaluate(violation, values) is True
            for violation in model.timing_violations
        )

    def search(position: int, values: dict[str, Any]) -> bool:
        if evaluate(condition, values) is False or unreachable(values):
            return False
        if position == len(names):
            return True
        for value in choices[position]:
            values[names[position]] = value
            if search(position + 1, values):
                return True
        del values[names[position]]
        return False

    return search(0, {})


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def describe(item: dict[str, Any]) -> str:
    value = (
        item["value"]
        if "value" in item
        else f"input {item['value_from_input']}"
    )
    return (
        f"{value} from {item['origin']} {item['source']} when {item['when']}"
    )


def build_case(
    model: Model,
    case: dict[str, Any],
    base: Expression | None,
    selection: dict[str, tuple[Expression | None, str]],
) -> tuple[dict[str, Any], list[Diagnostic]]:
    """Build one case's symbolic control word.

    Reports each field that two assignments can set to different values in
    one reachable state.
    """

    diagnostics = []
    identifier = case["id"]
    assignments: dict[str, list[dict[str, Any]]] = {
        name: [] for name in model.words
    }
    guards: dict[str, list[Expression | None]] = {
        name: [] for name in model.words
    }
    conflicting: set[str] = set()

    def add(
        assignment: Assignment,
        guard: Expression | None,
        origin: str,
        source: str,
    ) -> None:
        field = assignment.field
        key = "value_from_input" if assignment.from_input else "value"
        item = {
            key: assignment.value,
            "when": canonical(guard),
            "origin": origin,
            "source": source,
        }
        if field not in conflicting:
            for prior, prior_guard in zip(assignments[field], guards[field]):
                same = prior.get(key) == assignment.value
                if not same and can_hold_together(prior_guard, guard, model):
                    conflicting.add(field)
                    diagnostics.append(
                        make_error(
                            "CONFLICTING_ASSIGNMENTS",
                            f"{describe(prior)} conflicts with "
                            f"{describe(item)}.",
                            identifier,
                            field,
                        )
                    )
                    break
        assignments[field].append(item)
        guards[field].append(guard)

    for name, (guard, origin) in selection.items():
        for assignment in model.mappings[name]:
            add(assignment, guard, origin, name)

    guards_by_name = {name: guard for name, (guard, _) in selection.items()}
    applicable = []
    for definition in model.direct:
        context = substitute_selected(definition.context, guards_by_name)
        if not can_hold_together(base, context, model):
            continue
        guard = conjunction([base, context])
        applicable.append(definition.id)
        for assignment, origin in definition.assignments:
            add(assignment, guard, origin, definition.id)

    symbolic = {
        "execution_case_id": identifier,
        "source": case["source"],
        "base_context": canonical(base),
        "defaults": dict(model.defaults),
        "field_assignments": assignments,
        "selected_micro_operations": {
            name: canonical(guards_by_name[name])
            for name in sorted(guards_by_name)
        },
        "applicable_direct_control_definitions": applicable,
    }
    return symbolic, diagnostics


def generate(model: Model) -> tuple[list[dict[str, Any]], list[Diagnostic]]:
    """Build every case's symbolic control word, in execution order."""

    cases = []
    diagnostics = []
    for case, base, selection in model.cases:
        symbolic, case_diagnostics = build_case(model, case, base, selection)
        cases.append(symbolic)
        diagnostics += case_diagnostics
    return cases, diagnostics


# ---------------------------------------------------------------------------
# Review against the maintained artifact
# ---------------------------------------------------------------------------


def review_changes(
    generated: Sequence[dict[str, Any]],
    maintained: dict[str, dict[str, Any]],
) -> list[Diagnostic]:
    """Warn about new, changed, and stale cases."""

    diagnostics = []
    generated_ids = set()

    for case in generated:
        identifier = case["execution_case_id"]
        generated_ids.add(identifier)
        previous = maintained.get(identifier)
        if previous is None:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "NEW_CASE",
                    "Case is not present in the maintained artifact.",
                    identifier,
                )
            )
            continue
        changed = [
            key
            for key in dict.fromkeys([*case, *previous])
            if case.get(key) != previous.get(key)
        ]
        if changed:
            diagnostics.append(
                Diagnostic(
                    WARNING,
                    "CHANGED_CASE",
                    "Generated case differs from the maintained artifact in: "
                    + ", ".join(changed)
                    + ".",
                    identifier,
                )
            )

    diagnostics.extend(
        Diagnostic(
            WARNING,
            "STALE_CASE",
            "Maintained case is no longer generated.",
            identifier,
        )
        for identifier in maintained
        if identifier not in generated_ids
    )
    return diagnostics


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


def build_candidate(
    documents: dict[str, dict[str, Any]],
    maintained: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[Diagnostic]]:
    """Validate the inputs and build the candidate artifact.

    Returns ``(None, diagnostics)`` when any error is found; otherwise the
    candidate and its warnings.
    """

    diagnostics, indexes = validate_inputs(documents)
    version = documents["words"].get("control_design_version")
    maintained_diagnostics, maintained_cases = validate_maintained(
        maintained, version
    )
    diagnostics += maintained_diagnostics
    if has_failures(diagnostics):
        return None, diagnostics

    model, diagnostics = resolve_inputs(documents, indexes)
    if model is None:
        return None, diagnostics

    cases, diagnostics = generate(model)
    if has_failures(diagnostics):
        return None, diagnostics

    candidate = {
        "format_version": FORMAT_VERSION,
        "control_design_version": model.version,
        "artifact": ARTIFACT,
        "generation_stage": GENERATION_STAGE,
        "representation": REPRESENTATION,
        "sources": [spec.file_name for spec in INPUT_SPECS],
        "cases": cases,
        "diagnostics": [],
    }
    return candidate, review_changes(cases, maintained_cases)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def serialize_json(data: dict[str, Any]) -> str:
    """Serialize JSON preserving key order, with a trailing newline."""

    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


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


def format_heading(diagnostic: Diagnostic) -> str:
    """Return ``SEVERITY CODE`` followed by any bracketed id and field."""

    text = f"{diagnostic.severity} {diagnostic.code}"
    if diagnostic.entry_id:
        text += f" [{diagnostic.entry_id}]"
    if diagnostic.field_name:
        text += f" [{diagnostic.field_name}]"
    return text


def build_report(
    diagnostics: Sequence[Diagnostic],
    case_count: int,
    candidate_written: bool,
) -> str:
    """Build the human-readable generation report."""

    counts = {
        severity: sum(item.severity == severity for item in diagnostics)
        for severity in SEVERITIES
    }
    title = "Symbolic Control-Word Generation Report"
    lines = [
        title,
        "=" * len(title),
        "",
        f"Cases generated: {case_count}",
        f"Candidate written: {'yes' if candidate_written else 'no'}",
        f"Information diagnostics: {counts[INFO]}",
        f"Warnings: {counts[WARNING]}",
        f"Errors: {counts[ERROR]}",
        f"Fatal errors: {counts[FATAL]}",
        "",
        "Diagnostics",
        "-----------",
    ]
    lines += [
        f"{format_heading(item)}: {item.message}" for item in diagnostics
    ] or ["No diagnostics."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def parse_arguments(
    arguments: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Generate reviewable symbolic control words."
    )
    parser.add_argument(
        "--repo-root",
        required=True,
        type=Path,
        help="Path to the repository root.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=DEFAULT_ARTIFACT_DIRECTORY,
        help="Directory holding the six input specifications.",
    )
    parser.add_argument(
        "--maintained",
        type=Path,
        default=DEFAULT_MAINTAINED,
        help="Maintained symbolic control-word artifact; may be absent.",
    )
    parser.add_argument(
        "--candidate-output",
        type=Path,
        default=DEFAULT_CANDIDATE,
        help="Candidate artifact output path.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=DEFAULT_REPORT,
        help="Generation report output path.",
    )
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the generator; return 1 if any error-level diagnostic exists.

    Relative paths are resolved from the repository root.
    """

    options = parse_arguments(arguments)
    root = options.repo_root.resolve()
    artifact_directory = resolve_from_repo(root, options.artifact_dir)
    input_paths = {
        spec.key: artifact_directory / spec.file_name for spec in INPUT_SPECS
    }
    maintained_path = resolve_from_repo(root, options.maintained)
    candidate_path = resolve_from_repo(root, options.candidate_output)
    report_path = resolve_from_repo(root, options.report_output)

    try:
        remove_previous_outputs(
            (candidate_path, report_path),
            (*input_paths.values(), maintained_path),
        )
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}")
        return 1

    diagnostics: list[Diagnostic] = []
    case_count = 0
    candidate_written = False

    try:
        documents = {key: read_json(path) for key, path in input_paths.items()}
        maintained = read_json(maintained_path, optional=True)
        candidate, diagnostics = build_candidate(documents, maintained)

        if candidate is not None:
            case_count = len(candidate["cases"])
            write_text(candidate_path, serialize_json(candidate))
            candidate_written = True
    except GenerationFailure as error:
        diagnostics = [Diagnostic(FATAL, "GENERATION_FAILURE", str(error))]

    diagnostics = sorted(diagnostics, key=diagnostic_sort_key)
    write_text(
        report_path, build_report(diagnostics, case_count, candidate_written)
    )

    failures = [
        item for item in diagnostics if item.severity in FAILURE_SEVERITIES
    ]
    exit_code = 1 if failures else 0

    print("Symbolic control-word generation")
    print(f"Status: {'FAILED' if exit_code else 'SUCCEEDED'}")
    print(f"Cases: {case_count}")
    print(f"Candidate written: {'yes' if candidate_written else 'no'}")
    print(f"Diagnostics: {len(diagnostics)}")
    print(f"Candidate output: {candidate_path}")
    print(f"Report output: {report_path}")

    if failures:
        print()
        print("Failure diagnostics")
        print("-------------------")
        for item in failures:
            print(format_heading(item))
            print(f"  {item.message}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
