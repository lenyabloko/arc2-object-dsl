CARD = "bc93ec48"
READING = ("Each shape that occupies a grid corner is copied, unrotated, into the next corner clockwise "
           "and painted over whatever is there, while the original shapes stay where they are not covered.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comp(g, i, j, c8):
    H, W = len(g), len(g[0])
    c = g[i][j]
    seen = {(i, j)}
    st = [(i, j)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if c8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    while st:
        a, b = st.pop()
        for da, db in nb:
            x, y = a + da, b + db
            if 0 <= x < H and 0 <= y < W and (x, y) not in seen and g[x][y] == c:
                seen.add((x, y))
                st.append((x, y))
    return c, seen


def _solve(g, cw, c8):
    bg = _bg(g)
    H, W = len(g), len(g[0])
    corners = [(0, 0), (0, W - 1), (H - 1, W - 1), (H - 1, 0)]  # clockwise order
    shapes = []
    for (i, j) in corners:
        if g[i][j] == bg:
            shapes.append(None)
        else:
            shapes.append(_comp(g, i, j, c8))
    out = [list(r) for r in g]
    step = 1 if cw else -1
    for k, sh in enumerate(shapes):
        if sh is None:
            continue
        c, cells = sh
        r0 = min(p[0] for p in cells)
        r1 = max(p[0] for p in cells)
        q0 = min(p[1] for p in cells)
        q1 = max(p[1] for p in cells)
        ti, tj = corners[(k + step) % 4]
        dr = (0 - r0) if ti == 0 else (H - 1 - r1)
        dc = (0 - q0) if tj == 0 else (W - 1 - q1)
        for (a, b) in cells:
            x, y = a + dr, b + dc
            if 0 <= x < H and 0 <= y < W:
                out[x][y] = c
    return out


def fam(train):
    opts = (("corner_shapes_to_next_corner_cw_4conn", 1, True, False),
            ("corner_shapes_to_next_corner_cw_8conn", 2, True, True),
            ("corner_shapes_to_next_corner_ccw_4conn", 3, False, False),
            ("corner_shapes_to_next_corner_ccw_8conn", 4, False, True))
    for name, cost, cw, c8 in opts:
        fn = (lambda cw, c8: (lambda g: _solve(g, cw, c8)))(cw, c8)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
