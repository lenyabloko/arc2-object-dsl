"""Line family for card ca8de6ea (test-blind; written from the reviewer's line and train pairs only).

Reading: the input holds one sparse shape (every non-background cell) spread over a larger grid with
empty cells between its pixels. "Compactify" squeezes the empty space out so the coloured cells pack
edge to edge into a square, keeping their relative order: first try deleting whole empty rows and
columns; failing that, slide cells together along rows (or columns); failing that, pack the cells by
rank -- the k*k cells, taken top-to-bottom, fill the square row by row, each output row keeping its
cells in their left-to-right order (or the transposed rule).
"""

from math import isqrt

CARD = "ca8de6ea"
LINE = "compactify(remove empty space) shape into square"
READING = {
    "generator": "Take every non-background cell of the shape and squeeze out the empty cells between "
                 "them so they pack edge to edge into a square: the n cells, in top-to-bottom order, fill "
                 "a sqrt(n) x sqrt(n) square row by row, and inside each row they keep their original "
                 "left-to-right order (cheaper squeezes -- deleting empty rows/columns, or sliding cells "
                 "together along one axis -- are tried first).",
    "stop": "Stops when the coloured cells touch with no empty cell left; the output is the square of side "
            "sqrt(n) for n coloured cells (side ceil(sqrt(n)), padded with background at the end, if n is "
            "not a perfect square), or the shape's grid once its empty rows/columns are gone.",
    "params": "squeeze in {drop_empty_lines, slide_rows, slide_cols, rank_rows, rank_cols} "
              "(tried in that order) . bg = most frequent input colour",
    "participants": "The shape: all cells whose colour differs from the background (most frequent colour "
                    "of the input); each keeps its own colour; no other objects take part.",
    "preconditions": "Each input has at least one non-background cell and some empty (background) cell "
                     "inside the shape's bounding box; every training output is a square (or the input "
                     "grid with only its empty rows/columns removed).",
}


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _cells(g, bg):
    return [(r, c, v) for r, row in enumerate(g) for c, v in enumerate(row) if v != bg]


def _transpose(g):
    return [list(t) for t in zip(*g)]


def _drop_empty_lines(g):
    bg = _bg(g)
    rows = [r for r, row in enumerate(g) if any(v != bg for v in row)]
    cols = [c for c in range(len(g[0])) if any(g[r][c] != bg for r in range(len(g)))]
    if not rows or not cols:
        return None
    return [[g[r][c] for c in cols] for r in rows]


def _slide_rows(g):
    """In every row squeeze out the empty cells (cells close up to the left, order kept), then drop
    empty rows; ragged rows are right-padded with background."""
    bg = _bg(g)
    rows = [[v for v in row if v != bg] for row in g]
    rows = [r for r in rows if r]
    if not rows:
        return None
    w = max(len(r) for r in rows)
    return [r + [bg] * (w - len(r)) for r in rows]


def _slide_cols(g):
    out = _slide_rows(_transpose(g))
    return None if out is None else _transpose(out)


def _rank_rows(g):
    """n coloured cells -> side s = ceil(sqrt(n)); cells taken in row-major order are cut into runs of
    s, run i becomes output row i, and inside a run cells are ordered by their original column."""
    bg = _bg(g)
    cells = _cells(g, bg)
    n = len(cells)
    if n == 0:
        return None
    s = isqrt(n)
    if s * s < n:
        s += 1
    cells.sort(key=lambda t: (t[0], t[1]))
    out = []
    for i in range(s):
        run = sorted(cells[i * s:(i + 1) * s], key=lambda t: (t[1], t[0]))
        row = [v for _, _, v in run]
        out.append(row + [bg] * (s - len(row)))
    return out


def _rank_cols(g):
    return _transpose(_rank_rows(_transpose(g)))


SQUEEZES = (
    ("drop_empty_lines", 1, _drop_empty_lines),
    ("slide_rows", 2, _slide_rows),
    ("slide_cols", 2, _slide_cols),
    ("rank_rows", 3, _rank_rows),
    ("rank_cols", 3, _rank_cols),
)


def _pre(g):
    if not g or not g[0]:
        return False
    bg = _bg(g)
    cells = _cells(g, bg)
    if not cells:
        return False
    r0 = min(t[0] for t in cells); r1 = max(t[0] for t in cells)
    c0 = min(t[1] for t in cells); c1 = max(t[1] for t in cells)
    return len(cells) < (r1 - r0 + 1) * (c1 - c0 + 1)          # some empty space to remove


def fam(train):
    if not train or not all(_pre(p["input"]) for p in train):
        return
    seen = set()
    for name, cost, f in SQUEEZES:
        try:
            outs = [f(p["input"]) for p in train]
        except Exception:
            continue
        if any(o != p["output"] for o, p in zip(outs, train)):
            continue
        if not all(len(o) == len(o[0]) for o in outs) and name != "drop_empty_lines":
            continue                                            # "into square"
        sig = repr(outs)
        if sig in seen:
            continue
        seen.add(sig)
        yield "compactify[squeeze=%s]" % name, cost, f


FAMILIES = [fam]
