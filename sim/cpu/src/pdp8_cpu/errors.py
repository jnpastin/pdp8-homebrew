"""Errors raised by the simulator.

Every error carries the rule it concerns (a document citation) and the machine context in which
it occurred, so a failure names the timing state, the instruction, and the control-store
addresses involved.
"""

from __future__ import annotations


class SimError(Exception):
    """Base class: a condition that stops simulation."""

    def __init__(self, message: str, rule: str = "", context: dict | None = None):
        self.message = message
        self.rule = rule
        self.context = dict(context or {})
        super().__init__(self._format())

    def _format(self) -> str:
        parts = [self.message]
        if self.rule:
            parts.append(f"rule: {self.rule}")
        if self.context:
            parts.append("context: " + ", ".join(f"{k}={_fmt(v)}" for k, v in self.context.items()))
        return " | ".join(parts)

    def with_context(self, **context) -> SimError:
        """Return the same error with more context added (existing keys win)."""
        merged = dict(context)
        merged.update(self.context)
        return type(self)(self.message, self.rule, merged)


class SpecViolation(SimError):
    """A documented rule is broken: an invalid encoding, conflicting signals, an undriven bus."""


class SpecGap(SimError):
    """The documentation is silent or inconsistent about behavior the simulator needs."""


class ImageError(SimError):
    """The control-store images or packing description are missing or malformed."""


class NotModelled(SimError):
    """The machine reached behavior outside the simulator's current scope (for example DMA)."""


def _fmt(value) -> str:
    if value is None:
        return "UNDEFINED"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:o}"
    return str(value)
