"""Control-store address formation, coded from docs/04-control/08-control-store-organization.md (CSO).

These functions form every address as the hardware does. They deliberately do not import the
control-store packer; the packer's address functions serve only as a cross-check in the tests.

An address input that is UNDEFINED (None) is reported as an undefined address bit. The caller
evaluates every combination and requires the resulting behavior to agree, which is the
hardware-level meaning of "no control word depends on that input here".
"""

from __future__ import annotations

from . import encodings as E
from .errors import SpecViolation
from .logic import bit


def ms_eff(ms, run):
    """CSO §5.1: MS_EFF = HALTED (7) if RUN = 0, else MS."""
    if run is None or ms is None:
        raise SpecViolation("MS_EFF formed from an undefined MS or RUN", "CSO §5.1")
    return E.HALTED if run == 0 else ms


def ms_eff_is_execute(mseff) -> int:
    """CSO §5.1: MS_EFF compared with the EXECUTE code."""
    return int(mseff == E.EXECUTE)


def ts_code(ts) -> int:
    """CSO §5.1: TS_CODE[1:0] = TS - 1, TS_CODE[0] = TS2 OR TS4, TS_CODE[1] = TS3 OR TS4."""
    if ts not in (1, 2, 3, 4):
        raise SpecViolation(f"invalid timing state {ts}", "Timing Terminology §5")
    b0 = int(ts in (2, 4))
    b1 = int(ts in (3, 4))
    return (b1 << 1) | b0


def mapping_address(ir, ts):
    """CSO §5.3: A14..A3 = IR, A2..A1 = TS_CODE, A0 = 0. None if IR is undefined."""
    if ir is None:
        return None
    return (ir << 3) | (ts_code(ts) << 1)


def mapr_fields(mapr):
    """CSO §5.4.1: MAPR[4:0] variant, MAPR[6:5] overlay group, MAPR[7] sequencer decode."""
    if mapr is None:
        return None, None, None
    o, w = E.MAPR_FIELDS["VARIANT"]
    variant = (mapr >> o) & ((1 << w) - 1)
    o, w = E.MAPR_FIELDS["DP_OVL_SEL"]
    sel = (mapr >> o) & ((1 << w) - 1)
    o, w = E.MAPR_FIELDS["IR_SEQ"]
    ir_seq = (mapr >> o) & ((1 << w) - 1)
    return variant, sel, ir_seq


def execute_selection(is_execute, mapr, ir_indirect):
    """CSO §5.4.2: VARIANT, DP_OVL_SEL, IR_SEQ from MAPR in EXECUTE; 0, 1, IR_INDIRECT otherwise."""
    if is_execute:
        variant, sel, ir_seq = mapr_fields(mapr)
        if variant is None:
            raise SpecViolation("MAPR is undefined in EXECUTE", "CSO §5.4.3")
        return variant, sel, ir_seq
    return 0, 1, ir_indirect


def overlay_bits(group_bits, value_of):
    """CSO §6: DP_OVL[4:0] for one overlay group; value_of(signal) gives each signal's value.

    group_bits: [(bit, signal, width)] from the packing description."""
    out = [0] * 5
    for position, signal, width in group_bits:
        value = value_of(signal)
        for k in range(width):
            out[position + k] = None if value is None else (value >> k) & 1
    return out


def seq_ovl_bits(run, fp_cmd, single_instruction, single_step, interrupt_request_valid):
    """CSO §5.6: SEQ_OVL[2:0] = FP_CMD while halted, (SI, SS, INTERRUPT_REQUEST_VALID) while running."""
    if run == 0:
        return [bit(fp_cmd, 0), bit(fp_cmd, 1), bit(fp_cmd, 2)]
    return [interrupt_request_valid, single_step, single_instruction]


def _assemble(fields):
    """fields: [(lsb_position, value_or_None)] of single bits -> (address, undefined positions)."""
    address, undefined = 0, []
    for position, value in fields:
        if value is None:
            undefined.append(position)
        elif value:
            address |= 1 << position
    return address, undefined


def datapath_address(mseff, tscode, variant, ovl):
    """CSO §5.5: A14..A12 MS_EFF, A11..A10 TS_CODE, A9..A5 VARIANT, A4..A0 DP_OVL."""
    fields = [(12 + k, (mseff >> k) & 1) for k in range(3)]
    fields += [(10 + k, (tscode >> k) & 1) for k in range(2)]
    fields += [(5 + k, (variant >> k) & 1) for k in range(5)]
    fields += [(k, ovl[k]) for k in range(5)]
    return _assemble(fields)


def sequencer_address(mseff, tscode, hlt_req, fp_stop, seq_ovl, dma_req_n, ir_seq):
    """CSO §5.6: A14..A12 MS_EFF, A11..A10 TS_CODE, A9 HLT_REQ, A8 FP_STOP, A7..A5 SEQ_OVL,
    A4 /DMA_REQ, A3 IR_SEQ, A2..A0 = 0."""
    fields = [(12 + k, (mseff >> k) & 1) for k in range(3)]
    fields += [(10 + k, (tscode >> k) & 1) for k in range(2)]
    fields += [(9, hlt_req), (8, fp_stop)]
    fields += [(5 + k, seq_ovl[k]) for k in range(3)]
    fields += [(4, dma_req_n), (3, ir_seq)]
    return _assemble(fields)


def expand(address, undefined):
    """Every address obtained by giving the undefined bit positions each combination of values."""
    out = []
    for combo in range(1 << len(undefined)):
        a = address
        for k, position in enumerate(undefined):
            if (combo >> k) & 1:
                a |= 1 << position
        out.append(a)
    return out
