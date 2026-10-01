"""Self-test of schema_center_periphery (synthetic only).

For every node: draw seeds 0..3; ok = all four drawn, outputs differ from inputs, and family(node) fitted on pairs
0-2 predicts pair 3 exactly with its first program.  `--specs` runs the same test with every full spec as a node.
"""
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_center_periphery as M  # noqa: E402


def check(node):
    pairs = []
    for sd in range(4):
        try:
            p = M.draw(node, sd)
        except Exception as e:
            return "draw_exception:%s" % type(e).__name__, None, 0.0
        if p is None:
            return "draw_none", None, 0.0
        pairs.append(p)
    for i, o in pairs:
        if i == o:
            return "identity", None, 0.0
        if len(i) > 20 or len(i[0]) > 20 or any(not (0 <= v <= 9) for row in i + o for v in row):
            return "bad_grid", None, 0.0
    fam = M.family(node)
    train = [{"input": i, "output": o} for i, o in pairs[:3]]
    t0 = time.time()
    try:
        first = None
        for name, cost, fn in fam(train):
            first = (name, cost, fn)
            break
    except Exception as e:
        return "family_exception:%s" % type(e).__name__, None, time.time() - t0
    dt = time.time() - t0
    if first is None:
        return "no_program", None, dt
    pred = first[2](pairs[3][0])
    if pred != pairs[3][1]:
        return "wrong_prediction", first[0], dt
    if dt > 0.5:
        return "slow", first[0], dt
    return "ok", first[0], dt


def full_time(node):
    """time to exhaust the family on the drawn train pairs (worst case for the supervisor)"""
    pairs = [M.draw(node, sd) for sd in range(3)]
    if any(p is None for p in pairs):
        return 0.0
    t0 = time.time()
    list(M.family(node)([{"input": i, "output": o} for i, o in pairs]))
    return time.time() - t0


def main():
    if "--specs" in sys.argv:
        ns = [dict((d, v) for d, v in zip(M.DIMS, t) if v is not None) for t in M.SPECS]
        label = "specs"
    else:
        ns = M.nodes()
        label = "nodes"
    reasons = Counter()
    fails = []
    drawn = 0
    tmax = 0.0
    for n in ns:
        r, name, dt = check(n)
        tmax = max(tmax, dt)
        if not r.startswith("draw") and r != "identity":
            drawn += 1
        reasons[r] += 1
        if r != "ok":
            fails.append((r, M.key(n), M.drawn_spec(n), name))
    # canonical keys: key <-> completion set is a bijection; draw is deterministic
    ks = {}
    for n in ns:
        ks.setdefault(M.key(n), set()).add(frozenset(M.completions(n)))
    sets = [next(iter(v)) for v in ks.values()]
    assert all(len(v) == 1 for v in ks.values()) and len(set(sets)) == len(sets), "key not canonical"
    assert all(M.draw(n, 1) == M.draw(n, 1) for n in ns[:50]), "draw not deterministic"
    depth = Counter(len(n) for n in ns)
    print("%s: %d  (by depth %s)  specs: %d" % (label, len(ns), dict(sorted(depth.items())), len(M.SPECS)))
    print("drawn: %d   ok: %d" % (drawn, reasons["ok"]))
    print("reasons:", dict(reasons))
    print("max first-program fit time: %.3fs" % tmax)
    if "--time" in sys.argv:
        worst = max((full_time(n), M.key(n)) for n in ns[:60])
        print("worst exhaustive family time (first 60 nodes): %.3fs %s" % worst)
    for f in fails[: int(os.environ.get("SHOW", "40"))]:
        print("  FAIL", f)


if __name__ == "__main__":
    main()
