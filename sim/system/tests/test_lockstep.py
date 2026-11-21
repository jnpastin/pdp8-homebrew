"""Milestone M2: lock-step comparison of the control-store simulator with the reference model."""

import random
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system.lockstep import (
    Divergence,
    Lockstep,
    ReferenceError,
    disassemble,
    reference_from,
)
from pdp8_system.machine import ControlStore, Machine, load_store

HLT, NOP = 0o7402, 0o7000


def started(blocks, start=0o200, field=0, data_field=None):
    m = Machine(load_store())
    for (f, a), words in blocks.items():
        m.deposit_block(a, words, instruction_field=f)
    m.load_address(start, field, field if data_field is None else data_field)
    m.start()
    return m


PROGRAMS = {
    "mri": {(0, 0o200): [0o7300, 0o1250, 0o1251, 0o3252, 0o1253, 0o0254, 0o2255, HLT, HLT],
            (0, 0o250): [0o3777, 0o0001, 0o1111, 0o7070, 0o0770, 0o7777]},
    "jms": {(0, 0o200): [0o4220, HLT], (0, 0o220): [0, 0o7001, 0o5620]},
    "autoindex": {(0, 0o200): [0o7300, 0o1410, 0o1410, 0o3410, HLT],
                  (0, 0o010): [0o0277], (0, 0o300): [0o0005, 0o0006]},
    "fields": {(0, 0o200): [0o6211, 0o1620, 0o6222, 0o4621, HLT], (0, 0o220): [0o0500, 0o0400],
               (1, 0o500): [0o0777], (2, 0o400): [0, 0o7001, HLT]},
    "iots": {(0, 0o200): [0o7120, 0o6231, 0o6001, 0o6004, 0o6000, HLT, 0o6005, 0o5611],
             (0, 0o211): [0o0300], (0, 0o300): [HLT]},
}


class ProgramsInLockstep(unittest.TestCase):
    """The M1 programs, compared after every instruction instead of only at the end."""

    def test_programs(self):
        for name, blocks in PROGRAMS.items():
            with self.subTest(program=name):
                m = started(blocks)
                m.state["IB"] = 0o03     # "iots": GTF reports IB, and RTF then restores IF 0, DF 3 from it
                Lockstep(m).run(200)
                self.assertEqual(m.state["RUN"], 0)

    def test_interrupt_programs(self):
        isr = [0o6234, 0o3020, 0o6244, 0o5400]          # RIB; DCA 20; RMF; JMP I 0
        blocks = {(1, 0o200): [0o6221, 0o6001, NOP, 0o6212, 0o5300], (1, 0o300): [0o7001, HLT],
                  (0, 0o001): isr}
        m = started(blocks, field=1)
        requests = {2, 3, 4, 5, 9, 10}                    # asserted for these steps only
        Lockstep(m, int_req=lambda n: n in requests).run(200)
        self.assertEqual((m.state["IF"], m.state["DF"]), (1, 2))


def biased_memory(rng):
    """Random words, a quarter of them drawn from the processor and memory-extension IOTs."""
    interesting = ([0o6000 + k for k in range(8)] + [0o6201 + (n << 3) + k for n in range(8) for k in range(3)]
                   + [0o6214, 0o6224, 0o6234, 0o6244])
    return [rng.choice(interesting) if rng.random() < 0.25 else rng.randrange(4096) for _ in range(4096)]


def random_episodes(seed, episodes, length):
    """Short lock-step runs from random processor states over random memory in all eight fields."""
    rng = random.Random(seed)
    m = Machine(load_store())
    for f in range(8):
        m.memory.preload(f, 0, biased_memory(rng))
    coverage, st = Counter(), m.state
    for _ in range(episodes):
        m.load_address(rng.randrange(4096), rng.randrange(8), rng.randrange(8))
        # Test-harness state: registers a program could reach, set directly before CONTINUE.
        st["AC"], st["L"], st["MQ"], st["IE"], st["IB"] = (rng.randrange(4096), rng.randrange(2),
                                                         rng.randrange(4096), rng.randrange(2), rng.randrange(64))
        if rng.random() < 0.2:
            st["DIF"], st["CIFP"], st["II"] = rng.randrange(8), 1, 1
        else:
            st["CIFP"], st["II"] = 0, 0
        m.panel.sr = rng.randrange(4096)
        m.cont()
        ls = Lockstep(m, reference_from(m), int_req=lambda n: rng.random() < 0.5)
        try:
            for _ in range(length):
                expected, _ = ls.step()
                coverage["interrupt" if expected.kind == "interrupt" else disassemble(expected.ir).split()[0]] += 1
                if expected.halted:
                    break
        except ReferenceError:
            coverage["undefined state"] += 1
        if m.cpu.running:                                 # end at the boundary just reached
            st["RUN"] = 0
    return coverage


class RandomEpisodes(unittest.TestCase):
    def test_random_programs_agree(self):
        coverage = Counter()
        for seed in (11, 12):
            coverage += random_episodes(seed, episodes=120, length=30)
        for item in ("interrupt", "CIF", "CDF", "RMF", "RTF", "RIB", "GTF", "ION", "SKON", "CAF",
                     "JMS", "JMP", "ISZ", "DCA", "TAD", "AND", "IOT"):
            self.assertGreater(coverage[item], 0, item)


class DivergenceDetection(unittest.TestCase):
    def test_a_simulator_fault_is_reported_with_the_instruction_and_ts(self):
        original = ControlStore.decode_datapath

        def jms_via_df(self, address):
            f = original(self, address)
            if f["/WR"] == 0 and (address >> 12) == 2 and f["PC_LOAD"] == 1:
                f = dict(f, MFB_SRC=1)                    # JMS return-address write via DF
            return f

        ControlStore.decode_datapath = jms_via_df
        try:
            m = started({(0, 0o200): [0o6221, 0o4220, HLT], (0, 0o220): [0, HLT]})
            with self.assertRaises(Divergence) as caught:
                Lockstep(m).run(20)
        finally:
            ControlStore.decode_datapath = original
        message = str(caught.exception)
        self.assertIn("0:0201 4220 JMS 020", message)
        self.assertIn("memory writes: simulator [2:0220=0202], reference [0:0220=0202]", message)

    def test_a_register_difference_names_the_committing_ts(self):
        m = started({(0, 0o200): [0o7001, HLT]})
        ls = Lockstep(m)
        ls.ref.ac = 0o0100                                # make the reference disagree
        with self.assertRaises(Divergence) as caught:
            ls.step()
        # Group 1 IAC commits at EXECUTE TP3 in v1 and at FETCH TP3 in v2 (OPR pass, slice C1).
        where = "FETCH TP3" if m.cpu.design.opr_pass else "EXECUTE TP3"   # V1-ONLY: the EXECUTE
        self.assertIn(f"AC: simulator 1, reference 101 (last committed at {where})", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
