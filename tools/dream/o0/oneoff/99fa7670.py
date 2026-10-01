CARD = "99fa7670"
READING = ("Each coloured cell shoots a ray of its colour rightwards to the edge and then down "
           "the right edge, stopping just above the row of the next coloured cell (or at the bottom).")


def _make(bg):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [list(r) for r in g]
        pts = sorted((i, j, g[i][j]) for i in range(H) for j in range(W) if g[i][j] != bg)
        for k, (i, j, c) in enumerate(pts):
            for x in range(j, W):
                out[i][x] = c
            end = pts[k + 1][0] if k + 1 < len(pts) else H
            for y in range(i + 1, end):
                out[y][W - 1] = c
        return out
    return fn


def fam(train):
    fn = _make(0)
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("ray_right_then_down", 1, fn)


FAMILIES = [fam]
