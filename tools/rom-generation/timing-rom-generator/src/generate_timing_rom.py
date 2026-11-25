#!/usr/bin/env python3
"""Generate the timing ROM image from the documented TS lengths.

The timing ROM (Timing Terminology §3.5) gives each timing state's setup length and TP width,
addressed by MS_EFF, the TS code, AUTO_INDEX_REQUIRED, and TIMING_MODE. The values are read from
the two tables of Timing Architecture §5.1: the TS lengths per context and speed mode, and the
timing states whose TP is two steps wide. The major-state codes are read from Control Store
Organization §5.1.

Layout (Timing Terminology §3.5):

    address  A7..A5 = MS_EFF, A4..A3 = TS code (TS - 1), A2 = AUTO_INDEX_REQUIRED,
             A1..A0 = TIMING_MODE, A14..A8 = 0
    data     D2..D0 = setup length (TS length - TP width), D3 = TP width - 1, D7..D4 = 0

Addresses no running state reads hold safe values: the reserved TIMING_MODE codes repeat
mode 1, and the MS_EFF codes that are not major states (including HALTED) hold the slow TS
lengths with one-step TPs.

Outputs, under the design's build directory: images/timing.hex (32768 lines, two hex digits,
address 0 first), timing-rom.json, and generation-report.txt.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))
from design import DESIGN  # noqa: E402  (control-design selection: common/design.py)

TIMING_ARCHITECTURE = Path("docs/09-timing/02-timing-architecture.md")
CONTROL_STORE_ORGANIZATION = Path("docs/04-control/08-control-store-organization.md")
OUTPUT_DIRECTORY = Path(f"{DESIGN.build}/timing-rom-generator")
DEFAULT_IMAGE = OUTPUT_DIRECTORY / "images" / "timing.hex"
DEFAULT_JSON = OUTPUT_DIRECTORY / "timing-rom.json"
DEFAULT_REPORT = OUTPUT_DIRECTORY / "generation-report.txt"

IMAGE_DEPTH = 1 << 15
TIMING_STATES = (1, 2, 3, 4)
MODES = (0, 1)                       # documented modes
RESERVED_MODES = {2: 1, 3: 1}        # reserved mode -> the documented mode it repeats (§3.5)
SAFE_MODE = 1                        # the uniform slow timing (§3.5)
MAJOR_STATES = ("FETCH", "DEFER", "EXECUTE", "INTERRUPT", "DMA")
MAX_SETUP = 7                        # D2..D0
STRUCTURE_HEADING = re.compile(r"^###\s+5\.1\s+Structure\s*$")

ERROR, WARNING, INFO = "ERROR", "WARNING", "INFO"


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    code: str
    message: str
    entry: str | None = None


def address(ms_eff: int, ts: int, auto_index: int, mode: int) -> int:
    return (ms_eff << 5) | ((ts - 1) << 3) | (auto_index << 2) | mode


def encode(ts_length: int, tp_width: int) -> int:
    return ((tp_width - 1) << 3) | (ts_length - tp_width)


def decode(byte: int) -> tuple[int, int]:
    """(TS length, TP width) of a ROM byte."""
    width = ((byte >> 3) & 1) + 1
    return (byte & 7) + width, width


# ---------------------------------------------------------------------------
# Reading the documentation
# ---------------------------------------------------------------------------


def section(text: str) -> list[str]:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if STRUCTURE_HEADING.match(line):
            end = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("### ")
                        or lines[j].startswith("## ")), len(lines))
            return lines[i + 1:end]
    return []


def tables(lines: Sequence[str]) -> list[list[list[str]]]:
    """Each Markdown table in `lines` as rows of cells, header first, separator dropped."""
    found, current = [], []
    for line in list(lines) + [""]:
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                current.append(cells)
        elif current:
            found.append(current)
            current = []
    return found


def contexts(cell: str, diagnostics: list[Diagnostic]) -> list[tuple[str, int | None]]:
    """(major state, AUTO_INDEX_REQUIRED or None for either) for each context named in a cell."""
    out = []
    for part in cell.replace("`", "").split(";"):
        part = part.strip()
        if not part:
            continue
        name = part.split(",")[0].split()[0]
        if name not in MAJOR_STATES:
            if name.lower() != "console":
                diagnostics.append(Diagnostic(ERROR, "UNKNOWN_CONTEXT",
                                              f"Timing context {part!r} is not a major state.", part))
            continue
        match = re.search(r"AUTO_INDEX_REQUIRED\s*=\s*([01])", part)
        out.append((name, int(match.group(1)) if match else None))
    return out


def read_lengths(lines, diagnostics):
    """{(state, auto_index or None): {mode: (TS1..TS4 lengths)}} from the TS-length table."""
    lengths: dict[tuple[str, int | None], dict[int, tuple[int, ...]]] = {}
    for table in tables(lines):
        header = table[0]
        modes = [int(m.group(1)) if (m := re.match(r"Mode\s+(\d)", h)) else None for h in header]
        if not any(m is not None for m in modes):
            continue
        for row in table[1:]:
            for ctx in contexts(row[0], diagnostics):
                for col, mode in enumerate(modes):
                    if mode is None or col >= len(row):
                        continue
                    cell = row[col].replace("*", "")
                    m = re.match(r"\s*(\d+)/(\d+)/(\d+)/(\d+)\s*=\s*(\d+)", cell)
                    if not m:
                        diagnostics.append(Diagnostic(ERROR, "UNREADABLE_LENGTHS",
                                                      f"Cannot read TS lengths from {cell!r}.", row[0]))
                        continue
                    values = tuple(int(x) for x in m.groups()[:4])
                    if sum(values) != int(m.group(5)):
                        diagnostics.append(Diagnostic(
                            ERROR, "TOTAL_MISMATCH",
                            f"Mode {mode}: {'/'.join(map(str, values))} totals {sum(values)}, "
                            f"not the stated {m.group(5)}.", row[0]))
                    lengths.setdefault(ctx, {})[mode] = values
    return lengths


def read_wide(lines, diagnostics):
    """{(state, auto_index or None): set of TSs with a two-step TP} from the TP-width table."""
    wide: dict[tuple[str, int | None], set[int]] = {}
    for table in tables(lines):
        if not any("two-step" in h for h in table[0]):
            continue
        for row in table[1:]:
            for ctx in contexts(row[0], diagnostics):
                wide[ctx] = {int(t) for t in re.findall(r"TS([1-4])", row[1])}
    return wide


def read_ms_codes(text: str, diagnostics) -> dict[str, int]:
    codes = {name: int(code) for name, code in re.findall(r"`([A-Z]+) = (\d)`", text)}
    missing = [s for s in MAJOR_STATES if s not in codes]
    if missing:
        diagnostics.append(Diagnostic(ERROR, "MISSING_MS_CODE",
                                      f"No major-state code for {', '.join(missing)}."))
    return codes


# ---------------------------------------------------------------------------
# The image
# ---------------------------------------------------------------------------


def lookup(table, state, auto_index):
    """The entry for a context: the one naming AUTO_INDEX_REQUIRED's value, else the general one."""
    return table.get((state, auto_index), table.get((state, None)))


def build(arch_text: str, cso_text: str):
    diagnostics: list[Diagnostic] = []
    lines = section(arch_text)
    if not lines:
        diagnostics.append(Diagnostic(ERROR, "MISSING_SECTION",
                                      "Timing Architecture §5.1 Structure not found."))
        return None, None, diagnostics
    lengths = read_lengths(lines, diagnostics)
    wide = read_wide(lines, diagnostics)
    codes = read_ms_codes(cso_text, diagnostics)
    entries = []
    image = [0] * IMAGE_DEPTH
    slow = lookup(lengths, "EXECUTE", 0)
    safe = slow.get(SAFE_MODE) if slow else None
    if safe is None:
        diagnostics.append(Diagnostic(ERROR, "MISSING_LENGTHS",
                                      f"No mode {SAFE_MODE} lengths for EXECUTE, the safe values."))
    for state in MAJOR_STATES:
        for auto_index in (0, 1):
            per_mode = lookup(lengths, state, auto_index)
            if per_mode is None:
                diagnostics.append(Diagnostic(ERROR, "MISSING_LENGTHS",
                                              f"No TS lengths for {state} (AUTO_INDEX_REQUIRED = "
                                              f"{auto_index}).", state))
                continue
            twostep = lookup(wide, state, auto_index) or set()
            for mode in MODES:
                if mode not in per_mode:
                    diagnostics.append(Diagnostic(ERROR, "MISSING_LENGTHS",
                                                  f"No mode {mode} lengths for {state}.", state))
                    continue
                for ts in TIMING_STATES:
                    length, width = per_mode[mode][ts - 1], 2 if ts in twostep else 1
                    if not 1 <= length - width <= MAX_SETUP:
                        diagnostics.append(Diagnostic(
                            ERROR, "SETUP_OUT_OF_RANGE",
                            f"{state} TS{ts} mode {mode}: setup length {length - width} does not "
                            f"fit D2..D0.", state))
                        continue
                    byte = encode(length, width)
                    for m in [mode] + [r for r, d in RESERVED_MODES.items() if d == mode]:
                        image[address(codes.get(state, 0), ts, auto_index, m)] = byte
                    entries.append({"major_state": state, "auto_index_required": auto_index,
                                    "timing_mode": mode, "ts": ts, "ts_length": length,
                                    "tp_width": width, "setup_length": length - width,
                                    "byte": f"{byte:02X}"})
    used = {codes[s] for s in MAJOR_STATES if s in codes}
    if safe is not None:
        for ms_eff in range(8):
            if ms_eff in used:
                continue
            for ts in TIMING_STATES:
                for auto_index in (0, 1):
                    for mode in range(4):
                        image[address(ms_eff, ts, auto_index, mode)] = encode(safe[ts - 1], 1)
    if any(d.severity == ERROR for d in diagnostics):
        return None, entries, diagnostics
    return image, entries, diagnostics


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def report(entries, diagnostics) -> str:
    errors = sum(1 for d in diagnostics if d.severity == ERROR)
    lines = ["Timing ROM Generation Report", "============================", "",
             f"Status: {'FAILED' if errors else 'SUCCEEDED'}", f"Errors: {errors}", ""]
    if entries:
        lines += ["Entries (TS length / TP width -> byte)", "--------------------------------------"]
        rows: dict[tuple, list[str]] = {}
        for e in entries:
            key = (e["timing_mode"], e["major_state"], e["auto_index_required"])
            rows.setdefault(key, []).append(f"{e['ts_length']}/{e['tp_width']} -> {e['byte']}")
        for (mode, state, ai), cells in sorted(rows.items()):
            lines.append(f"mode {mode} {state:<9} AUTO_INDEX_REQUIRED = {ai}: " + ", ".join(cells))
        lines.append("")
    if diagnostics:
        lines += ["Diagnostics", "-----------"]
        for d in diagnostics:
            lines.append(f"{d.severity} {d.code}" + (f" [{d.entry}]" if d.entry else "") + f": {d.message}")
        lines.append("")
    return "\n".join(lines)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def parse_arguments(arguments: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(arguments)


def main(arguments: Sequence[str] | None = None) -> int:
    root = parse_arguments(arguments).repo_root.resolve()
    for path in (DEFAULT_IMAGE, DEFAULT_JSON, DEFAULT_REPORT):
        if (root / path).exists():
            (root / path).unlink()
    try:
        arch = (root / TIMING_ARCHITECTURE).read_text(encoding="utf-8")
        cso = (root / CONTROL_STORE_ORGANIZATION).read_text(encoding="utf-8")
    except OSError as exc:
        diagnostics = [Diagnostic(ERROR, "MISSING_SOURCE", str(exc))]
        write_text(root / DEFAULT_REPORT, report([], diagnostics))
        print(f"Timing ROM generation\nStatus: FAILED\n{exc}")
        return 1
    image, entries, diagnostics = build(arch, cso)
    write_text(root / DEFAULT_REPORT, report(entries, diagnostics))
    if image is None:
        print("Timing ROM generation\nStatus: FAILED")
        return 1
    write_text(root / DEFAULT_IMAGE, "".join(f"{v:02X}\n" for v in image))
    write_text(root / DEFAULT_JSON, json.dumps(
        {"artifact": "timing-rom", "control_design_version": DESIGN.name,
         "sources": [TIMING_ARCHITECTURE.as_posix(), CONTROL_STORE_ORGANIZATION.as_posix()],
         "entries": entries}, indent=2, ensure_ascii=False) + "\n")
    print("Timing ROM generation\nStatus: SUCCEEDED")
    print(f"Image: {root / DEFAULT_IMAGE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
