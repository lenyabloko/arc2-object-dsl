"""crop.fit_by_anchor: pieces carrying anchor cells are translated so that their anchors land on matching
anchor cells of a target (canvas / assembly); the result is drawn on the chosen output canvas.

One parametrised primitive  fit(target, match, out):
  target : rect    - a single-colour region whose bbox holds only tiny (<=2-cell) marker blobs; its markers
                     are the free anchors; pieces are the 8-connected multicolour components outside that bbox
                     (on the most common colour outside it); anchor colours = the marker colours
           | root  - an assembly started from the piece that contains a root colour (induced: the colour whose
                     piece never moves in training); anchors = the connector colour (least frequent colour
                     shared by every piece)
           | largest - as root, but the assembly starts from the largest piece
  match  : all     - every anchor of the piece lands on a free anchor of the same colour
           | two   - at least two anchors of the piece coincide with free anchors (connectors), the rest become
                     new free anchors; bodies may not overlap
           | comp  - complementary glue: the piece's anchors land on assembly body cells, and its body covers
                     assembly anchors (which take the covering colour); bodies may not overlap
  out    : target (target bbox) | full (input-size canvas on bg) | union (bbox of the assembly)
Pieces are placed greedily (unique best translation first) until none fits.  All parameters are enumerated
from these small domains or induced from training pairs; programs are verified on all pairs before yield.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def comps(g, ok, nb=N8, region=None):
    h, w = H(g), W(g); seen = set(); out = []
    for r in range(h):
        for c in range(w):
            if (r, c) in seen or not ok(r, c): continue
            st = [(r, c)]; seen.add((r, c)); cells = {}
            while st:
                y, x = st.pop(); cells[(y, x)] = g[y][x]
                for dy, dx in nb:
                    p = (y + dy, x + dx)
                    if 0 <= p[0] < h and 0 <= p[1] < w and p not in seen and ok(*p):
                        seen.add(p); st.append(p)
            out.append(cells)
    return out


def bb(cells):
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    return min(ys), min(xs), max(ys), max(xs)


# ------------------------------------------------------------------ targets
def rect_target(g):
    """Largest single-colour 4-component whose bbox contains only tiny marker blobs (>=1 marker)."""
    best = None
    for col in {v for r in g for v in r}:
        for cp in comps(g, lambda y, x, col=col: g[y][x] == col, N4):
            r0, c0, r1, c1 = bb(cp); area = (r1 - r0 + 1) * (c1 - c0 + 1)
            if area < 9 or len(cp) * 2 < area or r1 == r0 or c1 == c0: continue
            if best and area <= best[0]: continue
            inb = lambda y, x: r0 <= y <= r1 and c0 <= x <= c1 and g[y][x] != col
            marks = comps(g, inb, N4)
            if not marks or any(len(m) > 2 for m in marks): continue
            best = (area, col, (r0, c0, r1, c1))
    return best


def shared_colour(pieces):
    common = None; cnt = Counter()
    for p in pieces:
        cs = set(p.values()); cnt.update(p.values())
        common = cs if common is None else common & cs
    if not common or len(set(cnt)) < 2: return None
    return min(common, key=lambda c: (cnt[c], c))


def setup(g, target, root_col, bgc=None):
    """-> dict(canvas, free, body, pieces, acols, base_bbox, bg) or None."""
    if target == 'rect':
        t = rect_target(g)
        if not t: return None
        _, fill, (r0, c0, r1, c1) = t
        inside = lambda y, x: r0 <= y <= r1 and c0 <= x <= c1
        outc = Counter(g[y][x] for y in range(H(g)) for x in range(W(g)) if not inside(y, x))
        if not outc: return None
        sbg = outc.most_common(1)[0][0]
        pieces = comps(g, lambda y, x: not inside(y, x) and g[y][x] != sbg)
        if not pieces or len(pieces) > 30: return None
        canvas = {(y, x): g[y][x] for y in range(r0, r1 + 1) for x in range(c0, c1 + 1)}
        free = {p: v for p, v in canvas.items() if v != fill}
        return dict(canvas=canvas, free=free, body=set(), pieces=pieces, acols=set(free.values()),
                    bbox=(r0, c0, r1, c1), bg=fill, clip=True)
    bg = bgc if bgc is not None and any(bgc in r for r in g) else bg_of(g)
    pieces = comps(g, lambda y, x: g[y][x] != bg)
    if len(pieces) < 2 or len(pieces) > 30: return None
    k = shared_colour(pieces)
    if k is None: return None
    if target == 'root':
        roots = [p for p in pieces if root_col in p.values()]
        if len(roots) != 1 or root_col == k: return None
        root = roots[0]
    else:
        sz = sorted(len(p) for p in pieces)
        if sz[-1] == sz[-2]: root = max(pieces, key=lambda p: (len(p), -min(p)[0], -min(p)[1]))
        else: root = max(pieces, key=len)
    pieces = [p for p in pieces if p is not root]
    free = {p: v for p, v in root.items() if v == k}
    body = {p for p, v in root.items() if v != k}
    return dict(canvas=dict(root), free=free, body=body, pieces=pieces, acols={k},
                bbox=(0, 0, H(g) - 1, W(g) - 1), bg=bg, clip=False, fdir=adirs(root, {k}))


def adirs(piece, acols):
    """For each anchor cell: the 4-directions in which its own piece's body lies."""
    return {(y, x): {(a, b) for a, b in N4 if (y + a, x + b) in piece and piece[(y + a, x + b)] not in acols}
            for (y, x), v in piece.items() if v in acols}


# ------------------------------------------------------------------ placement
def conn_moves(st, piece, pd):
    """Connector matching: translations where >=1 piece connector coincides with a free connector, the two
    bodies meet it from different sides, and nothing else collides.  -> [(hits, bridges, t)]"""
    pa = {p: v for p, v in piece.items() if v in st['acols']}
    pb = [p for p, v in piece.items() if v not in st['acols']]
    free, body, fd = st['free'], st['body'], st['fdir']
    h, w = st['bbox'][2] + 1, st['bbox'][3] + 1
    ts = {(f[0] - q[0], f[1] - q[1]) for q, v in pa.items() for f, fv in free.items() if fv == v}
    res = []
    for dy, dx in ts:
        ok = True; hit = br = 0
        for y, x in pb:
            p = (y + dy, x + dx)
            if not (0 <= p[0] < h and 0 <= p[1] < w) or p in body or p in free: ok = False; break
        if not ok: continue
        for (y, x), v in pa.items():
            p = (y + dy, x + dx)
            if not (0 <= p[0] < h and 0 <= p[1] < w) or p in body: ok = False; break
            if p in free:
                a, b = pd[(y, x)], fd.get(p, set())
                if free[p] != v or a & b: ok = False; break
                hit += 1; br += any((-u, -z) in b for u, z in a)
        if ok and hit: res.append((hit, br, (dy, dx)))
    return res



def assemble(st, limit=4000):
    """Search placements of all pieces (DFS); best = (placed, hits, bridges); None unless unique best."""
    pieces = st['pieces']; pds = [adirs(p, st['acols']) for p in pieces]
    best = [None, set()]; seen = set(); nodes = [0]

    def rec(st, todo, placed, score):
        key = frozenset(placed)
        if key in seen or nodes[0] > limit: return
        seen.add(key); nodes[0] += 1
        sc = (len(placed),) + score
        if best[0] is None or sc > best[0]: best[0] = sc; best[1] = {key}
        elif sc == best[0]: best[1].add(key)
        moves = [(hit, br, i, t) for i in todo for hit, br, t in conn_moves(st, pieces[i], pds[i])]
        if not moves: return
        top = max(m[:2] for m in moves)                  # branch only over the strongest joins
        for hit, br, i, t in moves:
            if (hit, br) != top: continue
            s2 = dict(canvas=dict(st['canvas']), free=dict(st['free']), body=set(st['body']),
                      fdir=dict(st['fdir']), acols=st['acols'], bbox=st['bbox'])
            place(s2, pieces[i], t, 'two')
            rec(s2, todo - {i}, placed | {(i, t)}, (score[0] + hit, score[1] + br))

    rec(st, frozenset(range(len(pieces))), frozenset(), (0, 0))

    if nodes[0] > limit or len(best[1]) != 1: return None
    (sol,) = best[1]
    for i, t in sol: place(st, pieces[i], t, 'two')
    return len(sol)


def candidates(st, piece, match, minhit=2):
    pa = {p: v for p, v in piece.items() if v in st['acols']}
    pb = {p: v for p, v in piece.items() if v not in st['acols']}
    free, body = st['free'], st['body']
    if not pa: return []
    ts = set()
    if match == 'comp':
        for f in free:
            for q in pb: ts.add((f[0] - q[0], f[1] - q[1]))
    else:
        for q, v in pa.items():
            for f, fv in free.items():
                if fv == v: ts.add((f[0] - q[0], f[1] - q[1]))
    r0, c0, r1, c1 = st['bbox']
    res = []
    for dy, dx in ts:
        mb = {(y + dy, x + dx) for y, x in pb}
        ma = {(y + dy, x + dx): v for (y, x), v in pa.items()}
        if match == 'comp':
            if mb & body or not all(p in body for p in ma): continue
            cov = sum(1 for p in free if p in mb)
            if cov == 0: continue
            adj = sum(1 for (y, x) in ma if any((y + a, x + b) in free for a, b in N4))
            res.append(((cov, adj), (dy, dx)))
            continue
        hit = sum(1 for p, v in ma.items() if free.get(p) == v)
        if match == 'two':                         # coinciding connectors must bridge the two bodies
            pd = adirs(piece, st['acols']); fd = st['fdir']
            if any(free.get((y + dy, x + dx)) == v and not any((-a, -b) in fd.get((y + dy, x + dx), ())
                                                              for a, b in pd[(y, x)])
                   for (y, x), v in pa.items()): continue
        if match == 'all':
            if hit != len(ma) or mb & body: continue
            if not st['clip'] and any(not (r0 <= y <= r1 and c0 <= x <= c1) for y, x in mb): continue
        else:
            if hit < minhit or mb & body or mb & set(free): continue
            if any(p in body for p in ma if free.get(p) != ma[p]): continue
            if any(not (r0 <= y <= r1 and c0 <= x <= c1) for y, x in list(mb) + list(ma)): continue
        res.append((hit, (dy, dx)))
    return res


def place(st, piece, t, match):
    dy, dx = t
    acols = st['acols']
    if 'fdir' in st:
        for (y, x), d in adirs(piece, acols).items(): st['fdir'][(y + dy, x + dx)] = d
    for (y, x), v in piece.items():
        p = (y + dy, x + dx)
        if v in acols:
            if match == 'comp': continue               # glue lands on assembly body: keep body colour
            if st['free'].get(p) == v: del st['free'][p]
            elif match == 'two': st['free'][p] = v
            st['canvas'][p] = v
        else:
            if match == 'comp' and p in st['free']: del st['free'][p]
            st['canvas'][p] = v; st['body'].add(p)


def fit(g, target, match, out, root_col=None, need_all=False, bgc=None):
    st = setup(g, target, root_col, bgc)
    if st is None: return None
    todo = list(st['pieces']); placed = 0
    minhit = 2
    if match == 'two':
        placed = assemble(st) or 0
        todo = todo[placed:] if placed else todo
    while todo and match != 'two':
        prog = False
        for piece in sorted(todo, key=lambda p: -len(p)):
            c = candidates(st, piece, match, minhit)
            if not c: continue
            m = max(h for h, _ in c); best = [t for h, t in c if h == m]
            if len(best) != 1: continue
            place(st, piece, best[0], match); todo.remove(piece); placed += 1; prog = True
            break
        if prog: minhit = 2
        elif match == 'two' and minhit == 2: minhit = 1   # fall back to a single bridging connector
        else: break
    if placed == 0 or (need_all and todo): return None
    canvas = st['canvas']
    if out == 'target':
        r0, c0, r1, c1 = st['bbox']
    elif out == 'full':
        r0, c0, r1, c1 = 0, 0, H(g) - 1, W(g) - 1
    else:
        r0, c0, r1, c1 = bb(canvas)
    if r1 - r0 >= 30 or c1 - c0 >= 30: return None
    res = [[st['bg']] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
    for (y, x), v in canvas.items():
        if r0 <= y <= r1 and c0 <= x <= c1: res[y - r0][x - c0] = v
    return res


# ------------------------------------------------------------------ induction
def root_colours(train):
    """Colours whose (unique) piece sits unchanged at the same place in every training output."""
    ok = None
    for p in train:
        i, o = p['input'], p['output']
        if (H(i), W(i)) != (H(o), W(o)): return set()
        bg = bg_of(i)
        pcs = comps(i, lambda y, x: i[y][x] != bg)
        cs = set()
        for c in {v for r in i for v in r} - {bg}:
            ps = [q for q in pcs if c in q.values()]
            if len(ps) == 1 and len(ps[0]) >= 3 and all(o[y][x] == v for (y, x), v in ps[0].items()):
                cs.add(c)
        ok = cs if ok is None else ok & cs
    return ok or set()


CONFIGS = (('rect', 'all', 'target'), ('root', 'two', 'full'), ('largest', 'two', 'full'),
           ('largest', 'comp', 'union'), ('largest', 'all', 'union'), ('largest', 'comp', 'full'))


def fam_fit_by_anchor(train):
    i0, o0 = train[0]['input'], train[0]['output']
    same = (H(i0), W(i0)) == (H(o0), W(o0))
    for target, match, out in CONFIGS:
        if out == 'full' and not same: continue
        if out != 'full' and same: continue
        roots = sorted(root_colours(train)) if target == 'root' else [None]
        for rc in roots[:3]:
          for bgc in ((None,) if target == 'rect' else (None, glob_bg(train))):
            for need in (True, False):
                fn = lambda g, a=target, b=match, c=out, rc=rc, nd=need, bgc=bgc: fit(g, a, b, c, rc, nd, bgc)
                good = True
                for p in train:
                    try: r = fn(p['input'])
                    except Exception: r = None
                    if r != p['output']: good = False; break
                if good:
                    yield (f"fit-by-anchor[{target},{match},{out}{',bg=' + str(bgc) if bgc is not None else ''}{',root=' + str(rc) if rc is not None else ''}"
                           f"{',all' if need else ''}]", 5, fn)
                    break
            else: continue
            break


def glob_bg(train):
    """Background role induced over the whole task: most common colour over all training inputs."""
    c = Counter(v for p in train for r in p['input'] for v in r)
    return c.most_common(1)[0][0]


FAMILIES = (fam_fit_by_anchor,)


# ================================================================== crop.fit_by_shape
# Same idea with the anchor being the SHAPE of a hole: a host component with bg holes inside its bbox; every
# hole is filled by a loose piece whose key cells (all its cells | its host-coloured cells) have the hole's
# shape (identity | dihedral; pieces optionally drawn at scale s); output = host bbox (optionally x s).
def _d8(cells):
    """cells: {(y,x): v} -> list of 8 normalised dihedral images."""
    out = []
    for k in range(8):
        t = {}
        for (y, x), v in cells.items():
            a, b = (y, x) if k < 4 else (y, -x)
            for _ in range(k % 4): a, b = b, -a
            t[(a, b)] = v
        out.append(_norm(t))
    return out


def _norm(cells):
    y0 = min(y for y, _ in cells); x0 = min(x for _, x in cells)
    return {(y - y0, x - x0): v for (y, x), v in cells.items()}


def _down(cells, s):
    if s == 1: return cells
    c = _norm(cells); out = {}
    for (y, x), v in c.items():
        q = (y // s, x // s)
        if out.setdefault(q, v) != v: return None
    for (y, x), v in out.items():
        if any(c.get((y * s + a, x * s + b)) != v for a in range(s) for b in range(s)): return None
    if len(out) * s * s != len(c): return None
    return out


def fit_shape(g, key, hconn, dih, s, up, bgc=None):
    if s == "auto":                    # piece scale induced per grid: the largest s at which every hole fits
        for k in (4, 3, 2, 1):
            r = fit_shape(g, key, hconn, dih, k, k if up == 's' else up, bgc)
            if r is not None: return r
        return None
    bg = bgc if bgc is not None and any(bgc in r for r in g) else bg_of(g)
    best = None
    for col in {v for r in g for v in r} - {bg}:
        for h in comps(g, lambda y, x, col=col: g[y][x] == col, N4):
            if len(h) < 4: continue
            r0, c0, r1, c1 = bb(h)
            inb = lambda y, x: r0 <= y <= r1 and c0 <= x <= c1 and g[y][x] == bg
            holes = comps(g, inb, N8 if hconn == 8 else N4)
            if not holes or len(holes) > 12: continue
            hk = set(h)
            pieces = [p for p in comps(g, lambda y, x: g[y][x] != bg and (y, x) not in hk)
                      if not (r0 <= min(p)[0] <= r1 and c0 <= min(p, key=lambda q: q[1])[1] <= c1)]
            fills = {}; ok = True; used = set()
            for hole in sorted(holes, key=len):
                hn = _norm(hole); hy, hx = min(y for y, _ in hole), min(x for _, x in hole)
                opts = {}
                for pi, p in enumerate(pieces):
                    if pi in used: continue
                    pd = _down(p, s)
                    if pd is None: continue
                    for t in (_d8(pd) if dih else [_norm(pd)]):
                        kc = {q: v for q, v in t.items() if key == 'all' or v == col}
                        if not kc or len(kc) != len(hn): continue
                        kn = _norm(kc)
                        if set(kn) != set(hn): continue
                        ky, kx = min(y for y, _ in kc), min(x for _, x in kc)
                        dy, dx = hy - ky, hx - kx
                        paint = {(y + dy, x + dx): v for (y, x), v in t.items()}
                        if any(not (r0 <= y <= r1 and c0 <= x <= c1) or (g[y][x] != col and (y, x) not in hole)
                               for y, x in paint): continue
                        opts.setdefault(tuple(sorted(paint.items())), pi)
                        break                                 # first fitting transform: rotations before flips
                if len(opts) != 1: ok = False; break
                (pt, pi), = opts.items(); used.add(pi); fills.update(dict(pt))
            if not ok: continue
            area = (r1 - r0 + 1) * (c1 - c0 + 1)
            if best is None or area > best[0]: best = (area, (r0, c0, r1, c1), fills, col)
            elif area == best[0]: best = (area, None, None, None)
    if not best or best[1] is None: return None
    r0, c0, r1, c1 = best[1]
    out = [[g[y][x] for x in range(c0, c1 + 1)] for y in range(r0, r1 + 1)]
    for (y, x), v in best[2].items(): out[y - r0][x - c0] = v
    if up > 1: out = [[v for v in row for _ in range(up)] for row in out for _ in range(up)]
    if len(out) > 30 or len(out[0]) > 30: return None
    return out


def fam_fit_by_shape(train):
    i0, o0 = train[0]['input'], train[0]['output']
    if H(o0) >= H(i0) and W(o0) >= W(i0) and (H(o0), W(o0)) == (H(i0), W(i0)): return
    for key in ('all', 'host'):
        for hconn in (4, 8):
            for dih in (False, True):
                for s, up in ((1, 1), ('auto', 's'), (2, 2), (2, 1), (1, 2)):
                    fn = lambda g, a=key, b=hconn, c=dih, d=s, e=up: fit_shape(g, a, b, c, d, e)
                    try: good = all(fn(p['input']) == p['output'] for p in train)
                    except Exception: good = False
                    if good:
                        yield (f"fit-by-shape[{key},{hconn},{'d8' if dih else 'id'},s={s},up={up}]", 5, fn)
                        return


FAMILIES = (fam_fit_by_anchor, fam_fit_by_shape)
