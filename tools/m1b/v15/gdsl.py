"""G-DSL: whole-grid primitives with parameters inferred from training pairs only.

Every program is verified exactly on all training pairs before it is applied to a test input.
Programs are enumerated in description-length order (cheapest first). No task identifiers,
no task-specific constants: every parameter (colours, factors, selectors, masks) is induced
from the task's own training pairs.
"""
from __future__ import annotations
from collections import Counter
from itertools import product

# ------------------------------------------------------------------ grid helpers
def H(g): return len(g)
def W(g): return len(g[0])
def T(g): return [list(r) for r in zip(*g)]
def fh(g): return [r[::-1] for r in g]
def fv(g): return g[::-1]
def r90(g): return fh(T(g))
def r180(g): return fv(fh(g))
def r270(g): return fv(T(g))
def at(g): return r180(T(g))
D8 = {"id": lambda g: [list(r) for r in g], "r90": r90, "r180": r180, "r270": r270,
      "fh": fh, "fv": fv, "T": T, "aT": at}
def bg_of(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]
def colours(g): return {v for r in g for v in r}
def eq(a, b): return a == b

def objects(g, bg, diag=False, by_colour=True):
    h, w = H(g), W(g); seen = [[False] * w for _ in range(h)]; out = []
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if diag else [])
    for r in range(h):
        for c in range(w):
            if seen[r][c] or g[r][c] == bg: continue
            col = g[r][c]; st = [(r, c)]; seen[r][c] = True; cells = []
            while st:
                y, x = st.pop(); cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] and g[yy][xx] != bg and (not by_colour or g[yy][xx] == col):
                        seen[yy][xx] = True; st.append((yy, xx))
            out.append(cells)
    return out

def bbox(cells):
    ys = [y for y, _ in cells]; xs = [x for _, x in cells]
    return min(ys), min(xs), max(ys), max(xs)

def crop(g, b):
    r0, c0, r1, c1 = b
    return [row[c0:c1 + 1] for row in g[r0:r1 + 1]]

# ------------------------------------------------------------------ colour map (post-step)
def fit_cmap(preds, outs):
    """Global colour substitution consistent across all pairs; None if impossible."""
    m = {}
    for p, o in zip(preds, outs):
        if p is None or H(p) != H(o) or W(p) != W(o): return None
        for rp, ro in zip(p, o):
            for a, b in zip(rp, ro):
                if m.setdefault(a, b) != b: return None
    return m

def apply_cmap(g, m):
    """Apply an induced colour substitution; refuse colours never seen in training (no extrapolation)."""
    if g is None: return None
    if any(v not in m for r in g for v in r): return None
    return [[m[v] for v in r] for r in g]

# ------------------------------------------------------------------ primitive families
# Each family yields (name, cost, fn) where fn(grid) -> grid or None. Families may inspect
# training pairs to induce parameters (never test outputs).

def fam_geometric(train):
    for k, f in D8.items():
        if k != "id": yield ("dihedral:" + k, 1, f)

def fam_tile(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) % H(i) or W(o) % W(i): return
    n, m = H(o) // H(i), W(o) // W(i)
    if n * m == 1 or n * m > 16: return
    # per-tile dihedral transform inferred from the first pair, verified later on all pairs
    pat = []
    for a in range(n):
        row = []
        for b in range(m):
            blk = [r[b * W(i):(b + 1) * W(i)] for r in o[a * H(i):(a + 1) * H(i)]]
            ks = [k for k, f in D8.items() if (H(i) == W(i) or k in ("id", "r180", "fh", "fv")) and f(i) == blk]
            if not ks: return
            row.append(ks[0])
        pat.append(row)
    def fn(g, pat=pat, n=n, m=m):
        out = []
        for a in range(n):
            blks = [D8[pat[a][b]](g) for b in range(m)]
            if any(H(x) != H(blks[0]) for x in blks): return None
            for rr in range(H(blks[0])):
                out.append(sum((x[rr] for x in blks), []))
        return out
    yield (f"tile:{n}x{m}", 2, fn)

def fam_scale(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) % H(i) == 0 and W(o) % W(i) == 0 and (H(o) > H(i) or W(o) > W(i)):
        kh, kw = H(o) // H(i), W(o) // W(i)
        yield (f"upscale:{kh}x{kw}", 2, lambda g, kh=kh, kw=kw: [[v for v in r for _ in range(kw)] for r in g for _ in range(kh)])
    if H(i) % H(o) == 0 and W(i) % W(o) == 0 and (H(i) > H(o) or W(i) > W(o)):
        kh, kw = H(i) // H(o), W(i) // W(o)
        def down(g, kh=kh, kw=kw, mode="mode"):
            if H(g) % kh or W(g) % kw: return None
            bg = bg_of(g); out = []
            for a in range(0, H(g), kh):
                row = []
                for b in range(0, W(g), kw):
                    blk = [v for r in g[a:a + kh] for v in r[b:b + kw]]
                    nz = [v for v in blk if v != bg]
                    row.append(Counter(nz).most_common(1)[0][0] if (mode == "any" and nz) else (Counter(blk).most_common(1)[0][0] if mode == "mode" else bg))
                out.append(row)
            return out
        yield (f"downscale-mode:{kh}x{kw}", 2, down)
        yield (f"downscale-any:{kh}x{kw}", 3, lambda g, d=down: d(g, mode="any"))

def fam_fractal(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i) * H(i), W(i) * W(i)): return
    for inv, bgm in product((False, True), ("mode", "zero")):
        def fn(g, inv=inv, bgm=bgm):
            bg = bg_of(g) if bgm == "mode" else 0
            h, w = H(g), W(g); out = [[bg] * (w * w) for _ in range(h * h)]
            for a in range(h):
                for b in range(w):
                    if (g[a][b] != bg) != inv:
                        for y in range(h):
                            for x in range(w):
                                out[a * h + y][b * w + x] = g[y][x]
            return out
        yield ("fractal" + (":inverse" if inv else "") + ("" if bgm == "mode" else ":bg0"), 3, fn)

SELECTORS = ("largest", "smallest", "most_colours", "unique_colour", "unique_shape", "topmost", "bottommost",
             "leftmost", "rightmost", "densest_bbox", "sparsest_bbox", "most_frequent_shape")

def select(objs, g, how):
    if not objs: return None
    key = {
        "largest": lambda o: len(o), "smallest": lambda o: -len(o),
        "topmost": lambda o: -bbox(o)[0], "bottommost": lambda o: bbox(o)[2],
        "leftmost": lambda o: -bbox(o)[1], "rightmost": lambda o: bbox(o)[3],
        "most_colours": lambda o: len({g[y][x] for y, x in o}),
        "densest_bbox": lambda o: len(o) / ((bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1)),
        "sparsest_bbox": lambda o: -len(o) / ((bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1)),
    }
    if how in key:
        vals = [key[how](o) for o in objs]; best = max(vals)
        hits = [o for o, v in zip(objs, vals) if v == best]
        return hits[0] if len(hits) == 1 else None
    def shape(o):
        r0, c0, _, _ = bbox(o); return tuple(sorted((y - r0, x - c0) for y, x in o))
    if how == "unique_colour":
        cs = Counter(g[o[0][0]][o[0][1]] for o in objs)
        hits = [o for o in objs if cs[g[o[0][0]][o[0][1]]] == 1]
        return hits[0] if len(hits) == 1 else None
    if how in ("unique_shape", "most_frequent_shape"):
        cs = Counter(shape(o) for o in objs)
        if how == "unique_shape":
            hits = [o for o in objs if cs[shape(o)] == 1]
        else:
            top = cs.most_common(1)[0]
            if len(cs) > 1 and cs.most_common(2)[1][1] == top[1]: return None
            hits = [o for o in objs if shape(o) == top[0]][:1]
        return hits[0] if len(hits) == 1 else None
    return None

def fam_crop(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) > H(i) or W(o) > W(i) or (H(o), W(o)) == (H(i), W(i)): return
    def all_fg(g):
        bg = bg_of(g); cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] != bg]
        return crop(g, bbox(cells)) if cells else None
    yield ("crop:all-foreground", 2, all_fg)
    for diag, byc, how in product((False, True), (True, False), SELECTORS):
        def fn(g, diag=diag, byc=byc, how=how):
            bg = bg_of(g); ob = select(objects(g, bg, diag, byc), g, how)
            return crop(g, bbox(ob)) if ob else None
        yield (f"crop:object[{'8' if diag else '4'}{'' if byc else ',multi'}]:{how}", 3, fn)

def split_panels(g):
    """Split by full-length single-colour separator rows/cols; returns (panels, sep_colour) or None."""
    h, w = H(g), W(g)
    for sc in colours(g):
        rows = [r for r in range(h) if all(v == sc for v in g[r])]
        cols = [c for c in range(w) if all(g[r][c] == sc for r in range(h))]
        if not rows and not cols: continue
        if len(rows) == h or len(cols) == w: continue
        rb = [-1] + rows + [h]; cb = [-1] + cols + [w]
        panels = []
        for a in range(len(rb) - 1):
            for b in range(len(cb) - 1):
                if rb[a + 1] - rb[a] > 1 and cb[b + 1] - cb[b] > 1:
                    panels.append(crop(g, (rb[a] + 1, cb[b] + 1, rb[a + 1] - 1, cb[b + 1] - 1)))
        if len(panels) >= 2 and all((H(p), W(p)) == (H(panels[0]), W(panels[0])) for p in panels):
            return panels, sc
    # no separator: equal halves
    if h % 2 == 0 and h >= 2: pass
    return None

def halves(g):
    h, w = H(g), W(g); out = []
    if w % 2 == 0: out.append([[r[:w // 2] for r in g], [r[w // 2:] for r in g]])
    if h % 2 == 0: out.append([g[:h // 2], g[h // 2:]])
    return out

BOOLS = {"and": lambda a, b: a and b, "or": lambda a, b: a or b, "xor": lambda a, b: a != b,
         "nor": lambda a, b: not a and not b, "a_not_b": lambda a, b: a and not b, "b_not_a": lambda a, b: b and not a}

def fam_panels(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) == (H(i), W(i)): return
    def getp(g, mode):
        if mode == "sep":
            sp = split_panels(g); return sp[0] if sp else None
        hs = halves(g); k = int(mode[-1])
        return hs[k] if len(hs) > k else None
    oc = [c for c in colours(o)]
    for mode in ("sep", "half0", "half1"):
        ps = getp(i, mode)
        if not ps or (H(ps[0]), W(ps[0])) != (H(o), W(o)): continue
        # boolean combination of two panels -> constant colour on true, bg on false
        if len(ps) == 2:
            for bn, f in BOOLS.items():
                for on_c in oc:
                    def fn(g, mode=mode, f=f, on_c=on_c):
                        p = getp(g, mode)
                        if not p or len(p) != 2: return None
                        a, b = p; bg = bg_of(g)
                        return [[on_c if f(a[y][x] != bg, b[y][x] != bg) else bg for x in range(W(a))] for y in range(H(a))]
                    yield (f"panels[{mode}]:{bn}->colour", 3, fn)
        # overlay: later panels painted over earlier (non-zero wins), both orders
        for order in ("fwd", "rev"):
            def ov(g, mode=mode, order=order):
                p = getp(g, mode)
                if not p: return None
                p = p if order == "fwd" else p[::-1]
                bgg = bg_of(g); out = [r[:] for r in p[0]]
                for q in p[1:]:
                    for y in range(H(q)):
                        for x in range(W(q)):
                            if q[y][x] != bgg: out[y][x] = q[y][x]
                return out
            yield (f"panels[{mode}]:overlay-{order}", 3, ov)
        for how in ("most_fg", "least_fg", "unique", "most_colours", "least_colours"):
            def sel(g, mode=mode, how=how):
                p = getp(g, mode)
                if not p: return None
                if how == "unique":
                    cs = Counter(str(q) for q in p); hits = [q for q in p if cs[str(q)] == 1]
                    return hits[0] if len(hits) == 1 else None
                bgg = bg_of(g)
                key = {"most_fg": lambda q: sum(v != bgg for r in q for v in r), "least_fg": lambda q: -sum(v != bgg for r in q for v in r),
                       "most_colours": lambda q: len(colours(q)), "least_colours": lambda q: -len(colours(q))}[how]
                vals = [key(q) for q in p]; hits = [q for q, v in zip(p, vals) if v == max(vals)]
                return hits[0] if len(hits) == 1 else None
            yield (f"panels[{mode}]:select-{how}", 3, sel)

SYMS = {"fh": fh, "fv": fv, "r180": r180, "T": T, "aT": at, "r90": r90}

def fam_symmetry(train):
    """Occluder colour (present in input, absent in output) is replaced by symmetric counterparts.
    Output either the repaired grid (same size) or the repaired patch under the occluder."""
    i, o = train[0]["input"], train[0]["output"]
    occ = [c for c in colours(i) if all(c in colours(p["input"]) and c not in colours(p["output"]) for p in train)]
    same = (H(o), W(o)) == (H(i), W(i))
    for c in occ:
        for combo in (("fh",), ("fv",), ("fh", "fv"), ("fh", "fv", "r180"), ("T",), ("fh", "fv", "T", "aT", "r90", "r180")):
            def rep(g, c=c, combo=combo):
                out = [r[:] for r in g]
                for _ in range(3):
                    changed = False
                    for k in combo:
                        if k in ("T", "aT", "r90") and H(g) != W(g): return None
                        m = SYMS[k](out)
                        for y in range(H(g)):
                            for x in range(W(g)):
                                if out[y][x] == c and m[y][x] != c:
                                    out[y][x] = m[y][x]; changed = True
                    if not changed: break
                return None if any(v == c for r in out for v in r) else out
            if same:
                yield (f"symmetry-repair:{'+'.join(combo)}", 3, rep)
            else:
                def patch(g, c=c, rep=rep):
                    cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == c]
                    if not cells: return None
                    r = rep(g)
                    return crop(r, bbox(cells)) if r else None
                yield (f"symmetry-patch:{'+'.join(combo)}", 4, patch)

def fam_gravity(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    # (to frame, from frame): transform so that the motion direction becomes 'down'
    frames = {"down": (lambda g: g, lambda g: g), "up": (fv, fv), "right": (T, T), "left": (lambda g: T(fh(g)), lambda g: fh(T(g)))}
    for d, (to, back) in frames.items():
        def fn(g, to=to, back=back):
            bg = bg_of(g); out = [r[:] for r in to(g)]
            for x in range(W(out)):
                col = [out[y][x] for y in range(H(out)) if out[y][x] != bg]
                for y in range(H(out)): out[y][x] = bg
                for k, v in enumerate(reversed(col)): out[H(out) - 1 - k][x] = v
            return back(out)
        yield (f"gravity-cells:{d}", 2, fn)

def fam_colour_count(train):
    """Output is a 1-row/col strip or square filled from colour counts (sorted by frequency)."""
    i, o = train[0]["input"], train[0]["output"]
    if H(o) * W(o) > 30: return
    def strip(g, orient):
        bg = bg_of(g); cs = Counter(v for r in g for v in r if v != bg)
        seq = [c for c, _ in cs.most_common()]
        if not seq: return None
        return [seq] if orient == "row" else [[c] for c in seq]
    yield ("colours-by-frequency:row", 3, lambda g: strip(g, "row"))
    yield ("colours-by-frequency:col", 3, lambda g: strip(g, "col"))

FAMILIES = (fam_geometric, fam_tile, fam_scale, fam_fractal, fam_crop, fam_panels, fam_symmetry, fam_gravity, fam_colour_count)


# ------------------------------------------------------------------ cycle 2 families
def fam_crop_colour(train):
    """Crop to the bbox of one colour's cells, or to the interior of that bbox (frame contents).
    The colour is induced: it must reproduce every training output."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) == (H(i), W(i)) or H(o) > H(i) or W(o) > W(i): return
    for c in sorted(colours(i)):
        for inner in (False, True):
            def fn(g, c=c, inner=inner):
                cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == c]
                if not cells: return None
                r0, c0, r1, c1 = bbox(cells)
                if inner: r0, c0, r1, c1 = r0 + 1, c0 + 1, r1 - 1, c1 - 1
                if r1 < r0 or c1 < c0: return None
                return crop(g, (r0, c0, r1, c1))
            yield (f"crop:colour-bbox{'-interior' if inner else ''}[c{c}]", 3, fn)

def fam_fill_enclosed(train):
    """Background regions not connected to the border are filled with an induced colour."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    new = Counter(o[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x])
    for c, _ in new.most_common(2):
        for diag in (False, True):
            def fn(g, c=c, diag=diag):
                bg = bg_of(g); h, w = H(g), W(g); out = [r[:] for r in g]
                seen = [[False] * w for _ in range(h)]
                st = [(y, x) for y in range(h) for x in range(w) if (y in (0, h - 1) or x in (0, w - 1)) and g[y][x] == bg]
                for y, x in st: seen[y][x] = True
                nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if diag else [])
                while st:
                    y, x = st.pop()
                    for dy, dx in nb:
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and not seen[yy][xx] and g[yy][xx] == bg:
                            seen[yy][xx] = True; st.append((yy, xx))
                for y in range(h):
                    for x in range(w):
                        if g[y][x] == bg and not seen[y][x]: out[y][x] = c
                return out
            yield (f"fill-enclosed[c{c}{',8' if diag else ''}]", 2, fn)

def fam_symmetrize(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    for combo in (("fh",), ("fv",), ("fh", "fv", "r180"), ("T",), ("fh", "fv", "T", "aT", "r90", "r180", "r270")):
        def fn(g, combo=combo):
            bg = bg_of(g); out = [r[:] for r in g]
            for k in combo:
                if k in ("T", "aT", "r90", "r270") and H(g) != W(g): return None
                m = (SYMS.get(k) or D8[k])(g)
                for y in range(H(g)):
                    for x in range(W(g)):
                        if out[y][x] == bg and m[y][x] != bg: out[y][x] = m[y][x]
            return out
        yield (f"symmetrize:{'+'.join(combo)}", 2, fn)

def fam_object_filter(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    for diag, byc in product((False, True), (True, False)):
        for k in (1, 2, 3):
            def noise(g, k=k, diag=diag, byc=byc):
                bg = bg_of(g); out = [r[:] for r in g]
                for ob in objects(g, bg, diag, byc):
                    if len(ob) <= k:
                        for y, x in ob: out[y][x] = bg
                return out
            yield (f"remove-objects-size<={k}[{'8' if diag else '4'}{'' if byc else ',multi'}]", 2, noise)
        for how in ("largest", "smallest", "unique_colour", "unique_shape", "most_colours"):
            def keep(g, how=how, diag=diag, byc=byc):
                bg = bg_of(g); obs = objects(g, bg, diag, byc); ob = select(obs, g, how)
                if not ob: return None
                out = [[bg] * W(g) for _ in range(H(g))]
                for y, x in ob: out[y][x] = g[y][x]
                return out
            yield (f"keep-object[{'8' if diag else '4'}{'' if byc else ',multi'}]:{how}", 3, keep)

RAYS = {"orth": [(-1, 0), (1, 0), (0, -1), (0, 1)], "diag": [(-1, -1), (-1, 1), (1, -1), (1, 1)],
        "up": [(-1, 0)], "down": [(1, 0)], "left": [(0, -1)], "right": [(0, 1)], "vert": [(-1, 0), (1, 0)], "horiz": [(0, -1), (0, 1)]}

def fam_rays(train):
    """Cells of an induced colour emit rays (own colour) in induced directions, stopping at non-background
    (or passing over it)."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    src = sorted({i[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != bg_of(i)})
    for c in src:
        for dn, dirs in RAYS.items():
            for stop in (True, False):
                def fn(g, c=c, dirs=dirs, stop=stop):
                    bg = bg_of(g); out = [r[:] for r in g]
                    for y in range(H(g)):
                        for x in range(W(g)):
                            if g[y][x] != c: continue
                            for dy, dx in dirs:
                                yy, xx = y + dy, x + dx
                                while 0 <= yy < H(g) and 0 <= xx < W(g):
                                    if g[yy][xx] != bg:
                                        if stop: break
                                    else: out[yy][xx] = c
                                    yy += dy; xx += dx
                    return out
                yield (f"rays[c{c}]:{dn}{':stop' if stop else ':through'}", 3, fn)

def fam_connect(train):
    """Same-colour cells sharing a row/column are joined by a line of their colour (or an induced colour)."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    new = [None] + [c for c, _ in Counter(o[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x]).most_common(1)]
    for axes in ("both", "row", "col"):
        for lc in new:
            def fn(g, axes=axes, lc=lc):
                bg = bg_of(g); out = [r[:] for r in g]
                pts = {}
                for y in range(H(g)):
                    for x in range(W(g)):
                        if g[y][x] != bg: pts.setdefault(g[y][x], []).append((y, x))
                for c, ps in pts.items():
                    for (y1, x1), (y2, x2) in product(ps, ps):
                        if (y1, x1) >= (y2, x2): continue
                        if y1 == y2 and axes in ("both", "row"):
                            for x in range(min(x1, x2) + 1, max(x1, x2)):
                                if out[y1][x] == bg: out[y1][x] = lc if lc is not None else c
                        if x1 == x2 and axes in ("both", "col"):
                            for y in range(min(y1, y2) + 1, max(y1, y2)):
                                if out[y][x1] == bg: out[y][x1] = lc if lc is not None else c
                return out
            yield (f"connect-same-colour:{axes}{'' if lc is None else f'[c{lc}]'}", 3, fn)
    for lc in new:
        def dfn(g, lc=lc):
            bg = bg_of(g); out = [r[:] for r in g]; pts = {}
            for y in range(H(g)):
                for x in range(W(g)):
                    if g[y][x] != bg: pts.setdefault(g[y][x], []).append((y, x))
            for c, ps in pts.items():
                for (y1, x1), (y2, x2) in product(ps, ps):
                    if (y1, x1) >= (y2, x2) or abs(y1 - y2) != abs(x1 - x2): continue
                    sy = 1 if y2 > y1 else -1; sx = 1 if x2 > x1 else -1
                    for k in range(1, abs(y2 - y1)):
                        if out[y1 + k * sy][x1 + k * sx] == bg: out[y1 + k * sy][x1 + k * sx] = lc if lc is not None else c
            return out
        yield (f"connect-same-colour:diagonal{'' if lc is None else f'[c{lc}]'}", 3, dfn)

PROPS = {"size": lambda o, g: len(o), "height": lambda o, g: bbox(o)[2] - bbox(o)[0] + 1, "width": lambda o, g: bbox(o)[3] - bbox(o)[1] + 1,
         "size_rank": None, "is_rect": lambda o, g: len(o) == (bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1),
         "shape": lambda o, g: tuple(sorted((y - bbox(o)[0], x - bbox(o)[1]) for y, x in o)),
         "touches_border": lambda o, g: any(y in (0, H(g) - 1) or x in (0, W(g) - 1) for y, x in o),
         "n_holes": None}

def fam_recolour_by_property(train):
    """Each object is recoloured by a mapping property-value -> colour induced from training pairs.
    Refuses property values never seen in training."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    for diag, byc in product((False, True), (True, False)):
        for pn in ("size", "height", "width", "size_rank", "is_rect", "shape", "touches_border", "n_holes", "adj_colours",
                   "colour_set", "shape_count", "extreme_size", "area_rank"):
            def pval(obs, g, pn=pn):
                if pn == "size_rank":
                    sizes = sorted({len(x) for x in obs}, reverse=True)
                    return [sizes.index(len(x)) for x in obs]
                if pn == "area_rank":
                    ar = lambda o: (bbox(o)[2] - bbox(o)[0] + 1) * (bbox(o)[3] - bbox(o)[1] + 1)
                    vals = sorted({ar(x) for x in obs}, reverse=True)
                    return [vals.index(ar(x)) for x in obs]
                if pn == "extreme_size":
                    mx = max(len(x) for x in obs); mn = min(len(x) for x in obs)
                    return ["max" if len(x) == mx else "min" if len(x) == mn else "mid" for x in obs]
                if pn == "shape_count":
                    sh = [PROPS["shape"](x, g) for x in obs]; cs = Counter(sh)
                    return [min(cs[s], 3) for s in sh]
                if pn == "colour_set":
                    return [frozenset(g[y][x] for y, x in o) for o in obs]
                if pn == "adj_colours":
                    bg = bg_of(g); out = []
                    for o in obs:
                        cs = set(o); col = set()
                        for y, x in o:
                            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                                yy, xx = y + dy, x + dx
                                if 0 <= yy < H(g) and 0 <= xx < W(g) and (yy, xx) not in cs and g[yy][xx] != bg: col.add(g[yy][xx])
                        out.append(frozenset(col))
                    return out
                if pn == "n_holes":
                    bg = bg_of(g); out = []
                    for o in obs:
                        r0, c0, r1, c1 = bbox(o); cs = set(o)
                        sub = [[1 if (y, x) in cs else 0 for x in range(c0 - 1, c1 + 2)] for y in range(r0 - 1, r1 + 2)]
                        holes = objects(sub, 1, False, True)   # regions of 0 (non-object) cells
                        out.append(sum(1 for hcells in holes if not any(y in (0, len(sub) - 1) or x in (0, len(sub[0]) - 1) for y, x in hcells)))
                    return out
                return [PROPS[pn](x, g) for x in obs]
            m = {}; ok = True
            for p in train:
                gi, go = p["input"], p["output"]
                if (H(gi), W(gi)) != (H(go), W(go)): ok = False; break
                bg = bg_of(gi); obs = objects(gi, bg, diag, byc)
                for ob, v in zip(obs, pval(obs, gi)):
                    cs = {go[y][x] for y, x in ob}
                    if len(cs) != 1 or m.setdefault(v, cs.pop()) != go[ob[0][0]][ob[0][1]]: ok = False; break
                if not ok: break
            if not ok or not m: continue
            def fn(g, m=m, diag=diag, byc=byc, pval=pval):
                bg = bg_of(g); out = [r[:] for r in g]; obs = objects(g, bg, diag, byc)
                for ob, v in zip(obs, pval(obs, g)):
                    if v not in m: return None
                    for y, x in ob: out[y][x] = m[v]
                return out
            yield (f"recolour-by-{pn}[{'8' if diag else '4'}{'' if byc else ',multi'}]", 3, fn)

def fam_panels_multi(train):
    i, o = train[0]["input"], train[0]["output"]
    sp = split_panels(i)
    if not sp or len(sp[0]) < 3 or (H(sp[0][0]), W(sp[0][0])) != (H(o), W(o)): return
    for rule in ("all", "any", "one", "none"):
        for on_c in sorted(colours(o)):
            def fn(g, rule=rule, on_c=on_c):
                s = split_panels(g)
                if not s: return None
                ps = s[0]; bg = bg_of(g)
                if any((H(p), W(p)) != (H(ps[0]), W(ps[0])) for p in ps): return None
                def f(y, x):
                    n = sum(p[y][x] != bg for p in ps)
                    return {"all": n == len(ps), "any": n > 0, "one": n == 1, "none": n == 0}[rule]
                return [[on_c if f(y, x) else bg for x in range(W(ps[0]))] for y in range(H(ps[0]))]
            yield (f"panels[sep]:{rule}-of-{len(sp[0])}->colour", 3, fn)

RESHAPERS = ("tile", "crop", "panels", "upscale", "downscale", "fractal", "symmetry-patch", "symmetry-offset-patch", "kronecker")

def compose_dihedral(base):
    """Any output-reshaping program followed by a dihedral transform (one extra step)."""
    for name, cost, fn in base:
        if not name.startswith(RESHAPERS): continue
        for k, f in D8.items():
            if k == "id": continue
            yield (name + ">" + k, cost + 1, lambda g, fn=fn, f=f: (lambda r: f(r) if r else None)(fn(g)))

def fam_codex(train):
    try:
        import codex_ops
    except Exception:
        return
    yield from codex_ops.programs(train)

FAMILIES = FAMILIES + (fam_crop_colour, fam_fill_enclosed, fam_symmetrize, fam_object_filter, fam_rays, fam_connect, fam_recolour_by_property, fam_panels_multi, fam_codex)

# ------------------------------------------------------------------ cycle 9 families (motivated by training + eval half A)
def _sym_transforms(h, w):
    """Candidate symmetries with arbitrary axis/centre positions: (name, f(y,x)->(y,x))."""
    out = []
    for s in range(w // 2, w + w // 2):           # horizontal mirror x -> s - x  (axis at s/2)
        out.append((f"mirror-x@{s}", lambda y, x, s=s: (y, s - x)))
    for s in range(h // 2, h + h // 2):
        out.append((f"mirror-y@{s}", lambda y, x, s=s: (s - y, x)))
    for d in range(-3, 4):                        # transpose about an offset main diagonal
        out.append((f"transpose@{d}", lambda y, x, d=d: (x - d, y + d)))
    return out

def infer_symmetries(g, occ, min_agree=0.98, min_pairs=0.3):
    h, w = H(g), W(g); acc = []
    for name, f in _sym_transforms(h, w):
        agree = tot = 0
        for y in range(h):
            for x in range(w):
                if g[y][x] == occ: continue
                yy, xx = f(y, x)
                if 0 <= yy < h and 0 <= xx < w and g[yy][xx] != occ:
                    tot += 1; agree += g[y][x] == g[yy][xx]
        if tot >= min_pairs * h * w and agree >= min_agree * tot:
            acc.append((name, f))
    return acc

def offset_repair(g, occ):
    syms = infer_symmetries(g, occ)
    if not syms: return None
    out = [r[:] for r in g]; h, w = H(g), W(g)
    for _ in range(4):
        changed = False
        for y in range(h):
            for x in range(w):
                if out[y][x] != occ: continue
                for _, f in syms:
                    yy, xx = f(y, x)
                    if 0 <= yy < h and 0 <= xx < w and out[yy][xx] != occ:
                        out[y][x] = out[yy][xx]; changed = True; break
        if not changed: break
    return None if any(v == occ for r in out for v in r) else out

def fam_symmetry_offset(train):
    i, o = train[0]["input"], train[0]["output"]
    occ = [c for c in colours(i) if all(c in colours(p["input"]) and c not in colours(p["output"]) for p in train)]
    same = (H(o), W(o)) == (H(i), W(i))
    for c in occ:
        if same:
            yield (f"symmetry-offset-repair[c{c}]", 4, lambda g, c=c: offset_repair(g, c))
        else:
            def patch(g, c=c):
                cells = [(y, x) for y in range(H(g)) for x in range(W(g)) if g[y][x] == c]
                if not cells: return None
                r = offset_repair(g, c)
                return crop(r, bbox(cells)) if r else None
            yield (f"symmetry-offset-patch[c{c}]", 4, patch)

def fam_object_symmetrize(train):
    """Each object keeps only cells whose mirror partner (about the object's best axis) is present."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    for axis in ("x", "y"):
        for diag, byc in product((True, False), (True, False)):
            def fn(g, axis=axis, diag=diag, byc=byc):
                bg = bg_of(g); out = [r[:] for r in g]
                for ob in objects(g, bg, diag, byc):
                    cells = set(ob); r0, c0, r1, c1 = bbox(ob); best = None
                    lo, hi = (2 * c0, 2 * c1) if axis == "x" else (2 * r0, 2 * r1)
                    for s in range(lo, hi + 1):
                        keep = {(y, x) for y, x in cells if ((y, s - x) if axis == "x" else (s - y, x)) in cells and
                                g[y][x] == g[(y if axis == "x" else s - y)][(s - x if axis == "x" else x)]}
                        if best is None or len(keep) > len(best): best = keep
                    for y, x in cells - (best or set()): out[y][x] = bg
                return out
            yield (f"object-symmetrize:{axis}[{'8' if diag else '4'}{'' if byc else ',multi'}]", 3, fn)

def fam_kronecker(train):
    """Two objects: a single-colour mask and a pattern tile; output places the tile at each (non-)mask cell."""
    i, o = train[0]["input"], train[0]["output"]
    for inv in (False, True):
        for pick in ("mono_mask", "small_mask"):
            def fn(g, inv=inv, pick=pick):
                bg = bg_of(g); obs = objects(g, bg, True, False)
                if len(obs) != 2: return None
                a, b = [crop(g, bbox(x)) for x in obs]
                if pick == "mono_mask":
                    ma = len(colours(a) - {bg}) == 1; mb = len(colours(b) - {bg}) == 1
                    if ma == mb: return None
                    mask, tile = (a, b) if ma else (b, a)
                else:
                    mask, tile = (a, b) if H(a) * W(a) <= H(b) * W(b) else (b, a)
                out = []
                for y in range(H(mask)):
                    blk = [tile if ((mask[y][x] != bg) != inv) else [[bg] * W(tile) for _ in range(H(tile))] for x in range(W(mask))]
                    for rr in range(H(tile)): out.append(sum((q[rr] for q in blk), []))
                return out
            yield (f"kronecker:{pick}{':inverse' if inv else ''}", 3, fn)

def frame_interior(g):
    """Interior of the largest rectangle whose border cells all share one non-background colour."""
    bg = bg_of(g); best = None
    for ob in objects(g, bg, False, True):
        r0, c0, r1, c1 = bbox(ob)
        if r1 - r0 < 2 or c1 - c0 < 2: continue
        col = g[ob[0][0]][ob[0][1]]
        border = [(r0, x) for x in range(c0, c1 + 1)] + [(r1, x) for x in range(c0, c1 + 1)] + [(y, c0) for y in range(r0, r1 + 1)] + [(y, c1) for y in range(r0, r1 + 1)]
        if all(g[y][x] == col for y, x in border):
            area = (r1 - r0) * (c1 - c0)
            if best is None or area > best[0]: best = (area, (r0 + 1, c0 + 1, r1 - 1, c1 - 1))
    return crop(g, best[1]) if best else None

def fam_frame_crop(train):
    i, o = train[0]["input"], train[0]["output"]
    if H(o) >= H(i) and W(o) >= W(i): return
    yield ("crop:frame-interior", 2, frame_interior)

def fam_outline(train):
    """Background cells adjacent (4 or 8) to objects of an induced colour are painted an induced colour."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    new = Counter(o[y][x] for y in range(H(i)) for x in range(W(i)) if i[y][x] != o[y][x])
    srcs = sorted(colours(i) - {bg_of(i)})
    for c, _ in new.most_common(2):
        for s in srcs + [None]:
            for diag in (False, True):
                def fn(g, c=c, s=s, diag=diag):
                    bg = bg_of(g); out = [r[:] for r in g]
                    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)] + ([(-1, -1), (-1, 1), (1, -1), (1, 1)] if diag else [])
                    for y in range(H(g)):
                        for x in range(W(g)):
                            if g[y][x] != bg: continue
                            for dy, dx in nb:
                                yy, xx = y + dy, x + dx
                                if 0 <= yy < H(g) and 0 <= xx < W(g) and g[yy][xx] != bg and (s is None or g[yy][xx] == s):
                                    out[y][x] = c; break
                    return out
                yield (f"outline[c{c}{'' if s is None else f',src{s}'}{',8' if diag else ''}]", 3, fn)

def fam_period_extend(train):
    """Rows (or columns) containing a partial periodic sequence are continued periodically across the grid."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    for axis in ("row", "col"):
        for mode in ("from_first", "full"):
            def fn(g, axis=axis, mode=mode):
                gg = g if axis == "row" else T(g); bg = bg_of(g); out = [r[:] for r in gg]
                for y, row in enumerate(gg):
                    idx = [x for x, v in enumerate(row) if v != bg]
                    if len(idx) < 2: continue
                    a, b = idx[0], idx[-1]; seg = row[a:b + 1]
                    for p in range(1, len(seg) + 1):   # smallest period consistent with the observed segment
                        if all(seg[k] == seg[k % p] for k in range(len(seg))) and p < len(seg): break
                    else:
                        continue
                    start = a if mode == "from_first" else a % p
                    for x in range(start, len(row)):
                        out[y][x] = seg[(x - a) % p]
                return out if axis == "row" else T(out)
            yield (f"period-extend:{axis}:{mode}", 3, fn)
        def prog(g, axis=axis):
            """First two marks set the step; marks repeat up to the last mark, in the last mark's colour."""
            gg = g if axis == "row" else T(g); bg = bg_of(g); out = [r[:] for r in gg]
            for y, row in enumerate(gg):
                idx = [x for x, v in enumerate(row) if v != bg]
                if len(idx) < 3: continue
                a, b, last = idx[0], idx[1], idx[-1]; p = b - a
                if p <= 0 or (last - a) % p: continue
                for x in range(a, last + 1, p): out[y][x] = row[last]
            return out if axis == "row" else T(out)
        yield (f"progression:{axis}", 3, prog)
    def prog_row(row, bg):
        """Two same-colour marks set a step; continue to the odd-coloured last mark (in its colour), else to the edge."""
        idx = [x for x, v in enumerate(row) if v != bg]
        if len(idx) < 2 or row[idx[0]] != row[idx[1]]: return None
        a, p = idx[0], idx[1] - idx[0]
        rest = [x for x in idx[2:] if row[x] != row[a]]
        if any(row[x] == row[a] for x in idx[2:]): return None
        if len(rest) > 1: return None
        keep_other = False
        if rest and (rest[0] - a) % p == 0:
            end, col = rest[0], row[rest[0]]
        else:                                   # odd mark off the lattice (or none): continue to the edge
            end, col, keep_other = len(row) - 1, row[a], bool(rest)
        new = list(row)
        for x in range(a, end + 1, p):
            if keep_other and row[x] != bg and row[x] != row[a]: continue
            new[x] = col
        return new
    def prog_row_bi(row, bg):
        """The anchoring same-colour pair sits at a grid edge; progress away from that edge."""
        if row and row[0] != bg:
            return prog_row(row, bg)
        if row and row[-1] != bg:
            r = prog_row(row[::-1], bg)
            return r[::-1] if r is not None else None
        return None
    def prog_auto(g):
        bg = bg_of(g)
        cand = {}
        for ax, gg in (("r", g), ("c", T(g))):
            rows = [prog_row_bi(r, bg) for r in gg]
            cand[ax] = (sum(1 for r in rows if r is not None), gg, rows)
        (nr, _, _), (nc, _, _) = cand["r"], cand["c"]
        if nr == nc: return None
        ax = "r" if nr > nc else "c"; _, gg, rows = cand[ax]
        out = [r if r is not None else list(o) for r, o in zip(rows, gg)]
        return out if ax == "r" else T(out)
    yield ("progression:auto-axis", 4, prog_auto)

FAMILIES = FAMILIES + (fam_symmetry_offset, fam_object_symmetrize, fam_kronecker, fam_frame_crop, fam_outline, fam_period_extend)

# ------------------------------------------------------------------ cycle 10b families
def key_pairs(g, bg):
    """In-grid colour key: isolated 2-cell objects made of two different colours define a->b."""
    m = {}; keycells = set()
    for ob in objects(g, bg, False, False):
        if len(ob) != 2: continue
        (y1, x1), (y2, x2) = sorted(ob)
        a, b = g[y1][x1], g[y2][x2]
        if a == b: continue
        if m.get(a, b) != b: return None, None
        m[a] = b; keycells |= set(ob)
    return (m, keycells) if m else (None, None)

def fam_key_recolour(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    for rev in (False, True):
        def fn(g, rev=rev):
            bg = bg_of(g); m, kc = key_pairs(g, bg)
            if not m: return None
            if rev: m = {v: k for k, v in m.items()}
            return [[m.get(v, v) if (y, x) not in kc else v for x, v in enumerate(r)] for y, r in enumerate(g)]
        yield (f"key-recolour{':reverse' if rev else ''}", 3, fn)

def fam_marker_object(train):
    """Crop / keep the (multi-colour) object that contains a cell of an induced marker colour."""
    i, o = train[0]["input"], train[0]["output"]
    same = (H(o), W(o)) == (H(i), W(i))
    for c in sorted(colours(i) - {bg_of(i)}):
        for diag in (True, False):
            def pick(g, c=c, diag=diag):
                bg = bg_of(g); hits = [ob for ob in objects(g, bg, diag, False) if any(g[y][x] == c for y, x in ob)]
                return hits[0] if len(hits) == 1 else None
            if same:
                def keep(g, pick=pick):
                    ob = pick(g)
                    if not ob: return None
                    bg = bg_of(g); out = [[bg] * W(g) for _ in range(H(g))]
                    for y, x in ob: out[y][x] = g[y][x]
                    return out
                yield (f"keep-object-with[c{c}{',8' if diag else ''}]", 3, keep)
            else:
                yield (f"crop:object-with[c{c}{',8' if diag else ''}]", 3, lambda g, pick=pick: (lambda ob: crop(g, bbox(ob)) if ob else None)(pick(g)))

def fam_count_output(train):
    """Output size equals a count of objects; filled with an induced colour or the counted colour."""
    shapes = {(H(p["output"]), W(p["output"])) for p in train}
    outs_c = [colours(p["output"]) for p in train]
    if not all(len(c) == 1 for c in outs_c): return
    for diag, byc in product((False, True), (True, False)):
        for orient in ("row", "col"):
            for colour_rule in ("most_common_object_colour", "constant"):
                const = list(outs_c[0])[0]
                def fn(g, diag=diag, byc=byc, orient=orient, colour_rule=colour_rule, const=const):
                    bg = bg_of(g); obs = objects(g, bg, diag, byc)
                    if not obs: return None
                    col = const if colour_rule == "constant" else Counter(g[o[0][0]][o[0][1]] for o in obs).most_common(1)[0][0]
                    n = len(obs) if colour_rule == "constant" else sum(1 for o in obs if g[o[0][0]][o[0][1]] == col)
                    return [[col] * n] if orient == "row" else [[col] for _ in range(n)]
                yield (f"count-objects[{'8' if diag else '4'}{'' if byc else ',multi'}]:{orient}:{colour_rule}", 3, fn)

def fam_colour_select_fill(train):
    """Output has a fixed shape (same in all pairs) filled with one colour chosen by a rule."""
    shapes = {(H(p["output"]), W(p["output"])) for p in train}
    if len(shapes) != 1 or not all(len(colours(p["output"])) == 1 for p in train): return
    h, w = shapes.pop()
    rules = {"most_frequent_fg": lambda g, bg: Counter(v for r in g for v in r if v != bg).most_common(1)[0][0],
             "least_frequent_fg": lambda g, bg: Counter(v for r in g for v in r if v != bg).most_common()[-1][0],
             "largest_object": lambda g, bg: (lambda ob: g[ob[0][0]][ob[0][1]])(max(objects(g, bg, False, True), key=len)),
             "smallest_object": lambda g, bg: (lambda ob: g[ob[0][0]][ob[0][1]])(min(objects(g, bg, False, True), key=len)),
             "most_objects": lambda g, bg: Counter(g[o[0][0]][o[0][1]] for o in objects(g, bg, False, True)).most_common(1)[0][0]}
    for rn, f in rules.items():
        def fn(g, f=f):
            bg = bg_of(g); c = f(g, bg)
            return [[c] * w for _ in range(h)]
        yield (f"fill-{h}x{w}-with:{rn}", 3, fn)

FAMILIES = FAMILIES + (fam_key_recolour, fam_marker_object, fam_count_output, fam_colour_select_fill)

def candidates(train):
    out = []
    for fam in FAMILIES:
        try:
            out.extend(fam(train))
        except Exception:
            continue
    out = out + list(compose_dihedral(out))
    out.sort(key=lambda x: x[1])
    return out

def run(fn, g):
    try:
        r = fn(g)
        if r is not None and not isinstance(r, list): r = [list(map(int, row)) for row in r]
        elif r is not None: r = [list(map(int, row)) for row in r]
        if r is None or not r or not r[0] or H(r) > 30 or W(r) > 30: return None
        return r
    except Exception:
        return None

# ------------------------------------------------------------------ cycle 11 families: object motion
DIRV = {"down": (1, 0), "up": (-1, 0), "left": (0, -1), "right": (0, 1)}

def static_colours(train):
    """Colours whose cells never change between input and output in any training pair (obstacles/anchors)."""
    st = None
    for p in train:
        i, o = p["input"], p["output"]
        if (H(i), W(i)) != (H(o), W(o)): return set()
        cs = {v for r in i for v in r}
        ok = {c for c in cs if all(o[y][x] == c for y in range(H(i)) for x in range(W(i)) if i[y][x] == c)}
        st = ok if st is None else st & ok
    return st or set()

def slide(g, movers, statics, dy, dx, bg):
    """Move each mover object rigidly by (dy,dx) steps until the next step would leave the grid or hit
    a non-background cell that is not part of itself. Movers are processed from the leading edge."""
    out = [r[:] for r in g]
    key = lambda ob: -max(y * dy + x * dx for y, x in ob)
    for ob in sorted(movers, key=key):
        col = {(y, x): out[y][x] for y, x in ob}
        for y, x in ob: out[y][x] = bg
        cur = list(ob); k = 0
        while True:
            nxt = [(y + dy, x + dx) for y, x in cur]
            if any(not (0 <= y < H(g) and 0 <= x < W(g)) or out[y][x] != bg for y, x in nxt): break
            cur = nxt; k += 1
        for (y0, x0), (y, x) in zip(ob, cur): out[y][x] = col[(y0, x0)]
    return out

def fam_object_gravity(train):
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    st = static_colours(train)
    for d, (dy, dx) in DIRV.items():
        for diag, byc in product((False, True), (True, False)):
            def fn(g, dy=dy, dx=dx, diag=diag, byc=byc):
                bg = bg_of(g); obs = objects(g, bg, diag, byc)
                movers = [ob for ob in obs if not all(g[y][x] in st for y, x in ob)]
                if not movers or len(movers) == len(obs) and st: return None
                return slide(g, movers, st, dy, dx, bg)
            yield (f"object-gravity:{d}[{'8' if diag else '4'}{'' if byc else ',multi'}]", 3, fn)

def fam_move_to_target(train):
    """Each mover object moves in a straight line toward the static (anchor) object it faces, stopping on contact."""
    i, o = train[0]["input"], train[0]["output"]
    if (H(o), W(o)) != (H(i), W(i)): return
    st = static_colours(train)
    if not st: return
    for diag, byc in product((False, True), (True, False)):
        def fn(g, diag=diag, byc=byc):
            bg = bg_of(g); obs = objects(g, bg, diag, byc)
            anchors = [ob for ob in obs if all(g[y][x] in st for y, x in ob)]
            movers = [ob for ob in obs if ob not in anchors]
            if not anchors or not movers: return None
            out = [r[:] for r in g]
            for ob in movers:
                r0, c0, r1, c1 = bbox(ob); best = None
                for an in anchors:
                    a0, b0, a1, b1 = bbox(an)
                    if b0 <= c1 and c0 <= b1:           # vertical overlap -> move up/down
                        d = (1, 0) if a0 > r1 else (-1, 0) if a1 < r0 else None
                        dist = a0 - r1 if a0 > r1 else r0 - a1
                    elif a0 <= r1 and r0 <= a1:         # horizontal overlap -> move left/right
                        d = (0, 1) if b0 > c1 else (0, -1) if b1 < c0 else None
                        dist = b0 - c1 if b0 > c1 else c0 - b1
                    else:
                        continue
                    if d and (best is None or dist < best[0]): best = (dist, d)
                if best: out = slide(out, [ob], st, best[1][0], best[1][1], bg)
            return out
        yield (f"move-to-anchor[{'8' if diag else '4'}{'' if byc else ',multi'}]", 3, fn)

FAMILIES = FAMILIES + (fam_object_gravity, fam_move_to_target)

def residual_steps(train, k=4):
    """Same-size first steps that move every pair strictly closer to its output and never break a correct cell."""
    outs = [p["output"] for p in train]
    if any((H(p["input"]), W(p["input"])) != (H(o), W(o)) for p, o in zip(train, outs)): return []
    scored = []
    for name, cost, fn in candidates(train):
        if name.startswith(RESHAPERS) or ">" in name: continue
        gain = 0; ok = True; preds = []
        for p, o in zip(train, outs):
            i = p["input"]; r = run(fn, i)
            if r is None or (H(r), W(r)) != (H(o), W(o)) or r == i: ok = False; break
            broke = any(i[y][x] == o[y][x] and r[y][x] != o[y][x] for y in range(H(o)) for x in range(W(o)))
            fixed = sum(i[y][x] != o[y][x] and r[y][x] == o[y][x] for y in range(H(o)) for x in range(W(o)))
            if broke or fixed == 0: ok = False; break
            gain += fixed; preds.append(r)
        if ok: scored.append((-gain, cost, name, fn, preds))
    scored.sort(key=lambda x: (x[0], x[1]))
    return scored[:k]

def search2(task, max_programs=4):
    """Two-step programs: a residual first step, then a full single-step search on its outputs."""
    res = []
    for _, cost, name, fn, preds in residual_steps(task["train"]):
        sub = {"train": [{"input": r, "output": p["output"]} for r, p in zip(preds, task["train"])],
               "test": [{"input": run(fn, t["input"])} for t in task["test"]]}
        if any(t["input"] is None for t in sub["test"]): continue
        for r in search(sub, max_programs=2, allow2=False):
            res.append({"program": name + " ; " + r["program"], "cost": cost + r["cost"], "preds": r["preds"]})
        if len(res) >= max_programs: break
    return res

def search(task, max_programs=6, allow2=True):
    """Return verified programs: list of dicts {program, cost, preds}. Cheapest first; with and without colour map."""
    train = task["train"]; outs = [p["output"] for p in train]
    found = []
    # identity + colour map alone (pure recolouring)
    ident = [p["input"] for p in train]
    m = fit_cmap(ident, outs)
    if m and any(k != v for k, v in m.items()) and all(apply_cmap(a, m) == b for a, b in zip(ident, outs)):
        found.append(("colour-map", 1, lambda g, m=m: apply_cmap(g, m)))
    for name, cost, fn in candidates(train):
        preds = []
        for p, o in zip(train, outs):
            r = run(fn, p["input"])
            if r is None or H(r) != H(o) or W(r) != W(o): preds = None; break
            if not preds and fit_cmap([r], [o]) is None: preds = None; break
            preds.append(r)
        if not preds: continue
        if preds == outs:
            found.append((name, cost, fn))
        else:
            m = fit_cmap(preds, outs)
            if m and all(apply_cmap(a, m) == b for a, b in zip(preds, outs)):
                found.append((name + "+colour-map", cost + 1, lambda g, fn=fn, m=m: apply_cmap(run(fn, g), m)))
        if len(found) >= max_programs: break
    res, seen = [], set()
    for name, cost, fn in sorted(found, key=lambda x: x[1]):
        preds = [run(fn, t["input"]) for t in task["test"]]
        if any(p is None for p in preds): continue
        k = str(preds)
        if k in seen: continue
        seen.add(k); res.append({"program": name, "cost": cost, "preds": preds})
    if not res and allow2:
        res = search2(task)
    return res

# ------------------------------------------------------------------ cycle 12: own primitives (latent/)
import importlib as _il
for _m in ("fam_lines", "fam_move_by_vector", "fam_crop_by_score", "fam_summarise_ranked_bars",
           "fam_move_slide_until_contact", "fam_fill_region_by_property", "fam_stamp_local_stencil",
           "fam_ray_diagonal_from_object", "fam_stamp_complete_partial_matches", "fam_extend_periodic_fill",
           "fam_ray_orthogonal_directed", "fam_summarise_panel_to_pixel", "fam_summarise_count_to_glyph",
           "fam_ray_walker_turn_split", "fam_move_to_position", "fam_recolour_by_distance_layers", "fam_move_toward_anchor",
           "fam_stamp_template_at_markers", "fam_transform_kronecker", "fam_crop_fit_by_anchor", "fam_segment_pack_pieces",
           "fam_summarise_concentric_rings", "fam_combine_boolean_panels"):
    try:
        FAMILIES = FAMILIES + tuple(_il.import_module(_m).FAMILIES)
    except Exception:
        pass
