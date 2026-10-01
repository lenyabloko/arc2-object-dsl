CARD = "b7249182"
READING = ("Two aligned single cells each shoot a line toward the other; just before the midpoint each "
           "line ends in a perpendicular bar whose ends turn one step toward the midpoint, so the two "
           "coloured brackets face each other across the middle.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _T(g):
    return [list(r) for r in zip(*g)]


def _horiz(g, bg, hw):
    # g has exactly two non-bg cells in one row; returns drawn grid or None
    pts = [(i, j, g[i][j]) for i in range(len(g)) for j in range(len(g[0])) if g[i][j] != bg]
    if len(pts) != 2 or pts[0][0] != pts[1][0]:
        return None
    pts.sort(key=lambda p: p[1])
    r = pts[0][0]
    (_, a, ca), (_, b, cb) = pts
    H, W = len(g), len(g[0])
    out = [row[:] for row in g]
    s = a + b
    la = s // 2 if s % 2 else s // 2 - 1    # last column of A's arms
    lb = la + 1 if s % 2 else s // 2 + 1    # first column of B's arms
    ba, bb = la - 1, lb + 1                 # bar columns

    def put(i, j, c):
        if 0 <= i < H and 0 <= j < W:
            out[i][j] = c
    for j in range(a, ba + 1):
        put(r, j, ca)
    for j in range(bb, b + 1):
        put(r, j, cb)
    for i in range(r - hw, r + hw + 1):
        put(i, ba, ca)
        put(i, bb, cb)
    for i in (r - hw, r + hw):
        for j in range(ba, la + 1):
            put(i, j, ca)
        for j in range(lb, bb + 1):
            put(i, j, cb)
    return out


def _make(hw):
    def fn(g):
        bg = _bg(g)
        o = _horiz(g, bg, hw)
        if o is not None:
            return o
        o = _horiz(_T(g), bg, hw)
        if o is not None:
            return _T(o)
        return [row[:] for row in g]
    return fn


def fam(train):
    for hw in (1, 2, 3, 4):
        fn = _make(hw)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("facing_brackets_hw%d" % hw, 1.0 + 0.1 * hw, fn)


FAMILIES = [fam]
