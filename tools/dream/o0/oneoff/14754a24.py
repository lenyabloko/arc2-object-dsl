CARD = "14754a24"
READING = "Marker-coloured cells are the visible parts of plus shapes hidden in the noise; find the non-overlapping pluses (all cells non-background, at least two marker cells) that cover every marker cell and recolour their noise-coloured cells to the new colour."

from collections import Counter

PLUS = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))


def _cands(a, marker, body, minm):
    H, W = len(a), len(a[0])
    cands = []
    for r in range(H):
        for c in range(W):
            inb = [(r + dr, c + dc) for dr, dc in PLUS if 0 <= r + dr < H and 0 <= c + dc < W]
            if all(a[y][x] in (marker, body) for y, x in inb):
                n = sum(a[y][x] == marker for y, x in inb)
                if n >= minm:
                    cands.append((-n, r, c, frozenset(inb)))
    cands.sort(key=lambda t: (t[0], t[1], t[2]))
    return cands


def _paint(a, sel, body, new):
    o = [row[:] for row in a]
    for cells in sel:
        for y, x in cells:
            if o[y][x] == body:
                o[y][x] = new
    return o


def _greedy(marker, body, new, minm):
    def fn(a):
        used = set()
        sel = []
        for _, r, c, cells in _cands(a, marker, body, minm):
            if cells & used:
                continue
            sel.append(cells)
            used |= cells
        return _paint(a, sel, body, new)
    return fn


def _exact(marker, body, new, minm):
    def fn(a):
        H, W = len(a), len(a[0])
        cands = _cands(a, marker, body, minm)
        targets = sorted((r, c) for r in range(H) for c in range(W) if a[r][c] == marker)
        by_cell = {}
        for cand in cands:
            for cell in cand[3]:
                by_cell.setdefault(cell, []).append(cand[3])
        best = [None]
        budget = [20000]

        def rec(i, used, sel):
            budget[0] -= 1
            if budget[0] < 0:
                return True
            while i < len(targets) and targets[i] in used:
                i += 1
            if i == len(targets):
                best[0] = list(sel)
                return True
            for cells in by_cell.get(targets[i], []):
                if cells & used:
                    continue
                sel.append(cells)
                if rec(i + 1, used | cells, sel):
                    return True
                sel.pop()
            return False

        rec(0, frozenset(), [])
        if best[0] is None:
            return _greedy(marker, body, new, minm)(a)
        return _paint(a, best[0], body, new)
    return fn


def _colours(train):
    changes = set()
    cols = set()
    for p in train:
        a, b = p["input"], p["output"]
        for r in range(len(a)):
            for c in range(len(a[0])):
                cols.add(a[r][c])
                if a[r][c] != b[r][c]:
                    changes.add((a[r][c], b[r][c]))
    if len(changes) != 1:
        return []
    body, new = next(iter(changes))
    return [(m, body, new) for m in sorted(cols) if m != body]


def fam(train):
    for marker, body, new in _colours(train):
        for minm, mc in ((2, 0), (1, 1)):
            for maker, name, cost in ((_greedy, "plus_greedy", 1), (_exact, "plus_exactcover", 2)):
                fn = maker(marker, body, new, minm)
                try:
                    if all(fn(p["input"]) == p["output"] for p in train):
                        yield ("%s_m%d_min%d" % (name, marker, minm), cost + mc, fn)
                except Exception:
                    pass


FAMILIES = [fam]
