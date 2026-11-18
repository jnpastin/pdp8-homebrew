"""Full-system harness: CPU, memory, front panel, trace, and the command-line runner.

Importing this package puts the sibling simulator packages (sim/cpu/src, sim/memory/src,
sim/reference/src) on the import path, so no install step is needed (standard library only).
"""

import sys
from pathlib import Path

_SIM_ROOT = Path(__file__).resolve().parents[3]
for _package in ("cpu", "memory", "reference"):
    _src = str(_SIM_ROOT / _package / "src")
    if _src not in sys.path:
        sys.path.insert(0, _src)
