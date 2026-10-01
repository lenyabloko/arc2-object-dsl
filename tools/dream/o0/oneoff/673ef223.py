CARD = "673ef223"
READING = ("Each dot beside one wall bar is joined to that bar by a line of the dot colour and the dot "
           "becomes the marker colour, and the matching rows of the other (equal-length) wall bar get "
           "a line of the dot colour running from that bar across the whole grid.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _T(g):
    return [list(r) for r in zip(*g)]


def _bars(g, b):
    # maximal vertical runs of colour b with length >= 2
    H, W = len(g), len(g[0])
    out = []
    for j in range(W):
        i = 0
        while i < H:
            if g[i][j] == b:
                k = i
                while k < H and g[k][j] == b:
                    k += 1
                if k - i >= 2:
                    out.append((i, k - 1, j))
                i = k
            else:
                i += 1
    return out


def _solve(g, b, d, m):
    H, W = len(g), len(g[0])
    bars = _bars(g, b)
    if len(bars) != 2:
        return None
    dots = [(i, j) for i in range(H) for j in range(W) if g[i][j] == d]
    if not dots:
        return None
    A = B = None
    for bar in bars:
        t, e, c = bar
        if all(t <= i <= e for i, j in dots):
            A = bar
    if A is None:
        return None
    B = bars[0] if bars[1] == A else bars[1]
    tA, eA, cA = A
    tB, eB, cB = B
    out = [r[:] for r in g]
    dirA = None
    for i, j in dots:
        s = 1 if j > cA else -1
        if dirA is None:
            dirA = s
        elif dirA != s:
            return None
        for y in range(cA + s, j, s):
            out[i][y] = d
        out[i][j] = m
    dirB = -dirA
    for i, j in dots:
        r = i - tA + tB
        if not (0 <= r < H):
            continue
        y = cB + dirB
        while 0 <= y < W:
            out[r][y] = d
            y += dirB
    return out


def _make(b, d, m, transpose):
    def fn(g):
        if transpose:
            r = _solve(_T(g), b, d, m)
            return _T(r) if r is not None else [row[:] for row in g]
        r = _solve(g, b, d, m)
        return r if r is not None else [row[:] for row in g]
    return fn


def fam(train):
    ins, news = set(), set()
    for p in train:
        bg = _bg(p["input"])
        ic = {x for r in p["input"] for x in r} - {bg}
        ins |= ic
        news |= {x for r in p["output"] for x in r} - ic - {bg}
    for transpose in (False, True):
        for b in sorted(ins):
            for d in sorted(ins - {b}):
                for m in sorted(news):
                    fn = _make(b, d, m, transpose)
                    if all(fn(p["input"]) == p["output"] for p in train):
                        yield ("bar_dot_lines" + ("_T" if transpose else ""), 1.0, fn)
                        return


FAMILIES = [fam]
