"""Family for ARC task 9aaea919 -- concept: CONSERVATION (physics: source -> sink transfer of a counted quantity).

Picture: tokens (identical objects) are stacked in lanes that stand on a *gauge edge* of the grid.  Coloured
bars on that edge label some lanes as SOURCE or SINK.  Quantity is conserved: every token in the source lanes
is withdrawn (it stays as a spent ghost, repainted in the "spent" colour) and the same number of tokens is
deposited on the sink lane(s), stacked further away from the edge with the lane's own pitch.  The labelling
bars are consumed (become background).

Everything is induced from the training pairs:
  background     = most common colour of the input
  gauge edge     = the grid border line holding the labelling bars (tried in all 4 orientations, per grid)
  source colour  = bar colour whose lane's tokens change colour in the output
  sink colour    = bar colour whose lane grows in the output
  spent colour   = the single colour source tokens take in the output
  pitch          = token extent + the gap between the bar and the nearest token (measured per lane)
Declared finite domains: orientation k in {0,1,2,3} (quarter turns, found per grid), connectivity in {4, 8}.
"""
from collections import Counter


def most_common_colour(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def rot(g, k):
    """Rotate k quarter turns clockwise."""
    for _ in range(k % 4):
        g = [list(r) for r in zip(*g[::-1])]
    return [list(r) for r in g]


def runs(row, bg):
    """Maximal runs of equal non-background colour: (colour, c0, c1) inclusive."""
    out, c = [], 0
    while c < len(row):
        if row[c] == bg:
            c += 1
            continue
        s = c
        while c + 1 < len(row) and row[c + 1] == row[s]:
            c += 1
        out.append((row[s], s, c))
        c += 1
    return out


def objects(g, bg, rows, conn):
    """Connected non-background components restricted to the given row range."""
    H, W = len(g), len(g[0])
    nb = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if conn == 8:
        nb += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    seen, comps = set(), []
    for r in rows:
        for c in range(W):
            if g[r][c] == bg or (r, c) in seen:
                continue
            st, cells = [(r, c)], []
            seen.add((r, c))
            while st:
                y, x = st.pop()
                cells.append((y, x, g[y][x]))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if yy in rows and 0 <= xx < W and (yy, xx) not in seen and g[yy][xx] != bg:
                        seen.add((yy, xx))
                        st.append((yy, xx))
            comps.append(cells)
    return comps


def lanes(g, bg, conn):
    """For a grid whose gauge edge is the bottom row: list of (bar colour, c0, c1, tokens nearest-first)."""
    H = len(g)
    rows = range(H - 1)
    comps = objects(g, bg, rows, conn)
    out = []
    for col, c0, c1 in runs(g[H - 1], bg):
        toks = [o for o in comps if min(x for _, x, _ in o) <= c1 and max(x for _, x, _ in o) >= c0]
        toks.sort(key=lambda o: -max(y for y, _, _ in o))
        out.append((col, c0, c1, toks))
    return out


def orient(g, bg, bar_colours):
    """Quarter-turn k that brings the gauge edge (a border line whose non-bg cells are all bar colours) down."""
    for k in range(4):
        h = rot(g, k)
        edge = [v for v in h[-1] if v != bg]
        if edge and all(v in bar_colours for v in edge):
            return k
    return None


def conserve(g, bg, source, sink, spent, conn):
    H, W = len(g), len(g[0])
    out = [row[:] for row in g]
    ls = lanes(g, bg, conn)
    moved = sum(len(t) for col, _, _, t in ls if col == source)
    for col, c0, c1, toks in ls:
        if col == source:
            for o in toks:
                for y, x, _ in o:
                    out[y][x] = spent
        elif col == sink and toks and moved:
            near = toks[0]
            gap = (H - 1) - max(y for y, _, _ in near) - 1
            far = toks[-1]
            ext = max(y for y, _, _ in far) - min(y for y, _, _ in far) + 1
            pitch = ext + gap
            for i in range(1, moved + 1):
                for y, x, v in far:
                    yy = y - i * pitch
                    if 0 <= yy < H - 1:
                        out[yy][x] = v
    out[H - 1] = [bg] * W
    return out


def induce_roles(train, conn):
    """Return (source colour, sink colour, spent colour) consistent with all pairs, else None."""
    source = sink = spent = None
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        bg = most_common_colour(a)
        k = None
        for kk in range(4):
            ra, rb = rot(a, kk), rot(b, kk)
            if any(v != bg for v in ra[-1]) and all(v == bg for v in rb[-1]):
                k = kk
                break
        if k is None:
            return None
        ra, rb = rot(a, k), rot(b, k)
        for col, c0, c1, toks in lanes(ra, bg, conn):
            if not toks:
                continue
            new = {rb[y][x] for o in toks for y, x, _ in o}
            recoloured = any(rb[y][x] != v for o in toks for y, x, v in o)
            grown = False
            top = min(y for o in toks for y, _, _ in o)
            for y in range(top):
                if any(rb[y][x] != ra[y][x] for x in range(c0, c1 + 1)):
                    grown = True
            if recoloured and not grown:
                if len(new) != 1 or (source not in (None, col)) or (spent not in (None, next(iter(new)))):
                    return None
                source, spent = col, next(iter(new))
            elif grown and not recoloured:
                if sink not in (None, col):
                    return None
                sink = col
    if None in (source, sink, spent) or source == sink:
        return None
    return source, sink, spent


def fam_conservation(train):
    for conn in (4, 8):
        roles = induce_roles(train, conn)
        if roles is None:
            continue
        source, sink, spent = roles

        def fn(g, source=source, sink=sink, spent=spent, conn=conn):
            bg = most_common_colour(g)
            k = orient(g, bg, {source, sink})
            if k is None:
                return [row[:] for row in g]
            return rot(conserve(rot(g, k), bg, source, sink, spent, conn), -k)

        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("physics:conservation[source=%d,sink=%d,spent=%d,conn=%d]" % (source, sink, spent, conn), 3, fn)
            return


FAMILIES = (fam_conservation,)
