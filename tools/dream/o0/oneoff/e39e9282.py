CARD = "e39e9282"
READING = ("Marker cells touching a solid square are processed by the square's colour: for one colour the "
           "marker slides into the square onto its middle line (square kept), for the other the square is "
           "erased and the marker stays and also extends one cell into where the square was.")


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
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            out.append((col, cells))
    return out


def _blocks(g, bg):
    res = []
    for col, cells in _comps(g, bg):
        if len(cells) < 4:
            continue
        r0 = min(a for a, b in cells); r1 = max(a for a, b in cells)
        c0 = min(b for a, b in cells); c1 = max(b for a, b in cells)
        if (r1 - r0 + 1) * (c1 - c0 + 1) == len(cells) and r1 > r0 and c1 > c0:
            res.append((col, r0, r1, c0, c1))
    return res


def _apply(g, beh, default):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    blocks = _blocks(g, bg)
    bcols = set(b[0] for b in blocks)
    inblock = set()
    for col, r0, r1, c0, c1 in blocks:
        for a in range(r0, r1 + 1):
            for b in range(c0, c1 + 1):
                inblock.add((a, b))
    out = [row[:] for row in g]
    paints = []
    removed = set()
    for col, r0, r1, c0, c1 in blocks:
        mode = beh.get(col, default)
        if mode == "erase":
            for a in range(r0, r1 + 1):
                for b in range(c0, c1 + 1):
                    out[a][b] = bg
        # adjacent markers
        adj = []
        for b in range(c0, c1 + 1):
            adj.append((r0 - 1, b, 1, 0))
            adj.append((r1 + 1, b, -1, 0))
        for a in range(r0, r1 + 1):
            adj.append((a, c0 - 1, 0, 1))
            adj.append((a, c1 + 1, 0, -1))
        for a, b, da, db in adj:
            if not (0 <= a < H and 0 <= b < W):
                continue
            m = g[a][b]
            if m == bg or (a, b) in inblock or m in bcols:
                continue
            if mode == "absorb":
                if da:
                    t = (r0 + r1) // 2
                    paints.append((t, b, m))
                else:
                    t = (c0 + c1) // 2
                    paints.append((a, t, m))
                removed.add((a, b))
            else:
                paints.append((a + da, b + db, m))
    for a, b in removed:
        out[a][b] = bg
    for a, b, m in paints:
        out[a][b] = m
    return out


def _make(beh, default):
    return lambda g: _apply(g, beh, default)


def fam(train):
    cols = []
    for p in train:
        bg = _bg(p["input"])
        for b in _blocks(p["input"], bg):
            if b[0] not in cols:
                cols.append(b[0])
    cols.sort()
    cands = []
    n = len(cols)
    if n > 6:
        return
    modes = ("absorb", "erase")
    for mask in range(1 << n):
        beh = {c: modes[(mask >> i) & 1] for i, c in enumerate(cols)}
        for di, default in enumerate(modes):
            cands.append(("square_marker_%s_def%s" % ("".join(str((mask >> i) & 1) for i in range(n)), default),
                          bin(mask).count("1") + di, _make(beh, default)))
    cands.sort(key=lambda t: t[1])
    k = 0
    for name, cost, fn in cands:
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
            yield (name, cost, fn)
            k += 1
            if k >= 2:
                return


FAMILIES = [fam]
