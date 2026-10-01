CARD = "37ce87bb"
READING = ("Next to the row of bottom-anchored bars, at the next column in their regular spacing, a new bar "
           "of the new colour is drawn whose height is the count of plus-colour cells minus the count of "
           "minus-colour cells.")


def _count(g):
    c = {}
    for r in g:
        for x in r:
            c[x] = c.get(x, 0) + 1
    return c


def _make(plus, minus, new, absval):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _count(g)
        bg = max(cnt, key=lambda k: cnt[k])
        cols = [j for j in range(W) if any(g[i][j] != bg for i in range(H))]
        if not cols:
            return [list(r) for r in g]
        if len(cols) >= 2:
            step = cols[-1] - cols[-2]
        else:
            step = 2
        c = cols[-1] + step
        h = cnt.get(plus, 0) - cnt.get(minus, 0)
        if absval:
            h = abs(h)
        out = [list(r) for r in g]
        if 0 <= c < W:
            for k in range(max(0, min(h, H))):
                out[H - 1 - k][c] = new
        return out
    return fn


def fam(train):
    cin = set()
    for p in train:
        cin |= set(_count(p["input"]))
    news = None
    for p in train:
        n = set(_count(p["output"])) - set(_count(p["input"]))
        news = n if news is None else news & n
    found = 0
    for absval in (False, True):
        for new in sorted(news or ()):
            for plus in sorted(cin):
                for minus in sorted(cin):
                    if plus == minus:
                        continue
                    fn = _make(plus, minus, new, absval)
                    try:
                        ok = all(fn(p["input"]) == p["output"] for p in train)
                    except Exception:
                        ok = False
                    if ok:
                        found += 1
                        yield ("bar_diff_%d_minus_%d" % (plus, minus), 1 + absval, fn)
                        if found >= 3:
                            return
FAMILIES = [fam]
