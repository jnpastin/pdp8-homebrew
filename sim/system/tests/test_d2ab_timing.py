"""MAINDEC-8E-D2AB PRG0 instruction timing, on the reference model alone (option2/plan.md phase 0).

D2AB PRG0 routines 4 and 5 time the Teletype printer flag with ISZ/JMP delay loops calibrated to
PDP-8/E instruction timing; the flag must set no earlier than 9 and no later than about 9.55 bit
times after TLS. The reference model, run alone with the simulated design's cycle counts and
state durations, shows whether the design meets that window (phase 0: the ISZ + JMP loop must
take 3.75 to 3.85 us).

About 32 million reference-model instructions: run only when PDP8_LONG_TESTS is set (PyPy
recommended). Expected per design:
- v1: halt at 2607, "printer flag set prior to 9 bit times" (too slow). # V1-ONLY
- v2: halt at 2607 until slice D gives it its state lengths; then the end-of-program halt.
"""

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system import maindec  # noqa: E402
from pdp8_system.lockstep import reference_from  # noqa: E402

LONG = bool(os.environ.get("PDP8_LONG_TESTS"))
EXPECTED = {"v1": 0o2607, "v2": 0o2607}   # error-halt address, or None for a pass


def run_reference_alone(name: str, max_steps: int, seed: int = 1):
    """Run a diagnostic on the reference model alone, from the state the simulator's console
    loading left; returns (halt address or None for a documented end, steps)."""
    d = maindec.DIAGNOSTICS[name]
    m, _ = maindec.prepare(name, seed)
    ref = reference_from(m)
    for steps in range(1, max_steps + 1):
        r = ref.step()
        if r.halted:
            if ref.pc in d.continue_halts:
                ref.sr = d.continue_switches
                continue
            if ref.pc in d.pass_halts:
                return None, steps
            return r.pc, steps
    raise AssertionError(f"{name}: no halt in {max_steps} steps")


@unittest.skipUnless(LONG, "set PDP8_LONG_TESTS=1 to run (about 32 million reference instructions)")
class D2abTimingTests(unittest.TestCase):
    def test_prg0_timing_result_matches_design(self):
        m, _ = maindec.prepare("d2ab-prg0", 1)
        design = m.cpu.design.name
        halt, steps = run_reference_alone("d2ab-prg0", 60_000_000)
        expected = EXPECTED[design]
        where = "the end of the program" if halt is None else f"a halt at {halt:04o}"
        want = "the end of the program" if expected is None else f"a halt at {expected:04o}"
        self.assertEqual(halt, expected, f"design {design}: {where} after {steps} instructions, "
                                         f"expected {want}")


if __name__ == "__main__":
    unittest.main()
