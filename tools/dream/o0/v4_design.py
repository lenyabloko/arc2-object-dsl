"""Engine v4 on design (Fable v21 B.2 (i) / B.3): fits at depth 1 vs depth 2, and R(part). Training pairs only; no
harness check, no test output.

Population before the v4 freeze ('dev'): design (ARC-1 training minus N2, plus the 99) minus the 14 T86 tasks minus
every task of the sealed draws (H_loose and the fallback H2, /home/claude/work/sealed/t90_H.json), so that the T90
population stays untouched until the placement run. Only counts and keys of dev tasks are written; no H id is read
into the output.
modes:
  depth1   fit depth 1 on dev; writes results/o0/v4_R_depth1.json (R(key) = dev tasks a key fits; the enumeration order
           of v21a B.1) and results/o0/v4_design_depth1.json
  depth2   fit depth <= 2 on dev (budget per task); writes results/o0/v4_design_depth2.json with per-task keys (dev only),
           depth-1 vs depth-2 counts (all / build-failing) and R(part) with the source task excluded (G85)
usage: python3 v4_design.py depth1|depth2 [procs]"""
import json, os, signal, sys, time
from collections import Counter
from multiprocessing import Pool
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
import line_check as LC

BUDGET = 45


class TO(Exception): pass
def _alarm(*a): raise TO()


def population():
    held = set(json.load(open(os.path.join(REPO, 'results/o0/t86_heldout.json'))))
    S = json.load(open('/home/claude/work/sealed/t90_H.json'))
    sealed = set(S.get('H', [])) | set(S.get('H_loose', [])) | set(S.get('H2_fallback', []))
    keys = [k for k in sorted(LC.tr) if k not in LC.N2] + sorted(LC.D99)
    return [k for k in keys if k not in held and k not in sealed], len(sealed)


def work(arg):
    k, max_depth = arg
    import scale_free as SF
    signal.signal(signal.SIGALRM, _alarm)
    t = LC.task(k)
    if t is None: return k, None
    s = time.time()
    try:
        signal.alarm(BUDGET + 15); F = SF.fit(t[0]['train'], max_depth=max_depth, budget=BUDGET); signal.alarm(0)
    except TO: return k, {'timeout': True, 'fits': [], 'parts': []}
    except Exception as e:
        signal.alarm(0); return k, {'error': repr(e)[:80], 'fits': [], 'parts': []}
    return k, {'fits': [SF.key(S) for S in F], 'depths': [SF.depth(S) for S in F],
               'parts': sorted(set().union(*[SF.parts(S) for S in F])) if F else [], 's': round(time.time() - s, 1)}


def main():
    mode = sys.argv[1]; procs = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    pop, n_sealed = population()
    fail = set(json.load(open(os.path.join(REPO, 'results/o0/t80b_population.json'))))
    md = 1 if mode == 'depth1' else 2
    t0 = time.time()
    with Pool(procs) as P: res = dict(P.map(work, [(k, md) for k in pop], chunksize=2))
    res = {k: v for k, v in res.items() if v is not None}
    def count(ks, d):
        return sum(any(x <= d for x in res[k].get('depths', [])) for k in ks)
    bf = [k for k in res if k in fail]
    summ = {'population': 'dev = design - T86 14 - sealed draws (%d sealed tasks not touched)' % n_sealed, 'n': len(res),
            'timeouts': sum(bool(v.get('timeout')) for v in res.values()), 'minutes': round((time.time() - t0) / 60, 1),
            'fit_depth1': count(res, 1), 'build_failing_n': len(bf), 'build_failing_fit_depth1': count(bf, 1)}
    if md == 2:
        summ.update({'fit_depth_le2': count(res, 2), 'build_failing_fit_depth_le2': count(bf, 2),
                     'only_depth2': sum(bool(v.get('depths')) and min(v['depths']) == 2 for v in res.values()),
                     'build_failing_only_depth2': sum(bool(res[k].get('depths')) and min(res[k]['depths']) == 2 for k in bf)})
        import scale_free as SF
        Rp = Counter()
        for k, v in res.items():
            for p in v.get('parts', []):
                if SF.SOURCE.get(p) != k: Rp[p] += 1
        summ['R_part'] = dict(Rp.most_common())
        summ['len_parts'] = {p: Rp.get(p, 0) for p in SF.SOURCE}
        json.dump({'summary': summ, 'tasks': res}, open(os.path.join(REPO, 'results/o0/v4_design_depth2.json'), 'w'), indent=1)
    else:
        Rk = Counter(f for v in res.values() for f in set(v.get('fits', [])))
        json.dump({'R': dict(Rk), 'note': 'R(key) = dev tasks the depth-1 key fits (v4 enumeration order, v21a B.1)'},
                  open(os.path.join(REPO, 'results/o0/v4_R_depth1.json'), 'w'), indent=1)
        json.dump({'summary': summ, 'tasks': res}, open(os.path.join(REPO, 'results/o0/v4_design_depth1.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in summ.items() if k != 'R_part'}, indent=1))


if __name__ == '__main__':
    main()
