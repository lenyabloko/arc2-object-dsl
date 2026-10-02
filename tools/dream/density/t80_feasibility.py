"""Fable v17 T80 preparation (Oct 2 2026): on the ARC-GEN density cases only (design-side instrument, G74), is the
expected test output among the predictions of the programs that fit the training pairs?

For each wrong non-source or member-miss case of the T72' rows (label size / mixed / anchor_* / on_stop_* / shift),
every program of the family is checked against the training pairs (budget per case); the distinct test predictions of
the fitting programs are grouped. Reported: n fitting programs, n distinct predictions (n > 1 = an OPEN choice exists),
and whether one of them is the expected output (selection alone could fix it) or none is (a new value is needed).
Output: results/o0/t80_feasibility.jsonl.txt and a summary on stdout.
usage: python3 t80_feasibility.py [max_cases_per_family_label]"""
import importlib, json, glob, os, sys, time
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import t75_density as D

FAMS = ('kronecker_tiling', 'learned_key_table', 'stamp_stencil_at_anchors', 'ray_cast_to_stop', 'mirror_symmetry_completion')
LABELS = ('size', 'mixed', 'anchor_other', 'anchor_inter', 'anchor_midpoint', 'on_stop_paint', 'on_stop_turn', 'shift')


def key(g): return json.dumps(g) if isinstance(g, list) else None


def all_fits(M, train, test_in, budget=40, gen_budget=10, cap=400):
    t0 = time.time()
    try:
        D.signal.alarm(gen_budget); progs = [p for fam in M.FAMILIES for p in fam(train)]; D.signal.alarm(0)
    except BaseException:
        D.signal.alarm(0); return None
    fits = []
    for i, (name, cost, fn) in enumerate(progs[:cap]):
        if time.time() - t0 > budget: break
        try:
            D.signal.alarm(5); ok = all(fn(p['input']) == p['output'] for p in train); D.signal.alarm(0)
        except BaseException:
            D.signal.alarm(0); ok = False
        if ok:
            try:
                D.signal.alarm(5); pr = fn(test_in); D.signal.alarm(0)
            except BaseException:
                D.signal.alarm(0); pr = None
            fits.append((i, name, pr))
    return fits, len(progs)


def main():
    cap = int(sys.argv[1]) if len(sys.argv) > 1 else 15
    fams = {(d, n): M for d, n, M, _ in D.families()}
    rows = []
    for p in sorted(glob.glob(os.path.join(REPO, 'results/o0/t72p_density_*.jsonl.txt'))):
        rows += [json.loads(l) for l in open(p)]
    sel = defaultdict(list)
    for r in rows:
        if r['family'] in FAMS and r['label'] in LABELS: sel[(r['family'], r['label'])].append(r)
    cases = [r for k in sorted(sel) for r in sel[k][:cap]]
    out = open(os.path.join(REPO, 'results/o0/t80_feasibility.jsonl.txt'), 'w')
    for r in cases:
        mod = importlib.import_module('tasks.task_' + r['task'])
        T = D.variant(mod, r['task'], r['v'])
        if T is None: continue
        exp = T['test'][0]['output']
        res = all_fits(fams[(r['dir'], r['family'])], T['train'], T['test'][0]['input'])
        if res is None: continue
        fits, nprog = res
        preds = Counter(key(pr) for _, _, pr in fits)
        first = key(fits[0][2]) if fits else None
        hit = [n for i, n, pr in fits if pr == exp]
        row = dict(task=r['task'], v=r['v'], dir=r['dir'], family=r['family'], label=r['label'], programs=nprog, fitting=len(fits),
                   distinct=len(preds), expected_among=bool(hit), first_hit=hit[0] if hit else None, first=fits[0][1] if fits else None)
        out.write(json.dumps(row) + '\n'); out.flush()
    out.close()
    rows = [json.loads(l) for l in open(os.path.join(REPO, 'results/o0/t80_feasibility.jsonl.txt'))]
    s = defaultdict(Counter)
    for r in rows:
        k = (r['family'], r['label'])
        s[k]['n'] += 1; s[k]['open'] += r['distinct'] > 1; s[k]['expected_among'] += r['expected_among']
    for k in sorted(s): print(k, dict(s[k]))
    print('total', len(rows), 'open', sum(r['distinct'] > 1 for r in rows), 'expected among fits', sum(r['expected_among'] for r in rows))


if __name__ == '__main__':
    main()
