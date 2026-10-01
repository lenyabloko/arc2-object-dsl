CARD = "8597cfd7"
READING = ("The grid is split by a full separator line; the output is a fixed-size block filled with "
           "the colour whose cell count grows the most from the first part to the second part.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _split(g, bg):
    H, W = len(g), len(g[0])
    for i in range(H):
        if len(set(g[i])) == 1 and g[i][0] != bg:
            return [r for r in g[:i]], [r for r in g[i + 1:]], g[i][0]
    for j in range(W):
        col = [g[i][j] for i in range(H)]
        if len(set(col)) == 1 and col[0] != bg:
            return ([r[:j] for r in g], [r[j + 1:] for r in g], col[0])
    return None


def _count(part):
    c = {}
    for r in part:
        for x in r:
            c[x] = c.get(x, 0) + 1
    return c


def _make(mode, oh, ow):
    def fn(g):
        bg = _bg(g)
        s = _split(g, bg)
        if s is None:
            return None
        a, b, sep = s
        ca, cb = _count(a), _count(b)
        cols = sorted(set(ca) | set(cb) - {bg, sep})
        cols = [c for c in cols if c not in (bg, sep)]
        if not cols:
            return None

        def val(c):
            x, y = ca.get(c, 0), cb.get(c, 0)
            if mode == "diff":
                return y - x
            if mode == "ratio":
                return y / x if x else float("inf")
            return y  # "second"
        best = max(cols, key=lambda c: (val(c), -c))
        return [[best] * ow for _ in range(oh)]
    return fn


def fam(train):
    shapes = set((len(p["output"]), len(p["output"][0])) for p in train)
    if len(shapes) != 1:
        return
    oh, ow = shapes.pop()
    for name, cost, mode in (("max_growth_diff", 1, "diff"), ("max_growth_ratio", 2, "ratio"),
                             ("max_count_second", 3, "second")):
        fn = _make(mode, oh, ow)
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
            yield (name, cost, fn)


FAMILIES = [fam]
