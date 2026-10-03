"""Fable v19 C.2 / OQ-19.2 diagnostic: column induction by fit (situation_engine.fit), training pairs only.

  t83        the 38 T83 lines: does a column fit, and is the parsed WHAT's column among the fitted ones?
  design     every design task (ARC-1 training minus N2, plus the 99): how many get at least one fitted situation,
             per column; the same restricted to the 153 build-failing design tasks (results/o0/t80b_population.json)
  heldout    the 14 T86 tasks (results/o0/t86_heldout.json): which situations fit their training pairs (placement, B.3)
Nothing reads a test output; there is no harness check here. Output: results/o0/c2_column_fit.json
usage: python3 c2_column_fit.py [t83|design|heldout]..."""
import json, os, signal, sys, time
from collections import Counter
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import line_check as LC
import situation_engine as SE

WHAT2COL = {'tile_scale': 'tile', 'copy_stamp': 'stamp', 'decorate': 'stamp', 'draw_line': 'extend', 'mirror_complete': 'mirror',
            'recolour': 'recolour', 'delete': 'recolour', 'fill': 'fill', 'complete_shape': 'fill', 'move': 'move', 'extract': 'extract'}


class TO(Exception): pass


def _alarm(*a): raise TO()


def fit_one(k, budget=25):
    signal.signal(signal.SIGALRM, _alarm)
    t = LC.task(k)
    if t is None: return k, None
    s = time.time()
    try:
        signal.alarm(budget); F = SE.fit(t[0]['train']); signal.alarm(0)
    except TO:
        return k, {'timeout': True, 'fits': []}
    except Exception as e:
        signal.alarm(0); return k, {'error': repr(e)[:80], 'fits': []}
    return k, {'fits': [SE.situation_key(S) for S in F], 'situations': F, 's': round(time.time() - s, 2)}


def run(keys, procs=2):
    with Pool(procs) as P: return dict(P.map(fit_one, keys, chunksize=4))


def main():
    out_p = os.path.join(REPO, os.environ.get('C2_OUT', 'results/o0/c2_column_fit.json'))
    R = json.load(open(out_p)) if os.path.exists(out_p) else {}
    modes = sys.argv[1:] or ['t83', 'design', 'heldout']
    if 't83' in modes:
        P = json.load(open(os.path.join(REPO, 'results/o0/t83_parsed.json')))
        res = run([x['card'] for x in P])
        rows = []
        for x in P:
            r = res.get(x['card']) or {'fits': []}
            cols = sorted({f.split('(')[0] for f in r['fits']})
            want = WHAT2COL.get(x['WHAT'])
            rows.append({'card': x['card'], 'parsed_WHAT': x['WHAT'], 'parsed_col': want, 'fitted_cols': cols, 'fits': r['fits'],
                         'agree': bool(want and want in cols), 'timeout': r.get('timeout', False), 'readable': r is not None})
        R['t83'] = {'n': len(rows), 'with_fitted_column': sum(bool(r['fitted_cols']) for r in rows),
                    'parsed_col_among_fitted': sum(r['agree'] for r in rows),
                    'parsed_has_col': sum(bool(r['parsed_col']) for r in rows), 'rows': rows}
        print('t83', {k: v for k, v in R['t83'].items() if k != 'rows'}, flush=True)
    if 'design' in modes:
        keys = [x for x in sorted(LC.tr) if x not in LC.N2] + sorted(LC.D99)
        held = set(json.load(open(os.path.join(REPO, 'results/o0/t86_heldout.json'))))
        keys = [k for k in keys if k not in held]
        res = run(keys)
        fail = set(json.load(open(os.path.join(REPO, 'results/o0/t80b_population.json'))))
        def summ(ks):
            ks = [k for k in ks if res.get(k) is not None]
            per = Counter(c for k in ks for c in {f.split('(')[0] for f in res[k]['fits']})
            return {'n': len(ks), 'with_fit': sum(bool(res[k]['fits']) for k in ks), 'timeouts': sum(bool(res[k].get('timeout')) for k in ks),
                    'per_column': dict(per.most_common())}
        R['design'] = {'all': summ(keys), 'build_failing': summ([k for k in keys if k in fail]),
                       'fits': {k: res[k]['fits'] for k in keys if res.get(k) and res[k]['fits']}}
        print('design', R['design']['all'], '\nbuild-failing', R['design']['build_failing'], flush=True)
    if 'heldout' in modes:
        held = sorted(json.load(open(os.path.join(REPO, 'results/o0/t86_heldout.json'))))
        held = [k for k in held if k not in os.environ.get('EXCLUDE', '').split(',')]   # v20 A.4: dd2401ed excluded (Len has seen it)
        res = run(held)
        R['heldout'] = {k: {'fits': (res[k] or {}).get('fits', []), 'situations': (res[k] or {}).get('situations', []),
                            'timeout': (res[k] or {}).get('timeout', False)} for k in held}
        print('heldout', {k: v['fits'] for k, v in R['heldout'].items()}, flush=True)
    R['time'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
    json.dump(R, open(out_p, 'w'), indent=1)


if __name__ == '__main__':
    main()
