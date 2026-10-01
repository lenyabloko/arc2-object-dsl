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
            best, apex, tie = None, None, False
            for a in cells:
                s = sum((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 for b in cells)
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


def _hits(g, bg, d, pol, stamp):
    """Return (glyphs, owner map cell->glyph index, hit counts cell->k)."""
    H, W = len(g), len(g[0])
    gl = _glyphs(g, bg)
    owner = {}
    for i, o in enumerate(gl):
        for p in o["cells"]:
            owner[p] = i
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
    return gl, owner, hits


def _render(g, bg, d, pol, stamp, hit, mcol, ccol):
    gl, owner, hits = _hits(g, bg, d, pol, stamp)
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


def _induce(train, d, pol, stamp, hit):
    """Read the alternative colour and the collision colour off the training outputs."""
    s1, s2 = set(), set()
    for p in train:
        g, o = p["input"], p["output"]
        bg = _bg(g)
        _, owner, hits = _hits(g, bg, d, pol, stamp)
        for t, k in hits.items():
            if t in owner and hit == "keep":
                continue
            (s1 if k == 1 else s2).add(o[t[0]][t[1]])
    if len(s1) != 1 or len(s2) > 1:
        return None
    mcol = next(iter(s1))
    ccol = next(iter(s2)) if s2 else mcol
    return mcol, ccol


def fam(train):
    if not train:
        return
    dmax = 0
    for p in train:
        g, o = p["input"], p["output"]
        if not g or len(g) != len(o) or len(g[0]) != len(o[0]):
            return
        if g == o:
            return
        bg = _bg(g)
        if not any(x["dir"] is not None for x in _glyphs(g, bg)):
            return
        dmax = max(dmax, len(g), len(g[0]))
    found = []
    for pol in (1, -1):
        for stamp in ("pixel", "glyph"):
            for hit in ("glyph", "cell", "keep"):
                for d in range(1, dmax):
                    cols = _induce(train, d, pol, stamp, hit)
                    if cols is None:
                        continue
                    mcol, ccol = cols
                    ok = True
                    for p in train:
                        g = p["input"]
                        bg = _bg(g)
                        if mcol == bg or _render(g, bg, d, pol, stamp, hit, mcol, ccol) != p["output"]:
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
