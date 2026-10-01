CARD = "7d419a02"
READING = ("The grid is striped into bands by empty lines and holds one marker block; every "
           "body cell outside the marker's band whose distance along the band (in marker-sized "
           "steps) is at least its band distance from the marker is recoloured, giving two "
           "diagonal cones running along the bands.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _counts(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return cnt


def _row_bands(g, bg):
    """Return band index per row (None for separator rows)."""
    idx, b, prev_sep = [], -1, True
    for row in g:
        sep = all(v == bg for v in row)
        if sep:
            idx.append(None)
        else:
            if prev_sep:
                b += 1
            idx.append(b)
        prev_sep = sep
    return idx


def _has_interior_sep(g, bg):
    H = len(g)
    return any(all(v == bg for v in g[r]) for r in range(1, H - 1)) and any(
        not all(v == bg for v in g[r]) for r in range(H))


def _make(bg, paint, rel):
    def solve_rows(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        cols = sorted((k for k in cnt if k != bg), key=lambda k: -cnt[k])
        if len(cols) != 2:
            return None
        body, mark = cols
        mcells = [(r, c) for r in range(H) for c in range(W) if g[r][c] == mark]
        bands = _row_bands(g, bg)
        mb = set(bands[r] for r, _ in mcells)
        if len(mb) != 1 or None in mb:
            return None
        mb = mb.pop()
        c0 = min(c for _, c in mcells)
        c1 = max(c for _, c in mcells)
        s = c1 - c0 + 1
        out = [row[:] for row in g]
        for r in range(H):
            if bands[r] is None:
                continue
            bd = abs(bands[r] - mb)
            for c in range(W):
                if g[r][c] != body:
                    continue
                d = c0 - c if c < c0 else (c - c1 if c > c1 else 0)
                au = (d + s - 1) // s
                if rel(au, bd):
                    out[r][c] = paint
        return out

    def fn(g):
        g = [list(r) for r in g]
        if _has_interior_sep(g, bg):
            return solve_rows(g)
        t = _T(g)
        if _has_interior_sep(t, bg):
            o = solve_rows(t)
            return None if o is None else _T(o)
        return None
    return fn


_RELS = (
    ("cone_ge", 1, lambda au, bd: bd >= 1 and au >= bd),
    ("cone_gt", 2, lambda au, bd: bd >= 1 and au > bd),
    ("cone_ge_incl0", 3, lambda au, bd: au >= bd and au >= 1),
)


def fam(train):
    changes = set()
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return
        for ra, rb in zip(a, b):
            for x, y in zip(ra, rb):
                if x != y:
                    changes.add(y)
    if len(changes) != 1:
        return
    paint = changes.pop()
    for bg in (0,) + tuple(k for k in range(1, 10)):
        for name, cost, rel in _RELS:
            fn = _make(bg, paint, rel)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("%s_bg%d" % (name, bg), cost + (0 if bg == 0 else 5), fn)
            except Exception:
                pass


FAMILIES = [fam]
