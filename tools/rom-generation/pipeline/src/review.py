"""Reviewed decisions that the run's evidence disagrees with, and recording the answers.

Two decisions in the maintained artifacts are made by a reviewer, not generated:

- `control_uses` of each control input (control-input schema): `predicate` when a condition
  reads the input, `value` when its value reaches a register through a source the control word
  selects, or `none` when the control store reads neither (Control Input Definitions §7).
- `control_word_role` of each control-word field (control-word schema): `encoded`, `derived`,
  or `external_input`.

After a run, `collect` compares them with the evidence and returns an `Item` for each that
disagrees, with a proposal and the evidence for it. The proposal is never applied without the
reviewer's answer; `record` writes the answers into the maintained artifacts.

The evidence for `predicate` is exact: the equivalence analyzer's category of the input
(`behavioral` or `no_effect` when a condition reads it). The evidence for `value` is an
encoding of a control-word field that names the input, such as `DF_SRC = IR_DF`; a `value`
already reviewed is kept, because a value can reach a register in ways no encoding names.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

INPUT_SCHEMA, WORD_SCHEMA = "control-input-schema", "control-word-schema"
USES, ROLE = "control_uses", "control_word_role"
CONTROL_USES = ("predicate", "value", "none")
ROLES = ("encoded", "derived", "external_input")
READ_CATEGORIES = ("behavioral", "no_effect")
UNRESOLVED_CODES = {USES: "CONTROL_USES_UNRESOLVED", ROLE: "CONTROL_WORD_ROLE_UNRESOLVED"}


@dataclass
class Item:
    artifact: str                    # INPUT_SCHEMA or WORD_SCHEMA
    name: str
    key: str                         # USES or ROLE
    current: Any
    proposed: Any                    # None when the evidence gives no proposal
    evidence: list[str] = field(default_factory=list)


def _names(text: str) -> set[str]:
    return set(re.findall(r"(?<![A-Za-z0-9_/])(/?[A-Z][A-Z0-9_]*)(?![A-Za-z0-9_])", text))


def control_use_items(schema: dict, analysis: dict, words: dict,
                      outside: dict[str, bool] | None = None) -> list[Item]:
    """The inputs whose reviewed control_uses differ from the evidence. `outside` gives each
    input's Control Input Definitions section 7 listing; by default the schema's own."""
    if outside is None:
        outside = {f["name"]: f["outside_selection"] for f in schema.get("fields", [])
                   if "outside_selection" in f}
    category = {e["name"]: e["category"] for e in analysis.get("inputs", [])
                if e.get("kind") == "control_input"}
    encodings: dict[str, list[str]] = {}
    for f in words.get("fields", []):
        for v in f.get("values") or []:
            for name in _names(str(v.get("meaning", ""))):
                encodings.setdefault(name, []).append(f"{f['name']} = {v.get('meaning')}")
    items = []
    for f in schema.get("fields", []):
        name, current = f["name"], list(f.get(USES) or [])
        if name not in category:
            continue
        read = category[name] in READ_CATEGORIES
        named = encodings.get(name, [])
        evidence = [f"a condition reads it ({category[name]})" if read
                    else f"no condition reads it ({category[name]})"]
        if named:
            evidence.append("named by the encoding " + "; ".join(named[:3]))
        listed = outside.get(name)
        if listed:
            evidence.append("listed outside the control-word selection (Control Input "
                            "Definitions section 7)")
        proposed = (["predicate"] if read else []) + (
            ["value"] if named or "value" in current else [])
        if not proposed:
            if listed:
                proposed = ["none"]
            elif listed is None:
                proposed = None
                evidence.append("the schema does not record section 7; type a classification")
            else:
                proposed = None
                evidence.append("not listed in section 7 either: a specification gap; type a "
                                "classification, or skip and correct the documentation")
        if proposed is None or sorted(proposed) != sorted(current):
            items.append(Item(INPUT_SCHEMA, name, USES, current, proposed, evidence))
    return items


def role_items(words: dict) -> list[Item]:
    """The control-word fields with no reviewed role."""
    items = []
    for f in words.get("fields", []):
        if f.get(ROLE) in ROLES:
            continue
        explicit = f.get("explicit_value_required")
        proposed = "derived" if explicit == "No" else "encoded" if explicit == "Yes" else None
        items.append(Item(WORD_SCHEMA, f["name"], ROLE, f.get(ROLE), proposed,
                          [f"Explicit Value Required: {explicit}"]))
    return items


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def collect(root: Path, input_schema: Path, word_schema: Path, analysis: Path,
            skip: set[tuple[str, str]] = frozenset(),
            input_candidate: Path | None = None) -> list[Item]:
    """Every disagreement, from the maintained schemas and the run's analysis; none when an
    artifact is missing. Items named in `skip` (artifact, name) are left out."""
    schema, words, found = _read(root / input_schema), _read(root / word_schema), _read(root / analysis)
    if schema is None or words is None or found is None:
        return []
    # Section 7 as the documentation now gives it: the run's candidate, when there is one.
    candidate = _read(root / input_candidate) if input_candidate else None
    outside = None
    if candidate is not None and any("outside_selection" in f for f in candidate.get("fields", [])):
        outside = {f["name"]: f.get("outside_selection", False) for f in candidate["fields"]}
    items = control_use_items(schema, found, words, outside) + role_items(words)
    return [i for i in items if (i.artifact, i.name) not in skip]


def parse_answer(item: Item, text: str) -> Any:
    """A typed classification: `predicate,value`, `none`, or a role. ValueError if invalid."""
    text = text.strip().lower()
    if item.key == ROLE:
        if text not in ROLES:
            raise ValueError(f"a role is one of {', '.join(ROLES)}")
        return text
    uses = [u.strip() for u in text.split(",") if u.strip()]
    if not uses or any(u not in CONTROL_USES for u in uses) or len(set(uses)) != len(uses) or (
            "none" in uses and len(uses) > 1):
        raise ValueError("control uses are predicate and value, or none alone")
    return uses


def record(root: Path, paths: dict[str, Path], answers: list[tuple[Item, Any]]) -> None:
    """Write the answers into the maintained artifacts, removing the warning each resolves."""
    by_artifact: dict[str, list[tuple[Item, Any]]] = {}
    for item, value in answers:
        by_artifact.setdefault(item.artifact, []).append((item, value))
    for artifact, pairs in by_artifact.items():
        path = root / paths[artifact]
        data = json.loads(path.read_text(encoding="utf-8"))
        fields = {f["name"]: f for f in data.get("fields", [])}
        resolved = set()
        for item, value in pairs:
            fields[item.name][item.key] = value
            resolved.add((UNRESOLVED_CODES[item.key], item.name))
        if "diagnostics" in data:
            data["diagnostics"] = [
                d for d in data["diagnostics"]
                if (d.get("code"), d.get("input_name") or d.get("field_name")) not in resolved]
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")


def describe(item: Item) -> list[str]:
    proposal = "no proposal" if item.proposed is None else f"proposed {item.proposed}"
    lines = [f"  {item.name}: {item.key} {item.current} -> {proposal}"]
    lines += [f"      {e}" for e in item.evidence]
    return lines
