"""transform.kronecker: output = blocks laid out by a mask grid; block(i,j) = tile_on(mask[i,j]) if pred(mask[i,j]) else tile_off.

One core (`kron`) + role inducers that decide where mask / tile / colours come from:
  self   : mask = tile source = the input itself (pred over cell colours, tile = input or self-colour mask)
  panels : input split into equal panels; mask = one shape panel, tile = another, fg/bg recolour from solid panels
  legend : mask = multicolour object, tile_on(c) = the motif paired (by legend order) with swatch colour c
  inplace: mask = sparse dot lattice, tile = mask(largest shape) painted by dot colour, drawn in place at the shape
All parameters (predicate colour, roles, order, colour swap) are enumerated over small domains and induced by fit.
"""
import sys
from collections import Counter
from itertools import permutations
from math import gcd
sys.path.insert(0, '/home/claude/work/widen')
from gdsl import H, W, bg_of, colours, objects, bbox, crop


def kron(mask, on_fn, off_tile, th, tw):
    """Assemble an (H(mask)*th) x (W(mask)*tw) grid; on_fn(c) returns a th x tw tile or None (use off_tile)."""
    out = []
    for y in range(H(mask)):
        blks = []
        for x in range(W(mask)):
            t = on_fn(mask[y][x])
            t = off_tile if t is None else t
            if t is None or H(t) != th or W(t) != tw: return None
            blks.append(t)
        for r in range(th): out.append(sum((b[r] for b in blks), []))
    return out


def solid(h, w, c): return [[c] * w for _ in range(h)]


def ranked(g, which):
    cnt = Counter(v for r in g for v in r).most_common()
    if which == "most":
        return cnt[0][0] if len(cnt) == 1 or cnt[0][1] > cnt[1][1] else None
    return cnt[-1][0] if len(cnt) == 1 or cnt[-1][1] < cnt[-2][1] else None


def _fits0(train, fn):
    try: return fn(train[0]["input"]) == train[0]["output"]
    except Exception: return False


# ---------------------------------------------------------------- self-similar (mask = tile = input)
def fam_kron_self(train):
    if not all((H(p["output"]), W(p["output"])) == (H(p["input"]) ** 2, W(p["input"]) ** 2) for p in train): return
    common = set.intersection(*(colours(p["input"]) for p in train))
    preds = [("nonbg", None), ("nonzero", None), ("most", None), ("least", None), ("all", None)] + [("eq", c) for c in sorted(common)]
    for (pk, pc) in preds:
        for inv in ((False,) if pk == "all" else (False, True)):
            for tile in ("input", "selfmask"):
                for z in ("zero", "bg"):
                    if tile == "input" and pk in ("nonbg", "nonzero") and not (inv and pk == "nonbg"):
                        continue  # plain fractal already in gdsl.fam_fractal
                    def fn(g, pk=pk, pc=pc, inv=inv, tile=tile, z=z):
                        bg = bg_of(g); zc = 0 if z == "zero" else bg
                        tgt = ranked(g, pk) if pk in ("most", "least") else pc
                        if pk in ("most", "least") and tgt is None: return None
                        def pred(v):
                            r = {"nonbg": v != bg, "nonzero": v != 0, "all": True}.get(pk, v == tgt)
                            return r != inv
                        h, w = H(g), W(g)
                        def on(v):
                            if not pred(v): return None
                            if tile == "input": return g
                            return [[v if q == v else zc for q in row] for row in g]
                        return kron(g, on, solid(h, w, zc), h, w)
                    name = f"kron:self[pred={pk}{'' if pc is None else pc}{',inv' if inv else ''},tile={tile},off={z}]"
                    if _fits0(train, fn): yield (name, 4, fn)


# ---------------------------------------------------------------- panels (mask panel x tile panel, recolour by solid panels)
def _split_any(g):
    """Split by full-length single-colour separator rows/cols (panels may differ in size)."""
    h, w = H(g), W(g)
    for sc in sorted(colours(g) - {bg_of(g)}):
        rows = [r for r in range(h) if all(v == sc for v in g[r])]
        cols = [c for c in range(w) if all(g[r][c] == sc for r in range(h))]
        if not rows and not cols or len(rows) == h or len(cols) == w: continue
        rb = [-1] + rows + [h]; cb = [-1] + cols + [w]
        ps = [crop(g, (rb[a] + 1, cb[b] + 1, rb[a + 1] - 1, cb[b + 1] - 1))
              for a in range(len(rb) - 1) for b in range(len(cb) - 1) if rb[a + 1] - rb[a] > 1 and cb[b + 1] - cb[b] > 1]
        if len(ps) >= 3: return ps
    return None


def _panel_roles(g):
    panels = _split_any(g)
    if not panels: return None
    bg = Counter(v for p in panels for r in p for v in r).most_common(1)[0][0]
    shapes, cols, sc = [], [], []
    for p in panels:
        cells = [(y, x) for y in range(H(p)) for x in range(W(p)) if p[y][x] != bg]
        if not cells or len({p[y][x] for y, x in cells}) != 1: return None
        r0, c0, r1, c1 = bbox(cells)
        if len(cells) == (r1 - r0 + 1) * (c1 - c0 + 1) and len(cells) > 1: cols.append(p[cells[0][0]][cells[0][1]])
        else: shapes.append(p); sc.append(cells)
    if len(shapes) < 2: return None
    b = bbox([c for cs in sc for c in cs])
    if any(b[2] >= H(p) or b[3] >= W(p) for p in shapes): return None
    return [crop(p, b) for p in shapes], cols, bg


def fam_kron_panels(train):
    i, o = train[0]["input"], train[0]["output"]
    r = _panel_roles(i)
    if not r: return
    shapes, cols, _ = r
    if len(shapes) < 2 or len(shapes) > 4 or len(cols) > 4: return
    colsel = list(permutations(range(len(cols)), 2)) if len(cols) >= 2 else [None]
    for m, t in permutations(range(len(shapes)), 2):
        for cs in colsel:
            def fn(g, m=m, t=t, cs=cs):
                r = _panel_roles(g)
                if not r: return None
                shapes, cols, bg = r
                if max(m, t) >= len(shapes) or (cs and max(cs) >= len(cols)): return None
                mk, tl = shapes[m], shapes[t]
                if cs: fg, ob = cols[cs[0]], cols[cs[1]]
                else: fg, ob = None, bg
                on_t = [[(v if fg is None else fg) if v != bg else ob for v in row] for row in tl]
                return kron(mk, lambda v: on_t if v != bg else None, solid(H(tl), W(tl), ob), H(tl), W(tl))
            yield (f"kron:panels[mask={m},tile={t}{'' if cs is None else f',fg=p{cs[0]},bg=p{cs[1]}'}]", 5, fn)


# ---------------------------------------------------------------- legend (swatch colour -> motif)
def _merge_nested(os):
    """Merge same-colour components whose bounding boxes overlap (a motif with a detached inner stroke is one motif)."""
    os = [list(o) for o in os]; changed = True
    while changed:
        changed = False
        for a in range(len(os)):
            for b in range(a + 1, len(os)):
                A, B = bbox(os[a]), bbox(os[b])
                if A[0] <= B[2] and B[0] <= A[2] and A[1] <= B[3] and B[1] <= A[3]:
                    os[a] += os.pop(b); changed = True; break
            if changed: break
    return os


def _legend(g, order):
    bg = bg_of(g)
    obs = objects(g, bg, True, False)
    mono = [o for o in obs if len({g[y][x] for y, x in o}) == 1]
    multi = [o for o in obs if len({g[y][x] for y, x in o}) > 1]
    if len(multi) != 1: return None
    mask = crop(g, bbox(multi[0]))
    bycol = {}
    for o in mono: bycol.setdefault(g[o[0][0]][o[0][1]], []).append(o)
    bycol = {c: _merge_nested(os) for c, os in bycol.items()}
    mot = [c for c, os in bycol.items() if len(os) >= 2 and len({(bbox(o)[2] - bbox(o)[0], bbox(o)[3] - bbox(o)[1]) for o in os}) == 1]
    if len(mot) != 1: return None
    motifs = bycol.pop(mot[0])
    sw = [o for os in bycol.values() for o in os]
    if len(sw) != len(motifs) or len({g[o[0][0]][o[0][1]] for o in sw}) != len(sw): return None
    if any(len(o) != (bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1) for o in sw): return None
    key = (lambda o: (bbox(o)[0], bbox(o)[1])) if order == "row" else (lambda o: (bbox(o)[1], bbox(o)[0]))
    sw.sort(key=key); motifs.sort(key=key)
    return mask, {g[s[0][0]][s[0][1]]: crop(g, bbox(m)) for s, m in zip(sw, motifs)}, mot[0], bg


def fam_kron_legend(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) <= H(i) and W(o) <= W(i) and (H(o), W(o)) != (H(i), W(i)) and H(o) * W(o) < 4: return
    if not _legend(i, "row"): return
    for order in ("row", "col"):
        def fn(g, order=order):
            L = _legend(g, order)
            if not L: return None
            mask, lut, mc, bg = L
            t0 = next(iter(lut.values())); th, tw = H(t0), W(t0)
            def on(v):
                if v not in lut: return None
                return [[v if q == mc else q for q in row] for row in lut[v]]
            return kron(mask, on, solid(th, tw, bg), th, tw)
        yield (f"kron:legend[order={order}]", 5, fn)


# ---------------------------------------------------------------- in place (dot lattice x shape mask, anchored at shape)
def _inplace(g, recol):
    bg = bg_of(g)
    obs = objects(g, bg, True, True)
    if len(obs) < 3: return None
    big = max(obs, key=len)
    if sum(1 for o in obs if len(o) == len(big)) != 1: return None
    dots = [o for o in obs if o is not big]
    if any(len(o) != 1 for o in dots): return None
    sc = g[big[0][0]][big[0][1]]
    pts = [(o[0][0], o[0][1], g[o[0][0]][o[0][1]]) for o in dots]
    r0 = min(p[0] for p in pts); c0 = min(p[1] for p in pts)
    py = px = 0
    for y, x, _ in pts: py = gcd(py, y - r0); px = gcd(px, x - c0)
    py = py or 1; px = px or 1
    anchor = [p for p in pts if p[2] == sc]
    if len(anchor) != 1: return None
    others = {p[2] for p in pts} - {sc}
    if recol == "swap" and len(others) != 1: return None
    oc = next(iter(others)) if others else sc
    R0, C0, R1, C1 = bbox(big); sh, sw = R1 - R0 + 1, C1 - C0 + 1
    ay, ax = (anchor[0][0] - r0) // py, (anchor[0][1] - c0) // px
    out = [row[:] for row in g]
    for y, x in big: out[y][x] = bg
    for y, x, _ in pts: out[y][x] = bg
    rel = [(y - R0, x - C0) for y, x in big]
    for y, x, c in pts:
        i, j = (y - r0) // py - ay, (x - c0) // px - ax
        col = c if recol == "dot" else (oc if c == sc else sc)
        for dy, dx in rel:
            yy, xx = R0 + i * sh + dy, C0 + j * sw + dx
            if 0 <= yy < H(g) and 0 <= xx < W(g): out[yy][xx] = col
    return out


def fam_kron_inplace(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    for recol in ("dot", "swap"):
        fn = lambda g, recol=recol: _inplace(g, recol)
        if _fits0(train, fn): yield (f"kron:inplace[colour={recol}]", 5, fn)


FAMILIES = (fam_kron_self, fam_kron_panels, fam_kron_legend, fam_kron_inplace)
