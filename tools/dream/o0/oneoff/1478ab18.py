CARD = "1478ab18"
READING = "The marker dots occupy three corners of a square plus one interior point; draw, in the fill colour, the right triangle formed by the missing corner, its two adjacent corners and the diagonal joining them (keeping the dots)."

from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _line(p, q):
    (y0, x0), (y1, x1) = p, q
    n = max(abs(y1 - y0), abs(x1 - x0))
    if n == 0:
        return [p]
    pts = []
    for k in range(n + 1):
        pts.append((y0 + round(k * (y1 - y0) / n), x0 + round(k * (x1 - x0) / n)))
    return pts


def _make(fill, require_square):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        dots = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
        o = [row[:] for row in g]
        if not dots:
            return o
        r0 = min(r for r, _ in dots); r1 = max(r for r, _ in dots)
        c0 = min(c for _, c in dots); c1 = max(c for _, c in dots)
        if require_square and (r1 - r0) != (c1 - c0):
            return o
        corners = [(r0, c0), (r0, c1), (r1, c0), (r1, c1)]
        missing = [p for p in corners if g[p[0]][p[1]] == bg]
        if len(missing) != 1:
            return o
        m = missing[0]
        a = (m[0], c1 if m[1] == c0 else c0)  # same row
        b = (r1 if m[0] == r0 else r0, m[1])  # same column
        for p, q in ((m, a), (m, b), (a, b)):
            for y, x in _line(p, q):
                if o[y][x] == bg:
                    o[y][x] = fill
        return o
    return fn


def _fills(train):
    fs = set()
    for p in train:
        a, b = p["input"], p["output"]
        for r in range(len(a)):
            for c in range(len(a[0])):
                if a[r][c] != b[r][c]:
                    fs.add(b[r][c])
    return sorted(fs)


def fam(train):
    for fill in _fills(train):
        for sq, cost in ((True, 1), (False, 2)):
            fn = _make(fill, sq)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("missing_corner_triangle_f%d%s" % (fill, "" if sq else "_rect"), cost, fn)
            except Exception:
                pass


FAMILIES = [fam]
