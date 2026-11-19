"""Three-valued logic and field helpers.

A value is an int, or None when UNDEFINED. Power-on leaves most registers undefined
([Timing Terminology §3.4](../../../../docs/09-timing/01-terminology.md#34-power-on-reset)); the
simulator carries that through combinational logic instead of choosing a value. A bit that is
0 decides an AND regardless of undefined inputs, and a bit that is 1 decides an OR.
"""

from __future__ import annotations

UNDEFINED = None


def t_and(*bits):
    undefined = False
    for b in bits:
        if b == 0:
            return 0
        if b is None:
            undefined = True
    return None if undefined else 1


def t_or(*bits):
    undefined = False
    for b in bits:
        if b == 1:
            return 1
        if b is None:
            undefined = True
    return None if undefined else 0


def t_not(bit):
    return None if bit is None else 1 - bit


def bit(value, n):
    """Bit n of value (bit 11 is the most significant bit of a 12-bit word, DEC bit 0)."""
    return None if value is None else (value >> n) & 1


def bits(value, hi, lo):
    """value[hi:lo]."""
    return None if value is None else (value >> lo) & ((1 << (hi - lo + 1)) - 1)


def eq(value, constant):
    return None if value is None else int(value == constant)


def defined(*values) -> bool:
    return all(v is not None for v in values)


def u(fn, *values):
    """Apply fn to values, or return UNDEFINED if any value is undefined."""
    return fn(*values) if defined(*values) else None
