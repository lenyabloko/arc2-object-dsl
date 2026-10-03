"""Structured prior distillation, batch checker (Fable v23 C.7 a.i / v23a item 1).

A reading (written by a model from a task's training pairs and test inputs only) is a situation in the v19 form:
S = HOW(arg1..argk) + WHY. This script is the translator's back end and the judge:
  1. normalise: HOW must be one of the engine's 8 columns; otherwise the reading's own verb is looked up in the L4
     draft (l4_verbs.json). A verb with no executor is recorded as a frame that aligns but cannot solve.
  2. new rows: a reading may define cell-set rows as Datalog over the base relations (cell / obj / off / px); each
     is stored under parts/ and registered as a row, namespaced per task and sample.
  3. exact training fit with the engine as it stands (situation_engine depth 1; map / seq forms through
     scale_free, as overnight_check.fit_spec). An argument given as "open" is bound by the engine over that slot's
     domain (the slot is reported open).
  4. one harness check per task (ledger results/o0/distill_harness.json; a second check is refused, G87): the fitted
     situations of all samples are pooled, ordered by the number of samples that support the same frame key (G48),
     then by scale_free.order_key; the first two distinct predictions are the two attempts. The check runs only if
     some fit predicts every test input; otherwise the task is recorded as abstaining (no check spent).
  5. frames and parts are recorded with their fillers (the row cells each slot bound on each training input).
usage: python3 distill_check.py <batch.json> [group ...]     writes results/o0/distill_b<batch>_<group>.json
       python3 distill_check.py --summary <batch.json>       writes results/o0/distill_b<batch>_summary.json"""
import glob, itertools, json, os, re, signal, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); O0 = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(O0, '..', '..', '..'))
sys.path.insert(0, O0)
import line_check as LC
import defrows, situation_engine as SE, scale_free as SF
from overnight_check import fit_spec

L4 = json.load(open(os.path.join(HERE, 'l4_verbs.json')))
COLS = L4['columns']
LEDGER = os.path.join(REPO, 'results/o0/distill_harness.json')
PARTS = os.path.join(HERE, 'parts'); os.makedirs(PARTS, exist_ok=True)


class TO(Exception): pass


def _alarm(s, f): raise TO()


signal.signal(signal.SIGALRM, _alarm)


def timed(fn, secs, *a):
    signal.alarm(secs)
    try: return fn(*a)
    except TO: return 'timeout'
    finally: signal.alarm(0)


def norm_verb(v):
    v = (v or '').strip().lower()
    if v in COLS: return v, 'column'
    if v in L4['verbs']: return L4['verbs'][v][0], L4['verbs'][v][1]
    w = v.split(' ')[0] if v else ''
    if w in L4['verbs']: return L4['verbs'][w][0], L4['verbs'][w][1] + ' (first word)'
    return None, 'not in L4'


def register_rows(task, k, rows):
    """new rows -> registered names (namespaced); returns ({given: internal}, errors)"""
    names, errs = {}, []
    for r in rows or []:
        nm = re.sub(r'[^a-z0-9_]', '_', str(r.get('name', '')).lower()).strip('_') or 'row'
        text = r.get('datalog', '')
        if not re.search(r'%\s*output:\s*[a-z_][a-z0-9_]*\(', text):
            out = r.get('output') or nm
            text = f'% output: {out.split("(")[0]}(Y, X)\n' + text
        internal = f'd_{task}_{k}_{nm}'
        p = os.path.join(PARTS, internal + '.dl.txt')
        open(p, 'w').write(f'% row: {internal}\n% source: distillation batch reading, task {task}, sample {k}\n' + text)
        try:
            row = defrows.load(p)
            SE.ROWS[internal] = row; SE.DEF_ROWS[internal] = row; defrows.DEF_ROWS[internal] = row
            names[r.get('name')] = internal
        except Exception as e:
            errs.append(f'{nm}: {type(e).__name__}: {str(e)[:120]}')
    return names, errs


def spec_of(fr, names):
    """the reading's frame -> (spec with 'open' slots, list of (path, domain) for open slots, problems)"""
    probs = []
    if fr.get('form') == 'map':
        sub, opens, p = spec_of(fr.get('sub', {}), names); probs += p
        sc = fr.get('scale')
        if sc not in SF.SCALES: probs.append(f'scale {sc!r} not in {SF.SCALES}')
        return {'form': 'map', 'scale': sc, 'sub': sub}, [(('sub',) + q, d) for q, d in opens], probs
    if fr.get('form') == 'seq':
        a, oa, pa = spec_of(fr.get('sub', {}), names); b, ob, pb = spec_of(fr.get('outer', {}), names)
        return {'form': 'seq', 'sub': a, 'outer': b}, [(('sub',) + q, d) for q, d in oa] + [(('outer',) + q, d) for q, d in ob], pa + pb
    how = fr.get('how')
    if how not in SE.COLUMNS: return None, [], [f'how {how!r} has no executor']
    C = SE.COLUMNS[how]; args = {}; opens = []
    for a, dom in C['args']:
        v = (fr.get('args') or {}).get(a, 'open')
        if v in names: v = names[v]
        if v == 'open' or v is None: opens.append(((a,), dom)); args[a] = None
        elif v in dom or (v in SE.ROWS and v.startswith('d_')): args[a] = v
        else: probs.append(f'{how}.{a} = {v!r} not in domain'); opens.append(((a,), dom)); args[a] = None
    extra = set((fr.get('args') or {})) - {a for a, _ in C['args']}
    if extra: probs.append(f'unknown args {sorted(extra)}')
    return {'how': how, 'args': args}, opens, probs


def setp(spec, path, v):
    """bind the open slot at path (('anchors',) | ('sub', 'anchors') | ('outer', 'key')) to v"""
    s = json.loads(json.dumps(spec)); cur = s
    for p in path[:-1]: cur = cur[p]
    cur['args'][path[-1]] = v
    return s


def fillers(S, train):
    """for each slot bound to a row: the number of cells and colours it binds on each training input"""
    out = {}
    def walk(s, pre=''):
        if s.get('form') == 'map': walk(s['sub'], pre + 'map.')
        elif s.get('form') == 'seq': walk(s['sub'], pre + 'seq1.'); walk(s['outer'], pre + 'seq2.')
        else:
            for a, v in s['args'].items():
                if v in SE.ROWS:
                    vals = []
                    for p in train:
                        try:
                            r = SE.ROWS[v](p['input'], SE.bgc(p['input']))
                            cells = r if isinstance(r, (set, frozenset, list)) else None
                            vals.append(None if cells is None else [len(cells), sorted({p['input'][y][x] for y, x in cells if isinstance(y, int)})])
                        except Exception:
                            vals.append('err')
                    out[pre + s['how'] + '.' + a + '=' + v] = vals
    walk(S); return out


def slot_match(R, names, train):
    """for every new row of the reading: is it the set of changed cells on every training pair (same-size pairs)?"""
    out = {}
    for given, internal in names.items():
        rel = []
        for p in train:
            g, o = p['input'], p['output']
            if len(g) != len(o) or len(g[0]) != len(o[0]): rel.append('size'); continue
            try: r = SE.ROWS[internal](g, SE.bgc(g)) or set()
            except Exception: rel.append('err'); continue
            ch = {(y, x) for y in range(len(g)) for x in range(len(g[0])) if g[y][x] != o[y][x]}
            rel.append('equal' if r == ch else 'superset' if ch < r else 'subset' if r < ch else 'other')
        out[given] = rel
    return out


def frame_key(S):
    """the frame: the situation without its training-bound constants (rows named, distilled rows as 'd_row')"""
    if S.get('form') == 'map': return f"map[{S['scale']}]({frame_key(S['sub'])})"
    if S.get('form') == 'seq': return f"seq({frame_key(S['sub'])} ; {frame_key(S['outer'])})"
    a = ', '.join(f"{k}:={'d_row' if str(v).startswith('d_') else v}" for k, v in sorted(S['args'].items()))
    return f"{S['how']}({a})"


def check_reading(task, k, R, train):
    rec = {'task': task, 'sample': k, 'verb': R.get('verb'), 'reading': R.get('reading', '')[:400], 'why': R.get('why', '')[:300]}
    fr = R.get('frame') or {}
    if fr.get('form') not in ('map', 'seq'):
        how = fr.get('how')
        if how not in COLS:
            col, rel = norm_verb(how if how and how != 'other' else R.get('verb'))
            rec['l4'] = rel
            if col: fr = dict(fr, how=col)
    names, errs = register_rows(task, k, R.get('new_rows'))
    rec['new_rows'] = list(names.values()); rec['row_errors'] = errs
    if names: rec['row_vs_changed'] = slot_match(R, names, train)
    spec, opens, probs = spec_of(fr, names)
    rec['problems'] = probs
    if spec is None:
        rec.update(executable=False, fits=[], n_open=0); return rec, []
    rec['executable'] = True; rec['n_open'] = len(opens); rec['open'] = ['.'.join(p) for p, _ in opens]
    fits = []
    combos = list(itertools.product(*[d for _, d in opens])) if opens else [()]
    t0 = time.time()
    for vals in combos[:64]:
        s = spec
        for (p, _), v in zip(opens, vals): s = setp(s, p, v)
        r = timed(fit_spec, 30, s, train)
        if r == 'timeout': rec.setdefault('timeouts', 0); rec['timeouts'] += 1; continue
        fits += r[0]
        if time.time() - t0 > 120: rec['time_capped'] = True; break
    rec['fits'] = [SF.key(S) for S in fits][:8]; rec['n_fits'] = len(fits)
    rec['frames'] = sorted({frame_key(S) for S in fits})
    if fits: rec['fillers'] = fillers(fits[0], train)
    return rec, fits


def harness(task, pooled):
    L = json.load(open(LEDGER)) if os.path.exists(LEDGER) else {}
    if task in L: return L[task]['result'] + ' (ledger)'
    T, sol = LC.task(task)
    preds = []
    first = None
    for S, sup, mo in sorted(pooled, key=lambda t: (-t[1], t[2], SF.order_key(t[0]))):   # support, then fewest open slots
        try: p = [SF.apply(S, q['input']) for q in T['test']]
        except Exception: continue
        if any(v is None for v in p) or p in preds: continue
        preds.append(p)
        if first is None: first = {'key': SF.key(S), 'support': sup, 'n_open': mo}
        if len(preds) == 2: break
    if not preds: return 'abstains (no fit predicts every test input; no check spent)'
    res = 'exact' if all(any(p[i] == sol[i] for p in preds) for i in range(len(sol))) else 'wrong'
    L[task] = {'result': res, 'n_predictions': len(preds), 'first': first, 'program': 'distillation batch 1 readings, pooled by support (G48), then fewest open slots'}
    json.dump(L, open(LEDGER, 'w'), indent=1)
    return res


def run_group(batch, gi):
    B = json.load(open(batch)); grp = B['groups'][gi]
    out = {'group': gi, 'tasks': {}}
    files = sorted(glob.glob(os.path.join(HERE, 'readings', f'g{gi:02d}_s*.json')))
    readings = {k: [] for k in grp}
    for f in files:
        s = int(re.search(r'_s(\d+)\.json$', f).group(1))
        try: D = json.load(open(f))
        except Exception as e: out.setdefault('bad_files', []).append(f'{os.path.basename(f)}: {e}'); continue
        for R in (D if isinstance(D, list) else D.get('readings', [])):
            if R.get('task') in readings: readings[R['task']].append((s, R))
    for task in grp:
        train = LC.task(task)[0]['train']
        recs = []; pooled = {}
        for s, R in readings[task]:
            rec, fits = check_reading(task, s, R, train)
            recs.append(rec)
            for S in fits:
                key = SF.key(S)
                if key not in pooled: pooled[key] = [S, set(), 99]
                pooled[key][1].add(s); pooled[key][2] = min(pooled[key][2], rec.get('n_open', 99))
        pool = [(S, len(ss), mo) for S, ss, mo in pooled.values()]
        res = ('not run (NOHARNESS)' if os.environ.get('NOHARNESS') else harness(task, pool)) if pool else 'no fit'
        out['tasks'][task] = {'n_readings': len(recs), 'n_executable': sum(r['executable'] for r in recs),
                              'n_fitting': sum(bool(r.get('n_fits')) for r in recs), 'harness': res,
                              'max_support': max((n for _, n, _ in pool), default=0), 'readings': recs}
    p = os.path.join(REPO, f"results/o0/distill_b{B['batch']}_g{gi:02d}.json")
    json.dump(out, open(p, 'w'), indent=1)
    return out


if __name__ == '__main__':
    if sys.argv[1] == '--summary':
        B = json.load(open(sys.argv[2])); rows = []
        for f in sorted(glob.glob(os.path.join(REPO, f"results/o0/distill_b{B['batch']}_g*.json"))):
            rows.append(json.load(open(f)))
        print(len(rows), 'groups checked')
    else:
        for g in sys.argv[2:]:
            o = run_group(sys.argv[1], int(g))
            t = o['tasks']
            print(g, 'tasks', len(t), 'readings', sum(v['n_readings'] for v in t.values()), 'fitting tasks', sum(v['n_fitting'] > 0 for v in t.values()),
                  'harness', {r: sum(v['harness'].startswith(r) for v in t.values()) for r in ('exact', 'wrong', 'abstains', 'no fit')})
