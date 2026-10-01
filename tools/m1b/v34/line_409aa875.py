"""Line family for card 409aa875 (test-blind; written from the reviewer's line and train pairs only).

Reading: every glyph is an arrowhead (a small object whose medoid cell, the apex, sits off its
centroid; the direction centroid -> apex is where it points).  The glyph pattern is replicated as
a pattern of single pixels in an alternative colour: each glyph throws one pixel a fixed number of
steps from its apex along its direction.  Where a thrown pixel lands on another glyph, that glyph
is redrawn in the alternative colour (the pixel pattern replicated by an alternative glyph).  A
cell reached by several glyphs gets a second alternative colour.
"""

CARD = "409aa875"
LINE = "replicate glyph/pixel pattern using alternative pixel/glyph"
READING = {
    "generator": "Each arrowhead glyph is replicated as one pixel of an alternative colour placed d "
                 "steps from its apex in the direction it points; a glyph that such a pixel lands on "
                 "is redrawn whole in that alternative colour.",
    "stop": "One pixel per glyph (no ray): drawing stops after the single stamp at distance d; "
            "stamps falling outside the grid are dropped.",
    "params": "d in {1..max(H,W)-1} (shared by all glyphs) · pol in {forward, backward} along the "
              "glyph direction · stamp in {pixel, glyph} (single pixel or a copy of the glyph shape) · "
              "hit in {glyph, cell, keep} (what happens when a stamp lands on a glyph) · "
              "alt colour and collision colour induced from the training outputs · bg = most frequent colour",
    "participants": "Glyphs: 8-connected components of non-background cells. Apex: the unique cell "
                    "minimising the summed squared distance to the glyph's other cells. Direction: the "
                    "sign vector of apex minus centroid (up/down/left/right or diagonal). Glyphs "
                    "without a unique apex or with zero direction (e.g. single pixels) do not throw "
                    "but can still be hit.",
    "preconditions": "Output has the input's size; every training input has at least one pointing "
                     "glyph; the changed cells are exactly the stamps (and the glyphs they hit), all in "
                     "one alternative colour except cells reached by two or more glyphs.",
}


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _sign(x):
    return (x > 0) - (x < 0)


def _glyphs(g, bg):
    """8-connected non-bg components with apex and direction (dir None if inert)."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            stack = [(r, c)]
            seen[r][c] = True
            cells = []
            while stack:
                y, x = stack.pop()
                cells.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                            seen[ny][nx] = True
                            stack.append((ny, nx))
            cells.sort()
            n = len(cells)
            # summed squared distance in closed form (exact integers, same values as the pairwise sum)
            s0 = sum(p[0] for p in cells)
            s1 = sum(p[1] for p in cells)
            q = sum(p[0] * p[0] + p[1] * p[1] for p in cells)
            best, apex, tie = None, None, False
            for a in cells:
                s = n * (a[0] * a[0] + a[1] * a[1]) - 2 * (a[0] * s0 + a[1] * s1) + q
                if best is None or s < best:
                    best, apex, tie = s, a, False
                elif s == best:
                    tie = True
            d = None
            if not tie and n > 1:
                sr = sum(p[0] for p in cells)
                sc = sum(p[1] for p in cells)
                dv = (_sign(n * apex[0] - sr), _sign(n * apex[1] - sc))
                if dv != (0, 0):
                    d = dv
            out.append({"cells": cells, "apex": apex, "dir": d})
    return out


def _owner(gl):
    owner = {}
    for i, o in enumerate(gl):
        for p in o["cells"]:
            owner[p] = i
    return owner


def _throw(gl, H, W, d, pol, stamp):
    """hit counts cell->k for precomputed glyphs."""
    hits = {}
    for o in gl:
        if o["dir"] is None:
            continue
        oy, ox = pol * d * o["dir"][0], pol * d * o["dir"][1]
        src = [o["apex"]] if stamp == "pixel" else o["cells"]
        for (y, x) in src:
            t = (y + oy, x + ox)
            if 0 <= t[0] < H and 0 <= t[1] < W:
                hits[t] = hits.get(t, 0) + 1
    return hits


def _hits(g, bg, d, pol, stamp):
    """Return (glyphs, owner map cell->glyph index, hit counts cell->k)."""
    gl = _glyphs(g, bg)
    return gl, _owner(gl), _throw(gl, len(g), len(g[0]), d, pol, stamp)


def _paint(g, gl, owner, hits, hit, mcol, ccol):
    out = [list(row) for row in g]
    recol = {}
    for t in sorted(hits):
        col = mcol if hits[t] == 1 else ccol
        if t not in owner:
            out[t[0]][t[1]] = col
        elif hit == "cell":
            out[t[0]][t[1]] = col
        elif hit == "glyph":
            i = owner[t]
            # several hits on one glyph: the collision colour wins
            if recol.get(i) != ccol:
                recol[i] = col
    for i in sorted(recol):
        for (y, x) in gl[i]["cells"]:
            out[y][x] = recol[i]
    return out


def _render(g, bg, d, pol, stamp, hit, mcol, ccol):
    gl, owner, hits = _hits(g, bg, d, pol, stamp)
    return _paint(g, gl, owner, hits, hit, mcol, ccol)


def _induce(pre, hl, hit):
    """Read the alternative colour and the collision colour off the training outputs."""
    s1, s2 = set(), set()
    for P, hits in zip(pre, hl):
        o, owner = P["o"], P["owner"]
        for t, k in hits.items():
            if t in owner and hit == "keep":
                continue
            (s1 if k == 1 else s2).add(o[t[0]][t[1]])
    if len(s1) != 1 or len(s2) > 1:
        return None
    mcol = next(iter(s1))
    ccol = next(iter(s2)) if s2 else mcol
    return mcol, ccol


def _explains(P, hits, hit):
    """Necessary condition: every changed cell is one the rendering could have repainted."""
    owner = P["owner"]
    if hit == "glyph":
        hitg = {owner[t] for t in hits if t in owner}
    for c in P["chg"]:
        i = owner.get(c)
        if i is None or hit == "cell":
            if c not in hits:
                return False
        elif hit == "keep":
            return False
        elif i not in hitg:
            return False
    return True


def fam(train):
    if not train:
        return
    dmax = 0
    pre = []
    for p in train:
        g, o = p["input"], p["output"]
        if not g or len(g) != len(o) or len(g[0]) != len(o[0]):
            return
        if g == o:
            return
        bg = _bg(g)
        gl = _glyphs(g, bg)
        if not any(x["dir"] is not None for x in gl):
            return
        dmax = max(dmax, len(g), len(g[0]))
        pre.append({"g": g, "o": o, "bg": bg, "gl": gl, "H": len(g), "W": len(g[0])})
    # every repainted cell takes the alternative or the collision colour: at most two new colours
    newcols = set()
    for P in pre:
        g, o = P["g"], P["o"]
        P["chg"] = [(y, x) for y in range(P["H"]) for x in range(P["W"]) if g[y][x] != o[y][x]]
        newcols |= {o[y][x] for (y, x) in P["chg"]}
        if len(newcols) > 2:
            return
    for P in pre:
        P["owner"] = _owner(P["gl"])
    found = []
    for pol in (1, -1):
        for stamp in ("pixel", "glyph"):
            hcache = {}
            for hit in ("glyph", "cell", "keep"):
                for d in range(1, dmax):
                    hl = hcache.get(d)
                    if hl is None:
                        hl = hcache[d] = [_throw(P["gl"], P["H"], P["W"], d, pol, stamp) for P in pre]
                    if not all(_explains(P, h, hit) for P, h in zip(pre, hl)):
                        continue
                    cols = _induce(pre, hl, hit)
                    if cols is None:
                        continue
                    mcol, ccol = cols
                    ok = True
                    for P, h in zip(pre, hl):
                        if mcol == P["bg"]:
                            ok = False
                            break
                        if _paint(P["g"], P["gl"], P["owner"], h, hit, mcol, ccol) != P["o"]:
                            ok = False
                            break
                    if not ok:
                        continue
                    cost = (d + (0 if pol == 1 else 3) + (0 if stamp == "pixel" else 2)
                            + {"glyph": 0, "cell": 1, "keep": 2}[hit])
                    name = "throw_d%d_%s_%s_hit-%s_alt%d_col%d" % (
                        d, "fwd" if pol == 1 else "bwd", stamp, hit, mcol, ccol)

                    def fn(grid, d=d, pol=pol, stamp=stamp, hit=hit, mcol=mcol, ccol=ccol):
                        return _render(grid, _bg(grid), d, pol, stamp, hit, mcol, ccol)
                    found.append((cost, name, fn))
    found.sort(key=lambda t: (t[0], t[1]))
    for cost, name, fn in found:
        yield name, cost, fn


FAMILIES = [fam]
