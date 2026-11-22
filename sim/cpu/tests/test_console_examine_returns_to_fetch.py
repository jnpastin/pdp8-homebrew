"""CONTINUE after EXAMINE or DEPOSIT starts a FETCH, on the packed v2 images (review item C11).

- docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md §3.2.12
- docs/03-microarchitecture/09-console-execution.md §3
- PDP-8/E: CONT after EXAM or DEP causes a FETCH cycle (maintenance manual, volume 1, §3.8.2)
"""

import unittest

import _paths  # noqa: F401
from pdp8_cpu import design as D
from pdp8_cpu import encodings as E
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory

TAD_300, HLT = 0o1300, 0o7402

_STORE = None


def store():
    global _STORE
    if _STORE is None:
        _STORE = ControlStore.load(design=D.select("v2"))
    return _STORE


def machine():
    cpu = Cpu(store(), Memory())
    cpu.power_on()
    for a in range(0o10000):
        cpu.memory.write(0, a, HLT)
    cpu.memory.write(0, 0o200, TAD_300)
    cpu.memory.write(0, 0o300, 0o0005)
    cpu.memory.write(0, 0o400, 0o0040)
    cpu.panel.sr = 0o200
    cpu.press("LOAD_ADDRESS")
    cpu.press("START")
    return cpu


def run(cpu, limit=200):
    records = []
    for _ in range(limit):
        r = cpu.step_ts()
        if r is None:
            return records
        records.append(r)
    raise AssertionError("no halt")


class ExamineDuringSingleStep(unittest.TestCase):
    def halted_in_execute(self):
        cpu = machine()
        cpu.panel.single_step = True
        run(cpu)                                                    # the TAD's FETCH
        self.assertEqual((cpu.st["RUN"], cpu.st["MS"], cpu.st["PC"]), (0, E.EXECUTE, 0o201))
        cpu.panel.single_step = False
        return cpu

    def test_continue_without_examine_finishes_the_instruction(self):
        cpu = self.halted_in_execute()
        cpu.press("CONTINUE")
        records = run(cpu)
        self.assertEqual(records[0].ms, E.EXECUTE)
        self.assertEqual(cpu.st["AC"], 0o0005)

    def test_examine_makes_continue_start_a_fetch(self):
        for command in ("EXAMINE", "DEPOSIT"):
            with self.subTest(command=command):
                cpu = self.halted_in_execute()
                cpu.panel.sr = 0o400
                cpu.press("LOAD_ADDRESS")
                cpu.press(command)
                self.assertEqual((cpu.st["MS"], cpu.st["PC"]), (E.FETCH, 0o401))
                cpu.press("CONTINUE")
                records = run(cpu)
                self.assertEqual(records[0].ms, E.FETCH)             # not the TAD's EXECUTE
                self.assertEqual(cpu.st["AC"], 0)                    # the TAD never completes

    def test_examine_replaces_a_held_dma_state(self):
        cpu = machine()
        cpu.panel.single_step = True
        cpu.ext.dma_req_n = 0
        run(cpu)                                                    # the TAD's FETCH
        cpu.press("CONTINUE")
        run(cpu)                                                    # its EXECUTE, then DMA is next
        self.assertEqual((cpu.st["RUN"], cpu.st["MS"]), (0, E.DMA))
        cpu.press("EXAMINE")
        self.assertEqual(cpu.st["MS"], E.FETCH)


if __name__ == "__main__":
    unittest.main()
