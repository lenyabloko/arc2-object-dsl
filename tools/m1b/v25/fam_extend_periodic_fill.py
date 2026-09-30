"""extend.periodic_fill: a periodic pattern visible in a known region is continued over a domain.

One primitive, parameters induced from training pairs:
  canvas : output size rule (same | 2x | 2x width | 2x height | square)           -- matched on all pairs
  domain : whole grid | each connected non-background region | each row/column line
  known  : all cells | cells not of an occluder colour (fixed colour absent from outputs, or the
           colour filling an edge strip) | bounding box of non-background cells
  key    : 'min'  smallest translation lattice {(py,s),(0,px)} (either orientation, py/px may be
                  infinite) consistent with the known cells
           'tile' period = known bounding box (anchored on it)
           'ring' L-shaped rings max(y,x) mod p (smallest consistent p)
  phase  : output offset (dy,dx) in [-2,2]^2 induced from the first pair (0 preferred)
Unknown lattice classes keep the input value (inside the input) or become background.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
import numpy as np
from gdsl import H, W, bg_of, colours

INF = None

# ------------------------------------------------------------------ lattices
def _reduce(y, x, lat):
    py, s, px = lat
    if py:
        k = y // py; y -= k * py; x -= k * s
    if px:
        x %= px
    return (y, x)

def _consistent(known, lat):
    d = {}
    rep = False
    for (y, x), v in known:
        k = _reduce(y, x, lat)
        u = d.get(k)
        if u is None:
            d[k] = v
        elif u != v:
            return None
        else:
            rep = True
    return d if rep else None

def _ncls(py, s, px, hk, wk):
    """Number of lattice classes met by a full hk x wk rectangle (the description length)."""
    if py is INF: return hk * px
    if px: return py * px
    tot = 0
    for r in range(min(py, hk)):
        nk = (hk - 1 - r) // py + 1
        tot += wk + abs(s) * (nk - 1)
    return tot

from functools import lru_cache
@lru_cache(maxsize=256)
def _cands(hk, wk):
    cands = []
    for py in list(range(1, hk)) + [INF]:
        for px in list(range(1, wk)) + [INF]:
            if py is INF and px is INF: continue
            if py is INF:
                cands.append((_ncls(py, 0, px, hk, wk), 0, (py, 0, px)))
                continue
            ss = range(px) if px else range(-(wk - 1), wk)
            for s in ss:
                sa = abs(s if not px or s <= px // 2 else s - px)
                a = _ncls(py, s, px, hk, wk)
                if a < hk * wk: cands.append((a, sa, (py, s, px)))
    cands.sort(key=lambda c: (c[0], c[1]))
    return tuple(cands)

def _min_lattice(known, hk, wk, limit=20000):
    """Translation lattice with the fewest classes that is consistent with the known cells.
    known: list of ((y,x),v) relative to the known bbox (0..hk-1, 0..wk-1)."""
    cands = _cands(hk, wk)
    A = np.full((hk, wk), -1, dtype=np.int16)
    for (y, x), v in known: A[y, x] = v
    memo = {}
    def vec_ok(dy, dx):
        k = (dy, dx)
        if k not in memo:
            if dy >= hk or abs(dx) >= wk: memo[k] = True
            else:
                a = A[:hk - dy, max(0, -dx):wk - max(0, dx)]
                b = A[dy:, max(0, dx):max(0, dx) + a.shape[1]]
                m = (a >= 0) & (b >= 0)
                memo[k] = not bool(np.any(a[m] != b[m]))
        return memo[k]
    for n, (area, _, lat) in enumerate(cands):
        if n > limit: break
        py, s, px = lat
        if px and not vec_ok(0, px): continue
        if py and not vec_ok(py, s): continue
        d = _consistent(known, lat)
        if d is not None:
            return area, lat, d
    return None

def _T(g): return [list(r) for r in zip(*g)]

# ------------------------------------------------------------------ roles
def _strip_colour(g):
    """Colour filling an entire edge row/column (occluding strip); None unless unique."""
    h, w = H(g), W(g); cs = set()
    for line in (g[0], g[h - 1], [r[0] for r in g], [r[w - 1] for r in g]):
        if len(set(line)) == 1: cs.add(line[0])
    if len(cs) != 1: return None
    c = cs.pop()
    return c if c != bg_of(g) or True else None

def _known_cells(g, known, cells=None, bg=None):
    """Return list of ((y,x),v) known cells within `cells` (default whole grid)."""
    if cells is None:
        cells = [(y, x) for y in range(H(g)) for x in range(W(g))]
    if known == 'all':
        return [((y, x), g[y][x]) for y, x in cells]
    if known == 'bbox':
        nb = [(y, x) for y, x in cells if g[y][x] != bg]
        if not nb: return []
        y0 = min(y for y, _ in nb); y1 = max(y for y, _ in nb)
        x0 = min(x for _, x in nb); x1 = max(x for _, x in nb)
        return [((y, x), g[y][x]) for y, x in cells if y0 <= y <= y1 and x0 <= x <= x1]
    if known == 'strip':
        c = _strip_colour(g)
        if c is None: return []
    else:
        c = known  # integer occluder colour
    return [((y, x), g[y][x]) for y, x in cells if g[y][x] != c]

# ------------------------------------------------------------------ class functions
_CACHE = {}
def _class_fn(known, key):
    ck = (tuple(known), key)
    if ck in _CACHE: return _CACHE[ck]
    if len(_CACHE) > 4000: _CACHE.clear()
    r = _CACHE[ck] = _class_fn0(known, key)
    return r

def _class_fn0(known, key):
    """Return (lookup(y,x)->colour|None, lean) for known cells ((y,x),v) in grid coordinates.
    lean: -1 if the lattice extends leftward (for anchoring on enlarged canvases), 'T' flag."""
    if not known: return None
    ys = [p[0] for p, _ in known]; xs = [p[1] for p, _ in known]
    y0, x0 = min(ys), min(xs); hk = max(ys) - y0 + 1; wk = max(xs) - x0 + 1
    rel = [((y - y0, x - x0), v) for (y, x), v in known]
    if key == 'tile':
        if len(rel) != hk * wk: return None
        d = {p: v for p, v in rel}
        return (lambda y, x: d.get(((y - y0) % hk, (x - x0) % wk))), 0
    if key == 'ring':
        best = None
        ks = {max(y, x) for (y, x), _ in known}
        for p in range(1, max(ks) + 2):
            d = {}; ok = True
            for (y, x), v in known:
                if d.setdefault(max(y, x) % p, v) != v: ok = False; break
            if ok:
                best = (p, d); break
        if not best: return None
        p, d = best
        return (lambda y, x: d.get(max(y, x) % p) if y >= 0 and x >= 0 else None), 0
    # min lattice, both orientations
    a = _min_lattice(rel, hk, wk)
    b = _min_lattice([((x, y), v) for (y, x), v in rel], wk, hk)
    if a is None and b is None: return None
    if b is None or (a is not None and a[0] <= b[0]):
        _, lat, d = a
        return (lambda y, x: d.get(_reduce(y - y0, x - x0, lat))), (-1 if lat[0] and lat[1] < 0 and not lat[2] else 0)
    _, lat, d = b
    return (lambda y, x: d.get(_reduce(x - x0, y - y0, lat))), (-2 if lat[0] and lat[1] < 0 and not lat[2] else 0)

# ------------------------------------------------------------------ canvas rules
CANVAS = {
    'same': lambda h, w: (h, w),
    '2x': lambda h, w: (2 * h, 2 * w),
    '2w': lambda h, w: (h, 2 * w),
    '2h': lambda h, w: (2 * h, w),
    'square': lambda h, w: (max(h, w), max(h, w)),
}

def _regions(g, bg):
    h, w = H(g), W(g); seen = [[False] * w for _ in range(h)]; out = []
    for r in range(h):
        for c in range(w):
            if seen[r][c] or g[r][c] == bg: continue
            st = [(r, c)]; seen[r][c] = True; cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] and g[yy][xx] != bg:
                        seen[yy][xx] = True; st.append((yy, xx))
            out.append(cells)
    return out

def _line_fill(seq, key):
    """1D: seq = list of (pos,v) contiguous span; return (lookup(pos), ok)."""
    n = len(seq); a = seq[0][0]; vals = [v for _, v in seq]
    p = n
    if key == 'min':
        for q in range(1, n):
            if all(vals[i] == vals[i % q] for i in range(n)): p = q; break
    return lambda t: vals[(t - a) % p]

def render(g, canvas, domain, known, key, off=(0, 0)):
    h, w = H(g), W(g); bg = bg_of(g)
    Ho, Wo = CANVAS[canvas](h, w)
    if Ho > 30 or Wo > 30: return None
    dy, dx = off
    if domain == 'whole':
        kc = _known_cells(g, known, bg=bg)
        cf = _class_fn(kc, key)
        if cf is None: return None
        f, lean = cf
        ay = ax = 0
        if lean == -1: ax = Wo - w
        elif lean == -2: ay = Ho - h
        out = [[bg] * Wo for _ in range(Ho)]
        for Y in range(Ho):
            for X in range(Wo):
                y, x = Y - ay + dy, X - ax + dx
                v = f(y, x)
                if v is None:
                    yy, xx = Y - ay, X - ax
                    v = g[yy][xx] if 0 <= yy < h and 0 <= xx < w else bg
                out[Y][X] = v
        return out
    if canvas != 'same' or off != (0, 0): return None
    out = [r[:] for r in g]
    if domain == 'regions':
        regs = _regions(g, bg)
        if not regs: return None
        for cells in regs:
            rbg = Counter(g[y][x] for y, x in cells).most_common(1)[0][0]
            kc = _known_cells(g, known, cells, rbg)
            if not kc or len(kc) == len(cells): continue
            cf = _class_fn(kc, key)
            if cf is None: continue
            f, _ = cf
            for y, x in cells:
                v = f(y, x)
                if v is not None: out[y][x] = v
        return out
    if domain == 'lines':
        any_ = False
        for axis in (0, 1):
            L = g if axis == 0 else _T(g)
            for r, row in enumerate(L):
                idx = [i for i, v in enumerate(row) if v != bg]
                if len(idx) < 2: continue
                a, b = idx[0], idx[-1]
                f = _line_fill([(i, row[i]) for i in range(a, b + 1)], key)
                any_ = True
                for t in range(len(row)):
                    if axis == 0: out[r][t] = f(t)
                    else: out[t][r] = f(t)
        return out if any_ else None
    return None

# ------------------------------------------------------------------ family
OFFS = sorted(((a, b) for a in range(-2, 3) for b in range(-2, 3)), key=lambda o: (abs(o[0]) + abs(o[1]), abs(o[0]), -o[1], -o[0]))

def fam_periodic_fill(train):
    i0, o0 = train[0]['input'], train[0]['output']
    canv = [c for c, f in CANVAS.items() if all(f(H(p['input']), W(p['input'])) == (H(p['output']), W(p['output'])) for p in train)]
    if not canv: return
    if 'square' in canv and len(canv) > 1 and all(H(p['input']) == W(p['input']) for p in train):
        canv.remove('square')
    ins = [p['input'] for p in train]; outs = [p['output'] for p in train]
    occ = sorted(c for c in set().union(*map(colours, ins)) if not any(c in colours(o) for o in outs))
    knowns = ['all', 'bbox', 'strip'] + occ
    configs = []
    for cv in canv:
        for kn in knowns:
            for key in ('min', 'tile', 'ring'):
                configs.append((cv, 'whole', kn, key))
        if cv == 'same':
            for key in ('tile', 'min'):
                configs.append((cv, 'regions', 'bbox', key))
                configs.append((cv, 'lines', 'bbox', key))
    n = 0
    for cv, dom, kn, key in configs:
        try:
            base = render(i0, cv, dom, kn, key)
        except Exception:
            continue
        if base is None: continue
        offs = OFFS if dom == 'whole' else [(0, 0)]
        hits = 0
        for off in offs:
            try:
                r = base if off == (0, 0) else render(i0, cv, dom, kn, key, off)
            except Exception:
                r = None
            if r == o0:
                if cv == 'same' and dom == 'whole' and kn == 'all' and off == (0, 0) and r == i0:
                    break
                ks = kn if isinstance(kn, str) else f'c{kn}'
                name = f"periodic-fill:{key}[{cv},{dom},{ks}" + (f",off{off[0]},{off[1]}" if off != (0, 0) else '') + ']'
                cost = 4 + (off != (0, 0)) + (dom != 'whole')
                yield (name, cost, lambda g, cv=cv, dom=dom, kn=kn, key=key, off=off: render(g, cv, dom, kn, key, off))
                n += 1; hits += 1
                if off == (0, 0) or hits >= 2: break
        if n >= 12: return

FAMILIES = (fam_periodic_fill,)
