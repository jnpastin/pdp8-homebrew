"""Command-line runner for the control-store simulator.

    python sim/system/src/run_sim.py --check
        Load and validate the control-store images, the packing description, and the field
        encodings, then power on and run the console self-check (LOAD ADDRESS, DEPOSIT,
        EXAMINE, START of a HLT).
"""

from __future__ import annotations

import argparse
import sys

from pdp8_system.machine import Machine, SimError, load_store


def self_check() -> int:
    store = load_store()
    print(f"control store loaded: {len(store.datapath_layout)} datapath slots, "
          f"{len(store.overlay_groups)} overlay groups")
    m = Machine(store)
    m.deposit_block(0o200, [0o7402])                  # HLT
    m.load_address(0o200)
    if m.examine() != 0o7402:
        print("EXAMINE did not return the deposited word")
        return 1
    m.load_address(0o200)
    m.start()
    n = m.run(max_ts=100)
    pc = m.state["PC"]
    print(f"HLT at 0200 halted after {n} timing states with PC = {pc:04o}")
    return 0 if pc == 0o201 else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="validate the images and run the console self-check")
    args = parser.parse_args(argv)
    if not args.check:
        parser.print_help()
        return 2
    try:
        return self_check()
    except SimError as e:
        print(f"{type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
