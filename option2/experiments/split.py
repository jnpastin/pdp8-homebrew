import sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import d2ab_timing as T
from sweep import mk
for F, X in [(1250, 1300), (1300, 1200), (1225, 1350), (1250, 1250)]:
    name = f"F{F} X{X}"
    T.MODELS[name] = mk(F, X, F + X)
    outcome, steps, ref, kl, secs = T.run(name)
    print(f"{name:12s} 2F+X={2*F+X}  {outcome}", flush=True)
