CARD = "22425bda"
READING = ("Each non-background colour is a straight line; read which line lies on top at every crossing and "
           "output the line colours as one row ordered from bottom-most to top-most.")
from collections import Counter


def _bg(g):
    c = Counter(v for r in g for v in r)
    return c.most_common(1)[0][0]


def _line_of(g, cells):
    best = None
    cnt = Counter()
    for r, c in cells:
        cnt[("r", r)] += 1
        cnt[("c", c)] += 1
        cnt[("d", r - c)] += 1
        cnt[("a", r + c)] += 1
    best = max(sorted(cnt), key=lambda k: cnt[k])
    return best


def _line_cells(g, key):
    H, W = len(g), len(g[0])
    kind, v = key
    res = []
    for r in range(H):
        for c in range(W):
            if (kind == "r" and r == v) or (kind == "c" and c == v) or \
               (kind == "d" and r - c == v) or (kind == "a" and r + c == v):
                res.append((r, c))
    return res


def _order(g):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    cells = {}
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg:
                cells.setdefault(g[r][c], []).append((r, c))
    above = {k: set() for k in cells}   # above[c] = colours drawn over c
    first = {k: min(v) for k, v in cells.items()}
    for col, cl in cells.items():
        key = _line_of(g, cl)
        for r, c in _line_cells(g, key):
            d = g[r][c]
            if d != col and d != bg and d in cells:
                above[col].add(d)
    # Kahn: bottom first (colours with nothing below them)
    below_cnt = {k: 0 for k in cells}
    for k, s in above.items():
        for d in s:
            if k not in above[d]:
                below_cnt[d] += 1
    order = []
    remaining = set(cells)
    while remaining:
        ready = [k for k in remaining if below_cnt[k] == 0]
        if not ready:
            ready = list(remaining)
        k = min(ready, key=lambda x: first[x])
        order.append(k)
        remaining.discard(k)
        for d in above[k]:
            if d in remaining and k not in above[d]:
                below_cnt[d] -= 1
    return order


def _make(rev):
    def fn(g):
        o = _order(g)
        if rev:
            o = o[::-1]
        return [o]
    return fn


def fam(train):
    for rev, name in ((False, "lines_bottom_to_top"), (True, "lines_top_to_bottom")):
        fn = _make(rev)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
