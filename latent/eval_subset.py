"""Quick design-set eval for a composition engine (no N2, no half B, no sealed ids are ever touched).
usage: python3 eval_subset.py <engine.py> <baseline.jsonl.txt> [--design] [--regress N] [--ids a,b,c] [--workers 1]
  --design     the 99 design-unsolved tasks of V19 (N1 85 + half A 14, design_unsolved_v19.json)
  --regress N  N tasks the baseline engine solves (deterministic sample, every k-th) -> must stay exact
Prints exact / fit / wrong per subset, NEW (exact now, not in baseline) and LOST (exact in baseline, not now)."""
import json, sys, os, re, signal, importlib.util, argparse
from multiprocessing import Pool
sys.path.insert(0, '/home/claude/work/widen'); sys.path.insert(0, '/home/claude/work/latent')
ap = argparse.ArgumentParser(); ap.add_argument('engine'); ap.add_argument('baseline')
ap.add_argument('--design', action='store_true'); ap.add_argument('--regress', type=int, default=0)
ap.add_argument('--ids', default=''); ap.add_argument('--workers', type=int, default=1); ap.add_argument('--timeout', type=int, default=60)
a = ap.parse_args()
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'
tr = json.load(open(B + 'arc-agi_training_challenges.json')); trs = json.load(open(B + 'arc-agi_training_solutions.json'))
ev = json.load(open(B + 'arc-agi_evaluation_challenges.json')); evs = json.load(open(B + 'arc-agi_evaluation_solutions.json'))
rd = lambda f: [x for x in re.split(r'[,\s]+', open(f).read()) if x]
ALLOWED = set(tr) - set() ; A = rd('/home/claude/work/widen/deval_a.txt')
base = {json.loads(l)['task']: json.loads(l) for l in open(a.baseline)}   # baseline files contain no N2 rows
spec = importlib.util.spec_from_file_location('eng', os.path.abspath(a.engine)); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
class TO(Exception): pass
def one(k):
    ch, so = (tr, trs) if k in tr else (ev, evs)
    def h(*x): raise TO()
    signal.signal(signal.SIGALRM, h); signal.alarm(a.timeout)
    try:
        res = M.SEARCH(ch[k])
        ok = bool(res) and all(any(r['preds'][i] == so[k][i] for r in res[:2]) for i in range(len(so[k])))
        return {'task': k, 'occ': bool(res), 'exact': ok, 'prog': res[0]['program'] if res else None}
    except TO: return {'task': k, 'occ': False, 'exact': False, 'timeout': True}
    except BaseException as e: return {'task': k, 'occ': False, 'exact': False, 'err': repr(e)[:120]}
    finally: signal.alarm(0)
subsets = []
if a.design:
    d = json.load(open('/home/claude/work/latent/design_unsolved_v19.json')); subsets.append(('design', d['N1_unsolved_v19'] + d['halfA_unsolved_v19']))
if a.regress:
    sol = sorted(t for t, r in base.items() if r['exact']); k = max(1, len(sol) // a.regress); subsets.append(('regress', sol[::k][:a.regress]))
if a.ids: subsets.append(('ids', a.ids.split(',')))
for name, ids in subsets:
    ids = [t for t in ids if t in base]            # only ids present in a baseline (never N2)
    with Pool(a.workers) as p: R = p.map(one, ids, chunksize=1)
    e = sum(r['exact'] for r in R); o = sum(r['occ'] for r in R); w = sum(r['occ'] and not r['exact'] for r in R)
    new = sorted(r['task'] for r in R if r['exact'] and not base[r['task']]['exact'])
    lost = sorted(r['task'] for r in R if not r['exact'] and base[r['task']]['exact'])
    print(f"{name}: n={len(R)} exact={e} fit={o} wrong={w} NEW={new} LOST={lost} timeouts={sum(1 for r in R if r.get('timeout'))} errors={sum(1 for r in R if r.get('err'))}")
    for r in R:
        if r['exact'] or r.get('err'): print('  ', r['task'], 'exact' if r['exact'] else 'ERR ' + r.get('err', ''), r.get('prog'))
