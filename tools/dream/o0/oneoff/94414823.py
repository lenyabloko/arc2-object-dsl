CARD = "94414823"
READING = ("The empty interior of the rectangular frame is split into four quadrants; each outside marker pixel "
           "paints the quadrant nearest to it and the diagonally opposite quadrant with its colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _frame(g, bg):
    # the colour with the most cells forming a hollow rectangle border
    H, W = len(g), len(g[0])
    best = None
    for c in {x for r in g for x in r if x != bg}:
        cells = [(i, j) for i in range(H) for j in range(W) if g[i][j] == c]
        r0 = min(i for i, _ in cells); r1 = max(i for i, _ in cells)
        c0 = min(j for _, j in cells); c1 = max(j for _, j in cells)
        border = {(i, j) for i in range(r0, r1 + 1) for j in range(c0, c1 + 1)
                  if i in (r0, r1) or j in (c0, c1)}
        if r1 - r0 >= 2 and c1 - c0 >= 2 and border == set(cells):
            if best is None or len(cells) > best[0]:
                best = (len(cells), c, r0, r1, c0, c1)
    return best


def fn(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    fr = _frame(g, bg)
    out = [r[:] for r in g]
    if fr is None:
        return out
    _, fc, r0, r1, c0, c1 = fr
    ir0, ir1, ic0, ic1 = r0 + 1, r1 - 1, c0 + 1, c1 - 1
    h, w = ir1 - ir0 + 1, ic1 - ic0 + 1
    rm, cm = ir0 + h // 2, ic0 + w // 2  # first row/col of lower/right half
    cy2, cx2 = r0 + r1, c0 + c1  # twice the centre
    marks = [(i, j, g[i][j]) for i in range(H) for j in range(W)
             if g[i][j] not in (bg, fc) and not (r0 <= i <= r1 and c0 <= j <= c1)]
    quad = {}
    for i, j, v in marks:
        sy = 1 if 2 * i > cy2 else 0
        sx = 1 if 2 * j > cx2 else 0
        quad[(sy, sx)] = v
        quad[(1 - sy, 1 - sx)] = v
    for (sy, sx), v in quad.items():
        rr = range(rm, ir1 + 1) if sy else range(ir0, rm)
        cc = range(cm, ic1 + 1) if sx else range(ic0, cm)
        for i in rr:
            for j in cc:
                out[i][j] = v
    return out


def fam(train):
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("quadrant_diagonal_markers", 1, fn)


FAMILIES = [fam]
