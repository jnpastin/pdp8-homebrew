"""Sweep: option-2 cycle counts, FETCH and DEFER at F ns, EXECUTE at X ns; and a uniform state length."""
import sys
sys.argv = [sys.argv[0], sys.argv[1]] + sys.argv[2:]
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import d2ab_timing as T

def mk(F, X, iot):
    def cost(c, auto):
        d = X if auto else F
        return {"opr": F, "iot": iot, "jmp": F, "jmpi": F + d, "mri": F + X, "mrii": F + d + X}[c]
    return cost

if __name__ != "__main__":
    pass
if __name__ == "__main__":
    mode = sys.argv[2] if len(sys.argv) > 2 else "none"
    if mode == "listing":
        m, _ = T.maindec.prepare("d2ab-prg0", 1)
        ref = T.reference_from(m)
        for a in range(0o2540, 0o2640):
            w = ref.memory[0][a]
            print(f"{a:04o} {w:04o} {T.disassemble(w) if w is not None else ''}")
        sys.exit()
    points = []
    if mode == "exec":
        for X in range(1200, 1701, 50):
            points.append((f"F1200 X{X}", mk(1200, X, 2400)))
    else:
        for U in range(1200, 1401, 25):
            points.append((f"uniform {U}", mk(U, U, 2 * U)))
    for name, cost in points:
        T.MODELS[name] = cost
        outcome, steps, ref, kl, secs = T.run(name)
        print(f"{name:16s} {outcome:40s} {steps:>11,d} instr {ref.elapsed_ns/1e9:7.2f} s sim", flush=True)
