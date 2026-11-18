"""The reference model: one instruction, or one interrupt entry, per step.

Sources (docs/):

- ENC = 02-isa/00-encoding-model.md        - G1, G2, G3 = 02-isa/01..03-group-*.md
- IOT = 02-isa/04-iot.md                     - ADR = 02-isa/05-addressing-model.md
- EA  = 02-isa/06-ea-generation.md           - INH = 08-interrupts-and-skip/03-interrupt-enable-and-inhibit.md
- ENT = 08-interrupts-and-skip/04-interrupt-entry-and-return.md
- REC = 08-interrupts-and-skip/02-interrupt-recognition-and-sequencing.md

State is the programmer-visible machine: AC, L, MQ, PC, IF, DF, IE, the interrupt-saved fields
(IB), a staged instruction field (set by CIF, RMF, or RTF and applied by the next JMP or JMS), and
32K words of memory. Controllers in `devices` (for example the KL8E model) respond to their
external-device IOTs; an IOT that selects no controller has no effect (IOT §1, ENC §5).
"""

from __future__ import annotations

from dataclasses import dataclass, field

M12 = 0o7777
FIELDS, WORDS = 8, 4096


class ReferenceError(Exception):
    """The reference model cannot proceed (for example, it read an undefined memory word)."""


@dataclass
class StepResult:
    kind: str                      # "instruction" or "interrupt"
    pc: int                        # address of the instruction (or the interrupted PC)
    field: int                     # its instruction field
    ir: int | None                 # the instruction word (None for an interrupt entry)
    writes: list = field(default_factory=list)   # (field, address, value) memory writes
    halted: bool = False           # a HLT executed
    interrupt_next: bool = False   # an interrupt is recognized at this boundary


class Reference:
    def __init__(self):
        self.ac = self.l = self.mq = self.pc = self.if_ = self.df = self.ie = 0
        self.ib = None                 # interrupt-saved fields: IB[5:3] = IF, IB[2:0] = DF (ENT §7);
                                       # undefined until the first interrupt entry
        self.staged_if = None          # deferred instruction field, or None when none is pending
        self.sr = 0                    # front-panel switch register (G2 OSR)
        self.int_req = False           # interrupt request from outside the model (test stimulus)
        self.devices = []              # attached controllers
        self._late = []                # controller effects that commit at TP4
        self.memory = [[None] * WORDS for _ in range(FIELDS)]
        self.interrupt_pending = False # recognized at the last boundary; entry is the next step
        self._writes = []

    # -- memory -----------------------------------------------------------------------------

    def read(self, f, a):
        value = self.memory[f][a & M12]
        if value is None:
            raise ReferenceError(f"read of undefined memory {f:o}:{a & M12:04o}")
        return value

    def write(self, f, a, value):
        self.memory[f][a & M12] = value & M12
        self._writes.append((f, a & M12, value & M12))

    def interrupt_request(self) -> bool:
        """The aggregate request: the stimulus, or any controller's contribution."""
        return bool(self.int_req or any(d.interrupt_request() for d in self.devices))

    def _finish_boundary(self):
        """Apply controller effects that commit at TP4, then count the instruction boundary."""
        for action in self._late:
            action()
        self._late = []
        for device in self.devices:
            device.at_boundary()

    # -- one step -----------------------------------------------------------------------------

    def step(self) -> StepResult:
        self._writes = []
        if self.interrupt_pending:
            return self._interrupt_entry()
        pc, f = self.pc, self.if_
        ir = self.read(f, pc)
        self.pc = (pc + 1) & M12                      # the PC advances during fetch
        cifp_at_start = self.staged_if is not None
        result = StepResult("instruction", pc, f, ir)
        inhibit = self._execute(ir, pc, result) or cifp_at_start
        result.writes = self._writes
        # REC §6: recognition at instruction completion; INH §16: ION, CIF, RMF, RTF and a pending
        # field change inhibit recognition at this boundary; IOT §3.2: never at CAF's completion.
        caf = ir == 0o6007
        result.interrupt_next = bool(self.ie and self.interrupt_request() and not inhibit and not caf)
        self.interrupt_pending = result.interrupt_next
        self._finish_boundary()
        return result

    def _interrupt_entry(self) -> StepResult:
        """ENT §4-§6: M[0:0000] <- PC; IB <- IF, DF; IE, IF, DF, staged field cleared; PC <- 0001."""
        result = StepResult("interrupt", self.pc, self.if_, None)
        self.write(0, 0, self.pc)
        self.ib = (self.if_ << 3) | self.df
        self.ie = 0
        self.if_ = self.df = 0
        self.staged_if = None
        self.pc = 0o0001
        self.interrupt_pending = False
        result.writes = self._writes
        self._finish_boundary()
        return result

    # -- instruction classes ------------------------------------------------------------------

    def _execute(self, ir, pc, result) -> bool:
        """Execute ir fetched from pc; return True if it inhibits interrupt recognition."""
        op = ir >> 9
        if op <= 5:
            self._mri(ir, pc)
            return False
        if op == 6:
            return self._iot(ir)
        self._opr(ir, result)
        return False

    def _effective_address(self, ir, pc):
        """EA §6-§8, ADR §7: base address in IF; indirect pointer in IF with autoindex; the final
        field is DF for AND, TAD, ISZ, DCA and IF (after any staged change) for JMP and JMS."""
        offset = ir & 0o177
        base = (pc & 0o7600) | offset if ir & 0o200 else offset   # page of the instruction (ADR §8)
        if not ir & 0o400:
            return self.if_, base
        if 0o010 <= base <= 0o017:                                # EA §8.2 autoindex
            self.write(self.if_, base, self.read(self.if_, base) + 1)
        pointer = self.read(self.if_, base)
        return (self.df if (ir >> 9) <= 3 else None), pointer      # JMP/JMS: field decided below

    def _apply_staged_field(self):
        """IOT §4.1: a staged IF is applied by JMP or JMS."""
        if self.staged_if is not None:
            self.if_ = self.staged_if
            self.staged_if = None

    def _mri(self, ir, pc):
        op = ir >> 9
        f, ea = self._effective_address(ir, pc)
        if op == 0:                                                # AND
            self.ac &= self.read(f, ea)
        elif op == 1:                                              # TAD
            s = self.ac + self.read(f, ea)
            self.ac, self.l = s & M12, self.l ^ (s >> 12)
        elif op == 2:                                              # ISZ
            v = (self.read(f, ea) + 1) & M12
            self.write(f, ea, v)
            if v == 0:
                self.pc = (self.pc + 1) & M12
        elif op == 3:                                              # DCA
            self.write(f, ea, self.ac)
            self.ac = 0
        elif op == 4:                                              # JMS: store in the new IF
            self._apply_staged_field()
            self.write(self.if_, ea, self.pc)
            self.pc = (ea + 1) & M12
        else:                                                      # JMP
            self._apply_staged_field()
            self.pc = ea

    def _iot(self, ir) -> bool:
        device, operation = (ir >> 3) & 0o77, ir & 0o7
        if device == 0:
            return self._processor_iot(operation)
        if (device >> 3) == 0o2:
            return self._memory_extension(ir)
        for controller in self.devices:                            # external-device IOT
            if controller.selects(device):
                skip, late = controller.iot(self, device, operation)
                if skip:
                    self.pc = (self.pc + 1) & M12
                if late:
                    self._late.append(late)
        return False

    def _processor_iot(self, operation) -> bool:
        """IOT §3."""
        if operation == 0:                                         # SKON
            if self.ie:
                self.pc = (self.pc + 1) & M12
            self.ie = 0
        elif operation == 1:                                       # ION (deferred by one instruction)
            self.ie = 1
            return True
        elif operation == 2:                                       # IOF
            self.ie = 0
        elif operation == 3:                                       # SRQ
            if self.interrupt_request():
                self.pc = (self.pc + 1) & M12
        elif operation == 4:                                       # GTF (§3.1.1)
            self.ac = ((self.l << 11) | (int(self.interrupt_request()) << 9) | (self.ie << 7)
                       | (self.if_ << 3) | self.df)
        elif operation == 5:                                       # RTF (§3.1.2)
            self.l = self.ac >> 11
            self.df = self.ac & 0o7
            self.staged_if = (self.ac >> 3) & 0o7
            self.ie = 1
            return True
        elif operation == 6:                                       # SGT: defined no-op (§6.1)
            pass
        else:                                                      # CAF (§3.2): controllers at TP4
            self.ac = 0
            self.l = 0
            self.ie = 0
            self._late.extend(d.initialize for d in self.devices)
        return False

    def _memory_extension(self, ir) -> bool:
        """IOT §4: devices 20-27."""
        n = (ir >> 3) & 0o7
        low = ir & 0o7
        inhibit = False
        if not low & 0o4:
            if low & 0o1:                                          # CDF
                self.df = n
            if low & 0o2:                                          # CIF (deferred)
                self.staged_if = n
                inhibit = True
            return inhibit
        if low == 0o4:
            if n in (3, 4) and self.ib is None:
                raise ReferenceError("RIB or RMF reads the interrupt buffer before any interrupt entry")
            if n == 1:                                             # RDF
                self.ac |= self.df << 3
            elif n == 2:                                           # RIF
                self.ac |= self.if_ << 3
            elif n == 3:                                           # RIB
                self.ac |= self.ib
            elif n == 4:                                           # RMF
                self.df = self.ib & 0o7
                self.staged_if = self.ib >> 3
                inhibit = True
        return inhibit

    def _opr(self, ir, result):
        if not ir & 0o400:
            self._group1(ir)
        elif not ir & 0o001:
            self._group2(ir, result)
        else:
            self._group3(ir)

    def _group1(self, ir):
        """G1 §1: CLA, CLL; CMA, CML; IAC; then RAR, RAL, BSW (notes 1-4)."""
        if ir & 0o200:
            self.ac = 0
        if ir & 0o100:
            self.l = 0
        if ir & 0o040:
            self.ac = ~self.ac & M12
        if ir & 0o020:
            self.l ^= 1
        if ir & 0o001:
            s = self.ac + 1
            self.ac, self.l = s & M12, self.l ^ (s >> 12)
        rar, ral, bsw = ir & 0o010, ir & 0o004, ir & 0o002
        if rar and ral:
            return                                                 # note 4
        if rar or ral:
            for _ in range(2 if bsw else 1):
                v = (self.l << 12) | self.ac
                v = (((v & 1) << 12) | (v >> 1)) if rar else (((v << 1) & 0o17777) | (v >> 12))
                self.l, self.ac = v >> 12, v & M12
        elif bsw:
            self.ac = ((self.ac & 0o77) << 6) | (self.ac >> 6)

    def _group2(self, ir, result):
        """G2: skip test first; then CLA; then OSR and HLT."""
        sma, sza, snl = ir & 0o100, ir & 0o040, ir & 0o020
        neg, zero = self.ac >> 11, self.ac == 0
        if ir & 0o010:                                             # AND sub-group; SKP (§6)
            skip = (not sma or not neg) and (not sza or not zero) and (not snl or not self.l)
        else:
            skip = (sma and neg) or (sza and zero) or (snl and self.l)
        if skip:
            self.pc = (self.pc + 1) & M12
        if ir & 0o200:
            self.ac = 0
        if ir & 0o004:
            self.ac |= self.sr
        if ir & 0o002:
            result.halted = True

    def _group3(self, ir):
        """G3: CLA; then MQA, MQL, or SWP; EAE bits select nothing."""
        if ir & 0o200:
            self.ac = 0
        mqa, mql = ir & 0o100, ir & 0o020
        if mqa and mql:
            self.ac, self.mq = self.mq, self.ac
        elif mqa:
            self.ac |= self.mq
        elif mql:
            self.mq, self.ac = self.ac, 0
