"""Phase 0 feasibility: run MAINDEC-8E-D2AB PRG0 on the reference model alone under different
per-instruction cycle-cost models. Scratch experiment; not part of the repository.

Usage: pypy3.12 d2ab_timing.py REPO [model ...]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(sys.argv[1]).resolve()
for pkg in ("cpu", "memory", "reference", "io", "system"):
    sys.path.insert(0, str(REPO / "sim" / pkg / "src"))

from pdp8_reference import Reference, disassemble  # noqa: E402
from pdp8_system import maindec  # noqa: E402
from pdp8_system.lockstep import reference_from  # noqa: E402

F, S = 1200, 1400  # 8/E fast and slow cycle, ns


def classify(ir, pc, ref_before_memory, if_):
    """Instruction class: opr, iot, jmp, jmpi, mri, mrii; and whether an indirect is autoindex."""
    op = ir >> 9
    ind = (ir >> 8) & 1
    if op == 7:
        return "opr", False
    if op == 6:
        return "iot", False
    page = (ir >> 7) & 1
    addr = (ir & 0o177) | ((pc & 0o7600) if page else 0)
    auto = bool(ind and 0o10 <= addr <= 0o17)
    if op == 5:
        return ("jmpi" if ind else "jmp"), auto
    return ("mrii" if ind else "mri"), auto


# Each model: class -> ns, given autoindex flag. Interrupt entry and DMA stay 1200.
def today(c, auto):
    return {"opr": 2 * F, "iot": 2 * F, "jmp": 2 * F, "jmpi": 3 * F, "mri": 2 * F, "mrii": 3 * F}[c]


def opt2_uniform(c, auto):
    return {"opr": F, "iot": 2 * F, "jmp": F, "jmpi": 2 * F, "mri": 2 * F, "mrii": 3 * F}[c]


def _defer(auto):
    return S if auto else F


def opt2_8e_iot2400(c, auto):
    """Option 2 with 8/E durations (FETCH fast, EXECUTE slow, autoindex DEFER slow); IOT keeps a
    1.2 us EXECUTE (2.4 us total)."""
    return {"opr": F, "iot": 2 * F, "jmp": F, "jmpi": F + _defer(auto),
            "mri": F + S, "mrii": F + _defer(auto) + S}[c]


def opt2_8e_iot2600(c, auto):
    """As above, IOT's EXECUTE slow (2.6 us total)."""
    d = opt2_8e_iot2400(c, auto)
    return F + S if c == "iot" else d


def opt2_8e_iot1200(c, auto):
    """As above, but the TS-length table squeezes IOT's two states into 1.2 us total."""
    d = opt2_8e_iot2400(c, auto)
    return F if c == "iot" else d


def opt1_8e(c, auto):
    """PDP-8/E: OPR, IOT, direct JMP one fast cycle."""
    return {"opr": F, "iot": F, "jmp": F, "jmpi": F + _defer(auto),
            "mri": F + S, "mrii": F + _defer(auto) + S}[c]


MODELS = {f.__name__: f for f in (today, opt2_uniform, opt2_8e_iot2400, opt2_8e_iot2600,
                                    opt2_8e_iot1200, opt1_8e)}


class CostedReference(Reference):
    cost = None
    counts = None



def run(model_name, max_steps=60_000_000, seed=1):
    d = maindec.DIAGNOSTICS["d2ab-prg0"]
    m, _ = maindec.prepare("d2ab-prg0", seed)
    base = reference_from(m)
    ref = CostedReference.__new__(CostedReference)
    ref.__dict__.update(base.__dict__)
    ref.cost = MODELS[model_name]
    ref.counts = {}
    kl = ref.devices[0]
    steps = 0
    t0 = time.time()
    outcome = "step limit"
    while steps < max_steps:
        r = _step_with_cost(ref)
        steps += 1
        if r.halted:
            if ref.pc in d.continue_halts:
                ref.sr = d.continue_switches
                continue
            if ref.pc in d.pass_halts:
                outcome = f"PASS (end halt at {ref.pc - 1:04o})"
            else:
                outcome = f"HALT at {r.pc:04o} {disassemble(r.ir)} AC={ref.ac:04o}"
            break
    return outcome, steps, ref, kl, time.time() - t0


def _step_with_cost(ref):
    """Apply the model's cost in place of the built-in charge, before controllers see the
    boundary: temporarily replace _finish_boundary."""
    orig_finish = Reference._finish_boundary
    state = {}

    def finish(self):
        if "cls" in state:
            c, auto, builtin = state["cls"]
            self.elapsed_ns += self.cost(c, auto) - builtin
        orig_finish(self)

    if not (ref.interrupt_pending or ref.dma_pending):
        ir = ref.memory[ref.if_][ref.pc]
        c, auto = classify(ir, ref.pc, None, ref.if_)
        indirect = ir >> 9 <= 0o5 and (ir >> 8) & 1
        t = ref.timing
        builtin = t["FETCH"] + (t["DEFER"] if indirect else 0) + t["EXECUTE"]
        state["cls"] = (c, auto, builtin)
        ref.counts[c] = ref.counts.get(c, 0) + 1
    ref._finish_boundary = finish.__get__(ref)
    try:
        return Reference.step(ref)
    finally:
        del ref._finish_boundary


def main():
    names = sys.argv[2:] or list(MODELS)
    for name in names:
        outcome, steps, ref, kl, secs = run(name)
        printed = maindec.text(kl.printed)
        print(f"{name:18s} {outcome:45s} {steps:>10,d} instr  {ref.elapsed_ns / 1e9:8.2f} s sim  "
              f"{len(kl.printed)} chars  ({secs:.0f} s wall)", flush=True)
        print(f"{'':18s} classes {ref.counts}", flush=True)
        print(f"{'':18s} printed tail {printed[-60:]!r}", flush=True)


if __name__ == "__main__":
    main()
