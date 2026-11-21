"""Slice B (option2/plan.md phase 4), run on the packed v2 images: JMP completes in FETCH (direct)
or DEFER (JMP I).

- docs/03-microarchitecture/04-fetch-defer.md §3.3, §3.4, §4.4, §4.5
- docs/04-control/30-direct-control-definitions/01-sequencing-and-internal-control.md §3.1.1
  (instruction completion), §3.2, §3.3, §3.4
- docs/08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md §12 (JMP applies a pending field
  change at FETCH TP3 or DEFER TP3, so an interrupt may follow at the same JMP's completion)
"""

import unittest

import _paths  # noqa: F401
from pdp8_cpu import design as D
from pdp8_cpu import encodings as E
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory

JMP_300, JMP_I_50, JMP_I_10 = 0o5300, 0o5450, 0o5410   # JMP 0300 (current page); JMP I 0050, 0010
NOP, HLT, ION, CIF_2 = 0o7000, 0o7402, 0o6001, 0o6222

_STORE = None


def store():
    global _STORE
    if _STORE is None:
        _STORE = ControlStore.load(design=D.select("v2"))
    return _STORE


def machine(program, start=0o200, fields=(0,)):
    """`program`: {address: word} in field 0. Every other word of the listed fields is a HLT,
    so a wrong transfer stops quickly."""
    cpu = Cpu(store(), Memory())
    cpu.power_on()
    for f in fields:
        for a in range(0o10000):
            cpu.memory.write(f, a, HLT)
    for addr, word in program.items():
        f, a = addr if isinstance(addr, tuple) else (0, addr)
        cpu.memory.write(f, a, word)
    cpu.panel.sr = start
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


def states(records):
    """The major states run, one entry per state (at its TS1)."""
    return [E.MS_NAMES[r.ms] for r in records if r.ts == 1]


class JmpPaths(unittest.TestCase):
    def test_direct_jmp_completes_in_fetch(self):
        cpu = machine({0o200: JMP_300, 0o300: HLT})
        records = run(cpu)
        self.assertEqual(states(records)[:2], ["FETCH", "FETCH"])     # JMP, then HLT's FETCH
        fetch = records[:4]
        self.assertEqual(fetch[2].loads["PC"], 0o300)                   # PC <- formed address at TP3
        self.assertEqual(cpu.boundary_kind(fetch[3]), "instruction")    # completes at FETCH TP4
        self.assertEqual(cpu.st["PC"], 0o301)

    def test_jmp_i_completes_in_defer(self):
        cpu = machine({0o200: JMP_I_50, 0o50: 0o400, 0o400: HLT})
        records = run(cpu)
        self.assertEqual(states(records)[:3], ["FETCH", "DEFER", "FETCH"])
        defer = records[4:8]
        self.assertEqual(defer[3].loads["PC"], 0o400)                   # PC <- MB at DEFER TP4
        self.assertEqual(cpu.boundary_kind(defer[3]), "instruction")
        self.assertEqual(cpu.st["PC"], 0o401)

    def test_autoindex_jmp_i_uses_the_incremented_pointer(self):
        cpu = machine({0o200: JMP_I_10, 0o10: 0o477, 0o500: HLT})
        run(cpu)
        self.assertEqual(cpu.memory.read(0, 0o10), 0o500)               # written back
        self.assertEqual(cpu.st["PC"], 0o501)                           # HLT at 0500 ran

    def test_other_instructions_still_enter_execute(self):
        cpu = machine({0o200: 0o1050, 0o201: HLT, 0o50: 1})              # TAD 0050
        self.assertEqual(states(run(cpu))[:2], ["FETCH", "EXECUTE"])


class InterruptAtJmpCompletion(unittest.TestCase):
    def enable(self, cpu):
        cpu.st["IE"], cpu.ext.int_req_n = 1, 0                          # request held from the start

    def test_interrupt_after_direct_jmp(self):
        cpu = machine({0o200: JMP_300, 0o1: HLT})
        self.enable(cpu)
        records = run(cpu)
        self.assertEqual(states(records)[:3], ["FETCH", "INTERRUPT", "FETCH"])
        self.assertEqual(cpu.memory.read(0, 0), 0o300)                  # return address = JMP target

    def test_interrupt_after_jmp_i(self):
        cpu = machine({0o200: JMP_I_50, 0o50: 0o400, 0o1: HLT})
        self.enable(cpu)
        records = run(cpu)
        self.assertEqual(states(records)[:3], ["FETCH", "DEFER", "INTERRUPT"])
        self.assertEqual(cpu.memory.read(0, 0), 0o400)

    def test_cif_then_jmp_applies_the_field_and_allows_the_interrupt(self):
        # Gap L, KM8-E §2.9: the JMP that applies a pending field change clears II at TP3, so the
        # interrupt is recognized at that JMP's completion and saves the new field in IB.
        cpu = machine({0o200: CIF_2, 0o201: JMP_300, 0o1: HLT}, fields=(0, 2))
        self.enable(cpu)
        records = run(cpu)
        self.assertEqual(states(records)[:4], ["FETCH", "EXECUTE", "FETCH", "INTERRUPT"])
        self.assertEqual(cpu.memory.read(0, 0), 0o300)
        self.assertEqual(cpu.st["IB"] >> 3, 2)                          # saved IF = the new field
        self.assertEqual(cpu.st["IF"], 0)                               # interrupt entry: field 0

    def test_cif_then_jmp_without_interrupt_fetches_from_the_new_field(self):
        cpu = machine({0o200: CIF_2, 0o201: JMP_300, (2, 0o300): NOP, (2, 0o301): HLT}, fields=(0, 2))
        run(cpu)
        self.assertEqual((cpu.st["IF"], cpu.st["PC"]), (2, 0o302))

    def test_cif_then_autoindex_jmp_i_writes_the_pointer_in_the_old_field(self):
        # Fetch & Defer §4.5: JMP I applies the field at DEFER TP4, after the auto-index
        # write-back in DEFER TS4, which addresses the pointer through IF (found by lock-step).
        cpu = machine({0o200: CIF_2, 0o201: JMP_I_10, 0o10: 0o477, (2, 0o500): HLT}, fields=(0, 2))
        cpu.memory.write(2, 0o10, 0o1234)                               # field 2's 0010: untouched
        run(cpu)
        self.assertEqual(cpu.memory.read(0, 0o10), 0o500)               # old field's pointer
        self.assertEqual(cpu.memory.read(2, 0o10), 0o1234)
        self.assertEqual((cpu.st["IF"], cpu.st["PC"]), (2, 0o501))      # HLT in field 2 ran

    def test_ion_then_jmp(self):
        # ION's own completion is inhibited; the JMP after it is the first eligible boundary.
        cpu = machine({0o200: ION, 0o201: JMP_300, 0o1: HLT})
        cpu.ext.int_req_n = 0
        records = run(cpu)
        self.assertEqual(states(records)[:4], ["FETCH", "EXECUTE", "FETCH", "INTERRUPT"])
        self.assertEqual(cpu.memory.read(0, 0), 0o300)


class DmaAtFetchCompletion(unittest.TestCase):
    def test_dma_entered_at_direct_jmp_completion(self):
        cpu = machine({0o200: JMP_300, 0o300: HLT})
        cpu.ext.dma_req_n = 0
        cpu.step_ts(), cpu.step_ts(), cpu.step_ts()
        r = cpu.step_ts()                                               # FETCH TS4 of the JMP
        self.assertEqual((r.ms, r.ts), (E.FETCH, 4))
        self.assertEqual(cpu.st["MS"], E.DMA)
        self.assertEqual(cpu.st["PC"], 0o300)


class HaltsAtJmpCompletion(unittest.TestCase):
    def test_single_instruction_halts_after_direct_jmp_in_fetch(self):
        cpu = machine({0o200: JMP_300})
        cpu.panel.single_instruction = True
        records = run(cpu)
        self.assertEqual(len(records), 4)                               # one FETCH
        self.assertEqual((cpu.st["RUN"], cpu.st["MS"], cpu.st["PC"]), (0, E.FETCH, 0o300))

    def test_single_instruction_halts_after_jmp_i_in_defer(self):
        cpu = machine({0o200: JMP_I_50, 0o50: 0o400})
        cpu.panel.single_instruction = True
        records = run(cpu)
        self.assertEqual(states(records), ["FETCH", "DEFER"])
        self.assertEqual((cpu.st["RUN"], cpu.st["PC"]), (0, 0o400))

    def test_single_step_halts_between_fetch_and_defer_of_jmp_i(self):
        cpu = machine({0o200: JMP_I_50, 0o50: 0o400})
        cpu.panel.single_step = True
        run(cpu)
        self.assertEqual((cpu.st["RUN"], cpu.st["MS"], cpu.st["PC"]), (0, E.DEFER, 0o201))
        cpu.press("CONTINUE")
        run(cpu)
        self.assertEqual((cpu.st["MS"], cpu.st["PC"]), (E.FETCH, 0o400))

    def test_stop_halts_a_jmp_loop_at_its_completion(self):
        cpu = machine({0o200: 0o5200})                                  # JMP .
        for _ in range(12):
            cpu.step_ts()
        cpu.panel.stop = True
        records = run(cpu)
        self.assertEqual((records[-1].ms, records[-1].ts), (E.FETCH, 4))
        self.assertEqual((cpu.st["RUN"], cpu.st["MS"], cpu.st["PC"], cpu.st["HLT_REQ"]),
                         (0, E.FETCH, 0o200, 0))


class Costs(unittest.TestCase):
    def test_major_states(self):
        d = D.select("v2")
        self.assertEqual(D.major_states(d, JMP_300), ("FETCH",))
        self.assertEqual(D.major_states(d, JMP_I_50), ("FETCH", "DEFER"))
        self.assertEqual(D.major_states(d, 0o1450), ("FETCH", "DEFER", "EXECUTE"))  # TAD I
        self.assertEqual(D.major_states(d, HLT), ("FETCH",))               # group 2 OPR (slice C2)
        self.assertEqual(D.major_states(d, 0o7421), ("FETCH",))            # group 3 OPR (slice C3)
        self.assertEqual(D.major_states(d, ION), ("FETCH", "EXECUTE"))     # IOT keeps EXECUTE

    def test_last_state_is_instr_end(self):
        d = D.select("v2")
        self.assertTrue(D.is_last_state(d, "FETCH", JMP_300))
        self.assertFalse(D.is_last_state(d, "FETCH", JMP_I_50))
        self.assertTrue(D.is_last_state(d, "DEFER", JMP_I_50))
        self.assertFalse(D.is_last_state(d, "DEFER", 0o1450))
        self.assertTrue(D.is_last_state(d, "EXECUTE", 0o1450))
        self.assertFalse(D.is_last_state(d, "FETCH", None))


if __name__ == "__main__":
    unittest.main()
