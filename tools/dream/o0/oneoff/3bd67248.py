CARD = "3bd67248"
READING = ("With a full coloured line down the left edge, fill the bottom row to its right with one new colour "
           "and draw the anti-diagonal from the top-right corner down to just above that row in another.")


def _colors(g):
    s = set()
    for r in g:
        s.update(r)
    return s


def _make(row_col, diag_col):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [list(r) for r in g]
        for j in range(1, W):
            out[H - 1][j] = row_col
        for i in range(H - 1):
            j = W - 1 - i
            if 1 <= j < W:
                out[i][j] = diag_col
        return out
    return fn


def fam(train):
    news = None
    for p in train:
        n = _colors(p["output"]) - _colors(p["input"])
        news = n if news is None else news & n
    for a in sorted(news or ()):
        for b in sorted(news or ()):
            if a == b:
                continue
            fn = _make(a, b)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("bottom_row_%d_antidiag_%d" % (a, b), 1, fn)
FAMILIES = [fam]
