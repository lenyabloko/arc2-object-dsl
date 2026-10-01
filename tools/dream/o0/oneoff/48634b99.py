CARD = "48634b99"
READING = ("The marked fill at one end of a bar is erased and transferred to the next-longer bar, "
           "filling the same end of that bar to the same fraction of its length.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _T(g):
    return [list(r) for r in zip(*g)]


def _bars(g, bg):
    H, W = len(g), len(g[0])
    bars = []
    for c in range(W):
        r = 0
        while r < H:
            if g[r][c] != bg:
                s = r
                while r < H and g[r][c] != bg:
                    r += 1
                bars.append((c, s, r - 1))
            else:
                r += 1
    return bars


def _solve_v(g, rule):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    bars = _bars(g, bg)
    cnt = {}
    for c, s, e in bars:
        for i in range(s, e + 1):
            cnt[g[i][c]] = cnt.get(g[i][c], 0) + 1
    if len(cnt) < 2:
        return None
    body = max(cnt, key=lambda k: cnt[k])
    marked = [b for b in bars if any(g[i][b[0]] != body for i in range(b[1], b[2] + 1))]
    if len(marked) != 1:
        return None
    c, s, e = marked[0]
    L = e - s + 1
    seg = [g[i][c] for i in range(s, e + 1)]
    mk = [x for x in seg if x != body][0]
    k = sum(1 for x in seg if x == mk)
    top = seg[0] == mk
    longer = [b for b in bars if b[2] - b[1] + 1 > L]
    if not longer:
        return None
    m = min(b[2] - b[1] + 1 for b in longer)
    tgt = [b for b in longer if b[2] - b[1] + 1 == m]
    tgt.sort(key=lambda b: abs(b[0] - c) + abs(b[1] - s))
    tc, ts, te = tgt[0]
    L2 = te - ts + 1
    if rule == "frac":
        if (k * L2) % L:
            return None
        k2 = k * L2 // L
    else:
        k2 = k + (L2 - L) // 2
    out = [list(r) for r in g]
    for i in range(s, e + 1):
        out[i][c] = body
    rows = range(ts, ts + k2) if top else range(te - k2 + 1, te + 1)
    for i in rows:
        out[i][tc] = mk
    return out


def _make(rule):
    def fn(g):
        r = _solve_v(g, rule)
        if r is None:
            r2 = _solve_v(_T(g), rule)
            if r2 is not None:
                return _T(r2)
            return [list(x) for x in g]
        return r
    return fn


def fam(train):
    for name, rule in (("transfer_fill_next_longer_frac", "frac"),
                       ("transfer_fill_next_longer_plus", "plus")):
        fn = _make(rule)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
