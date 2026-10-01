CARD = "8b28cd80"
READING = ("The single coloured cell's position, mapped onto the enlarged grid, becomes the centre of a "
           "square spiral of that colour with one-cell gaps (arms of length 2, 2, 4, 4, 6, 6, ...), "
           "clipped to the output grid.")

_DIRS = [(-1, 0), (0, 1), (1, 0), (0, -1)]  # up, right, down, left (clockwise order)


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _spiral(g, k, start, chir, cmap):
    h, w = len(g), len(g[0])
    cnt = _counts(g)
    bg = max(cnt, key=lambda q: (cnt[q], -q))
    cells = [(i, j) for i in range(h) for j in range(w) if g[i][j] != bg]
    if len(cells) != 1:
        return None
    (pi, pj) = cells[0]
    col = g[pi][pj]
    H, W = h * k, w * k
    if cmap == 0:
        ci = pi * (H - 1) // (h - 1) if h > 1 else (H - 1) // 2
        cj = pj * (W - 1) // (w - 1) if w > 1 else (W - 1) // 2
    else:
        ci, cj = pi * k + k // 2, pj * k + k // 2
    out = [[bg] * W for _ in range(H)]
    r, c = ci, cj
    out[r][c] = col
    d = start
    seg = 0
    lim = 2 * (H + W) + 8
    while True:
        L = 2 * (seg // 2 + 1)
        if L > lim:
            break
        di, dj = _DIRS[d]
        for _ in range(L):
            r += di
            c += dj
            if 0 <= r < H and 0 <= c < W:
                out[r][c] = col
        d = (d + chir) % 4
        seg += 1
    return out


def _scale(train):
    ks = set()
    for ex in train:
        g, o = ex['input'], ex['output']
        if len(o) % len(g) or len(o[0]) % len(g[0]) or len(o) // len(g) != len(o[0]) // len(g[0]):
            return None
        ks.add(len(o) // len(g))
    return ks.pop() if len(ks) == 1 else None


def fam(train):
    k = _scale(train)
    if not k:
        return
    n = 0
    for cmap in (0, 1):
        for start in range(4):
            for chir in (1, 3):
                fn = (lambda s, ch, cm: (lambda g: _spiral(g, k, s, ch, cm)))(start, chir, cmap)
                try:
                    if all(fn(ex['input']) == ex['output'] for ex in train):
                        yield ('spiral_s%d_c%d_m%d' % (start, chir, cmap), 1 + cmap, fn)
                        n += 1
                        if n >= 2:
                            return
                except Exception:
                    continue


FAMILIES = [fam]
