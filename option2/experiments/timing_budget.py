#!/usr/bin/env python3
"""Worst-case timing budget for every timing state of v2, under the two-rank TP model.

The path list is derived, not chosen:

- every micro-operation of every execution case, in its TS
- every encoded control field, at its consumer, in every TS
- every overlay and sequencer address input of the packed control store
- what changes at the start of each TS: exactly what the previous TP can commit

An unknown micro-operation, control field, or address input is an error, so a new one cannot be
left out of the budget silently.

Run from the repository root, after a v2 pipeline run:

    python -I -X utf8 option2/experiments/timing_budget.py [--weak-pullup] [--strobes-from-store] [--all]

`--weak-pullup` and `--strobes-from-store` each remove one of the corrections the budget shows to be
needed (a strong /INT_REQ pull-up; /INITIALIZE decoded and /RD and the MDB drive qualified outside
the control store). Times are ns from the TS boundary (the TCLK edge that ends the previous TP).
All figures are datasheet maxima over temperature at CL = 50 pF, and minima where a race needs one.
"""

from __future__ import annotations

import glob
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass

ROM = "rom/microcode/v2/"
BUILD = "build/simulation_outputs/rom-generation-v2/"
STEP = 50.0

# ---------------------------------------------------------------------------
# Parts (max unless named MIN). TI unless noted; see option2/timing.md section 2.
# ---------------------------------------------------------------------------

CQ, CQ_MIN = 12.0, 2.0              # 74ACT574
SETUP, CE_SETUP = 2.5, 4.5          # 574 data; 74F377A clock enable
Q_MAX, NQ_MAX = 13.0, 13.0          # 74ACT74 clock to Q, /Q rising
Q_RISE_MIN, Q_FALL_MIN = 4.0, 3.5
Q_FALL_MAX = 11.5
BUF, BUF_MIN = 10.0, 1.5            # 74ACT244, also the backplane driver
SCHMITT, SCHMITT_MIN = 12.5, 1.5    # 74ACT14, remote clock receiver
RCV, EN, WIRE = 9.0, 12.5, 5.0      # receiver, 3-state enable, one crossing
GATE, XOR = 10.0, 10.5              # 74ACT08/32, 86
FAST_GATE = 6.6                     # 74F11, F32
D157, S157 = 8.6, 13.2
D153, S153 = 16.4, 20.0
D151, S151 = 15.4, 19.6
DEC = 10.9                          # 74ACT138
EQ = 11.0                           # 74F521
ADD12 = 27.5                        # three 74F283
ZERO = 30.0                         # 12-bit NOR tree
PRIORITY = 45.0                     # two-level priority encoder (allowance)
ENCODE = 20.0                       # FP_CMD encoder (allowance)
COUNT = 15.2                        # 74ACT163 clock to Q
F74_SETUP = 3.0
SHADOW, SRAM, CW_BUF = 9.0, 15.0, 9.0   # address buffer, AS7C256C-15, fan-out buffer
LVC, LVC_EN = 6.3, 8.5              # 74LVC245A at 3.3 V
LVC32_MIN, LVC32_MAX = 1.0, 3.8
OC_RISE = 13.0                      # 74F38, open collector, rising
BUS_C = 200e-12                     # allowance for a loaded backplane line
PULL_STRONG, PULL_WEAK = 220.0, 4700.0
MRAM = dict(taa=35.0, toe=15.0, pulse=15.0, hold=12.0, aw=18.0, dw=10.0)     # Everspin MR256A08B

BP = BUF + WIRE + RCV               # one driven backplane crossing
CW = SHADOW + SRAM + CW_BUF + WIRE  # address stable to control word at its receivers

L = NQ_MAX + BUF + CQ               # CPU output rank (r2) valid, buffered clock
RL = Q_FALL_MAX + BUF + WIRE + SCHMITT + CQ     # a controller's output rank valid
TS_CODE = CQ
TS_DEC = TS_CODE + DEC
TS_REMOTE = TS_DEC + BP
CLK_MIN = Q_RISE_MIN + BUF_MIN      # earliest capture clock after the edge that starts TP

# ---------------------------------------------------------------------------
# Timing model
# ---------------------------------------------------------------------------

FAST, SLOW = (5, 8, 6, 5), (6, 8, 7, 7)
CONTEXTS = {                        # name: (MS, TS lengths, TSs with a two-step TP)
    "FETCH": ("FETCH", FAST, ()),
    "DEFER": ("DEFER", FAST, ()),
    "DEFER auto": ("DEFER", SLOW, (4,)),
    "EXECUTE": ("EXECUTE", SLOW, (3, 4)),
    "INTERRUPT": ("INTERRUPT", SLOW, (3,)),
    "DMA": ("DMA", SLOW, (2,)),
    "CONSOLE": ("CONSOLE", (9,), (1,)),
}
SEQUENCER_MAP = ("A14..A12 = MS_EFF, A11..A10 = TS_CODE (TS-1), A9 = HLT_REQ, A8 = FP_STOP, "
                 "A7..A5 = SEQ_OVL, A4 = /DMA_REQ, A3 = IR_SEQ, A2 = IR_NO_EXECUTE, A1 = IR_OPR_HLT, A0 = 0")
REGISTERS = ("AC L MQ PC MA MB IR EA_ADDR IF DF DIF IB IE II CIFP SKIP IOT_TRANSFER HLT_REQ MS RUN "
             "MAPR").split()


@dataclass
class Row:
    context: str
    ts: int
    path: str
    due: float
    need: float

    @property
    def margin(self) -> float:
        return self.due - self.need


class State:
    """Arrival times in one TS of one execution case."""

    def __init__(self, ms, ts, changed, group, external_iot, pullup):
        self.ms, self.ts, self.changed, self.group = ms, ts, changed, group
        self.external_iot, self.pullup = external_iot, pullup
        self.halted = ms == "CONSOLE"

    def r(self, *names):
        for n in names:
            assert n in REGISTERS, n
        return L if set(names) & self.changed else 0.0

    # external lines

    def response(self):
        if not self.external_iot:
            return 0.0
        match = self.r("MS", "RUN") + GATE + BP + GATE + EN + WIRE + RCV
        data = max(TS_REMOTE, RL) + 3 * GATE + BP
        return max(match, data) if self.ts == 1 else data

    def int_req(self):
        rise = self.pullup * BUS_C * 1e9 * 0.43                    # RC rise from 0.4 V to 2.0 V
        return RL + 2 * GATE + OC_RISE + rise + WIRE + RCV

    def dma_req(self):
        ie = max(TS_DEC, self.r("MS", "RUN") + D157 + 2 * GATE, self.r("IR") + DEC + 3 * GATE) + GATE + BP
        request = RL + GATE + BP + 2 * GATE
        return max(ie + GATE, request, RL + 2 * GATE) + GATE + BP

    # address formation

    def ms_eff(self):
        if "RUN" in self.changed:
            return L + S157
        return (L + D157) if "MS" in self.changed else 0.0

    def exec_bit(self):
        return self.r("MS", "RUN")                          # decision 11a: registered

    def fp_cmd(self):
        return CQ + ENCODE if self.halted else 0.0

    def after(self, t, d):
        return t + d if t else 0.0

    def overlay_input(self, s):
        a = self.after
        if s.startswith("IO_"):
            return self.response()
        table = {
            "IOT_READ_PENDING": lambda: a(self.r("IOT_TRANSFER"), GATE),
            "IOT_WRITE_PENDING": lambda: a(self.r("IOT_TRANSFER"), GATE),
            # qualified by the SRQ decode: no other variant of its group depends on it
            "/INT_REQ": lambda: 0.0 if self.external_iot else self.int_req() + GATE,
            "SKIP": lambda: max(a(self.r("SKIP"), D157), a(self.r("RUN"), S157)),
            "FP_CMD": lambda: max(a(self.fp_cmd(), D157), a(self.r("RUN"), S157)),
            "AUTO_INDEX_REQUIRED": lambda: max(a(self.r("EA_ADDR"), EQ + GATE), a(self.r("IR"), 2 * GATE)),
            "CIFP": lambda: self.r("CIFP"),
            "IE": lambda: self.r("IE"),
            "IF_CHANGE_PENDING": lambda: self.r("CIFP"),
            "ISZ_SKIP_REQ": lambda: max(a(self.r("MB"), ZERO + GATE), a(self.r("IR"), 2 * GATE)),
        }
        if s not in table:
            sys.exit(f"address input not modeled: {s}")
        return table[s]()

    def datapath_address(self):
        a = self.after
        executing = self.ms == "EXECUTE"
        variant = [a(self.exec_bit(), S157), a(self.r("MAPR"), D157) if executing
                   else a(self.r("IR"), DEC + 2 * GATE + D157)]
        select = max(a(self.exec_bit(), S157), a(self.r("MAPR"), D157) if executing else 0.0)
        overlay = [a(select, S153)] + [a(self.overlay_input(s), D153) for s in self.group]
        return max([TS_CODE, self.ms_eff()] + variant + overlay)

    def sequencer_address(self):
        a = self.after
        inputs = [TS_CODE, self.ms_eff(), self.r("HLT_REQ"), L]         # L: captured STOP and modes
        irv = max(self.r("IE"), a(self.r("II"), GATE), self.int_req() + GATE) + GATE
        running = a(self.fp_cmd(), D157) if self.halted else max(irv, L) + D157
        inputs += [running, a(self.r("RUN"), S157), self.dma_req() if not self.halted else 0.0]
        inputs += [a(self.r("IR"), DEC + 2 * GATE), a(self.exec_bit(), S157)]
        inputs += [a(self.r("MAPR"), D157) if self.ms == "EXECUTE" else a(self.r("IR"), GATE + D157)]
        return max(inputs)


def operation(u, s, cw):
    """Arrival at the register input (or device pins) for one micro-operation."""
    r, a = s.r, s.after

    def idb(source):
        return max(cw + DEC + EN + WIRE, source + RCV + WIRE)

    def m153(*data):
        return max([cw + S153] + [d + D153 for d in data])

    def m157(*data):
        return max([cw + S157] + [d + D157 for d in data])

    def m151(*data):
        return max([cw + S151] + [d + D151 for d in data])

    def alu(op, *operands):
        a_in = m153(*[r(x) for x in operands[:1]])
        b_in = m157(*[r(x) for x in operands[1:]])
        if op in ("ADD", "INC"):
            out = max(a_in, b_in, cw + GATE) + ADD12
        elif op == "AND":
            out = max(a_in, b_in) + GATE
        else:
            out = 0.0
        return max(cw + S153, out + D153), out

    def merge(field):
        return m151(max(r("AC"), field) + GATE)

    ea = max(a(r("IR"), S157), a(r("MA"), D157))
    ir_ctl = a(r("IR"), DEC + 2 * GATE)
    opr = max(ir_ctl, r("AC", "L", "MQ"), L) + GATE + GATE + XOR + ADD12 + XOR + D153

    if u in ("AC_AND_MB", "ADD_AC_MB", "AC_CLEAR"):
        op = {"AC_AND_MB": "AND", "ADD_AC_MB": "ADD", "AC_CLEAR": "CLEAR"}[u]
        result, adder = alu(op, "AC", "MB")
        t = m151(idb(result))
        return max(t, m153(adder + XOR)) if op == "ADD" else t
    if u == "MQ_CLEAR":
        return m157(idb(alu("CLEAR")[0]))
    if u == "MB_INC":
        return m153(idb(alu("INC", "MB")[0]))
    if u == "PC_INC":
        return m157(alu("INC", "PC")[0])

    table = {
        "AC_TO_DF": lambda: m151(r("AC")), "AC_TO_DIF": lambda: m151(r("AC")),
        "AC_TO_L": lambda: m153(r("AC")), "L_CLEAR": lambda: m153(),
        "AC_TO_MB": lambda: m153(idb(r("AC"))), "PC_TO_MB": lambda: m153(idb(r("PC"))),
        "PC_TO_MA": lambda: m153(r("PC")), "EA_ADDR_TO_MA": lambda: m153(r("EA_ADDR")),
        "MA_CLEAR": lambda: m153(),
        "CIFP_CLEAR": lambda: cw, "CIFP_SET": lambda: cw, "IE_CLEAR": lambda: cw, "IE_SET": lambda: cw,
        "II_CLEAR": lambda: cw, "II_SET": lambda: cw,
        "IOT_TRANSFER_CAPTURE": lambda: cw, "IOT_TRANSFER_CLEAR": lambda: cw,
        "DF_CLEAR": lambda: m151(), "DIF_CLEAR": lambda: m151(), "IF_CLEAR": lambda: m153(),
        "DIF_TO_IF": lambda: m153(r("DIF")),
        "FP_DF_TO_DF": lambda: m151(L), "FP_IF_TO_DIF": lambda: m151(L), "FP_IF_TO_IF": lambda: m153(L),
        "FP_SR_TO_MB": lambda: m153(L),
        "FP_SR_TO_PC": lambda: m153(idb(L)) + D157,
        "IB_TO_DF": lambda: m151(r("IB")), "IB_TO_DIF": lambda: m151(r("IB")),
        "IR_DF_TO_DF": lambda: m151(r("IR")), "IR_IF_TO_DIF": lambda: m151(r("IR")),
        "IF_DF_TO_IB": lambda: r("IF", "DF"),
        "DF_TO_AC": lambda: merge(r("DF")), "IF_TO_AC": lambda: merge(r("IF")),
        "IB_TO_AC": lambda: merge(r("IB")),
        "GTF_FLAGS_TO_AC": lambda: merge(max(r("L", "IE", "II", "IB"), s.int_req() + GATE)),
        "IR_ADDR_TO_EA_ADDR": lambda: m157(ea), "IR_ADDR_TO_PC": lambda: m153(ea) + D157,
        "MB_TO_EA_ADDR": lambda: m157(idb(r("MB"))), "PC_TO_EA_ADDR": lambda: m157(idb(r("PC"))),
        "MB_TO_PC": lambda: m153(idb(r("MB"))) + D157,
        "PC_LOAD_EA_ADDR": lambda: m153(idb(r("EA_ADDR"))) + D157,
        "PC_SET_1": lambda: m153() + D157,
        "OPR_PASS": lambda: max(m151(opr), m153(opr)),
        "OPR_PASS_TO_MQ": lambda: m157(max(ir_ctl + GATE, r("AC", "MQ")) + 2 * GATE),
        # SKIP's input, OPR_SKIP_REQ; SKIP loads it at every main-sequence TP (Registers, SKIP).
        "SKIP_DATA": lambda: max(a(r("AC", "L"), ZERO), ir_ctl) + 3 * GATE + XOR,
        "DB_READ_TO_AC": lambda: db_read(s, cw),
    }
    if u in table:
        return table[u]()
    if u in ("MEM_READ_TO_MB", "MDB_TO_IR"):
        t = memory_read(s, cw)
        return m153(t) if u == "MEM_READ_TO_MB" else t
    if u in ("MEM_WRITE_FROM_MB", "MEM_WRITE_FROM_FP_SR", "DB_WRITE_FROM_AC"):
        return None                                         # checked at the receiving device
    sys.exit(f"micro-operation not modeled: {u}")


def db_open():
    return 2 * STEP + CQ + GATE                             # two TSTEPs into the TS, from IOT_TRANSFER


def db_read(s, cw):
    strobe = db_open() + BP + GATE + EN + WIRE + RCV
    data = RL + D151 + BP                                   # the controller's own register
    return max(cw + S151, max(strobe, data, s.r("AC")) + GATE + D151)


def memory_address(s, cw):
    ab = max(cw + S157, s.r("MA", "PC") + D157)
    mfb = max(cw + S157, s.r("IF", "DF") + D157)
    return max(ab, mfb) + BUF + WIRE + RCV


def memory_read(s, cw, taa=None):
    address = memory_address(s, cw) + (MRAM["taa"] if taa is None else taa)
    strobe = 3 * STEP + CQ + GATE + BP
    chip = max(address, strobe + MRAM["toe"]) + LVC
    return max(chip, strobe + LVC_EN) + WIRE + RCV


# ---------------------------------------------------------------------------
# Inputs from the generated artifacts
# ---------------------------------------------------------------------------

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def inputs():
    cases = load(ROM + "execution-definitions.json")["cases"]
    symbolic = {c["execution_case_id"]: c for c in load(ROM + "symbolic-control-words.json")["cases"]}
    packing = load(glob.glob(BUILD + "control-store-packer/control-store-packing.json")[0])
    schema = load(ROM + "control-word-schema.json")
    groups = {}
    for g in packing["overlay_groups"]:
        bits = g["bits"] + g.get("running_bits", [])
        groups[g["code"]] = sorted({b["signal"] for b in bits})
    targets = {}
    for u in load(glob.glob(BUILD + "micro-operation-extractor/*.json")[0])["micro_operations"]:
        names = {re.split(r"[\[\s]", x)[0] for x in u["targets"]}
        if names - set(REGISTERS) - {"DB", "M"}:
            sys.exit(f"target not modeled: {u['name']} {sorted(names)}")
        targets[u["name"]] = names & set(REGISTERS)
    encoded = [f["name"] for f in schema["fields"] if f["control_word_role"] == "encoded"]
    seq = [x["field"] for x in packing["sequencer_layout"]]
    if packing["address_maps"]["sequencer_slice"] != SEQUENCER_MAP:
        sys.exit("the sequencer address map changed: update State.sequencer_address")
    return cases, symbolic, groups, targets, encoded, seq


def case_group(case, symbolic, groups, ts):
    cid = case["id"]
    if cid.startswith("iot:external"):
        return groups[2 if ts == 4 else 0]
    text = json.dumps(symbolic.get(cid, {}).get("field_assignments", {}))
    used = {s for g in (2, 3) for s in groups[g] if re.search(r"(?<![A-Za-z_/])" + re.escape(s) + r" !?=", text)}
    for g in (3, 2):
        if used and used <= set(groups[g]):
            return groups[g]
    return []                                               # group 0: responses, idle outside an external IOT


def case_ops(case):
    return list(case["micro_operations"]) + [c["micro_operation"] for c in case["conditional_micro_operations"]]


# ---------------------------------------------------------------------------
# The budget
# ---------------------------------------------------------------------------

def budget(pullup, decoded):
    cases, symbolic, groups, targets, encoded, seq_fields = inputs()
    by = defaultdict(list)
    for c in cases:
        ms = next((t.split("= ")[1] for t in c["context"] if t.startswith("MS =")), "CONSOLE")
        by[ms, c["timing_state"] or 1].append(c)

    rows, taa = [], []
    for name, (ms, lengths, wide) in CONTEXTS.items():
        for ts, n in enumerate(lengths, 1):
            setup_steps = n - (2 if ts in wide else 1)
            rise = setup_steps * STEP
            due = rise + CLK_MIN
            if ts == 1:
                changed = set(REGISTERS) - {"IR"}           # anything a TP4 or TPC can commit
            else:
                changed = {"MAPR", "HLT_REQ", "SKIP"}       # MAPR and SKIP load at every TP
                for c in by[ms, ts - 1]:
                    for u in case_ops(c):
                        changed |= targets[u]
                if ms == "EXECUTE":
                    changed.add("IOT_TRANSFER")
            for case in by[ms, ts]:
                ops = case_ops(case)
                if name == "DEFER":                         # no auto-index in the fast DEFER
                    ops = [u for u in ops if u not in ("MB_INC", "MEM_WRITE_FROM_MB")]
                ext = case["id"].startswith("iot:external")
                group = groups[1] if ms != "EXECUTE" else case_group(case, symbolic, groups, ts)
                s = State(ms, ts, changed, group, ext, pullup)
                cw = s.datapath_address() + CW
                cws = s.sequencer_address() + CW

                def add(path, need, limit=due):
                    rows.append(Row(name, ts, path, limit, need))

                for u in ops:
                    t = operation(u, s, cw)
                    if t is not None:
                        add(u, t + SETUP)

                for f in encoded:
                    if f in seq_fields:
                        if f == "/INITIALIZE":
                            if decoded:                     # decoded outside the control store
                                d = max(TS_DEC, s.r("MS", "RUN"), s.fp_cmd()) + 2 * GATE
                            else:
                                d = cws
                            add("/INITIALIZE settled at CW_VALID", d, 3 * STEP + CQ_MIN)
                            if (ms, ts) in (("EXECUTE", 4), ("CONSOLE", 1)):
                                add("/INITIALIZE at a controller", max(d, 3 * STEP + CQ) + GATE + BP + GATE + SETUP)
                        else:
                            add(f"sequencer {f}", cws + CE_SETUP)
                    elif f.endswith("_LOAD") or f == "PC_INC":
                        extra = GATE if f in ("PC_LOAD", "PC_INC") else 0.0
                        add(f"enable {f}", cw + extra + CE_SETUP)
                    elif f in ("/RD", "MDB_SRC"):
                        d = cw + (DEC if f == "MDB_SRC" else 0.0)
                        io_dependent = ms == "EXECUTE" and case["id"].startswith("iot:")
                        if decoded and io_dependent:            # qualified off during every IOT
                            d = s.r("MS", "RUN") + GATE
                        add(f"{f} settled at CW_VALID", d, 3 * STEP + CQ_MIN)
                    elif f in ("/DB_READ", "/DB_WRITE"):
                        add(f"{f} settled at its window", s.r("IOT_TRANSFER") + GATE, 2 * STEP + CQ_MIN)
                    elif not (f.endswith(("_SRC", "_VAL", "_OP")) or f in ("IDB_DRIVE", "/WR")):
                        sys.exit(f"control field not modeled: {f}")

                if ts in wide and ms != "DMA":
                    add("/WR settled at the pulse", cw + BP, rise + Q_FALL_MIN)
                if any(u.startswith("MEM_WRITE") for u in ops):
                    start = rise + Q_FALL_MIN
                    add("write: address and field", memory_address(s, cw) + 0.0, start)
                    data = max(3 * STEP + CQ + GATE, cw + DEC) + EN + WIRE + RCV + LVC
                    data = max(data, (L if "FP_SR" in " ".join(ops) else s.r("MB")) + BUF + WIRE + RCV + LVC)
                    add("write: data", data, start)
                if "DB_WRITE_FROM_AC" in ops:
                    data = max(db_open() + EN, s.r("AC") + BUF) + WIRE + RCV
                    add("DB write at a controller", data + 2 * GATE + SETUP)
                    add("DB write: controller load enable", max(TS_REMOTE, RL) + 2 * GATE + CE_SETUP)
                if "MEM_READ_TO_MB" in ops:
                    fixed = memory_address(s, cw) + LVC + WIRE + RCV
                    taa.append((due - SETUP - D153 - fixed, name, ts))

                if ts == len(lengths) or ms == "CONSOLE":
                    add("MS, RUN data", cws + SETUP)
                if ms != "CONSOLE":
                    add("MAPR", max(TS_CODE, s.r("IR")) + SHADOW + SRAM + SETUP)
                    add("SKIP data", operation("SKIP_DATA", s, cw) + SETUP)
                    rom = max(TS_CODE, s.ms_eff(), s.after(s.r("EA_ADDR"), EQ + GATE)) + SHADOW + SRAM
                    add("timing ROM at first compare", rom + EQ + 2 * FAST_GATE + F74_SETUP, 4 * STEP)

                if ms == "DMA":
                    if ts == 1:
                        add("arbiter selection", RL + GATE + BP + PRIORITY + SETUP)
                    if ts == 2:
                        drive = max(TS_REMOTE, RL + BP + EQ) + GATE + EN + WIRE + RCV
                        start = rise + Q_FALL_MIN
                        add("DMA write: address, data, /WR", drive + LVC, start)
                        chip = max(drive + MRAM["taa"], drive + MRAM["toe"]) + LVC
                        read = max(chip, drive + LVC_EN) + WIRE + RCV
                        add("DMA read at the controller", read + SETUP)
                    if ts == 3:
                        add("arbiter burst end", RL + GATE + BP + 2 * D151 + 2 * GATE + SETUP)
    return rows, taa


def edge_checks():
    """Checks between clock edges: they do not depend on the TS."""
    rows = []

    def add(path, have, need=0.0):
        rows.append(Row("edges", 0, path, have, need))

    r1_max = Q_MAX + BUF + CQ
    r2_min = STEP + Q_RISE_MIN + BUF_MIN
    add("r1 to r2 setup", r2_min, r1_max + SETUP)
    add("r1 to r2, through the 11a decode", r2_min, r1_max + FAST_GATE + SETUP)
    remote_r1 = Q_MAX + BUF + SCHMITT + CQ                  # the wire delay is common to both edges
    remote_r2 = STEP + Q_FALL_MIN + BUF_MIN + SCHMITT_MIN
    add("controller r1 to r2 setup", remote_r2, remote_r1 + SETUP)
    change = STEP + CQ_MIN
    add("CPU capture hold", change, Q_MAX + BUF + 5.0)
    add("controller capture hold", change + 2 * BUF_MIN, Q_MAX + BUF + WIRE + SCHMITT + 5.0)
    add("TP flip-flop, one TSTEP", STEP, COUNT + EQ + 2 * FAST_GATE + F74_SETUP)
    turn_off = CQ + GATE + EN + WIRE
    add("DB turnaround: CPU off before controller on", db_open(), turn_off)
    remote_off = CQ + GATE + BP + GATE + EN + WIRE
    add("DB turnaround: controller off before CPU on", 2 * STEP + CQ_MIN + 2.0, remote_off)

    narrow = (Q_FALL_MAX - Q_RISE_MIN) + 2 * (BUF - BUF_MIN) + (LVC32_MAX - LVC32_MIN)
    add("write pulse at an MRAM", STEP - narrow, MRAM["pulse"])
    end = STEP + Q_MAX + 2 * BUF + LVC32_MAX
    moved = 2 * STEP + CQ_MIN + 4 * BUF_MIN + 2.4           # address path at every minimum
    add("write: address hold at an MRAM", moved - end, MRAM["hold"])
    released = 2 * STEP + CQ_MIN + 3 * BUF_MIN
    add("write: data hold", released - end)
    return rows


def main():
    weak, stored = "--weak-pullup" in sys.argv, "--strobes-from-store" in sys.argv
    rows, taa = budget(PULL_WEAK if weak else PULL_STRONG, not stored)
    rows += edge_checks()
    worst = {}
    for r in rows:
        key = (r.context, r.ts, r.path)
        if key not in worst or r.margin < worst[key].margin:
            worst[key] = r
    ordered = sorted(worst.values(), key=lambda r: r.margin)

    print("model: approved changes;", "weak" if weak else "strong", "pull-up;",
          "strobes from the control store" if stored else "strobes decoded")
    print(f"{len(rows)} checks, {len(worst)} distinct paths, {sum(r.margin < 0 for r in ordered)} failing\n")
    print("| Context | TS | Setup limit | Worst path | Arrives | Margin |")
    print("|---|---:|---:|---|---:|---:|")
    done = set()
    table = []
    for r in ordered:
        if r.context != "edges" and (r.context, r.ts) not in done:
            done.add((r.context, r.ts))
            table.append(r)
    order = list(CONTEXTS)
    for r in sorted(table, key=lambda r: (order.index(r.context), r.ts)):
        print(f"| {r.context} | {r.ts} | {r.due:.1f} | {r.path} | {r.need:.1f} | {r.margin:.1f} |")
    print("\n| Between edges | Available | Required | Margin |")
    print("|---|---:|---:|---:|")
    for r in ordered:
        if r.context == "edges":
            print(f"| {r.path} | {r.due:.1f} | {r.need:.1f} | {r.margin:.1f} |")
    count = len(ordered) if "--all" in sys.argv else 22
    print("\n| Tightest | TS | Path | Margin |")
    print("|---|---:|---|---:|")
    for r in ordered[:count]:
        print(f"| {r.context} | {r.ts} | {r.path} | {r.margin:.1f} |")
    limit = min(taa)
    print(f"\nMain-memory access time limit: {limit[0]:.1f} ns ({limit[1]} TS{limit[2]}).")


if __name__ == "__main__":
    main()
