"""Line family for card a644e277 (test-blind; induced only from train pairs).

Reading: the input is a lattice of tiles separated by full grid lines of one colour.  A few cells
lying ON the grid lines carry the tiles' own colour instead of the line colour: these are the
markers.  They surround a rectangular block of the tiling; the output is that block cut out of
the input (markers included, or only what lies strictly inside them).
"""
from collections import Counter

CARD = "a644e277"
LINE = "extract the tiled area surrounded by markers of the same color as tiles"
READING = {
    "generator": "Cut out of the input the rectangle spanned by the markers - the cells on the grid lines "
                 "that have the tiles' colour instead of the line colour - and output it unchanged.",
    "stop": "The crop stops at the outermost markers: the bounding box of all markers (kept as the border, "
            "or dropped so only the area strictly inside them remains).",
    "params": "crop ∈ {inclusive, exclusive} · marker ∈ {tile colour, any non-line colour}",
    "participants": "Tile colour = most frequent colour (re-checked as the most frequent colour off the lines); "
                    "grid lines = full rows/columns in which one other colour is the strict majority (line "
                    "colour = the colour with the most such lines); markers = cells on a grid line whose colour "
                    "is the tile colour (or, in the looser variant, any colour other than the line colour).",
    "preconditions": "Every training output is smaller than its input; each input has grid lines of one colour, "
                     "at least two markers, all markers lie on the border of their bounding box (they surround "
                     "it), and the crop is non-empty.",
}


def _structure(g):
    """-> (line colour, tile colour, line rows, line cols) or None."""
    H, W = len(g), len(g[0])
    cnt = Counter(v for r in g for v in r)
    t0 = min(cnt, key=lambda c: (-cnt[c], c))
    best = None
    for c in sorted(cnt):
        if c == t0:
            continue
        rows = [y for y in range(H) if 2 * sum(1 for v in g[y] if v == c) > W]
        cols = [x for x in range(W) if 2 * sum(1 for y in range(H) if g[y][x] == c) > H]
        n = len(rows) + len(cols)
        if n and (best is None or n > best[0]):
            best = (n, c, rows, cols)
    if best is None:
        return None
    _, L, rows, cols = best
    if len(rows) == H or len(cols) == W:
        return None
    rs, cs = set(rows), set(cols)
    off = Counter(g[y][x] for y in range(H) for x in range(W) if y not in rs and x not in cs)
    if not off:
        return None
    T = min(off, key=lambda c: (-off[c], c))
    if T == L:
        return None
    return L, T, rs, cs


def _markers(g, marker):
    st = _structure(g)
    if st is None:
        return None
    L, T, rs, cs = st
    H, W = len(g), len(g[0])
    ms = []
    for y in range(H):
        for x in range(W):
            if (y in rs or x in cs) and (g[y][x] == T if marker == "tile" else g[y][x] != L):
                ms.append((y, x))
    if len(ms) < 2:
        return None
    y0 = min(p[0] for p in ms); y1 = max(p[0] for p in ms)
    x0 = min(p[1] for p in ms); x1 = max(p[1] for p in ms)
    # "surrounded": every marker lies on the border of the markers' bounding box
    if any(y0 < y < y1 and x0 < x < x1 for y, x in ms):
        return None
    return y0, y1, x0, x1


def _crop(g, marker, crop):
    bb = _markers(g, marker)
    if bb is None:
        return None
    y0, y1, x0, x1 = bb
    if crop == "exclusive":
        y0, y1, x0, x1 = y0 + 1, y1 - 1, x0 + 1, x1 - 1
    if y0 > y1 or x0 > x1:
        return None
    return [list(r[x0:x1 + 1]) for r in g[y0:y1 + 1]]


def _make(marker, crop):
    def fn(grid):
        r = _crop(grid, marker, crop)
        if r is None:
            raise ValueError("no marked tiled area")
        return r
    return fn


def fam(train):
    if not train:
        return
    for p in train:
        gi, go = p["input"], p["output"]
        if len(go) * len(go[0]) >= len(gi) * len(gi[0]):
            return
        if len(go) > len(gi) or len(go[0]) > len(gi[0]):
            return
    for mc, marker in enumerate(("tile", "nonline")):
        for cc, crop in enumerate(("inclusive", "exclusive")):
            if all(_crop(p["input"], marker, crop) == p["output"] for p in train):
                yield "extract_marked_tiles[%s,%s]" % (marker, crop), 10 + 2 * mc + cc, _make(marker, crop)


FAMILIES = [fam]
