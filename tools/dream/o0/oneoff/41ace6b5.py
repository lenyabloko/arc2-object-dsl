CARD = "41ace6b5"
READING = ("In each gap column of the two striped rows, the upper colour is redrawn as a bar of the "
           "common (tallest) height ending on the first stripe row, the lower-colour cells are "
           "restacked to start on the second stripe row, and the rest of the column below is filled "
           "with a new colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _structure(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    R2 = None
    for i in range(H):
        if any(x != bg for x in g[i]):
            R2 = i
            break
    if R2 is None or R2 + 1 >= H:
        return None
    row = g[R2]
    c2 = max(set(row), key=row.count)
    cols = [j for j in range(W) if row[j] != c2]
    return bg, R2, R2 + 1, cols


def _learn_colours(train):
    """up/down/fill colours, read from the first training output."""
    res = None
    for p in train:
        a, b = p["input"], p["output"]
        s = _structure(a)
        if s is None:
            return None
        bg, R2, R5, cols = s
        if not cols:
            continue
        j = cols[0]
        up = b[R2][j]
        down = b[R5][j]
        H = len(b)
        fill = None
        for jj in cols:
            v = b[H - 1][jj]
            if v not in (up, down, bg):
                fill = v
                break
        if fill is None:
            continue
        cand = (up, down, fill)
        if res is None:
            res = cand
        elif res != cand:
            return None
    return res


def _make(up, down, fill, height_mode):
    def fn(g):
        s = _structure(g)
        out = [row[:] for row in g]
        if s is None:
            return out
        bg, R2, R5, cols = s
        H = len(g)
        counts = [sum(1 for i in range(R2, H) if g[i][j] == up) for j in cols]
        if height_mode == "max":
            common = max(counts) if counts else 0
        elif height_mode == "mode":
            common = max(sorted(set(counts)), key=counts.count) if counts else 0
        else:
            common = None
        for k, j in enumerate(cols):
            n_up = counts[k] if common is None else common
            n_dn = sum(1 for i in range(R2, H) if g[i][j] == down)
            for i in range(0, H):
                if i <= R2:
                    out[i][j] = up if i > R2 - n_up else bg
                else:
                    if i < R5 + n_dn:
                        out[i][j] = down
                    else:
                        out[i][j] = fill
        return out
    return fn


def fam(train):
    cols = _learn_colours(train)
    if cols is None:
        return
    for cost, mode in ((1, "max"), (2, "mode"), (3, "percol")):
        fn = _make(cols[0], cols[1], cols[2], mode)
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
            yield ("restack_at_stripes_up" + mode, cost, fn)


FAMILIES = [fam]
