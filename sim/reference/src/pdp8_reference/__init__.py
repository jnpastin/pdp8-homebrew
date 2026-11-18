"""Instruction-level reference model of the PDP-8/e-compatible ISA.

Written only from the ISA documentation (docs/02-isa) and the architectural interrupt rules
(docs/08-interrupts-and-skip). It knows nothing of timing states, micro-operations, or the
control store, so comparing it with the control-store simulator checks one documentation layer
against the other.
"""

from .disasm import disassemble
from .kl8e import KL8E
from .model import Reference, ReferenceError, StepResult

__all__ = ["KL8E", "Reference", "ReferenceError", "StepResult", "disassemble"]
