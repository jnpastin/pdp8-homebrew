"""Console transactions executed through the console microcode (docs/03-microarchitecture/09-console-execution.md)."""

import unittest

import _paths  # noqa: F401
from pdp8_cpu import encodings as E
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory

_STORE = None


def new_cpu():
    global _STORE
    if _STORE is None:
        _STORE = ControlStore.load()
    records = []
    cpu = Cpu(_STORE, Memory(), trace=records.append)
    cpu.power_on()
    return cpu, records


def load_address(cpu, address, fp_if=0, fp_df=0):
    cpu.panel.sr, cpu.panel.fp_if, cpu.panel.fp_df = address, fp_if, fp_df
    cpu.press("LOAD_ADDRESS")


class PowerOnTests(unittest.TestCase):
    def test_power_on_state(self):
        # Timing Terminology §3.4
        cpu, _ = new_cpu()
        st = cpu.st
        self.assertEqual((st["RUN"], st["MS"], st["HLT_REQ"], st["IOT_TRANSFER"], st.ts),
                         (0, E.FETCH, 0, E.IOT_NONE, 1))
        self.assertEqual((st["AC"], st["L"], st["IE"]), (0, 0, 0))
        for name in ("PC", "IF", "DF", "MQ", "MAPR", "IR", "CIFP", "II"):
            self.assertIsNone(st[name], name)

    def test_undefined_address_inputs_are_enumerated(self):
        # While halted after power-on, the state overlay group carries CIFP and AUTO_INDEX_REQUIRED,
        # both undefined; every combination must give the same effect (CSO §5.7, §9).
        cpu, rec = new_cpu()
        load_address(cpu, 0o200)
        self.assertEqual(len(rec[-1].dp_addresses), 4)
        self.assertEqual(cpu.st["CIFP"], 0)          # defined from here on
        load_address(cpu, 0o200)
        self.assertEqual(len(rec[-1].dp_addresses), 2)  # AUTO_INDEX_REQUIRED still depends on IR


class ConsoleTests(unittest.TestCase):
    def test_load_address(self):
        # §6: CIFP <- 0, DF <- FP_DF, DIF <- FP_IF, IF <- FP_IF, PC <- FP_SR; no memory access
        cpu, rec = new_cpu()
        load_address(cpu, 0o1234, fp_if=5, fp_df=3)
        st = cpu.st
        self.assertEqual((st["PC"], st["IF"], st["DIF"], st["DF"], st["CIFP"]), (0o1234, 5, 5, 3, 0))
        self.assertEqual(st["RUN"], 0)
        self.assertEqual((rec[-1].kind, rec[-1].mem_read, rec[-1].mem_write), ("TPC", None, None))

    def test_deposit(self):
        # §8: MA, EA_ADDR <- PC; MB <- FP_SR; M[IF:PC] <- FP_SR; PC <- PC + 1
        cpu, _ = new_cpu()
        load_address(cpu, 0o7776, fp_if=2)
        cpu.panel.sr = 0o5252
        cpu.press("DEPOSIT")
        st = cpu.st
        self.assertEqual(cpu.memory.read(2, 0o7776), 0o5252)
        self.assertEqual((st["MA"], st["EA_ADDR"], st["MB"], st["PC"]), (0o7776, 0o7776, 0o5252, 0o7777))
        cpu.press("DEPOSIT")
        self.assertEqual(st["PC"], 0)                       # PC wraps within the field

    def test_examine(self):
        # §7: MA, EA_ADDR <- PC; MB <- M[IF:PC]; PC <- PC + 1
        cpu, _ = new_cpu()
        cpu.memory.preload(1, 0o0400, [0o1357])
        load_address(cpu, 0o0400, fp_if=1)
        cpu.press("EXAMINE")
        st = cpu.st
        self.assertEqual((st["MB"], st["MA"], st["EA_ADDR"], st["PC"]), (0o1357, 0o400, 0o400, 0o401))

    def test_clear(self):
        # §9 and ACS §4.9: AC, L, IE cleared by the CLEAR word's micro-operations; /INITIALIZE asserted;
        # II, CIFP, DIF, IF, DF, IB unchanged
        cpu, rec = new_cpu()
        load_address(cpu, 0o200, fp_if=4, fp_df=6)
        st = cpu.st
        st["AC"], st["L"], st["IE"], st["II"], st["IB"] = 0o7777, 1, 1, 1, 0o46
        cpu.press("CLEAR")
        self.assertEqual((st["AC"], st["L"], st["IE"]), (0, 0, 0))
        self.assertEqual((st["II"], st["CIFP"], st["DIF"], st["IF"], st["DF"], st["IB"]), (1, 0, 4, 4, 6, 0o46))
        self.assertEqual(rec[-1].sequencer["/INITIALIZE"], 0)
        self.assertEqual(st["RUN"], 0)

    def test_start(self):
        # §10: AC, L, MQ, IE, II cleared; RUN <- 1; FETCH at TS1
        cpu, _ = new_cpu()
        load_address(cpu, 0o200)
        st = cpu.st
        st["AC"], st["MQ"], st["L"] = 0o1111, 0o2222, 1
        cpu.press("START")
        self.assertEqual((st["AC"], st["L"], st["MQ"], st["IE"], st["II"]), (0, 0, 0, 0, 0))
        self.assertEqual((st["RUN"], st["MS"], st.ts, st["PC"]), (1, E.FETCH, 1, 0o200))

    def test_continue_keeps_state(self):
        # §11: RUN <- 1; PC, AC, L, MQ, IF, DF, MA, EA_ADDR, MS, TS unchanged
        cpu, _ = new_cpu()
        load_address(cpu, 0o300)
        st = cpu.st
        st["AC"], st["MQ"] = 0o4444, 0o3333
        before = st.snapshot()
        cpu.press("CONTINUE")
        after = st.snapshot()
        self.assertEqual(after["RUN"], 1)
        for name in ("PC", "AC", "L", "MQ", "IF", "DF", "MA", "EA_ADDR", "MS", "TS"):
            self.assertEqual(after[name], before[name], name)

    def test_commands_ignored_while_running(self):
        # EXT §4.1: accepted only while RUN = 0
        cpu, _ = new_cpu()
        load_address(cpu, 0o200)
        cpu.press("START")
        self.assertFalse(cpu.press("DEPOSIT"))
        self.assertFalse(cpu.press("LOAD_ADDRESS"))


class SmokeTests(unittest.TestCase):
    def test_hlt_program(self):
        # Deposit HLT at 0200, start there: FETCH, EXECUTE, halt at EXECUTE TP4 with PC = 0201.
        cpu, rec = new_cpu()
        load_address(cpu, 0o200)
        cpu.panel.sr = 0o7402
        cpu.press("DEPOSIT")
        load_address(cpu, 0o200)
        cpu.press("START")
        n = 0
        while cpu.running and n < 100:
            cpu.step_ts()
            n += 1
        st = cpu.st
        self.assertEqual(n, 8)
        self.assertEqual((st["RUN"], st["PC"], st["IR"], st["MS"], st.ts, st["HLT_REQ"]),
                         (0, 0o201, 0o7402, E.FETCH, 1, 0))
        self.assertEqual([(r.ms, r.ts) for r in rec if r.kind == "TS"],
                         [(E.FETCH, t) for t in (1, 2, 3, 4)] + [(E.EXECUTE, t) for t in (1, 2, 3, 4)])


if __name__ == "__main__":
    unittest.main()
