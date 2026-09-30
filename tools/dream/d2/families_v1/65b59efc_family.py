"""Family for ARC task 65b59efc -- concept: TILEMAP (computer graphics / 8-bit video hardware).

A tile-based display is described by three tables:
  * a pattern table  (the tile set: one small bitmap per tile, each tile identified by its colour),
  * a name table     (the tile map: which tile goes into each screen cell),
  * a palette table  (which ink each tile is drawn with).
The input grid is a sheet cut by a lattice of separator lines into k x k panels arranged in bands.
One band is the pattern table, one band is the name table (its panels are overlaid into a single
k x k map whose colours name tiles), one band is the palette (one ink colour per panel column).
Rendering = replace every map cell by the k x k bitmap of the named tile, painted with the ink
from the palette entry in the same panel column as that tile; empty map cells stay background.

Everything is induced:
  background  = most common colour
  separator   = the colour (and period k+1, phase o) whose cells best form a lattice of lines
  k           = panel size (lattice period - 1)
Declared finite parameters (induced from the training pairs):
  orient  in {rows, cols}            -- bands stacked vertically (rows) or side by side (cols)
  roles   in permutations of (0,1,2) -- which band is (pattern table, name table, palette)
  ink     in {palette, own}          -- paint tiles with palette ink or with the tile's own colour
"""
from collections import Counter
from itertools import permutations


# ---------------------------------------------------------------- helpers
def transpose(g):
    return [list(r) for r in zip(*g)]


def background(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def find_lattice(g, bg):
    """Return (sep_colour, k, phase): lines at indices i with i % (k+1) == phase, in both axes.
    Score = (fraction of line intersections carrying the colour) * (fraction of that colour's
    cells lying on a line).  Ties -> more matched intersections, then coarser lattice."""
    H, W = len(g), len(g[0])
    pos = {}
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg:
                pos.setdefault(g[r][c], []).append((r, c))
    best, best_key = None, None
    for col, cells in pos.items():
        n = len(cells)
        for k in range(1, max(H, W)):
            p = k + 1
            for o in range(0, k + 1):
                R = range(o, H, p)
                C = range(o, W, p)
                if not R or not C:
                    continue
                hit = sum(1 for r in R for c in C if g[r][c] == col)
                if hit == 0:
                    continue
                a = hit / (len(R) * len(C))
                b = sum(1 for (r, c) in cells if r % p == o or c % p == o) / n
                key = (round(a * b, 9), hit, k)
                if best_key is None or key > best_key:
                    best_key, best = key, (col, k, o)
    return best


def runs(n, k, o):
    """Maximal runs of non-line indices in range(n) for lines at i % (k+1) == o."""
    out, cur = [], []
    for i in range(n):
        if i % (k + 1) == o:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def dominant(vals, bg):
    cnt = Counter(v for v in vals if v != bg)
    return cnt.most_common(1)[0][0] if cnt else None


def render_tilemap(g, orient, roles, ink):
    if orient == "cols":
        g = transpose(g)
    bg = background(g)
    lat = find_lattice(g, bg)
    if lat is None:
        return None
    sep, k, o = lat
    H, W = len(g), len(g[0])
    bands = runs(H, k, o)                              # horizontal bands of panels
    cols = [cr for cr in runs(W, k, o) if len(cr) == k]  # full panel columns
    if len(bands) <= max(roles) or not cols:
        return None
    LB, MB, PB = (bands[i] for i in roles)
    if len(LB) != k or len(MB) != k:
        return None

    # pattern table: tile colour -> (bitmap, panel column index)
    tiles = {}
    inks = {}
    for j, cr in enumerate(cols):
        panel = [[g[r][c] for c in cr] for r in LB]
        tc = dominant([v for row in panel for v in row], bg)
        if tc is None or tc == sep or tc in tiles:
            continue
        tiles[tc] = [[v == tc for v in row] for row in panel]
        pc = dominant([g[r][c] for r in PB for c in cr], bg)
        inks[tc] = pc if (ink == "palette" and pc is not None and pc != sep) else tc
    if not tiles:
        return None

    # name table: overlay of all panels of the map band
    name = [[bg] * k for _ in range(k)]
    for cr in cols:
        for i, r in enumerate(MB):
            for jj, c in enumerate(cr):
                v = g[r][c]
                if v != bg and v != sep and name[i][jj] == bg:
                    name[i][jj] = v

    # render
    out = [[bg] * (k * k) for _ in range(k * k)]
    for i in range(k):
        for j in range(k):
            t = name[i][j]
            if t not in tiles:
                continue
            bm, colour = tiles[t], inks[t]
            for a in range(k):
                for b in range(k):
                    if bm[a][b]:
                        out[i * k + a][j * k + b] = colour
    if orient == "cols":
        out = transpose(out)
    return out


# ---------------------------------------------------------------- family
def fam_tilemap(train):
    for orient in ("rows", "cols"):
        for roles in permutations(range(3)):
            for ink in ("palette", "own"):
                def fn(g, orient=orient, roles=roles, ink=ink):
                    return render_tilemap(g, orient, roles, ink)
                try:
                    ok = all(fn(p["input"]) == p["output"] for p in train)
                except Exception:
                    ok = False
                if ok:
                    yield ("graphics:tilemap[orient=%s,roles=%s,ink=%s]"
                           % (orient, "".join(map(str, roles)), ink), 3, fn)
                    return


FAMILIES = (fam_tilemap,)
