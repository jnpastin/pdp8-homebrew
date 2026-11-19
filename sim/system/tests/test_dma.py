"""Milestone M7: DMA major states through the control store, in lock-step with the reference model.

A DmaTestMaster (test equipment, not a device model) performs prepared single-word transfers;
the DmaArbiter selects it (docs/07-io/05-dma-interface.md, 06-dma-arbitration.md). Each DMA major
state is a lock-step boundary: both models must agree on its memory write, the master's state,
and the arbiter's selection and burst count.
"""

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system.lockstep import Lockstep, ReferenceError, reference_from
from pdp8_system.machine import DmaArbiter, DmaTestMaster, Machine, load_store

HLT, NOP, IAC = 0o7402, 0o7000, 0o7001
KINDS = {"instruction": "I", "interrupt": "N", "dma": "D"}


def write(f, a, v):
    return ("write", f, a, v)


def machine(blocks, masters, burst_limits=None):
    m = Machine(load_store(), devices=list(masters), dma=DmaArbiter(masters, burst_limits=burst_limits))
    for (f, a), words in blocks.items():
        m.deposit_block(a, words, instruction_field=f)
    m.load_address(0o200)
    m.start()
    return m


def run(m, int_req=None, max_steps=200):
    """Lock-step to the halt; returns the boundary kinds as a string (I, N, D; H after a halt)."""
    ls = Lockstep(m, int_req=int_req)
    kinds = []
    for _ in range(max_steps):
        expected, _ = ls.step()
        kinds.append(KINDS[expected.kind])
        if expected.halted:
            return "".join(kinds) + "H"
    raise AssertionError("did not halt")


class Bursts(unittest.TestCase):
    def test_bursts_fairness_reads_and_writes(self):
        # ARB §11: bursts of at most the limit; §12: one instruction between bursts. DMA §5: reads
        # capture memory (here a word DMA wrote, and a program word); writes reach memory.
        master = DmaTestMaster(3, schedule={3: [write(1, 0o100, 0o1234), write(1, 0o101, 0o4321),
                                                write(2, 0o7777, 0o0007), ("read", 1, 0o100),
                                                ("read", 0, 0o200)]})
        m = machine({(0, 0o200): [IAC] * 12 + [HLT]}, [master], burst_limits={3: 2})
        self.assertEqual(run(m), "IIIIDDIDDIDIIIIIIIH")
        self.assertEqual(master.read_values, [0o1234, IAC])
        self.assertEqual((m.memory.read(1, 0o101), m.memory.read(2, 0o7777), m.state["AC"]),
                         (0o4321, 0o0007, 12))

    def test_the_program_sees_a_dma_write(self):
        master = DmaTestMaster(0, schedule={1: [write(0, 0o300, 0o0005)]})
        m = machine({(0, 0o200): [NOP, NOP, 0o7200, 0o1300, HLT], (0, 0o300): [0]}, [master])  # TAD 300
        self.assertEqual(run(m), "IIDIIIH")   # loaded at boundary 1, sampled at the next TS4
        self.assertEqual(m.state["AC"], 5)


class Priority(unittest.TestCase):
    def test_fixed_priority_non_preemptive(self):
        # ARB §9: master 2 arrives during master 5's burst and waits; it wins the next arbitration.
        a = DmaTestMaster(5, schedule={1: [write(0, 0o300 + i, i) for i in range(6)]})
        b = DmaTestMaster(2, schedule={3: [write(0, 0o400 + i, i) for i in range(3)]})
        m = machine({(0, 0o200): [NOP] * 12 + [HLT]}, [a, b], burst_limits={5: 3, 2: 2})
        self.assertEqual(run(m), "IIDDDIDDIDIDDDIIIIIIIIH")


class InterruptsAndInitialization(unittest.TestCase):
    def test_interrupt_takes_precedence(self):
        # REC §7: an interrupt and DMA at the same EXECUTE TP4 select INTERRUPT; no DMA follows the
        # INTERRUPT state; the deferred DMA (REC §8) is served after the handler's first instruction.
        master = DmaTestMaster(1, schedule={2: [write(0, 0o300, 7)]})
        m = machine({(0, 0o200): [0o6001, NOP, NOP, NOP, HLT], (0, 0o001): [NOP, HLT]}, [master])
        self.assertEqual(run(m, int_req=lambda n: n >= 2), "IIINIDIH")
        self.assertEqual(m.memory.read(0, 0o300), 7)

    def test_caf_cancels_a_sampled_request(self):
        # DMX §5: CAF's /INITIALIZE cancels the request sampled at its TS4; the DMA major state
        # that follows transfers nothing.
        master = DmaTestMaster(1, schedule={1: [write(0, 0o300 + i, i) for i in range(5)]})
        m = machine({(0, 0o200): [NOP, 0o6007, NOP, HLT]}, [master], burst_limits={1: 8})
        self.assertEqual(run(m), "IIDIIH")
        self.assertEqual(master.queue, [])

    def test_no_dma_after_a_halt(self):
        master = DmaTestMaster(1, schedule={1: [write(0, 0o300, 1)]})
        m = machine({(0, 0o200): [NOP, HLT]}, [master])
        self.assertEqual(run(m), "IIH")


def random_dma_episodes(seed, episodes, length):
    """Random programs over random memory with two masters doing random transfers in all fields."""
    rng = random.Random(seed)
    schedule = lambda: {k: [(("read", rng.randrange(8), rng.randrange(4096)) if rng.random() < 0.3 else
                              write(rng.randrange(8), rng.randrange(4096), rng.randrange(4096)))
                             for _ in range(rng.randrange(1, 6))]
                        for k in range(1, episodes * length, 7)}
    masters = [DmaTestMaster(rng.randrange(0, 7), schedule()), DmaTestMaster(rng.randrange(7, 15), schedule())]
    m = machine({}, masters, burst_limits={masters[0].dma_priority: rng.randrange(1, 4)})
    m.cpu.st["RUN"] = 0
    for f in range(8):
        m.memory.preload(f, 0, [rng.randrange(4096) for _ in range(4096)])
    coverage, st = Counter(), m.state
    for _ in range(episodes):
        m.load_address(rng.randrange(4096), rng.randrange(8), rng.randrange(8))
        st["AC"], st["L"], st["IE"], st["IB"] = rng.randrange(4096), rng.randrange(2), rng.randrange(2), rng.randrange(64)
        st["CIFP"], st["II"] = 0, 0
        m.cont()
        ls = Lockstep(m, reference_from(m), int_req=lambda n: rng.random() < 0.3)
        try:
            for _ in range(length):
                expected, _ = ls.step()
                coverage[expected.kind] += 1
                if expected.halted:
                    break
        except ReferenceError:
            coverage["undefined state"] += 1
        if m.cpu.running:
            st["RUN"] = 0
    return coverage


class RandomEpisodes(unittest.TestCase):
    def test_random_programs_with_dma_agree(self):
        coverage = Counter()
        for seed in (31, 32):
            coverage += random_dma_episodes(seed, episodes=60, length=40)
        for kind in ("instruction", "interrupt", "dma"):
            self.assertGreater(coverage[kind], 0, kind)


if __name__ == "__main__":
    unittest.main()
