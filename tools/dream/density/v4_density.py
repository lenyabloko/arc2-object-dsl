"""Fable v21 C.3: chance-fit control for engine v4 on the ARC-GEN density instrument (G74: synthetic, an instrument
only, never evidence). The same 1,330 variants as T80/P3: 5 seeded variants (3 train + 1 test pairs) of each of the 266
fitted ARC-1 tasks (results/o0/t75_fitted_tasks.json; V1 generators only, N2 guard as in t75_density.py).

Per variant, for depth 1 and for depth <= 2: fitted situations in prediction order (scale_free.fit: depth 1 first,
then R, then key); the first one that gives a prediction on the test input is the answer.
  pass@1  the answer equals the test output        wrong  an answer that does not
Go (C.3): pass@1(depth 2) >= pass@1(depth 1) and wrong(depth 2) <= wrong(depth 1) + 2.
Output: results/o0/v4_density_<part>.jsonl.txt, summary on stdout and results/o0/v4_density_summary.json (merge).
usage: [GUARD=1] [TAG=v4] [SEED0=0] [FORMS=map,seq] python3 v4_density.py <variants> <part> <parts>  |  ... merge <parts>"""
import importlib, json, os, signal, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, 'tools/dream/o0'))
import t75_density as D                     # chdir to ARC-GEN, SIGALRM handler, variant()
import scale_free as SF

BUDGET = 30
GUARD = os.environ.get('GUARD') == '1'          # B.4 / G5 margin guard (scale_free.fit_guarded)
TAG = os.environ.get('TAG', 'v4')                # output prefix; seeds offset by SEED0 variants (fresh draws)
SEED0 = int(os.environ.get('SEED0', '0'))
FORMS = os.environ.get('FORMS', 'map,seq')       # which depth-2 forms are allowed


def answer(F, x):
    for S in F:
        try:
            signal.alarm(5); p = SF.apply(S, x); signal.alarm(0)
        except BaseException:
            signal.alarm(0); p = None
        if p is not None: return S, p
    return None, None


def run(V, part, parts):
    tasks = json.load(open(os.path.join(REPO, 'results/o0/t75_fitted_tasks.json')))[part::parts]
    out = open(os.path.join(REPO, 'results/o0/%s_density_%d.jsonl.txt' % (TAG, part)), 'w'); t0 = time.time()
    for i, t in enumerate(tasks):
        mod = importlib.import_module('tasks.task_' + t)
        for v in range(SEED0, SEED0 + V):
            T = D.variant(mod, t, v)
            if T is None: continue
            x, y = T['test'][0]['input'], T['test'][0]['output']
            row = {'task': t, 'v': v}
            for d in (1, 2):
                try:
                    signal.alarm(BUDGET + 10); F = (SF.fit_guarded if GUARD else SF.fit)(T['train'], max_depth=d, budget=BUDGET); signal.alarm(0)
                    F = [S for S in F if SF.depth(S) == 1 or S.get('form') in FORMS.split(',')]
                except BaseException:
                    signal.alarm(0); F = []
                S, p = answer(F, x)
                row['d%d' % d] = {'fits': len(F), 'answered': p is not None, 'exact': p == y if p is not None else False,
                                  'key': SF.key(S) if S else None, 'depth': SF.depth(S) if S else None}
            out.write(json.dumps(row) + '\n'); out.flush()
        if i % 10 == 0: print(json.dumps({'done': i, 'of': len(tasks), 's': round(time.time() - t0)}), flush=True)
    out.close()


def merge(parts):
    rows = []
    for k in range(parts):
        p = os.path.join(REPO, 'results/o0/%s_density_%d.jsonl.txt' % (TAG, k))
        if os.path.exists(p): rows += [json.loads(l) for l in open(p)]
    s = {'variants': len(rows)}
    for d in (1, 2):
        a = [r['d%d' % d] for r in rows]
        s['d%d' % d] = {'answered': sum(x['answered'] for x in a), 'pass@1': sum(x['exact'] for x in a),
                        'wrong': sum(x['answered'] and not x['exact'] for x in a)}
    s['depth2_answers_from_depth2_programs'] = sum(r['d2']['depth'] == 2 for r in rows)
    s['depth2_exact_from_depth2_programs'] = sum(r['d2']['depth'] == 2 and r['d2']['exact'] for r in rows)
    s['go_C3'] = s['d2']['pass@1'] >= s['d1']['pass@1'] and s['d2']['wrong'] <= s['d1']['wrong'] + 2
    json.dump(s, open(os.path.join(REPO, 'results/o0/%s_density_summary.json' % TAG), 'w'), indent=1)
    print(json.dumps(s, indent=1))


if __name__ == '__main__':
    if sys.argv[1] == 'merge': merge(int(sys.argv[2]))
    else: run(int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]))
