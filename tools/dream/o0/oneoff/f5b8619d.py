CARD = "f5b8619d"
READING = ("Every empty cell in a column that contains a coloured cell is painted with a new fill "
           "colour, and the result is tiled into a grid of copies (2x2 here).")


def _colors(g):
    return {x for r in g for x in r}


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _fill_cols(g, bg, fill):
    H, W = len(g), len(g[0])
    cols = {c for c in range(W) if any(g[r][c] != bg for r in range(H))}
    return [[fill if (g[r][c] == bg and c in cols) else g[r][c] for c in range(W)] for r in range(H)]


def _tile(g, ky, kx):
    return [row * kx for row in g] * ky


def fam(train):
    ky = kx = None
    fill = None
    for p in train:
        i, o = p["input"], p["output"]
        H, W = len(i), len(i[0])
        h, w = len(o), len(o[0])
        if h % H or w % W:
            return
        a, b = h // H, w // W
        if ky is None:
            ky, kx = a, b
        elif (ky, kx) != (a, b):
            return
        new = _colors(o) - _colors(i)
        if len(new) != 1:
            return
        f = next(iter(new))
        if fill is None:
            fill = f
        elif fill != f:
            return

    def fn(g, ky=ky, kx=kx, fill=fill):
        bg = _bg(g)
        return _tile(_fill_cols(g, bg, fill), ky, kx)

    def fn0(g, ky=ky, kx=kx, fill=fill):
        return _tile(_fill_cols(g, 0, fill), ky, kx)

    for name, f in (("colfill_tile_bg", fn), ("colfill_tile_0", fn0)):
        try:
            if all(f(p["input"]) == p["output"] for p in train):
                yield (name, 1, f)
        except Exception:
            pass


FAMILIES = [fam]
