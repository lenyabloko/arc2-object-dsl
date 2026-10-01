"""Self-test for schema_cycle: every node -> draw seeds 0..3 -> fit family on pairs 0-2 -> predict pair 3.

usage: python3 test_cycle.py [-v]      (synthetic only; no ARC files are read)
"""
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_cycle as S  # noqa: E402


def check(node, seeds=(0, 1, 2, 3)):
    pairs = [S.draw(node, s) for s in seeds]
    if any(p is None for p in pairs):
        return "draw_none", 0.0, None
    if [S.draw(node, s) for s in seeds] != pairs:
        return "nondeterministic_draw", 0.0, None
    if any(i == o for i, o in pairs):
        return "out_eq_in", 0.0, None
    t0 = time.time()
    try:
        progs = list(S.family(node)(pairs[:3]))
    except Exception as e:  # pragma: no cover
        return "fam_exception:%s" % type(e).__name__, time.time() - t0, None
    dt = time.time() - t0
    if not progs:
        return "no_program", dt, None
    for name, cost, fn in progs:
        if any(fn(i) != o for i, o in pairs[:3]):
            return "program_misfits_train", dt, name
    pred = progs[0][2](pairs[3][0])
    if pred != pairs[3][1]:
        return ("wrong_prediction" if pred is not None else "test_inapplicable"), dt, progs[0][0]
    return ("slow" if dt > 0.5 else "ok"), dt, progs[0][0]


def main():
    verbose = "-v" in sys.argv
    ns = S.nodes()
    keys = [S.key(n) for n in ns]
    assert len(set(keys)) == len(keys), "duplicate keys"
    by_depth = Counter(S.depth(n) for n in ns)
    reasons = Counter()
    drawn = ok = 0
    tmax = 0.0
    fails = []
    for n in ns:
        r, dt, name = check(n)
        tmax = max(tmax, dt)
        if r != "draw_none":
            drawn += 1
        reasons[r] += 1
        if r == "ok":
            ok += 1
        else:
            fails.append((r, n, name))
    # second synthetic task per node (seeds 4..7), reported for information only
    ok2 = sum(1 for n in ns if check(n, (4, 5, 6, 7))[0] == "ok")
    print("schema %s  nodes %d  (by depth %s)" % (S.SCHEMA, len(ns), dict(sorted(by_depth.items()))))
    print("drawn %d  ok %d  ok(task 2, seeds 4-7) %d  max fit time %.3fs" % (drawn, ok, ok2, tmax))
    print("reasons", dict(reasons))
    if verbose:
        for r, n, name in fails:
            print("  FAIL", r, n, name)


if __name__ == "__main__":
    main()
