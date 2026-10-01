CARD = "465b7d93"
READING = ("The loose small shape is removed and redrawn inside the hollow frame, stretched to fill the frame's "
           "interior with its cells as corners: edges between adjacent cells become full lines and fully "
           "filled cell squares become solid areas.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _frame(g, bg):
    """Return (colour, r0, c0, r1, c1) of a colour forming exactly the border of its bbox."""
    H, W = len(g), len(g[0])
    pos = {}
    for i in range(H):
        for j in range(W):
            if g[i][j] != bg:
                pos.setdefault(g[i][j], []).append((i, j))
    for col, ps in pos.items():
        r0 = min(a for a, _ in ps)
        r1 = max(a for a, _ in ps)
        c0 = min(b for _, b in ps)
        c1 = max(b for _, b in ps)
        if r1 - r0 < 2 or c1 - c0 < 2:
            continue
        s = set(ps)
        ring = set()
        for c in range(c0, c1 + 1):
            ring.add((r0, c))
            ring.add((r1, c))
        for r in range(r0, r1 + 1):
            ring.add((r, c0))
            ring.add((r, c1))
        if s == ring:
            return col, r0, c0, r1, c1, pos
    return None


def _idx(i, n, k):
    """Pattern indices (of k) covered by interior index i (of n), corners-as-vertices mapping."""
    if k == 1:
        return [0]
    if n == 1:
        return list(range(k))
    num = i * (k - 1)
    q, rem = divmod(num, n - 1)
    if rem == 0:
        return [q]
    return [q, q + 1]


def _nn(i, n, k):
    return [min(k - 1, (i * k) // n)]


def _make(mapper):
    def fn(g):
        bg = _bg(g)
        fr = _frame(g, bg)
        if fr is None:
            return None
        fcol, r0, c0, r1, c1, pos = fr
        shape = [p for col, ps in pos.items() if col != fcol for p in ps]
        if not shape:
            return [list(r) for r in g]
        scol = {}
        for a, b in shape:
            scol[g[a][b]] = scol.get(g[a][b], 0) + 1
        sr0 = min(a for a, _ in shape)
        sc0 = min(b for _, b in shape)
        kh = max(a for a, _ in shape) - sr0 + 1
        kw = max(b for _, b in shape) - sc0 + 1
        P = [[g[sr0 + i][sc0 + j] for j in range(kw)] for i in range(kh)]
        out = [list(r) for r in g]
        for a, b in shape:
            out[a][b] = bg
        nh, nw = r1 - r0 - 1, c1 - c0 - 1
        for i in range(nh):
            ri = mapper(i, nh, kh)
            for j in range(nw):
                cj = mapper(j, nw, kw)
                vals = [P[x][y] for x in ri for y in cj]
                if all(v != bg for v in vals):
                    cnt = {}
                    for v in vals:
                        cnt[v] = cnt.get(v, 0) + 1
                    out[r0 + 1 + i][c0 + 1 + j] = max(cnt, key=lambda k: cnt[k])
        return out
    return fn


def fam(train):
    for name, mp, cost in (("vertex_stretch", _idx, 1.0), ("nearest_stretch", _nn, 1.3)):
        fn = _make(mp)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("shape_into_frame_" + name, cost, fn)


FAMILIES = [fam]
