CARD = "0a938d79"
READING = "Two seed pixels mark positions along the grid's long axis; draw full-width lines of their colours at those positions and keep repeating the pair with the same spacing until the edge."


def _cells(g):
    return [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != 0]


def _make(axis_mode):
    def fn(g):
        H, W = len(g), len(g[0])
        cells = _cells(g)
        if len(cells) != 2:
            return [row[:] for row in g]
        if axis_mode == "long":
            cols = W >= H
        else:
            cols = axis_mode == "cols"
        # position along the long axis
        key = (lambda t: t[1]) if cols else (lambda t: t[0])
        cells.sort(key=key)
        (a, b) = cells
        p1, p2 = key(a), key(b)
        d = p2 - p1
        out = [[0] * W for _ in range(H)]
        n = W if cols else H
        if d <= 0:
            return [row[:] for row in g]
        k = 0
        while True:
            pos = p1 + k * d
            if pos >= n:
                break
            col = a[2] if k % 2 == 0 else b[2]
            if cols:
                for r in range(H):
                    out[r][pos] = col
            else:
                for c in range(W):
                    out[pos][c] = col
            k += 1
        return out
    return fn


def fam(train):
    for name, cost, mode in (("long_axis_stripes", 1, "long"),
                             ("col_stripes", 2, "cols"),
                             ("row_stripes", 2, "rows")):
        fn = _make(mode)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
