CARD = "770cc55f"
READING = ("The columns shared by the two edge bars are filled with a new colour in the gap between the "
           "divider line and the larger of the two bars.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _transpose(g):
    return [list(r) for r in zip(*g)]


def _core(g, fill):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    lines = [i for i in range(1, H - 1) if g[i][0] != bg and all(x == g[i][0] for x in g[i])]
    if len(lines) != 1:
        return None
    L = lines[0]
    lc = g[L][0]
    top = [(i, j) for i in range(L) for j in range(W) if g[i][j] not in (bg, lc)]
    bot = [(i, j) for i in range(L + 1, H) for j in range(W) if g[i][j] not in (bg, lc)]
    if not top or not bot:
        return None
    cols = sorted(set(j for _, j in top) & set(j for _, j in bot))
    out = [list(r) for r in g]
    if len(top) == len(bot):
        return None
    if len(top) > len(bot):
        rows = range(max(i for i, _ in top) + 1, L)
    else:
        rows = range(L + 1, min(i for i, _ in bot))
    for i in rows:
        for j in cols:
            if out[i][j] == bg:
                out[i][j] = fill
    return out


def _make(fill):
    def fn(g):
        r = _core(g, fill)
        if r is not None:
            return r
        r = _core(_transpose(g), fill)
        return None if r is None else _transpose(r)
    return fn


def fam(train):
    fills = None
    for p in train:
        ins = set(x for r in p["input"] for x in r)
        new = set(x for r in p["output"] for x in r) - ins
        fills = new if fills is None else fills & new
    for fill in sorted(fills or ()):
        fn = _make(fill)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("shared_cols_fill_larger_side_c%d" % fill, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
