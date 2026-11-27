"""DEC MAINDEC-8E diagnostics run in lock-step to a complete pass, in parallel.

The regression suite (test_maindec.py) bounds each program at 25,000 instructions. These runs go
on to each program's first pass marker, end typeout, or end-of-program halt, so every test the
program makes is made once, on the simulated control design, and checked against the reference
model on every instruction. Each program runs in its own process, one per core.

Opt-in, by PDP8_FULL_PASSES (PyPy recommended). Lock-step runs about 22,000 instructions/s in
one process, and about 12,000 per process with every core busy:

- `short`: D0CC to D0JC (0.7 to 4.6 million instructions each) and D1EC (10.3 million). About
  15 minutes, bounded by D1EC.
- `all`: also D1HA (92.5 million), D1FB to its first time tick (109.3 million), D1BC (125
  million), D1AA (127 million), and D2AB PRG0 (about 32 million), whose timing routines then run on
  the microcoded CPU rather than only on the reference model (test_d2ab_timing.py). About 2 to 3
  hours, bounded by D1AA and D1BC.

Not run: D2CA, which needs a PC8-E reader/punch model and has no write-up
(sim/test_programs/README.md).
"""

import os
import sys
import time
import unittest
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system import maindec  # noqa: E402

MODE = os.environ.get("PDP8_FULL_PASSES", "").lower()
DESIGN = os.environ.get("PDP8_DESIGN", "v1")   # V1-ONLY: the selector's default

# (name, instruction limit, what ends the pass). Limits are about 1.3 times the pass length
# observed on the reference model (maindec.DIAGNOSTICS comments).
SHORT = (
    ("d0cc", 800_000, "text SIMAD"),        # end typeout after 737,358 instructions
    ("d0db", 1_600_000, "marker"),
    ("d0eb", 3_700_000, "marker"),
    ("d0fc", 4_300_000, "marker"),
    ("d0gc", 3_200_000, "marker"),
    ("d0hc", 5_400_000, "marker"),
    ("d0ib", 4_900_000, "marker"),
    ("d0jc", 6_000_000, "marker"),
    ("d1ec", 13_500_000, "marker"),         # first "EC" after 10,335,681 instructions
)
LONG = (
    ("d1ha", 120_000_000, "marker"),        # first bell after 92,510,728 instructions
    ("d1fb", 140_000_000, "marker"),        # first "5" (a time tick) after 109,305,776 instructions
    ("d1bc", 165_000_000, "marker"),        # first pass "5" after 125,006,147 instructions
    ("d1aa", 165_000_000, "marker"),        # first "5" after 127,159,300 instructions
    ("d2ab-prg0", 60_000_000, "end halt"),  # about 32 million
)
# V1-ONLY: v1's state durations make D2AB PRG0's flag test fail (test_d2ab_timing.py).
D2AB_V1_HALT = "at 2607"


def selected():
    if MODE == "short":
        return SHORT
    if MODE == "all":
        return SHORT + LONG
    return ()


def run_one(job):
    """One program, in a worker process: returns its outcome and wall time."""
    name, limit, end = job
    start = time.time()
    outcome = maindec.run(name, limit, stop_after_markers=1 if end == "marker" else None)
    return outcome, time.time() - start


@unittest.skipUnless(selected(), "set PDP8_FULL_PASSES=short or all to run (PyPy recommended)")
class FullPasses(unittest.TestCase):
    def test_programs(self):
        jobs = selected()
        with ProcessPoolExecutor(max_workers=min(len(jobs), os.cpu_count() or 1)) as pool:
            results = list(pool.map(run_one, jobs))
        for (name, limit, end), (outcome, seconds) in zip(jobs, results):
            print(f"\n  {DESIGN} {outcome.summary()[:150]} ({seconds:.0f} s)", file=sys.stderr, end="")
            with self.subTest(program=name):
                if name == "d2ab-prg0" and DESIGN == "v1":                       # V1-ONLY
                    self.assertTrue(outcome.halt and outcome.halt.startswith(D2AB_V1_HALT),  # V1-ONLY
                                    outcome.summary())                           # V1-ONLY
                    continue                                                     # V1-ONLY
                self.assertTrue(outcome.passed, outcome.summary())
                if end == "marker":
                    self.assertGreaterEqual(outcome.markers, 1, outcome.summary())
                elif end == "end halt":
                    self.assertTrue(outcome.completed, outcome.summary())
                else:
                    self.assertIn(end.split()[1], maindec.text(outcome.printed), outcome.summary())


if __name__ == "__main__":
    unittest.main()
