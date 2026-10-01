CARD = "33067df9"
READING = ("The input is a lattice of single coloured cells; it is redrawn as a fixed-size canvas of "
           "equal blocks with margin and gaps, where horizontally adjacent equal colours merge into one "
           "block and then vertically adjacent merged blocks of equal colour and equal span merge too.")


def _cells(g, bg):
    H, W = len(g), len(g[0])
    rows = list(range(1, H, 2))
    cols = list(range(1, W, 2))
    # separators must be background
    for r in range(H):
        for c in range(W):
            if (r % 2 == 0 or c % 2 == 0) and g[r][c] != bg:
                return None
    return [[g[r][c] for c in cols] for r in rows]


def _merge(cells, bg, order):
    n, m = len(cells), len(cells[0])
    # first pass: runs along primary axis
    blocks = []  # (color, r0, r1, c0, c1)
    if order == "h":
        for i in range(n):
            j = 0
            while j < m:
                col = cells[i][j]
                k = j
                while k + 1 < m and cells[i][k + 1] == col:
                    k += 1
                if col != bg:
                    blocks.append([col, i, i, j, k])
                j = k + 1
    else:
        for j in range(m):
            i = 0
            while i < n:
                col = cells[i][j]
                k = i
                while k + 1 < n and cells[k + 1][j] == col:
                    k += 1
                if col != bg:
                    blocks.append([col, i, k, j, j])
                i = k + 1
    # second pass: merge blocks with identical span along secondary axis
    changed = True
    while changed:
        changed = False
        for a in blocks:
            for b in blocks:
                if a is b or a[0] != b[0]:
                    continue
                if order == "h" and a[3] == b[3] and a[4] == b[4] and b[1] == a[2] + 1:
                    a[2] = b[2]
                    blocks.remove(b)
                    changed = True
                    break
                if order == "v" and a[1] == b[1] and a[2] == b[2] and b[3] == a[4] + 1:
                    a[4] = b[4]
                    blocks.remove(b)
                    changed = True
                    break
            if changed:
                break
    return blocks


def _layout(S, n, mg, gap):
    avail = S - 2 * mg - (n - 1) * gap
    if avail <= 0 or avail % n:
        return None
    sz = avail // n
    return [(mg + i * (sz + gap), mg + i * (sz + gap) + sz - 1) for i in range(n)]


def _render(g, bg, SH, SW, mg, gap, order):
    cells = _cells(g, bg)
    if cells is None:
        return None
    n, m = len(cells), len(cells[0])
    ry = _layout(SH, n, mg, gap)
    rx = _layout(SW, m, mg, gap)
    if ry is None or rx is None:
        return None
    out = [[bg] * SW for _ in range(SH)]
    for col, r0, r1, c0, c1 in _merge(cells, bg, order):
        for r in range(ry[r0][0], ry[r1][1] + 1):
            for c in range(rx[c0][0], rx[c1][1] + 1):
                out[r][c] = col
    return out


def fam(train):
    sizes = set((len(p["output"]), len(p["output"][0])) for p in train)
    if len(sizes) != 1:
        return
    SH, SW = sizes.pop()
    bg = 0
    cands = []
    for order in ("h", "v"):
        for mg in range(0, 5):
            for gap in range(0, 5):
                ok = True
                for p in train:
                    o = _render(p["input"], bg, SH, SW, mg, gap, order)
                    if o != p["output"]:
                        ok = False
                        break
                if ok:
                    cands.append((order, mg, gap))
    for order, mg, gap in cands[:3]:
        def fn(g, order=order, mg=mg, gap=gap):
            return _render(g, bg, SH, SW, mg, gap, order)
        yield ("blocks_%s_m%d_g%d" % (order, mg, gap), 3, fn)


FAMILIES = [fam]
