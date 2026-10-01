CARD = "a8c38be5"
READING = ("The equal-sized filler-colour pieces scattered on the background are assembled into a 3x3 "
           "mosaic, each piece placed in the slot indicated by which side(s) its coloured marks lie on "
           "(centroid of non-filler cells), so the marks form the outer frame.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for r in range(H):
        for c in range(W):
            if g[r][c] != bg and not seen[r][c]:
                st = [(r, c)]
                seen[r][c] = True
                cells = []
                while st:
                    a, b = st.pop()
                    cells.append((a, b))
                    for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                            seen[x][y] = True
                            st.append((x, y))
                out.append(cells)
    return out


def _tile(cells, ph, pw):
    """Exactly cover a component with ph x pw rectangles; the first uncovered cell in
    row-major order must be a rectangle's top-left corner, so the cover is greedy."""
    left = set(cells)
    tiles = []
    while left:
        a, b = min(left)
        block = [(a + i, b + j) for i in range(ph) for j in range(pw)]
        if any(x not in left for x in block):
            return None
        for x in block:
            left.discard(x)
        tiles.append((a, b))
    return tiles


def _slot(v, n):
    # v = mean offset from centre; sign gives slot 0/1/2
    if v < -1e-9:
        return 0
    if v > 1e-9:
        return 2
    return 1


def _apply(g, ph, pw):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    pieces = []
    for cells in _comps(g, bg):
        tiles = _tile(cells, ph, pw)
        if tiles is None:
            continue
        for a, b in tiles:
            pieces.append([row[b:b + pw] for row in g[a:a + ph]])
    if not pieces:
        return None
    cnt = {}
    for pc in pieces:
        for row in pc:
            for x in row:
                cnt[x] = cnt.get(x, 0) + 1
    filler = max(cnt, key=lambda k: cnt[k])
    out = [[filler] * (3 * pw) for _ in range(3 * ph)]
    for pc in pieces:
        marks = [(i, j) for i in range(ph) for j in range(pw) if pc[i][j] != filler]
        if marks:
            mr = sum(i for i, _ in marks) / len(marks) - (ph - 1) / 2.0
            mc = sum(j for _, j in marks) / len(marks) - (pw - 1) / 2.0
        else:
            mr = mc = 0.0
        sr, sc = _slot(mr, ph), _slot(mc, pw)
        for i in range(ph):
            for j in range(pw):
                out[sr * ph + i][sc * pw + j] = pc[i][j]
    return out


def fam(train):
    sizes = set()
    for p in train:
        o = p["output"]
        if len(o) % 3 or len(o[0]) % 3:
            return
        sizes.add((len(o) // 3, len(o[0]) // 3))
    if len(sizes) != 1:
        return
    ph, pw = sizes.pop()

    def fn(g, ph=ph, pw=pw):
        r = _apply(g, ph, pw)
        return r if r is not None else [list(x) for x in g]

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("assemble_3x3_frame", 1, fn)


FAMILIES = [fam]
