CARD = "b745798f"
READING = ("Each small three-cell L piece names a grid corner by its orientation, and the output is a "
           "blank grid with that corner drawn as a big L of the piece's colour whose arms run half the "
           "grid's side (stopping before the middle row/column).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    res = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            c = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == c:
                        seen[x][y] = True
                        st.append((x, y))
            res.append((c, cells))
    return res


def _corner(cells):
    if len(cells) != 3:
        return None
    r0 = min(a for a, _ in cells)
    c0 = min(b for _, b in cells)
    box = {(a - r0, b - c0) for a, b in cells}
    full = {(0, 0), (0, 1), (1, 0), (1, 1)}
    if not box <= full:
        return None
    (mr, mc), = full - box
    return (1 - mr, 1 - mc)


def _make(armfn):
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        out = [[bg] * W for _ in range(H)]
        av, ah = armfn(H), armfn(W)
        for c, cells in _comps(g, bg):
            k = _corner(cells)
            if k is None:
                continue
            cr = 0 if k[0] == 0 else H - 1
            cc = 0 if k[1] == 0 else W - 1
            dr = 1 if k[0] == 0 else -1
            dc = 1 if k[1] == 0 else -1
            for t in range(ah):
                out[cr][cc + dc * t] = c
            for t in range(av):
                out[cr + dr * t][cc] = c
        return out
    return fn


_ARMS = [("half_floor", lambda n: (n - 1) // 2),
         ("half_ceil", lambda n: n // 2),
         ("full", lambda n: n)]


def fam(train):
    for i, (nm, af) in enumerate(_ARMS):
        fn = _make(af)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("L_piece_to_corner_" + nm, 1.0 + 0.1 * i, fn)


FAMILIES = [fam]
