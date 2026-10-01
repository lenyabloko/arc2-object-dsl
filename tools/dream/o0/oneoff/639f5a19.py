CARD = "639f5a19"
READING = ("Every solid rectangle is recoloured into four quadrant colours with an inner "
           "rectangle (inset by a fixed margin from each edge) painted a fifth colour; colours and "
           "margin are read from the training pairs.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _rects(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            col = g[i][j]
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
            c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
            if len(cells) == (r1 - r0 + 1) * (c1 - c0 + 1):
                out.append((r0, c0, r1 - r0 + 1, c1 - c0 + 1))
    return out


def _role(i, j, h, w, k):
    if k <= i < h - k and k <= j < w - k:
        return 4
    return (0 if 2 * i < h else 2) + (0 if 2 * j < w else 1)


def _make(k, cols):
    def fn(g):
        bg = _bg(g)
        out = [row[:] for row in g]
        for r0, c0, h, w in _rects(g, bg):
            for i in range(h):
                for j in range(w):
                    out[r0 + i][c0 + j] = cols.get(_role(i, j, h, w, k), g[r0 + i][c0 + j])
        return out
    return fn


def fam(train):
    for k in range(0, 6):
        cols = {}
        ok = True
        for p in train:
            I, O = p["input"], p["output"]
            if len(I) != len(O) or len(I[0]) != len(O[0]):
                return
            for r0, c0, h, w in _rects(I, _bg(I)):
                for i in range(h):
                    for j in range(w):
                        ro = _role(i, j, h, w, k)
                        v = O[r0 + i][c0 + j]
                        if cols.get(ro, v) != v:
                            ok = False
                        cols[ro] = v
                if not ok:
                    break
            if not ok:
                break
        if not ok or not cols:
            continue
        fn = _make(k, cols)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("quadrants_inset_%d" % k, 1.0 + 0.01 * k, fn)
            return


FAMILIES = [fam]
