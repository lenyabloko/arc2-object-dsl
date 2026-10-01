CARD = "fb791726"
READING = ("The grid is enlarged by placing copies of the input on the main diagonal of a doubled "
           "canvas, and every row lying between two same-coloured cells stacked one row apart is "
           "filled with a new colour.")


def _colors(g):
    return {x for r in g for x in r}


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _diag(g, k, bg):
    H, W = len(g), len(g[0])
    out = [[bg] * (W * k) for _ in range(H * k)]
    for t in range(k):
        for r in range(H):
            for c in range(W):
                out[t * H + r][t * W + c] = g[r][c]
    return out


def _bridge(out, bg, fill):
    H, W = len(out), len(out[0])
    res = [row[:] for row in out]
    for r in range(1, H - 1):
        if any(out[r][c] != bg for c in range(W)):
            continue
        if any(out[r - 1][c] != bg and out[r - 1][c] == out[r + 1][c] for c in range(W)):
            res[r] = [fill] * W
    return res


def fam(train):
    k = None
    fill = None
    for p in train:
        i, o = p["input"], p["output"]
        H, W = len(i), len(i[0])
        if len(o) % H or len(o[0]) % W or len(o) // H != len(o[0]) // W:
            return
        kk = len(o) // H
        if k is None:
            k = kk
        elif k != kk:
            return
        new = _colors(o) - _colors(i)
        if len(new) != 1:
            return
        f = next(iter(new))
        if fill is None:
            fill = f
        elif fill != f:
            return

    def fn(g, k=k, fill=fill):
        bg = _bg(g)
        return _bridge(_diag(g, k, bg), bg, fill)

    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("diag_bridge_rows", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
