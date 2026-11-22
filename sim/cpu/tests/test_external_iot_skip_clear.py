"""External IOT skip with AC clear at the same TP, run on the packed v2 images (review item D2).

- docs/07-io/02-external-iot-interface.md §7: skip and clear, and skip, write, and clear, are valid
- docs/09-timing/03-major-state-timing.md §5.2.7: a clear in TS4 is excluded only by a pending read
- MCS AC_SRC: AC_CLEAR loads the hardwired ZERO, so the ALU is free for PC_INC

The controller sees only what the contract allows a response to use: selection and the TS.
"""

import unittest
from types import SimpleNamespace

import _paths  # noqa: F401
from pdp8_cpu import design as D
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory

DEVICE, IOT = 0o70, 0o6707
VALUES = [0, 0o7777, 0o1234] + [1 << bit for bit in range(12)]

_STORE = None


def store():
    global _STORE
    if _STORE is None:
        _STORE = ControlStore.load(design=D.select("v2"))
    return _STORE


class Controller:
    """Requests a skip and an AC clear in TS4, with `write` also a write in TS3 (transfer in TS4)."""

    def __init__(self, skip, clear, write):
        self.skip, self.clear, self.write, self.captured = skip, clear, write, []

    def selects(self, device):
        return device == DEVICE

    def present(self, bus):
        r = SimpleNamespace(io_read_req=0, io_write_req=0, io_skip_req=0, io_clear_ac_req=0,
                            db=None, int_req=False)
        if not bus.iot_active or bus.ioa != DEVICE or bus.console:
            return r
        if bus.ts == 3:
            r.io_write_req = int(self.write)
        elif bus.ts == 4:
            r.io_skip_req, r.io_clear_ac_req = int(self.skip), int(self.clear)
        return r

    def commit(self, bus, tp, db_write, initialize):
        if db_write is not None and bus.iot_active:
            self.captured.append((tp, db_write))

    def at_boundary(self, now_ns=0):
        pass

    def interrupt_request(self):
        return False

    def initialize(self):
        pass

    def state(self):
        return {}


def execute(ac, link, skip, clear, write):
    device = Controller(skip, clear, write)
    cpu = Cpu(store(), Memory(), devices=[device])
    cpu.power_on()
    cpu.memory.write(0, 0o200, IOT)
    cpu.panel.sr = 0o200
    cpu.press("LOAD_ADDRESS")
    cpu.press("START")
    cpu.st["AC"], cpu.st["L"] = ac, link
    for _ in range(8):      # FETCH and EXECUTE
        cpu.step_ts()
    return cpu.st["AC"], cpu.st["L"], cpu.st["PC"], device.captured


class SkipWithClear(unittest.TestCase):
    def check(self, skip, clear, write):
        for ac in VALUES:
            for link in (0, 1):
                with self.subTest(ac=oct(ac), link=link):
                    self.assertEqual(execute(ac, link, skip, clear, write),
                                     (0 if clear else ac, link, 0o202 if skip else 0o201,
                                      [(4, ac)] if write else []))

    def test_skip_alone(self):
        self.check(True, False, False)

    def test_skip_and_clear_commit_at_tp4(self):
        self.check(True, True, False)

    def test_skip_write_and_clear_commit_at_tp4(self):
        self.check(True, True, True)


if __name__ == "__main__":
    unittest.main()
