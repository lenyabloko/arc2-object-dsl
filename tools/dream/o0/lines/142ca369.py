"""Line family for card 142ca369 (test-blind; induced only from train pairs).

Reading: every object is a single-colour 4-connected component.  An "outer corner" is an elbow cell of an
object: a cell whose in-object orthogonal neighbours are exactly two perpendicular ones (the vertex of an L,
the corner of a rectangle); bars and singletons have none.  From each outer corner a diagonal ray leaves
outward (away from both arms), painted in the object's colour.  The ray bounces off every flat surface it
touches (an input cell orthogonally ahead of it on one axis flips that axis), takes the colour of that
surface, and runs on until its next step would leave the grid.
"""
from collections import Counter

CARD = "142ca369"
LINE = ("from each outer corner shoot a diagonal laser ray of the same color witch bounces from every flat "
        "surface and acquires the surface color until it reaches the outer edge")
READING = {
    "generator": "From every outer corner (elbow cell) of every object, draw a diagonal ray pointing away from the "
                 "corner's two arms, in the object's colour; whenever the ray touches a flat surface of any input "
                 "object it bounces (the touched axis flips) and from that cell on it is drawn in the surface's colour.",
    "stop": "A ray stops when its next step would leave the grid (the outer edge); also on a repeated (cell, "
            "direction) state, on stepping into an object cell, or (corner=stop) on meeting a pointed corner head-on.",
    "params": "contact ∈ {side: bounce when an orthogonal neighbour ahead is a surface, ahead: bounce only when the "
              "next diagonal cell is blocked} · apex ∈ {new: the turning cell takes the surface colour, old} · "
              "corner ∈ {reverse, stop} (pointed corner met head-on, not a flat surface) · "
              "overlap ∈ {later ray wins, earlier ray wins}",
    "participants": "Objects = single-colour 4-connected components of non-background cells (background = most "
                    "frequent input colour). Emitters = elbow cells of objects (exactly two in-object orthogonal "
                    "neighbours, perpendicular); ray direction = minus the sum of the two arm offsets. Surfaces = "
                    "all non-background input cells; their colour is what the ray acquires.",
    "preconditions": "Input and output have the same size; every non-background input cell is unchanged; only "
                     "background cells change; every training input has at least one outer corner; and a setting "
                     "reproduces every training pair.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _bg(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _emitters(g, bg):
    """Elbow cells: (r, c, dr, dc, colour), sorted by position."""
    H, W = len(g), len(g[0])
    out = []
    for r in range(H):
        for c in range(W):
            col = g[r][c]
            if col == bg:
                continue
            nb = [(a, b) for a, b in D4 if 0 <= r + a < H and 0 <= c + b < W and g[r + a][c + b] == col]
            if len(nb) != 2:
                continue
            (a1, b1), (a2, b2) = nb
            if a1 * a2 + b1 * b2 != 0:          # collinear (middle of a bar)
                continue
            dr, dc = -(a1 + a2), -(b1 + b2)
            out.append((r, c, dr, dc, col))
    return out


def _trace(g, bg, r, c, dr, dc, col, contact, apex, corner):
    """Cells (r, c, colour) painted by one ray leaving cell (r, c) along (dr, dc)."""
    H, W = len(g), len(g[0])

    def wall(y, x):
        return 0 <= y < H and 0 <= x < W and g[y][x] != bg

    path = []
    seen = set()
    y, x = r + dr, c + dc
    while 0 <= y < H and 0 <= x < W and g[y][x] == bg and (y, x, dr, dc) not in seen:
        seen.add((y, x, dr, dc))
        old = col
        vw, hw = wall(y + dr, x), wall(y, x + dc)
        stop_here = False
        if contact == "side":
            if vw or hw:
                if vw:
                    col = g[y + dr][x]; dr = -dr
                if hw:
                    col = g[y][x + dc]; dc = -dc
            elif wall(y + dr, x + dc):
                if corner == "reverse":
                    col = g[y + dr][x + dc]; dr, dc = -dr, -dc
                else:
                    stop_here = True
        else:  # ahead: classic billiard, bounce only when the next diagonal cell is blocked
            if wall(y + dr, x + dc):
                if vw and not hw:
                    col = g[y + dr][x]; dr = -dr
                elif hw and not vw:
                    col = g[y][x + dc]; dc = -dc
                elif vw and hw:
                    col = g[y + dr][x + dc]; dr, dc = -dr, -dc
                elif corner == "reverse":
                    col = g[y + dr][x + dc]; dr, dc = -dr, -dc
                else:
                    stop_here = True
        path.append((y, x, col if apex == "new" else old))
        if stop_here:
            break
        y, x = y + dr, x + dc
    return path


def _apply(g, contact, apex, corner, overlap):
    bg = _bg(g)
    out = [row[:] for row in g]
    em = _emitters(g, bg)
    if overlap == "first":
        em = em[::-1]
    for r, c, dr, dc, col in em:
        for y, x, k in _trace(g, bg, r, c, dr, dc, col, contact, apex, corner):
            out[y][x] = k
    return out


def _make(contact, apex, corner, overlap):
    def fn(grid):
        return _apply([list(r) for r in grid], contact, apex, corner, overlap)
    return fn


def fam(train):
    if not train:
        return
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if not gi or len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        bg = _bg(gi)
        changed = False
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != b:
                    if a != bg:
                        return                  # objects are never altered
                    changed = True
        if not changed or not _emitters(gi, bg):
            return
    settings = []
    for contact, c1 in (("side", 0), ("ahead", 2)):
        for apex, c2 in (("new", 0), ("old", 1)):
            for corner, c3 in (("reverse", 0), ("stop", 1)):
                for overlap, c4 in (("last", 0), ("first", 1)):
                    settings.append((10 + c1 + c2 + c3 + c4, contact, apex, corner, overlap))
    settings.sort(key=lambda s: s[0])
    for cost, contact, apex, corner, overlap in settings:
        fn = _make(contact, apex, corner, overlap)
        try:
            outs = [fn(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        name = "laser_bounce[contact=%s,apex=%s,corner=%s,overlap=%s]" % (contact, apex, corner, overlap)
        yield name, cost, fn


FAMILIES = [fam]
