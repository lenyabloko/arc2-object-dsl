CARD = "941d9a10"
READING = ("In the grid of cells cut by full separator lines, the top-left cell, the central cell and the "
           "bottom-right cell are filled with three fixed colours (learned from the examples).")


def _runs(n, seps):
    s = set(seps)
    out, cur = [], []
    for i in range(n):
        if i in s:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def _cells(g):
    H, W = len(g), len(g[0])
    for c in sorted({x for r in g for x in r}, reverse=True):
        rows = [i for i in range(H) if all(x == c for x in g[i])]
        cols = [j for j in range(W) if all(g[i][j] == c for i in range(H))]
        if rows and cols:
            return c, _runs(H, rows), _runs(W, cols)
    return None


def _pick(R, C):
    nr, nc = len(R), len(C)
    return [(0, 0), (nr // 2, nc // 2), (nr - 1, nc - 1)]


def _learn(train):
    cols = None
    for p in train:
        g, o = p["input"], p["output"]
        cs = _cells(g)
        if cs is None:
            return None
        _, R, C = cs
        got = []
        for (a, b) in _pick(R, C):
            v = {o[i][j] for i in R[a] for j in C[b]}
            if len(v) != 1:
                return None
            got.append(v.pop())
        if cols is None:
            cols = got
        elif cols != got:
            return None
    return cols


def fam(train):
    cols = _learn(train)
    if cols is None:
        return

    def fn(g):
        cs = _cells(g)
        out = [r[:] for r in g]
        if cs is None:
            return out
        _, R, C = cs
        for (a, b), v in zip(_pick(R, C), cols):
            for i in R[a]:
                for j in C[b]:
                    out[i][j] = v
        return out

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("corner_center_corner", 1, fn)


FAMILIES = [fam]
