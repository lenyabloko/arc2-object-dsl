"""Line family for card 52df9849 -- reviewer (Len): "reverse order of occlusion: what was occluded becomes visible and vise versa".

Reading: the input is a stack of solid shapes on a background; where two shapes overlap only the front one shows.
Every shape is completed to its full extent (the hidden part it has under the shapes in front of it), the
front-to-back order read off the overlaps is reversed, and the stack is repainted: on every overlap cell the shape
that used to be hidden now shows and the one that used to show is now hidden.
Shape completion uses the simplest model that hides only foreground cells (never background):
  rect   the shape's bounding box                       (solid rectangles, bars, full-width bands)
  hull   the lattice points of its convex hull          (straight lines in any of the 8 directions, triangles,
                                                          other convex blobs)
  as-is  its visible cells only                         (nothing can be said about what it hides)
No coordinates, sizes, colours or counts are constants: the background is the grid's most common colour, a shape is
all cells of one colour inside one 8-connected foreground blob, and the order is read per grid from the overlaps.
"""
from collections import Counter

CARD = "52df9849"
LINE = "reverse order of occlusion: what was occluded becomes visible and vise versa"
READING = {
    "generator": "Each solid shape is completed to its full extent (bounding rectangle, else convex hull, so hidden "
                 "parts of bars, rectangles, lines and triangles are restored), the front-to-back order read off "
                 "the overlaps is reversed, and every overlap cell is repainted with the shape that is now in front "
                 "(the formerly hidden one).",
    "stop": "Each overlap cell is repainted once; cells covered by a single shape and background cells never change.",
    "params": "completion ∈ {rect, hull, as-is}, chosen per shape as the first model whose hidden cells are all "
              "foreground · order = reversed topological order of the 'shows over' relation (per-cell swap of the "
              "two shapes when the relation is cyclic) · background = most common colour, per grid",
    "participants": "Background: most common colour. Shapes: for each 8-connected blob of non-background cells, the "
                    "cells of each colour in it form one shape (fragments split by an occluder stay one shape). "
                    "Occluders: the shape whose colour is visible on a cell lying inside another shape's completed "
                    "extent.",
    "preconditions": "Output has the input's shape; every training input contains at least one overlap (a cell "
                     "inside the completed extent of a shape of a different colour), so there is an order to reverse.",
}


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _blobs(g, bg):
    """8-connected components of non-background cells -> list of lists of (r, c)."""
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] == bg or seen[r][c]:
                continue
            comp, st = [], [(r, c)]
            seen[r][c] = True
            while st:
                y, x = st.pop()
                comp.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < H and 0 <= nx < W and not seen[ny][nx] and g[ny][nx] != bg:
                            seen[ny][nx] = True
                            st.append((ny, nx))
            out.append(comp)
    return out


def _cross(o, a, b):
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _hull(pts):
    """Monotone-chain convex hull (counter-clockwise, no collinear points)."""
    pts = sorted(set(pts))
    if len(pts) <= 2:
        return pts
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and _cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and _cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _in_hull(h, p):
    if len(h) == 1:
        return p == h[0]
    if len(h) == 2:
        a, b = h
        return (_cross(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                and min(a[1], b[1]) <= p[1] <= max(a[1], b[1]))
    n = len(h)
    return all(_cross(h[i], h[(i + 1) % n], p) >= 0 for i in range(n))


def _extent(g, bg, cells):
    """Completed extent of a shape: first of rect / hull whose extra cells are all foreground, else the cells."""
    r0 = min(r for r, _ in cells); r1 = max(r for r, _ in cells)
    c0 = min(c for _, c in cells); c1 = max(c for _, c in cells)
    box = [(r, c) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
    if all(g[r][c] != bg for r, c in box):
        return set(box)
    h = _hull(cells)
    ext = [p for p in box if _in_hull(h, p)]
    if all(g[r][c] != bg for r, c in ext):
        return set(ext)
    return set(cells)


def _parse(g):
    """-> (bg, shapes {sid: colour}, cover {cell: [sid,...]}, above set of (front, back))."""
    bg = _bg(g)
    shapes, cover, above = {}, {}, set()
    for b, comp in enumerate(_blobs(g, bg)):
        by_col = {}
        for r, c in comp:
            by_col.setdefault(g[r][c], []).append((r, c))
        for col in sorted(by_col):
            sid = (b, col)
            shapes[sid] = col
            for p in _extent(g, bg, by_col[col]):
                cover.setdefault(p, []).append(sid)
    for (r, c), sids in cover.items():
        if len(sids) < 2:
            continue
        vis = [s for s in sids if shapes[s] == g[r][c]]
        if len(vis) != 1:
            continue
        for s in sids:
            if s != vis[0]:
                above.add((vis[0], s))
    return bg, shapes, cover, above


def _topo(shapes, above):
    """Front-to-back rank (0 = front) or None when the relation is cyclic; ties broken by shape id."""
    indeg = {s: 0 for s in shapes}
    succ = {s: [] for s in shapes}
    for a, b in above:
        succ[a].append(b)
        indeg[b] += 1
    ready = sorted(s for s in shapes if indeg[s] == 0)
    rank = {}
    while ready:
        s = ready.pop(0)
        rank[s] = len(rank)
        for t in succ[s]:
            indeg[t] -= 1
            if indeg[t] == 0:
                ready.append(t)
        ready.sort()
    return rank if len(rank) == len(shapes) else None


def reverse_occlusion(grid):
    g = [list(r) for r in grid]
    if not g or not g[0]:
        return g
    bg, shapes, cover, above = _parse(g)
    rank = _topo(shapes, above)
    out = [list(r) for r in g]
    for (r, c), sids in cover.items():
        if len(sids) < 2:
            continue
        if rank is not None:
            new = max(sids, key=lambda s: rank[s])            # the backmost shape comes to the front
        elif len(sids) == 2:
            vis = [s for s in sids if shapes[s] == g[r][c]]
            if len(vis) != 1:
                continue
            new = sids[0] if sids[1] == vis[0] else sids[1]   # woven pair: swap on this cell
        else:
            continue
        out[r][c] = shapes[new]
    return out


def _shape(g):
    return (len(g), len(g[0]) if g else 0)


def fam(train):
    if not train or any(not p["input"] or not p["input"][0] or _shape(p["input"]) != _shape(p["output"])
                        for p in train):
        return
    try:
        if any(not _parse(p["input"])[3] for p in train):
            return
        ok = all(reverse_occlusion(p["input"]) == p["output"] for p in train)
    except Exception:
        ok = False
    if ok:
        yield ("reverse_occlusion[completion=rect>hull>as-is]", 3, reverse_occlusion)


FAMILIES = [fam]
