"""Sequencing commits at a TP.

- MS, RUN, HLT_REQ: docs/01-architecture/01-registers.md; Sequencing Control Signals §4
  (docs/04-control/20-control-output-definitions/03-sequencing-control-signals.md, SCS).
- Halt only at TP4, TSEQ held at TS1 while halted: docs/09-timing/03-major-state-timing.md (MST) §8.1.
- TS advance TS n -> TS n+1, TS4 -> TS1: Timing Terminology §3.2.
"""

from __future__ import annotations

from . import encodings as E
from .errors import SpecViolation


def sequencer_loads(seq, main_sequence: bool, ts: int) -> dict:
    """The register loads the sequencer word commits at this TP (or TP_FP)."""
    loads = {"RUN": seq["RUN_NEXT"], "HLT_REQ": seq["HLT_REQ_NEXT"]}   # SCS §3.1: applied every TP
    if seq["MS_LOAD"]:
        if E.SEQUENCER_FIELDS["MS_NEXT"].is_reserved(seq["MS_NEXT"]):
            raise SpecViolation(f"MS_NEXT = {seq['MS_NEXT']} is a reserved major-state code",
                                "SCS §4.1, Registers MS")
        loads["MS"] = seq["MS_NEXT"]
    if main_sequence and seq["RUN_NEXT"] == 0 and ts != 4:
        raise SpecViolation(f"RUN_NEXT = 0 at TP{ts}; a halt commits only at TP4", "MST §8.1")
    return loads


def next_ts(ts: int, run_after: int) -> int:
    """TS after a main-sequence TP: held at TS1 once halted, otherwise advanced."""
    if run_after == 0:
        return 1
    return 1 if ts == 4 else ts + 1
