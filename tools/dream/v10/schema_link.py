"""LINK image schema of the v10 description lattice (Fable guidance v10 sections 1-3).

A LINK description says: two participants a and b that share a token (colour, mark, tile content) and are aligned
are joined by painting what lies between them.  The records parsed with schema == "LINK" (connect / join / fill /
bridge / draw / copy / highlight; results/o0/v10_records.json) all fit one parametric generator:

    for every item a (selector) and every axis kind k in axis:
        b = stop(a, k)                      partner | obstacle | endpoint | border
        paint the background between a and b (and a, b themselves if inclusive), every period-th cell,
        in colour_rule(a)                   source (a's colour / a copy of a's tile) | literal c | table T[colour(a)]
    where lines of different kinds cross:   overlap = row_wins | col_wins | mix (constant m)

A node of the lattice is a dict of choices over NODE_DIMS (verb, selector, stop, axis, colour_rule, inclusive,
overlap, period); free fields are fitted from data by family().  Synthetic only: no ARC file is read here.
Pure stdlib, deterministic.
"""
import itertools
import random
import zlib
from collections import Counter

SCHEMA = "LINK"

KDIR = {'h': (0, 1), 'v': (1, 0), 'd1': (1, 1), 'd2': (1, -1)}
AXES = {'rc': ('h', 'v'), 'row': ('h',), 'col': ('v',), 'diag': ('d1', 'd2'), 'all': ('h', 'v', 'd1', 'd2')}
ORDER = {'row_wins': ('h', 'v', 'd1', 'd2'), 'col_wins': ('v', 'h', 'd1', 'd2')}

DIMS = ('selector', 'stop', 'axis', 'colour_rule', 'inclusive', 'overlap', 'period')
IDX = {d: i for i, d in enumerate(DIMS)}
DOMAIN = {
    'selector': ('cell', 'twice', 'edge', 'block', 'tile'),
    'stop': ('partner', 'obstacle', 'endpoint', 'border'),
    'axis': ('rc', 'row', 'col', 'diag', 'all'),
    'colour_rule': ('source', 'literal', 'table'),
    'inclusive': ('strict', 'inclusive'),
    'overlap': ('row_wins', 'col_wins', 'mix'),
    'period': (1, 2),
}
COST = {
    'selector': {'cell': 0.0, 'twice': 1.0, 'edge': 1.0, 'block': 0.5, 'tile': 0.5},
    'stop': {'partner': 0.0, 'obstacle': 0.2, 'endpoint': 0.6, 'border': 0.8},
    'axis': {'rc': 0.0, 'row': 0.3, 'col': 0.3, 'all': 0.5, 'diag': 0.6},
    'colour_rule': {'source': 0.0, 'literal': 0.5, 'table': 1.0},
    'inclusive': {'strict': 0.0, 'inclusive': 0.4},
    'overlap': {'row_wins': 0.0, 'col_wins': 0.1, 'mix': 0.5},
    'period': {1: 0.0, 2: 0.7},
}

# schema -> verb: each verb lifts to LINK and binds a set of values on some dimensions
VERBS = {
    'connect': {'stop': ('partner', 'obstacle'), 'colour_rule': ('source',)},
    'join': {'stop': ('obstacle',), 'colour_rule': ('source', 'table')},
    'fill': {'stop': ('endpoint',), 'colour_rule': ('literal',)},
    'bridge': {'selector': ('block',)},
    'draw': {'stop': ('border',)},
    'copy': {'selector': ('tile',), 'colour_rule': ('source',)},
    'highlight': {'colour_rule': ('literal', 'table'), 'inclusive': ('inclusive',)},
}
NODE_DIMS = ('verb',) + DIMS

MENU = {
    'schema': SCHEMA,
    'roles': {'a': 'item carrying a token (colour / mark / tile content)',
              'b': 'aligned item reached from a by the stop rule'},
    'selector': {  # role -> selector (a and b share the selector)
        'cell': 'any non-background cell (cell of colour c)',
        'twice': 'cell of a colour occurring exactly twice',
        'edge': 'edge marker: non-background cell on the grid border',
        'block': 'object face: same-colour 4-connected block; band = span both faces share',
        'tile': 'marked tile of a separator-line lattice; token = tile content',
    },
    'stop': {  # stop class -> member
        'partner': 'nearest same-token item along the line (other foreground skipped, never painted)',
        'obstacle': 'the next foreground item must be the same-token partner (clear line)',
        'endpoint': 'next consecutive foreground item, any token',
        'border': 'line through a and an aligned same-token item, border to border',
    },
    'params': {
        'axis': {'rc': 'rows and columns', 'row': 'rows', 'col': 'columns', 'diag': 'both diagonals',
                 'all': 'rows, columns, diagonals'},
        'inclusive': {'strict': 'between cells only', 'inclusive': 'also recolour a and b'},
        'overlap': {'row_wins': 'row line colour at crossings', 'col_wins': 'column line colour at crossings',
                    'mix': 'constant colour m at crossings (fitted)'},
        'period': {1: 'solid', 2: 'dotted (odd distances from a)'},
    },
    'colour_rule': {'source': "a's colour (tiles: copy a's content)", 'literal': 'constant c (fitted)',
                    'table': 'map colour(a) -> c (fitted)'},
    'verbs': VERBS,
    'records': ['d2_3e6067c3', 'd2_7b0280bc', 'grp_M034', 'grp_M035', 'grp_M041', 'grp_M127', 'oo_06df4c85',
                'oo_673ef223', 'oo_98c475bf', 'oo_a096bf4d', 'oo_b7f8a4d8', 'oo_bcb3040b', 'oo_cbded52d',
                'oo_e760a62e', 'oo_f35d900a', 'pc_bridge_aligned_pairs'],
    'not_covered': ['shortest-route highlight', 'triangle fill', 'piece chaining (move)', 'MST corridors',
                    'polygon over marker centres', 'parity split along a cable', 'connectivity test -> 1x1',
                    'arm/post through a bracket'],
}

# Nodes pruned by the self-test (test_link.py): their specialisations (config sets contained in theirs) go too.
# Self-test 2026-10-01: 331 nodes, 331 drawn, 331 ok -> nothing pruned.  Stress check (every one of the 1209
# canonical configurations drawn, fitted by the all-free top family): 1200 predict pair 3, 9 ambiguous
# (twice/edge/tile with endpoint or border stops), max fit 0.09 s.
PRUNED = []


# ----------------------------------------------------------------------------------------------- configurations
def _compatible(cfg):
    sel, stop, axis, paint, incl, ov, per = cfg
    if sel in ('block', 'tile') and (axis in ('diag', 'all') or per != 1):
        return False
    if stop == 'border' and per != 1:
        return False
    return True


def _canon(cfg):
    sel, stop, axis, paint, incl, ov, per = cfg
    if axis not in ('rc', 'all'):
        ov = 'row_wins'
    if paint == 'source' and stop != 'endpoint':
        incl = 'strict'
    return (sel, stop, axis, paint, incl, ov, per)


_RAW = [c for c in itertools.product(*(DOMAIN[d] for d in DIMS)) if _compatible(c)]


def _consistent(cfg, node):
    for d, v in node.items():
        if d == 'verb':
            for dd, vals in VERBS[v].items():
                if cfg[IDX[dd]] not in vals:
                    return False
        elif d in IDX:
            if cfg[IDX[d]] != v:
                return False
    return True


_SCACHE = {}


def _S(node):
    """Set of canonical configurations (= generators) a node denotes."""
    k = tuple(sorted((d, str(v)) for d, v in node.items()))
    if k not in _SCACHE:
        _SCACHE[k] = frozenset(_canon(c) for c in _RAW if _consistent(c, node))
    return _SCACHE[k]


def _nstr(node):
    return SCHEMA + '(' + ','.join('%s=%s' % (d, node[d]) for d in NODE_DIMS if d in node) + ')'


_TABLE = None


def _table():
    """All candidate nodes at depth <= 2, grouped by denoted generator set; one representative per group."""
    global _TABLE
    if _TABLE is not None:
        return _TABLE
    singles = [(d, v) for d in NODE_DIMS for v in (sorted(VERBS) if d == 'verb' else DOMAIN[d])]
    cands = [{}] + [{d: v} for d, v in singles]
    for (d1, v1), (d2, v2) in itertools.combinations(singles, 2):
        if d1 != d2:
            cands.append({d1: v1, d2: v2})
    groups = {}
    for n in cands:
        S = _S(n)
        if not S:
            continue
        groups.setdefault(S, []).append(n)
    rep = {}
    for S, ns in groups.items():
        rep[S] = min(ns, key=lambda n: (len(n), int('verb' in n), _nstr(n)))
    _TABLE = rep
    return rep


def key(node):
    """Canonical string: nodes denoting the same generator set get the same key."""
    S = _S(node)
    r = _table().get(S)
    return _nstr(r if r is not None else node)


def nodes():
    rep = _table()
    pruned = [_S(p) for p in PRUNED]
    out = []
    for S, n in rep.items():
        if any(S <= P for P in pruned):
            continue
        out.append(n)
    out.sort(key=lambda n: (len(n), _nstr(n)))
    assert len(out) <= 400, len(out)
    return out


# ----------------------------------------------------------------------------------------------- grid analysis
def _bg(g):
    c = Counter(v for r in g for v in r)
    return 0 if 0 in c else min(c, key=lambda k: (-c[k], k))


_LCACHE = {}


def _lines(R, C, k):
    kk = (R, C, k)
    if kk in _LCACHE:
        return _LCACHE[kk]
    dr, dc = KDIR[k]
    if k == 'h':
        starts = [(r, 0) for r in range(R)]
    elif k == 'v':
        starts = [(0, c) for c in range(C)]
    elif k == 'd1':
        starts = [(0, c) for c in range(C)] + [(r, 0) for r in range(1, R)]
    else:
        starts = [(0, c) for c in range(C)] + [(r, C - 1) for r in range(1, R)]
    lines = []
    for r, c in starts:
        L = []
        while 0 <= r < R and 0 <= c < C:
            L.append((r, c))
            r += dr
            c += dc
        if len(L) >= 2:
            lines.append(L)
    _LCACHE[kk] = lines
    return lines


def _abs_links(R, C, A, items, stop, k):
    """Links on an abstract grid (cells or tiles): (kind, ends_a, ends_b, [(dist, pos)], token)."""
    out = []
    for line in _lines(R, C, k):
        occ = [(i, p) for i, p in enumerate(line) if p in A]
        if len(occ) < 2:
            continue
        if stop in ('obstacle', 'endpoint'):
            for (i, p), (j, q) in zip(occ, occ[1:]):
                if j - i < 2 or p not in items or q not in items:
                    continue
                if stop == 'obstacle' and A[p] != A[q]:
                    continue
                out.append((k, (p,), (q,), [(t - i, line[t]) for t in range(i + 1, j)], A[p]))
        elif stop == 'partner':
            its = [(i, p) for i, p in occ if p in items]
            for x, (i, p) in enumerate(its):
                for j, q in its[x + 1:]:
                    if A[q] == A[p]:
                        btw = [(t - i, line[t]) for t in range(i + 1, j) if line[t] not in A]
                        if btw:
                            out.append((k, (p,), (q,), btw, A[p]))
                        break
        else:  # border
            first = {}
            for i, p in occ:
                if p in items:
                    first.setdefault(A[p], []).append((i, p))
            for tok, lst in first.items():
                if len(lst) >= 2:
                    i0, p0 = lst[0]
                    p1 = lst[1][1]
                    btw = [(t - i0, line[t]) for t in range(len(line)) if line[t] not in A]
                    if btw:
                        out.append((k, (p0,), (p1,), btw, tok))
    return out


def _lattice(g, H, W):
    rowu = {r: g[r][0] for r in range(H) if all(v == g[r][0] for v in g[r])}
    colu = {c: g[0][c] for c in range(W) if all(g[r][c] == g[0][c] for r in range(H))}
    best = None
    for sep in sorted(set(rowu.values()) | set(colu.values())):
        rs = {r for r, v in rowu.items() if v == sep}
        cs = {c for c, v in colu.items() if v == sep}
        rr, cr = _runs([r for r in range(H) if r not in rs]), _runs([c for c in range(W) if c not in cs])
        if len(rr) * len(cr) < 2:
            continue
        cnt = Counter(g[r][c] for run in rr for r in run for run2 in cr for c in run2)
        bg = 0 if 0 in cnt else min(cnt, key=lambda k: (-cnt[k], k))
        if bg == sep:
            continue
        score = len(rs) + len(cs)
        if best is None or score > best[0]:
            best = (score, sep, rr, cr, bg)
    if best is None:
        return None
    _, sep, rr, cr, bg = best
    A = {}
    for i, rows in enumerate(rr):
        for j, cols in enumerate(cr):
            content = tuple(tuple(g[r][c] for c in cols) for r in rows)
            if any(v != bg for row in content for v in row):
                A[(i, j)] = content
    return {'sep': sep, 'rr': rr, 'cr': cr, 'bg': bg, 'A': A}


def _runs(xs):
    out, cur = [], []
    for x in xs:
        if cur and x != cur[-1] + 1:
            out.append(cur)
            cur = []
        cur.append(x)
    if cur:
        out.append(cur)
    return out


def _components(g, H, W, bg):
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            col = g[r][c]
            st = [(r, c)]
            seen.add((r, c))
            cells = []
            while st:
                y, x = st.pop()
                cells.append((y, x))
                for dy, dx in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and (yy, xx) not in seen and g[yy][xx] == col:
                        seen.add((yy, xx))
                        st.append((yy, xx))
            cells.sort()
            ys = [p[0] for p in cells]
            xs = [p[1] for p in cells]
            comps.append({'col': col, 'cells': cells, 'r0': min(ys), 'r1': max(ys), 'c0': min(xs), 'c1': max(xs)})
    return comps


class _A:
    """Per-grid analysis with caches (structures per selector, links per (selector, stop, kind))."""

    def __init__(s, g):
        s.g = g
        s.H, s.W = len(g), len(g[0])
        s.bg = _bg(g)
        s._st = {}
        s._lk = {}

    def struct(s, sel):
        if sel in s._st:
            return s._st[sel]
        g, H, W, bg = s.g, s.H, s.W, s.bg
        st = None
        if sel in ('cell', 'twice', 'edge'):
            A = {(r, c): g[r][c] for r in range(H) for c in range(W) if g[r][c] != bg}
            if sel == 'cell':
                items = set(A)
            elif sel == 'twice':
                cnt = Counter(A.values())
                items = {p for p, v in A.items() if cnt[v] == 2}
            else:
                items = {p for p in A if p[0] in (0, H - 1) or p[1] in (0, W - 1)}
            st = {'kind': 'abs', 'R': H, 'C': W, 'A': A, 'items': items, 'bg': bg}
        elif sel == 'tile':
            lat = _lattice(g, H, W)
            if lat is not None:
                st = {'kind': 'tile', 'R': len(lat['rr']), 'C': len(lat['cr']), 'A': lat['A'],
                      'items': set(lat['A']), 'bg': lat['bg'], 'rr': lat['rr'], 'cr': lat['cr']}
        else:
            st = {'kind': 'blk', 'comps': _components(g, H, W, bg), 'bg': bg}
        s._st[sel] = st
        return st

    def links(s, sel, stop, k):
        kk = (sel, stop, k)
        if kk in s._lk:
            return s._lk[kk]
        st = s.struct(sel)
        if st['kind'] in ('abs', 'tile'):
            out = _abs_links(st['R'], st['C'], st['A'], st['items'], stop, k)
        else:
            out = s._blk_links(st, stop, k)
        s._lk[kk] = out
        return out

    def _blk_links(s, st, stop, k):
        if k not in ('h', 'v'):
            return []
        g, bg, H, W = s.g, st['bg'], s.H, s.W
        comps = st['comps']
        if k == 'h':
            lo, hi, a0, a1, N = 'r0', 'r1', 'c0', 'c1', W
        else:
            lo, hi, a0, a1, N = 'c0', 'c1', 'r0', 'r1', H
        out = []
        for a in comps:
            cand = [b for b in comps if b is not a and b[a0] > a[a1] and b[lo] <= a[hi] and a[lo] <= b[hi]]
            if not cand:
                continue
            cand.sort(key=lambda b: (b[a0], b[lo]))
            q = None
            if stop in ('obstacle', 'endpoint'):
                q = cand[0]
                if stop == 'obstacle' and q['col'] != a['col']:
                    q = None
            else:
                for b in cand:
                    if b['col'] == a['col']:
                        q = b
                        break
            if q is None:
                continue
            u0, u1 = max(a[lo], q[lo]), min(a[hi], q[hi])
            vs = range(N) if stop == 'border' else range(a[a1] + 1, q[a0])
            band = [((u, v) if k == 'h' else (v, u)) for u in range(u0, u1 + 1) for v in vs]
            if stop in ('obstacle', 'endpoint') and any(g[r][c] != bg for r, c in band):
                continue
            btw = [((c if k == 'h' else r) - a[a1], (r, c)) for r, c in band if g[r][c] == bg]
            if btw:
                out.append((k, tuple(a['cells']), tuple(q['cells']), btw, a['col']))
        return out

    def plan(s, geom):
        sel, stop, axis, incl, per = geom
        if s.struct(sel) is None:
            return None
        P = {}
        for k in AXES[axis]:
            for kk, ea, eb, btw, tok in s.links(sel, stop, k):
                for d, pos in btw:
                    if per == 2 and d % 2 == 0:
                        continue
                    P.setdefault(pos, []).append((kk, tok))
                if incl == 'inclusive':
                    for pos in ea + eb:
                        P.setdefault(pos, []).append((kk, tok))
        return P

    def covered(s, sel, P):
        st = s.struct(sel)
        if st['kind'] != 'tile':
            return set(P)
        out = set()
        for i, j in P:
            for r in st['rr'][i]:
                for c in st['cr'][j]:
                    out.add((r, c))
        return out

    def rep(s, sel, pos):
        st = s.struct(sel)
        if st['kind'] != 'tile':
            return pos
        return st['rr'][pos[0]][0], st['cr'][pos[1]][0]

    def tokcol(s, sel, tok):
        st = s.struct(sel)
        if st['kind'] != 'tile':
            return tok
        cs = {v for row in tok for v in row if v != st['bg']}
        return cs.pop() if len(cs) == 1 else None


def _resolve(ents, ov):
    kinds = {k for k, _ in ents}
    if len(kinds) == 1:
        return ents[0][1], False
    if ov == 'mix':
        return None, True
    order = ORDER[ov]
    return min(ents, key=lambda e: order.index(e[0]))[1], False


def _render(A, sel, P, paint, ov, prm):
    c, T, m = prm
    st = A.struct(sel)
    tile = st['kind'] == 'tile'
    g = [row[:] for row in A.g]
    for pos, ents in P.items():
        tok, mixed = _resolve(ents, ov)
        if mixed:
            val, cp = m, False
        elif paint == 'source':
            val, cp = tok, tile
        elif paint == 'literal':
            val, cp = c, False
        else:
            val, cp = T.get(A.tokcol(sel, tok)), False
        if val is None:
            return None
        if not tile:
            g[pos[0]][pos[1]] = val
            continue
        rows, cols = st['rr'][pos[0]], st['cr'][pos[1]]
        if cp:
            if len(val) != len(rows) or len(val[0]) != len(cols):
                return None
            for a, r in enumerate(rows):
                for b, cc in enumerate(cols):
                    g[r][cc] = val[a][b]
        else:
            for r in rows:
                for cc in cols:
                    g[r][cc] = val
    return g


def _fit(paint, ov, sel, As, plans, outs):
    c, T, m = None, {}, None
    for A, P, o in zip(As, plans, outs):
        bg = A.struct(sel)['bg']
        for pos, ents in P.items():
            r, cc = A.rep(sel, pos)
            oc = o[r][cc]
            if oc == bg and paint != 'source':
                return None
            tok, mixed = _resolve(ents, ov)
            if mixed:
                if m is None:
                    m = oc
                elif m != oc:
                    return None
                continue
            if paint == 'literal':
                if c is None:
                    c = oc
                elif c != oc:
                    return None
            elif paint == 'table':
                tc = A.tokcol(sel, tok)
                if tc is None:
                    return None
                if T.setdefault(tc, oc) != oc:
                    return None
    if paint == 'literal' and c is None:
        return None
    if ov == 'mix' and m is None:
        return None
    return c, T, m


def _cfg_cost(cfg):
    return round(sum(COST[d][v] for d, v in zip(DIMS, cfg)), 3)


def _cfg_name(cfg, prm):
    sel, stop, axis, paint, incl, ov, per = cfg
    c, T, m = prm
    p = paint
    if paint == 'literal':
        p += '(%d)' % c
    elif paint == 'table':
        p += '(%s)' % ','.join('%s>%s' % kv for kv in sorted(T.items()))
    o = ov + ('(%d)' % m if ov == 'mix' else '')
    return 'link[%s,%s,%s,%s,%s,%s,p%d]' % (sel, stop, axis, p, incl, o, per)


def _apply(cfg, prm, grid):
    sel, stop, axis, paint, incl, ov, per = cfg
    A = _A(grid)
    P = A.plan((sel, stop, axis, incl, per))
    if P is None:
        return None
    return _render(A, sel, P, paint, ov, prm)


def _make_fn(cfg, prm):
    def fn(grid):
        try:
            return _apply(cfg, prm, grid)
        except Exception:
            return None
    return fn


def family(node):
    """fam(train) yields (name, cost, fn) for every configuration of the node that reproduces all training pairs,
    cheapest first.  fn(grid) -> grid, or None when the program does not apply."""
    groups = {}
    for cfg in sorted(_S(node), key=str):
        sel, stop, axis, paint, incl, ov, per = cfg
        groups.setdefault((sel, stop, axis, incl, per), []).append((paint, ov))
    def full(gm, po):
        return (gm[0], gm[1], gm[2], po[0], gm[3], po[1], gm[4])
    geoms = sorted(groups, key=lambda gm: (min(_cfg_cost(full(gm, po)) for po in groups[gm]), str(gm)))

    def fam(train):
        pairs = [(i, o) for i, o in train]
        if not pairs:
            return
        for i, o in pairs:
            if not i or not o or len(i) != len(o) or len(i[0]) != len(o[0]) or len(i) > 30 or len(i[0]) > 30:
                return
        if all(i == o for i, o in pairs):
            return
        As = [_A(i) for i, _ in pairs]
        outs = [o for _, o in pairs]
        changed = [{(r, c) for r in range(len(i)) for c in range(len(i[0])) if i[r][c] != o[r][c]} for i, o in pairs]
        res = []
        for gm in geoms:
            sel = gm[0]
            plans = []
            for A, ch in zip(As, changed):
                P = A.plan(gm)
                if P is None or not ch <= A.covered(sel, P):
                    plans = None
                    break
                plans.append(P)
            if plans is None:
                continue
            for paint, ov in groups[gm]:
                prm = _fit(paint, ov, sel, As, plans, outs)
                if prm is None:
                    continue
                if all(_render(A, sel, P, paint, ov, prm) == o for A, P, o in zip(As, plans, outs)):
                    cfg = (sel, gm[1], gm[2], paint, gm[3], ov, gm[4])
                    res.append((_cfg_cost(cfg), _cfg_name(cfg, prm), cfg, prm))
        res.sort(key=lambda t: (t[0], t[1]))
        for cost, name, cfg, prm in res:
            yield name, cost, _make_fn(cfg, prm)
    return fam


# ----------------------------------------------------------------------------------------------- synthetic drawer
ALLK = ('h', 'v', 'd1', 'd2')


def _aligned(p, q, kinds):
    for k in kinds:
        if k == 'h' and p[0] == q[0]:
            return True
        if k == 'v' and p[1] == q[1]:
            return True
        if k == 'd1' and p[0] - p[1] == q[0] - q[1]:
            return True
        if k == 'd2' and p[0] + p[1] == q[0] + q[1]:
            return True
    return False


def _task(node):
    """Task-level choices (constant over the pairs of one synthetic task): a full configuration and colours."""
    k = key(node)
    rng = random.Random(zlib.crc32(k.encode()))
    S = sorted(_S(node), key=str)
    act = [c for c in S if _consistent(c, node)]
    cfg = rng.choice(act or S)
    sel, stop, axis, paint, incl, ov, per = cfg
    cols = list(range(1, 10))
    c = rng.choice(cols)
    m = rng.choice([x for x in cols if x != c])
    tp = {'cfg': cfg, 'c': c if paint == 'literal' else None, 'm': m if (ov == 'mix' and axis in ('rc', 'all')) else None}
    tp['sep'] = rng.choice([x for x in cols if x not in (tp['c'], tp['m'])]) if sel == 'tile' else None
    pal = [x for x in cols if x not in (tp['c'], tp['m'], tp['sep'])]
    rng.shuffle(pal)
    tp['pal'] = pal
    if paint == 'table':
        nd = 4
        D = pal[:nd]
        T = {}
        usedv = set()
        for x in D:
            opts = [v for v in cols if v != x and v not in usedv and v not in (tp['m'], tp['sep'])]
            v = rng.choice(opts)
            T[x] = v
            usedv.add(v)
        tp['D'], tp['T'], tp['rest'] = D, T, pal[nd:]
    tp['s'] = rng.choice([2, 3])
    tp['pat'] = rng.choice(['full', 'dot', 'mask'])
    return tp


class _Colours:
    def __init__(s, tp, rng, unique):
        cfg = tp['cfg']
        s.unique = unique
        s.used = Counter()
        if cfg[3] == 'table':
            s.link = list(tp['D'])
            rest = list(tp['rest'])
            rng.shuffle(rest)
            if cfg[0] == 'edge' and cfg[1] == 'endpoint':
                rest = []  # every border item may be linked: all colours need table entries
            s.free = rest if rest else list(tp['D'])
        else:
            p = list(tp['pal'])
            rng.shuffle(p)
            s.link = s.free = p

    def get(s, kind):
        pool = s.link if kind == 'link' else s.free
        for x in pool:
            if s.used[x] == 0:
                s.used[x] += 1
                return x
        if s.unique:
            return None
        x = min(pool, key=lambda y: (s.used[y], pool.index(y)))
        s.used[x] += 1
        return x

    def release(s, *xs):
        for x in xs:
            if x is not None and s.used[x] > 0:
                s.used[x] -= 1


class _Canvas:
    """Abstract canvas (grid cells or lattice tiles) holding tokens; reserved cells must stay empty."""

    def __init__(s, R, C, rng, kinds, strict):
        s.R, s.C, s.rng, s.kinds, s.strict = R, C, rng, kinds, strict
        s.occ = {}
        s.res = set()

    def inb(s, p):
        return 0 <= p[0] < s.R and 0 <= p[1] < s.C

    def border(s, p):
        return p[0] in (0, s.R - 1) or p[1] in (0, s.C - 1)

    def free(s, p):
        return s.inb(p) and p not in s.occ and p not in s.res

    def ok(s, p, col):
        if not s.free(p):
            return False
        for q, qc in s.occ.items():
            if qc == col and _aligned(p, q, ALLK):
                return False
            if s.strict and _aligned(p, q, s.kinds) and s._clear(p, q):
                return False
        return True

    def _clear(s, p, q):
        dr = (q[0] > p[0]) - (q[0] < p[0])
        dc = (q[1] > p[1]) - (q[1] < p[1])
        r, c = p[0] + dr, p[1] + dc
        while (r, c) != q:
            if (r, c) in s.occ:
                return False
            r, c = r + dr, c + dc
        return True

    def single(s, col, mode='any', tries=60):
        for _ in range(tries):
            p = (s.rng.randrange(s.R), s.rng.randrange(s.C))
            if mode == 'interior' and s.border(p):
                continue
            if mode == 'edge' and not s.border(p):
                continue
            if s.ok(p, col):
                s.occ[p] = col
                return p
        return None

    def _line_full(s, a, k):
        dr, dc = KDIR[k]
        out = []
        r, c = a
        while s.inb((r - dr, c - dc)):
            r, c = r - dr, c - dc
        while s.inb((r, c)):
            out.append((r, c))
            r, c = r + dr, c + dc
        return out

    def _ends(s, k, gmin, gmax, mode):
        dr, dc = KDIR[k]
        R, C, rng = s.R, s.C, s.rng
        if mode == 'edge':
            bcells = [(r, c) for r in range(R) for c in range(C) if s.border((r, c))]
            a = rng.choice(bcells)
            walk = []
            r, c = a
            while True:
                r, c = r + dr, c + dc
                if not s.inb((r, c)):
                    break
                walk.append((r, c))
            opts = [i for i, p in enumerate(walk) if s.border(p) and gmin <= i <= gmax]
            if not opts:
                return None
            g = rng.choice(opts)
            return a, walk[g], g
        g = rng.randint(gmin, gmax)
        a = (rng.randrange(R), rng.randrange(C))
        b = (a[0] + (g + 1) * dr, a[1] + (g + 1) * dc)
        if not s.inb(b):
            return None
        if mode == 'interior' and (s.border(a) or s.border(b)):
            return None
        return a, b, g

    def pair(s, k, ca, cb, gmin, gmax, mode='any', blocker=None, full=False, per=1, tries=120):
        dr, dc = KDIR[k]
        for _ in range(tries):
            e = s._ends(k, gmin, gmax, mode)
            if e is None:
                continue
            a, b, g = e
            btw = [(a[0] + i * dr, a[1] + i * dc) for i in range(1, g + 1)]
            if not all(s.free(p) for p in btw):
                continue
            if not s.ok(a, ca) or not s.ok(b, cb):
                continue
            if s.strict and ca != cb and False:
                continue
            bp = None
            if blocker is not None:
                if g < 2:
                    continue
                opts = list(range(g))
                if per == 2:
                    opts = [i for i in opts if (i + 1) % 2 == 0] or opts
                bi = s.rng.choice(opts)
                bp = btw[bi]
                if blocker == ca or not s.ok(bp, blocker):
                    continue
            if full and mode != 'edge':
                if not (s.inb((a[0] - dr, a[1] - dc)) or s.inb((b[0] + dr, b[1] + dc))):
                    continue
                line = s._line_full(a, k)
                if not all(p in (a, b) or s.free(p) or (p in s.res and p not in s.occ) for p in line):
                    continue
            s.occ[a] = ca
            s.occ[b] = cb
            if bp is not None:
                s.occ[bp] = blocker
            for p in btw:
                if p != bp:
                    s.res.add(p)
            if full:
                for p in s._line_full(a, k):
                    if p not in s.occ:
                        s.res.add(p)
            return a, b
        return None

    def cross(s, ch, cv, gmin, mode, per, full, tries=150):
        R, C, rng = s.R, s.C, s.rng
        lo = max(gmin, 1)
        for _ in range(tries):
            if mode == 'edge':
                r, c = rng.randrange(1, R - 1), rng.randrange(1, C - 1)
                c1, c2, r1, r2 = 0, C - 1, 0, R - 1
            else:
                r, c = rng.randrange(R), rng.randrange(C)
                c1 = c - rng.randint(1, max(1, (lo + 1) // 2 + 2))
                c2 = c1 + lo + 1 + rng.randint(0, 3)
                r1 = r - rng.randint(1, max(1, (lo + 1) // 2 + 2))
                r2 = r1 + lo + 1 + rng.randint(0, 3)
            if not (c1 < c < c2 and r1 < r < r2):
                continue
            if full and mode != 'edge' and not ((c1 > 0 or c2 < C - 1) and (r1 > 0 or r2 < R - 1)):
                continue
            if per == 2 and ((c - c1) % 2 == 0 or (r - r1) % 2 == 0):
                continue
            a1, b1, a2, b2 = (r, c1), (r, c2), (r1, c), (r2, c)
            if not all(s.inb(p) for p in (a1, b1, a2, b2)):
                continue
            if mode == 'interior' and any(s.border(p) for p in (a1, b1, a2, b2)):
                continue
            hb = [(r, x) for x in range(c1 + 1, c2)]
            vb = [(y, c) for y in range(r1 + 1, r2)]
            if not all(s.free(p) for p in hb + vb):
                continue
            if not (s.ok(a1, ch) and s.ok(b1, ch)):
                continue
            s.occ[a1] = ch
            s.occ[b1] = ch
            if not (s.ok(a2, cv) and s.ok(b2, cv)):
                del s.occ[a1], s.occ[b1]
                continue
            s.occ[a2] = cv
            s.occ[b2] = cv
            s.res.update(hb + vb)
            if full:
                for p in s._line_full(a1, 'h') + s._line_full(a2, 'v'):
                    if p not in s.occ:
                        s.res.add(p)
            return True
        return False


def _recipe(cfg, rng):
    sel, stop, axis, paint, incl, ov, per = cfg
    kinds = AXES[axis]
    S = []
    if axis in ('rc', 'all'):
        S.append(('cross',))
        if axis == 'all':
            S.append(('pos', rng.choice(('d1', 'd2'))))
    elif axis == 'diag':
        S += [('pos', 'd1'), ('pos', 'd2')]
    else:
        S.append(('pos', kinds[0]))
    S.append(('blocked', rng.choice(kinds)))
    if stop == 'endpoint':
        S.append(('diff', rng.choice(kinds)))
    covered = set(kinds)
    for k in (('h', 'v') if sel in ('block', 'tile') else ('h', 'v', 'D')):
        if k == 'D':
            if not (covered & {'d1', 'd2'}):
                S.append(('distract', rng.choice(('d1', 'd2'))))
        elif k not in covered:
            S.append(('distract', k))
    if sel == 'cell':
        S.append(('third',))
    elif sel == 'twice':
        S.append(('triple', rng.choice(kinds)))
    elif sel == 'edge':
        S.append(('interior', rng.choice(kinds)))
    if stop != 'endpoint' and sel in ('cell', 'twice', 'edge'):
        S.append(('noise',))
    return S


def _draw_abstract(tp, rng, tiles, req):
    cfg = tp['cfg']
    sel, stop, axis, paint, incl, ov, per = cfg
    if tiles:
        s = tp['s']
        hi = 6 if s == 2 else 5
        R, C = rng.randint(4, hi), rng.randint(4, hi)
        gmin, gmax = 1, 3
    else:
        R, C = rng.randint(10, 18), rng.randint(10, 18)
        gmin = 3 if per == 2 else 2
        gmax = min(R, C) - 3
    kinds = AXES[axis]
    cv = _Canvas(R, C, rng, kinds, stop == 'endpoint' and sel != 'edge')
    twice = sel == 'twice'
    col = _Colours(tp, rng, unique=twice)
    mode = {'edge': 'edge', 'cell': 'interior'}.get(sel, 'any')
    full = stop == 'border'
    linked = []
    bmin = 2 if tiles else max(gmin, 3)
    for st in _recipe(cfg, rng):
        t = st[0]
        if t == 'cross':
            ch, cvv = col.get('link'), col.get('link')
            if ch is None or cvv is None or not cv.cross(ch, cvv, gmin, mode, per, full):
                return None
            linked += [ch, cvv]
        elif t == 'pos':
            ca = col.get('link')
            if ca is None or cv.pair(st[1], ca, ca, gmin, gmax, mode, full=full, per=per) is None:
                if axis == 'diag' and st[1] == 'd2' and linked and not req:
                    col.release(ca)
                    continue
                return None
            linked.append(ca)
        elif t == 'blocked':
            ca = col.get('link')
            cb = col.get('free' if sel in ('twice', 'edge') else 'link')
            if ca is None or cb is None or ca == cb or cv.pair(st[1], ca, ca, bmin, max(gmax, bmin), mode,
                                                                blocker=cb, full=full, per=per) is None:
                if req:
                    return None
                col.release(ca, cb)
            else:
                linked.append(ca)
        elif t == 'diff':
            ca = col.get('link')
            cb = col.get('free' if sel in ('twice', 'edge') else 'link')
            if ca is None or cb is None or ca == cb or cv.pair(st[1], ca, cb, gmin, gmax, mode, per=per) is None:
                if req:
                    return None
                col.release(ca, cb)
                continue
            if twice:
                if cv.single(ca) is None or cv.single(cb) is None:
                    return None
        elif t == 'distract':
            ca = col.get('free')
            if ca is None or cv.pair(st[1], ca, ca, gmin, gmax, 'edge' if sel == 'edge' else 'any') is None:
                if req:
                    return None
                col.release(ca)
        elif t == 'third':
            if linked and cv.single(linked[0]) is None and req:
                return None
        elif t == 'triple':
            ca = col.get('free')
            if ca is None or cv.pair(st[1], ca, ca, gmin, gmax, 'any') is None:
                if req:
                    return None
                col.release(ca)
            elif cv.single(ca) is None:
                return None
        elif t == 'interior':
            ca = col.get('free')
            if ca is None or cv.pair(st[1], ca, ca, gmin, gmax, 'interior') is None:
                if req:
                    return None
                col.release(ca)
        elif t == 'noise':
            for _ in range(rng.randint(1, 2)):
                ca = col.get('free')
                if ca is None:
                    break
                if cv.single(ca, 'interior' if sel == 'edge' else 'any') is None:
                    col.release(ca)
    if not tiles:
        g = [[0] * C for _ in range(R)]
        for (r, c), v in cv.occ.items():
            g[r][c] = v
        return g
    s = tp['s']
    sep = tp['sep']
    H, W = R * (s + 1) - 1, C * (s + 1) - 1
    g = [[0] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if r % (s + 1) == s or c % (s + 1) == s:
                g[r][c] = sep
    pat = tp['pat']
    dot = (rng.randrange(s), rng.randrange(s))
    masks = {}
    for (i, j), v in sorted(cv.occ.items()):
        if pat == 'full':
            mk = {(a, b) for a in range(s) for b in range(s)}
        elif pat == 'dot':
            mk = {dot}
        else:
            if v not in masks:
                cells = [(a, b) for a in range(s) for b in range(s)]
                n = rng.randint(1, len(cells) - 1)
                masks[v] = set(rng.sample(cells, n))
            mk = masks[v]
        for a, b in mk:
            g[i * (s + 1) + a][j * (s + 1) + b] = v
    return g


class _BCanvas:
    def __init__(s, H, W, rng, kinds, strict):
        s.H, s.W, s.rng, s.kinds, s.strict = H, W, rng, kinds, strict
        s.occ = {}
        s.res = set()
        s.blocks = []

    def rect_ok(s, r0, r1, c0, c1, col, exempt=()):
        if r0 < 0 or c0 < 0 or r1 >= s.H or c1 >= s.W:
            return False
        for r in range(r0 - 1, r1 + 2):
            for c in range(c0 - 1, c1 + 2):
                if (r, c) in s.occ:
                    return False
                if r0 <= r <= r1 and c0 <= c <= c1 and (r, c) in s.res:
                    return False
        for b in s.blocks:
            if b in exempt:
                continue
            ro = b[0] <= r1 and r0 <= b[1]
            co = b[2] <= c1 and c0 <= b[3]
            if b[4] == col and (ro or co):
                return False
            if s.strict and (('h' in s.kinds and ro) or ('v' in s.kinds and co)):
                return False
        return True

    def put(s, r0, r1, c0, c1, col):
        b = (r0, r1, c0, c1, col)
        s.blocks.append(b)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                s.occ[(r, c)] = col
        return b

    def pair(s, k, ca, cb, gmin, gmax, blocker=None, full=False, tries=150):
        rng = s.rng
        U, V = (s.H, s.W) if k == 'h' else (s.W, s.H)

        def rc(u0, u1, v0, v1):
            return (u0, u1, v0, v1) if k == 'h' else (v0, v1, u0, u1)

        for _ in range(tries):
            ha, wa, hb, wb = (rng.randint(1, 3) for _ in range(4))
            if blocker is not None:
                ha, hb = max(ha, 2), max(hb, 2)
            u0a = rng.randrange(0, U - ha + 1)
            v0a = rng.randrange(0, V - wa + 1)
            need = 2 if blocker is not None else 1
            lo, hi = u0a - hb + need, u0a + ha - need
            if lo > hi:
                continue
            u0b = rng.randint(lo, hi)
            if u0b < 0 or u0b + hb > U:
                continue
            g = rng.randint(gmin, gmax)
            v0b = v0a + wa + g
            if v0b + wb > V:
                continue
            A = rc(u0a, u0a + ha - 1, v0a, v0a + wa - 1)
            B = rc(u0b, u0b + hb - 1, v0b, v0b + wb - 1)
            bu0, bu1 = max(u0a, u0b), min(u0a + ha, u0b + hb) - 1
            band = [((u, v) if k == 'h' else (v, u)) for u in range(bu0, bu1 + 1) for v in range(v0a + wa, v0b)]
            if not all(p not in s.occ and p not in s.res for p in band):
                continue
            if not s.rect_ok(*A, ca):
                continue
            bA = s.put(*A, ca)
            if not s.rect_ok(*B, cb, exempt=(bA,)):
                s._undo(bA)
                continue
            bB = s.put(*B, cb)
            bp = None
            if blocker is not None:
                if g < 3:
                    s._undo(bB)
                    s._undo(bA)
                    continue
                u = rng.randint(bu0, bu1)
                v = rng.randint(v0a + wa + 1, v0b - 2)
                bp = (u, v) if k == 'h' else (v, u)
                if not s.rect_ok(bp[0], bp[0], bp[1], bp[1], blocker, exempt=(bA, bB)):
                    s._undo(bB)
                    s._undo(bA)
                    continue
                s.put(bp[0], bp[0], bp[1], bp[1], blocker)
            for p in band:
                if p != bp:
                    s.res.add(p)
            if full:
                for u in range(bu0, bu1 + 1):
                    for v in range(V):
                        p = (u, v) if k == 'h' else (v, u)
                        if p not in s.occ:
                            s.res.add(p)
            return bA, bB, (bu0, bu1, v0a + wa, v0b - 1)
        return None

    def _undo(s, b):
        s.blocks.remove(b)
        for r in range(b[0], b[1] + 1):
            for c in range(b[2], b[3] + 1):
                s.occ.pop((r, c), None)

    def cross(s, ch, cv, full, tries=60):
        rng = s.rng
        for _ in range(tries):
            hp = s.pair('h', ch, ch, 5, 9, full=full, tries=30)
            if hp is None:
                continue
            bA, bB, (br0, br1, bc0, bc1) = hp
            for _ in range(40):
                w = rng.randint(1, 2)
                if bc1 - 1 - w + 1 < bc0 + 1:
                    break
                vc = rng.randint(bc0 + 1, bc1 - w)
                ht, hb = rng.randint(1, 2), rng.randint(1, 2)
                if br0 - 2 < ht - 1 or br1 + 2 > s.H - hb:
                    break
                r1t = rng.randint(ht - 1, br0 - 2)
                r0b = rng.randint(br1 + 2, s.H - hb)
                TOP = (r1t - ht + 1, r1t, vc, vc + w - 1)
                BOT = (r0b, r0b + hb - 1, vc, vc + w - 1)
                vband = [(r, c) for r in range(r1t + 1, r0b) for c in range(vc, vc + w)]
                hband = set((r, c) for r in range(br0, br1 + 1) for c in range(bc0, bc1 + 1))
                if any(p in s.occ or (p in s.res and p not in hband) for p in vband):
                    continue
                if not s.rect_ok(*TOP, cv, exempt=(bA, bB)):
                    continue
                bt = s.put(*TOP, cv)
                if not s.rect_ok(*BOT, cv, exempt=(bA, bB, bt)):
                    s._undo(bt)
                    continue
                s.put(*BOT, cv)
                s.res.update(vband)
                if full:
                    for r in range(s.H):
                        for c in range(vc, vc + w):
                            if (r, c) not in s.occ:
                                s.res.add((r, c))
                return True
            # give up on this h pair
            s._undo(bB)
            s._undo(bA)
            s.res -= {(r, c) for r in range(br0, br1 + 1) for c in range(s.W)} if full else \
                {(r, c) for r in range(br0, br1 + 1) for c in range(bc0, bc1 + 1)}
        return False


def _draw_blocks(tp, rng, req):
    cfg = tp['cfg']
    sel, stop, axis, paint, incl, ov, per = cfg
    H, W = rng.randint(13, 20), rng.randint(13, 20)
    kinds = AXES[axis]
    bc = _BCanvas(H, W, rng, kinds, stop == 'endpoint')
    col = _Colours(tp, rng, unique=False)
    full = stop == 'border'
    for st in _recipe(cfg, rng):
        t = st[0]
        if t == 'cross':
            ch, cvv = col.get('link'), col.get('link')
            if not bc.cross(ch, cvv, full):
                return None
        elif t == 'pos':
            ca = col.get('link')
            if bc.pair(st[1], ca, ca, 2, 7, full=full) is None:
                return None
        elif t == 'blocked':
            ca, cb = col.get('link'), col.get('link')
            if ca == cb or bc.pair(st[1], ca, ca, 3, 7, blocker=cb, full=full) is None:
                if req:
                    return None
                col.release(ca, cb)
        elif t == 'diff':
            ca, cb = col.get('link'), col.get('link')
            if ca == cb or bc.pair(st[1], ca, cb, 2, 7) is None:
                if req:
                    return None
                col.release(ca, cb)
        elif t == 'distract':
            ca = col.get('free')
            if bc.pair(st[1], ca, ca, 2, 7) is None:
                if req:
                    return None
                col.release(ca)
    g = [[0] * W for _ in range(H)]
    for (r, c), v in bc.occ.items():
        g[r][c] = v
    return g


def _check(cfg, prm, inp):
    """Drawn input must change and show a painted link along every kind the axis needs."""
    sel, stop, axis, paint, incl, ov, per = cfg
    A = _A(inp)
    P = A.plan((sel, stop, axis, incl, per))
    if not P:
        return None
    out = _render(A, sel, P, paint, ov, prm)
    if out is None or out == inp:
        return None
    ks = {k for ents in P.values() for k, _ in ents}
    need = {'rc': [{'h'}, {'v'}], 'row': [{'h'}], 'col': [{'v'}], 'diag': [{'d1', 'd2'}],
            'all': [{'h'}, {'v'}, {'d1', 'd2'}]}[axis]
    if any(not (ks & n) for n in need):
        return None
    if axis in ('rc', 'all') and not any(len({k for k, _ in e}) > 1 for e in P.values()):
        return None
    return out


def draw(node, seed):
    """Deterministic synthetic pair (inp, out) for the node, or None.  Free fields of the node are fixed per task
    (from the node key); sizes, positions and (unless fitted) colours vary with the seed."""
    if not _S(node):
        return None
    tp = _task(node)
    cfg = tp['cfg']
    prm = (tp['c'], tp.get('T', {}), tp['m'])
    rng = random.Random(zlib.crc32(('%s#%d' % (key(node), seed)).encode()))
    for att in range(60):
        req = att < 40
        if cfg[0] == 'block':
            inp = _draw_blocks(tp, rng, req)
        else:
            inp = _draw_abstract(tp, rng, cfg[0] == 'tile', req)
        if inp is None or len(inp) > 20 or len(inp[0]) > 20:
            continue
        out = _check(cfg, prm, inp)
        if out is not None:
            return inp, out
    return None


# Interface adapter (supervisor, Oct 1): the solver and the pile harness pass training pairs as
# {"input": grid, "output": grid} dicts (D2 family convention); this module was written with (input, output) tuples.
_family_tuples = family


def family(node):
    f = _family_tuples(node)

    def fam(train):
        tr = [(p['input'], p['output']) if isinstance(p, dict) else p for p in train]
        yield from f(tr)
    return fam
