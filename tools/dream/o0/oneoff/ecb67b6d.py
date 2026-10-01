CARD = "ecb67b6d"
READING = ("Every 8-connected group of the scattered colour that contains a diagonal run of at "
           "least three cells is recoloured to the new colour; all other groups stay as they are.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, col, conn8):
    H, W = len(g), len(g[0])
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if conn8:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] != col or seen[i][j]:
                continue
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            out.append(cells)
    return out


def _maxdiag(cells):
    s = set(cells)
    best = 0
    for (a, b) in cells:
        for da, db in ((1, 1), (1, -1)):
            if (a - da, b - db) in s:
                continue
            n = 0
            x, y = a, b
            while (x, y) in s:
                n += 1
                x += da
                y += db
            best = max(best, n)
    return best


def _make(src, dst, k, conn8):
    def fn(g):
        out = [row[:] for row in g]
        for cells in _comps(g, src, conn8):
            if _maxdiag(cells) >= k:
                for a, b in cells:
                    out[a][b] = dst
        return out
    return fn


def fam(train):
    pairs = set()
    for p in train:
        gi, go = p["input"], p["output"]
        if len(gi) != len(go) or len(gi[0]) != len(go[0]):
            return
        for ri, ro in zip(gi, go):
            for a, b in zip(ri, ro):
                if a != b:
                    pairs.add((a, b))
    if len(pairs) != 1:
        return
    src, dst = pairs.pop()
    for conn8 in (True, False):
        for k in (3, 2, 4, 5):
            fn = _make(src, dst, k, conn8)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("diag_run_group_recolor_k%d_%s" % (k, "8" if conn8 else "4"), 1.0 + 0.1 * (not conn8), fn)


FAMILIES = [fam]
