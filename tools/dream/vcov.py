"""V_cov (Fable v9, G55 / T45): vocabulary coverage of the failed design tasks.

For every design task V29 fails (ARC-1 training minus N2: c32 results; the 99: e99_v29) whose training pairs keep the
grid size, and for each lattice abstraction, the target individuals X of a pair are the input individuals (lattice
nodes) that contain a changed cell.  Per task and abstraction:
  uncovered   changed cells that lie in no individual (new cells on background: nothing to describe them with)
  C_t         lcs over all pairs of msc_1(x), x in X (names + roles touches/inside/contains/aligned/same_shape)
  loose       every pair has X non-empty, no uncovered changed cell, and C_t is not top (has a name or a role)
  exact       some concept of C_t (name, or role chain of depth <= 2 to a name) has extension exactly X in every pair
              (exact_proper: and X is a proper subset of the individuals in some pair, i.e. selection is not trivial)
A task counts as covered (loose / exact) if any abstraction covers it.  Reported: V_cov_loose, V_cov_exact and the
split of uncovered tasks by the share of changed cells on background.  Training pairs only; no test data.
usage: python3 vcov.py <probe_dir> <c32_results.jsonl> <e99_v29.jsonl> <out.json>"""
import json, os, signal, sys

probe, c32f, e99f, outf = sys.argv[1:5]; outf = os.path.abspath(outf)
os.environ["M1B_VOCAB"] = 'fill_interior,ray,connect,border,bbox_fill,outline8,L_inertia,D12,S_holes,D4,D1,S_size,P_pixel,P_frame,D10,S_atoms,G_dsl'
sys.path[:0] = [probe, os.path.dirname(os.path.abspath(__file__))]
os.chdir(probe)
import occupancy2 as P
import routeA_t24 as RA

B = '/kaggle/input/arc-prize-2026-arc-agi-2/'


class TO(BaseException): pass


signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def failed_design():
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ev = json.load(open(B + 'arc-agi_evaluation_challenges.json'))
    out = {}
    for l in open(c32f):
        d = json.loads(l)
        if d['task'] in tr and not d.get('exact'): out[d['task']] = tr[d['task']]
    for l in open(e99f):
        d = json.loads(l)
        f = d.get('final')
        if not (isinstance(f, list) and any(f)): out[d['task']] = ev[d['task']]
    return out


def task_cov(t, ab):
    pairs = []; uncovered = 0; changed = 0
    for p in t['train']:
        a, b = p['input'], p['output']
        nodes, bg, at, src, others, oc = P.prepare(a, ab)
        ch = {(y, x) for y in range(len(a)) for x in range(len(a[0])) if a[y][x] != b[y][x]}
        X = {i for i, n in enumerate(nodes) if n['pix'] & ch}
        cov = set().union(*[nodes[i]['pix'] for i in X]) if X else set()
        uncovered += len(ch - cov); changed += len(ch)
        pairs.append((nodes, at, RA.roles_of(nodes), X))
    res = {'uncovered': uncovered, 'changed': changed, 'loose': False, 'exact': False,
           'x_all': all(len(X) == len(nodes) for nodes, at, R, X in pairs)}
    if uncovered or any(not X for *_, X in pairs): return res
    RA.K = 1
    C = None
    for nodes, at, R, X in pairs:
        for i in sorted(X):
            m = RA.msc(i, at, R, 1); C = m if C is None else RA.lcs(C, m)
    res['loose'] = bool(C and (C[0] or C[1]))
    if C: res['ct'] = {'names': sorted(map(str, C[0]))[:12], 'roles': sorted(C[1])}
    if not res['loose']: return res
    W = [0]
    try:
        for chain, name in RA.candidates(C):
            if all({i for i in range(len(at)) if RA.holds(i, chain, name, at, R, W)} == X for nodes, at, R, X in pairs):
                res['exact'] = True; res['concept'] = [list(chain), name]; break
    except RA.Budget:
        res['budget'] = True
    return res


def main():
    T = failed_design(); rows = []
    for k in sorted(T):
        t = T[k]
        if any((len(p['input']), len(p['input'][0])) != (len(p['output']), len(p['output'][0])) for p in t['train']):
            rows.append({'task': k, 'same_size': False}); continue
        best = {'task': k, 'same_size': True, 'loose': False, 'exact': False, 'bg_share': None}
        for ab in P.ABSTRACTIONS:
            try:
                signal.alarm(20); r = task_cov(t, ab); signal.alarm(0)
            except TO: continue
            except Exception: signal.alarm(0); continue
            share = r['uncovered'] / max(r['changed'], 1)
            if best['bg_share'] is None or share < best['bg_share']: best['bg_share'] = round(share, 3)
            if r['loose'] and not best['loose']: best['loose'] = True; best['ab_loose'] = ab; best['ct'] = r.get('ct')
            if r['exact'] and not best['exact']: best['exact'] = True; best['ab_exact'] = ab; best['concept'] = r.get('concept')
            if r['exact'] and not r['x_all']: best['exact_proper'] = True
        rows.append(best); print(json.dumps(best), flush=True)
    S = [r for r in rows if r['same_size']]
    unc = [r for r in S if not r['loose']]
    summ = {'failed_design_tasks': len(rows), 'same_size': len(S),
            'V_cov_loose': round(sum(r['loose'] for r in S) / max(len(S), 1), 3),
            'V_cov_exact': round(sum(r['exact'] for r in S) / max(len(S), 1), 3),
            'n_loose': sum(r['loose'] for r in S), 'n_exact': sum(r['exact'] for r in S),
            'n_exact_proper_subset': sum(bool(r.get('exact_proper')) for r in S),
            'uncovered_by_bg_share': {'all changes on background (>=0.9)': sum(1 for r in unc if (r['bg_share'] or 0) >= 0.9),
                                      'mixed (0.1-0.9)': sum(1 for r in unc if 0.1 <= (r['bg_share'] or 0) < 0.9),
                                      'changes on objects (<0.1)': sum(1 for r in unc if (r['bg_share'] or 0) < 0.1)}}
    json.dump({'summary': summ, 'rows': rows}, open(outf, 'w'), indent=0)
    print(json.dumps(summ), file=sys.stderr)


if __name__ == '__main__':
    main()
