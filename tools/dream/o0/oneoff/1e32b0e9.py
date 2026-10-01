CARD = "1e32b0e9"
READING = "Separator lines split the grid into equal cells; the pattern in the template cell is stamped into every other cell, filling only its empty positions with the separator colour."

from collections import Counter


def _sep(g):
    H, W = len(g), len(g[0])
    best = None
    for c in set(v for row in g for v in row):
        rows = [r for r in range(H) if all(v == c for v in g[r])]
        cols = [x for x in range(W) if all(g[r][x] == c for r in range(H))]
        if rows or cols:
            n = len(rows) + len(cols)
            if best is None or n > best[0]:
                best = (n, c, rows, cols)
    return best


def _spans(n, lines):
    spans, start = [], 0
    for i in list(lines) + [n]:
        if i > start:
            spans.append((start, i))
        start = i + 1
    return spans


def _make(template_mode):
    def fn(g):
        H, W = len(g), len(g[0])
        s = _sep(g)
        out = [row[:] for row in g]
        if s is None:
            return out
        _, sc, rows, cols = s
        bg = Counter(v for row in g for v in row if v != sc).most_common(1)
        bg = bg[0][0] if bg else 0
        cells = [(r0, r1, c0, c1) for (r0, r1) in _spans(H, rows) for (c0, c1) in _spans(W, cols)]
        if not cells:
            return out
        h, w = cells[0][1] - cells[0][0], cells[0][3] - cells[0][2]
        cells = [b for b in cells if b[1] - b[0] == h and b[3] - b[2] == w]

        def mask(b):
            r0, _, c0, _ = b
            return {(i, j): g[r0 + i][c0 + j] for i in range(h) for j in range(w) if g[r0 + i][c0 + j] != bg}

        if template_mode == "first":
            tb = cells[0]
        else:
            tb = max(cells, key=lambda b: len(mask(b)))
        tm = mask(tb)
        for b in cells:
            if b == tb:
                continue
            r0, _, c0, _ = b
            for (i, j) in tm:
                if out[r0 + i][c0 + j] == bg:
                    out[r0 + i][c0 + j] = sc
        return out
    return fn


def fam(train):
    for name, cost, mode in (("stamp_first_cell", 1, "first"), ("stamp_fullest_cell", 2, "fullest")):
        fn = _make(mode)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
