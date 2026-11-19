"""The DMA arbiter and the DMA test master on their own, with no CPU.

Each test checks a rule of docs/07-io/06-dma-arbitration.md (ARB §n) or 05-dma-interface.md
(DMA §n). `dma_state()` plays CPU control through one DMA major state: it commits TP1-TP4 with the
DMA context, performing the selected controller's transfer at TP2 as the CPU's memory interface
would, and returns the aggregate /DMA_REQ sampled during TS4.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_io.dma import NO_CONTROLLER, DmaArbiter, DmaTestMaster


def write(a, v=0):
    return ("write", 0, a, v)


def dma_state(arb, memory=None):
    """One DMA major state. Returns aggregate /DMA_REQ as sampled during TS4."""
    memory = {} if memory is None else memory
    arb.commit(1, False, True, False)
    op = arb.operation()
    value = None
    if op is not None:
        if op[0] == "read":
            value = memory.get((op[1], op[2]))
        else:
            memory[(op[1], op[2])] = value = op[3]
    arb.commit(2, False, True, False, value)
    arb.commit(3, False, True, False)
    request_n = arb.aggregate_n(False, True, 4)
    arb.commit(4, False, True, False)
    return request_n


def execute_tp4(arb):
    """The EXECUTE TP4 that ends an instruction. Returns aggregate /DMA_REQ sampled in TS4."""
    request_n = arb.aggregate_n(True, False, 4)
    arb.commit(4, True, False, False)
    return request_n


class Enable(unittest.TestCase):
    def test_dma_enable_by_context(self):
        # ARB §5: 1 in EXECUTE TS4, the retained burst-enabled state in DMA, otherwise 0.
        arb = DmaArbiter()
        self.assertTrue(arb.dma_enable(True, False, 4))
        for ts in (1, 2, 3):
            self.assertFalse(arb.dma_enable(True, False, ts))
        self.assertFalse(arb.dma_enable(False, False, 4))            # FETCH, DEFER, INTERRUPT
        self.assertFalse(arb.dma_enable(False, True, 4))             # initialized: not enabled
        execute_tp4(arb)
        self.assertTrue(arb.dma_enable(False, True, 4))              # ARB §4: set at EXECUTE TP4

    def test_aggregate_request(self):
        # ARB §7: /DMA_REQ = NOT (DMA_ENABLE AND any request); requests may stay asserted
        # while the aggregate is deasserted.
        m = DmaTestMaster(3)
        arb = DmaArbiter([m])
        self.assertEqual(arb.aggregate_n(True, False, 4), 1)
        m.load([write(0o100)])
        self.assertEqual((arb.aggregate_n(True, False, 4), arb.aggregate_n(True, False, 3)), (0, 1))


class Selection(unittest.TestCase):
    def test_lowest_number_wins_and_grant_id_is_15_when_none(self):
        # ARB §8, §9.
        low, high = DmaTestMaster(7), DmaTestMaster(2)
        arb = DmaArbiter([low, high])
        self.assertEqual(arb.grant_id, NO_CONTROLLER)
        low.load([write(1)])
        high.load([write(2)])
        execute_tp4(arb)
        arb.commit(1, False, True, False)
        self.assertEqual(arb.grant_id, 2)

    def test_no_request_no_transfer(self):
        # DMX §5: a DMA major state with no request transfers nothing and returns to FETCH.
        arb = DmaArbiter([DmaTestMaster(1)])
        execute_tp4(arb)
        memory = {}
        self.assertEqual(dma_state(arb, memory), 1)
        self.assertEqual((memory, arb.grant_id), ({}, NO_CONTROLLER))

    def test_non_preemptive(self):
        # ARB §9: a higher-priority request arriving during a burst waits for the burst to end.
        low, high = DmaTestMaster(9), DmaTestMaster(1)
        arb = DmaArbiter([low, high], burst_limits={9: 3})
        low.load([write(a) for a in range(5)])
        execute_tp4(arb)
        dma_state(arb)
        high.load([write(0o500)])
        self.assertEqual(dma_state(arb), 0)
        self.assertEqual(arb.grant_id, 9)
        self.assertEqual(dma_state(arb), 1)                         # the limit ends the burst
        self.assertEqual(arb.grant_id, NO_CONTROLLER)
        execute_tp4(arb)
        arb.commit(1, False, True, False)
        self.assertEqual(arb.grant_id, 1)                           # priority reevaluated


class Bursts(unittest.TestCase):
    def test_burst_limit_then_fairness(self):
        # ARB §11, §12: the limit ends the burst at TP3 and the aggregate is deasserted in TS4,
        # though the controller still requests; one instruction later it is served again.
        m = DmaTestMaster(4)
        arb = DmaArbiter([m], burst_limits={4: 2})
        m.load([write(a) for a in range(3)])
        memory = {}
        execute_tp4(arb)
        self.assertEqual([dma_state(arb, memory), dma_state(arb, memory)], [0, 1])
        self.assertTrue(m.dma_request())
        self.assertEqual(execute_tp4(arb), 0)
        self.assertEqual(dma_state(arb, memory), 1)                 # the controller has finished
        self.assertEqual(sorted(memory), [(0, 0), (0, 1), (0, 2)])

    def test_a_finished_controller_ends_the_burst(self):
        # ARB §11: the burst terminates when the selected controller deasserts its request.
        m = DmaTestMaster(4)
        arb = DmaArbiter([m], burst_limits={4: 10})
        m.load([write(1)])
        execute_tp4(arb)
        self.assertEqual(dma_state(arb), 1)
        self.assertEqual((arb.grant_id, arb.burst_count), (NO_CONTROLLER, 0))

    def test_reads_capture_the_memory_word(self):
        # DMA §5.1: for a read, the controller captures MDB at TP2.
        m = DmaTestMaster(0)
        arb = DmaArbiter([m])
        m.load([("read", 3, 0o1234)])
        execute_tp4(arb)
        dma_state(arb, {(3, 0o1234): 0o5252})
        self.assertEqual(m.read_values, [0o5252])


class Initialization(unittest.TestCase):
    def test_initialize(self):
        # ARB §13.2: DMA_GRANT_ID 15, burst-enabled state and count cleared; controllers deassert.
        m = DmaTestMaster(2)
        arb = DmaArbiter([m], burst_limits={2: 5})
        m.load([write(a) for a in range(4)])
        execute_tp4(arb)
        dma_state(arb)
        arb.commit(4, True, False, True)                            # CAF's EXECUTE TP4
        m.commit(None, 4, None, True)
        self.assertEqual(arb.state(), {"grant_id": NO_CONTROLLER, "burst_enabled": False, "burst_count": 0})
        self.assertFalse(m.dma_request())

    def test_invalid_configurations(self):
        # ARB §6: distinct priorities 0-14; ARB §11.1: a burst limit of zero is invalid.
        for make in (lambda: DmaArbiter([DmaTestMaster(3), DmaTestMaster(3)]),
                     lambda: DmaArbiter([DmaTestMaster(15)]),
                     lambda: DmaArbiter([DmaTestMaster(1)], burst_limits={1: 0})):
            with self.assertRaises(ValueError):
                make()


class TestMasterContract(unittest.TestCase):
    def test_request_deasserts_after_the_last_transfer(self):
        # DMA §7, ARB §11: after the TP2 transfer of its last word, the request deasserts
        # before the TP3 update.
        m = DmaTestMaster(0)
        m.load([write(1)])
        self.assertTrue(m.dma_request())
        m.dma_transferred(None)
        self.assertFalse(m.dma_request())
        m.dma_advance()
        self.assertEqual((m.queue, m.dma_request()), ([], False))

    def test_schedule_loads_at_a_boundary(self):
        m = DmaTestMaster(0, schedule={2: [write(7)]})
        m.at_boundary()
        self.assertFalse(m.dma_request())
        m.at_boundary()
        self.assertTrue(m.dma_request())


if __name__ == "__main__":
    unittest.main()
