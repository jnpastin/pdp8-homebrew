"""Mnemonic disassembly for reports (docs/02-isa). Informational only; it never affects execution."""

from __future__ import annotations

MRI = ("AND", "TAD", "ISZ", "DCA", "JMS", "JMP")
PROCESSOR_IOT = ("SKON", "ION", "IOF", "SRQ", "GTF", "RTF", "SGT", "CAF")
# KL8E device 03 and 04 IOTs (docs/07-io/10-controllers/01-kl8e-uart.md §10, §18)
DEVICE_IOT = {0o03: ("KCF", "KSF", "KCC", None, "KRS", "KIE", "KRB", None),
              0o04: ("TFL", "TSF", "TCF", None, "TPC", "TSK", "TLS", None)}


def _group1(ir):
    names = [n for bit, n in ((0o200, "CLA"), (0o100, "CLL"), (0o040, "CMA"), (0o020, "CML"), (0o001, "IAC"))
             if ir & bit]
    rar, ral, bsw = ir & 0o010, ir & 0o004, ir & 0o002
    if rar and ral:
        names.append("RAR RAL")
    elif rar:
        names.append("RTR" if bsw else "RAR")
    elif ral:
        names.append("RTL" if bsw else "RAL")
    elif bsw:
        names.append("BSW")
    return " ".join(names) or "NOP"


def _group2(ir):
    if ir & 0o010:
        skips = [n for bit, n in ((0o100, "SPA"), (0o040, "SNA"), (0o020, "SZL")) if ir & bit] or ["SKP"]
    else:
        skips = [n for bit, n in ((0o100, "SMA"), (0o040, "SZA"), (0o020, "SNL")) if ir & bit]
    names = skips + [n for bit, n in ((0o200, "CLA"), (0o004, "OSR"), (0o002, "HLT")) if ir & bit]
    return " ".join(names) or "NOP"


def _group3(ir):
    mqa, mql = ir & 0o100, ir & 0o020
    names = ["CLA"] if ir & 0o200 else []
    names += ["SWP"] if mqa and mql else ["MQA"] if mqa else ["MQL"] if mql else []
    return " ".join(names) or "NOP"


def disassemble(ir) -> str:
    if ir is None:
        return "(undefined)"
    op = ir >> 9
    if op <= 5:
        return (f"{MRI[op]}{' I' if ir & 0o400 else ''} "
                f"{'' if ir & 0o200 else 'Z '}{ir & 0o177:03o}")
    if op == 6:
        device, operation = (ir >> 3) & 0o77, ir & 0o7
        if device == 0:
            return PROCESSOR_IOT[operation]
        if device >> 3 == 0o2:
            n = device & 0o7
            if not operation & 0o4:
                parts = [p for bit, p in ((1, f"CDF {n}0"), (2, f"CIF {n}0")) if operation & bit]
                return " ".join(parts) or f"IOT {ir:04o}"
            if operation == 0o4 and 1 <= n <= 4:
                return ("RDF", "RIF", "RIB", "RMF")[n - 1]
        name = DEVICE_IOT.get(device, (None,) * 8)[operation]
        return name or f"IOT {ir:04o}"
    if not ir & 0o400:
        return _group1(ir)
    return _group3(ir) if ir & 1 else _group2(ir)
