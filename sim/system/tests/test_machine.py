import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import run_sim
from pdp8_cpu import design as D
from pdp8_system.machine import Machine


class MachineTests(unittest.TestCase):
    def test_deposit_examine_block(self):
        m = Machine()
        m.deposit_block(0o0200, [0o1111, 0o2222, 0o3333], instruction_field=1)
        m.load_address(0o0200, instruction_field=1)
        self.assertEqual([m.examine() for _ in range(3)], [0o1111, 0o2222, 0o3333])
        self.assertEqual(m.memory.write_count, 3)                    # one write per DEPOSIT

    def test_run_until_halt(self):
        m = Machine(keep_trace=True)
        m.deposit_block(0o0200, [0o7402])
        m.load_address(0o0200)
        m.start()
        # HLT runs FETCH and EXECUTE in v1, FETCH alone in v2 (Group 2 OPR completes in FETCH).
        self.assertEqual(m.run(max_ts=50), 4 * len(D.major_states(m.cpu.design, 0o7402)))
        self.assertEqual(m.state["PC"], 0o0201)

    def test_cli_check(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(run_sim.main(["--check"]), 0)
        self.assertIn("PC = 0201", out.getvalue())


if __name__ == "__main__":
    unittest.main()
