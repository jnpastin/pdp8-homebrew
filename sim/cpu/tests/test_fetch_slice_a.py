"""Slice A FETCH (option2/plan.md phase 3), run on the packed v2 images.

docs/03-microarchitecture/04-fetch-defer.md §3: TS1 PC_TO_MA and PC_INC; TS2 MEM_READ_TO_MB and
MDB_TO_IR; TS3 IR_ADDR_TO_EA_ADDR, the page from MA; TS4 only the next-state decision.
docs/04-control/08-control-store-organization.md §5.4.3: the MAPR entry captured at FETCH TP2 is
formed from the previous IR; from TP3 on, every entry is the current IR's.
"""

import unittest

import _paths  # noqa: F401
from pdp8_cpu import address as A
from pdp8_cpu import design as D
from pdp8_cpu import encodings as E
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory

NOP, TAD_CURRENT_100, HLT = 0o7000, 0o1300, 0o7402


def machine(design):
    """NOP at 0376; TAD 0300 (current page, offset 100) at 0377, the last word of page 0200-0377;
    HLT at 0400, the first word of the next page. M[0300] = 0042; M[0700] = 0077 (the wrong page)."""
    store = ControlStore.load(design=D.select(design))
    cpu = Cpu(store, Memory())
    cpu.power_on()
    for addr, word in ((0o376, NOP), (0o377, TAD_CURRENT_100), (0o400, HLT),
                       (0o300, 0o0042), (0o700, 0o0077)):
        cpu.memory.write(0, addr, word)
    cpu.panel.sr = 0o376
    cpu.press("LOAD_ADDRESS")
    cpu.press("START")
    return cpu


def run_to_halt(cpu, limit=100):
    records = []
    for _ in range(limit):
        r = cpu.step_ts()
        if r is None:
            return records
        records.append(r)
    raise AssertionError("no halt")


class CurrentPageAtEndOfPage(unittest.TestCase):
    """Architectural result: the current page is the instruction's page, in both designs."""

    def check(self, design):
        cpu = machine(design)
        run_to_halt(cpu)
        self.assertEqual(cpu.st["AC"], 0o0042)
        self.assertEqual(cpu.st["PC"], 0o0401)

    def test_v2(self):
        self.check("v2")

    def test_v1(self):  # V1-ONLY
        self.check("v1")


class FetchTimingV2(unittest.TestCase):
    def setUp(self):
        self.cpu = machine("v2")
        self.records = run_to_halt(self.cpu)
        tad_start = next(i for i, r in enumerate(self.records)
                         if r.ms == E.FETCH and r.ts == 1 and r.pc == 0o377)
        self.fetch = self.records[tad_start:tad_start + 4]

    def test_ts1_loads_ma_and_increments_pc(self):
        loads = self.fetch[0].loads
        self.assertEqual(loads["MA"], 0o377)
        self.assertEqual(loads["PC"], 0o400)

    def test_ts2_loads_ir_and_mb_from_the_read(self):
        r = self.fetch[1]
        self.assertEqual(r.loads["IR"], TAD_CURRENT_100)
        self.assertEqual(r.loads["MB"], TAD_CURRENT_100)
        self.assertEqual(r.mem_read, (0, 0o377))

    def test_ts3_forms_ea_from_the_page_of_ma(self):
        self.assertEqual(self.fetch[2].loads["EA_ADDR"], 0o300)    # not 0700 (PC's page)

    def test_ts4_changes_no_datapath_register(self):
        datapath = {"AC", "L", "MQ", "IR", "PC", "MA", "MB", "EA_ADDR"}
        self.assertFalse(datapath & self.fetch[3].loads.keys())


class MaprAtTp2(unittest.TestCase):
    """CSO §5.4.3: the mapping ROM is addressed by the pre-TP IR."""

    def test_entries_follow_ir(self):
        cpu = machine("v2")
        while not (cpu.st["MS"] == E.FETCH and cpu.st.ts == 1 and cpu.st["PC"] == 0o377):
            cpu.step_ts()
        cpu.step_ts()                                   # TS1
        cpu.step_ts()                                   # TS2: IR loads at TP2
        self.assertEqual(cpu.st["IR"], TAD_CURRENT_100)
        self.assertEqual(cpu.st["MAPR"], cpu.store.mapping_entry(A.mapping_address(NOP, 2)))
        cpu.step_ts()                                   # TS3
        self.assertEqual(cpu.st["MAPR"], cpu.store.mapping_entry(A.mapping_address(TAD_CURRENT_100, 3)))


if __name__ == "__main__":
    unittest.main()
