"""External IOT write with AC clear at the same TP, run on the packed v2 images.

- docs/09-timing/03-major-state-timing.md §5.2.5: a clear in TS3 is excluded only by a pending read
- docs/07-io/02-external-iot-interface.md §6: the device captures the pre-TP AC and AC clears
- docs/07-io/10-controllers/03-rk8e-storage.md §23.4: DMAN, whose responses do not depend on DB

The controllers here see only what the contract allows a response to use: selection, the TS, and
state they registered at an earlier TP.
"""

import unittest
from types import SimpleNamespace

import _paths  # noqa: F401
from pdp8_cpu import design as D
from pdp8_cpu.cpu import Cpu
from pdp8_cpu.images import ControlStore
from pdp8_memory import Memory

DEVICE, IOT = 0o70, 0o6707
READ_FUNCTION, BUFFER = 0o0020, 0o0055      # DMAN AC[4], and a lower-data-buffer value
ONE_BIT_VALUES = [0, 0o7777, 0o1234] + [1 << bit for bit in range(12)]

_STORE = None


def store():
    global _STORE
    if _STORE is None:
        _STORE = ControlStore.load(design=D.select("v2"))
    return _STORE


class Controller:
    """Requests a write in TS2 and an AC clear in TS3. With `read`, it also requests a read in TS3
    and answers in TS4 from the function it registered at TP3, as DMAN does."""

    def __init__(self, read):
        self.read, self.function, self.captured = read, None, []

    def selects(self, device):
        return device == DEVICE

    def present(self, bus):
        r = SimpleNamespace(io_read_req=0, io_write_req=0, io_skip_req=0, io_clear_ac_req=0,
                            db=None, int_req=False)
        if not bus.iot_active or bus.ioa != DEVICE or bus.console:
            return r
        if bus.ts == 2:
            r.io_write_req = 1
        elif bus.ts == 3:
            r.io_clear_ac_req = 1
            r.io_read_req = int(self.read)
        elif bus.ts == 4 and self.read:
            r.db = BUFFER if self.function == READ_FUNCTION else 0
        return r

    def commit(self, bus, tp, db_write, initialize):
        if db_write is not None and bus.iot_active:
            self.function = db_write
            self.captured.append((tp, db_write))

    def at_boundary(self, now_ns=0):
        pass

    def interrupt_request(self):
        return False

    def initialize(self):
        pass

    def state(self):
        return {}


def execute(ac, link, read):
    device = Controller(read)
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


class WriteWithClear(unittest.TestCase):
    def check(self, read, expected_ac):
        for ac in ONE_BIT_VALUES:
            for link in (0, 1):
                with self.subTest(ac=oct(ac), link=link):
                    self.assertEqual(execute(ac, link, read),
                                     (expected_ac(ac), link, 0o201, [(3, ac)]))

    def test_write_and_clear_commit_at_tp3(self):
        self.check(False, lambda ac: 0)

    def test_dman_answers_from_the_function_registered_at_tp3(self):
        self.check(True, lambda ac: BUFFER if ac == READ_FUNCTION else 0)


if __name__ == "__main__":
    unittest.main()
