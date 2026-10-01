CARD = "a644e277"
READING = ("The grid is ruled by lines of one colour; the few line intersections that break the line colour "
           "mark the corners of a rectangle, and the output is that rectangle cropped out.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _lines(g, frac):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    best = None
    for L in set(x for r in g for x in r):
        if L == bg:
            continue
        rows = [r for r in range(H) if sum(1 for x in g[r] if x == L) > frac * W]
        cols = [c for c in range(W) if sum(1 for r in range(H) if g[r][c] == L) > frac * H]
        if rows and cols:
            sc = len(rows) + len(cols)
            if best is None or sc > best[0]:
                best = (sc, L, rows, cols)
    return best


def _make(frac):
    def fn(g):
        b = _lines(g, frac)
        if b is None:
            return None
        _, L, rows, cols = b
        holes = [(r, c) for r in rows for c in cols if g[r][c] != L]
        if len(holes) < 2:
            return None
        r0 = min(r for r, c in holes); r1 = max(r for r, c in holes)
        c0 = min(c for r, c in holes); c1 = max(c for r, c in holes)
        return [list(g[r][c0:c1 + 1]) for r in range(r0, r1 + 1)]
    return fn


def fam(train):
    for frac in (0.5, 0.7):
        fn = _make(frac)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("crop_line_holes_%s" % frac, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
