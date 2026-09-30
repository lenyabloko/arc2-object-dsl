"""Family for 2d0172a1 -- cartography: SCHEMATIC MAP (Beck's Tube-map principle).

A schematic map keeps only topology and order: every hand-drawn closed curve becomes an axis-aligned
rectangle, every solid blob becomes a single station-dot, nesting (inside/outside) and the left/right,
above/below order of all features is preserved, features whose extents overlap on an axis are aligned
on that axis, and all distances are replaced by one uniform spacing (one background line between
consecutive features).  Rectangles are drawn to the edge of the map; a dot carries a margin of `margin`
background cells around it (so a dot lying outside every curve does not sit on the map border).

Parameters (finite, induced from train):  conn in {4, 8}  (connectivity of the drawn strokes),
                                          margin in {1, 0} (background margin kept around a dot).
Colours by role: background = most frequent input colour; each shape keeps its own colour.
"""
from collections import Counter

N4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
N8 = N4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))


def _components(g, bg, nb):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    comps = []
    for r in range(H):
        for c in range(W):
            if seen[r][c] or g[r][c] == bg:
                continue
            seen[r][c] = True
            st, cells = [(r, c)], []
            while st:
                y, x = st.pop()
                cells.append((y, x))
                for dy, dx in nb:
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < H and 0 <= xx < W and not seen[yy][xx] and g[yy][xx] != bg:
                        seen[yy][xx] = True
                        st.append((yy, xx))
            comps.append(cells)
    return comps


def _interior(cells, H, W, nb_dual):
    """Cells enclosed by the stroke `cells`: not reachable from the grid border without crossing it."""
    wall = set(cells)
    seen = set()
    st = []
    for r in range(H):
        for c in range(W):
            if (r in (0, H - 1) or c in (0, W - 1)) and (r, c) not in wall:
                seen.add((r, c)); st.append((r, c))
    while st:
        y, x = st.pop()
        for dy, dx in nb_dual:
            p = (y + dy, x + dx)
            if 0 <= p[0] < H and 0 <= p[1] < W and p not in seen and p not in wall:
                seen.add(p); st.append(p)
    return {(r, c) for r in range(H) for c in range(W) if (r, c) not in seen and (r, c) not in wall}


def _levels(intervals):
    """Order-preserving compression: overlapping extents share a level, disjoint ones keep their order."""
    order = sorted(range(len(intervals)), key=lambda i: intervals[i])
    lev, cur, hi = [0] * len(intervals), -1, None
    for i in order:
        lo, h = intervals[i]
        if hi is None or lo > hi:
            cur += 1; hi = h
        else:
            hi = max(hi, h)
        lev[i] = cur
    return lev


def schematic_map(g, conn, margin):
    H, W = len(g), len(g[0])
    bg = Counter(v for row in g for v in row).most_common(1)[0][0]
    nb, nb_dual = (N4, N8) if conn == 4 else (N8, N4)
    comps = _components(g, bg, nb)
    if not comps:
        return None
    inter = [_interior(cs, H, W, nb_dual) for cs in comps]
    ring = [bool(I) for I in inter]
    # containment tree: parent = innermost enclosing stroke
    parent = []
    for j, cs in enumerate(comps):
        best = None
        for i in range(len(comps)):
            if i != j and ring[i] and cs[0] in inter[i]:
                if best is None or len(inter[i]) < len(inter[best]):
                    best = i
        parent.append(best)
    # one feature per dot, two (near/far edge) per ring, on each axis
    out_feats = []
    for axis in (0, 1):
        ivs, owner = [], []
        for k, cs in enumerate(comps):
            lo = min(p[axis] for p in cs); hi = max(p[axis] for p in cs)
            if ring[k]:
                ivs += [(lo, lo), (hi, hi)]; owner += [(k, 0), (k, 1)]
            else:
                ivs.append((lo, hi)); owner.append((k, 0))
        lv = _levels(ivs)
        pos = {o: 2 * l for o, l in zip(owner, lv)}
        # validity: each descendant strictly between its ancestors' edges
        for k in range(len(comps)):
            a = parent[k]
            while a is not None:
                inner = [pos[(k, 0)]] + ([pos[(k, 1)]] if ring[k] else [])
                if not all(pos[(a, 0)] < v < pos[(a, 1)] for v in inner):
                    return None
                a = parent[a]
        out_feats.append(pos)
    prow, pcol = out_feats
    # map extent: rings to their edges, dots with their margin
    rs, cs_ = [], []
    for k in range(len(comps)):
        if ring[k]:
            rs += [prow[(k, 0)], prow[(k, 1)]]; cs_ += [pcol[(k, 0)], pcol[(k, 1)]]
        else:
            rs += [prow[(k, 0)] - margin, prow[(k, 0)] + margin]
            cs_ += [pcol[(k, 0)] - margin, pcol[(k, 0)] + margin]
    r0, c0 = min(rs), min(cs_)
    out = [[bg] * (max(cs_) - c0 + 1) for _ in range(max(rs) - r0 + 1)]
    for k, cells in enumerate(comps):
        col = Counter(g[y][x] for y, x in cells).most_common(1)[0][0]
        if ring[k]:
            t, b = prow[(k, 0)] - r0, prow[(k, 1)] - r0
            l, rr = pcol[(k, 0)] - c0, pcol[(k, 1)] - c0
            for x in range(l, rr + 1):
                out[t][x] = col; out[b][x] = col
            for y in range(t, b + 1):
                out[y][l] = col; out[y][rr] = col
        else:
            y, x = prow[(k, 0)] - r0, pcol[(k, 0)] - c0
            if out[y][x] != bg:
                return None
            out[y][x] = col
    return out


def fam_schematic_map(train):
    for conn in (4, 8):
        for margin in (1, 0):
            fn = (lambda c, m: (lambda g: schematic_map(g, c, m)))(conn, margin)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("cartography:schematic_map[conn=%d,margin=%d]" % (conn, margin), 3, fn)
                return


FAMILIES = (fam_schematic_map,)
