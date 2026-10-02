"""Fable v17 P3 where it can count (Oct 2 2026): the design tasks the build still fails.

Population: design tasks in the V32 failure list that no V33-V35 stratum (priors2/3/4, lines, concepts ledgers) already
solves (results/o0/t80b_population.json). Pool per task = every program of the 38 prior families (priors4 first, then
priors3, the build's stratum order) that reproduces all training pairs, at most CAP per family, with non-empty
predictions on every test input. base = the first two distinct predictions in pool order (build semantics, pass@2);
p3 = the same after moving candidates that keep every training invariant (invariants.py) to the front. One harness
check per version (invariants v1); the expected outputs are read only to score, after both picks are made.
Also reported: inertia (one distinct prediction), forced simulation (no candidate keeps the invariants), and how many
tasks have the expected output anywhere in the pool (aggregate only).
Output: results/o0/t80b_design.jsonl.txt. usage: python3 t80b_design.py"""
import importlib.util, json, os, sys, time, glob, signal
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import line_check as LC
import invariants as INV
CAP = 5


def load():
    out = []
    for d in ('priors4', 'priors3'):
        for p in sorted(glob.glob(os.path.join(HERE, d, '*.py'))):
            s = importlib.util.spec_from_file_location('B_%s_%s' % (d, os.path.basename(p)[:-3]), p)
            M = importlib.util.module_from_spec(s); s.loader.exec_module(M); out.append((d, os.path.basename(p)[:-3], M))
    return out


def fitting(M, T, budget=12):
    t0 = time.time()
    try:
        signal.alarm(8); progs = [p for fam in M.FAMILIES for p in fam(T['train'])]; signal.alarm(0)
    except Exception:
        signal.alarm(0); return []
    out = []
    for name, cost, fn in progs:
        if len(out) >= CAP or time.time() - t0 > budget: break
        try:
            signal.alarm(5); ok = all(fn(p['input']) == p['output'] for p in T['train']); signal.alarm(0)
        except Exception:
            signal.alarm(0); ok = False
        if not ok: continue
        try:
            signal.alarm(5); pr = [fn(q['input']) for q in T['test']]; signal.alarm(0)
        except Exception:
            signal.alarm(0); pr = None
        if pr and all(INV.dims(x) for x in pr): out.append((name, pr))
    return out


def pick2(c):
    seen, out = set(), []
    for _, pr in c:
        k = json.dumps(pr)
        if k not in seen: seen.add(k); out.append(pr)
        if len(out) == 2: break
    return out


def main():
    fams = load()
    pop = json.load(open(os.path.join(REPO, 'results/o0/t80b_population.json')))
    out = open(os.path.join(REPO, 'results/o0/t80b_design.jsonl.txt'), 'w')
    for t in pop:
        T, S = LC.task(t)
        pool = []
        for d, n, M in fams:
            pool += [(d + '/' + n + ':' + nm, pr) for nm, pr in fitting(M, T)]
        inv = INV.induce(T['train'])
        keep = lambda pr: all(not INV.check(inv, q['input'], y) for q, y in zip(T['test'], pr))
        ok = [c for c in pool if keep(c[1])]; rest = [c for c in pool if not keep(c[1])]
        b, p = pick2(pool), pick2(ok + rest)
        row = dict(task=t, pool=len(pool), distinct=len({json.dumps(c[1]) for c in pool}), kept=len(ok), forced_sim=bool(pool) and not ok,
                   base2=S in b, p32=S in p, base1=bool(b) and b[0] == S, p31=bool(p) and p[0] == S, in_pool=any(c[1] == S for c in pool))
        out.write(json.dumps(row) + '\n'); out.flush()
    out.close()
    rows = [json.loads(l) for l in open(os.path.join(REPO, 'results/o0/t80b_design.jsonl.txt'))]
    print(json.dumps({'tasks': len(rows), 'answered': sum(r['pool'] > 0 for r in rows), 'open': sum(r['distinct'] > 1 for r in rows),
                      'forced_sim': sum(r['forced_sim'] for r in rows), 'base@2': sum(r['base2'] for r in rows), 'p3@2': sum(r['p32'] for r in rows),
                      'base@1': sum(r['base1'] for r in rows), 'p3@1': sum(r['p31'] for r in rows), 'expected_in_pool': sum(r['in_pool'] for r in rows)}))


if __name__ == '__main__':
    main()
