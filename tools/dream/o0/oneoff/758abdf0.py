CARD = "758abdf0"
READING = ("Stubs sticking out from the border line that are shorter than full length are extended to "
           "full length, while full-length stubs are erased and marked by a full-length bar of the border "
           "colour at the opposite edge.")


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


def _canon(g):
    """Return (k, rotated grid) with the uniform non-bg border line in column 0."""
    bg = _bg(g)
    for k in range(4):
        h = _rotn(g, k)
        c = h[0][0]
        if c != bg and all(r[0] == c for r in h):
            return k, h
    return None, None


def _runs(h, bg, line):
    res = []
    for r in h:
        n = 0
        while 1 + n < len(r) and r[1 + n] not in (bg, line):
            n += 1
        res.append(n)
    return res


def _make(fixedL):
    def fn(g):
        k, h = _canon(g)
        if h is None:
            return None
        bg = _bg(g)
        line = h[0][0]
        runs = _runs(h, bg, line)
        L = fixedL if fixedL else max(runs)
        if L <= 0:
            return None
        W = len(h[0])
        out = [list(r) for r in h]
        for i, n in enumerate(runs):
            if n == 0:
                continue
            fg = h[i][1]
            if n < L:
                for j in range(1, min(W, 1 + L)):
                    out[i][j] = fg
            else:
                for j in range(1, 1 + n):
                    out[i][j] = bg
                for j in range(max(1, W - L), W):
                    out[i][j] = line
        return _rotn(out, 4 - k)
    return fn


def fam(train):
    Ls = []
    for p in train:
        k, h = _canon(p["input"])
        if h is None:
            return
        Ls.append(max(_runs(h, _bg(p["input"]), h[0][0])))
    cands = [("stub_fix_L%d" % max(Ls), 1, _make(max(Ls))), ("stub_fix_gridmax", 2, _make(0))]
    for name, cost, fn in cands:
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
