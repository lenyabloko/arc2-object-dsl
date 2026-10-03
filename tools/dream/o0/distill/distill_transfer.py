"""Transfer check (Fable v23a: 'a frame suggested on a task it was not distilled from is the event that matters'):
for every dev task that NEEDS a distilled row from another task (results/o0/distill_b<batch>_reuse.json), the
source reading's frame with that row is fitted on the task's training pairs and checked ONCE on its test input
(separate ledger results/o0/distill_transfer_harness.json, one check per task per transferred family, G87).
usage: python3 distill_transfer.py <batch.json>"""
import glob, itertools, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); O0 = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(O0, '..', '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, O0)
import distill_check as DC, line_check as LC, scale_free as SF
B = json.load(open(sys.argv[1]))
LEDGER = os.path.join(REPO, 'results/o0/distill_transfer_harness.json')
R_ = json.load(open(os.path.join(REPO, f"results/o0/distill_b{B['batch']}_reuse.json")))['items']
need = {}
for o in R_:
    for k in o['needed']: need.setdefault(k, []).append((o['source'], o['sample']))
readings = {}
for gi in range(len(B['groups'])):
    for f in glob.glob(os.path.join(HERE, 'readings', f'g{gi:02d}_s*.json')):
        s = int(re.search(r'_s(\d+)\.json$', f).group(1))
        for R in json.load(open(f)): readings[(R.get('task'), s)] = R
L = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
for k, srcs in sorted(need.items()):
    if k in L: print(k, L[k]['result'], '(ledger)'); continue
    train = LC.task(k)[0]['train']; pooled = {}
    for t, s in srcs:
        R = readings[(t, s)]
        fr = R.get('frame') or {}
        names, _ = DC.register_rows(t, s, R.get('new_rows'))
        spec, opens, _ = DC.spec_of(fr, names)
        for vals in list(itertools.product(*[d for _, d in opens]))[:16] if opens else [()]:
            sp = spec
            for (p, _), v in zip(opens, vals): sp = DC.setp(sp, p, v)
            r = DC.timed(DC.fit_spec, 30, sp, train)
            if r != 'timeout':
                for S in r[0]: pooled.setdefault(SF.key(S), [S, set()])[1].add((t, s))
    T, sol = LC.task(k); preds = []
    for key, (S, sup) in sorted(pooled.items(), key=lambda kv: (-len(kv[1][1]), SF.order_key(kv[1][0]))):
        try: p = [SF.apply(S, q['input']) for q in T['test']]
        except Exception: continue
        if any(v is None for v in p) or p in preds: continue
        preds.append(p)
        if len(preds) == 2: break
    res = 'abstains' if not preds else ('exact' if all(any(p[i] == sol[i] for p in preds) for i in range(len(sol))) else 'wrong')
    L[k] = {'result': res, 'sources': sorted({t for t, _ in srcs}), 'n_fits': len(pooled), 'keys': list(pooled)[:3]}
    json.dump(L, open(LEDGER, 'w'), indent=1)
    print(k, res, 'from', sorted({t for t, _ in srcs}), 'fits', len(pooled), list(pooled)[:1])
