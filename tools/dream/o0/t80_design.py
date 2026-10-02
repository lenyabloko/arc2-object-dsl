"""Fable v17 T80 as defined (Oct 2 2026): the same 38 prior families, with the P3 open-slot filler, before vs after.

For every design task (ARC-1 training minus N2, plus the 99) and every family: all programs of the family that
reproduce the training pairs (at most CAP, in yield order) with their predictions on the test inputs.
  base  the harness rule: the first fitting program (an empty prediction counts as a wrong answer, as in prior_check)
  p3    G80: the choice among fitting programs is made by P3 -- candidates whose predictions keep every training
        invariant (invariants.py v1) come first (relational order = the family's own role-first yield order, then IRI);
        if none keeps them (forced simulation) the base order stands; empty predictions are never chosen while a
        non-empty one exists
Logged per (family, task): fitting count, distinct predictions (1 = inertia), forced_sim, base/p3 exact, base/p3 answer.
T80 reads: on the 60 T72 size/mixed design cases, flips to exact; over the whole population, new wrong (base exact,
p3 not). One harness check per version (P3 v1). Output: results/o0/t80_<dir>.jsonl.txt.
usage: python3 t80_design.py <dir>"""
import importlib.util, json, os, sys, time, glob, signal
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import line_check as LC
import invariants as INV
CAP = 8


def fits(M, T, budget=15):
    t0 = time.time()
    try:
        signal.alarm(8); progs = [p for fam in M.FAMILIES for p in fam(T['train'])]; signal.alarm(0)
    except Exception:
        signal.alarm(0); return []
    out = []
    for name, cost, fn in progs:
        if len(out) >= CAP or time.time() - t0 > budget: break
        try:
            signal.alarm(10); ok = all(fn(p['input']) == p['output'] for p in T['train']); signal.alarm(0)
        except Exception:
            signal.alarm(0); ok = False
        if not ok: continue
        try:
            signal.alarm(10); pr = [fn(q['input']) for q in T['test']]; signal.alarm(0)
        except Exception:
            signal.alarm(0); pr = None
        out.append((name, pr))
    return out


def main():
    d = sys.argv[1]
    keys = [x for x in sorted(LC.tr) if x not in LC.N2] + sorted(LC.D99)
    out = open(os.path.join(REPO, 'results/o0/t80_%s.jsonl.txt' % d), 'w')
    for p in sorted(glob.glob(os.path.join(HERE, d, '*.py'))):
        c = os.path.basename(p)[:-3]
        s = importlib.util.spec_from_file_location('T80_%s_%s' % (d, c), p); M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
        mem = set(getattr(M, 'MEMBERS', []))
        for k in keys:
            t = LC.task(k)
            if t is None: continue
            T, S = t
            F = fits(M, T)
            if not F: continue
            inv = INV.induce(T['train'])
            good = lambda pr: pr is not None and all(INV.dims(y) for y in pr) and all(not INV.check(inv, q['input'], y) for q, y in zip(T['test'], pr))
            nonempty = [f for f in F if f[1] is not None and all(INV.dims(y) for y in f[1])]
            keep = [f for f in nonempty if good(f[1])]
            base = F[0][1]
            p3 = (keep or nonempty or F)[0][1]
            row = dict(dir=d, family=c, task=k, member=k in mem, fitting=len(F), distinct=len({json.dumps(f[1]) for f in F}),
                       forced_sim=bool(nonempty) and not keep, base_exact=base == S, p3_exact=p3 == S,
                       base_answer=base is not None, p3_answer=p3 is not None, p3_changed=json.dumps(p3) != json.dumps(base))
            out.write(json.dumps(row) + '\n')
        out.flush()
    out.close()


if __name__ == '__main__':
    main()
