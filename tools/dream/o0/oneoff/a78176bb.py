CARD = "a78176bb"
READING = ("The filler triangles attached to the full diagonal line are erased, and on each side that "
           "had filler a new full line parallel to the diagonal is drawn just beyond the triangle's "
           "farthest cell (gap induced from training).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _parse(g):
    """Find line colour, orientation (+1: r-c const, -1: r+c const), line index, filler colour."""
    bg = _bg(g)
    H, W = len(g), len(g[0])
    cols = {}
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg:
                cols.setdefault(g[r][c], []).append((r, c))
    best = None
    for col, cells in cols.items():
        for orient in (1, -1):
            keys = {(r - c) if orient == 1 else (r + c) for r, c in cells}
            if len(keys) == 1:
                k = keys.pop()
                sc = len(cells)
                if best is None or sc > best[0]:
                    best = (sc, col, orient, k)
    if best is None:
        return None
    _, lcol, orient, k = best
    fill = [(r, c) for col, cells in cols.items() if col != lcol for r, c in cells]
    return bg, lcol, orient, k, fill


def _apply(g, gap):
    p = _parse(g)
    if p is None:
        return None
    bg, lcol, orient, k, fill = p
    H, W = len(g), len(g[0])
    key = (lambda r, c: r - c) if orient == 1 else (lambda r, c: r + c)
    lo = hi = None
    for r, c in fill:
        d = key(r, c) - k
        if d > 0:
            hi = d if hi is None else max(hi, d)
        elif d < 0:
            lo = d if lo is None else min(lo, d)
    targets = {k}
    if hi is not None:
        targets.add(k + hi + gap)
    if lo is not None:
        targets.add(k + lo - gap)
    out = [[bg] * W for _ in range(H)]
    for r in range(H):
        for c in range(W):
            if key(r, c) in targets:
                out[r][c] = lcol
    return out


def fam(train):
    for gap in (2, 1, 3):
        def fn(g, gap=gap):
            r = _apply(g, gap)
            return r if r is not None else [list(x) for x in g]

        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("diag_parallel_gap%d" % gap, 1, fn)
            return


FAMILIES = [fam]
