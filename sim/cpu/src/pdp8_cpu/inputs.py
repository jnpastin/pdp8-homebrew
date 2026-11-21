"""Control inputs: IR decodes, primitive flags, derived flags, and external inputs.

Definitions (docs/04-control/10-control-input-definitions/):

- IRD = 02-ir-derived-fields.md
- FLG = 01-flags.md
- DRV = 03-derived-flags.md
- EXT = 04-external-inputs.md

Bit numbering: bit 11 is the most significant bit (DEC bit 0). Every value is 0/1, a multi-bit
int, or None when it depends on an undefined register.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache

from .logic import bit, bits, eq, t_and, t_not, t_or


@dataclass
class ExternalInputs:
    """EXT §7 and §8. Levels as named: active-low signals are 0 when asserted."""
    int_req_n: int = 1      # /INT_REQ
    dma_req_n: int = 1      # /DMA_REQ (aggregate)
    io_read_req: int = 0
    io_write_req: int = 0
    io_skip_req: int = 0
    io_clear_ac_req: int = 0
    io_wait_n: int = 1      # /IO_WAIT (TSTEP-level; not modelled at TS granularity)
    db_input: int | None = None  # value a selected controller drives on DB, if any


@cache
def ir_decodes(ir) -> dict:
    """IRD: every IR-derived signal, computed from the live IR.

    A pure function of IR, so it is cached per IR value; callers must not modify the result."""
    op = bits(ir, 11, 9)
    is_iot = eq(op, 0o6)                                              # IRD IR_IS_IOT
    is_opr = eq(op, 0o7)                                              # IRD IR_IS_OPR
    is_mri = None if op is None else int(op <= 0o5)                   # IRD IR_IS_MRI
    ioa = bits(ir, 8, 3)                                              # IRD IR_IOA
    iot_op = bits(ir, 2, 0)                                           # IRD IR_IOT_OP
    g1 = t_and(is_opr, t_not(bit(ir, 8)))                             # IRD IR_OPR_GROUP1
    g2 = t_and(is_opr, bit(ir, 8), t_not(bit(ir, 0)))                 # IRD IR_OPR_GROUP2
    g3 = t_and(is_opr, bit(ir, 8), bit(ir, 0))                        # IRD IR_OPR_GROUP3
    memext = t_and(is_iot, eq(bits(ir, 8, 6), 0o2))                   # IRD IR_IS_MEMEXT_IOT
    dev00 = eq(ioa, 0)
    hi6 = bits(ir, 11, 6)
    memext_6x = eq(hi6, 0o62)  # IR[11:6] == 110010
    jmp = eq(op, 0o5)
    class_b2 = t_or(g2, g3)
    class_b1 = t_or(t_and(jmp, bit(ir, 8)), g1)
    class_b0 = t_or(t_and(jmp, t_not(bit(ir, 8))), g1, g3)
    return {
        # IRD IR_CLASS = {IR_OPR_GROUP2 OR IR_OPR_GROUP3,
        #                 (IR[11:9] = 101 AND IR[8]) OR IR_OPR_GROUP1,
        #                 (IR[11:9] = 101 AND NOT IR[8]) OR IR_OPR_GROUP1 OR IR_OPR_GROUP3}
        "IR_CLASS": None if None in (class_b2, class_b1, class_b0)
        else (class_b2 << 2) | (class_b1 << 1) | class_b0,
        "IR_NO_EXECUTE": t_or(jmp, is_opr),                           # IRD IR_NO_EXECUTE: JMP, OPR
        "IR_IS_MRI": is_mri,
        "IR_IS_IOT": is_iot,
        "IR_IS_OPR": is_opr,
        "IR_MRI_OPCODE": op,
        "IR_INDIRECT": t_and(is_mri, bit(ir, 8)),                     # IRD IR_INDIRECT
        "IR_ZERO_PAGE": t_and(is_mri, t_not(bit(ir, 7))),             # IRD IR_ZERO_PAGE
        "IR_ADDR": bits(ir, 6, 0),
        "IR_DF": bits(ir, 5, 3),
        "IR_IF": bits(ir, 5, 3),
        "IR_IOA": ioa,
        "IR_IOT_OP": iot_op,
        "IR_IS_CAF": t_and(is_iot, dev00, eq(iot_op, 0o7)),           # IRD IR_IS_CAF
        "IR_IS_GTF": t_and(is_iot, dev00, eq(iot_op, 0o4)),           # IRD IR_IS_GTF
        "IR_IS_RTF": t_and(is_iot, dev00, eq(iot_op, 0o5)),           # IRD IR_IS_RTF
        "IR_IS_MEMEXT_IOT": memext,
        "IR_IS_EXTERNAL_IOT": t_and(is_iot, t_not(dev00), t_not(memext)),  # IRD IR_IS_EXTERNAL_IOT
        "IR_OPR_GROUP1": g1,
        "IR_OPR_GROUP2": g2,
        "IR_OPR_GROUP3": g3,
        "IR_OPR_CLA": t_and(is_opr, bit(ir, 7)),
        "IR_OPR_CLL": t_and(g1, bit(ir, 6)),
        "IR_OPR_CMA": t_and(g1, bit(ir, 5)),
        "IR_OPR_CML": t_and(g1, bit(ir, 4)),
        "IR_OPR_RAR": t_and(g1, bit(ir, 3)),
        "IR_OPR_RAL": t_and(g1, bit(ir, 2)),
        "IR_OPR_BSW": t_and(g1, bit(ir, 1)),
        "IR_OPR_IAC": t_and(g1, bit(ir, 0)),
        "IR_OPR_SMA": t_and(g2, bit(ir, 6)),
        "IR_OPR_SZA": t_and(g2, bit(ir, 5)),
        "IR_OPR_SNL": t_and(g2, bit(ir, 4)),
        "IR_OPR_SKIP_MODE": t_and(g2, bit(ir, 3)),
        "IR_OPR_OSR": t_and(g2, bit(ir, 2)),
        "IR_OPR_HLT": t_and(g2, bit(ir, 1)),
        "IR_OPR_MQA": t_and(g3, bit(ir, 6)),
        "IR_OPR_MQL": t_and(g3, bit(ir, 4)),
        # IRD §2.5 memory management (devices 20-27)
        "IR_WRITES_DF": t_and(memext_6x, t_not(bit(ir, 2)), bit(ir, 0)),
        "IR_WRITES_IF": t_and(memext_6x, t_not(bit(ir, 2)), bit(ir, 1)),
        "IR_READS_DF": t_and(memext_6x, eq(iot_op, 0o4), eq(bits(ir, 5, 3), 0o1)),
        "IR_READS_IF": t_and(memext_6x, eq(iot_op, 0o4), eq(bits(ir, 5, 3), 0o2)),
        "IR_READS_IB": t_and(memext_6x, eq(iot_op, 0o4), eq(bits(ir, 5, 3), 0o3)),
        "IR_RESTORES_IB": t_and(memext_6x, eq(iot_op, 0o4), eq(bits(ir, 5, 3), 0o4)),
    }


def primitive_flags(st) -> dict:
    """FLG §4: functions of committed register state."""
    ea = st["EA_ADDR"]
    xfer = st["IOT_TRANSFER"]
    return {
        "ACN": bit(st["AC"], 11),
        "ACZ": eq(st["AC"], 0),
        "LZ": eq(st["L"], 0),
        "MBZ": eq(st["MB"], 0),
        "EAI": None if ea is None else int(0o10 <= ea <= 0o17),
        "CIFP": st["CIFP"],
        "IE": st["IE"],
        "II": st["II"],
        "HLT_REQ": st["HLT_REQ"],
        "RUN": st["RUN"],
        "SKIP": st["SKIP"],
        "IOT_READ_PENDING": eq(xfer, 0b01),
        "IOT_WRITE_PENDING": eq(xfer, 0b10),
    }


def opr_skip_req(d, f):
    """DRV OPR_SKIP_REQ."""
    mode = d["IR_OPR_SKIP_MODE"]
    nmode = t_not(mode)
    or_any = t_or(t_and(nmode, d["IR_OPR_SMA"], eq(f["ACN"], 1)),
                  t_and(nmode, d["IR_OPR_SZA"], eq(f["ACZ"], 1)),
                  t_and(nmode, d["IR_OPR_SNL"], eq(f["LZ"], 0)))
    spa = t_and(mode, d["IR_OPR_SMA"])
    sna = t_and(mode, d["IR_OPR_SZA"])
    szl = t_and(mode, d["IR_OPR_SNL"])
    and_all = t_and(t_or(t_not(spa), eq(f["ACN"], 0)),
                    t_or(t_not(sna), eq(f["ACZ"], 0)),
                    t_or(t_not(szl), eq(f["LZ"], 1)))
    return t_and(d["IR_OPR_GROUP2"], t_or(t_and(nmode, or_any), t_and(mode, and_all)))


class Conditions:
    """All control inputs for one TS, computed lazily from state, external inputs, and panel."""

    def __init__(self, st, ext: ExternalInputs, panel):
        self.st, self.ext, self.panel = st, ext, panel
        self._ir = None
        self._flags = None

    @property
    def ir(self) -> dict:
        if self._ir is None:
            self._ir = ir_decodes(self.st["IR"])
        return self._ir

    @property
    def flags(self) -> dict:
        if self._flags is None:
            self._flags = primitive_flags(self.st)
        return self._flags

    def get(self, name):
        if name in self.flags:
            return self.flags[name]
        if name in self.ir:
            return self.ir[name]
        f, d = self.flags, self.ir
        if name in ("OPR_SKIP_REQ", "SKIP_TAKEN"):                     # SKIP_TAKEN: V1-ONLY name
            return opr_skip_req(d, f)
        if name in ("ISZ_SKIP_REQ", "ISZ_SKIP_REQUIRED"):             # DRV ISZ_SKIP_REQ; V1-ONLY name
            return t_and(eq(d["IR_MRI_OPCODE"], 0o2), f["MBZ"])
        if name == "AUTO_INDEX_REQUIRED":                             # DRV AUTO_INDEX_REQUIRED
            return t_and(d["IR_INDIRECT"], f["EAI"])
        if name == "IF_CHANGE_PENDING":                               # DRV IF_CHANGE_PENDING
            return f["CIFP"]
        if name == "INTERRUPT_REQUEST_VALID":                         # DRV INTERRUPT_REQUEST_VALID
            return t_and(f["IE"], eq(f["II"], 0), eq(self.ext.int_req_n, 0))
        ext = {
            "/INT_REQ": self.ext.int_req_n,
            "/DMA_REQ": self.ext.dma_req_n,
            "IO_READ_REQ": self.ext.io_read_req,
            "IO_WRITE_REQ": self.ext.io_write_req,
            "IO_SKIP_REQ": self.ext.io_skip_req,
            "IO_CLEAR_AC_REQ": self.ext.io_clear_ac_req,
            "FP_STOP": int(self.panel.stop),
            "FP_SINGLE_STEP": int(self.panel.single_step),
            "FP_SINGLE_INSTRUCTION": int(self.panel.single_instruction),
        }
        if name in ext:
            return ext[name]
        raise KeyError(f"unknown control input {name}")
