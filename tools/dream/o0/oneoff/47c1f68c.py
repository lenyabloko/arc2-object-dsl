CARD = "47c1f68c"
READING = ("A full-length cross of one colour splits the grid; the shape in the occupied quadrant is "
           "recoloured to the cross colour and mirrored into all four quadrants of a grid without the cross.")


def _cross(g):
    H, W = len(g), len(g[0])
    rows = [i for i in range(H) if g[i][0] != 0 and all(x == g[i][0] for x in g[i])]
    cols = [j for j in range(W) if g[0][j] != 0 and all(g[i][j] == g[0][j] for i in range(H))]
    for r in rows:
        for c in cols:
            if g[r][0] == g[0][c]:
                return r, c, g[r][0]
    return None


def _make(recolor):
    def fn(g):
        H, W = len(g), len(g[0])
        r, c, col = _cross(g)
        quads = [(0, r, 0, c), (0, r, c + 1, W), (r + 1, H, 0, c), (r + 1, H, c + 1, W)]
        best = None
        for qi, (a, b, d, e) in enumerate(quads):
            q = [g[i][d:e] for i in range(a, b)]
            n = sum(1 for row in q for x in row if x != 0)
            if q and q[0] and (best is None or n > best[0]):
                best = (n, qi, q)
        _, qi, q = best
        if qi in (1, 3):
            q = [row[::-1] for row in q]
        if qi in (2, 3):
            q = q[::-1]
        if recolor:
            q = [[col if x != 0 else 0 for x in row] for row in q]
        top = [row + row[::-1] for row in q]
        return top + top[::-1]
    return fn


def fam(train):
    for name, rc in (("cross_quadrant_mirror_recolor", True), ("cross_quadrant_mirror", False)):
        fn = _make(rc)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
