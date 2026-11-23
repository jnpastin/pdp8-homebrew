"""Compare two generated JSON artifacts, ignoring source line references, so only content changes show.

Usage: python -I option2/experiments/json_content_diff.py OLD.json NEW.json [LIMIT]
Typical use: copy rom/microcode/v2 aside, run the pipeline, then diff each file against the copy.
"""
import json
import sys

old, new = (json.load(open(p, encoding="utf-8")) for p in sys.argv[1:3])
limit = int(sys.argv[3]) if len(sys.argv) > 3 else 60
IGNORE = {"line", "lines", "line_start", "line_end", "start_line", "end_line"}
out = []


def key_of(x):
    if isinstance(x, dict):
        for k in ("id", "name", "micro_operation", "field", "address", "heading"):
            if k in x and isinstance(x[k], (str, int)):
                return f"{k}={x[k]}"
    return None


def walk(a, b, path):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in IGNORE:
                continue
            if k not in a:
                out.append(f"+ {path}.{k} = {json.dumps(b[k])[:200]}")
            elif k not in b:
                out.append(f"- {path}.{k} = {json.dumps(a[k])[:200]}")
            else:
                walk(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        ka, kb = [key_of(x) for x in a], [key_of(x) for x in b]
        if all(ka) and all(kb) and len(set(ka)) == len(ka) and len(set(kb)) == len(kb):
            da, db = dict(zip(ka, a)), dict(zip(kb, b))
            for k in ka:
                if k not in db:
                    out.append(f"- {path}[{k}] = {json.dumps(da[k])[:300]}")
            for k in kb:
                if k not in da:
                    out.append(f"+ {path}[{k}] = {json.dumps(db[k])[:300]}")
                else:
                    walk(da[k], db[k], f"{path}[{k}]")
        elif len(a) == len(b):
            for i, (x, y) in enumerate(zip(a, b)):
                walk(x, y, f"{path}[{i}]")
        else:
            sa = {json.dumps(strip(x), sort_keys=True) for x in a}
            sb = {json.dumps(strip(x), sort_keys=True) for x in b}
            for x in sorted(sa - sb):
                out.append(f"- {path}[] {x[:300]}")
            for x in sorted(sb - sa):
                out.append(f"+ {path}[] {x[:300]}")
    elif a != b:
        out.append(f"~ {path}: {json.dumps(a)[:150]} -> {json.dumps(b)[:150]}")


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in IGNORE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


walk(old, new, "")
print(f"{len(out)} differences")
for line in out[:limit]:
    print(" ", line)
