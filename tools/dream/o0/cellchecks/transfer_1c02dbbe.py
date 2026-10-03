"""Transfer check of Len's stamp prior (engine v3: marks / place / rest) on a task he never saw described: 1c02dbbe
(ARC-1, build-failing, not N2, not held-out), the only non-source design task v3 newly fits. Candidates: v3's fitted
situations on its training pairs, distinct test predictions ordered by R(S) (design fit counts, v3), at most 2.
ONE harness check: exact if every test input is matched by a placed prediction; expected outputs never printed."""
import json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import line_check as LC, situation_engine as SE
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
k = '1c02dbbe'
R = Counter(f for v in json.load(open(os.path.join(REPO, 'results/o0/c2_column_fit_v3.json')))['design']['fits'].values() for f in set(v))
T, S_ = LC.task(k)
cands = []
for S in SE.fit(T['train']):
    p = [SE.apply(S, q['input']) for q in T['test']]
    if any(x is None for x in p): continue
    cands.append((-R[SE.situation_key(S)], SE.situation_key(S), p))
cands.sort(key=lambda c: (c[0], c[1])); distinct = []
for c in cands:
    if all(c[2] != d[2] for d in distinct): distinct.append(c)
placed = distinct[:2]
res = 'empty' if not placed else ('exact' if all(any(c[2][i] == S_[i] for c in placed) for i in range(len(S_))) else 'wrong')
out = {'task': k, 'fitted': [c[1] for c in cands], 'distinct_predictions': len(distinct), 'placed': [c[1] for c in placed], 'result': res}
print(json.dumps(out)); json.dump(out, open(os.path.join(REPO, 'results/o0/cellcheck_transfer_1c02dbbe.json'), 'w'), indent=1)
