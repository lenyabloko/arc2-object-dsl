"""Self-test of schema_path: for every node draw seeds 0..3, fit family(node) on pairs 0-2, predict pair 3.
usage: python3 test_path.py [-v]   (synthetic only; no ARC files are read)"""
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_path as S  # noqa: E402


def check(node):
    pairs = [S.draw(node, s) for s in range(4)]
    if any(p is None for p in pairs):
        return "draw_failed", None, 0.0
    if any(i == o for i, o in pairs):
        return "no_change", None, 0.0
    train = [{"input": i, "output": o} for i, o in pairs[:3]]
    t0 = time.time()
    try:
        progs = list(S.family(node)(train))
    except Exception as e:  # pragma: no cover
        return "exception:%s" % type(e).__name__, None, time.time() - t0
    dt = time.time() - t0
    if not progs:
        return "no_program", None, dt
    name, cost, fn = progs[0]
    for _, _, f in progs:
        for p in train:
            if f(p["input"]) != p["output"]:
                return "yield_not_fitting", name, dt
    pred = fn(pairs[3][0])
    if pred != pairs[3][1]:
        return "wrong_prediction", name, dt
    if dt > 0.5:
        return "slow", name, dt
    return "ok", name, dt


def main():
    verbose = "-v" in sys.argv
    t0 = time.time()
    ns = S.nodes()
    keys = [S.key(n) for n in ns]
    assert len(set(keys)) == len(keys), "duplicate keys"
    res = Counter()
    drawn = 0
    times = []
    fails = []
    for n, k in zip(ns, keys):
        why, name, dt = check(n)
        times.append(dt)
        res[why.split(":")[0]] += 1
        if why not in ("draw_failed",):
            drawn += 1
        if why != "ok":
            fails.append((k, why, name, n))
        if verbose:
            print("%-18s %.3fs %s %s" % (why, dt, k, name or ""))
    print("nodes", len(ns), "drawn", drawn, "ok", res["ok"])
    print("failures by kind", dict((k, v) for k, v in res.items() if k != "ok"))
    print("family time max %.3fs mean %.3fs   total %.1fs" % (max(times), sum(times) / len(times), time.time() - t0))
    for k, why, name, n in fails:
        print("FAIL", why, n, "|", name or "")


if __name__ == "__main__":
    main()
