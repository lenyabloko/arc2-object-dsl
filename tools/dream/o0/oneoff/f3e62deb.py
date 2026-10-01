CARD = "f3e62deb"
READING = ("The single shape slides all the way to one grid edge, the edge being chosen by the shape's "
           "colour (colour-to-direction table learned from the examples, an unseen colour taking the one "
           "unused direction).")

DIRS = ((-1, 0), (0, 1), (1, 0), (0, -1))


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _slide(g, d):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] != bg]
    if not cells:
        return [r[:] for r in g]
    di, dj = d
    if di < 0:
        s = min(i for i, _ in cells)
    elif di > 0:
        s = H - 1 - max(i for i, _ in cells)
    elif dj < 0:
        s = min(j for _, j in cells)
    else:
        s = W - 1 - max(j for _, j in cells)
    out = [[bg] * W for _ in range(H)]
    for i, j in cells:
        out[i + di * s][j + dj * s] = g[i][j]
    return out


def _colour(g):
    bg = _bg(g)
    cnt = {}
    for r in g:
        for x in r:
            if x != bg:
                cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k]) if cnt else None


def _learn(train):
    table = {}
    for p in train:
        c = _colour(p["input"])
        ds = [d for d in DIRS if _slide(p["input"], d) == p["output"]]
        if not ds:
            return None
        if c in table:
            if table[c] not in ds:
                return None
        else:
            table[c] = ds[0]
    return table


def _make(table):
    used = set(table.values())
    free = [d for d in DIRS if d not in used]

    def fn(g):
        c = _colour(g)
        if c in table:
            d = table[c]
        elif len(free) == 1:
            d = free[0]
        else:
            return [r[:] for r in g]
        return _slide(g, d)
    return fn


def fam(train):
    table = _learn(train)
    if not table:
        return
    fn = _make(table)
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("colour_direction_slide", 1, fn)


FAMILIES = [fam]
