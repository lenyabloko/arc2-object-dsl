CARD = "896d5239"
READING = ("Each V of shape-colour cells (a 45-degree corner with two diagonal arms, possibly with missing arm "
           "cells) is closed into a right isosceles triangle as deep as its longest arm, and every "
           "non-shape cell inside that triangle is painted with the fill colour.")

# orientation: arm directions from the apex, and the level step (perpendicular to the base)
_ORI = [
    ((1, -1), (1, 1)),    # apex up, opens downward
    ((-1, -1), (-1, 1)),  # apex down, opens upward
    ((-1, 1), (1, 1)),    # apex left, opens right
    ((-1, -1), (1, -1)),  # apex right, opens left
]


def _learn_colours(train):
    fill = None
    cnt = {}
    for ex in train:
        g, o = ex['input'], ex['output']
        if len(g) != len(o) or len(g[0]) != len(o[0]):
            return None
        for i in range(len(g)):
            for j in range(len(g[0])):
                cnt[g[i][j]] = cnt.get(g[i][j], 0) + 1
                if g[i][j] != o[i][j]:
                    if fill is None:
                        fill = o[i][j]
                    elif fill != o[i][j]:
                        return None
    if fill is None:
        return None
    cands = [k for k in cnt if k != fill]
    if not cands:
        return None
    shape = min(cands, key=lambda k: (cnt[k], k))
    return shape, fill


def _vees(g, shape, maxgap, maxt):
    H, W = len(g), len(g[0])

    def isS(i, j):
        return 0 <= i < H and 0 <= j < W and g[i][j] == shape

    def inside(i, j):
        return 0 <= i < H and 0 <= j < W

    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != shape:
                continue
            for (d1, d2) in _ORI:
                # apex test: some level t <= maxt with both arm cells being shape
                ok = False
                for t in range(1, maxt + 1):
                    if isS(r + t * d1[0], c + t * d1[1]) and isS(r + t * d2[0], c + t * d2[1]):
                        ok = True
                        break
                if not ok:
                    continue
                last, t = 0, 1
                while True:
                    a = (r + t * d1[0], c + t * d1[1])
                    b = (r + t * d2[0], c + t * d2[1])
                    if not inside(*a) and not inside(*b):
                        break
                    if isS(*a) or isS(*b):
                        last = t
                    elif t - last > maxgap:
                        break
                    t += 1
                out.append((r, c, d1, d2, last))
    return out


def _apply(g, shape, fill, maxgap, maxt):
    H, W = len(g), len(g[0])
    out = [list(x) for x in g]
    for (r, c, d1, d2, k) in _vees(g, shape, maxgap, maxt):
        for t in range(1, k + 1):
            a = (r + t * d1[0], c + t * d1[1])
            b = (r + t * d2[0], c + t * d2[1])
            n = max(abs(a[0] - b[0]), abs(a[1] - b[1]))
            si = (b[0] - a[0]) // n if n else 0
            sj = (b[1] - a[1]) // n if n else 0
            for s in range(n + 1):
                i, j = a[0] + s * si, a[1] + s * sj
                if 0 <= i < H and 0 <= j < W and g[i][j] != shape:
                    out[i][j] = fill
    return out


def fam(train):
    cols = _learn_colours(train)
    if cols is None:
        return
    shape, fill = cols
    n = 0
    for maxt in (1, 2, 3):
        for maxgap in (1, 2):
            fn = (lambda s, f, mg, mt: (lambda g: _apply(g, s, f, mg, mt)))(shape, fill, maxgap, maxt)
            try:
                if all(fn(ex['input']) == ex['output'] for ex in train):
                    yield ('vee_triangle_fill_t%d_g%d' % (maxt, maxgap), maxt + maxgap, fn)
                    n += 1
                    if n >= 2:
                        return
            except Exception:
                continue


FAMILIES = [fam]
