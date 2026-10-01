CARD = "522fdd07"
READING = ("Every solid square keeps its colour and centre but its side length steps through a "
           "learned cycle (each size shrinks by two, and a single cell grows to the largest size).")


def _comps(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if seen[i][j] or g[i][j] == bg:
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
            r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
            c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
            out.append((col, r0, r1, c0, c1))
    return out


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _learn(train):
    m = {}
    for p in train:
        gi, go = p["input"], p["output"]
        bg = _bg(gi)
        ci = _comps(gi, bg)
        co = _comps(go, bg)
        for (col, r0, r1, c0, c1) in ci:
            match = [o for o in co if o[0] == col]
            if len(match) != 1:
                return None
            _, R0, R1, C0, C1 = match[0]
            for d, D in ((r1 - r0 + 1, R1 - R0 + 1), (c1 - c0 + 1, C1 - C0 + 1)):
                if m.get(d, D) != D:
                    return None
                m[d] = D
    return m


def _make(m):
    def size(d):
        if d in m:
            return m[d]
        return d - 2 if d > 2 else max(m.values())

    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        out = [[bg] * W for _ in range(H)]
        for (col, r0, r1, c0, c1) in _comps(g, bg):
            h = size(r1 - r0 + 1); w = size(c1 - c0 + 1)
            cr2 = r0 + r1  # twice the centre
            cc2 = c0 + c1
            R0 = (cr2 - (h - 1)) // 2
            C0 = (cc2 - (w - 1)) // 2
            for i in range(R0, R0 + h):
                for j in range(C0, C0 + w):
                    if 0 <= i < H and 0 <= j < W:
                        out[i][j] = col
        return out
    return fn


def fam(train):
    m = _learn(train)
    if not m:
        return
    fn = _make(m)
    for p in train:
        if fn(p["input"]) != p["output"]:
            return
    yield ("square_size_cycle", 3, fn)


FAMILIES = [fam]
