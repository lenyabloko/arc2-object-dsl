"""Line family for card 5ad4f10b (test-blind; written from the reviewer's line and train pairs only).

Reading: the input holds a large blocky "area" shape (one colour, built from equal rectangular
cells on a coarse lattice) among scattered noise of another colour (single pixels, short rows or
columns). The area shape is extracted at its own cell resolution -- one output cell per lattice
cell of its bounding box -- and its occupied cells are recoloured with the noise colour, the rest
left as background.
"""

from math import gcd

CARD = "5ad4f10b"
LINE = "extract area shapes and recolor into sinlge pixels/rows/columns' color"
READING = {
    "generator": "Crop the bounding box of the large blocky shape, shrink it so each of its "
                 "equal-size cells becomes one pixel, and paint the occupied cells with the colour "
                 "of the scattered single pixels / short rows / columns (other cells background).",
    "stop": "The output ends at the shape's bounding box; its size is that box divided by the "
            "shape's cell size (gcd of its run lengths, or the output size shared by all train pairs).",
    "params": "sel in {largest_component, fewest_components} (which colour is the area) · "
              "cell in {runs, out_shape} (how the cell lattice is found) · "
              "ink in {noise, area} · bg = most frequent input colour",
    "participants": "Area: every pixel of the non-background colour picked by `sel` (owner of the "
                    "largest 8-connected component, or the colour with fewest components). Noise: the "
                    "most frequent remaining non-background colour; its pixels are treated as "
                    "unknown when they fall on the area's box.",
    "preconditions": "Every input has at least two non-background colours; the area's bounding box "
                     "splits into equal cells, each (ignoring noise pixels) wholly area or wholly not.",
}


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _components(g, col):
    H, W = len(g), len(g[0])
    seen = set()
    comps = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != col or (r, c) in seen:
                continue
            stack = [(r, c)]
            seen.add((r, c))
            n = 0
            while stack:
                y, x = stack.pop()
                n += 1
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < H and 0 <= xx < W and (yy, xx) not in seen and g[yy][xx] == col:
                            seen.add((yy, xx))
                            stack.append((yy, xx))
            comps.append(n)
    return comps


def _roles(g, sel):
    """(bg, area colour, noise colour) or None."""
    bg = _bg(g)
    cnt = {}
    for row in g:
        for v in row:
            if v != bg:
                cnt[v] = cnt.get(v, 0) + 1
    cols = sorted(cnt)
    if len(cols) < 2:
        return None
    comps = {c: _components(g, c) for c in cols}
    if sel == "largest_component":
        area = max(cols, key=lambda c: (max(comps[c]), -len(comps[c]), -c))
    else:
        area = min(cols, key=lambda c: (len(comps[c]), -max(comps[c]), c))
    rest = [c for c in cols if c != area]
    noise = max(rest, key=lambda c: (cnt[c], -c))
    return bg, area, noise


def _band_ok(rows, k):
    """rows: list of sequences over {0,1,None}; True if every band of k consecutive rows is constant
    per column (None = unknown)."""
    if k <= 0 or len(rows) % k:
        return False
    W = len(rows[0])
    for b in range(0, len(rows), k):
        for x in range(W):
            v = None
            for y in range(b, b + k):
                u = rows[y][x]
                if u is None:
                    continue
                if v is None:
                    v = u
                elif u != v:
                    return False
    return True


def _coarsest(rows):
    """Largest band height k dividing len(rows) with constant bands (gcd of vertical runs)."""
    n = len(rows)
    for k in range(n, 0, -1):
        if n % k == 0 and _band_ok(rows, k):
            return k
    return 1


def _mask(g, area, noise):
    pts = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == area]
    r0 = min(p[0] for p in pts); r1 = max(p[0] for p in pts)
    c0 = min(p[1] for p in pts); c1 = max(p[1] for p in pts)
    m = [[1 if g[r][c] == area else (None if g[r][c] == noise else 0) for c in range(c0, c1 + 1)]
         for r in range(r0, r1 + 1)]
    return m


def _make(sel, cell, ink, shape=None):
    def fn(g):
        roles = _roles(g, sel)
        if roles is None:
            return None
        bg, area, noise = roles
        m = _mask(g, area, noise)
        H, W = len(m), len(m[0])
        if cell == "runs":
            kh = _coarsest(m)
            kw = _coarsest([list(t) for t in zip(*m)])
        else:
            oh, ow = shape
            if H % oh or W % ow:
                return None
            kh, kw = H // oh, W // ow
        colour = noise if ink == "noise" else area
        out = []
        for by in range(0, H, kh):
            row = []
            for bx in range(0, W, kw):
                on = off = 0
                for y in range(by, by + kh):
                    for x in range(bx, bx + kw):
                        v = m[y][x]
                        if v == 1:
                            on += 1
                        elif v == 0:
                            off += 1
                row.append(colour if on > off else bg)
            out.append(row)
        return out
    return fn


def fam(train):
    for p in train:
        if _roles(p["input"], "largest_component") is None:
            return
    shapes = {(len(p["output"]), len(p["output"][0])) for p in train}
    progs = []
    for si, sel in enumerate(("largest_component", "fewest_components")):
        for ki, ink in enumerate(("noise", "area")):
            progs.append(("area_downscale_recolor[sel=%s,cell=runs,ink=%s]" % (sel, ink),
                          1 + si + 2 * ki, _make(sel, "runs", ink)))
            if len(shapes) == 1:
                shp = next(iter(shapes))
                progs.append(("area_downscale_recolor[sel=%s,cell=out_shape,ink=%s]" % (sel, ink),
                              2 + si + 2 * ki, _make(sel, "out_shape", ink, shp)))
    progs.sort(key=lambda t: t[1])
    seen = set()
    for name, cost, fn in progs:
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        sig = repr(outs)
        if sig in seen:
            continue  # identical behaviour on train to a cheaper program
        seen.add(sig)
        yield name, cost, fn


FAMILIES = [fam]
