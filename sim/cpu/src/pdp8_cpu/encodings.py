"""Control-word field encodings, written from the documentation.

Sources (paths relative to the repository root):

- MCS  = docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md §5
- ACS  = docs/04-control/20-control-output-definitions/02-architectural-control-signals.md §4
- SCS  = docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md §4
- CSO  = docs/04-control/08-control-store-organization.md

`check_against_schema` compares these definitions with the promoted
`rom/microcode/v1/control-word-schema.json`, so a disagreement between the documentation as read
here and the extracted artifact stops the simulator at startup.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

LOAD = {0: "no load", 1: "load"}
ACTIVE_LOW = {0: "asserted", 1: "deasserted"}
BOOL_VAL = {0: "0", 1: "1"}


@dataclass(frozen=True)
class FieldDef:
    name: str
    width: int
    values: dict
    cite: str

    def meaning(self, code: int) -> str:
        return self.values.get(code, "unlisted")

    def is_reserved(self, code: int) -> bool:
        return self.values.get(code, "reserved") in ("reserved", "invalid")


def _f(name, width, values, cite):
    return FieldDef(name, width, dict(values), cite)


# Datapath-slice fields (CSO §4.2), encodings from MCS §5 and ACS §4.1-§4.4.
DATAPATH_FIELDS = {f.name: f for f in [
    _f("/RD", 1, ACTIVE_LOW, "ACS §4.1"),
    _f("/WR", 1, ACTIVE_LOW, "ACS §4.2"),
    _f("/DB_READ", 1, ACTIVE_LOW, "ACS §4.3"),
    _f("/DB_WRITE", 1, ACTIVE_LOW, "ACS §4.4"),
    _f("AB_SRC", 1, {0: "MA", 1: "PC"}, "MCS AB_SRC"),
    _f("AC_LOAD", 1, LOAD, "MCS AC_LOAD"),
    _f("AC_SRC", 3, {0: "IDB", 1: "DB", 2: "IF (field-merge)", 3: "DF (field-merge)",
                     4: "IB (field-merge)", 5: "MQ", 6: "GTF_FLAGS", 7: "reserved"}, "MCS AC_SRC"),
    _f("ALU_A_SRC", 2, {0: "AC", 1: "MB", 2: "PC", 3: "reserved"}, "MCS ALU_A_SRC"),
    _f("ALU_B_SRC", 2, {0: "NONE", 1: "MB", 2: "MQ", 3: "FP_SR"}, "MCS ALU_B_SRC"),
    _f("ALU_OP", 4, {0: "ADD", 1: "AND", 2: "OR", 3: "NOT", 4: "INC", 5: "ROR", 6: "ROL",
                     7: "RTR", 0o10: "RTL", 0o11: "BSW", 0o12: "CLEAR",
                     **{c: "reserved" for c in range(0o13, 0o20)}}, "MCS ALU_OP"),
    _f("CIFP_LOAD", 1, LOAD, "MCS CIFP_LOAD"),
    _f("CIFP_VAL", 1, BOOL_VAL, "MCS CIFP_VAL"),
    _f("DF_LOAD", 1, LOAD, "MCS DF_LOAD"),
    _f("DF_SRC", 3, {0: "Zero (hardwired 000)", 1: "IB", 2: "FP_DF", 3: "AC[2:0]",
                     4: "IR_DF (IR[5:3])", 5: "reserved", 6: "reserved", 7: "reserved"}, "MCS DF_SRC"),
    _f("DIF_LOAD", 1, LOAD, "MCS DIF_LOAD"),
    _f("DIF_SRC", 3, {0: "IB", 1: "Zero (hardwired 000)", 2: "FP_IF", 3: "AC[5:3]",
                      4: "IR_IF (IR[5:3])", 5: "reserved", 6: "reserved", 7: "reserved"}, "MCS DIF_SRC"),
    _f("EA_ADDR_LOAD", 1, LOAD, "MCS EA_ADDR_LOAD"),
    _f("EA_ADDR_SRC", 1, {0: "IDB", 1: "IR address formation unit"}, "MCS EA_ADDR_SRC"),
    _f("IB_LOAD", 1, LOAD, "MCS IB_LOAD"),
    _f("IDB_DRIVE", 1, {0: "no drive", 1: "drive IDB"}, "MCS IDB_DRIVE"),
    _f("IDB_SRC", 3, {0: "AC", 1: "PC", 2: "MB", 3: "MQ", 4: "FP_SR", 5: "EA_ADDR", 6: "IR",
                      7: "ALU"}, "MCS IDB_SRC"),
    _f("IE_LOAD", 1, LOAD, "MCS IE_LOAD"),
    _f("IE_VAL", 1, BOOL_VAL, "MCS IE_VAL"),
    _f("IF_LOAD", 1, LOAD, "MCS IF_LOAD"),
    _f("IF_SRC", 2, {0: "Zero (hardwired 000)", 1: "DIF", 2: "FP_IF", 3: "reserved"}, "MCS IF_SRC"),
    _f("II_LOAD", 1, LOAD, "MCS II_LOAD"),
    _f("II_VAL", 1, BOOL_VAL, "MCS II_VAL"),
    _f("IOT_TRANSFER_LOAD", 1, {0: "no load", 1: "load IOT_TRANSFER"}, "MCS IOT_TRANSFER_LOAD"),
    _f("IOT_TRANSFER_VAL", 2, {0: "NONE", 1: "READ", 2: "WRITE", 3: "invalid"}, "MCS IOT_TRANSFER_VAL"),
    _f("IR_LOAD", 1, LOAD, "MCS IR_LOAD"),
    _f("L_LOAD", 1, LOAD, "MCS L_LOAD"),
    _f("L_OP", 2, {0: "CLEAR", 1: "COMP", 2: "ALU_LINK", 3: "AC[11]"}, "MCS L_OP"),
    _f("MA_LOAD", 1, LOAD, "MCS MA_LOAD"),
    _f("MA_SRC", 2, {0: "PC", 1: "EA_ADDR", 2: "Zero (hardwired 0000)", 3: "reserved"}, "MCS MA_SRC"),
    _f("MB_LOAD", 1, LOAD, "MCS MB_LOAD"),
    _f("MB_SRC", 2, {0: "IDB", 1: "MDB", 2: "FP_SR", 3: "reserved"}, "MCS MB_SRC"),
    _f("MDB_SRC", 2, {0: "Memory", 1: "MB", 2: "FP_SR", 3: "DMA"}, "MCS MDB_SRC"),
    _f("MFB_SRC", 1, {0: "IF", 1: "DF"}, "MCS MFB_SRC"),
    _f("MQ_LOAD", 1, LOAD, "MCS MQ_LOAD"),
    _f("MQ_SRC", 1, {0: "IDB", 1: "AC"}, "MCS MQ_SRC"),
    _f("PC_INC", 1, {0: "no increment", 1: "increment"}, "MCS PC_INC"),
    _f("PC_LOAD", 1, LOAD, "MCS PC_LOAD"),
    _f("PC_SRC", 1, {0: "IDB", 1: "Constant 0001 (hardwired)"}, "MCS PC_SRC"),
]}

# Sequencer-slice fields (CSO §4.1), encodings from SCS §4 and ACS §4.9.
SEQUENCER_FIELDS = {f.name: f for f in [
    _f("MS_NEXT", 3, {0: "FETCH", 1: "DEFER", 2: "EXECUTE", 3: "INTERRUPT", 4: "DMA"}, "SCS §4.1"),
    _f("MS_LOAD", 1, {0: "MS held", 1: "MS loaded from MS_NEXT"}, "SCS §4.4"),
    _f("RUN_NEXT", 1, {0: "processor halted", 1: "processor running"}, "SCS §4.2"),
    _f("HLT_REQ_NEXT", 1, {0: "no halt request pending", 1: "halt request pending"}, "SCS §4.3"),
    _f("/INITIALIZE", 1, ACTIVE_LOW, "ACS §4.9"),
]}

ALL_FIELDS = {**DATAPATH_FIELDS, **SEQUENCER_FIELDS}

# Major-state codes (CSO §5.1).
FETCH, DEFER, EXECUTE, INTERRUPT, DMA, HALTED = 0, 1, 2, 3, 4, 7
MS_NAMES = {FETCH: "FETCH", DEFER: "DEFER", EXECUTE: "EXECUTE", INTERRUPT: "INTERRUPT",
            DMA: "DMA", HALTED: "HALTED"}

# Front-panel command codes (CSO §5.2).
FP_CMD_CODES = {None: 0, "START": 1, "CONTINUE": 2, "CLEAR": 3, "LOAD_ADDRESS": 4,
                "EXAMINE": 5, "DEPOSIT": 6}

# ALU operations (MCS ALU_OP).
ADD, AND, OR, NOT, INC, ROR, ROL, RTR, RTL, BSW, CLEAR = range(11)

# IOT_TRANSFER encoding (Registers, IOT_TRANSFER).
IOT_NONE, IOT_READ, IOT_WRITE = 0, 1, 2

# Mapping-register fields (CSO §5.4.1): (offset, width).
MAPR_FIELDS = {"VARIANT": (0, 5), "DP_OVL_SEL": (5, 2), "IR_SEQ": (7, 1)}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def check_against_schema(schema_path: Path) -> list[str]:
    """Return every disagreement between these definitions and the control-word schema."""
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
    by_name = {f["name"]: f for f in schema["fields"] if f["control_word_role"] == "encoded"}
    problems = []
    for name, fd in ALL_FIELDS.items():
        sf = by_name.get(name)
        if sf is None:
            problems.append(f"{name}: not an encoded field in the schema")
            continue
        if sf["width"] != fd.width:
            problems.append(f"{name}: width {fd.width} here, {sf['width']} in the schema")
        if not sf["values"]:  # /INITIALIZE lists no encodings in the schema
            continue
        theirs = {int(v["encoding"], 8): _norm(v["meaning"]) for v in sf["values"]}
        ours = {c: _norm(m) for c, m in fd.values.items()}
        if theirs != ours:
            problems.append(f"{name}: encodings differ: here {ours}, schema {theirs}")
    for name in by_name.keys() - ALL_FIELDS.keys():
        problems.append(f"{name}: encoded in the schema but not defined here")
    return problems
