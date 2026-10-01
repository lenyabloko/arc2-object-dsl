CARD = "6b9890af"
READING = ("Crop the hollow square frame and fill its interior with the small separate pattern scaled up "
           "to exactly fit inside.")


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
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                            seen[x][y] = True
                            st.append((x, y))
            out.append((col, cells))
    return out


def _box(cells):
    return (min(a for a, _ in cells), max(a for a, _ in cells),
            min(b for _, b in cells), max(b for _, b in cells))


def _make():
    def fn(g):
        bg = _bg(g)
        comps = _comps(g, bg)
        def area(cc):
            r0, r1, c0, c1 = _box(cc[1])
            return (r1 - r0 + 1) * (c1 - c0 + 1)
        comps.sort(key=area, reverse=True)
        fcol, fcells = comps[0]
        r0, r1, c0, c1 = _box(fcells)
        rest = [c for col, cells in comps[1:] for c in cells]
        pr0, pr1, pc0, pc1 = _box(rest)
        ph, pw = pr1 - pr0 + 1, pc1 - pc0 + 1
        ih, iw = r1 - r0 - 1, c1 - c0 - 1
        if ih % ph or iw % pw:
            raise ValueError("no integer scale")
        sh, sw = ih // ph, iw // pw
        out = [row[c0:c1 + 1] for row in g[r0:r1 + 1]]
        for i in range(ih):
            for j in range(iw):
                out[1 + i][1 + j] = g[pr0 + i // sh][pc0 + j // sw]
        return out
    return fn


def fam(train):
    fn = _make()
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return
        except Exception:
            return
    yield ("frame_with_scaled_pattern", 1, fn)


FAMILIES = [fam]
