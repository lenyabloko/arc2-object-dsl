CARD = "7ec998c9"
READING = "From the lone odd pixel, draw a new-colour path along the top edge from one corner to its column, down that column (skipping the pixel), and along the bottom edge to the opposite corner, the starting corner chosen by the pixel's checkerboard parity."

from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _dot(g, bg):
    cells = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]
    return cells[0] if len(cells) == 1 else None


_PREDS = [
    ("sumpar", 1, lambda r, c, H, W: (r + c) % 2),
    ("rowpar", 2, lambda r, c, H, W: r % 2),
    ("colpar", 2, lambda r, c, H, W: c % 2),
    ("diag", 3, lambda r, c, H, W: int(r == c)),
    ("left", 3, lambda r, c, H, W: int(2 * c < W - 1)),
]


def _draw(g, ink, left_start):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    d = _dot(g, bg)
    out = [row[:] for row in g]
    if d is None:
        return out
    r0, c0 = d
    top = range(0, c0 + 1) if left_start else range(c0, W)
    bot = range(c0, W) if left_start else range(0, c0 + 1)
    for c in top:
        if out[0][c] == bg:
            out[0][c] = ink
    for c in bot:
        if out[H - 1][c] == bg:
            out[H - 1][c] = ink
    for r in range(H):
        if out[r][c0] == bg:
            out[r][c0] = ink
    return out


def _ink(train):
    inks = set()
    for p in train:
        a = set(v for row in p["input"] for v in row)
        b = set(v for row in p["output"] for v in row)
        inks |= (b - a)
    return inks.pop() if len(inks) == 1 else None


def fam(train):
    ink = _ink(train)
    if ink is None:
        return
    for pname, cost, pred in _PREDS:
        for pol in (0, 1):
            def fn(g, pred=pred, pol=pol):
                H, W = len(g), len(g[0])
                d = _dot(g, _bg(g))
                if d is None:
                    return [row[:] for row in g]
                return _draw(g, ink, pred(d[0], d[1], H, W) != pol)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("zpath_" + pname + str(pol), cost, fn)
            except Exception:
                pass


FAMILIES = [fam]
