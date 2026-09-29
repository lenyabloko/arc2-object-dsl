"""move.to_position: a mover is placed so that a reference point of it coincides with a target point defined by an
anchor that exists in the input; the original is erased.

One primitive  place(movers, ref, target, dihedral, rest)  with the target resolver chosen from a small enumerated set:
  key_marker   ref = key-colour cells (or the mover's corner cell diagonal to its single key cell);
               target = isolated monochrome marker(s) of the same colour; optional dihedral, ties broken by making
               line-coloured cells face the full-length line (border / divider) of their colour; one-to-one assignment.
  clamp        ref = singleton mover; target = nearest cell of the (unique) multi-cell anchor object's bbox.
  lattice      ref = mover bbox; target = centre of the lattice cell (cells between rows/cols of a static dot colour).
  corner       ref = singleton inside a frame; target = outer corner of the frame (opposite / same / h- / v-mirrored).
  codes        ref = mover centre; target = every interior cell whose row-code and column-code (frame border cells)
               equal the mover colour (copies); unmatched movers stay.
  dock         ref = piece's hub-facing edge; target = hub side of the same colour; dihedral chosen so the piece's
               first layer is exactly flush with that side.
  edge_line    ref = full-length line through a frame; target = a frame edge (per orientation).
Every parameter (colours, roles, which edge/corner, paint order, dihedral) is induced from the training pairs by
enumerating a small domain; the harness verifies exactness on all pairs.
"""
import sys; sys.path.insert(0, '/home/claude/work/widen')
from collections import Counter
from gdsl import H, W, bg_of, objects, bbox, static_colours

# ------------------------------------------------------------------ shared helpers
DIH = {
    "id": lambda y, x: (y, x), "r90": lambda y, x: (x, -y), "r180": lambda y, x: (-y, -x), "r270": lambda y, x: (-x, y),
    "fh": lambda y, x: (y, -x), "fv": lambda y, x: (-y, x), "T": lambda y, x: (x, y), "aT": lambda y, x: (-x, -y)}


def same_shape(train):
    return all(H(p["input"]) == H(p["output"]) and W(p["input"]) == W(p["output"]) for p in train)


def tcells(cells, d):
    """cells: list of (y,x,c) -> transformed and normalised to min (0,0)."""
    f = DIH[d]; t = [(*f(y, x), c) for y, x, c in cells]
    my = min(y for y, _, _ in t); mx = min(x for _, x, _ in t)
    return [(y - my, x - mx, c) for y, x, c in t]


def coloured(g, ob): return [(y, x, g[y][x]) for y, x in ob]


def touches_edge(ob, g):
    return any(y in (0, H(g) - 1) or x in (0, W(g) - 1) for y, x in ob)


def spans(ob, g):
    y0, x0, y1, x1 = bbox(ob)
    return y1 - y0 + 1 == H(g) or x1 - x0 + 1 == W(g)


def major_lines(g, bg):
    """Rows/cols more than half covered by one non-bg colour: list of (axis, index, colour)."""
    out = []
    for y in range(H(g)):
        c, n = Counter(g[y]).most_common(1)[0]
        if c != bg and 2 * n > W(g): out.append(("r", y, c))
    for x in range(W(g)):
        c, n = Counter(g[y][x] for y in range(H(g))).most_common(1)[0]
        if c != bg and 2 * n > H(g): out.append(("c", x, c))
    return out


def full_lines(g, bg):
    """Full-length uniform non-bg rows/cols: list of (axis, index, colour)."""
    out = []
    for y in range(H(g)):
        if len(set(g[y])) == 1 and g[y][0] != bg: out.append(("r", y, g[y][0]))
    for x in range(W(g)):
        col = {g[y][x] for y in range(H(g))}
        if len(col) == 1 and g[0][x] != bg: out.append(("c", x, g[0][x]))
    return out


def inb(g, y, x): return 0 <= y < H(g) and 0 <= x < W(g)


# ------------------------------------------------------------------ key_marker
def _key_marker(g, conn, ref, dih):
    bg = bg_of(g)
    lines = major_lines(g, bg)
    band = {(y, x) for a, i, c in lines for (y, x) in ([(i, x) for x in range(W(g))] if a == "r" else
                                                        [(y, i) for y in range(H(g))]) if g[y][x] == c}
    gm = [[bg if (y, x) in band else g[y][x] for x in range(W(g))] for y in range(H(g))]
    obs = [coloured(g, ob) for ob in objects(gm, bg, diag=conn == 8, by_colour=False)]
    multi = [ob for ob in obs if len({c for _, _, c in ob}) > 1 and not spans([(y, x) for y, x, _ in ob], g)]
    mono = [ob for ob in obs if len({c for _, _, c in ob}) == 1 and not spans([(y, x) for y, x, _ in ob], g)]
    mcols = {c for ob in multi for _, _, c in ob}
    markers = [ob for ob in mono if ob[0][2] in mcols]
    if not markers or not multi: return None
    kcols = {ob[0][2] for ob in markers}
    mk_of = {}
    for i, ob in enumerate(markers):
        for y, x, c in ob: mk_of[(y, x)] = (i, c)
    lcols = {c for _, _, c in lines}

    def score(cells):
        s = 0
        for y, x, c in cells:
            if c in lcols:
                s += min(abs((y if a == "r" else x) - i) for a, i, cc in lines if cc == c)
        return s

    plans = []
    for mi, mv in enumerate(multi):
        keys = [(y, x, c) for y, x, c in mv if c in kcols]
        if not keys: continue
        if ref == "corner" and len(keys) != 1: continue
        cands = {}
        for d in (DIH if dih else ("id",)):
            tc = tcells(mv, d); cs = {(y, x): c for y, x, c in tc}
            tk = [(y, x, c) for y, x, c in tc if c in kcols]
            if ref == "key":
                refs = tk
            else:
                ky, kx, kc = tk[0]; rr = []
                for dy in (-1, 1):
                    for dx in (-1, 1):
                        if (ky + dy, kx + dx) in cs and (ky + dy, kx) in cs and (ky, kx + dx) in cs:
                            rr.append((ky + dy, kx + dx, kc))
                if len(rr) != 1: continue
                refs = rr
            y0, x0, c0 = refs[0]
            for (my, mx), (i, c) in mk_of.items():
                if c != c0: continue
                oy, ox = my - y0, mx - x0
                used = set(); ok = True
                for y, x, c in refs:
                    m = mk_of.get((y + oy, x + ox))
                    if m is None or m[1] != c: ok = False; break
                    used.add(m[0])
                if not ok: continue
                cov = {(y + oy, x + ox) for y, x, _ in refs}
                if any((y, x) not in cov for u in used for y, x, _ in markers[u]): continue
                placed = tuple(sorted((y + oy, x + ox, c) for y, x, c in tc))
                if not all(inb(g, y, x) for y, x, _ in placed): continue
                sc = (score(placed), d not in ("id", "r90", "r180", "r270"))
                if placed not in cands or sc < cands[placed][0]: cands[placed] = (sc, frozenset(used))
        if cands:
            plans.append((mi, len(keys), cands))
    if not plans: return None
    out = [r[:] for r in g]
    taken = set(); todo = []
    for mi, nk, cands in sorted(plans, key=lambda p: -p[1]):
        opts = [(sc, pl, u) for pl, (sc, u) in cands.items() if not (u & taken)]
        if not opts: continue
        opts.sort(key=lambda t: t[0])
        if len(opts) > 1 and opts[1][0] == opts[0][0]: return None
        _, pl, u = opts[0]; taken |= u; todo.append((mi, pl))
    if not todo: return None
    for mi, _ in todo:
        for y, x, _ in multi[mi]: out[y][x] = bg
    for u in taken:
        for y, x, _ in markers[u]: out[y][x] = bg
    for _, pl in todo:
        for y, x, c in pl: out[y][x] = c
    return out


def fam_key_marker(train):
    if not same_shape(train): return
    for conn in (4, 8):
        for ref in ("key", "corner"):
            for dih in (False, True):
                yield (f"to-position:key-marker[{conn},{ref},{'dih' if dih else 'id'}]", 4 + dih,
                       lambda g, conn=conn, ref=ref, dih=dih: _key_marker(g, conn, ref, dih))


# ------------------------------------------------------------------ clamp into anchor
def _clamp(g, rest):
    bg = bg_of(g)
    obs = objects(g, bg, diag=True, by_colour=True)
    big = [ob for ob in obs if len(ob) > 1]; small = [ob for ob in obs if len(ob) == 1]
    if len(big) != 1 or not small: return None
    r0, c0, r1, c1 = bbox(big[0])
    out = [r[:] for r in g]
    if rest == "erase":
        for y, x in big[0]: out[y][x] = bg
    tgt = {}
    for (y, x), in small:
        t = (min(max(y, r0), r1), min(max(x, c0), c1))
        if t in tgt or t == (y, x): return None
        tgt[t] = g[y][x]; out[y][x] = bg
    for (y, x), c in tgt.items(): out[y][x] = c
    return out


def fam_clamp(train):
    if not same_shape(train): return
    for rest in ("keep", "erase"):
        yield (f"to-position:clamp-into-anchor[{rest}]", 4, lambda g, rest=rest: _clamp(g, rest))


# ------------------------------------------------------------------ lattice cell centre
def _intervals(seps, n):
    b = [-1] + sorted(seps) + [n]
    return [(a + 1, c - 1) for a, c in zip(b, b[1:]) if c - 1 >= a + 1]


def _lattice(g, L, rnd):
    bg = bg_of(g)
    cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == L]
    if len(cells) < 4: return None
    R = {y for y, _ in cells}; C = {x for _, x in cells}
    if len(R) < 2 or len(C) < 2: return None
    # lattice: every L cell on a separator row AND column, or L covers whole rows/cols
    RI, CI = _intervals(R, H(g)), _intervals(C, W(g))
    gg = [[bg if v == L else v for v in r] for r in g]
    obs = objects(gg, bg, diag=True, by_colour=False)
    if not obs: return None
    out = [r[:] for r in g]
    paint = []
    for ob in obs:
        y0, x0, y1, x1 = bbox(ob); cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        ri = [iv for iv in RI if iv[0] - .5 <= cy <= iv[1] + .5]; ci = [iv for iv in CI if iv[0] - .5 <= cx <= iv[1] + .5]
        if len(ri) != 1 or len(ci) != 1: return None
        (a, b), (c, d) = ri[0], ci[0]
        h, w = y1 - y0 + 1, x1 - x0 + 1
        if h > b - a + 1 or w > d - c + 1: return None
        ny = a + ((b - a + 1 - h) + rnd) // 2; nx = c + ((d - c + 1 - w) + rnd) // 2
        for y, x in ob:
            paint.append((y - y0 + ny, x - x0 + nx, g[y][x])); out[y][x] = bg
    for y, x, c in paint:
        if g[y][x] == L: return None
        out[y][x] = c
    return out


def fam_lattice(train):
    if not same_shape(train): return
    st = static_colours(train)
    cols = [c for c in st if c != bg_of(train[0]["input"]) and all(any(c in r for r in p["input"]) for p in train)]
    for L in cols[:3]:
        for rnd in (0, 1):
            yield (f"to-position:lattice-centre[{'floor' if not rnd else 'ceil'}]", 4,
                   lambda g, L=L, rnd=rnd: _lattice(g, L, rnd))


# ------------------------------------------------------------------ frame corner
def _corner(g, mode):
    bg = bg_of(g)
    obs = objects(g, bg, diag=True, by_colour=True)
    frames = [ob for ob in obs if len(ob) >= 8]
    if len(frames) != 1: return None
    r0, c0, r1, c1 = bbox(frames[0]); fs = set(frames[0])
    inner = [ob for ob in obs if ob is not frames[0]]
    if not inner or any(len(ob) != 1 for ob in inner): return None
    out = [r[:] for r in g]; paint = {}
    for (y, x), in inner:
        if not (r0 < y < r1 and c0 < x < c1): return None
        dy, dx = (y - r0) - (r1 - y), (x - c0) - (c1 - x)
        if dy == 0 or dx == 0: return None
        top, left = dy < 0, dx < 0
        if mode in ("opp", "v"): top = not top
        if mode in ("opp", "h"): left = not left
        t = (r0 - 1 if top else r1 + 1, c0 - 1 if left else c1 + 1)
        if not inb(g, *t) or t in paint: return None
        paint[t] = g[y][x]; out[y][x] = bg
    for (y, x), c in paint.items(): out[y][x] = c
    return out


def fam_corner(train):
    if not same_shape(train): return
    for mode in ("opp", "same", "h", "v"):
        yield (f"to-position:frame-outer-corner[{mode}]", 4, lambda g, mode=mode: _corner(g, mode))


# ------------------------------------------------------------------ border-code intersections
def _rect_bg(g, bg):
    best = None
    for ob in objects([[1 if v == bg else 0 for v in r] for r in g], 0, diag=False, by_colour=True):
        y0, x0, y1, x1 = bbox(ob)
        if len(ob) == (y1 - y0 + 1) * (x1 - x0 + 1) and y1 - y0 >= 2 and x1 - x0 >= 2:
            if best is None or len(ob) > best[0]: best = (len(ob), (y0, x0, y1, x1))
    return best and best[1]


def _codes(g, rowside, colside, order):
    bg = bg_of(g)
    rb = _rect_bg(g, bg)
    if not rb: return None
    r0, c0, r1, c1 = rb
    crs = [r0 - 1, r1 + 1] if rowside == "both" else [r0 - 1 if rowside == "top" else r1 + 1]
    ccs = [c0 - 1, c1 + 1] if colside == "both" else [c0 - 1 if colside == "left" else c1 + 1]
    if not all(inb(g, cr, c0) for cr in crs) or not all(inb(g, r0, cc) for cc in ccs): return None
    F = (r0 - 1, c0 - 1, r1 + 1, c1 + 1)
    movers = []
    for ob in objects(g, bg, diag=True, by_colour=True):
        y0, x0, y1, x1 = bbox(ob)
        if any(F[0] <= y <= F[2] and F[1] <= x <= F[3] for y, x in ob): continue
        if y1 - y0 + 1 >= H(g) or x1 - x0 + 1 >= W(g): continue
        if (y1 - y0) % 2 or (x1 - x0) % 2: continue
        movers.append(ob)
    if not movers: return None
    if order == "rev": movers = movers[::-1]
    out = [r[:] for r in g]; paint = []; hit = False
    for ob in movers:
        k = g[ob[0][0]][ob[0][1]]
        rows = [y for y in range(r0, r1 + 1) if all(g[y][cc] == k for cc in ccs)]
        cols = [x for x in range(c0, c1 + 1) if all(g[cr][x] == k for cr in crs)]
        if not rows or not cols: continue
        hit = True
        y0, x0, y1, x1 = bbox(ob); my, mx = (y0 + y1) // 2, (x0 + x1) // 2
        for y, x in ob: out[y][x] = bg
        for ty in rows:
            for tx in cols:
                paint.extend((y - my + ty, x - mx + tx, k) for y, x in ob)
    if not hit: return None
    for y, x, c in paint:
        if r0 <= y <= r1 and c0 <= x <= c1: out[y][x] = c
    return out


def fam_codes(train):
    if not same_shape(train): return
    for rs, cs in (("top", "left"), ("both", "both"), ("top", "right"), ("bottom", "left"), ("bottom", "right")):
            for order in ("fwd", "rev"):
                yield (f"to-position:code-intersections[{rs},{cs},{order}]", 5,
                       lambda g, rs=rs, cs=cs, order=order: _codes(g, rs, cs, order))


# ------------------------------------------------------------------ dock onto hub side
def _dock(g, rest):
    bg = bg_of(g)
    hubs = [ob for ob in objects(g, bg, diag=True, by_colour=False) if len({g[y][x] for y, x in ob}) >= 2]
    if len(hubs) != 1: return None
    hub = hubs[0]; hs = set(hub)
    hy0, hx0, hy1, hx1 = bbox(hub)
    pieces = [ob for ob in objects(g, bg, diag=True, by_colour=True) if not (set(ob) & hs)]
    if not pieces: return None
    out = [r[:] for r in g]
    for ob in pieces:
        for y, x in ob: out[y][x] = bg
    placedany = False
    for ob in pieces:
        k = g[ob[0][0]][ob[0][1]]
        S = [(y, x) for y, x in hub if g[y][x] == k]
        sides = []
        if S and all(x == hx0 for _, x in S): sides.append((0, -1))
        if S and all(x == hx1 for _, x in S): sides.append((0, 1))
        if S and all(y == hy0 for y, _ in S): sides.append((-1, 0))
        if S and all(y == hy1 for y, _ in S): sides.append((1, 0))
        if len(sides) != 1:
            if rest == "keep":
                for y, x in ob: out[y][x] = k
            continue
        dy, dx = sides[0]
        layer1 = {(y + dy, x + dx) for y, x in S}
        # projection coordinate along the outward direction
        proj = lambda y, x: y * dy + x * dx
        res = set()
        for d in DIH:
            tc = [(y, x) for y, x, _ in tcells([(y, x, 0) for y, x in ob], d)]
            lo = min(proj(y, x) for y, x in tc)
            first = [(y, x) for y, x in tc if proj(y, x) == lo]
            if len(first) != len(layer1): continue
            fy, fx = min(first); ty, tx = min(layer1)
            oy, ox = ty - fy, tx - fx
            if {(y + oy, x + ox) for y, x in first} != layer1: continue
            pl = frozenset((y + oy, x + ox) for y, x in tc)
            perp = (lambda y, x: x) if dy else (lambda y, x: y)
            if min(perp(*c) for c in pl) + max(perp(*c) for c in pl) != \
                    min(perp(*c) for c in S) + max(perp(*c) for c in S): continue
            if all(inb(g, y, x) for y, x in pl) and not (pl & hs): res.add(pl)
        if len(res) != 1:
            if res: return None
            if rest == "keep":
                for y, x in ob: out[y][x] = k
            continue
        placedany = True
        for y, x in next(iter(res)): out[y][x] = k
    return out if placedany else None


def fam_dock(train):
    if not same_shape(train): return
    for rest in ("erase", "keep"):
        yield (f"to-position:dock-on-hub-side[{rest}]", 5, lambda g, rest=rest: _dock(g, rest))


# ------------------------------------------------------------------ full-length lines snap to frame edge
def _edge_line(g, vside, hside):
    bg = bg_of(g)
    frames = []
    for ob in objects(g, bg, diag=False, by_colour=True):
        y0, x0, y1, x1 = bbox(ob)
        if y1 - y0 >= 2 and x1 - x0 >= 2 and set(ob) >= {(y, x) for y in (y0, y1) for x in range(x0, x1 + 1)} | \
                {(y, x) for x in (x0, x1) for y in range(y0, y1 + 1)}:
            frames.append((ob, (y0, x0, y1, x1)))
    if len(frames) != 1: return None
    ob, (r0, c0, r1, c1) = frames[0]; fc = g[ob[0][0]][ob[0][1]]
    vl = [x for x in range(W(g)) if all(g[y][x] != bg for y in range(H(g))) and
          len({g[y][x] for y in range(H(g))} - {fc}) == 1 and c0 < x < c1]
    hl = [y for y in range(H(g)) if all(v != bg for v in g[y]) and len(set(g[y]) - {fc}) == 1 and r0 < y < r1]
    if len(vl) > 1 or len(hl) > 1 or not (vl or hl): return None
    out = [r[:] for r in g]
    new = []
    for x in vl:
        L = ({g[y][x] for y in range(H(g))} - {fc}).pop()
        for y in range(H(g)):
            if out[y][x] == L: out[y][x] = bg
        tx = c0 if vside == "left" else c1
        new += [(y, tx, L) for y in range(H(g)) if not (r0 <= y <= r1)]
    for y in hl:
        L = (set(g[y]) - {fc}).pop()
        for x in range(W(g)):
            if out[y][x] == L: out[y][x] = bg
        ty = r0 if hside == "top" else r1
        new += [(ty, x, L) for x in range(W(g)) if not (c0 <= x <= c1)]
    for y, x, c in new: out[y][x] = c
    return out


def fam_edge_line(train):
    if not same_shape(train): return
    for vs in ("left", "right"):
        for hs in ("top", "bottom"):
            yield (f"to-position:line-to-frame-edge[{vs},{hs}]", 4, lambda g, vs=vs, hs=hs: _edge_line(g, vs, hs))


FAMILIES = (fam_key_marker, fam_clamp, fam_lattice, fam_corner, fam_codes, fam_dock, fam_edge_line)
