"""One timing state of datapath evaluation.

Source: docs/04-control/20-control-output-definitions/01-microarchitectural-control-signals.md
(MCS) §5 (field meanings), §7 (evaluation and commit), §11 (timing); architectural signals from
02-architectural-control-signals.md (ACS) §3-§5; memory from docs/06-memory/03-read-write-protocol.md
(MEM).

Evaluation is demand-driven from the enabled operations: a select field is interpreted only when
the operation it parameterizes is enabled (Control Word §8.2, §8.4, §8.5). Every read observes the
state committed at the previous TP (MCS §11.5); the returned `Effects` are committed together at
this TS's TP (MCS §7.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import encodings as E
from .errors import NotModelled, SpecViolation
from .logic import bit, bits, u

MASK12 = 0o7777


@dataclass
class Effects:
    loads: dict = field(default_factory=dict)       # register -> value committed at TP
    mem_read: tuple | None = None                   # (field, address) read during the TS
    mem_write: tuple | None = None                  # (field, address, value) stored by the TP
    db_write: int | None = None                     # AC value the CPU drives on DB
    db_read: bool = False
    strobes: dict = field(default_factory=dict)     # asserted architectural strobes

    def key(self):
        return (tuple(sorted(self.loads.items())), self.mem_read, self.mem_write,
                self.db_write, self.db_read, tuple(sorted(self.strobes.items())))


def alu(op, a, b, lin):
    """MCS §7.3.1. Returns (ALU_RESULT, ALU_LINK); None for an undefined result."""
    if op == E.CLEAR:
        return 0, lin
    if op in (E.ADD, E.AND, E.OR):
        if a is None or b is None:
            return None, None if op == E.ADD else lin
        if op == E.ADD:
            s = a + b
            return s & MASK12, u(lambda l: l ^ (s >> 12), lin)
        return (a & b, lin) if op == E.AND else (a | b, lin)
    if a is None:
        return None, None if op in (E.INC, E.ROR, E.ROL, E.RTR, E.RTL) else lin
    if op == E.NOT:
        return ~a & MASK12, lin
    if op == E.INC:
        s = a + 1
        return s & MASK12, u(lambda l: l ^ (s >> 12), lin)
    if op == E.BSW:
        return ((a & 0o77) << 6) | (a >> 6), lin
    # Rotates move LIN·A as a 13-bit ring.
    if op == E.ROR:
        return u(lambda l: (l << 11) | (a >> 1), lin), a & 1
    if op == E.ROL:
        return u(lambda l: ((a << 1) & MASK12) | l, lin), (a >> 11) & 1
    if op == E.RTR:
        return u(lambda l: ((a & 1) << 11) | (l << 10) | (a >> 2), lin), (a >> 1) & 1
    if op == E.RTL:
        return u(lambda l: ((a & 0o1777) << 2) | (l << 1) | (a >> 11), lin), (a >> 10) & 1
    raise SpecViolation(f"reserved ALU_OP {op:o}", "MCS ALU_OP")


class _Eval:
    def __init__(self, f, st, ext, panel, memory, cond, mseff):
        self.f, self.st, self.ext, self.panel, self.memory = f, st, ext, panel, memory
        self.cond, self.mseff = cond, mseff
        self.fx = Effects()
        self._alu = None
        self._mdb = None

    # -- helpers -----------------------------------------------------------------------------

    def sel(self, name):
        """Read a select field that is being interpreted; reserved encodings are violations."""
        code = self.f[name]
        if E.DATAPATH_FIELDS[name].is_reserved(code):
            raise SpecViolation(f"{name} = {code:o} is reserved", E.DATAPATH_FIELDS[name].cite)
        return code

    def asserted(self, name):
        return self.f[name] == 0  # active-low strobes (ACS §3.1)

    def alu(self):
        """MCS §7.3.1, with operands selected by ALU_A_SRC and ALU_B_SRC."""
        if self._alu is None:
            st = self.st
            a = {0: st["AC"], 1: st["MB"], 2: st["PC"]}[self.sel("ALU_A_SRC")]
            op = self.sel("ALU_OP")
            b_src = self.sel("ALU_B_SRC")
            if b_src == 0 and op in (E.ADD, E.AND, E.OR):
                raise SpecViolation(f"binary ALU_OP {op:o} with ALU_B_SRC = NONE",
                                    "MCS ALU_B_SRC (NONE is for unary operations), §9.5.2")
            b = {0: None, 1: st["MB"], 2: st["MQ"], 3: self.panel.sr}[b_src]
            self._alu = alu(op, a, b, st["L"])
        return self._alu

    def idb(self):
        """MCS IDB_DRIVE, IDB_SRC, §7.3.2: the selected source, only while driven."""
        if self.f["IDB_DRIVE"] != 1:
            raise SpecViolation("a register loads from the IDB while IDB_DRIVE = 0", "MCS IDB_DRIVE, §7.12")
        st = self.st
        src = self.sel("IDB_SRC")
        if src == 7:
            return self.alu()[0]
        return {0: st["AC"], 1: st["PC"], 2: st["MB"], 3: st["MQ"], 4: self.panel.sr,
                5: st["EA_ADDR"], 6: st["IR"]}[src]

    def memory_address(self, purpose):
        """MEM §3: MEM_ADDR = {MFB, AB}; AB by AB_SRC, MFB by MFB_SRC."""
        st = self.st
        ab = st["MA"] if self.sel("AB_SRC") == 0 else st["PC"]
        mfb = st["IF"] if self.sel("MFB_SRC") == 0 else st["DF"]
        if ab is None or mfb is None:
            raise SpecViolation(f"memory {purpose} with an undefined address (AB = {ab}, MFB = {mfb})",
                                "MEM §12")
        return mfb, ab

    def cpu_mdb_drive(self):
        """ACS §3.2: the CPU drives MDB whenever MDB_SRC selects MB or FP_SR."""
        src = self.f["MDB_SRC"]
        if src == 1:
            return True, self.st["MB"]
        if src == 2:
            return True, self.panel.sr
        return False, None

    def mdb(self):
        """The value on MDB this TS, for a consumer that loads it (MB_SRC = MDB)."""
        if self._mdb is None:
            cpu_drives, cpu_value = self.cpu_mdb_drive()
            if self.asserted("/RD"):
                if cpu_drives:
                    raise SpecViolation("CPU drives MDB during a memory read", "MEM §12")
                self._mdb = ("memory", self.memory.read(*self.fx.mem_read))
            elif cpu_drives:
                self._mdb = ("cpu", cpu_value)
            else:
                raise SpecViolation("MB loads from MDB, but nothing drives MDB", "MEM §12, MCS MB_SRC")
        return self._mdb[1]

    # -- evaluation --------------------------------------------------------------------------

    def run(self) -> Effects:
        f, st, fx = self.f, self.st, self.fx
        if self.mseff == E.DMA:
            raise NotModelled("the DMA major state is outside the simulator's current scope")

        rd, wr = self.asserted("/RD"), self.asserted("/WR")
        if rd and wr:
            raise SpecViolation("/RD and /WR asserted together", "ACS §5.1, MEM §3")
        if rd:
            fx.mem_read = self.memory_address("read")
            fx.strobes["/RD"] = True
        if wr:
            address = self.memory_address("write")
            cpu_drives, value = self.cpu_mdb_drive()
            if not cpu_drives:
                raise SpecViolation(f"memory write with MDB_SRC = {f['MDB_SRC']}: no CPU MDB driver",
                                    "MEM §12, MCS MDB_SRC")
            fx.mem_write = (address[0], address[1], value)
            fx.strobes["/WR"] = True

        dbr, dbw = self.asserted("/DB_READ"), self.asserted("/DB_WRITE")
        if dbr and dbw:
            raise SpecViolation("/DB_READ and /DB_WRITE asserted together", "ACS §4.3, §4.4")
        if dbw:
            fx.db_write = st["AC"]
            fx.strobes["/DB_WRITE"] = True
        if dbr:
            fx.db_read = True
            fx.strobes["/DB_READ"] = True

        if f["AC_LOAD"]:
            fx.loads["AC"] = self.ac_input(dbr)
        if f["L_LOAD"]:
            fx.loads["L"] = self.l_input()
        if f["MQ_LOAD"]:
            fx.loads["MQ"] = self.idb() if self.sel("MQ_SRC") == 0 else st["AC"]
        if f["IR_LOAD"]:
            fx.loads["IR"] = st["MB"]                      # MB_TO_IR: IR <- MB
        if f["PC_INC"] and f["PC_LOAD"]:
            raise SpecViolation("PC_INC and PC_LOAD asserted together", "MCS PC_INC, PC_LOAD")
        if f["PC_INC"]:
            if self.sel("ALU_OP") != E.INC or self.sel("ALU_A_SRC") != 2:
                raise SpecViolation("PC_INC without ALU_OP = INC and ALU_A_SRC = PC", "MCS PC_INC")
            fx.loads["PC"] = self.alu()[0]
        if f["PC_LOAD"]:
            fx.loads["PC"] = self.idb() if self.sel("PC_SRC") == 0 else 0o0001
        if f["MA_LOAD"]:
            fx.loads["MA"] = {0: st["PC"], 1: st["EA_ADDR"], 2: 0}[self.sel("MA_SRC")]
        if f["MB_LOAD"]:
            fx.loads["MB"] = {0: self.idb, 1: self.mdb, 2: lambda: self.panel.sr}[self.sel("MB_SRC")]()
        if f["EA_ADDR_LOAD"]:
            fx.loads["EA_ADDR"] = self.idb() if self.sel("EA_ADDR_SRC") == 0 else self.ea_formed()
        if f["IF_LOAD"]:
            fx.loads["IF"] = {0: 0, 1: st["DIF"], 2: self.panel.fp_if}[self.sel("IF_SRC")]
        if f["DF_LOAD"]:
            fx.loads["DF"] = {0: 0, 1: bits(st["IB"], 2, 0), 2: self.panel.fp_df,
                              3: bits(st["AC"], 2, 0), 4: bits(st["IR"], 5, 3)}[self.sel("DF_SRC")]
        if f["DIF_LOAD"]:
            fx.loads["DIF"] = {0: bits(st["IB"], 5, 3), 1: 0, 2: self.panel.fp_if,
                               3: bits(st["AC"], 5, 3), 4: bits(st["IR"], 5, 3)}[self.sel("DIF_SRC")]
        if f["IB_LOAD"]:
            fx.loads["IB"] = u(lambda i, d: (i << 3) | d, st["IF"], st["DF"])   # IF_DF_TO_IB
        if f["CIFP_LOAD"]:
            fx.loads["CIFP"] = f["CIFP_VAL"]
        if f["IE_LOAD"]:
            fx.loads["IE"] = f["IE_VAL"]
        if f["II_LOAD"]:
            fx.loads["II"] = f["II_VAL"]
        if f["IOT_TRANSFER_LOAD"]:
            fx.loads["IOT_TRANSFER"] = self.sel("IOT_TRANSFER_VAL")
        return fx

    def ac_input(self, db_read):
        """MCS AC_SRC: the IDB, or a field merge / transfer into AC."""
        st = self.st
        ac = st["AC"]
        src = self.sel("AC_SRC")
        if src == 0:
            return self.idb()
        if src == 1:                                     # DB_READ_TO_AC: AC <- AC OR DB
            if not db_read:
                raise SpecViolation("AC loads from DB while /DB_READ is not asserted", "ACS §4.3")
            if self.ext.db_input is None:
                raise SpecViolation("AC loads from DB, but no controller drives DB", "ACS §4.3")
            return u(lambda a: a | self.ext.db_input, ac)
        if src == 2:                                     # IF_TO_AC: AC[5:3] <- AC[5:3] OR IF
            return u(lambda a, i: a | (i << 3), ac, st["IF"])
        if src == 3:                                     # DF_TO_AC: AC[5:3] <- AC[5:3] OR DF
            return u(lambda a, d: a | (d << 3), ac, st["DF"])
        if src == 4:                                     # IB_TO_AC: AC[5:0] <- AC[5:0] OR IB
            return u(lambda a, b: a | b, ac, st["IB"])
        if src == 5:                                     # AC_MQ_SWAP: AC <- MQ
            return st["MQ"]
        return u(lambda a, g: a | g, ac, self.gtf_flags())  # GTF_FLAGS_TO_AC: AC <- AC OR GTF_FLAGS

    def gtf_flags(self):
        """MCS GTF_FLAGS: [11] L, [9] (/INT_REQ = 0), [7] IE, [5:0] IB (the save field)."""
        st = self.st
        int_req = int(self.ext.int_req_n == 0)
        return u(lambda l, ie, ib: (l << 11) | (int_req << 9) | (ie << 7) | ib,
                 st["L"], st["IE"], st["IB"])

    def l_input(self):
        """MCS L_OP: CLEAR, COMP, ALU_LINK, or the pre-TP AC[11]."""
        op = self.sel("L_OP")
        if op == 0:
            return 0
        if op == 1:
            return u(lambda l: 1 - l, self.st["L"])
        if op == 2:
            return self.alu()[1]
        return bit(self.st["AC"], 11)

    def ea_formed(self):
        """IR_ADDR_TO_EA_ADDR: zero page (0 || IR[6:0]) or current page (PC[11:7] || IR[6:0])."""
        ir, pc = self.st["IR"], self.st["PC"]
        zero_page = self.cond.get("IR_ZERO_PAGE")
        if ir is None or zero_page is None:
            return None
        if zero_page == 1:
            return ir & 0o177
        return u(lambda p: (p & 0o7600) | (ir & 0o177), pc)


def evaluate(fields, st, ext, panel, memory, cond, mseff) -> Effects:
    return _Eval(fields, st, ext, panel, memory, cond, mseff).run()
