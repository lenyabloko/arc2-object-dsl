"""Line family for card 17829a00 (test-blind; written from the reviewer's line and train pairs only).

Reading: some border lines of the grid are "edges" (a whole side painted one non-background
colour).  Every shape (single-colour connected component) whose colour equals an edge's colour is
pulled straight toward that edge, like iron to a magnet, and slides until it is attached: it
touches the edge, or (when blocked on the way) the shape it lands on.  Shapes of colours that no
edge has are left alone (or, as a declared alternative, erased).
"""
from collections import Counter

CARD = "17829a00"
LINE = "use the colored edges to attract the same-colored shapes until attached (like magnet)"
READING = {
    "generator": "Each shape whose colour matches a coloured border edge is moved rigidly, perpendicular "
                 "to that edge, toward it; the shape is redrawn at its new place and its old place becomes "
                 "background.",
    "stop": "A shape stops as soon as one more step would overlap something: it is then attached to the "
            "edge itself (adjacent to the edge line) or to a shape already attached in its path.",
    "params": "conn ∈ {8, 4} (shape connectivity) · block ∈ {stack, ghost} (stop on shapes in the path, or "
              "ignore them and slide to the edge) · other ∈ {keep, erase} (shapes whose colour no edge has) · "
              "two same-colour edges: the nearer one attracts",
    "participants": "Background = most frequent input colour. Edges: grid sides whose cells (corners aside) are "
                    "all one non-background colour. Shapes: single-colour connected components of the remaining "
                    "non-background cells; a shape is attracted by the edge of its own colour.",
    "preconditions": "Input and output have the same size; every training input has at least one coloured edge "
                     "and at least one shape of an edge's colour; the edges are unchanged in the output.",
}

D4 = ((-1, 0), (1, 0), (0, -1), (0, 1))
D8 = D4 + ((-1, -1), (-1, 1), (1, -1), (1, 1))
SIDES = (("T", (-1, 0)), ("B", (1, 0)), ("L", (0, -1)), ("R", (0, 1)))


def _bg(g):
    cnt = Counter(v for row in g for v in row)
    return max(sorted(cnt), key=lambda k: cnt[k])


def _side_cells(H, W, side, inner):
    """Cells of a border side; inner=True drops the two corners."""
    if side in ("T", "B"):
        r = 0 if side == "T" else H - 1
        cs = range(1, W - 1) if inner else range(W)
        return [(r, c) for c in cs]
    c = 0 if side == "L" else W - 1
    rs = range(1, H - 1) if inner else range(H)
    return [(r, c) for r in rs]


def _edges(g, bg):
    """List of (side, colour, direction) for border sides uniformly painted a non-background colour."""
    H, W = len(g), len(g[0])
    if H < 3 or W < 3:
        return []
    out = []
    for side, d in SIDES:
        vals = {g[r][c] for r, c in _side_cells(H, W, side, True)}
        if len(vals) == 1:
            col = vals.pop()
            if col != bg:
                out.append((side, col, d))
    return out


def _gap(cells, side, H, W):
    """Free steps between a shape and the edge line on `side`."""
    if side == "T":
        return min(r for r, _ in cells) - 1
    if side == "B":
        return (H - 2) - max(r for r, _ in cells)
    if side == "L":
        return min(c for _, c in cells) - 1
    return (W - 2) - max(c for _, c in cells)


def _shapes(g, bg, edge_cells, conn):
    H, W = len(g), len(g[0])
    nb = D8 if conn == 8 else D4
    seen = set(edge_cells)
    shapes = []
    for y in range(H):
        for x in range(W):
            if (y, x) in seen or g[y][x] == bg:
                continue
            col = g[y][x]
            st, pix = [(y, x)], []
            seen.add((y, x))
            while st:
                a, b = st.pop()
                pix.append((a, b))
                for dy, dx in nb:
                    p, q = a + dy, b + dx
                    if 0 <= p < H and 0 <= q < W and (p, q) not in seen and g[p][q] == col:
                        seen.add((p, q))
                        st.append((p, q))
            shapes.append((col, sorted(pix)))
    return shapes


def _apply(g, conn, block, other):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    edges = _edges(g, bg)
    if not edges:
        return None
    edge_cells = set()
    for side, _, _ in edges:
        edge_cells.update(_side_cells(H, W, side, False))
    shapes = _shapes(g, bg, edge_cells, conn)
    by_col = {}
    for side, col, d in edges:
        by_col.setdefault(col, []).append((side, d))
    movers, fixed = [], []
    for col, pix in shapes:
        if col in by_col:
            side, d = min(by_col[col], key=lambda e: (_gap(pix, e[0], H, W), "TBLR".index(e[0])))
            movers.append([col, pix, side, d])
        else:
            fixed.append((col, pix))
    if not movers:
        return None
    out = [[bg] * W for _ in range(H)]
    for r, c in edge_cells:
        out[r][c] = g[r][c]
    if other == "keep":
        for col, pix in fixed:
            for r, c in pix:
                out[r][c] = col
    if block == "ghost":
        movers.sort(key=lambda m: (-_gap(m[1], m[2], H, W), m[1][0]))
        for col, pix, side, (dr, dc) in movers:
            k = _gap(pix, side, H, W)
            for r, c in pix:
                out[r + k * dr][c + k * dc] = col
        return out
    # stack: occupancy map; nearest shapes slide first, passes repeat until nothing moves
    owner = {}
    for r, c in edge_cells:
        owner[(r, c)] = -1
    if other == "keep":
        for col, pix in fixed:
            for p in pix:
                owner[p] = -1
    for i, m in enumerate(movers):
        for p in m[1]:
            owner[p] = i
    moved = True
    while moved:
        moved = False
        order = sorted(range(len(movers)), key=lambda i: (_gap(movers[i][1], movers[i][2], H, W), movers[i][1][0]))
        for i in order:
            col, pix, side, (dr, dc) = movers[i]
            steps = 0
            while True:
                nxt = [(r + (steps + 1) * dr, c + (steps + 1) * dc) for r, c in pix]
                if all(0 <= r < H and 0 <= c < W and owner.get((r, c), i) == i for r, c in nxt):
                    steps += 1
                else:
                    break
            if steps:
                for p in pix:
                    del owner[p]
                pix = [(r + steps * dr, c + steps * dc) for r, c in pix]
                for p in pix:
                    owner[p] = i
                movers[i][1] = pix
                moved = True
    for col, pix, _, _ in movers:
        for r, c in pix:
            out[r][c] = col
    return out


def _make(conn, block, other):
    def fn(g):
        return _apply(g, conn, block, other)
    return fn


def _pre(train):
    if not train:
        return False
    for pr in train:
        gi, go = pr["input"], pr["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return False
        bg = _bg(gi)
        edges = _edges(gi, bg)
        if not edges:
            return False
        H, W = len(gi), len(gi[0])
        ecells = set()
        for side, _, _ in edges:
            ecells.update(_side_cells(H, W, side, False))
        if any(go[r][c] != gi[r][c] for r, c in ecells):
            return False
        cols = {col for _, col, _ in edges}
        if not any(gi[r][c] in cols for r in range(H) for c in range(W) if (r, c) not in ecells):
            return False
    return True


def fam(train):
    if not _pre(train):
        return
    cands = []
    cost = 0
    for conn in (8, 4):
        for block in ("stack", "ghost"):
            for other in ("keep", "erase"):
                cost += 1
                fn = _make(conn, block, other)
                hits, miss = 0, 0
                for pr in train:
                    try:
                        o = fn(pr["input"])
                    except Exception:
                        o = None
                    if o == pr["output"]:
                        hits += 1
                    elif o is None:
                        miss += len(pr["output"]) * len(pr["output"][0])
                    else:
                        miss += sum(a != b for ra, rb in zip(o, pr["output"]) for a, b in zip(ra, rb))
                cands.append((cost, "magnet_c%d_%s_%s" % (conn, block, other), fn, hits, miss))
    full = [c for c in cands if c[3] == len(train)]
    if full:
        for cost, name, fn, _, _ in full:
            yield name, cost, fn
        return
    # no setting reproduces every pair: offer the closest settings (most pairs, fewest wrong cells)
    best = max((c[3], -c[4]) for c in cands)
    for cost, name, fn, hits, miss in cands:
        if (hits, -miss) == best:
            yield name + "~partial", cost, fn


FAMILIES = [fam]
