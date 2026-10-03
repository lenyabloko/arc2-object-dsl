"""Fable v20 B.1, T86': the situation engine (v1, frozen sha f14127b651fe) on the build-failing design tasks it fits
exactly (results/o0/c2_column_fit.json, design.build_failing: 6 tasks on Oct 2).

Per task:
  1. fit(train) gives the situations; apply(S, test input) for each test input (WHY checked, C.3)
  2. candidate rule (v18a, adopted by v20 A.5): distinct predictions ordered by R(S) = the number of design tasks
     the same situation key fits (c2_column_fit.json), ties by key
  3. empty slots only: free slots = 2 - attempts the build already occupies (V34 full run c42 results.jsonl, the
     latest full-build record; 'occupied' / 'kinds')
  4. ONE harness check per task: exact if, for every test input, a placed candidate equals the expected output.
     Expected outputs are compared inside this script and never printed or stored.
Result per task: exact / wrong (placed, not exact) / empty (no prediction, or no free slot).
Go (v20 B.1): >= 3 of 6 exact and 0 wrong. Output: results/o0/t86prime.json
usage: python3 t86prime.py <c42 results.jsonl>"""
import hashlib, json, os, sys
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import line_check as LC
import situation_engine_v1_frozen as SE                  # engine v1 as frozen for T86' (v2 lives in situation_engine.py)

FROZEN = 'f14127b651fe'


def main():
    sha = hashlib.sha256(open(os.path.join(HERE, 'situation_engine_v1_frozen.py'), 'rb').read()).hexdigest()[:12]
    assert sha == FROZEN, 'engine changed since freeze: ' + sha
    C2 = json.load(open(os.path.join(REPO, 'results/o0/c2_column_fit.json')))
    fail = set(json.load(open(os.path.join(REPO, 'results/o0/t80b_population.json'))))
    pop = sorted(k for k in C2['design']['fits'] if k in fail)
    R = Counter(f for v in C2['design']['fits'].values() for f in set(v))
    occ = {}
    for l in open(sys.argv[1]):
        d = json.loads(l)
        if d.get('task') in pop: occ[d['task']] = len(d.get('kinds') or []) if d.get('occupied') else 0
    rows = []
    for k in pop:
        T, S_ = LC.task(k)
        sits = SE.fit(T['train'])
        cands = []                                              # (R(S), key, predictions for every test input)
        for S in sits:
            preds = [SE.apply(S, q['input']) for q in T['test']]
            if any(p is None for p in preds): continue          # WHY failed or nothing applies on some test input
            cands.append((-R[SE.situation_key(S)], SE.situation_key(S), preds))
        cands.sort(key=lambda c: (c[0], c[1]))
        distinct = []
        for c in cands:
            if all(c[2] != d[2] for d in distinct): distinct.append(c)
        free = 2 - occ.get(k, 0)
        placed = distinct[:max(0, free)]
        if not placed: res = 'empty'
        else:
            ok = all(any(c[2][i] == S_[i] for c in placed) for i in range(len(S_)))   # the one harness check
            res = 'exact' if ok else 'wrong'
        rows.append({'task': k, 'situations': [SE.situation_key(S) for S in sits], 'with_prediction': len(cands),
                     'distinct_predictions': len(distinct), 'build_occupied_slots': occ.get(k), 'free_slots': free,
                     'placed': [c[1] for c in placed], 'R_of_placed': [-c[0] for c in placed], 'result': res})
        print(json.dumps(rows[-1]), flush=True)
    n = Counter(r['result'] for r in rows)
    out = {'engine_sha': sha, 'population': len(rows), 'exact': n['exact'], 'wrong': n['wrong'], 'empty': n['empty'],
           'go': n['exact'] >= 3 and n['wrong'] == 0, 'rule': 'v20 B.1: >= 3 of 6 exact and 0 wrong', 'rows': rows,
           'slots_source': 'c42 (V34 full run) results.jsonl'}
    json.dump(out, open(os.path.join(REPO, 'results/o0/t86prime.json'), 'w'), indent=1)
    print({k: v for k, v in out.items() if k != 'rows'})


if __name__ == '__main__':
    main()
