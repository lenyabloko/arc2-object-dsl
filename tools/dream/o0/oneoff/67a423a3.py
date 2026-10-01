CARD = "67a423a3"
READING = ("Where the horizontal line crosses the vertical line, a square frame of the new colour "
           "(radius learned from training, 1 here) is drawn around the crossing cell, which keeps its colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _cross(g, bg):
    H, W = len(g), len(g[0])
    rs = [sum(1 for x in g[i] if x != bg) for i in range(H)]
    cs = [sum(1 for i in range(H) if g[i][j] != bg) for j in range(W)]
    r = max(range(H), key=lambda i: rs[i])
    c = max(range(W), key=lambda j: cs[j])
    return r, c


def _make(k, m):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        r, c = _cross(g, bg)
        out = [row[:] for row in g]
        for i in range(r - k, r + k + 1):
            for j in range(c - k, c + k + 1):
                if 0 <= i < H and 0 <= j < W and max(abs(i - r), abs(j - c)) == k:
                    out[i][j] = m
        return out
    return fn


def fam(train):
    news = set()
    for p in train:
        ic = {x for r in p["input"] for x in r}
        news |= {x for r in p["output"] for x in r} - ic
    for m in sorted(news):
        for k in (1, 2, 3):
            fn = _make(k, m)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("frame_at_crossing_r%d" % k, 1.0 + 0.1 * k, fn)
                return


FAMILIES = [fam]
