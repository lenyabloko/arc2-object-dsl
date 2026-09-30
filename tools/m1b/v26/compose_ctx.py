"""compose_ctx: inter-part CONTEXT composition.   part_out = OP(part_in, ctx)   [optionally + a library program]

A program here is   partition -> for every part: ctx = ROLE(part) -> OP(part, ctx) on the parts a PREDICATE
selects -> reassemble, every step induced from the training pairs; the whole program is verified on all
training pairs, then must pass a held-out-pair (leave-one-out) re-induction check.

Search space
  partitions   the partitions of compose_lift (imported, not copied): sep panels, bgsep bands (rc / r / c),
               frame interiors, equal blocks (nh x nw), object bounding boxes (8-conn multi-colour, 4- and 8-conn
               single-colour; INPLACE only, boxes must be disjoint); plus 'sepx': separator lines of any colour,
               the grid's majority colour included.
  ROLE (ctx)   'sel'  one global context part chosen by a lift selector (max / min attribute, odd-one-out,
                      has / lacks / most of a colour, fixed index): template, key, marker part ...
               'next' / 'prev' in reading order (cyclic or not); 'right' / 'left' / 'down' / 'up' neighbour in
                      the part lattice (cyclic or not); 'mh' / 'mv' / 'mp' mirror part (row / column / point
                      mirror of the lattice position).
  OP           'cell' cellwise table   out[y][x] = E(key)   with the ctx optionally transformed by one of D8
                      (dims must agree).  key = nothing ('u'), the ctx cell or the part cell or both, as a colour
                      ROLE (rank in its part by count; ties: scene background, first cell) or as a literal colour.
                      E = the part cell, the ctx cell, a role colour of the part or of the ctx, or a literal
                      colour; per key the consistent expressions are intersected (bit masks) and the first in
                      prior order is used.  The simplest key mode that is consistent wins.  Covers copy ctx,
                      overlay either way, stamp, swap, recolour ctx with the part's colours, boolean and/or/xor.
               'recol' per-colour recolour of the part (no cell alignment with ctx): part colour (role or
                      literal) -> the same colour, a role colour of the ctx or of the part, or a literal colour
                      (fill the part's background with ctx's colour, band i recoloured by band i+1 ...).
               'lib'  (after 'cell' / 'recol' when no table fits) one library program on the pooled
                      (OP result, output part) pairs, re-induced by compose_lift.lib_search.
  PREDICATE    which parts get OP (the others must be unchanged): all, not-the-ctx, has / lacks colour c,
               number of colours; the first predicate (prior order) that takes every changed part and leaves out
               every part OP would change wrongly.
  modes        INPLACE  same-size tasks, disjoint regions, cells outside regions unchanged.
               PROG     output = the NEXT panel of the input's panel sequence (reading order, forward or
                      backward, blank panels skipped as the canvas): per colour translation extrapolated by one
                      step, or growth continued (the cells added between the last two panels, shifted by the
                      unit step).  Output: the panel or the panel with its one-cell separator frame.
Generalisation check: re-induction on all training pairs but one predicts the held-out pair exactly (last pair
with a change; also the first one when >= 3 pairs change).  Test predictions proposed by several hypotheses
are ranked first (votes); at most 3 programs with distinct predictions are returned.
Budget: the DETERMINISTIC work counter of compose_lift (tick / Budget / work_cap / SEC); no clocks, no timers,
no signals.  Charges: one partition (lift's cost), one table fit / prediction (HYP_BASE + CELL_UNIT per cell
visited), library enumerations (lift's cost model).  <= 19 s of work per task.
"""
import sys
sys.path.append('/home/claude/work/widen'); sys.path.append('/home/claude/work/latent')
import gdsl
import compose_lift as L
from gdsl import H, W, colours
from collections import Counter

TOTAL_BUDGET = 19.0
DEBUG = False
DIAG = Counter()

HYP_BASE = 2_000                 # work units: one hypothesis fit / prediction pass (base)
CELL_UNIT = 6                    # work units per cell visited by a table fit or prediction (calibrated: >= CPU)
tick = L.tick
_Timeout = L._Timeout
SEC = L.SEC


def _cells(g):
    return len(g) * len(g[0]) if g and g[0] else 0


def dims(g):
    return (len(g), len(g[0]) if g else 0)


def d8(g, t):
    if t == 0: return g
    if t == 1: return [r[::-1] for r in g]
    if t == 2: return g[::-1]
    if t == 3: return [r[::-1] for r in g[::-1]]
    T = [list(r) for r in zip(*g)]
    if t == 4: return T
    if t == 5: return [r[::-1] for r in T]
    if t == 6: return T[::-1]
    return [r[::-1] for r in T[::-1]]


D8N = ('id', 'flipH', 'flipV', 'rot180', 'transpose', 'rot90', 'rot270', 'antitranspose')


def roles(g, sbg, rs=0):
    """Colours of a part in role order.  rs 0: the scene background first (when present), then by count, first
    cell; rs 1: by count (ties: the scene background first, then first cell)."""
    cnt = Counter(); first = {}
    for y, row in enumerate(g):
        for x, v in enumerate(row):
            cnt[v] += 1
            if v not in first: first[v] = (y, x)
    if rs: return sorted(cnt, key=lambda c: (-cnt[c], c != sbg, first[c]))
    return sorted(cnt, key=lambda c: (c != sbg, -cnt[c], first[c]))


MAXR = 4


def _ridx(rl, v):
    try:
        k = rl.index(v)
    except ValueError:
        return MAXR
    return k if k < MAXR else MAXR


# expression bits: 0 P (part cell), 1 C (ctx cell), 2..5 part role k, 6..9 ctx role k, 10..19 literal colour
def _cand(o, p, c, pr, cr, aligned):
    m = 1 << (10 + o)
    if o == p: m |= 1
    if aligned and o == c: m |= 2
    for k in range(min(MAXR, len(pr))):
        if pr[k] == o: m |= 1 << (2 + k)
    if cr is not None:
        for k in range(min(MAXR, len(cr))):
            if cr[k] == o: m |= 1 << (6 + k)
    return m


def _eval(e, p, c, pr, cr):
    if e == 0: return p
    if e == 1: return c
    if e < 6:
        k = e - 2
        return pr[k] if k < len(pr) else None
    if e < 10:
        k = e - 6
        return cr[k] if cr is not None and k < len(cr) else None
    return e - 10


def _low(m):
    return (m & -m).bit_length() - 1


def _enames(e):
    if e == 0: return 'P'
    if e == 1: return 'C'
    if e < 6: return f'p{e - 2}'
    if e < 10: return f'c{e - 6}'
    return f'#{e - 10}'


KEYMODES_ALIGNED = ('u', 'cr', 'pr', 'pcr', 'cl', 'pl', 'pcl')
KEYMODES_RECOL = ('u', 'pr', 'pl')


def _key(mode, p, c, pr, cr):
    if mode == 'u': return 0
    if mode == 'cr': return _ridx(cr, c)
    if mode == 'pr': return _ridx(pr, p)
    if mode == 'pcr': return (_ridx(pr, p), _ridx(cr, c))
    if mode == 'cl': return c
    if mode == 'pl': return p
    return (p, c)


def table_fit(recs, aligned, t, rs=0):
    """recs: [(part grid, ctx grid, out grid, scene bg)].  Returns (keymode, {key: expr}) for the simplest
    consistent key mode, or None."""
    prep = []
    for pg, cg, og, sbg in recs:
        if dims(og) != dims(pg): return None
        pr = roles(pg, sbg, rs); cr = roles(cg, sbg, rs) if cg is not None else None
        cgt = d8(cg, t) if aligned else None
        if aligned and dims(cgt) != dims(pg): return None
        cells = []
        for y in range(len(pg)):
            prow, orow = pg[y], og[y]
            crow = cgt[y] if aligned else None
            for x in range(len(prow)):
                p = prow[x]; c = crow[x] if aligned else None
                cells.append((p, c, _cand(orow[x], p, c, pr, cr, aligned)))
        tick(HYP_BASE + CELL_UNIT * len(cells))
        prep.append((pr, cr, cells))
    for mode in (KEYMODES_ALIGNED if aligned else KEYMODES_RECOL):
        tab = {}; ok = True
        for pr, cr, cells in prep:
            for p, c, m in cells:
                k = _key(mode, p, c, pr, cr)
                v = tab.get(k, -1) & m
                if not v: ok = False; break
                tab[k] = v
            if not ok: break
        if ok:
            tick(CELL_UNIT * sum(len(x[2]) for x in prep))
            return mode, {k: _low(v) for k, v in tab.items()}
    tick(CELL_UNIT * len(KEYMODES_ALIGNED) * sum(len(x[2]) for x in prep))
    return None


def table_apply(model, pg, cg, sbg, aligned, t, rs=0):
    mode, tab = model
    tick(HYP_BASE + CELL_UNIT * _cells(pg))
    pr = roles(pg, sbg, rs); cr = roles(cg, sbg, rs) if cg is not None else None
    if aligned:
        cgt = d8(cg, t)
        if dims(cgt) != dims(pg): return None
    out = []
    for y in range(len(pg)):
        prow = pg[y]; crow = cgt[y] if aligned else None; orow = []
        for x in range(len(prow)):
            p = prow[x]; c = crow[x] if aligned else None
            e = tab.get(_key(mode, p, c, pr, cr))
            if e is None: return None
            v = _eval(e, p, c, pr, cr)
            if v is None: return None
            orow.append(v)
        out.append(orow)
    return out


def model_name(model):
    mode, tab = model
    if mode == 'u': return _enames(tab[0])
    items = sorted(tab.items(), key=lambda kv: str(kv[0]))
    return mode + '{' + ','.join(f"{k}:{_enames(e)}" for k, e in items[:8]) + (',..' if len(items) > 8 else '') + '}'


# ------------------------------------------------------------------ partitions
def sepx_layout(g):
    """Like compose_lift.sep_layout, but the separator colour may be the grid's majority colour too (panels
    between full-length single-colour lines; the colour giving the most panels, non-majority first on ties)."""
    h, w = H(g), W(g); bg = L._ORIG_BG(g); best = None
    for sc in sorted(colours(g)):
        rows = [r for r in range(h) if all(v == sc for v in g[r])]
        cols = [c for c in range(w) if all(g[r][c] == sc for r in range(h))]
        if not rows and not cols: continue
        if len(rows) == h or len(cols) == w: continue
        ri, ci = L._intervals(rows, h), L._intervals(cols, w)
        n = len(ri) * len(ci)
        if n < 2: continue
        if best is None or (n, sc != bg) > best[0]: best = ((n, sc != bg), sc, ri, ci)
    return best[1:] if best else None


def partition(spec, g):
    if spec[0] != 'sepx': return L.partition(spec, g)
    tick(L.PART_BASE + L.PART_CELL * _cells(g))
    lay = sepx_layout(g)
    if lay is None: return None
    sc, ri, ci = lay
    ps = [L.Part(a, b, a1 - a + 1, b1 - b + 1, [row[b:b1 + 1] for row in g[a:a1 + 1]]) for a, a1 in ri for b, b1 in ci]
    if len(ps) > L.MAX_PARTS: return None
    for p in ps: p.a['sepc'] = sc
    L._attrs(ps, g)
    return ps


def spec_name(spec):
    return 'sepx' if spec[0] == 'sepx' else L.spec_name(spec)


# ------------------------------------------------------------------ lattice and context roles
def lattice(ps):
    rows = sorted({p.r0 for p in ps}); cols = sorted({p.c0 for p in ps})
    at = {}
    for k, p in enumerate(ps):
        key = (rows.index(p.r0), cols.index(p.c0))
        if key in at: return None
        at[key] = k
    return len(rows), len(cols), at


REL_RULES = [('next', True), ('prev', True), ('next', False), ('prev', False), ('right', True), ('left', True),
             ('down', True), ('up', True), ('right', False), ('left', False), ('down', False), ('up', False),
             ('mh',), ('mv',), ('mp',)]


def ctx_map(rule, ps):
    """Index of the context part of every part (None: no context), or None when the rule does not apply."""
    n = len(ps); kind = rule[0]
    if kind == 'sel':
        c = L.select(ps, rule[1])
        if c is None: return None
        i = next(k for k, p in enumerate(ps) if p is c)
        return [i] * n
    if kind in ('next', 'prev'):
        d = 1 if kind == 'next' else -1
        if rule[1]: return [(k + d) % n for k in range(n)]
        return [k + d if 0 <= k + d < n else None for k in range(n)]
    lat = lattice(ps)
    if lat is None: return None
    R, C, at = lat
    pos = {k: rc for rc, k in at.items()}
    out = []
    for k in range(n):
        r, c = pos[k]
        if kind in ('right', 'left', 'down', 'up'):
            dr, dc = {'right': (0, 1), 'left': (0, -1), 'down': (1, 0), 'up': (-1, 0)}[kind]
            if (kind in ('right', 'left') and C < 2) or (kind in ('down', 'up') and R < 2): return None
            rr, cc = r + dr, c + dc
            if rule[1]: rr %= R; cc %= C
        elif kind == 'mh': rr, cc = r, C - 1 - c
        elif kind == 'mv': rr, cc = R - 1 - r, c
        else: rr, cc = R - 1 - r, C - 1 - c
        out.append(at.get((rr, cc)))
    return out


def rule_name(rule):
    if rule[0] == 'sel': return f"sel-{rule[1][0]}-{rule[1][1]}"
    if len(rule) == 1: return rule[0]
    return rule[0] + ('-cyc' if rule[1] else '')


# ------------------------------------------------------------------ predicates (which parts get OP)
def _pred_list(palette, ncols):
    ps = [('all',), ('notctx',)]
    for c in sorted(palette):
        ps += [('has', c), ('lacks', c)]
    for n in sorted(ncols):
        ps.append(('ncol', n))
    ps.append(('ncol>=', 2))
    return ps


def pred_ok(pred, pt, is_ctx):
    k = pred[0]
    if k == 'all': return True
    if k == 'notctx': return not is_ctx
    cs = pt.a.get('allc')
    if cs is None:
        cs = frozenset(v for r in pt.g for v in r); pt.a['allc'] = cs
    if k == 'has': return pred[1] in cs
    if k == 'lacks': return pred[1] not in cs
    if k == 'ncol': return len(cs) == pred[1]
    if k == 'ncol>=': return len(cs) >= pred[1]
    return False


# ------------------------------------------------------------------ INPLACE-CTX
INPLACE_SPECS = [('sepx',), ('sep',), ('bgsep', 'rc'), ('bgsep', 'r'), ('bgsep', 'c'), ('frame',),
                 ('obj', True, False, 0, False), ('obj', False, True, 0, False), ('obj', True, True, 0, False)]


def setup_inplace(spec, grids_io):
    """[(parts, out crops or None, scene bg)] per grid; None when the spec does not give disjoint regions that
    hold every change."""
    res = []
    for gi, go in grids_io:
        ps = partition(spec, gi)
        if not ps or len(ps) < 2: return None
        occ = L._disjoint(ps, H(gi), W(gi))
        if occ is None: return None
        sbg = L._ORIG_BG(gi)
        outs = None
        if go is not None:
            if dims(go) != dims(gi): return None
            for y in range(H(gi)):
                ri, ro = gi[y], go[y]
                for x in range(W(gi)):
                    if ri[x] != ro[x] and (y, x) not in occ: return None
            outs = [L.region_crop(go, p.r0, p.c0, p.h, p.w, sbg) for p in ps]
        res.append((ps, outs, sbg))
    return res


class Hyp:
    """One context hypothesis: spec, role rule, op kind ('cell' with D8 t, or 'recol')."""
    def __init__(self, spec, rule, aligned, t, rs=0):
        self.spec, self.rule, self.aligned, self.t, self.rs = spec, rule, aligned, t, rs

    def name(self, model=None, pred=None):
        op = ('cell' + ('' if self.t == 0 else '@' + D8N[self.t])) if self.aligned else 'recol'
        op += '/major' if self.rs else ''
        s = f"ctx[{spec_name(self.spec)}]:{rule_name(self.rule)}:{op}"
        if model is not None: s += ':' + model_name(model)
        if pred is not None and pred != ('all',): s += ':if-' + '-'.join(map(str, pred))
        return s


def fit_hyp(h, setup, palette, ncols):
    """Induce (table model, predicate) of hypothesis h from the setup of some training pairs.  None if none."""
    recs = []; allrecs = []
    for ps, outs, sbg in setup:
        cm = ctx_map(h.rule, ps)
        if cm is None: return None
        for k, pt in enumerate(ps):
            ch = pt.g != outs[k]
            ci = cm[k]
            if ci is None:
                if ch: return None
                continue
            allrecs.append((pt, ps[ci], outs[k], sbg, ci == k, ch))
            if ch: recs.append((pt.g, ps[ci].g, outs[k], sbg))
    if not recs: return None
    model = table_fit(recs, h.aligned, h.t, h.rs)
    if model is None: return None
    good = []
    for pt, cp, o, sbg, isc, ch in allrecs:
        r = o if ch else table_apply(model, pt.g, cp.g, sbg, h.aligned, h.t, h.rs)
        good.append(r == o)
    for pred in _pred_list(palette, ncols):
        if all((pred_ok(pred, rc[0], rc[4]) if rc[5] else (g or not pred_ok(pred, rc[0], rc[4])))
               for rc, g in zip(allrecs, good)):
            return model, pred
    return None


def apply_hyp(h, model, pred, g):
    ps = partition(h.spec, g)
    if not ps or len(ps) < 2: return None
    if L._disjoint(ps, H(g), W(g)) is None: return None
    cm = ctx_map(h.rule, ps)
    if cm is None: return None
    sbg = L._ORIG_BG(g); canvas = L.copyg(g)
    for k, pt in enumerate(ps):
        ci = cm[k]
        if ci is None or not pred_ok(pred, pt, ci == k): continue
        r = table_apply(model, pt.g, ps[ci].g, sbg, h.aligned, h.t, h.rs)
        if r is None: return None
        L.paste(canvas, r, pt.r0, pt.c0)
    return canvas


def _palette(setup):
    pal = set(); nc = set()
    for ps, _, _ in setup:
        for pt in ps:
            cs = frozenset(v for r in pt.g for v in r); pt.a['allc'] = cs
            pal |= cs; nc.add(len(cs))
    return pal, nc


def try_inplace_ctx(task, budget, emit):
    train, test = task['train'], task['test']
    io = [(p['input'], p['output']) for p in train]
    tin = [p['input'] for p in train]
    specs = list(INPLACE_SPECS) + L._block_specs(tin + [t['input'] for t in test], limit=3)
    changed_pairs = [j for j, (a, b) in enumerate(io) if a != b]
    if not changed_pairs: return
    folds = [changed_pairs[-1]] + ([changed_pairs[0]] if len(changed_pairs) >= 3 else [])
    seen = set()
    for spec in specs:
        if budget.left() < 0.5: return
        st = setup_inplace(spec, io)
        if st is None: continue
        key = tuple((p.r0, p.c0, p.h, p.w) for ps, _, _ in st for p in ps)
        if key in seen: continue
        seen.add(key)
        tst = setup_inplace(spec, [(t['input'], None) for t in test])
        if tst is None: continue
        pal, nc = _palette(st)
        _palette(tst)
        ns = {len(ps) for ps, _, _ in st + tst}
        rules = [('sel', s) for s in L._selectors(tin, ns.pop() if len(ns) == 1 else 0)] + REL_RULES
        if DEBUG: print(' spec', spec_name(spec), 'parts', [len(x[0]) for x in st], 'rules', len(rules), flush=True)
        n_emit = 0
        for rule in rules:
            if budget.left() < 0.5: return
            sig = []
            ok = True
            for ps, _, _ in st + tst:
                cm = ctx_map(rule, ps)
                if cm is None: ok = False; break
                sig.append(tuple(cm))
            if not ok: continue
            sig = (tuple(sig))
            if (key, sig) in seen: continue          # same context assignment as an earlier rule
            seen.add((key, sig))
            for aligned, t, rs in OPS:
                h = Hyp(spec, rule, aligned, t, rs)
                fm = fit_hyp(h, st, pal, nc)
                if fm is None: continue
                model, pred = fm
                if not _loo(h, st, folds, pal, nc, io):
                    DIAG['loo_reject'] += 1
                    continue
                F = lambda g, h=h, model=model, pred=pred: apply_hyp(h, model, pred, g)
                cost = 20 + (0 if aligned else 1) + (2 if t else 0) + rs + _mode_cost(model) + (0 if pred == ('all',) else 1) \
                    + (0 if rule[0] != 'sel' else 1)
                if emit(h.name(model, pred), cost, F):
                    n_emit += 1
                break                                  # first op kind that fits for this rule
            if n_emit >= 4: break


OPS = [(True, 0, 0), (False, 0, 0), (True, 0, 1), (False, 0, 1)] + [(True, t, 0) for t in range(1, 8)]


def _mode_cost(model):
    return {'u': 0, 'cr': 1, 'pr': 1, 'pcr': 2, 'cl': 2, 'pl': 2, 'pcl': 3}[model[0]]


def _loo(h, st, folds, pal, nc, io):
    for j in folds:
        rest = [s for i, s in enumerate(st) if i != j]
        if not any(any(pt.g != o for pt, o in zip(ps, outs)) for ps, outs, _ in rest): return False
        fm = fit_hyp(h, rest, pal, nc)
        if fm is None: return False
        if apply_hyp(h, fm[0], fm[1], io[j][0]) != io[j][1]: return False
    return True




# ------------------------------------------------------------------ INPLACE-CTX + library (part level)
def _base_op(op, pg, cg, sbg):
    """A fixed binary operator whose result a library program then transforms: 'C' copy ctx, 'Co' ctx overlaid
    on the part (ctx non-background cells win), 'Po' the part overlaid on the ctx."""
    if dims(pg) != dims(cg): return None
    if op == 'C': return [r[:] for r in cg]
    pb, cb = roles(pg, sbg, 1)[0], roles(cg, sbg, 1)[0]
    if op == 'Co': return [[c if c != cb else p for p, c in zip(rp, rc)] for rp, rc in zip(pg, cg)]
    return [[p if p != pb else c for p, c in zip(rp, rc)] for rp, rc in zip(pg, cg)]


def try_inplace_lib(task, budget, emit, max_calls=4):
    train, test = task['train'], task['test']
    io = [(p['input'], p['output']) for p in train]
    tin = [p['input'] for p in train]
    tbg = L._task_bg(task)
    calls = 0; seen = set()
    for spec in INPLACE_SPECS[:6]:
        st = setup_inplace(spec, io)
        if st is None: continue
        tst = setup_inplace(spec, [(t['input'], None) for t in test])
        if tst is None: continue
        pal, nc = _palette(st); _palette(tst)
        ns = {len(ps) for ps, _, _ in st + tst}
        rules = [('sel', s) for s in L._selectors(tin, ns.pop() if len(ns) == 1 else 0)] + REL_RULES
        for rule in rules:
            maps = [ctx_map(rule, ps) for ps, _, _ in st]
            tmaps = [ctx_map(rule, ps) for ps, _, _ in tst]
            if any(m is None for m in maps + tmaps): continue
            ok = True; recs = []
            for (ps, outs, sbg), cm, j in zip(st, maps, range(len(st))):
                for k, pt in enumerate(ps):
                    if pt.g == outs[k]: continue
                    if cm[k] is None or cm[k] == k or dims(ps[cm[k]].g) != dims(pt.g): ok = False; break
                    recs.append((pt, ps[cm[k]], outs[k], sbg, j))
                if not ok: break
            if not ok or not recs or len({r[4] for r in recs}) < 2: continue
            for op in ('C', 'Co', 'Po'):
                if budget.left() < 1.0 or calls >= max_calls: return
                meta = [(r[0], _base_op(op, r[0].g, r[1].g, r[3]), r[2], r[4]) for r in recs]
                if any(m[1] is None for m in meta): continue
                if all(m[1] == m[2] for m in meta): continue       # the table search owns plain copies
                sig = str([(m[1], m[2]) for m in meta])
                if sig in seen: continue
                seen.add(sig)
                if not L._functional([(m[1], m[2]) for m in meta]): continue
                calls += 1
                res = L.lib_search([(m[1], m[2]) for m in meta], [], budget, cap=2.5, maxp=3, fbg=tbg)
                res = L.loo_filter(meta, res, budget, tbg, None, folds=2, occam=True)
                for name, cost, _, ap in res:
                    F = lambda g, spec=spec, rule=rule, op=op, ap=ap, pal=pal: _apply_lib(spec, rule, op, ap, g)
                    emit(f"ctx[{spec_name(spec)}]:{rule_name(rule)}:{op}>{name}", 32 + cost, F)


def _apply_lib(spec, rule, op, ap, g):
    """Every part whose ctx has its dims and differs from it gets LIB(OP(part, ctx)); other parts kept."""
    ps = partition(spec, g)
    if not ps or len(ps) < 2 or L._disjoint(ps, H(g), W(g)) is None: return None
    cm = ctx_map(rule, ps)
    if cm is None: return None
    sbg = L._ORIG_BG(g); canvas = L.copyg(g)
    for k, pt in enumerate(ps):
        ci = cm[k]
        if ci is None or ci == k or dims(ps[ci].g) != dims(pt.g): continue
        b = _base_op(op, pt.g, ps[ci].g, sbg)
        r = ap(b)
        if r is None or dims(r) != dims(pt.g): return None
        L.paste(canvas, r, pt.r0, pt.c0)
    return canvas


# ------------------------------------------------------------------ PROG (panel sequence extrapolation)
PROG_SPECS = [('sepx',), ('sep',), ('bgsep', 'rc'), ('bgsep', 'r'), ('bgsep', 'c')]
UNIT = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def _colour_sets(g, pbg):
    d = {}
    for y, row in enumerate(g):
        for x, v in enumerate(row):
            if v != pbg: d.setdefault(v, set()).add((y, x))
    return d


def _shift(cells, v):
    return {(y + v[0], x + v[1]) for y, x in cells}


def _translation(a, b):
    """The vector v with a shifted by v == b (None when there is none)."""
    if len(a) != len(b) or not a: return None
    (ya, xa), (yb, xb) = min(a), min(b)
    v = (yb - ya, xb - xa)
    return v if _shift(a, v) == b else None


def _pbg(panels):
    cnt = Counter(v for p in panels for r in p for v in r)
    return cnt.most_common(1)[0][0]


def extrapolate(seq, kind, pbg):
    """Next panel of a panel sequence.  kind 'shift': every changing colour moves by one constant vector per step
    (checked on every consecutive pair of the sequence); 'grow': every changing colour c continues its last step
    by one unit vector v:  out_c = (B_c + shift(added, v)) - shift(removed, v), where added = B_c - A_c,
    removed = A_c - B_c and added lies in A_c shifted by v."""
    A, B = seq[-2], seq[-1]
    h, w = dims(B)
    if any(dims(p) != (h, w) for p in seq): return None
    tick(HYP_BASE + CELL_UNIT * h * w * len(seq))
    sa, sb = _colour_sets(A, pbg), _colour_sets(B, pbg)
    out = [r[:] for r in B]
    if kind == 'shift':
        adds = []
        for c in sorted(set(sa) | set(sb)):
            a, b = sa.get(c, set()), sb.get(c, set())
            if a == b: continue
            v = _translation(a, b)
            if v is None or v == (0, 0): return None
            for k in range(len(seq) - 2):
                pa, pb = _colour_sets(seq[k], pbg).get(c, set()), _colour_sets(seq[k + 1], pbg).get(c, set())
                if _translation(pa, pb) != v: return None
            for y, x in b: out[y][x] = pbg
            adds.append((c, _shift(b, v)))
        if not adds: return None
        for c, cells in adds:
            for y, x in cells:
                if not (0 <= y < h and 0 <= x < w): return None
                out[y][x] = c
        return out
    rem, add = [], {}
    for c in sorted(set(sa) | set(sb)):
        a, b = sa.get(c, set()), sb.get(c, set())
        if a == b: continue
        D, R = b - a, a - b
        vs = [v for v in UNIT if D and D <= _shift(a, v)] if D else [v for v in UNIT if R <= _shift(b, (-v[0], -v[1]))]
        if len(vs) != 1: return None
        v = vs[0]
        rem.append((c, _shift(R, v)))
        for y, x in _shift(D, v) - b:
            if not (0 <= y < h and 0 <= x < w): continue
            if add.get((y, x), c) != c: return None
            add[(y, x)] = c
    if not rem: return None
    for c, cells in rem:
        for y, x in cells:
            if 0 <= y < h and 0 <= x < w and out[y][x] == c and (y, x) not in add: out[y][x] = pbg
    for (y, x), c in add.items(): out[y][x] = c
    return out


def prog_predict(spec, order, drop, kind, asm, g):
    ps = partition(spec, g)
    if not ps or len(ps) < 3 - drop: return None
    idx = list(range(len(ps)))
    if order: idx.reverse()
    seq = [ps[k] for k in idx]
    if drop:
        last, prev = seq[-1], seq[-2]
        if len(colours(last.g)) >= len(colours(prev.g)): return None
        seq = seq[:-1]
    if len(seq) < 2: return None
    pbg = _pbg([p.g for p in seq])
    r = extrapolate([p.g for p in seq], kind, pbg)
    if r is None: return None
    if asm == 'panel': return r
    base = seq[-1]
    ring = L.region_crop(g, base.r0 - 1, base.c0 - 1, base.h + 2, base.w + 2, L._ORIG_BG(g))
    L.paste(ring, r, 1, 1)
    return ring


def try_prog(task, budget, emit):
    train = task['train']
    for spec in PROG_SPECS:
        ps0 = partition(spec, train[0]['input'])
        if not ps0 or len({(p.h, p.w) for p in ps0}) != 1: continue
        h, w = ps0[0].h, ps0[0].w
        o = train[0]['output']
        asms = [a for a, d in (('panel', (h, w)), ('pad1', (h + 2, w + 2))) if dims(o) == d]
        for asm in asms:
            for kind in ('shift', 'grow'):
                for drop in (0, 1):
                    for order in (0, 1):
                        if budget.left() < 0.3: return
                        name = f"ctx-prog[{spec_name(spec)}]:{'rev' if order else 'fwd'}{'-dropblank' if drop else ''}:{kind}:{asm}"
                        F = lambda g, a=(spec, order, drop, kind, asm): prog_predict(*a, g)
                        emit(name, 30 + drop + order + (kind == 'grow'), F)



# ------------------------------------------------------------------ SELCTX (output = OP(selected part, its ctx))
SELCTX_SPECS = [('sepx',), ('sep',), ('bgsep', 'rc'), ('bgsep', 'r'), ('bgsep', 'c'), ('frame',)]


def selctx_pick(spec, sel, rule, g):
    ps = partition(spec, g)
    if not ps or len(ps) < 2: return None
    a = L.select(ps, sel)
    if a is None: return None
    k = next(i for i, p in enumerate(ps) if p is a)
    cm = ctx_map(rule, ps)
    if cm is None or cm[k] is None or cm[k] == k: return None
    return a.g, ps[cm[k]].g, L._ORIG_BG(g)


def try_selctx(task, budget, emit):
    train, test = task['train'], task['test']
    tin = [p['input'] for p in train]
    folds = [len(train) - 1] + ([0] if len(train) >= 3 else [])
    specs = SELCTX_SPECS + L._block_specs(tin + [t['input'] for t in test], limit=3)
    seen = set(); n = 0
    for spec in specs:
        pin = [partition(spec, g) for g in tin]
        if any(not ps or len(ps) < 2 for ps in pin): continue
        pte = [partition(spec, t['input']) for t in test]
        if any(not ps or len(ps) < 2 for ps in pte): continue
        ns = {len(ps) for ps in pin + pte}
        sels = L._selectors(tin, ns.pop() if len(ns) == 1 else 0)
        for sel in sels:
            if budget.left() < 0.3 or n >= 3: return
            tick(L.SEL_BASE + sum(_cells(g) for g in tin) // 2)
            ch = [L.select(ps, sel) for ps in pin]
            if any(c is None or dims(c.g) != dims(p['output']) for c, p in zip(ch, train)): continue
            for rule in [('sel', s2) for s2 in sels if s2 != sel] + REL_RULES:
                picks = [selctx_pick(spec, sel, rule, g) for g in tin]
                if any(x is None for x in picks): continue
                tp = [selctx_pick(spec, sel, rule, t['input']) for t in test]
                if any(x is None for x in tp): continue
                key = (str(picks), str(tp))
                if key in seen: continue
                seen.add(key)
                for aligned, t, rs in OPS:
                    recs = [(a, b, p['output'], sbg) for (a, b, sbg), p in zip(picks, train)]
                    model = table_fit(recs, aligned, t, rs)
                    if model is None: continue
                    if all(a == p['output'] for (a, b, sbg), p in zip(picks, train)): break
                    ok = True
                    for j in folds:
                        m2 = table_fit([r for i, r in enumerate(recs) if i != j], aligned, t, rs)
                        a, b, sbg = picks[j]
                        if m2 is None or table_apply(m2, a, b, sbg, aligned, t, rs) != train[j]['output']:
                            ok = False; break
                    if not ok:
                        DIAG['loo_reject'] += 1; continue
                    h = Hyp(spec, rule, aligned, t, rs)
                    F = lambda g, a=(spec, sel, rule), m=model, h=h: (lambda x: None if x is None else
                                                                       table_apply(m, x[0], x[1], x[2], h.aligned, h.t, h.rs))(selctx_pick(*a, g))
                    name = f"ctx-sel[{spec_name(spec)}]:{sel[0]}-{sel[1]}+{rule_name(rule)}:" + h.name(model).split(':', 3)[-1]
                    if emit(name, 25 + _mode_cost(model) + (2 if t else 0) + rs, F): n += 1
                    break


# ------------------------------------------------------------------ SEARCH
def SEARCH(task):
    L._WORK[0] = 0; del L._CAPS[:]
    budget = L.Budget(TOTAL_BUDGET)
    DIAG.clear()
    found = []; seen = {}
    train, test = task['train'], task['test']

    def emit(name, cost, F):
        try:
            for p in train:
                if F(p['input']) != p['output']: return False
            preds = [F(t['input']) for t in test]
        except _Timeout:
            raise
        except Exception as e:
            if DEBUG: print('  emit error', name, repr(e)[:100])
            return False
        if any(p is None for p in preds): return False
        k = str(preds)
        if k in seen:
            seen[k]['votes'] += 1
            return False
        seen[k] = {'program': name, 'cost': cost, 'preds': preds, 'votes': 1}
        found.append(seen[k])
        if DEBUG: print('  EMIT', name, cost, flush=True)
        return True

    patched = L._install_patch()
    try:
        with L.work_cap(TOTAL_BUDGET + 0.5):
            same = all(dims(p['input']) == dims(p['output']) for p in train)
            if same:
                try_inplace_ctx(task, budget.sub(12.0), emit)
                if not found:
                    try_inplace_lib(task, budget, emit)
            else:
                try_prog(task, budget.sub(3.0), emit)
                try_selctx(task, budget.sub(12.0), emit)
    except _Timeout:
        pass
    finally:
        L._remove_patch(patched)
        L._FORCED[0] = None
        del L._CAPS[:]
    found.sort(key=lambda r: (-r['votes'], r['cost']))
    SEARCH.stats = {'work': round(L._WORK[0] / SEC, 3), 'diag': dict(DIAG)}
    return [{'program': r['program'] + (f" (x{r['votes']})" if r['votes'] > 1 else ''), 'cost': r['cost'], 'preds': r['preds']}
            for r in found[:3]]
