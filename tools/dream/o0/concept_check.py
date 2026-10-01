"""Check a merged concept family against the separate line families it was anti-unified from (cycle 25, Oct 1 2026).

A concept family tools/dream/o0/concepts/<concept>.py (CARD, CONCEPT, MEMBERS, READING, FAMILIES) states one Layer-2
mechanism concept once, with parameters that span its member lines (tools/dream/o0/lines/<task>.py). Question: does
stating the concept once transfer to more design tasks than the member families do separately?
Measured on design data only (ARC-1 training minus N2, plus the 99 = half A + half B; N2 and sealed never touched),
with line_check.run (first program that reproduces every training pair; one harness test check per task and family
version):
    members      merged family on its members: training fit k of n, exact
    population   merged family: fires, fit, exact, wrong, exact on non-members, new over V29
    union        the member families together (first fitting program, members in order) on the same population
    vs union     tasks the merged family solves that the union does not (gained), and the reverse (lost)
    size         module lines vs the member modules' lines
Output: one JSON row per concept (stdout and results/o0/concept_ledger.jsonl.txt).
usage: python3 concept_check.py <concept>... [--v29 <c32 results.jsonl> <e99_v29.jsonl>]"""
import importlib.util, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import line_check as LC                                     # data loading, N2 guard, run()

HERE = os.path.dirname(os.path.abspath(__file__))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M); return M


class Union:                                                 # the member families as one family list, members in order
    def __init__(self, mods): self.FAMILIES = [f for m in mods for f in m.FAMILIES]


def v29_failures(c32, e99):
    out = set()
    for l in open(c32):
        d = json.loads(l)
        if d.get('task') in LC.N2: continue                  # N2 rows skipped unread
        if not d.get('exact'): out.add(d['task'])
    for l in open(e99):
        d = json.loads(l); f = d.get('final')
        if not (isinstance(f, list) and any(f)) or d.get('exact') is False: out.add(d['task'])
    return out


def main():
    names = [a for a in sys.argv[1:] if not a.startswith('--') and not a.endswith('.jsonl')]
    v29f = None
    if '--v29' in sys.argv:
        i = sys.argv.index('--v29'); v29f = v29_failures(sys.argv[i + 1], sys.argv[i + 2])
    keys = [x for x in sorted(LC.tr) if x not in LC.N2] + sorted(LC.D99)
    for c in names:
        t0 = time.time()
        cpath = os.path.join(HERE, 'concepts', c + '.py'); M = load(cpath, 'C_' + c)
        mods = [load(os.path.join(HERE, 'lines', t + '.py'), 'L' + t) for t in M.MEMBERS]
        U = Union(mods)
        mem = {t: LC.run(M, t) or {} for t in M.MEMBERS}
        res = {'merged': {}, 'union': {}}
        for x in keys:
            for tag, F in (('merged', M), ('union', U)):
                r = LC.run(F, x, budget=8)
                if r: res[tag][x] = r
        def summ(R):
            ex = sorted(x for x, r in R.items() if r.get('fit') and r.get('exact'))
            return {'fired': sum(bool(r.get('fired')) for r in R.values()), 'fit': sum(bool(r.get('fit')) for r in R.values()),
                    'exact': ex, 'wrong': sorted(x for x, r in R.items() if r.get('fit') and not r.get('exact'))}
        S, SU = summ(res['merged']), summ(res['union'])
        lines = lambda p: sum(1 for _ in open(p))
        row = {'concept': c, 'members': M.MEMBERS, 'reading': getattr(M, 'READING', {}),
               'members_fit': sum(bool(r.get('fit')) for r in mem.values()), 'members_exact': sorted(t for t, r in mem.items() if r.get('exact')),
               'pop_n': len(keys), 'pop_fired': S['fired'], 'pop_fit': S['fit'], 'pop_exact': len(S['exact']), 'pop_wrong': len(S['wrong']),
               'exact_other': [x for x in S['exact'] if x not in M.MEMBERS], 'wrong_tasks': S['wrong'],
               'new_over_v29': [x for x in S['exact'] if v29f is not None and x in v29f],
               'union_fit': SU['fit'], 'union_exact': len(SU['exact']), 'union_wrong': len(SU['wrong']),
               'union_exact_other': [x for x in SU['exact'] if x not in M.MEMBERS],
               'gained_vs_union': sorted(set(S['exact']) - set(SU['exact'])), 'lost_vs_union': sorted(set(SU['exact']) - set(S['exact'])),
               'new_wrong_vs_union': sorted(set(S['wrong']) - set(SU['wrong'])),
               'lines': lines(cpath), 'member_lines': sum(lines(os.path.join(HERE, 'lines', t + '.py')) for t in M.MEMBERS),
               'seconds': round(time.time() - t0, 1), 'time': time.strftime('%Y-%m-%dT%H:%MZ', time.gmtime())}
        os.makedirs(os.path.join(LC.REPO, 'results/o0'), exist_ok=True)
        with open(os.path.join(LC.REPO, 'results/o0/concept_ledger.jsonl.txt'), 'a') as f: f.write(json.dumps(row) + '\n')
        print(json.dumps(row), flush=True)


if __name__ == '__main__':
    main()
