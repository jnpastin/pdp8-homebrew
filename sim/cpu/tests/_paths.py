"""Test helper: put the simulator packages and the packer source on the import path."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
for src in (REPO / "sim" / "cpu" / "src", REPO / "sim" / "memory" / "src",
            REPO / "tools" / "rom-generation" / "control-store-packer" / "src"):
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from pdp8_cpu import encodings as E


def blank_fields(**overrides) -> dict:
    """A datapath word with every field at its default: loads off, strobes deasserted."""
    fields = {name: 0 for name in E.DATAPATH_FIELDS}
    for name in ("/RD", "/WR", "/DB_READ", "/DB_WRITE"):
        fields[name] = 1
    fields.update(overrides)
    return fields
