"""How a candidate artifact differs from the maintained one.

A documentation edit that only adds or removes lines shifts the source line of every entry after
it. Those entries have not changed in substance, so they are reported apart from the entries that
have. Each entry of a candidate is classified against the maintained artifact as one of:

- ``material``: its content differs, ignoring source line numbers
- ``moved``: only its source line numbers differ
- ``renamed``: it is new under its identifier, and its content equals that of exactly one
  maintained entry that is no longer present, as when a documentation section is renumbered
- ``added``: it is new
- ``removed``: a maintained entry that is no longer present

Source line numbers are the values of the keys in `LOCATION_KEYS`, at any depth. A changed source
path is material.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

LOCATION_KEYS = frozenset({"line", "source_line"})
IDENTITY_KEYS = ("id", "execution_case_id", "micro_operation", "name")
# A renumbered section renumbers the title and group that quote it, so the leading section
# number of these is ignored when looking for a rename.
NUMBERED_KEYS = frozenset({"title", "group"})
_SECTION_NUMBER = re.compile(r"^\d+(?:\.\d+)*\.?\s+")

MATERIAL, MOVED, RENAMED, ADDED, REMOVED = "material", "moved", "renamed", "added", "removed"
KINDS = (MATERIAL, RENAMED, ADDED, REMOVED, MOVED)


@dataclass(frozen=True)
class EntryChange:
    kind: str
    identifier: str
    previous: str | None = None      # for a rename, the maintained identifier


def strip_locations(value: Any) -> Any:
    """`value` with every source line number removed."""
    if isinstance(value, dict):
        return {k: strip_locations(v) for k, v in value.items() if k not in LOCATION_KEYS}
    if isinstance(value, list):
        return [strip_locations(v) for v in value]
    return value


def _content_key(entry: Any) -> str:
    if isinstance(entry, dict):
        entry = {k: (_SECTION_NUMBER.sub("", v) if k in NUMBERED_KEYS and isinstance(v, str) else v)
                 for k, v in entry.items() if k not in IDENTITY_KEYS}
    return json.dumps(strip_locations(entry), sort_keys=True, ensure_ascii=False)


def compare_entries(maintained: Mapping[str, Any], candidate: Mapping[str, Any],
                    prefix: str = "") -> list[EntryChange]:
    """Classify each changed entry, in candidate order, then the removed ones in maintained
    order. Unchanged entries are omitted."""
    removed = [i for i in maintained if i not in candidate]
    pool: dict[str, list[str]] = defaultdict(list)
    for i in removed:
        pool[_content_key(maintained[i])].append(i)
    renamed_from: dict[str, str] = {}
    for i, entry in candidate.items():
        if i not in maintained:
            matches = pool.get(_content_key(entry))
            if matches and len(matches) == 1:
                renamed_from[i] = matches.pop()
    changes = []
    for i, entry in candidate.items():
        if i in renamed_from:
            changes.append(EntryChange(RENAMED, prefix + i, prefix + renamed_from[i]))
        elif i not in maintained:
            changes.append(EntryChange(ADDED, prefix + i))
        elif entry == maintained[i]:
            continue
        elif strip_locations(entry) == strip_locations(maintained[i]):
            changes.append(EntryChange(MOVED, prefix + i))
        else:
            changes.append(EntryChange(MATERIAL, prefix + i))
    used = set(renamed_from.values())
    changes += [EntryChange(REMOVED, prefix + i) for i in removed if i not in used]
    return changes


def _identity_key(*lists: Sequence[Any]) -> str | None:
    items = [x for lst in lists for x in lst]
    if not items or not all(isinstance(x, dict) for x in items):
        return None
    for key in IDENTITY_KEYS:
        if all(isinstance(x.get(key), str) for x in items):
            if all(len({x[key] for x in lst}) == len(lst) for lst in lists):
                return key
    return None


def _single(key: str, old: Any, new: Any) -> list[EntryChange]:
    if old == new:
        return []
    if old is None:
        return [EntryChange(ADDED, key)]
    if new is None:
        return [EntryChange(REMOVED, key)]
    kind = MOVED if strip_locations(old) == strip_locations(new) else MATERIAL
    return [EntryChange(kind, key)]


def compare_artifacts(maintained: Mapping[str, Any] | None,
                      candidate: Mapping[str, Any]) -> list[EntryChange]:
    """Classify the differences between two artifacts. A top-level list of entries that all
    carry a unique identifier (`IDENTITY_KEYS`) is compared entry by entry, as
    ``key:identifier``; any other top-level value is compared as one entry named by its key."""
    maintained = maintained or {}
    changes: list[EntryChange] = []
    for key in dict.fromkeys([*candidate, *maintained]):
        old, new = maintained.get(key), candidate.get(key)
        if isinstance(old, list) and isinstance(new, list):
            ident = _identity_key(old, new)
            if ident is not None:
                changes += compare_entries({x[ident]: x for x in old}, {x[ident]: x for x in new},
                                           prefix=f"{key}:")
                continue
        changes += _single(key, old, new)
    return changes


def counts(changes: Sequence[EntryChange]) -> Counter:
    return Counter(c.kind for c in changes)


def describe(changes: Sequence[EntryChange]) -> str:
    """For example ``2 material, 1 renamed, 41 moved (source lines only)``."""
    n = counts(changes)
    parts = [f"{n[k]} {k}" + (" (source lines only)" if k == MOVED else "") for k in KINDS if n[k]]
    return ", ".join(parts) if parts else "no entry changes"


def only_moved(changes: Sequence[EntryChange]) -> bool:
    return bool(changes) and all(c.kind == MOVED for c in changes)
