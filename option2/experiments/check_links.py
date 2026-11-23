"""Check every relative Markdown link, and its #anchor, in docs/, option2/, and sim/system/README.md.

Run from the repository root: python -I option2/experiments/check_links.py
Anchors follow GitHub's rules: lowercase, punctuation removed, spaces to hyphens, repeats numbered.
"""
import collections
import pathlib
import re
import sys


def anchors(text):
    seen, out, fence = collections.Counter(), set(), False
    for line in text.split("\n"):
        if line.startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"#{1,6}\s+(.*?)\s*$", line)
        if m:
            s = re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", re.sub(r"\[([^]]*)\]\([^)]*\)", r"\1", m[1]).lower()))
            out.add(s if not seen[s] else f"{s}-{seen[s]}")
            seen[s] += 1
    return out


bad = n = 0
pages = [*pathlib.Path("docs").rglob("*.md"), pathlib.Path("sim/system/README.md"), *pathlib.Path("option2").glob("*.md")]
for p in pages:
    for t in re.findall(r"\]\(([^)\s]+)\)", p.read_text(encoding="utf-8")):
        if re.match(r"\w+:", t):
            continue
        n += 1
        path, _, a = t.partition("#")
        q = (p.parent / path) if path else p
        if not q.exists() or (a and q.suffix == ".md" and a not in anchors(q.read_text(encoding="utf-8"))):
            bad += 1
            print("BAD", p.as_posix(), t)
print(n, "links,", bad, "bad")
sys.exit(1 if bad else 0)
