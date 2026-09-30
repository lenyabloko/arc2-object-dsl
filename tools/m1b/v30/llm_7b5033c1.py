"""Family for 7b5033c1 -- geometry:rectification.

Concept: curve rectification (straightening a curve into a segment of the same arc length).
The foreground cells form one simple 4-connected curve on a uniform background; the curve is
traced from one endpoint to the other and laid out straight, so the output is a 1-cell-wide
strip whose k-th cell has the colour of the k-th cell along the curve.

Induced parameters (small declared finite domains):
  start  in START_RULES  -- which endpoint the arc-length parameter starts from
  layout in LAYOUTS      -- the straightened curve as a column or as a row
Background = most frequent colour of each input (role, not a number).
"""
from collections import Counter

START_RULES = ('reading_first', 'reading_last', 'column_first', 'column_last')
LAYOUTS = ('column', 'row')


def _background(g):
    return Counter(v for r in g for v in r).most_common(1)[0][0]


def _trace(g):
    """Return the list of cells of the single simple 4-connected curve, or None."""
    bg = _background(g)
    H, W = len(g), len(g[0])
    cells = {(r, c) for r in range(H) for c in range(W) if g[r][c] != bg}
    if not cells:
        return None

    def nbrs(p):
        r, c = p
        return [q for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)) if q in cells]

    deg = {p: len(nbrs(p)) for p in cells}
    if len(cells) == 1:
        return [next(iter(cells))], [next(iter(cells))]
    if any(d == 0 or d > 2 for d in deg.values()):
        return None
    ends = [p for p in cells if deg[p] == 1]
    if len(ends) != 2:
        return None
    return cells, ends


def _walk(cells, start):
    path, prev, cur = [start], None, start
    while True:
        r, c = cur
        nxt = [q for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)) if q in cells and q != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
        path.append(cur)
    return path if len(path) == len(cells) else None


def _choose(ends, rule):
    if rule == 'reading_first':
        return min(ends)
    if rule == 'reading_last':
        return max(ends)
    if rule == 'column_first':
        return min(ends, key=lambda p: (p[1], p[0]))
    return max(ends, key=lambda p: (p[1], p[0]))


def _rectify(g, rule, layout):
    t = _trace(g)
    if t is None:
        return None
    cells, ends = t
    if isinstance(cells, list):          # single-cell curve
        path = cells
    else:
        path = _walk(cells, _choose(ends, rule))
        if path is None:
            return None
    colours = [g[r][c] for r, c in path]
    return [[v] for v in colours] if layout == 'column' else [colours]


def fam_rectification(train):
    for rule in START_RULES:
        for layout in LAYOUTS:
            fn = (lambda rule, layout: lambda g: _rectify(g, rule, layout))(rule, layout)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("geometry:rectification[start=%s,layout=%s]" % (rule, layout), 3, fn)
                return


FAMILIES = (fam_rectification,)
