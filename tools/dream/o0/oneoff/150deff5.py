CARD = "150deff5"
READING = "Tile the single blob exactly with 2x2 squares and straight 1x3 bars, colouring squares with one colour and bars with another (piece shapes and colours chosen to fit training)."

from collections import Counter


def _bg(g):
    return Counter(v for row in g for v in row).most_common(1)[0][0]


def _bar(n):
    h = frozenset((0, i) for i in range(n))
    v = frozenset((i, 0) for i in range(n))
    return [h, v]


SHAPES = {
    "sq2": [frozenset({(0, 0), (0, 1), (1, 0), (1, 1)})],
    "bar3": _bar(3),
    "bar2": _bar(2),
    "bar4": _bar(4),
}


def _tile(cells, pieces, budget=200000):
    """pieces: list of (colour, [orientations]) in trial order. Returns {cell: colour} or None."""
    order = sorted(cells)
    placements = []
    for col, orients in pieces:
        for o in orients:
            anchor = min(o)
            placements.append((col, [(dy - anchor[0], dx - anchor[1]) for dy, dx in o]))
    assign = {}
    cnt = [budget]

    def rec(i):
        cnt[0] -= 1
        if cnt[0] < 0:
            return False
        while i < len(order) and order[i] in assign:
            i += 1
        if i == len(order):
            return True
        y, x = order[i]
        for col, offs in placements:
            pts = [(y + dy, x + dx) for dy, dx in offs]
            if all(p in cells and p not in assign for p in pts):
                for p in pts:
                    assign[p] = col
                if rec(i + 1):
                    return True
                for p in pts:
                    del assign[p]
        return False

    if rec(0):
        return dict(assign)
    return None


def _make(pieces):
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        cells = set((r, c) for r in range(H) for c in range(W) if g[r][c] != bg)
        res = _tile(cells, pieces)
        o = [row[:] for row in g]
        if res is None:
            return o
        for (r, c), col in res.items():
            o[r][c] = col
        return o
    return fn


def _out_colours(train):
    cs = set()
    for p in train:
        a, b = p["input"], p["output"]
        bg = _bg(a)
        for r in range(len(a)):
            for c in range(len(a[0])):
                if a[r][c] != bg:
                    cs.add(b[r][c])
    return sorted(cs)


def fam(train):
    cols = _out_colours(train)
    if len(cols) != 2:
        return
    names = ["sq2", "bar3", "bar2", "bar4"]
    found = 0
    for i, s1 in enumerate(names):
        for s2 in names[i + 1:]:
            for c1, c2 in ((cols[0], cols[1]), (cols[1], cols[0])):
                for first in (0, 1):
                    pieces = [(c1, SHAPES[s1]), (c2, SHAPES[s2])]
                    if first:
                        pieces = pieces[::-1]
                    fn = _make(pieces)
                    try:
                        if all(fn(p["input"]) == p["output"] for p in train):
                            yield ("tile_%s%d_%s%d_o%d" % (s1, c1, s2, c2, first), 1 + i + first, fn)
                            found += 1
                    except Exception:
                        pass
                    if found >= 3:
                        return


FAMILIES = [fam]
