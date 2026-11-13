"""Control predicates shared by the ROM-generation tools.

Holds the expression grammar used by the maintained specifications, its
three-valued evaluation, the value domain of every name an expression may
compare, and the reachability rules (exclusive input pairs and timing
constraints). Every tool that interprets a predicate uses this module, so
all tools read a predicate the same way.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

STATE_NAMES = ("MS", "TS")
TIMING_STATES = (1, 2, 3, 4)
# MS has no field of its own; its states are the meanings of the values of
# the field that loads it.
MAJOR_STATE_FIELD = "MS_NEXT"
EXCLUSIVE_KINDS = ("exactly_one", "at_most_one")
MUTUAL_EXCLUSION = re.compile(r"Mutually exclusive with ([^.`]+)\.?")


class ExpressionError(Exception):
    """An expression or assignment could not be parsed."""


def is_binary(value: Any) -> bool:
    return isinstance(value, str) and bool(value) and set(value) <= {"0", "1"}


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
# Domains and reachability
# ---------------------------------------------------------------------------


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


def exclusive_pairs(
    input_fields: dict[str, dict[str, Any]],
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

    for name, field in input_fields.items():
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


def can_hold_together(
    first: Expression | None,
    second: Expression | None,
    exclusive_pairs: Sequence[tuple[str, str]],
    timing_violations: Sequence[Expression],
    ir_values: "IrValues | None" = None,
) -> bool:
    """Return whether both conditions can hold in one reachable state.

    A state is unreachable when it sets both inputs of an exclusive pair to
    1, violates a timing constraint, or, given ``ir_values``, gives the
    IR-derived inputs values that no single IR value produces. Each
    compared name ranges over the
    values it is compared with plus one other value; a name compared with
    nothing is unconstrained. The search assigns the condition's names
    first and abandons a partial state as soon as the condition is false or
    the state is unreachable.
    """

    condition = conjunction([first, second])
    if condition is None:
        condition = ("const", True)

    domains: dict[str, dict[str, None]] = {}
    for expression in (condition, *timing_violations):
        for node in walk(expression):
            if node[0] == "cmp":
                domains.setdefault(node[1], {})[node[3]] = None
    own = compared_names(condition)
    names = own + sorted(set(domains) - set(own))
    choices = [[*domains[name], None] for name in names]  # None: other
    derived = [
        name for name in names if ir_values is not None and name in ir_values
    ]

    def no_ir_value(values: dict[str, Any]) -> bool:
        remaining = ALL_IR_VALUES
        for name in derived:
            if name in values:
                remaining &= ir_values.matching(name, values[name], domains[name])
                if not remaining:
                    return True
        return False

    def unreachable(values: dict[str, Any]) -> bool:
        return (derived and no_ir_value(values)) or any(
            values.get(left) == "1" and values.get(right) == "1"
            for left, right in exclusive_pairs
        ) or any(
            evaluate(violation, values) is True
            for violation in timing_violations
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
# IR derivations
#
# Each IR-derived control input documents its derivation as a function of
# the 12-bit IR (IR-Derived Flags, section 1.1). A derivation is parsed into
#
#   ("bits", high, low)          IR[high:low]
#   ("name", NAME)               another IR-derived input
#   ("eq", operand, literal)     operand == binary literal
#   ("not", x) / ("and", x, y) / ("or", x, y)
#
# and evaluated for every IR value.
# ---------------------------------------------------------------------------

IR_WIDTH = 12
DERIVATION_COMMENT = "//"
DERIVATION_TOKEN = re.compile(
    r"\s*(?:(IR\[(\d+)(?::(\d+))?\])|(==|=)|([()])|(AND|OR|NOT)\b"
    r"|([01]+)\b|([A-Za-z_/][A-Za-z0-9_/]*))"
)


class DerivationError(Exception):
    """A derivation could not be parsed or evaluated."""


def strip_derivation_comments(text: str) -> str:
    """Drop everything from ``//`` to the end of each line."""

    return "\n".join(
        line.split(DERIVATION_COMMENT, 1)[0] for line in text.splitlines()
    )


def tokenize_derivation(text: str) -> list[tuple]:
    tokens: list[tuple] = []
    text = strip_derivation_comments(text)
    position = 0
    while text[position:].strip():
        match = DERIVATION_TOKEN.match(text, position)
        if match is None:
            raise DerivationError(
                f"Unexpected text {text[position:].strip()[:20]!r}."
            )
        position = match.end()
        bits, high, low, compare, paren, logic, literal, name = match.groups()
        if bits:
            high_bit = int(high)
            low_bit = int(low) if low is not None else high_bit
            if not IR_WIDTH > high_bit >= low_bit >= 0:
                raise DerivationError(f"Invalid IR bit range {bits}.")
            tokens.append(("bits", high_bit, low_bit))
        elif compare:
            tokens.append(("compare", compare))
        elif paren:
            tokens.append(("paren", paren))
        elif logic:
            tokens.append(("logic", logic))
        elif literal:
            tokens.append(("literal", literal))
        else:
            tokens.append(("name", name))
    return tokens


def parse_derivation(text: str) -> tuple[str, tuple]:
    """Parse ``NAME = expression`` into the name and the expression."""

    tokens = tokenize_derivation(text)
    if (
        len(tokens) < 3
        or tokens[0][0] != "name"
        or tokens[1] != ("compare", "=")
    ):
        raise DerivationError("Derivation must read 'NAME = expression'.")
    position = 2

    def peek(kind: str, value: str | None = None) -> bool:
        if position >= len(tokens):
            return False
        token = tokens[position]
        return token[0] == kind and (value is None or token[1] == value)

    def take() -> tuple:
        nonlocal position
        token = tokens[position]
        position += 1
        return token

    def disjunction() -> tuple:
        node = conjunction()
        while peek("logic", "OR"):
            take()
            node = ("or", node, conjunction())
        return node

    def conjunction() -> tuple:
        node = negation()
        while peek("logic", "AND"):
            take()
            node = ("and", node, negation())
        return node

    def negation() -> tuple:
        if peek("logic", "NOT"):
            take()
            return ("not", negation())
        return comparison()

    def comparison() -> tuple:
        if peek("paren", "("):
            take()
            node = disjunction()
            if not peek("paren", ")"):
                raise DerivationError("Missing closing parenthesis.")
            take()
        elif peek("bits"):
            node = take()
        elif peek("name"):
            node = ("name", take()[1])
        else:
            raise DerivationError("Expected IR bits, a signal, or '('.")
        if peek("compare"):
            take()
            if not peek("literal"):
                raise DerivationError("Expected a binary literal.")
            node = ("eq", node, take()[1])
        return node

    expression = disjunction()
    if position != len(tokens):
        raise DerivationError(f"Unexpected token {tokens[position][-1]!r}.")
    return tokens[0][1], expression


def derivation_names(expression: tuple) -> list[str]:
    """Return the IR-derived inputs a derivation refers to."""

    kind = expression[0]
    if kind == "name":
        return [expression[1]]
    if kind == "bits":
        return []
    if kind in ("eq", "not"):
        return derivation_names(expression[1])
    return derivation_names(expression[1]) + derivation_names(expression[2])


IR_DERIVED_DOMAIN = "IR-Derived Signals"


def mentions_ir(text: str) -> bool:
    return "IR[" in strip_derivation_comments(text)


def is_ir_derived(field: dict[str, Any], text: str) -> bool:
    """Whether a derivation must be a function of IR alone.

    True for every input of the IR-Derived Signals domain, including one
    built only from other IR-derived inputs, and for any derivation that
    reads IR bits directly.
    """

    return field.get("domain") == IR_DERIVED_DOMAIN or mentions_ir(text)


def ir_derivation_table(
    input_fields: dict[str, dict[str, Any]],
) -> tuple[dict[str, tuple[str, ...]], list[tuple[str, str]]]:
    """Evaluate every IR-derived input for every IR value.

    Returns ``(table, problems)``. ``table`` maps each input whose
    derivation depends only on IR and other IR-derived inputs to its values
    for IR = 0 to 4095, each a binary string of the input's width.
    ``problems`` lists ``(input, message)`` for IR-derived inputs (the
    IR-Derived Signals domain, or any derivation that reads IR bits) whose
    derivations cannot be used. Other inputs are ignored.
    """

    parsed: dict[str, tuple] = {}
    problems: list[tuple[str, str]] = []
    for name, field in input_fields.items():
        derivation = field.get("derivation")
        text = derivation.get("text") if isinstance(derivation, dict) else None
        if not isinstance(text, str) or not is_ir_derived(field, text):
            continue
        try:
            defined, expression = parse_derivation(text)
        except DerivationError as error:
            problems.append((name, str(error)))
            continue
        if defined != name:
            problems.append((name, f"Derivation defines {defined}, not {name}."))
            continue
        parsed[name] = expression

    # Keep only inputs whose references are all usable, transitively.
    usable = dict(parsed)
    changed = True
    while changed:
        changed = False
        for name, expression in list(usable.items()):
            missing = [n for n in derivation_names(expression) if n not in usable]
            if missing:
                del usable[name]
                problems.append(
                    (
                        name,
                        "Derivation uses "
                        + ", ".join(missing)
                        + ", which is not derived from IR.",
                    )
                )
                changed = True

    widths = {name: int(input_fields[name]["width"]) for name in usable}
    values: dict[str, list[int]] = {}
    active: set[str] = set()

    def operand(node: tuple, ir: int) -> tuple[int, int]:
        """Return ``(value, width)`` of an IR-bits or signal operand."""

        if node[0] == "bits":
            _, high, low = node
            width = high - low + 1
            return (ir >> low) & ((1 << width) - 1), width
        return compute(node[1])[ir], widths[node[1]]

    def condition(node: tuple, ir: int) -> bool:
        kind = node[0]
        if kind in ("bits", "name"):
            value, width = operand(node, ir)
            if width != 1:
                raise DerivationError("A multi-bit value is used as a condition.")
            return value == 1
        if kind == "eq":
            value, width = operand(node[1], ir)
            if len(node[2]) != width:
                raise DerivationError(
                    f"Literal {node[2]} does not have width {width}."
                )
            return value == int(node[2], 2)
        if kind == "not":
            return not condition(node[1], ir)
        if kind == "and":
            return condition(node[1], ir) and condition(node[2], ir)
        return condition(node[1], ir) or condition(node[2], ir)

    def compute(name: str) -> list[int]:
        if name in values:
            return values[name]
        if name in active:
            raise DerivationError(f"{name} is defined in terms of itself.")
        active.add(name)
        try:
            expression = usable[name]
            irs = range(2**IR_WIDTH)
            if expression[0] in ("bits", "name"):
                result = [operand(expression, ir)[0] for ir in irs]
            else:
                result = [int(condition(expression, ir)) for ir in irs]
        finally:
            active.discard(name)
        values[name] = result
        return result

    table: dict[str, tuple[str, ...]] = {}
    for name in usable:
        try:
            column = compute(name)
        except DerivationError as error:
            problems.append((name, str(error)))
            continue
        width = widths[name]
        if any(value >= 2**width for value in column):
            problems.append((name, f"Derived value exceeds {width} bits."))
            continue
        table[name] = tuple(format(value, f"0{width}b") for value in column)
    return table, problems


ALL_IR_VALUES = (1 << 2**IR_WIDTH) - 1


class IrValues:
    """The IR values that give each IR-derived input each of its values.

    Built from an ``ir_derivation_table`` result. Sets of IR values are
    held as integers with bit ``n`` standing for IR = ``n``.
    """

    def __init__(self, table: dict[str, tuple[str, ...]]) -> None:
        self._table = table
        self._sets: dict[tuple[str, str], int] = {}

    def __contains__(self, name: object) -> bool:
        return name in self._table

    def having(self, name: str, value: str) -> int:
        """IR values for which ``name`` has ``value``."""

        key = (name, value)
        if key not in self._sets:
            self._sets[key] = sum(
                1 << ir
                for ir, derived in enumerate(self._table[name])
                if derived == value
            )
        return self._sets[key]

    def matching(
        self, name: str, value: str | None, compared: Iterable[str]
    ) -> int:
        """IR values for which ``name`` has ``value``, or, for ``None``,
        a value other than every one in ``compared``."""

        if value is not None:
            return self.having(name, value)
        result = ALL_IR_VALUES
        for other in compared:
            result &= ~self.having(name, other)
        return result
