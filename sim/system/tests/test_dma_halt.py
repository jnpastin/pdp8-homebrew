"""Halting between DMA cycles (docs/03-microarchitecture/10-dma-execution.md §4, DMX).

Single Step halts at the end of every major state, including DMA, so a burst can be held with
MS = DMA. The reference model has no halts inside a burst, so these tests drive the machine
through the console and check the arbiter, the controller, and memory directly.

- DMX §4: CONTINUE resumes at DMA TS1 and the burst continues with the same selection
- DMX §4, DMA Arbitration §13.3: EXAMINE loads FETCH as the held state; the selection is kept and
  the burst continues at the next DMA entry
- DMX §4, DMA Arbitration §13.2: START and CLEAR initialize the arbiter and the controllers,
  cancelling the burst; CONTINUE after CLEAR runs one DMA state with no selection (DMX §5)
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system.machine import DmaArbiter, DmaTestMaster, Machine, load_store  # sets the paths
from pdp8_cpu import encodings as E  # noqa: E402
from pdp8_cpu import design as DS  # noqa: E402

NOP, HLT = 0o7000, 0o7402
WORDS = (0o300, 0o301, 0o302)


def write(a, v):
    return ("write", 0, a, v)


@unittest.skipIf(DS.select().name == "v1",   # V1-ONLY: v1 runs every OPR through EXECUTE, and its
                 "v1 sequences OPR and START differently")     # START does not initialize
class HaltInsideABurst(unittest.TestCase):
    def setUp(self):
        # Three writes, prepared at the first instruction boundary, in one burst (limit 8).
        self.master = DmaTestMaster(1, schedule={1: [write(a, i + 1) for i, a in enumerate(WORDS)]})
        self.arbiter = DmaArbiter([self.master], burst_limits={1: 8})
        self.m = Machine(load_store(), devices=[self.master], dma=self.arbiter)
        self.m.deposit_block(0o200, [NOP, NOP, NOP, NOP, HLT])
        self.m.load_address(0o200)
        self.m.panel.single_step = True
        self.m.start()

    def halt(self):
        """Run to the next Single Step halt; return (held MS, grant, burst count, the three words)."""
        self.m.run(200)
        st = self.m.cpu.st
        self.assertEqual(st["RUN"], 0)
        return (st["MS"], self.arbiter.grant_id, self.arbiter.burst_count,
                [self.m.memory.read(0, a) for a in WORDS])

    def into_the_burst(self):
        """Halt after the burst's first word, with the selection held and MS = DMA."""
        self.assertEqual(self.halt()[0], E.FETCH)          # the first NOP, which loads the master
        self.m.cont()
        self.assertEqual(self.halt(), (E.DMA, 15, 0, [None, None, None]))   # second NOP: DMA next
        self.m.cont()
        self.assertEqual(self.halt(), (E.DMA, 1, 1, [1, None, None]))       # one word; DMA held
        self.assertEqual(self.m.cpu.st["PC"], 0o202)

    def test_continue_resumes_the_burst_with_the_same_selection(self):
        self.into_the_burst()
        self.m.cont()
        self.assertEqual(self.halt(), (E.DMA, 1, 2, [1, 2, None]))
        self.m.cont()
        self.assertEqual(self.halt(), (E.FETCH, 15, 0, [1, 2, 3]))         # the last word ends it
        self.assertEqual(self.m.cpu.st["PC"], 0o202)

    def test_examine_resumes_at_fetch_and_keeps_the_selection(self):
        self.into_the_burst()
        self.assertEqual(self.m.examine(), NOP)                            # memory used normally
        self.assertEqual(self.halt(), (E.FETCH, 1, 1, [1, None, None]))    # selection kept
        self.m.cont()                                                      # the instruction at 203
        self.assertEqual(self.halt(), (E.DMA, 1, 1, [1, None, None]))      # DMA entered again
        self.m.cont()
        self.assertEqual(self.halt(), (E.DMA, 1, 2, [1, 2, None]))         # same selection
        self.m.cont()
        self.assertEqual(self.halt()[3], [1, 2, 3])

    def test_start_cancels_the_held_burst(self):
        self.into_the_burst()
        self.m.panel.single_step = False
        self.m.start()
        self.assertEqual((self.arbiter.grant_id, self.arbiter.burst_count, self.master.queue),
                         (15, 0, []))
        self.assertEqual(self.halt(), (E.FETCH, 15, 0, [1, None, None]))   # runs to the HLT
        self.assertEqual(self.m.cpu.st["PC"], 0o205)

    def test_continue_after_clear_runs_one_dma_state_without_a_selection(self):
        self.into_the_burst()
        self.m.clear()
        self.assertEqual((self.m.cpu.st["MS"], self.arbiter.grant_id, self.master.queue),
                         (E.DMA, 15, []))
        self.m.cont()
        self.assertEqual(self.halt(), (E.FETCH, 15, 0, [1, None, None]))   # no transfer
        self.assertEqual(self.m.cpu.st["PC"], 0o202)


if __name__ == "__main__":
    unittest.main()
