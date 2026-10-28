"""Validate extracted direct-control definitions against generated schemas."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

DEFAULT_DEFINITIONS = Path("build/simulation_outputs/rom-generation/direct-control-generator/direct-control-definitions.candidate.json")
DEFAULT_INPUT_SCHEMA = Path("build/simulation_outputs/rom-generation/control-input-schema-generator/control-input-schema.candidate.json")
DEFAULT_WORD_SCHEMA = Path("build/simulation_outputs/rom-generation/control-word-schema-generator/control-word-schema.candidate.json")
DEFAULT_MAPPING = Path("build/simulation_outputs/rom-generation/micro-operation-mapping-generator/micro-operation-mapping.candidate.json")
DEFAULT_REPORT = Path("build/simulation_outputs/rom-generation/direct-control-validator/validation-report.txt")
FAILURE_SEVERITIES = {"ERROR", "FATAL"}
SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "FATAL": 3}
ASSIGNMENT = re.compile(r"^\s*([A-Z/][A-Z0-9_/]*(?:\[[^]]+\])?)\s*=\s*(.+?)\s*$")
CONDITION = re.compile(r"^\s*([A-Z/][A-Z0-9_/]*)\s*(=|!=)\s*([^\s]+)\s*$")
SELECTED = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s+is selected\s*$")
CONTROL_ADDRESS_CONTEXT = {"MS", "TS"}

SYMBOLIC_ALIASES = {
    "IOT_TRANSFER_VAL": {
        "NONE": "0",
        "READ": "1",
        "WRITE": "2",
    }
}


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    definition_id: str | None = None
    field: str | None = None


class ValidationFailure(Exception):
    """Raised for unreadable or structurally unusable input artifacts."""


def resolve(root: Path, path: Path) -> Path:
    return path.resolve() if path.is_absolute() else (root / path).resolve()


def load_json(path: Path, expected_type: str | None = None) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValidationFailure(f"Required artifact does not exist: {path}") from error
    except json.JSONDecodeError as error:
        raise ValidationFailure(f"Invalid JSON in {path}: {error}") from error
    except OSError as error:
        raise ValidationFailure(f"Unable to read {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValidationFailure(f"Artifact root must be an object: {path}")
    if expected_type and data.get("specification_type") != expected_type:
        raise ValidationFailure(
            f"Expected specification_type {expected_type!r} in {path}; "
            f"found {data.get('specification_type')!r}."
        )
    return data


def normalized(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def field_index(schema: dict) -> dict[str, dict]:
    return {field["name"]: field for field in schema.get("fields", []) if isinstance(field, dict) and "name" in field}


def mapping_index(mapping: dict) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in mapping.get("mappings", []):
        name = item.get("micro_operation")
        if not isinstance(name, str):
            continue
        result[name] = {
            assignment["field"]: str(assignment["value"])
            for assignment in item.get("assignments", [])
            if isinstance(assignment, dict) and "field" in assignment and "value" in assignment
        }
    return result


def resolve_value(field: dict, token: str) -> str | None:
    token = token.strip()
    if re.fullmatch(r"\d+", token):
        return token
    aliases = SYMBOLIC_ALIASES.get(field.get("name", ""), {})
    if token in aliases:
        return aliases[token]
    target = normalized(token)
    exact: list[str] = []
    prefix: list[str] = []
    for item in field.get("values", []):
        encoding = str(item.get("encoding"))
        meaning = normalized(str(item.get("meaning", "")))
        if meaning == target:
            exact.append(encoding)
        elif meaning.startswith(target) or target.startswith(meaning):
            prefix.append(encoding)
    choices = exact or prefix
    return choices[0] if len(set(choices)) == 1 else None


def parse_assignments(blocks: Sequence[str], definition_id: str, kind: str) -> tuple[list[tuple[str, str]], list[Diagnostic]]:
    assignments: list[tuple[str, str]] = []
    diagnostics: list[Diagnostic] = []
    for block in blocks:
        for line in block.splitlines():
            if not line.strip():
                continue
            match = ASSIGNMENT.match(line)
            if not match:
                diagnostics.append(Diagnostic("ERROR", "MALFORMED_ASSIGNMENT", f"Malformed {kind} assignment: {line}", definition_id))
                continue
            assignments.append((match.group(1), match.group(2)))
    return assignments, diagnostics


def validate_assignment_set(
    assignments: Sequence[tuple[str, str]],
    fields: dict[str, dict],
    definition_id: str,
    kind: str,
) -> tuple[dict[str, str], list[Diagnostic]]:
    resolved: dict[str, str] = {}
    diagnostics: list[Diagnostic] = []
    for name, token in assignments:
        field = fields.get(name)
        if field is None:
            diagnostics.append(Diagnostic("ERROR", "UNKNOWN_CONTROL_FIELD", f"{kind} references unknown control field {name}.", definition_id, name))
            continue
        if field.get("control_word_role") != "encoded":
            diagnostics.append(Diagnostic("ERROR", "NON_ENCODED_CONTROL_FIELD", f"{kind} assigns {name}, whose role is {field.get('control_word_role')!r}.", definition_id, name))
            continue
        value = resolve_value(field, token)
        if value is None:
            diagnostics.append(Diagnostic("ERROR", "UNKNOWN_CONTROL_VALUE", f"Cannot resolve {name} value {token!r} against the control-word schema.", definition_id, name))
            continue
        previous = resolved.get(name)
        if previous is not None and previous != value:
            diagnostics.append(Diagnostic("ERROR", "CONFLICTING_ASSIGNMENT", f"{kind} assigns conflicting values {previous} and {value} to {name}.", definition_id, name))
        resolved[name] = value
    return resolved, diagnostics


def selected_operations(definition: dict) -> set[str]:
    operations: set[str] = set()
    for block in definition.get("applicable_context", []):
        for line in block.splitlines():
            match = SELECTED.match(line)
            if match:
                operations.add(match.group(1))
    return operations


def validate_context(
    definition: dict,
    inputs: dict[str, dict],
    control_fields: dict[str, dict],
    mappings: dict[str, dict[str, str]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    definition_id = definition["id"]
    for block in definition.get("applicable_context", []):
        for line in block.splitlines():
            condition = CONDITION.match(line)
            if condition:
                name = condition.group(1)
                known = (
                    name in inputs
                    or name in control_fields
                    or name in CONTROL_ADDRESS_CONTEXT
                )
                if not known:
                    diagnostics.append(Diagnostic("ERROR", "UNKNOWN_CONTEXT_SYMBOL", f"Applicable context references unknown symbol {name}.", definition_id, name))
            selected = SELECTED.match(line)
            if selected and selected.group(1) not in mappings:
                diagnostics.append(Diagnostic("ERROR", "UNKNOWN_MICRO_OPERATION", f"Applicable context selects unknown micro-operation {selected.group(1)}.", definition_id))
    return diagnostics


def validate_micro_assignments(
    definition: dict,
    resolved: dict[str, str],
    fields: dict[str, dict],
    mappings: dict[str, dict[str, str]],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    definition_id = definition["id"]
    operations = selected_operations(definition)
    if not operations:
        return diagnostics
    for field_name, value in resolved.items():
        default = str(fields[field_name].get("default_value"))
        if value == default:
            continue
        if not any(mappings[operation].get(field_name) == value for operation in operations):
            diagnostics.append(Diagnostic("ERROR", "MICRO_OPERATION_ASSIGNMENT_MISMATCH", f"{field_name}={value} is neither the field default nor supplied by selected micro-operation(s): {', '.join(sorted(operations))}.", definition_id, field_name))
    return diagnostics


def validate_control_supplied_values(
    definition: dict,
    assignments: Sequence[tuple[str, str]],
    resolved: dict[str, str],
    fields: dict[str, dict],
    inputs: dict[str, dict],
) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    definition_id = definition["id"]
    for field_name, token in assignments:
        if field_name not in fields:
            continue
        if re.fullmatch(r"\d+", token) or field_name in resolved:
            if re.fullmatch(r"\d+", token):
                width = int(fields[field_name].get("width", 0))
                if int(token) >= 2**width:
                    diagnostics.append(Diagnostic("ERROR", "VALUE_OUT_OF_RANGE", f"{field_name} value {token} does not fit width {width}.", definition_id, field_name))
            continue
        source = inputs.get(token)
        if source is None:
            diagnostics.append(Diagnostic("ERROR", "UNKNOWN_VALUE_SOURCE", f"{field_name} is supplied from unknown control input {token}.", definition_id, field_name))
            continue
        if "value" not in source.get("control_uses", []):
            diagnostics.append(Diagnostic("ERROR", "INPUT_NOT_VALUE_CAPABLE", f"Control input {token} is not declared for value use.", definition_id, field_name))
        if int(source.get("width", -1)) != int(fields[field_name].get("width", -2)):
            diagnostics.append(Diagnostic("ERROR", "VALUE_WIDTH_MISMATCH", f"{token} width {source.get('width')} does not match {field_name} width {fields[field_name].get('width')}.", definition_id, field_name))
    return diagnostics


def validate_versions(artifacts: Sequence[tuple[str, dict]]) -> list[Diagnostic]:
    versions = {name: data.get("control_design_version") for name, data in artifacts}
    unique = set(versions.values())
    if len(unique) <= 1:
        return []
    return [Diagnostic("ERROR", "CONTROL_DESIGN_VERSION_MISMATCH", ", ".join(f"{name}={version!r}" for name, version in versions.items()))]


def validate(definitions: dict, input_schema: dict, word_schema: dict, mapping: dict) -> list[Diagnostic]:
    diagnostics = validate_versions((("definitions", definitions), ("inputs", input_schema), ("word", word_schema), ("mapping", mapping)))
    fields = field_index(word_schema)
    inputs = field_index(input_schema)
    mappings = mapping_index(mapping)
    seen: set[str] = set()
    for definition in definitions.get("definitions", []):
        definition_id = definition.get("id")
        if not isinstance(definition_id, str):
            diagnostics.append(Diagnostic("ERROR", "MISSING_DEFINITION_ID", "Definition has no string id."))
            continue
        if definition_id in seen:
            diagnostics.append(Diagnostic("ERROR", "DUPLICATE_DEFINITION_ID", f"Duplicate definition id {definition_id}.", definition_id))
        seen.add(definition_id)
        diagnostics.extend(validate_context(definition, inputs, fields, mappings))
        combined: dict[str, str] = {}
        for key, kind in (("direct_assignments", "direct-control"), ("micro_operation_assignments", "micro-operation")):
            parsed, found = parse_assignments(definition.get(key, []), definition_id, kind)
            diagnostics.extend(found)
            resolved, found = validate_assignment_set(parsed, fields, definition_id, kind)
            diagnostics.extend(found)
            for field_name, value in resolved.items():
                prior = combined.get(field_name)
                if prior is not None and prior != value:
                    diagnostics.append(Diagnostic("ERROR", "CROSS_DOMAIN_ASSIGNMENT_CONFLICT", f"Direct-control and micro-operation assignments conflict on {field_name}: {prior} versus {value}.", definition_id, field_name))
                combined[field_name] = value
            if key == "micro_operation_assignments":
                diagnostics.extend(validate_micro_assignments(definition, resolved, fields, mappings))
        supplied, found = parse_assignments(definition.get("control_supplied_values", []), definition_id, "control-supplied value")
        diagnostics.extend(found)
        # Resolve only literal/symbolic constants here; input names are validated separately.
        literal_pairs = [(name, token) for name, token in supplied if token not in inputs]
        supplied_resolved, found = validate_assignment_set(literal_pairs, fields, definition_id, "control-supplied value")
        diagnostics.extend(found)
        diagnostics.extend(validate_control_supplied_values(definition, supplied, supplied_resolved, fields, inputs))
    diagnostics.sort(key=lambda item: (SEVERITY_ORDER.get(item.severity, 99), item.code, item.definition_id or "", item.field or "", item.message))
    return diagnostics


