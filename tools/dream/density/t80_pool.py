"""Fable v17 P3 on the ARC-GEN density set (design-side instrument only, G74; Oct 2 2026).

Pool = every program of the 38 prior families (priors4 families first, then priors3, as the build orders L_priors4 before
L_priors3) that reproduces the 3 training pairs of a variant, at most CAP per family, with its non-empty prediction on
the test input. Two selections over the same pool:
  base   build semantics: the first two distinct predictions in pool order (pass@1 = the first)
  p3     the same, after moving candidates that keep every training invariant (invariants.py) to the front (stable);
         when no candidate keeps them all (forced simulation) the order is unchanged
Logged per variant: pool size, distinct predictions (1 = inertia: nothing open), forced-sim, and for both selections
exact@1, exact@2, answered. Output: results/o0/t80_pool.jsonl.txt + summary.
usage: python3 t80_pool.py <variants> <part> <parts>"""
import importlib, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, 'tools/dream/o0'))
import t75_density as D
import invariants as INV

CAP = 5


def fitting(M, train, test_in, budget=12):
    t0 = time.time()
    try:
        D.signal.alarm(8); progs = [p for fam in M.FAMILIES for p in fam(train)]; D.signal.alarm(0)
    except BaseException:
        D.signal.alarm(0); return []
    out = []
    for name, cost, fn in progs:
        if len(out) >= CAP or time.time() - t0 > budget: break
        try:
            D.signal.alarm(5); ok = all(fn(p['input']) == p['output'] for p in train); D.signal.alarm(0)
        except BaseException:
            D.signal.alarm(0); ok = False
        if not ok: continue
        try:
            D.signal.alarm(5); pr = fn(test_in); D.signal.alarm(0)
        except BaseException:
            D.signal.alarm(0); pr = None
        if INV.dims(pr): out.append((name, pr))
    return out


def pick2(cands):
    seen, out = set(), []
    for name, pr in cands:
        k = json.dumps(pr)
        if k in seen: continue
        seen.add(k); out.append(pr)
        if len(out) == 2: break
    return out


def main():
    V, part, parts = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    fams = D.families()
    order = [f for f in fams if f[0] == 'priors4'] + [f for f in fams if f[0] == 'priors3']
    tasks = json.load(open(os.path.join(REPO, 'results/o0/t75_fitted_tasks.json')))[part::parts]
    members = set().union(*[m for _, _, _, m in fams])
    out = open(os.path.join(REPO, 'results/o0/t80_pool_%d.jsonl.txt' % part), 'w')
    t0 = time.time()
    for i, t in enumerate(tasks):
        mod = importlib.import_module('tasks.task_' + t)
        for v in range(V):
            T = D.variant(mod, t, v)
            if T is None: continue
            x, y = T['test'][0]['input'], T['test'][0]['output']
            pool = []
            for d, n, M, mem in order:
                pool += [(d + '/' + n + ':' + name, pr) for name, pr in fitting(M, T['train'], x)]
            inv = INV.induce(T['train'])
            ok = [c for c in pool if not INV.check(inv, x, c[1])]
            rest = [c for c in pool if INV.check(inv, x, c[1])]
            b, p = pick2(pool), pick2(ok + rest)
            row = dict(task=t, v=v, member=t in members, pool=len(pool), distinct=len({json.dumps(c[1]) for c in pool}),
                       kept=len(ok), forced_sim=bool(pool) and not ok, inv=sorted(k for k in inv if inv[k]),
                       base1=bool(b) and b[0] == y, base2=y in b, p31=bool(p) and p[0] == y, p32=y in p, answered=bool(pool))
            out.write(json.dumps(row) + '\n')
        out.flush()
        if i % 20 == 0: print(json.dumps({'done': i, 'of': len(tasks), 's': round(time.time() - t0)}), flush=True)
    out.close()


if __name__ == '__main__':
    main()
