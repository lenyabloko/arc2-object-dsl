"""Description lattice (Fable v10 / v10a), T54-T56 harness.

The five schema modules (schema_<s>.py: SCHEMA, MENU, nodes(), key(), draw(), family()) were written test-blind from
the parsed description records (results/o0/v10_records.json). This script:
  ground   T54: every node drawn with seeds 0..3; ok = all drawn, outputs differ from inputs, the node's family fitted
           on pairs 0-2 predicts pair 3 (synthetic tasks are evidence only of ok(D), G59)
  index    T55: for each of the 68 far-cells design tasks (results/cycle21/far68_manual_split.json), score every
           grounded node: schema compatible with the task's change signature + the node family fits the task's
           training pairs (training pairs only; no test outputs). Reports how many tasks have a fitting node among
           the top-3 proposals, and among all nodes (oracle).
  redundancy T56: does an existing family (priors2, concepts, lines) solve the node's synthetic task?
  real     v10b G59/G67: every synthetically grounded node is fitted on every real design task (ARC-1 training minus
           N2, plus the 99; training pairs only, challenges files only, no solutions read). A node enters the pile
           iff it fits a real design task; output results/o0/v10_ground_real.json {node key: [tasks]}.
  index2   T55': retrieval on the 68 far-cells tasks over the real-grounded pile = lattice nodes with a real fit
           on a design task other than the one being indexed, plus the cycle-27 second-pass families
           (tools/dream/o0/priors3, fits read from results/o0/priors3_ledger.jsonl.txt) indexed for a task only
           when the task is not one of the family's members (sources). Ranking as in T55 (schema-compatible
           first, SIG2SCHEMA unchanged; family schemas from results/o0/t64_frame_schema.json), then more general.
           Pass (Fable v10b): a fitting node for >= 20/68 and one in the top 3 for >= 12/68.
  index3   T69 (Fable v11, G69): index2 plus composed nodes.  A composed node A>>B applies a lattice node family A,
           then a family B to A's output grid (the shared variable of the G69 parse, results/o0/v10_records_g69.json,
           is the cell set A paints and hands to B).  Restricted to (a) ordered schema pairs whose two schemas are a
           composed T64 frame's pair and both have a module (only CENTER-PERIPHERY + CYCLE: distance_rings_halo;
           both orders, since the G69 parse has both CP>CYCLE and CYCLE>CP records) and (b) both nodes in the
           real-grounded pile with a real fit on a design task other than the indexed one, one representative
           (most general = shortest key) per distinct real fit set.  The families are exact explainers, so the
           intermediate grid z is hypothesised, which fixes the shared variable: z = input with the changed cells
           of output colour set S painted (colour split, or the novel / present colour role), z = input with every
           changed cell in one colour c (A paints the cell set, B recolours it), and, for grid-size changes,
           z = a corner block of the output (A on the input, B tiles) or z = output with colour c cleared (A changes
           the size, B paints c), or z = input with the changed cells within Chebyshev distance 1 / 2 of the input
           foreground painted (near) or the others (far).  A>>B fits iff A fits (x, z) and B fits (z, y) on every
           training pair (then B(A(x)) = y); a hypothesis with z = x in every pair or z = y in every pair is skipped
           (a stage idle in some pairs is left to the family, which may reject identity pairs).  Budget: 2 s per family fit (as index), 60 s per
           task; ranking as index2 (schema-compatible first, then shorter key), composed nodes keyed by
           len(A)+len(B)+1.  Extra (not a pass criterion): leave-one-out for the top composed node.
           Output results/o0/v10_index3_far68.json.  Optional args: part parts (task slice) for 2 processes; the
           parts are merged by `index3 merge`.  `index3 scan part parts` runs the same composed search on every
           design task (information only: which real tasks ground a composed node); merge adds it to the summary.
usage: python3 pile.py ground|index|real|index2|index3 [part parts|merge|scan part parts]"""
import glob, importlib, json, os, re, signal, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MODS = ['schema_path', 'schema_link', 'schema_cycle', 'schema_center_periphery', 'schema_symmetry']
B = '/kaggle/input/arc-prize-2026-arc-agi-2/'


class TO(Exception): pass


signal.signal(signal.SIGALRM, lambda *a: (_ for _ in ()).throw(TO()))


def load():
    out = []
    for m in MODS:
        M = importlib.import_module(m)
        for n in M.nodes(): out.append((M, n, M.key(n)))
    return out


def fit_first(fam, train, budget=3):
    try:
        signal.alarm(budget)
        for name, cost, fn in fam(train):
            if all(fn(p['input']) == p['output'] for p in train):
                signal.alarm(0); return name, fn
        signal.alarm(0)
    except Exception:
        signal.alarm(0)
    return None


def ground(nodes):
    res = {}
    for M, n, k in nodes:
        pairs = []
        for s in range(4):
            try: p = M.draw(n, s)
            except Exception: p = None
            if not p: break
            pairs.append({'input': p[0], 'output': p[1]})
        ok = len(pairs) == 4 and all(p['input'] != p['output'] for p in pairs)
        if ok:
            f = fit_first(M.family(n), pairs[:3])
            try: ok = bool(f) and f[1](pairs[3]['input']) == pairs[3]['output']
            except Exception: ok = False
        res[k] = {'schema': M.SCHEMA, 'ok': ok}
    return res


SIG2SCHEMA = {'ray/line': {'PATH'}, 'between': {'LINK', 'PATH'}, 'periodic': {'CYCLE'}, 'fill': {'CENTER-PERIPHERY', 'LINK'},
              'reflection': {'SYMMETRY'}, 'copy': {'CYCLE', 'SYMMETRY'}, 'other generator': {'PATH', 'CYCLE', 'CENTER-PERIPHERY'}}


def index(nodes, grounded):
    far = json.load(open(os.path.join(REPO, 'results/cycle21/far68_manual_split.json')))['labels']
    ch = json.load(open(B + 'arc-agi_training_challenges.json')); ch.update(json.load(open(B + 'arc-agi_evaluation_challenges.json')))
    rows = []
    for t, lab in sorted(far.items()):
        train = ch[t]['train']; fits = []
        for M, n, k in nodes:
            if not grounded.get(k, {}).get('ok'): continue
            f = fit_first(M.family(n), train, budget=2)
            if f: fits.append((M.SCHEMA in SIG2SCHEMA.get(lab, set()), -len(k), k, f[0]))
        fits.sort(key=lambda x: (not x[0], -x[1]))          # schema-compatible first, then more general (shorter key)
        top3 = fits[:3]
        rows.append({'task': t, 'label': lab, 'n_fit': len(fits), 'top3': [x[2] for x in top3],
                     'top3_compatible': any(x[0] for x in top3)})
        print(json.dumps(rows[-1]), flush=True)
    n_top3 = sum(1 for r in rows if r['top3']); n_any = sum(1 for r in rows if r['n_fit'])
    print(json.dumps({'T55_tasks_with_fitting_node_in_top3': n_top3, 'oracle_any_node_fits': n_any, 'n': len(rows)}))
    return rows


def design_keys():
    rd = lambda f: [x for x in re.split(r'[,\s]+', open(os.path.join(REPO, 'tools/m1b', f)).read()) if x]
    n2 = set(rd('novel_N2.txt')); d99 = set(rd('deval_a.txt') + rd('deval_b.txt'))
    tr = json.load(open(B + 'arc-agi_training_challenges.json')); ev = json.load(open(B + 'arc-agi_evaluation_challenges.json'))
    ch = {k: v for k, v in tr.items() if k not in n2}; ch.update({k: ev[k] for k in d99 if k in ev})
    return ch


def real(nodes, grounded, part=0, parts=1):
    ch = design_keys(); out = {}
    keys = sorted(ch)[part::parts]
    for i, t in enumerate(keys):
        for M, n, k in nodes:
            if not grounded.get(k, {}).get('ok'): continue
            if fit_first(M.family(n), ch[t]['train'], budget=2): out.setdefault(k, []).append(t)
        if i % 50 == 0: print(json.dumps({'done': i, 'of': len(keys), 'nodes_with_fit': len(out)}), flush=True)
    return out


def index2():
    far = json.load(open(os.path.join(REPO, 'results/cycle21/far68_manual_split.json')))['labels']
    gr = {}
    for f in sorted(glob.glob(os.path.join(REPO, 'results/o0/v10_ground_real*.json'))):
        for k, ts in json.load(open(f)).items(): gr.setdefault(k, set()).update(ts)
    fam = {}
    for line in open(os.path.join(REPO, 'results/o0/priors3_ledger.jsonl.txt')):
        r = json.loads(line); fam[r['concept']] = r                 # last row per family wins
    sch = {r['frame']: {r['schema']} | ({r['schema2']} if r['schema2'] else set())
           for r in json.load(open(os.path.join(REPO, 'results/o0/t64_frame_schema.json')))}
    skey = {}
    for M, n, k in load(): skey[k] = M.SCHEMA
    rows = []
    for t, lab in sorted(far.items()):
        ok = SIG2SCHEMA.get(lab, set()); fits = []
        for k, ts in gr.items():
            if t in ts and ts - {t}:                                  # fits t, and grounded by another real task
                fits.append((skey.get(k) in ok, len(k), k, 'lattice'))
        for c, r in fam.items():
            if t in r['members']: continue                            # never index a family for its own source
            other = set(r['exact_other']) | set(r['wrong_other'])
            if t in other and other - {t}:
                fits.append((bool(sch.get(c, set()) & ok), 0, 'family:' + c, 'family'))
        fits.sort(key=lambda x: (not x[0], x[1]))
        rows.append({'task': t, 'label': lab, 'n_fit': len(fits), 'top3': [x[2] for x in fits[:3]],
                     'top3_compatible': any(x[0] for x in fits[:3])})
        print(json.dumps(rows[-1]), flush=True)
    n_any = sum(1 for r in rows if r['n_fit']); n_top3 = sum(1 for r in rows if r['top3'])
    summ = {'T55p_tasks_with_fitting_node': n_any, 'top3': n_top3, 'n': len(rows), 'pass': n_any >= 20 and n_top3 >= 12,
            'pile_lattice_nodes': sum(1 for ts in gr.values() if ts), 'pile_families': len(fam)}
    print(json.dumps(summ))
    return rows, summ


COMP_SCHEMAS = ('CENTER-PERIPHERY', 'CYCLE')


def _pile():
    gr = {}
    for f in sorted(glob.glob(os.path.join(REPO, 'results/o0/v10_ground_real*.json'))):
        for k, ts in json.load(open(f)).items(): gr.setdefault(k, set()).update(ts)
    return gr


def comp_pairs():
    """Ordered schema pairs allowed by (a): a composed T64 frame's pair, both schemas with a module."""
    have = set()
    for m in MODS: have.add(importlib.import_module(m).SCHEMA)
    out = []
    for r in json.load(open(os.path.join(REPO, 'results/o0/t64_frame_schema.json'))):
        if r['schema2'] and r['schema'] in have and r['schema2'] in have:
            for p in ((r['schema'], r['schema2']), (r['schema2'], r['schema'])):
                if p not in out: out.append(p)
    return out


def comp_reps(gr, schemas):
    """(b): pile nodes of the given schemas, one representative (shortest key) per distinct real fit set."""
    by = {}
    for M, n, k in load():
        if M.SCHEMA in schemas and gr.get(k):
            fs = frozenset(gr[k])
            if fs not in by or (len(k), k) < (len(by[fs][2]), by[fs][2]): by[fs] = (M, n, k)
    return [(M, n, k, fs) for fs, (M, n, k) in sorted(by.items(), key=lambda kv: kv[1][2])]


def _cols(g): return {v for r in g for v in r}


def comp_hyps(train):
    """Intermediate grids z (one per training pair) for A>>B; each hypothesis fixes the shared variable."""
    X = [p['input'] for p in train]; Y = [p['output'] for p in train]; H = []
    same = [len(x) == len(y) and len(x[0]) == len(y[0]) for x, y in zip(X, Y)]
    if all(same):
        D = [[(r, c) for r in range(len(x)) for c in range(len(x[0])) if x[r][c] != y[r][c]] for x, y in zip(X, Y)]
        C = [{y[r][c] for r, c in d} for y, d in zip(Y, D)]
        U = sorted(set().union(*C))

        XC = [_cols(x) for x in X]

        def paint(sel):
            zs = []
            for x, y, d, xc in zip(X, Y, D, XC):
                z = [row[:] for row in x]
                for r, c in d:
                    if sel(xc, y, r, c): z[r][c] = y[r][c]
                zs.append(z)
            return zs
        subs = []
        if len(U) <= 6:
            for m in range(1, 2 ** len(U) - 1): subs.append({U[i] for i in range(len(U)) if m >> i & 1})
        else:
            for u in U: subs += [{u}, set(U) - {u}]
        for S in subs: H.append(('colour_set:' + ''.join(map(str, sorted(S))), paint(lambda x, y, r, c, S=S: y[r][c] in S)))
        H.append(('role:novel', paint(lambda xc, y, r, c: y[r][c] not in xc)))
        H.append(('role:present', paint(lambda xc, y, r, c: y[r][c] in xc)))
        for rad in (1, 2):                   # spatial split: changed cells within Chebyshev rad of the input foreground
            NB = []
            for x in X:
                h, w = len(x), len(x[0])
                NB.append({(r + a, c + b) for r in range(h) for c in range(w) if x[r][c] != 0
                           for a in range(-rad, rad + 1) for b in range(-rad, rad + 1)})
            zs_n, zs_f = [], []
            for x, y, d, nb in zip(X, Y, D, NB):
                zn = [row[:] for row in x]; zf = [row[:] for row in x]
                for r, c in d:
                    if (r, c) in nb: zn[r][c] = y[r][c]
                    else: zf[r][c] = y[r][c]
                zs_n.append(zn); zs_f.append(zf)
            H.append(('near:%d' % rad, zs_n)); H.append(('far:%d' % rad, zs_f))
        common = set.intersection(*C) if C else set()
        cand = [('cells_as:%d' % c, c) for c in sorted(common)]
        cand.append(('cells_as:rank0', None))
        for nm, c in cand:
            zs = []
            for x, y, d in zip(X, Y, D):
                cc = c
                if cc is None:
                    cnt = {}
                    for r, q in d: cnt[y[r][q]] = cnt.get(y[r][q], 0) + 1
                    cc = max(sorted(cnt), key=lambda v: cnt[v]) if cnt else 0
                z = [row[:] for row in x]
                for r, q in d: z[r][q] = cc
                zs.append(z)
            H.append((nm, zs))
    elif not any(same):
        if all(len(y) % len(x) == 0 and len(y[0]) % len(x[0]) == 0 for x, y in zip(X, Y)):
            for bi, bj in ((0, 0), (0, -1), (-1, 0), (-1, -1)):
                zs = []
                for x, y in zip(X, Y):
                    h, w = len(x), len(x[0]); nr, nc = len(y) // h, len(y[0]) // w
                    i, j = bi % nr, bj % nc
                    zs.append([row[j * w:(j + 1) * w] for row in y[i * h:(i + 1) * h]])
                H.append(('block:%d,%d' % (bi, bj), zs))
        common = set.intersection(*[_cols(y) for y in Y]) - {0}
        for c in sorted(common):
            H.append(('bg_out:%d' % c, [[[0 if v == c else v for v in row] for row in y] for y in Y]))
    out, seen = [], set()
    for nm, zs in H:
        if all(z == x for z, x in zip(zs, X)) or all(z == y for z, y in zip(zs, Y)): continue   # both stages act
        key = json.dumps(zs)
        if key in seen: continue
        seen.add(key); out.append((nm, zs))
    return out


def comp_fit_task(t, train, reps, pairs, task_budget=60):
    """All composed nodes A>>B (A, B representatives) that fit every training pair through some hypothesis z."""
    t0 = time.time(); fits = {}; n_fit_calls = 0; trunc = False
    usable = [(M, n, k) for M, n, k, fs in reps if fs - {t}]              # grounded by another real design task
    for hname, zs in comp_hyps(train):
        if time.time() - t0 > task_budget: trunc = True; break
        tA = [{'input': p['input'], 'output': z} for p, z in zip(train, zs)]
        tB = [{'input': z, 'output': p['output']} for p, z in zip(train, zs)]
        FA = {}
        for M, n, k in usable:
            if not any(M.SCHEMA == a for a, b in pairs): continue
            n_fit_calls += 1
            f = fit_first(M.family(n), tA, budget=2)
            if f: FA.setdefault(M.SCHEMA, []).append((k, f[0], M, n))
        if not FA: continue
        FB = {}
        need = {b for a, b in pairs if a in FA}
        for M, n, k in usable:
            if M.SCHEMA not in need: continue
            if time.time() - t0 > task_budget: trunc = True; break
            n_fit_calls += 1
            f = fit_first(M.family(n), tB, budget=2)
            if f: FB.setdefault(M.SCHEMA, []).append((k, f[0], M, n))
        for a, b in pairs:
            for ka, pa, Ma, na in FA.get(a, []):
                for kb, pb, Mb, nb in FB.get(b, []):
                    ck = ka + ' >> ' + kb
                    if ck not in fits: fits[ck] = (a, b, ka, kb, hname, pa, pb, Ma, na, Mb, nb)
    return fits, n_fit_calls, trunc, round(time.time() - t0, 1)


def comp_loo(train, zs_of, Ma, na, Mb, nb):
    """Leave-one-out for one composed node: fit A, B on n-1 pairs (same hypothesis), predict the held-out pair."""
    if len(train) < 3: return None
    ok = 0
    for h in range(len(train)):
        tr = [p for i, p in enumerate(train) if i != h]
        zs = [z for i, z in enumerate(zs_of) if i != h]
        fa = fit_first(Ma.family(na), [{'input': p['input'], 'output': z} for p, z in zip(tr, zs)], budget=2)
        fb = fit_first(Mb.family(nb), [{'input': z, 'output': p['output']} for p, z in zip(tr, zs)], budget=2)
        try:
            ok += bool(fa and fb and fb[1](fa[1](train[h]['input'])) == train[h]['output'])
        except Exception:
            pass
    return '%d/%d' % (ok, len(train))


def index3(part=0, parts=1):
    far = json.load(open(os.path.join(REPO, 'results/cycle21/far68_manual_split.json')))['labels']
    ch = json.load(open(B + 'arc-agi_training_challenges.json')); ch.update(json.load(open(B + 'arc-agi_evaluation_challenges.json')))
    gr = _pile(); pairs = comp_pairs()
    schemas = {s for p in pairs for s in p}
    reps = comp_reps(gr, schemas)
    nrep = {s: sum(1 for M, n, k, fs in reps if M.SCHEMA == s) for s in schemas}
    n_pairs = sum(nrep[a] * nrep[b] for a, b in pairs)
    base = {r['task']: r for r in json.load(open(os.path.join(REPO, 'results/o0/v10_index2_far68.json')))['rows']}
    rows = []
    for t, lab in sorted(far.items())[part::parts]:
        ok = SIG2SCHEMA.get(lab, set())
        fits, calls, trunc, secs = comp_fit_task(t, ch[t]['train'], reps, pairs)
        comp = sorted(((bool({a, b} & ok), len(ka) + len(kb) + 1, ck, hn, pa + ' >> ' + pb)
                       for ck, (a, b, ka, kb, hn, pa, pb, Ma, na, Mb, nb) in fits.items()), key=lambda x: (not x[0], x[1], x[2]))
        loo = None
        if comp:
            a, b, ka, kb, hn, pa, pb, Ma, na, Mb, nb = fits[comp[0][2]]
            zs = dict(comp_hyps(ch[t]['train']))[hn]
            loo = comp_loo(ch[t]['train'], zs, Ma, na, Mb, nb)
        rows.append({'task': t, 'label': lab, 'composed_n_fit': len(comp), 'composed_top': [
            {'node': c[2], 'compatible': c[0], 'z': c[3], 'program': c[4]} for c in comp[:3]], 'composed_top_loo': loo,
            'fit_calls': calls, 'truncated': trunc, 'seconds': secs})
        print(json.dumps({k: rows[-1][k] for k in ('task', 'composed_n_fit', 'fit_calls', 'truncated', 'seconds')}), flush=True)
    meta = {'pairs': pairs, 'reps_per_schema': nrep, 'composed_node_pairs_indexed': n_pairs, 'part': part, 'parts': parts}
    return rows, meta


def index3_scan(part=0, parts=1):
    """Real grounding of the composed nodes (G59/G67 style, information only): every design task (ARC-1 training
    minus N2, plus the 99; training pairs only) is fitted with the same composed search."""
    ch = design_keys(); gr = _pile(); pairs = comp_pairs(); reps = comp_reps(gr, {s for p in pairs for s in p})
    out = {}; t0 = time.time(); keys = sorted(ch)[part::parts]
    for t in keys:
        fits, calls, trunc, secs = comp_fit_task(t, ch[t]['train'], reps, pairs, task_budget=20)
        if fits:
            out[t] = {'n_composed': len(fits), 'nodes': sorted(fits)[:5],
                      'example': {'node': sorted(fits)[0], 'z': fits[sorted(fits)[0]][4],
                                  'program': fits[sorted(fits)[0]][5] + ' >> ' + fits[sorted(fits)[0]][6]}}
    json.dump({'fits': out, 'n': len(keys), 'seconds': round(time.time() - t0, 1)},
              open(os.path.join(REPO, 'results/o0/v10_index3_scan_%d_%d.json' % (part, parts)), 'w'))
    print(json.dumps({'part': part, 'design_tasks': len(keys), 'with_composed_fit': len(out), 'seconds': round(time.time() - t0, 1)}))


def index3_merge():
    rows, meta = [], None
    for f in sorted(glob.glob(os.path.join(REPO, 'results/o0/v10_index3_part_*.json'))):
        d = json.load(open(f)); rows += d['rows']; meta = d['meta']
    base = {r['task']: r for r in json.load(open(os.path.join(REPO, 'results/o0/v10_index2_far68.json')))['rows']}
    gr = _pile(); skey = {k: M.SCHEMA for M, n, k in load()}
    fam = {}
    for line in open(os.path.join(REPO, 'results/o0/priors3_ledger.jsonl.txt')):
        q = json.loads(line); fam[q['concept']] = q
    sch = {q['frame']: {q['schema']} | ({q['schema2']} if q['schema2'] else set())
           for q in json.load(open(os.path.join(REPO, 'results/o0/t64_frame_schema.json')))}
    out = []
    for r in sorted(rows, key=lambda r: r['task']):
        b = base[r['task']]; ok = SIG2SCHEMA.get(r['label'], set()); t = r['task']
        fits = []                                     # index2's list for the task, rebuilt exactly as index2 does
        for k, ts in gr.items():
            if t in ts and ts - {t}: fits.append((skey.get(k) in ok, len(k), k))
        for c, q in fam.items():
            if t in q['members']: continue
            other = set(q['exact_other']) | set(q['wrong_other'])
            if t in other and other - {t}: fits.append((bool(sch.get(c, set()) & ok), 0, 'family:' + c))
        assert len(fits) == b['n_fit']
        n_single = b['n_fit']
        for c in r['composed_top']:
            a, bb = c['node'].split(' >> ')
            fits.append((c['compatible'], len(a) + len(bb) + 1, 'comp:' + c['node'] + ' @' + c['z']))
        fits.sort(key=lambda x: (not x[0], x[1]))
        top3 = [x[2] for x in fits[:3]]
        out.append(dict(r, n_fit_single=n_single, n_fit=n_single + r['composed_n_fit'], top3=top3,
                        top3_has_composed=any(x.startswith('comp:') for x in top3),
                        top3_compatible=any(x[0] for x in fits[:3])))
    n_any = sum(1 for r in out if r['n_fit']); n_top3 = sum(1 for r in out if r['top3'])
    n_comp = sum(1 for r in out if r['composed_n_fit'])
    new = sorted(r['task'] for r in out if r['composed_n_fit'] and not r['n_fit_single'])
    summ = {'T55p_index3_tasks_with_fitting_node': n_any, 'top3': n_top3, 'n': len(out),
            'tasks_with_fitting_node': sorted(r['task'] for r in out if r['n_fit']),
            'tasks_with_composed_fit': sorted(r['task'] for r in out if r['composed_n_fit']),
            'new_over_index2': new, 'index2_tasks_with_fitting_node': sum(1 for r in out if r['n_fit_single']),
            'composed_top_loo': {r['task']: r['composed_top_loo'] for r in out if r['composed_n_fit']},
            'pass_T69': n_any >= 5, 'fit_calls': sum(r['fit_calls'] for r in out),
            'tasks_truncated': sum(1 for r in out if r['truncated']), 'seconds_sum': round(sum(r['seconds'] for r in out), 1)}
    summ.update(meta or {}); summ.pop('part', None); summ.pop('parts', None)
    scan = {}; scan_n = 0; scan_s = 0
    for f in sorted(glob.glob(os.path.join(REPO, 'results/o0/v10_index3_scan_*.json'))):
        d = json.load(open(f)); scan.update(d['fits']); scan_n += d['n']; scan_s += d['seconds']
    if scan_n:
        summ['design_scan'] = {'design_tasks': scan_n, 'tasks_with_composed_fit': sorted(scan),
                               'examples': {t: v['example'] for t, v in sorted(scan.items())}, 'seconds_sum': round(scan_s, 1)}
    print(json.dumps(summ))
    json.dump({'rows': out, 'summary': summ}, open(os.path.join(REPO, 'results/o0/v10_index3_far68.json'), 'w'))
    return summ


def main():
    mode = sys.argv[1]
    if mode == 'index3':
        if len(sys.argv) > 2 and sys.argv[2] == 'merge':
            index3_merge(); return
        if len(sys.argv) > 2 and sys.argv[2] == 'scan':
            index3_scan(*(map(int, sys.argv[3:5]) if len(sys.argv) > 4 else (0, 1))); return
        part, parts = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)
        t0 = time.time(); rows, meta = index3(part, parts)
        meta['seconds'] = round(time.time() - t0, 1)
        json.dump({'rows': rows, 'meta': meta}, open(os.path.join(REPO, 'results/o0/v10_index3_part_%d_%d.json' % (part, parts)), 'w'))
        if parts == 1: index3_merge()
        return
    nodes = load()
    gpath = os.path.join(REPO, 'results/o0/v10_ground.json')
    if mode == 'ground':
        t0 = time.time(); g = ground(nodes)
        json.dump(g, open(gpath, 'w'))
        by = {}
        for v in g.values(): by.setdefault(v['schema'], [0, 0]); by[v['schema']][0] += 1; by[v['schema']][1] += v['ok']
        print(json.dumps({'nodes': len(g), 'ok': sum(v['ok'] for v in g.values()), 'by_schema': by, 'seconds': round(time.time() - t0, 1)}))
    elif mode == 'index':
        rows = index(nodes, json.load(open(gpath)))
        json.dump(rows, open(os.path.join(REPO, 'results/o0/v10_index_far68.json'), 'w'))
    elif mode == 'real':
        part, parts = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, 1)
        t0 = time.time(); out = real(nodes, json.load(open(gpath)), part, parts)
        json.dump(out, open(os.path.join(REPO, 'results/o0/v10_ground_real_%d_%d.json' % (part, parts)), 'w'))
        print(json.dumps({'nodes_with_real_fit': len(out), 'seconds': round(time.time() - t0, 1)}))
    elif mode == 'index2':
        rows, summ = index2()
        json.dump({'rows': rows, 'summary': summ}, open(os.path.join(REPO, 'results/o0/v10_index2_far68.json'), 'w'))


if __name__ == '__main__':
    main()
