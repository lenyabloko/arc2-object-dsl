CARD = "ac3e2b04"
READING = ("Through the centre of every boxed crossing on a line, draw a new-colour line perpendicular "
           "to that line over the background, and wherever this new line crosses another parallel line "
           "of the same colour, frame that crossing with a 3x3 ring of the new colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _boxes(g, bg):
    H, W = len(g), len(g[0])
    res = []
    for r in range(1, H - 1):
        for c in range(1, W - 1):
            ctr = g[r][c]
            if ctr == bg:
                continue
            ring = [g[r + a][c + b] for a in (-1, 0, 1) for b in (-1, 0, 1) if (a, b) != (0, 0)]
            f = ring[0]
            if f == bg or f == ctr or any(x != f for x in ring):
                continue
            res.append((r, c, f, ctr))
    return res


def _make(newcol):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        boxes = _boxes(g, bg)
        if not boxes:
            raise ValueError("no box")
        out = [row[:] for row in g]
        boxset = set((r, c) for r, c, _, _ in boxes)
        rings = []
        for r, c, f, L in boxes:
            # line orientation: vertical if cells beyond the box above/below carry L
            vert = (r - 2 >= 0 and g[r - 2][c] == L) or (r + 2 < H and g[r + 2][c] == L)
            horiz = (c - 2 >= 0 and g[r][c - 2] == L) or (c + 2 < W and g[r][c + 2] == L)
            if vert == horiz:
                raise ValueError("ambiguous box")
            if vert:
                # draw a horizontal new line along row r
                for j in range(W):
                    if g[r][j] == bg:
                        out[r][j] = newcol
                # crossings with other vertical lines of colour L
                for j in range(W):
                    if j == c or (r, j) in boxset:
                        continue
                    colvals = [g[i][j] for i in range(H)]
                    if g[r][j] == L and sum(1 for v in colvals if v == L) >= H - 3 * len(boxes):
                        rings.append((r, j))
            else:
                for i in range(H):
                    if g[i][c] == bg:
                        out[i][c] = newcol
                for i in range(H):
                    if i == r or (i, c) in boxset:
                        continue
                    rowvals = g[i]
                    if g[i][c] == L and sum(1 for v in rowvals if v == L) >= W - 3 * len(boxes):
                        rings.append((i, c))
        for r, c in rings:
            for a in (-1, 0, 1):
                for b in (-1, 0, 1):
                    if (a, b) == (0, 0):
                        continue
                    x, y = r + a, c + b
                    if 0 <= x < H and 0 <= y < W:
                        out[x][y] = newcol
        return out
    return fn


def fam(train):
    newcols = None
    for p in train:
        ins = set(v for r in p["input"] for v in r)
        outs = set(v for r in p["output"] for v in r)
        nc = outs - ins
        newcols = nc if newcols is None else (newcols & nc)
    if not newcols:
        return
    for nc in sorted(newcols):
        fn = _make(nc)
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
            yield ("perp_line_ring_new%d" % nc, 1, fn)


FAMILIES = [fam]
