"""Self-test of the LINK schema module: for every node draw seeds 0..3, fit family on pairs 0-2, predict pair 3.
usage: python3 test_link.py [-v]"""
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import schema_link as L  # noqa: E402


def run_node(n):
    pairs = []
    for s in range(4):
        d = L.draw(n, s)
        if d is None:
            return 'draw', 0.0
        pairs.append(d)
    if any(i == o for i, o in pairs):
        return 'nochange', 0.0
    if any(len(i) > 20 or len(i[0]) > 20 or any(not 0 <= v <= 9 for r in i + o for v in r) for i, o in pairs):
        return 'badgrid', 0.0
    t0 = time.time()
    first = next(L.family(n)(pairs[:3]), None)
    dt = time.time() - t0
    if first is None:
        return 'nofit', dt
    pred = first[2](pairs[3][0])
    if dt > 0.5:
        return 'slow', dt
    if pred is None:
        return 'noapply', dt
    if pred != pairs[3][1]:
        return 'wrong', dt
    return 'ok', dt


def main():
    verbose = '-v' in sys.argv
    t0 = time.time()
    ns = L.nodes()
    keys = [L.key(n) for n in ns]
    assert len(set(keys)) == len(keys), 'duplicate keys'
    res = Counter()
    drawn = 0
    fails = []
    tmax = 0.0
    for n in ns:
        r, dt = run_node(n)
        tmax = max(tmax, dt)
        res[r] += 1
        if r != 'draw':
            drawn += 1
        if r != 'ok':
            fails.append((r, L.key(n), L._task(n)['cfg']))
    print('nodes', len(ns), 'drawn', drawn, 'ok', res['ok'], 'max_fit_s %.3f' % tmax, 'total_s %.1f' % (time.time() - t0))
    print('failures by kind', dict((k, v) for k, v in res.items() if k != 'ok'))
    if verbose:
        for f in fails:
            print('  ', f)
    return fails


if __name__ == '__main__':
    main()
