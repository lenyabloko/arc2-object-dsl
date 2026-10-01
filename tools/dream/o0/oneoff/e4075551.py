CARD = "e4075551"
READING = ("Five dots: the topmost, bottommost, leftmost and rightmost dots each extend into one side of the "
           "rectangle they bound (in their own colour), and the remaining inner dot gets a cross of a fixed "
           "colour spanning the rectangle's interior through it.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _dots(g, bg):
    return [(i, j, v) for i, r in enumerate(g) for j, v in enumerate(r) if v != bg]


def _apply(g, cross, hfirst):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    d = _dots(g, bg)
    if len(d) < 5:
        return [r[:] for r in g]
    top = min(d, key=lambda t: t[0])
    bot = max(d, key=lambda t: t[0])
    lef = min(d, key=lambda t: t[1])
    rig = max(d, key=lambda t: t[1])
    ext = {top, bot, lef, rig}
    rest = [t for t in d if t not in ext]
    if not rest:
        return [r[:] for r in g]
    cen = rest[0]
    r0, r1, c0, c1 = top[0], bot[0], lef[1], rig[1]
    out = [[bg] * W for _ in range(H)]
    for i in range(r0 + 1, r1):
        out[i][cen[1]] = cross
    for j in range(c0 + 1, c1):
        out[cen[0]][j] = cross
    out[cen[0]][cen[1]] = cen[2]

    def horiz():
        for j in range(c0, c1 + 1):
            out[r0][j] = top[2]
            out[r1][j] = bot[2]

    def vert():
        for i in range(r0, r1 + 1):
            out[i][c0] = lef[2]
            out[i][c1] = rig[2]
    if hfirst:
        vert(); horiz()
    else:
        horiz(); vert()
    return out


def _make(cross, hfirst):
    return lambda g: _apply(g, cross, hfirst)


def fam(train):
    # cross colour: output colour that never appears in any input
    inc = set(v for p in train for r in p["input"] for v in r)
    outc = set(v for p in train for r in p["output"] for v in r)
    new = sorted(outc - inc)
    if not new:
        new = sorted(outc)
    cands = []
    for cross in new:
        for hfirst in (True, False):
            cands.append(("rect_from_dots_cross%d_h%d" % (cross, hfirst), 0 if hfirst else 1, _make(cross, hfirst)))
    cands.sort(key=lambda t: t[1])
    k = 0
    for name, cost, fn in cands:
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
            k += 1
            if k >= 2:
                return


FAMILIES = [fam]
