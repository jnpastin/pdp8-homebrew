"""Derived architectural outputs and their cross-checks.

- `/DMA_GRANT` and `IOT_ACTIVE` are decoded from MS_EFF (CSO §5.1, ACS §4.5 and §4.8).
- The direct-control definitions state them per context
  (docs/04-control/30-direct-control-definitions/02-interface-and-ownership-control.md, DCI §5.2,
  §5.3, §7.2, §7.3). The simulator evaluates those definitions exactly as written and requires
  them to agree with the decode in every context it reaches.
- `/INITIALIZE`'s assertion condition is ACS §4.9; the sequencer slice produces the signal.
- `/DB_READ`, `/DB_WRITE`, and the gate on `/RD` and the CPU's MDB drive are realized outside
  the control store (ACS §3.2). The simulator decodes the DB strobes from IOT_TRANSFER. It
  applies the rest of the control word as it stands, so it requires the word to give the same
  values as the gate in every TS it reaches. v1 has /DB_READ and /DB_WRITE fields, which must
  agree with the decode.
"""

from __future__ import annotations

from . import encodings as E
from .errors import SpecGap, SpecViolation
from .logic import t_and, t_not


def dma_grant_n(mseff) -> int:
    """CSO §5.1: /DMA_GRANT = NOT (MS_EFF = DMA)."""
    return int(mseff != E.DMA)


def iot_active(is_execute, ir_is_external_iot):
    """CSO §5.1: IOT_ACTIVE = MS_EFF_IS_EXECUTE AND IR_IS_EXTERNAL_IOT."""
    return t_and(is_execute, ir_is_external_iot)


def dma_grant_n_direct_control(run, ms):
    """DCI §5.2 (RUN = 1 AND MS = DMA -> 0) and §5.3 (NOT (RUN = 1 AND MS = DMA) -> 1), as written.

    Both definitions are evaluated independently, so an overlap or a hole between them is
    reported rather than resolved."""
    values = set()
    if run == 1 and ms == E.DMA:
        values.add(0)
    if not (run == 1 and ms == E.DMA):
        values.add(1)
    if len(values) != 1:
        raise SpecGap(f"direct-control definitions give /DMA_GRANT = {sorted(values)}",
                      "DCI §5.2 and §5.3 both apply", {"RUN": run, "MS": E.MS_NAMES.get(ms, ms)})
    return values.pop()


def iot_active_direct_control(run, ms, ir_is_external_iot):
    """DCI §7.2 (RUN = 1 AND MS = EXECUTE AND IR_IS_EXTERNAL_IOT = 1 -> 1) and §7.3 (otherwise -> 0)."""
    return t_and(int(run == 1), int(ms == E.EXECUTE), ir_is_external_iot)


def check_derived(run, ms, mseff, is_execute, ir_is_external_iot):
    """Assert the decoded outputs match the direct-control definitions; return them."""
    grant = dma_grant_n(mseff)
    active = iot_active(is_execute, ir_is_external_iot)
    context = {"RUN": run, "MS": E.MS_NAMES.get(ms, ms), "IR_IS_EXTERNAL_IOT": ir_is_external_iot}
    dc_grant = dma_grant_n_direct_control(run, ms)
    if dc_grant != grant:
        raise SpecGap(f"/DMA_GRANT decoded {grant}, direct-control definition gives {dc_grant}",
                      "CSO §5.1 vs DCI §5.2/§5.3", context)
    dc_active = iot_active_direct_control(run, ms, ir_is_external_iot)
    if dc_active != active:
        raise SpecGap(f"IOT_ACTIVE decoded {active}, direct-control definition gives {dc_active}",
                      "CSO §5.1 vs DCI §7.2/§7.3", context)
    return grant, active


def initialize_asserted(ir_is_caf, ms, ts, run, fp_clear, fp_start=0):
    """ACS §4.9: (IR_IS_CAF AND MS = EXECUTE AND TS = 4) OR (RUN = 0 AND (FP_CLEAR OR FP_START))."""
    caf = t_and(ir_is_caf, int(ms == E.EXECUTE), int(ts == 4))
    command = 1 if 1 in (fp_clear, fp_start) else (None if None in (fp_clear, fp_start) else 0)
    clear = t_and(int(run == 0), command)
    return 1 if caf == 1 or clear == 1 else (None if None in (caf, clear) else 0)


def check_db_strobes(db_read_n, db_write_n, iot_transfer):
    """V1-ONLY. ACS §3.2: the DB strobes are decoded from IOT_TRANSFER (READ, WRITE), within
    DB_VALID; v1's control word also has /DB_READ and /DB_WRITE fields, which must agree."""
    if iot_transfer is None:
        return
    expected = (int(iot_transfer != E.IOT_READ), int(iot_transfer != E.IOT_WRITE))
    if (db_read_n, db_write_n) != expected:
        raise SpecViolation(f"control word /DB_READ = {db_read_n}, /DB_WRITE = {db_write_n}; the "
                            f"decode of IOT_TRANSFER = {iot_transfer} gives {expected[0]}, {expected[1]}",
                            "ACS §3.2")


def check_iot_gate(is_execute, ir_is_iot, rd_asserted, cpu_drives_mdb):
    """ACS §3.2: /RD and the CPU's MDB drive are gated off by MS_EFF_IS_EXECUTE AND IR_IS_IOT. The
    simulator applies the control word ungated, so the word must assert neither there."""
    if t_and(is_execute, ir_is_iot) == 1 and (rd_asserted or cpu_drives_mdb):
        raise SpecViolation(f"control word asserts {'/RD' if rd_asserted else 'the MDB drive'} in an "
                            f"IOT's EXECUTE, where the gate holds it off", "ACS §3.2")


def check_initialize(seq_initialize_n, expected):
    """The sequencer's /INITIALIZE (active low) must match the ACS §4.9 condition."""
    if expected is None:
        return
    if seq_initialize_n != t_not(expected):
        raise SpecViolation(f"sequencer /INITIALIZE = {seq_initialize_n}, ACS §4.9 requires "
                            f"{t_not(expected)}", "ACS §4.9")
