"""Milestone M1: instruction execution, end to end.

Every program is placed with console DEPOSIT and started with START or CONTINUE, so the console
microcode runs too. Expected results are derived by hand from the ISA documentation (docs/02-isa,
"ISA" below) and the interrupt documentation (docs/08-interrupts-and-skip); each test cites the
section it checks. Milestone M2 replaces these hand-derived expectations with the reference model.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pdp8_system.machine import Machine, load_store

HLT, NOP = 0o7402, 0o7000
M12 = 0o7777


def machine(blocks, start=0o200, field=0, data_field=None):
    """A machine with `blocks` {(field, address): [words]} deposited, LOAD ADDRESS done."""
    m = Machine(load_store())
    for (f, a), words in blocks.items():
        m.deposit_block(a, words, instruction_field=f)
    m.load_address(start, instruction_field=field, data_field=field if data_field is None else data_field)
    return m


def run(blocks, **kw):
    m = machine(blocks, **kw)
    m.start()
    m.run(10_000)
    return m


# -- operate instructions, from ISA 01-group-1, 02-group-2, 03-group-3 -----------------------

def group1(ir, ac, link):
    """ISA Group 1 §1: CLA, CLL at 1; CMA, CML at 2; IAC at 3; RAR, RAL, BSW at 4 (notes 1-4)."""
    if ir & 0o200:
        ac = 0
    if ir & 0o100:
        link = 0
    if ir & 0o040:
        ac = ~ac & M12
    if ir & 0o020:
        link ^= 1
    if ir & 0o001:
        s = ac + 1
        ac, link = s & M12, link ^ (s >> 12)
    rar, ral, bsw = ir & 0o010, ir & 0o004, ir & 0o002
    if rar and ral:                       # note 4: no rotate or swap
        return ac, link
    for _ in range((2 if bsw else 1) if (rar or ral) else 0):
        v = (link << 12) | ac
        v = (((v & 1) << 12) | (v >> 1)) if rar else (((v << 1) & 0o17777) | (v >> 12))
        link, ac = v >> 12, v & M12
    if bsw and not (rar or ral):
        ac = ((ac & 0o77) << 6) | (ac >> 6)
    return ac, link


def group2(ir, ac, link, sr):
    """ISA Group 2: skip test at 1 (OR sub-group, or AND sub-group when bit 3 set), CLA at 2,
    OSR and HLT at 3. Returns (AC, skip, halt)."""
    sma, sza, snl, and_mode = ir & 0o100, ir & 0o040, ir & 0o020, ir & 0o010
    neg, zero = ac >> 11, ac == 0
    if and_mode:                          # SPA, SNA, SZL; SKP when none selected (§6)
        skip = (not sma or not neg) and (not sza or not zero) and (not snl or not link)
    else:
        skip = bool((sma and neg) or (sza and zero) or (snl and link))
    if ir & 0o200:
        ac = 0
    if ir & 0o004:
        ac |= sr
    return ac, int(skip), bool(ir & 0o002)


def group3(ir, ac, mq):
    """ISA Group 3 §1-§2: CLA at 1; MQA, MQL, or SWP at 2; EAE bits select nothing."""
    if ir & 0o200:
        ac = 0
    mqa, mql = ir & 0o100, ir & 0o020
    if mqa and mql:
        ac, mq = mq, ac
    elif mqa:
        ac |= mq
    elif mql:
        mq, ac = ac, 0
    return ac, mq


class OperateSweep(unittest.TestCase):
    """Every OPR instruction (7000-7777) from several starting states."""

    STATES = ((0o0000, 0), (0o7777, 1), (0o4000, 0), (0o0001, 1), (0o3456, 0))
    MQ, SR = 0o5252, 0o1234

    def execute(self, ir, ac, link):
        m = machine({(0, 0o200): [ir, HLT, HLT]})
        m.state["AC"], m.state["L"], m.state["MQ"] = ac, link, self.MQ   # test harness state
        m.panel.sr = self.SR
        m.cont()
        m.run(100)
        return m.state

    def test_all_operate_instructions(self):
        for ir in range(0o7000, 0o10000):
            g3, g2 = ir & 0o400 and ir & 1, ir & 0o400
            for ac, link in self.STATES:
                with self.subTest(ir=f"{ir:04o}", ac=f"{ac:04o}", link=link):
                    st = self.execute(ir, ac, link)
                    if g3:
                        eac, emq = group3(ir, ac, self.MQ)
                        self.assertEqual((st["AC"], st["L"], st["MQ"], st["PC"]), (eac, link, emq, 0o202))
                    elif g2:
                        eac, skip, halt = group2(ir, ac, link, self.SR)
                        pc = (0o201 if halt else 0o202) + skip
                        self.assertEqual((st["AC"], st["L"], st["MQ"], st["PC"]), (eac, link, self.MQ, pc))
                    else:
                        eac, elink = group1(ir, ac, link)
                        self.assertEqual((st["AC"], st["L"], st["MQ"], st["PC"]), (eac, elink, self.MQ, 0o202))


# -- memory reference instructions (ISA 00-encoding-model, 05-addressing-model) ---------------

class MemoryReference(unittest.TestCase):
    def test_and_tad_dca(self):
        m = run({(0, 0o200): [0o7300, 0o1250, 0o1251, 0o3252, 0o1253, 0o0254, HLT],
                 (0, 0o250): [0o3777, 0o0001, 0o1111, 0o7070, 0o0770]})
        self.assertEqual(m.memory.read(0, 0o252), 0o4000)          # DCA stores, then clears AC
        self.assertEqual((m.state["AC"], m.state["L"]), (0o0070, 0))

    def test_tad_carry_complements_link(self):
        m = run({(0, 0o200): [0o7300, 0o1210, 0o1211, HLT], (0, 0o210): [0o7777, 0o0002]})
        self.assertEqual((m.state["AC"], m.state["L"]), (0o0001, 1))

    def test_isz(self):
        m = run({(0, 0o200): [0o2210, 0o2211, HLT, HLT], (0, 0o210): [0o0005, 0o7777]})
        self.assertEqual((m.memory.read(0, 0o210), m.memory.read(0, 0o211)), (0o0006, 0))
        self.assertEqual(m.state["PC"], 0o204)                     # second ISZ skipped the first HLT

    def test_jms_and_jmp_indirect_return(self):
        m = run({(0, 0o200): [0o4220, HLT], (0, 0o220): [0, 0o7001, 0o5620]})
        self.assertEqual(m.memory.read(0, 0o220), 0o201)
        self.assertEqual((m.state["PC"], m.state["AC"]), (0o202, 1))

    def test_current_page_uses_the_instructions_page(self):
        # ISA addressing §8: the page is that of the instruction, even at the last word of a page.
        m = run({(0, 0o377): [0o1376], (0, 0o376): [0o0055], (0, 0o576): [0o0077], (0, 0o400): [HLT]},
                start=0o377)
        self.assertEqual(m.state["AC"], 0o0055)

    def test_zero_page(self):
        m = run({(0, 0o4000): [0o1050, HLT], (0, 0o0050): [0o0123], (0, 0o4050): [0o7777]}, start=0o4000)
        self.assertEqual(m.state["AC"], 0o0123)

    def test_indirect(self):
        m = run({(0, 0o200): [0o1620, HLT], (0, 0o220): [0o5000], (0, 0o5000): [0o0321]})
        self.assertEqual(m.state["AC"], 0o0321)

    def test_autoindex(self):
        # ISA addressing §13: the pointer at 0010-0017 is incremented, written back, then used.
        m = run({(0, 0o200): [0o7300, 0o1410, 0o1410, 0o3410, HLT],
                 (0, 0o010): [0o0277], (0, 0o300): [0o0005, 0o0006]})
        self.assertEqual(m.memory.read(0, 0o010), 0o0302)
        self.assertEqual(m.memory.read(0, 0o302), 0o0013)

    def test_autoindex_in_field_1(self):
        m = run({(1, 0o200): [0o1410, HLT], (1, 0o010): [0o0477], (1, 0o500): [0o0033],
                 (0, 0o010): [0o1111]}, field=1)
        self.assertEqual(m.state["AC"], 0o0033)
        self.assertEqual((m.memory.read(1, 0o010), m.memory.read(0, 0o010)), (0o0500, 0o1111))

    def test_pc_wraps_within_the_field(self):
        m = run({(2, 0o7777): [NOP], (2, 0o0000): [HLT]}, start=0o7777, field=2)
        self.assertEqual((m.state["PC"], m.state["IF"]), (0o0001, 2))


# -- memory extension (ISA 04-iot §4, addressing §7) ------------------------------------------

class MemoryExtension(unittest.TestCase):
    def test_cdf_then_indirect_operand_uses_df(self):
        m = run({(0, 0o200): [0o7300, 0o6211, 0o1620, HLT], (0, 0o220): [0o0500], (1, 0o500): [0o0777]})
        self.assertEqual((m.state["DF"], m.state["AC"]), (1, 0o0777))

    def test_dca_indirect_uses_df(self):
        m = run({(0, 0o200): [0o6221, 0o1210, 0o3620, HLT], (0, 0o210): [0o4321], (0, 0o220): [0o0600]})
        self.assertEqual(m.memory.read(2, 0o600), 0o4321)
        self.assertIsNone(m.memory.read(0, 0o600))

    def test_direct_access_ignores_df(self):
        m = run({(0, 0o200): [0o6231, 0o1210, HLT], (0, 0o210): [0o0042], (3, 0o210): [0o0077]})
        self.assertEqual(m.state["AC"], 0o0042)

    def test_cif_jmp(self):
        m = run({(0, 0o200): [0o6212, 0o5300], (1, 0o300): [HLT]})
        self.assertEqual((m.state["IF"], m.state["PC"], m.state["CIFP"]), (1, 0o301, 0))

    def test_cif_jms_indirect_stores_in_new_field(self):
        # ISA addressing §7: the JMS target, including its return-address word, is in the new IF.
        m = run({(0, 0o200): [0o6212, 0o4620, HLT], (0, 0o220): [0o0400], (1, 0o400): [0, 0o7001, HLT]})
        self.assertEqual(m.memory.read(1, 0o400), 0o0202)
        self.assertIsNone(m.memory.read(0, 0o400))
        self.assertEqual((m.state["IF"], m.state["AC"], m.state["PC"]), (1, 1, 0o403))

    def test_jms_indirect_ignores_df(self):
        m = run({(0, 0o200): [0o6221, 0o4620, HLT], (0, 0o220): [0o0400], (0, 0o400): [0, HLT]})
        self.assertEqual(m.memory.read(0, 0o400), 0o0202)
        self.assertIsNone(m.memory.read(2, 0o400))

    def test_cdf_cif_combined(self):
        m = run({(0, 0o200): [0o6233, 0o5300], (3, 0o300): [HLT]})
        self.assertEqual((m.state["DF"], m.state["IF"]), (3, 3))

    def test_rdf_rif(self):
        m = run({(1, 0o200): [0o6231, 0o7300, 0o6214, 0o3250, 0o6224, HLT]}, field=1)
        self.assertEqual(m.memory.read(1, 0o250), 0o0030)       # RDF ORs DF into AC[5:3]
        self.assertEqual(m.state["AC"], 0o0010)                 # RIF


# -- processor IOTs (ISA 04-iot §2-§3) ---------------------------------------------------------

class ProcessorIots(unittest.TestCase):
    def test_skon_skips_and_turns_off(self):
        m = run({(0, 0o200): [0o6001, 0o6000, HLT, HLT]})
        self.assertEqual((m.state["IE"], m.state["PC"]), (0, 0o204))

    def test_skon_with_interrupts_off(self):
        m = run({(0, 0o200): [0o6000, HLT, HLT]})
        self.assertEqual(m.state["PC"], 0o202)

    def test_iof(self):
        m = run({(0, 0o200): [0o6001, 0o6002, HLT]})
        self.assertEqual(m.state["IE"], 0)

    def test_srq(self):
        m = machine({(0, 0o200): [0o6003, HLT, HLT]})
        m.start()
        m.cpu.ext.int_req_n = 0
        m.run(100)
        self.assertEqual(m.state["PC"], 0o203)
        m = run({(0, 0o200): [0o6003, HLT, HLT]})
        self.assertEqual(m.state["PC"], 0o202)

    def test_sgt_never_skips(self):
        m = run({(0, 0o200): [0o6006, HLT, HLT]})
        self.assertEqual(m.state["PC"], 0o202)

    def test_gtf(self):
        # ISA 04-iot §3.1: L in bit 11, interrupt request in 9, IE in 7, IF in 5:3, DF in 2:0.
        m = run({(1, 0o200): [0o7120, 0o6231, 0o6001, 0o6004, HLT]}, field=1)   # STL; CDF 30; ION; GTF
        self.assertEqual(m.state["AC"], 0o4000 | 0o0200 | 0o0010 | 0o0003)

    def test_rtf_restores_and_applies_if_at_jmp(self):
        m = run({(0, 0o200): [0o7300, 0o1210, 0o6005, 0o5611], (0, 0o210): [0o4013, 0o0300],
                 (1, 0o300): [HLT]})
        st = m.state
        self.assertEqual((st["L"], st["DF"], st["IF"], st["IE"], st["PC"]), (1, 3, 1, 1, 0o301))

    def test_caf(self):
        m = run({(0, 0o200): [0o7240, 0o7120, 0o6001, 0o6007, HLT]})       # STA, STL, ION, CAF
        self.assertEqual((m.state["AC"], m.state["L"], m.state["IE"]), (0, 0, 0))

    def test_no_interrupt_at_caf_completion(self):
        # Interrupt Recognition and Sequencing §6: CAF's TP4 never selects INTERRUPT.
        m = machine({(0, 0o200): [0o6001, 0o6007, HLT]})
        m.start()
        m.cpu.ext.int_req_n = 0
        m.run(100)
        self.assertEqual(m.state["PC"], 0o203)
        self.assertIsNone(m.memory.read(0, 0))

    def test_external_iot_without_a_device_is_a_no_op(self):
        m = run({(0, 0o200): [0o7240, 0o6046, 0o6041, HLT, HLT]})          # STA; TLS; TSF
        self.assertEqual((m.state["AC"], m.state["PC"]), (0o7777, 0o204))


# -- interrupts (docs/08-interrupts-and-skip) --------------------------------------------------

def interrupt_machine(blocks, **kw):
    m = machine(blocks, **kw)
    m.start()
    m.cpu.ext.int_req_n = 0
    return m


class Interrupts(unittest.TestCase):
    def test_ion_delays_by_one_instruction(self):
        m = interrupt_machine({(0, 0o200): [0o6001, NOP, NOP, HLT], (0, 0o001): [HLT]})
        m.run(100)
        self.assertEqual(m.memory.read(0, 0), 0o202)                       # NOP at 0201 completed
        self.assertEqual((m.state["PC"], m.state["IE"]), (0o002, 0))

    def test_entry_from_nonzero_fields(self):
        # Interrupt Entry and Return §4-§6: PC to 0:0000, IF and DF to IB, fields cleared.
        m = interrupt_machine({(3, 0o200): [0o6251, 0o6001, NOP, HLT], (0, 0o001): [HLT]}, field=3)
        m.run(100)
        st = m.state
        self.assertEqual(m.memory.read(0, 0), 0o203)
        self.assertIsNone(m.memory.read(3, 0))
        self.assertEqual((st["IB"], st["IF"], st["DF"], st["DIF"], st["PC"]), (0o35, 0, 0, 0, 0o002))

    def test_cif_inhibits_until_after_the_jmp(self):
        # Interrupt Enable and Inhibit §16: recognition waits for the instruction after the JMP.
        m = interrupt_machine({(0, 0o200): [0o6001, 0o6212, 0o5300], (1, 0o300): [NOP, HLT],
                               (0, 0o001): [HLT]})
        m.run(100)
        self.assertEqual(m.memory.read(0, 0), 0o301)                       # after NOP at 1:0300
        self.assertEqual(m.state["IB"], 0o10)

    def test_rmf_and_return(self):
        # Interrupt Entry and Return §8: RMF restores DF now and IF at JMP I 0.
        isr = [0o6234, 0o3020, 0o6244, 0o5400]                             # RIB; DCA 20; RMF; JMP I 0
        m = machine({(1, 0o200): [0o6221, 0o6001, NOP, 0o7001, HLT], (0, 0o001): isr}, field=1)
        m.start()
        m.cpu.ext.int_req_n = 0
        while m.state["IE"] != 0 or m.state["MS"] != 0 or m.state["PC"] != 0o001:
            m.cpu.step_ts()
        m.cpu.ext.int_req_n = 1                                            # the ISR services the device
        m.run(200)
        st = m.state
        self.assertEqual(m.memory.read(0, 0o020), 0o12)                    # RIB: IF 1, DF 2
        self.assertEqual((st["IF"], st["DF"], st["AC"], st["PC"]), (1, 2, 1, 0o205))


# -- run control (docs/03-microarchitecture/09-console-execution.md §12-§13) -------------------

class RunControl(unittest.TestCase):
    def test_continue_after_hlt(self):
        m = run({(0, 0o200): [HLT, 0o7001, HLT]})
        self.assertEqual(m.state["PC"], 0o201)
        m.cont()
        m.run(100)
        self.assertEqual((m.state["PC"], m.state["AC"]), (0o203, 1))

    def test_single_step_through_defer(self):
        m = machine({(0, 0o200): [0o1620, HLT], (0, 0o220): [0o0300], (0, 0o300): [0o0042]})
        m.panel.single_step = True
        m.start()
        states = []
        for _ in range(3):
            m.run(100)
            states.append(m.state["MS"])
            m.cont()
        self.assertEqual(states, [1, 2, 0])                                 # after FETCH, DEFER, EXECUTE
        self.assertEqual(m.state["AC"], 0o0042)

    def test_single_instruction(self):
        m = machine({(0, 0o200): [0o1620, 0o7001, HLT], (0, 0o220): [0o0300], (0, 0o300): [0o0042]})
        m.panel.single_instruction = True
        m.start()
        m.run(100)
        self.assertEqual((m.state["PC"], m.state["AC"], m.state["MS"]), (0o201, 0o0042, 0))
        m.cont()
        m.run(100)
        self.assertEqual((m.state["PC"], m.state["AC"]), (0o202, 0o0043))

    def test_stop_halts_at_instruction_end(self):
        m = machine({(0, 0o200): [0o5200]})                                # JMP .
        m.start()
        for _ in range(10):
            m.cpu.step_ts()
        m.panel.stop = True
        m.run(100)
        self.assertEqual((m.state["MS"], m.state.ts, m.state["PC"]), (0, 1, 0o200))


if __name__ == "__main__":
    unittest.main()
