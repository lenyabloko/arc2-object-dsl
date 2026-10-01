CARD = "e5062a87"
READING = ("Copies of the red template shape are stamped onto background cells wherever the whole "
           "shape fits on background (template holes must not be background), taken greedily in "
           "reading order without overlap; this reading explains training pairs 2-3 but not pair "
           "1, where one fitting spot stays empty.")

# Status: no rule found that reproduces all training pairs. fam() only yields programs that
# fit every training pair, so it currently yields nothing; partial(train) returns the best attempt
# (reproduces 2 of 3 training pairs).


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _shape(g, col):
    H, W = len(g), len(g[0])
    sh = [(i, j) for i in range(H) for j in range(W) if g[i][j] == col]
    if not sh:
        return None
    r0 = min(a for a, b in sh); c0 = min(b for a, b in sh)
    rel = [(a - r0, b - c0) for a, b in sh]
    h = max(a for a, b in rel) + 1; w = max(b for a, b in rel) + 1
    S = set(rel)
    st = [(a, b) for a in range(-1, h + 1) for b in range(-1, w + 1) if a in (-1, h) or b in (-1, w)]
    out = set(st)
    while st:
        a, b = st.pop()
        for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
            if -1 <= x <= h and -1 <= y <= w and (x, y) not in S and (x, y) not in out:
                out.add((x, y)); st.append((x, y))
    holes = [(a, b) for a in range(h) for b in range(w) if (a, b) not in S and (a, b) not in out]
    return rel, holes


def _make(col, hole_rule, order):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = 0 if any(0 in r for r in g) else _bg(g)
        s = _shape(g, col)
        out = [row[:] for row in g]
        if s is None:
            return out
        rel, holes = s
        fits = []
        for i in range(H):
            for j in range(W):
                cells = [(i + a, j + b) for a, b in rel]
                if not all(0 <= x < H and 0 <= y < W and g[x][y] == bg for x, y in cells):
                    continue
                if hole_rule and any(g[i + a][j + b] == bg for a, b in holes):
                    continue
                fits.append(cells)
        if order == 1:
            fits.reverse()
        used = set()
        for cells in fits:
            if any(c in used for c in cells):
                continue
            for x, y in cells:
                out[x][y] = col
                used.add((x, y))
        return out
    return fn


def _colour(train):
    cs = set()
    for p in train:
        for a, b in zip(p["input"], p["output"]):
            for x, y in zip(a, b):
                if x != y:
                    cs.add(y)
    return cs.pop() if len(cs) == 1 else None


def fam(train):
    col = _colour(train)
    if col is None:
        return
    for hole_rule in (True, False):
        for order in (0, 1):
            fn = _make(col, hole_rule, order)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("stamp_fits_h%d_o%d" % (hole_rule, order), 3, fn)
            except Exception:
                pass


def partial(train):
    """Best attempt (fits training pairs 2 and 3 only); colour induced from train."""
    col = _colour(train)
    return None if col is None else _make(col, True, 0)

FAMILIES = [fam]
