"""Feasibility: near-miss (leave-one-pair-out) programs as best-effort attempts for tasks with no verified program.
Design splits only (ARC1-origin, N1, half A); N2 / half B / sealed are never touched here."""
import json, sys, os, re, signal
from multiprocessing import Pool
sys.path.insert(0, '/home/claude/work/widen/probe_v20')
import gdsl
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
tr = json.load(open(B + 'arc-agi_training_challenges.json')); trs = json.load(open(B + 'arc-agi_training_solutions.json'))
ev = json.load(open(B + 'arc-agi_evaluation_challenges.json')); evs = json.load(open(B + 'arc-agi_evaluation_solutions.json'))
rows = [json.loads(l) for l in open('c20_v20.jsonl.txt')]          # no N2 rows in this file
uns = [r['task'] for r in rows if not r['exact']]
def acc(a, b):
    if a is None or len(a) != len(b) or len(a[0]) != len(b[0]): return 0.0
    return sum(x == y for ra, rb in zip(a, b) for x, y in zip(ra, rb)) / (len(b) * len(b[0]))
class TO(Exception): pass
THR = float(os.environ.get('NM_THR', '0.0'))
def one(t):
    ch, so = (tr, trs) if t in tr else (ev, evs); task = ch[t]; P = task['train']; k = len(P)
    def h(*a): raise TO()
    signal.signal(signal.SIGALRM, h); signal.alarm(150)
    cand = {}
    try:
        subsets = range(k) if k == 2 else []
        for i in subsets:
            sub = {'train': P[:i] + P[i + 1:], 'test': [{'input': P[i]['input']}] + task['test']}
            for r in gdsl.search(sub, max_programs=3, allow2=False):
                a = acc(r['preds'][0], P[i]['output']); key = json.dumps(r['preds'][1:])
                c = cand.setdefault(key, {'votes': 0, 'acc': 0.0, 'cost': r['cost'], 'prog': r['program'], 'preds': r['preds'][1:]})
                c['votes'] += 1; c['acc'] = max(c['acc'], a)
    except TO:
        pass
    finally:
        signal.alarm(0)
    ranked = sorted([c for c in cand.values() if c['acc'] >= THR], key=lambda c: (-c['votes'], -c['acc'], c['cost'], c['prog']))[:2]
    ok = bool(ranked) and all(any(c['preds'][j] == so[t][j] for c in ranked) for j in range(len(so[t])))
    return {'task': t, 'k': k, 'n_cand': len(cand), 'accs': sorted([round(c['acc'],3) for c in cand.values()], reverse=True)[:3], 'exact_any': [c['acc'] for c in cand.values() if all(c['preds'][j] == so[t][j] for j in range(len(so[t])))], 'exact': ok, 'top': [(c['prog'], c['votes'], round(c['acc'], 3)) for c in ranked]}
if __name__ == '__main__':
    with Pool(2) as p: R = p.map(one, uns, chunksize=2)
    open('nearmiss_k2_results.jsonl', 'w').write('\n'.join(json.dumps(r) for r in R))
    rd = lambda f: set(x for x in re.split(r'[,\s]+', open(f).read()) if x)
    N1 = rd('/home/claude/work/latent/novel_N1.txt'); A = rd('/home/claude/work/widen/deval_a.txt')
    for name, sel in (('ARC1', lambda t: t not in N1 and t not in A), ('N1', lambda t: t in N1), ('halfA', lambda t: t in A)):
        rr = [r for r in R if sel(r['task'])]
        print(name, 'unsolved', len(rr), 'k>=3', sum(r['k'] >= 3 for r in rr), 'with near-miss', sum(r['n_cand'] > 0 for r in rr),
              'EXACT', sum(r['exact'] for r in rr), [r['task'] for r in rr if r['exact']])
