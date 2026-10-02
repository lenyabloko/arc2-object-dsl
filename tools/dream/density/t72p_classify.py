"""Fable v13 T72 / v14 T72' (Oct 2 2026): classify failing fits by the generator slot that would have fixed them.

Mechanical residual reading, no LLM, no proposals. For every fit that reproduces the training pairs and misses the
test pair, the prediction is recomputed (same first-fit rule as the measuring harness) and compared with the expected
output. Labels (first match; every flag is also recorded):

  size            prediction missing or of the wrong size
  iterate         applying the fitted program again to its own prediction (1..8 times) gives the expected output
  colour_only     the prediction changes exactly the right cells; only colours differ        (colour slot / G68 role)
  shift           the expected change set is the predicted change set translated by one vector (anchor slot: offset)
  on_stop_paint   every residual cell is missing ink within one cell of a tip of a drawn stroke   (on_stop: paint)
  on_stop_turn    every residual cell is missing ink on a straight ray from a stroke tip    (on_stop: turn/continue)
  accept_overlap  only extra ink, and the extra ink overwrites input ink                     (accept: no_overlap)
  accept_extra    only extra ink, on background                                               (accept: fits/aligned)
  anchor_midpoint only missing ink; a missing component sits at the midpoint of two input objects  (anchor: midpoint)
  anchor_inter    only missing ink; a missing component sits on one object's row and another's column (anchor: inter.)
  anchor_other    only missing ink, none of the above                                         (anchor: virtual/other)
  mixed           missing and extra ink together
A stroke tip is a changed cell with at most one changed 4-neighbour. Same-size tasks only for the ink labels; tasks
whose output size differs from the input get size / iterate / colour_only / shift / mixed only.

Modes:
  density  rows of results/o0/t75_density_*.jsonl.txt with exact == false (ARC-GEN variants, design-side instrument
           only, G74; regenerated from the recorded seeds)
  design   the wrong non-source fits listed in results/o0/<dir>_ledger.jsonl.txt (design tasks; the expected outputs are
           the same harness check prior_check already made; aggregate counts only, nothing is iterated on them)
Output: results/o0/t72p_<mode>.jsonl.txt (one row per case) and results/o0/t72p_<mode>_summary.json.
usage: python3 t72p_classify.py density [part parts] | design [priors3 priors4]"""
import importlib, importlib.util, json, os, sys, time
from collections import Counter, defaultdict
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(REPO, 'tools/dream/o0'))
import t75_density as D                                     # variant(), seed(), families(), the alarm handler; chdir(GEN)

DIRS8 = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def fit_fn(M, train, budget=8):
    """the harness's first-fit rule; returns the program's function (or None)"""
    try:
        D.signal.alarm(budget); progs = [p for fam in M.FAMILIES for p in fam(train)]; D.signal.alarm(0)
    except BaseException:
        D.signal.alarm(0); return None
    for name, cost, fn in progs:
        try:
            D.signal.alarm(5); ok = all(fn(p['input']) == p['output'] for p in train); D.signal.alarm(0)
        except BaseException:
            D.signal.alarm(0); ok = False
        if ok: return name, fn
    return None


def call(fn, g, t=5):
    try:
        D.signal.alarm(t); r = fn(g); D.signal.alarm(0); return r
    except BaseException:
        D.signal.alarm(0); return None


def dims(g): return (len(g), len(g[0])) if isinstance(g, list) and g and isinstance(g[0], list) and g[0] else None


def comps(cells):
    cells = set(cells); out = []
    while cells:
        s = cells.pop(); st = [s]; c = {s}
        while st:
            r, k = st.pop()
            for dr, dk in DIRS8:
                n = (r + dr, k + dk)
                if n in cells: cells.discard(n); c.add(n); st.append(n)
        out.append(c)
    return out


def centroid(c): return (sum(r for r, _ in c) / len(c), sum(k for _, k in c) / len(c))


def classify(fn, inp, exp, pred):
    f = {}
    if dims(pred) != dims(exp): return 'size', f
    x = pred
    for k in range(1, 9):
        x = call(fn, x)
        if x is None: break
        if x == exp: f['iterate_k'] = k; return 'iterate', f
        if x == pred: break
    H, W = dims(exp)
    same = dims(inp) == dims(exp)
    base = inp if same else None
    bgc = Counter(v for r in inp for v in r).most_common(1)[0][0]
    ref = base if same else [[bgc] * W for _ in range(H)]
    Ce = {(r, k) for r in range(H) for k in range(W) if exp[r][k] != ref[r][k]}
    Cp = {(r, k) for r in range(H) for k in range(W) if pred[r][k] != ref[r][k]}
    R = {(r, k) for r in range(H) for k in range(W) if pred[r][k] != exp[r][k]}
    miss, extra, rec = (R & Ce) - Cp, (R & Cp) - Ce, R & Ce & Cp
    f.update(residual=len(R), missing=len(miss), extra=len(extra), recolour=len(rec), same_size=same)
    if Ce == Cp: return 'colour_only', f
    if Cp and Ce and len(Cp) == len(Ce):                      # one translation of the change set (with its colours)
        a = min(Cp); b = min(Ce); dv = (b[0] - a[0], b[1] - a[1])
        if {(r + dv[0], k + dv[1]) for r, k in Cp} == Ce and all(pred[r][k] == exp[r + dv[0]][k + dv[1]] for r, k in Cp):
            f['shift'] = dv; return 'shift', f
    if not same: return 'mixed', f
    if miss and not extra and not rec:
        tips = {(r, k) for r, k in Cp if sum((r + dr, k + dk) in Cp for dr, dk in ((1, 0), (-1, 0), (0, 1), (0, -1))) <= 1}
        if tips:
            near = {(r + dr, k + dk) for r, k in tips for dr in (-1, 0, 1) for dk in (-1, 0, 1)}
            if miss <= near: f['tips'] = len(tips); return 'on_stop_paint', f
            rays = set()
            for r, k in tips:
                for dr, dk in DIRS8:
                    i, j = r + dr, k + dk
                    while 0 <= i < H and 0 <= j < W:
                        rays.add((i, j)); i += dr; j += dk
            if miss <= rays: f['tips'] = len(tips); return 'on_stop_turn', f
        objs = [c for c in comps({(r, k) for r in range(H) for k in range(W) if inp[r][k] != bgc}) if len(c) >= 1]
        cen = [centroid(c) for c in objs]
        rows = [{r for r, _ in c} for c in objs]; cols = [{k for _, k in c} for c in objs]
        mid = inter = False
        for mc in comps(miss):
            m = centroid(mc)
            if len(cen) <= 40:
                for i in range(len(cen)):
                    for j in range(i + 1, len(cen)):
                        if abs((cen[i][0] + cen[j][0]) / 2 - m[0]) <= 0.5 and abs((cen[i][1] + cen[j][1]) / 2 - m[1]) <= 0.5:
                            mid = True
            mr = {r for r, _ in mc}; mk = {k for _, k in mc}
            for i in range(len(objs)):
                for j in range(len(objs)):
                    if i != j and mr & rows[i] and mk & cols[j] and not (mr & rows[j] and mk & cols[j]):
                        inter = True
        if mid: return 'anchor_midpoint', f
        if inter: return 'anchor_inter', f
        return 'anchor_other', f
    if extra and not miss and not rec:
        over = any(inp[r][k] != bgc for r, k in extra)
        return ('accept_overlap' if over else 'accept_extra'), f
    return 'mixed', f


SLOT = {'iterate': 'iterate', 'colour_only': 'colour', 'shift': 'anchor', 'on_stop_paint': 'on_stop', 'on_stop_turn': 'on_stop',
        'accept_overlap': 'accept', 'accept_extra': 'accept', 'anchor_midpoint': 'anchor', 'anchor_inter': 'anchor',
        'anchor_other': 'anchor', 'mixed': '-', 'size': '-', 'nofit': '-'}


def run_density(part, parts):
    fams = {(d, n): M for d, n, M, _ in D.families()}
    rows = []
    for p in sorted(os.listdir(os.path.join(REPO, 'results/o0'))):
        if p.startswith('t75_density_') and p.endswith('.jsonl.txt'):
            rows += [json.loads(l) for l in open(os.path.join(REPO, 'results/o0', p)) if l.strip()]
    bad = [r for r in rows if not r['exact']]
    by = defaultdict(list)
    for r in bad: by[(r['task'], r['v'])].append(r)
    keys = sorted(by)[part::parts]
    out = open(os.path.join(REPO, 'results/o0/t72p_density_%d.jsonl.txt' % part), 'w')
    t0 = time.time()
    for i, (t, v) in enumerate(keys):
        mod = importlib.import_module('tasks.task_' + t)
        T = D.variant(mod, t, v)
        if T is None: continue
        inp, exp = T['test'][0]['input'], T['test'][0]['output']
        for r in by[(t, v)]:
            ff = fit_fn(fams[(r['dir'], r['family'])], T['train'])
            if not ff: lab, f = 'nofit', {}
            else: lab, f = classify(ff[1], inp, exp, call(ff[1], inp))
            out.write(json.dumps(dict(task=t, v=v, dir=r['dir'], family=r['family'], member=r['member'], label=lab, slot=SLOT[lab], **f)) + '\n')
        if i % 200 == 0:
            out.flush(); print(json.dumps({'done': i, 'of': len(keys), 's': round(time.time() - t0)}), flush=True)
    out.close()


def run_design(dirs):
    import line_check as LC
    out = open(os.path.join(REPO, 'results/o0/t72p_design.jsonl.txt'), 'w')
    for d in dirs:
        latest = {}
        for l in open(os.path.join(REPO, 'results/o0/%s_ledger.jsonl.txt' % d)):
            row = json.loads(l); latest[row['concept']] = row
        for c, row in sorted(latest.items()):
            s = importlib.util.spec_from_file_location('C_%s_%s' % (d, c), os.path.join(REPO, 'tools/dream/o0', d, c + '.py'))
            M = importlib.util.module_from_spec(s); s.loader.exec_module(M)
            for k in row.get('wrong_other', []):
                t = LC.task(k)
                if t is None: continue
                T, S = t
                ff = fit_fn(M, T['train'])
                if not ff: lab, f = 'nofit', {}
                else:
                    preds = [call(ff[1], q['input']) for q in T['test']]
                    i = next((i for i in range(len(S)) if preds[i] != S[i]), 0)   # first missed test input
                    lab, f = classify(ff[1], T['test'][i]['input'], S[i], preds[i])
                out.write(json.dumps(dict(task=k, dir=d, family=c, label=lab, slot=SLOT[lab], **f)) + '\n')
    out.close()


def summarise(mode):
    rows = []
    for p in sorted(os.listdir(os.path.join(REPO, 'results/o0'))):
        if p.startswith('t72p_%s' % mode) and p.endswith('.jsonl.txt'):
            rows += [json.loads(l) for l in open(os.path.join(REPO, 'results/o0', p)) if l.strip()]
    s = {'mode': mode, 'cases': len(rows)}
    for grp, sel in (('non_source', lambda r: not r.get('member', False)), ('member', lambda r: r.get('member', False))):
        rr = [r for r in rows if sel(r)]
        if not rr: continue
        lab = Counter(r['label'] for r in rr)
        tasks = defaultdict(set); fams = defaultdict(set)
        for r in rr: tasks[r['label']].add(r['task']); fams[r['label']].add(r['family'])
        s[grp] = {'cases': len(rr), 'distinct_tasks': len({r['task'] for r in rr}),
                  'by_label': {k: {'cases': n, 'tasks': len(tasks[k]), 'families': len(fams[k])} for k, n in lab.most_common()},
                  'by_slot': dict(Counter(r['slot'] for r in rr).most_common())}
    json.dump(s, open(os.path.join(REPO, 'results/o0/t72p_%s_summary.json' % mode), 'w'), indent=1)
    print(json.dumps(s, indent=1))


if __name__ == '__main__':
    m = sys.argv[1]
    if m == 'density': run_density(int(sys.argv[2]) if len(sys.argv) > 2 else 0, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
    elif m == 'design': run_design(sys.argv[2:] or ['priors3', 'priors4'])
    elif m == 'summary': summarise(sys.argv[2])
