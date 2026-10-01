CARD = "762cd429"
READING = ("The small seed at the grid edge is copied repeatedly away from the edge, each copy scaled up "
           "by a constant factor over the previous one, abutting it and centred on the seed's axis, until the grid is filled.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _rot(g):
    return [list(r) for r in zip(*g[::-1])]


def _rotn(g, n):
    for _ in range(n % 4):
        g = _rot(g)
    return g


def _core(g, f):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] != bg]
    if not cells:
        return None
    r0 = min(c[0] for c in cells); r1 = max(c[0] for c in cells)
    c0 = min(c[1] for c in cells); c1 = max(c[1] for c in cells)
    if c0 != 0:
        return None
    h, w = r1 - r0 + 1, c1 - c0 + 1
    seed = [g[r0 + a][c0:c0 + w] for a in range(h)]
    out = [list(r) for r in g]
    x = c0 + w
    s = f
    guard = 0
    while x < W and guard < 64:
        guard += 1
        top = r0 - (h * (s - 1)) // 2
        for a in range(h * s):
            for b in range(w * s):
                i, j = top + a, x + b
                if 0 <= i < H and 0 <= j < W:
                    out[i][j] = seed[a // s][b // s]
        x += w * s
        s *= f
    return out


def _make(k, f):
    def fn(g):
        r = _core(_rotn(g, k), f)
        return None if r is None else _rotn(r, 4 - k)
    return fn


def fam(train):
    for f in (2, 3):
        for k in range(4):
            fn = _make(k, f)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("geometric_zoom_f%d_rot%d" % (f, k), 1, fn)
            except Exception:
                pass


FAMILIES = [fam]
