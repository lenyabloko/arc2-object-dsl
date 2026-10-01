CARD = "58e15b12"
READING = ("Each pair of parallel equal bars sends staircase rays outward (left bar up-left and "
           "down-left, right bar up-right and down-right, one column per bar-length step), and cells "
           "where rays of different colours cross take the colour introduced by the outputs.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _T(g):
    return [list(r) for r in zip(*g)]


def _new_colour(train):
    cols = None
    for p in train:
        ins = set(x for r in p["input"] for x in r)
        outs = set(x for r in p["output"] for x in r)
        c = outs - ins
        cols = c if cols is None else cols | c  # union: not every pair shows a crossing
    if cols and len(cols) == 1:
        return next(iter(cols))
    return None


def _bars(g, bg):
    # vertical runs (4-connected components that are single-column segments)
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    bars = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            col = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            cs = set(b for _, b in cells)
            if len(cs) != 1:
                return None
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            bars.append((col, r0, r1, cells[0][1]))
    return bars


def _solve_v(g, bg, cross):
    H, W = len(g), len(g[0])
    bars = _bars(g, bg)
    if not bars:
        return None
    bycol = {}
    for b in bars:
        bycol.setdefault(b[0], []).append(b)
    paint = {}

    def put(i, j, c):
        if 0 <= i < H and 0 <= j < W:
            paint.setdefault((i, j), set()).add(c)

    for col, bl in bycol.items():
        if len(bl) != 2:
            return None
        bl.sort(key=lambda b: b[3])
        for idx, (c, r0, r1, cc) in enumerate(bl):
            L = r1 - r0 + 1
            d = -1 if idx == 0 else 1
            for i in range(r0, r1 + 1):
                put(i, cc, c)
            k = 1
            while 0 <= cc + d * k < W:
                jj = cc + d * k
                for i in range(r0, r1 + 1):
                    put(i - k * L, jj, c)
                    put(i + k * L, jj, c)
                k += 1
    out = [row[:] for row in g]
    for (i, j), cs in paint.items():
        if len(cs) == 1:
            out[i][j] = next(iter(cs))
        elif cross is not None:
            out[i][j] = cross
    return out


def _make(cross):
    def fn(g):
        bg = _bg(g)
        r = _solve_v(g, bg, cross)
        if r is not None:
            return r
        r = _solve_v(_T(g), bg, cross)
        if r is not None:
            return _T(r)
        return [row[:] for row in g]
    return fn


def fam(train):
    cross = _new_colour(train)
    fn = _make(cross)
    ok = True
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                ok = False
                break
        except Exception:
            ok = False
            break
    if ok:
        yield ("bar_pair_staircases", 0, fn)


FAMILIES = [fam]
