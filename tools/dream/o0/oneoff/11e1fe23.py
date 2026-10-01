CARD = "11e1fe23"
READING = "Three pixels are corners of a rectangle; mark its centre with a new colour and place a copy of each corner pixel diagonally adjacent to the centre on that corner's side."


def _new_colour(train):
    new = set()
    for p in train:
        ins = {v for row in p["input"] for v in row}
        outs = {v for row in p["output"] for v in row}
        new |= outs - ins
    return new.pop() if len(new) == 1 else None


def _sgn(x):
    return (x > 0) - (x < 0)


def _make(centre_col, dist):
    def fn(g):
        H, W = len(g), len(g[0])
        cells = [(r, c, g[r][c]) for r in range(H) for c in range(W) if g[r][c] != 0]
        out = [row[:] for row in g]
        if not cells:
            return out
        rs = [t[0] for t in cells]
        cs = [t[1] for t in cells]
        r0, r1, c0, c1 = min(rs), max(rs), min(cs), max(cs)
        cr, cc = (r0 + r1) // 2, (c0 + c1) // 2
        if centre_col is not None:
            out[cr][cc] = centre_col
        for r, c, v in cells:
            y, x = cr + dist * _sgn(r - cr), cc + dist * _sgn(c - cc)
            if 0 <= y < H and 0 <= x < W:
                out[y][x] = v
        return out
    return fn


def fam(train):
    nc = _new_colour(train)
    for dist in (1, 2):
        fn = _make(nc, dist)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("rect_centre_pull_corners_d%d" % dist, dist, fn)
        except Exception:
            pass


FAMILIES = [fam]
