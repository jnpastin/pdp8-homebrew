#!/usr/bin/env python3
"""Run every test suite under each control design (option2/plan.md phase 2.7).

    python sim/run_all_tests.py                 # both designs, every suite
    python sim/run_all_tests.py --design v2     # one design
    python sim/run_all_tests.py --quick         # skip the system suite (about 6 minutes per design)
    python sim/run_all_tests.py --build         # first pack each design (pipeline dry runs)
    PDP8_LONG_TESTS=1 python sim/run_all_tests.py   # also D2AB timing (use PyPy)

Each design's suites run with PDP8_DESIGN set (sim/cpu/src/pdp8_cpu/design.py). The
ROM-generation tool tests run once; they do not depend on the design. Exit status 0 when every
suite passes.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DESIGNS = ("v1", "v2")  # V1-ONLY: ("v2",) after cleanup
UNIT_SUITES = ("sim/cpu", "sim/memory", "sim/reference", "sim/io")


def run(label: str, command: list, cwd: Path, env: dict) -> bool:
    start = time.time()
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    tail = (result.stdout + result.stderr).strip().splitlines()
    summary = next((line for line in reversed(tail) if line.startswith(("OK", "FAILED"))), "?")
    ran = next((line for line in reversed(tail) if line.startswith("Ran ")), "")
    ok = result.returncode == 0
    print(f"  {label:<40} {summary:<28} {ran:<28} {time.time() - start:6.0f} s", flush=True)
    if not ok:
        print("\n".join("    " + line for line in tail[-30:]))
    return ok


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--design", choices=DESIGNS, action="append",
                        help="design(s) to test (default: all)")
    parser.add_argument("--quick", action="store_true", help="skip the system suite")
    parser.add_argument("--build", action="store_true", help="pack each design first")
    parser.add_argument("--no-tools", action="store_true", help="skip the ROM-generation tool tests")
    args = parser.parse_args(argv)
    designs = args.design or list(DESIGNS)
    python = sys.executable
    ok = True

    if args.build:
        print("Packing")
        for d in designs:
            ok &= run(f"pipeline --dry-run --design {d}",
                      [python, "tools/rom-generation/pipeline/src/run_pipeline.py", "--dry-run",
                       "--design", d], REPO, dict(os.environ))
    if not args.no_tools:
        print("ROM-generation tools")
        for tool in sorted((REPO / "tools" / "rom-generation").iterdir()):
            if (tool / "tests").is_dir():
                ok &= run(tool.name, [python, "-m", "unittest", "discover", "-s", str(tool / "tests"),
                                      "-p", "test_*.py"], REPO, dict(os.environ))
    for d in designs:
        env = dict(os.environ, PDP8_DESIGN=d)
        print(f"Simulator, design {d}")
        for suite in UNIT_SUITES:
            ok &= run(suite, [python, "-m", "unittest", "discover", "-s", f"{suite}/tests"], REPO, env)
        if not args.quick:
            ok &= run("sim/system", [python, "-m", "unittest", "discover", "-s", "."],
                      REPO / "sim" / "system" / "tests", env)
    print("\nAll suites passed." if ok else "\nFAILURES above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
