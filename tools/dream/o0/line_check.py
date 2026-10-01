"""Check a reviewer task line after its expansion (decision REVIEW-INPUT, Len Sep 30 2026; T49 restated).

Each line is expanded by the supervisor's LLM harness into tools/dream/o0/lines/<task>.py:
    CARD = task id, LINE = the reviewer's text, READING = {generator, stop, params, participants, preconditions},
    FAMILIES = [fam]   fam(train_pairs) -> iterable of (name, cost, fn)
This script measures, on design data only (N2 members and the 21 sealed tasks are never touched):
    own        the line's task: first program that reproduces every training pair; one harness test check
    held-out   the other members of the line's review group (minus N2): training fit of the same family on each
               (T43 reading: fits k of n), and one test check per fitted member
    population optional (--population): ARC-1 training minus N2 plus the 99; fires, fit, exact, wrong, new over V29
Output: one JSON row per line (stdout and results/o0/line_ledger.jsonl.txt) with the fields the review page's
`expansions` collection shows next to the line.
usage: python3 line_check.py <groups.json> <task id>... [--population] [--v29 <c32 results.jsonl> <e99_v29.jsonl>]"""
import importlib.util, json, math, os, re, signal, sys, time

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'


class TO(Exception): pass


signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def rd(f): return [x for x in re.split(r'[,\s]+', open(os.path.join(REPO, 'tools/m1b', f)).read()) if x]


tr = json.load(open(B + 'arc-agi_training_challenges.json')); ts = json.load(open(B + 'arc-agi_training_solutions.json'))
ev = json.load(open(B + 'arc-agi_evaluation_challenges.json')); es = json.load(open(B + 'arc-agi_evaluation_solutions.json'))
N2 = set(rd('novel_N2.txt')); D99 = set(rd('deval_a.txt') + rd('deval_b.txt'))


def task(k):
    if k in N2: return None                                     # held-out: never read here
    if k in tr: return tr[k], ts[k]
    if k in D99: return ev[k], es[k]
    return None                                                 # sealed or unknown: never read


def run(M, k, check=True, budget=20):
    t = task(k)
    if t is None: return None
    T, S = t
    try:
        signal.alarm(budget); progs = [p for fam in M.FAMILIES for p in fam(T['train'])]; signal.alarm(0)
    except Exception:
        signal.alarm(0); return {'fired': False, 'fit': False, 'error': True}
    if not progs: return {'fired': False, 'fit': False}
    for name, cost, fn in progs:
        try:
            signal.alarm(10); ok = all(fn(p['input']) == p['output'] for p in T['train']); signal.alarm(0)
        except Exception:
            signal.alarm(0); ok = False
        if ok:
            ex = None
            if check:
                try:
                    signal.alarm(10); pr = [fn(q['input']) for q in T['test']]; signal.alarm(0)
                    ex = all(pr[i] == S[i] for i in range(len(S)))
                except Exception:
                    signal.alarm(0); ex = False
            return {'fired': True, 'fit': True, 'exact': ex, 'program': name}
    return {'fired': True, 'fit': False}


def main():
    groups = json.load(open(sys.argv[1]))
    args = [a for a in sys.argv[2:] if re.fullmatch(r'[0-9a-f]{8}', a)]
    pop = '--population' in sys.argv
    v29_fail = None
    if '--v29' in sys.argv:
        i = sys.argv.index('--v29'); v29_fail = set()
        for l in open(sys.argv[i + 1]):
            d = json.loads(l)
            if d.get('task') in N2: continue                    # N2 rows skipped unread
            if not d.get('exact'): v29_fail.add(d['task'])
        for l in open(sys.argv[i + 2]):
            d = json.loads(l); f = d.get('final')
            if not (isinstance(f, list) and any(f)): v29_fail.add(d['task'])
    os.makedirs(os.path.join(REPO, 'results/o0'), exist_ok=True)
    for k in args:
        modf = os.path.join(REPO, 'tools/dream/o0/lines', k + '.py')
        spec = importlib.util.spec_from_file_location('L' + k, modf); M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
        gid = next((g for g, ms in groups.items() if k in ms), None)
        t0 = time.time()
        own = run(M, k) or {}
        held = [m for m in groups.get(gid, []) if m != k and m not in N2 and task(m) is not None]
        hr = {m: run(M, m) for m in held}
        fit_h = sorted(m for m, r in hr.items() if r and r.get('fit'))
        ex_h = sorted(m for m in fit_h if hr[m].get('exact'))
        row = {'task': k, 'group': gid, 'line': getattr(M, 'LINE', ''), 'reading': getattr(M, 'READING', {}),
               'own_fit': bool(own.get('fit')), 'own_exact': own.get('exact'), 'program': own.get('program'),
               'held_n': len(held), 'held_fit': len(fit_h), 'held_exact': len(ex_h), 'held_fit_tasks': fit_h, 'held_exact_tasks': ex_h}
        if pop:
            keys = [x for x in sorted(tr) if x not in N2] + sorted(D99)
            fired = fit = 0; exact = []; wrong = []
            for x in keys:
                r = run(M, x, budget=8)
                if not r: continue
                fired += r.get('fired', False); fit += r.get('fit', False)
                if r.get('fit'): (exact if r.get('exact') else wrong).append(x)
            row.update(pop_n=len(keys), pop_fired=fired, pop_fit=fit, pop_exact=len(exact), pop_wrong=len(wrong),
                       pop_exact_other=[x for x in exact if x != k],
                       pop_new_over_v29=[x for x in exact if v29_fail is not None and x in v29_fail and x != k])
        row['seconds'] = round(time.time() - t0, 1)
        row['T43_pass'] = row['held_fit'] >= max(2, math.ceil(row['held_n'] / 2)) if row['held_n'] else False
        row['time'] = time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())
        with open(os.path.join(REPO, 'results/o0/line_ledger.jsonl.txt'), 'a') as f: f.write(json.dumps(row) + '\n')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
