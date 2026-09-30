"""summarise.concentric_rings: an ordered colour list is rendered as nested concentric square rings.

One primitive, ring(depth d) = L[min(d, n-1)] (or a periodic table of d), with three induced
parameter axes:
  items/key : colour classes of the input ranked by count | bbox size | occlusion layer |
              distance to grid centre;  or a legend read from a corner/edge ray of the input;
              or a periodic table of d learned from the training outputs
  canvas    : fresh square (2n-1 | 2n | max item bbox dim | input side)
              | interior of the unique rectangular frame (depth from the frame)
              | around a seed cell on the input (unique isolated cell | unique line crossing)
  paint     : overwrite | bg-only
All choices are enumerated from small generic domains and verified on every training pair.
"""
import sys
sys.path.append('/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox


# ------------------------------------------------------------------ helpers
def _ring_grid(S, L):
    n = len(L)
    return [[L[min(min(y, x, S - 1 - y, S - 1 - x), n - 1)] for x in range(S)] for y in range(S)]


def _decode_rings(o):
    """Colour per depth if o is a square grid of monochrome concentric rings, else None."""
    S = H(o)
    if S != W(o): return None
    D = (S + 1) // 2; L = [None] * D
    for y in range(S):
        for x in range(S):
            d = min(y, x, S - 1 - y, S - 1 - x)
            if L[d] is None: L[d] = o[y][x]
            elif L[d] != o[y][x]: return None
    while len(L) > 1 and L[-1] == L[-2]: L.pop()
    return L


def _cells_by_colour(g, bg):
    cs = {}
    for y, r in enumerate(g):
        for x, v in enumerate(r):
            if v != bg: cs.setdefault(v, []).append((y, x))
    return cs


def _layers(g, bg, cells):
    """Bottom-to-top order of colour classes from occlusion evidence on their bbox perimeters
    (colour d seen on c's perimeter = d lies above c); the order violating the least evidence,
    None if that order is not unique or there is no evidence."""
    from itertools import permutations
    if len(cells) > 7: return None
    wt = Counter()
    for c, cs in cells.items():
        y0, x0, y1, x1 = bbox(cs)
        per = {(y0, x) for x in range(x0, x1 + 1)} | {(y1, x) for x in range(x0, x1 + 1)} | \
              {(y, x0) for y in range(y0, y1 + 1)} | {(y, x1) for y in range(y0, y1 + 1)}
        for y, x in per:
            v = g[y][x]
            if v != c and v != bg and v in cells: wt[(c, v)] += 1
    if not wt: return None
    best, arg = None, []
    for perm in permutations(cells):
        pos = {c: i for i, c in enumerate(perm)}
        cost = sum(n for (c, v), n in wt.items() if pos[v] < pos[c])
        if best is None or cost < best: best, arg = cost, [perm]
        elif cost == best: arg.append(perm)
    return list(arg[0]) if len(arg) == 1 else None


def _feature(g, bg, cells, key):
    h, w = H(g), W(g)
    if key == "count": return {c: len(v) for c, v in cells.items()}
    if key == "size":
        out = {}
        for c, v in cells.items():
            y0, x0, y1, x1 = bbox(v); out[c] = max(y1 - y0 + 1, x1 - x0 + 1)
        return out
    if key == "area":
        out = {}
        for c, v in cells.items():
            y0, x0, y1, x1 = bbox(v); out[c] = (y1 - y0 + 1) * (x1 - x0 + 1)
        return out
    if key == "centre":  # doubled Chebyshev distance of the class's nearest cell to the grid centre
        return {c: min(max(abs(2 * y - (h - 1)), abs(2 * x - (w - 1))) for y, x in v) for c, v in cells.items()}
    return None


def _rank(g, key, desc):
    bg = bg_of(g); cells = _cells_by_colour(g, bg)
    if not cells or len(cells) > 10: return None
    if key == "layer":
        o = _layers(g, bg, cells)
        if o is None: return None
        return o if not desc else o[::-1]
    f = _feature(g, bg, cells, key)
    vals = list(f.values())
    if len(set(vals)) != len(vals): return None  # ties -> ambiguous
    return sorted(cells, key=lambda c: -f[c] if desc else f[c])


def _canvas_size(g, L, how):
    n = len(L)
    if how == "2n-1": return 2 * n - 1
    if how == "2n": return 2 * n
    if how == "side": return H(g) if H(g) == W(g) else None
    if how == "maxdim":
        bg = bg_of(g); cells = _cells_by_colour(g, bg)
        m = 0
        for v in cells.values():
            y0, x0, y1, x1 = bbox(v); m = max(m, y1 - y0 + 1, x1 - x0 + 1)
        return m
    return None


# ------------------------------------------------------------------ A: fresh square canvas
def fam_rings_summary(train):
    outs = [p["output"] for p in train]
    Ls = [_decode_rings(o) for o in outs]
    if any(L is None or len(L) < 2 for L in Ls): return
    for key in ("count", "size", "area", "layer", "centre"):
        for desc in (True, False):
            ranks = [_rank(p["input"], key, desc) for p in train]
            if any(r is None or r != L for r, L in zip(ranks, Ls)): continue
            for how in ("2n-1", "2n", "maxdim", "side"):
                if all(_canvas_size(p["input"], L, how) == H(o) for p, L, o in zip(train, Ls, outs)):
                    def fn(g, key=key, desc=desc, how=how):
                        L = _rank(g, key, desc)
                        if not L: return None
                        S = _canvas_size(g, L, how)
                        if not S or S < 2 * len(L) - 1 or S > 30: return None
                        return _ring_grid(S, L)
                    yield ("rings:summary[key=%s%s,canvas=%s]" % (key, "-desc" if desc else "-asc", how), 4, fn)


# ------------------------------------------------------------------ legends (rays from corners)
RAYS = {}
for _cn, (_cy, _cx) in {"tl": (0, 0), "tr": (0, -1), "bl": (-1, 0), "br": (-1, -1)}.items():
    for _dn in ("row", "col", "diag"):
        RAYS[_cn + "-" + _dn] = (_cy, _cx, _dn)


def _legend(g, bg, ray, stop):
    cy, cx, dn = RAYS[ray]; h, w = H(g), W(g)
    y = cy % h; x = cx % w
    dy = 1 if y == 0 else -1; dx = 1 if x == 0 else -1
    if dn == "row": dy = 0
    if dn == "col": dx = 0
    L = []
    while 0 <= y < h and 0 <= x < w and (y, x) not in stop:
        if dn == "diag" and g[y][x] == bg: break
        L.append(g[y][x]); y += dy; x += dx
    while L and L[-1] == bg: L.pop()
    return L or None


# ------------------------------------------------------------------ B: inside a rectangular frame
def _frame(g, bg):
    """Unique single-colour rectangular outline (>=3x3) with an all-bg interior."""
    found = []
    for ob in objects(g, bg):
        y0, x0, y1, x1 = bbox(ob)
        if y1 - y0 < 2 or x1 - x0 < 2: continue
        per = 2 * (y1 - y0 + x1 - x0)
        if len(ob) != per: continue
        s = set(ob)
        if not all((y0, x) in s and (y1, x) in s for x in range(x0, x1 + 1)): continue
        if not all((y, x0) in s and (y, x1) in s for y in range(y0, y1 + 1)): continue
        if all(g[y][x] == bg for y in range(y0 + 1, y1) for x in range(x0 + 1, x1)):
            found.append((y0, x0, y1, x1, s))
    return found[0] if len(found) == 1 else None


def _fill_frame(g, ray):
    bg = bg_of(g); f = _frame(g, bg)
    if not f: return None
    y0, x0, y1, x1, s = f
    L = _legend(g, bg, ray, s)
    if not L: return None
    o = [r[:] for r in g]
    for y in range(y0 + 1, y1):
        for x in range(x0 + 1, x1):
            d = min(y - y0 - 1, x - x0 - 1, y1 - 1 - y, x1 - 1 - x)
            o[y][x] = L[min(d, len(L) - 1)]
    return o


def fam_rings_frame(train):
    i0, o0 = train[0]["input"], train[0]["output"]
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    if _frame(i0, bg_of(i0)) is None: return
    for ray in RAYS:
        if all(_fill_frame(p["input"], ray) == p["output"] for p in train):
            yield ("rings:frame[legend=%s]" % ray, 4, lambda g, ray=ray: _fill_frame(g, ray))


# ------------------------------------------------------------------ C: around a seed on the input
def _seed(g, bg, how):
    h, w = H(g), W(g)
    if how == "isolated":
        c = [(y, x) for y in range(h) for x in range(w) if g[y][x] != bg and
             all(g[yy][xx] == bg for yy in range(max(0, y - 1), min(h, y + 2))
                 for xx in range(max(0, x - 1), min(w, x + 2)) if (yy, xx) != (y, x))]
        return c[0] if len(c) == 1 else None
    if how == "crossing":
        rows = [y for y in range(h) if g[y][0] != bg and len(set(g[y])) == 1]
        cols = [x for x in range(w) if g[0][x] != bg and len({g[y][x] for y in range(h)}) == 1]
        return (rows[0], cols[0]) if len(rows) == 1 and len(cols) == 1 else None
    return None


def _paint_seed(g, how, L=None, ray=None, table=None):
    bg = bg_of(g); s = _seed(g, bg, how)
    if s is None: return None
    sy, sx = s; h, w = H(g), W(g); o = [r[:] for r in g]
    if ray is not None:
        L = _legend(g, bg, ray, {s})
        if not L or len(L) < 2 or L[0] != g[sy][sx]: return None
        for y in range(h):
            for x in range(w):
                d = max(abs(y - sy), abs(x - sx))
                if d < len(L): o[y][x] = L[d]
        return o
    p, T = table
    for y in range(h):
        for x in range(w):
            d = max(abs(y - sy), abs(x - sx))
            if d >= 1 and g[y][x] == bg: o[y][x] = T[d % p]
    return o


def _learn_table(train, how):
    for p in (1, 2, 3, 4):
        T = {}; ok = True
        for pr in train:
            g, o = pr["input"], pr["output"]; bg = bg_of(g); s = _seed(g, bg, how)
            if s is None: return None
            for y in range(H(g)):
                for x in range(W(g)):
                    d = max(abs(y - s[0]), abs(x - s[1]))
                    if d == 0 or g[y][x] != bg:
                        if o[y][x] != g[y][x]: return None
                        continue
                    k = d % p
                    if T.setdefault(k, o[y][x]) != o[y][x]: ok = False; break
                if not ok: break
            if not ok: break
        if ok and len(T) == p and len(set(T.values())) > 1: return (p, T)
    return None


def fam_rings_seed(train):
    i0, o0 = train[0]["input"], train[0]["output"]
    if (H(i0), W(i0)) != (H(o0), W(o0)): return
    for how in ("isolated", "crossing"):
        if any(_seed(p["input"], bg_of(p["input"]), how) is None for p in train): continue
        for ray in RAYS:
            if all(_paint_seed(p["input"], how, ray=ray) == p["output"] for p in train):
                yield ("rings:seed[%s,legend=%s]" % (how, ray), 4, lambda g, how=how, ray=ray: _paint_seed(g, how, ray=ray))
        tb = _learn_table(train, how)
        if tb and all(_paint_seed(p["input"], how, table=tb) == p["output"] for p in train):
            yield ("rings:seed[%s,periodic=%d]" % (how, tb[0]), 5, lambda g, how=how, tb=tb: _paint_seed(g, how, table=tb))


# ------------------------------------------------------------------ D: nested frames rebuilt from fragments
def _d4(y, x, s):
    m = s - 1
    return {(y, x), (x, y), (m - y, x), (y, m - x), (m - y, m - x), (m - x, y), (x, m - y), (m - x, m - y)}


def _complete(g, cs, s):
    """Unique D4-symmetric s x s pattern whose visible part (window inside the grid) equals the fragment cs."""
    h, w = H(g), W(g); y0, x0, y1, x1 = bbox(cs); fh, fw = y1 - y0 + 1, x1 - x0 + 1
    if fh > s or fw > s: return None
    rel = [(y - y0, x - x0) for y, x in cs]; found = set()
    for oy in range(s - fh + 1):
        for ox in range(s - fw + 1):
            P = set()
            for y, x in rel: P |= _d4(y + oy, x + ox, s)
            by, bx = y0 - oy, x0 - ox; ok = True
            for py, px in P:
                gy, gx = by + py, bx + px
                if 0 <= gy < h and 0 <= gx < w and (gy, gx) not in cs: ok = False; break
            if ok:
                # every visible fragment cell of the window must be in P (true by construction)
                found.add(frozenset(P))
                if len(found) > 1: return None
    return next(iter(found)) if found else None


def _nest_fragments(g):
    bg = bg_of(g); cells = _cells_by_colour(g, bg); n = len(cells)
    if n < 2 or n > 8: return None
    cells = {c: set(v) for c, v in cells.items()}
    vis = {}
    for c, v in cells.items():
        y0, x0, y1, x1 = bbox(v); vis[c] = max(y1 - y0 + 1, x1 - x0 + 1)
    lo = max(max(vis.values()), 2 * n - 1)
    for S in range(lo, min(30, lo + 6) + 1):
        sizes = [S - 2 * k for k in range(n)]
        if sizes[-1] < 1: continue
        feas = {c: {s: _complete(g, v, s) for s in sizes if s >= vis[c]} for c, v in cells.items()}
        feas = {c: {s: P for s, P in d.items() if P is not None} for c, d in feas.items()}
        # unique perfect matching colours -> sizes
        sols = []
        def rec(i, used, cur, cs=list(cells)):
            if len(sols) > 1: return
            if i == len(cs): sols.append(dict(cur)); return
            for s_, P in feas[cs[i]].items():
                if s_ not in used:
                    cur[cs[i]] = (s_, P); rec(i + 1, used | {s_}, cur); del cur[cs[i]]
        rec(0, frozenset(), {})
        if len(sols) == 1:
            o = [[bg] * S for _ in range(S)]
            for c, (s_, P) in sols[0].items():
                d = (S - s_) // 2
                for y, x in P: o[y + d][x + d] = c
            return o
        if len(sols) > 1: return None
    return None


def fam_rings_fragments(train):
    for p in train:
        o = p["output"]
        if H(o) != W(o) or o != [list(r) for r in zip(*o)] or o != o[::-1]: return
    if all(_nest_fragments(p["input"]) == p["output"] for p in train):
        yield ("rings:nest-fragments[D4]", 5, _nest_fragments)


FAMILIES = (fam_rings_summary, fam_rings_frame, fam_rings_seed, fam_rings_fragments)
