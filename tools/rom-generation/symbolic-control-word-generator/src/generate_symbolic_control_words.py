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
import sys
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))

from predicates import (  # noqa: E402  (shared ROM-generation module)
    EXCLUSIVE_KINDS,
    TIMING_STATES,
    Expression,
    ExpressionError,
    IrValues,
    can_hold_together,
    canonical,
    compared_names,
    conjunction,
    disjunction,
    evaluate,  # re-exported for the tests
    exclusive_pairs,
    ir_derivation_table,
    is_binary,
    parse_expression,
    selected_names,
    substitute_selected,
    value_domains,
    walk,
)

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

# Run-mode context default (Execution Model §2.3): a context that does not
# compare RUN applies only while running.
RUN_NAME = "RUN"
RUN_DEFAULT: Expression = ("cmp", RUN_NAME, "=", "1")

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
# Assignment blocks
#
# The expression grammar, evaluation, value domains and reachability rules
# live in the shared module tools/rom-generation/common/predicates.py.
# ---------------------------------------------------------------------------

ASSIGNMENT_PATTERN = re.compile(r"\s*([^\s=]+)\s*=\s*(\S+)\s*")


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


# ---------------------------------------------------------------------------
# Run-mode context default
# ---------------------------------------------------------------------------


def compares_run(expression: Expression | None) -> bool:
    return expression is not None and RUN_NAME in compared_names(expression)


def with_run_default(expression: Expression | None) -> Expression:
    """Add ``RUN = 1`` to a context that does not compare RUN.

    A context that tests a micro-operation selection is left unchanged:
    it takes its run mode from the case that selects the micro-operation.
    """

    if compares_run(expression):
        return expression
    if expression is not None and selected_names(expression):
        return expression
    return conjunction([expression, RUN_DEFAULT])


def conjuncts(expression: Expression | None) -> list[Expression]:
    """Return the top-level AND terms of an expression."""

    if expression is None:
        return []
    if expression[0] == "and":
        return conjuncts(expression[1]) + conjuncts(expression[2])
    return [expression]


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
    ir_values: IrValues
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
                    identifier,
                    disjunction([with_run_default(c) for c in contexts]),
                    tuple(assignments),
                )
            )

    ir_table, ir_problems = ir_derivation_table(indexes["inputs"])
    for name, message in ir_problems:
        check.error(
            "IR_DERIVATION_UNUSABLE",
            f"IR derivation cannot be evaluated: {message}",
            name,
            "derivation",
        )

    if RUN_NAME not in check.input_names:
        check.error(
            "RUN_INPUT_MISSING",
            "The run-mode context default requires the control input RUN.",
            "control-input-schema.json",
            RUN_NAME,
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
            indexes["inputs"], documents["inputs"]["constraints"]
        ),
        timing_violations=tuple(violations),
        ir_values=IrValues(ir_table),
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
    base = with_run_default(conjunction(parts))
    running = RUN_DEFAULT in conjuncts(base)

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
        # A predicate within a running case already has RUN = 1 from the
        # case base; elsewhere the default applies to the predicate itself.
        if predicate is not None and not running:
            predicate = with_run_default(predicate)
        select(
            item["micro_operation"],
            conjunction([base, predicate]),
            CONDITIONAL_ORIGIN,
            "conditional_micro_operations",
        )
    return case, base, selection


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
                if not same and can_hold_together(
                    prior_guard, guard, model.exclusive_pairs,
                    model.timing_violations, model.ir_values,
                ):
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
        if not can_hold_together(
            base, context, model.exclusive_pairs, model.timing_violations,
            model.ir_values,
        ):
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
