"""Self-test for schema_symmetry: draw seeds 0..3 per node, fit family on
pairs 0-2, predict pair 3.  Synthetic only."""
import collections
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_symmetry as S  # noqa: E402


def check(node):
    pairs = []
    for s in range(4):
        p = S.draw(node, s)
        if p is None:
            return "draw_none", None, 0.0
        pairs.append(p)
    if any(x == y for x, y in pairs):
        return "out_eq_in", None, 0.0
    for x, y in pairs:
        for g in (x, y):
            if len(g) > 20 or len(g[0]) > 20 or \
                    any(not (0 <= v <= 9) for row in g for v in row):
                return "bad_grid", None, 0.0
    t0 = time.time()
    progs = list(S.family(node)(pairs[:3]))
    dt = time.time() - t0
    if dt > 0.5:
        return "slow", None, dt
    if not progs:
        return "no_program", None, dt
    name, cost, fn = progs[0]
    if fn(pairs[3][0]) == pairs[3][1]:
        return "ok", name, dt
    if any(f(pairs[3][0]) == pairs[3][1] for _, _, f in progs[1:]):
        return "wrong_top1", name, dt
    return "wrong_pred", name, dt


def main():
    verbose = "-v" in sys.argv
    ns = S.nodes()
    keys = [S.key(n) for n in ns]
    assert len(set(keys)) == len(keys), "duplicate keys"
    reasons = collections.Counter()
    drawn = ok = 0
    tmax = 0.0
    fails = []
    for n in ns:
        why, name, dt = check(n)
        tmax = max(tmax, dt)
        reasons[why] += 1
        if why != "draw_none":
            drawn += 1
        if why == "ok":
            ok += 1
        else:
            fails.append((why, {k: v for k, v in n.items()}, name))
    print(f"nodes={len(ns)} drawn={drawn} ok={ok} max_fit_s={tmax:.3f}")
    print("reasons:", dict(reasons))
    if verbose:
        for f in fails:
            print(" ", f)


if __name__ == "__main__":
    main()
