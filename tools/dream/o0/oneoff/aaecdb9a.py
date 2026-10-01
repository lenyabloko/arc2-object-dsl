CARD = "aaecdb9a"
READING = ("Count the 8-connected objects of each non-background colour and draw a bottom-aligned bar "
           "chart, one column per colour in a fixed colour order, bar height = object count, "
           "chart height = largest count.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _counts(g, bg, diag):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    cnt = {}
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
                continue
            col = g[i][j]
            cnt[col] = cnt.get(col, 0) + 1
            st = [(i, j)]
            seen[i][j] = True
            while st:
                a, b = st.pop()
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
    return cnt


def _order_from_train(train):
    # column of each colour, read from the bottom rows of the training outputs
    colpos = {}
    width = None
    for p in train:
        o = p["output"]
        bgo = _bg(p["input"])
        w = len(o[0])
        if width is None:
            width = w
        elif width != w:
            return None, None
        for j in range(w):
            for i in range(len(o)):
                v = o[i][j]
                if v != bgo:
                    if colpos.get(v, j) != j:
                        return None, None
                    colpos[v] = j
    return colpos, width


def _make(colpos, width, diag):
    def fn(g):
        bg = _bg(g)
        cnt = _counts(g, bg, diag)
        h = 0
        for c, n in cnt.items():
            if c in colpos:
                h = max(h, n)
        if h == 0:
            raise ValueError("empty")
        out = [[bg] * width for _ in range(h)]
        for c, n in cnt.items():
            if c not in colpos:
                continue
            j = colpos[c]
            for k in range(n):
                out[h - 1 - k][j] = c
        return out
    return fn


def fam(train):
    colpos, width = _order_from_train(train)
    if colpos is None:
        return
    for diag, cost in ((True, 1), (False, 2)):
        fn = _make(colpos, width, diag)
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
            yield ("bar_chart_objcount_diag%d" % diag, cost, fn)


FAMILIES = [fam]
