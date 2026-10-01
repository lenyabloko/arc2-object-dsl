CARD = "c64f1187"
READING = ("Each block of the block-grid carries a colour marker; replace every block by the "
           "legend shape (drawn beside that colour's marker in the legend) painted in that colour, "
           "blank blocks become background, and output just the block-grid region.")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _comps(g, pred, diag=False):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    if diag:
        nb += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
    for i in range(H):
        for j in range(W):
            if seen[i][j] or not pred(i, j):
                continue
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da, db in nb:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and pred(x, y):
                        seen[x][y] = True
                        st.append((x, y))
            out.append(cells)
    return out


def _make(dr, dc):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        bg = max(cnt, key=lambda k: cnt[k])
        nonbg = {k: v for k, v in cnt.items() if k != bg}
        body = max(nonbg, key=lambda k: nonbg[k])
        # blocks: 4-connected non-bg components containing a body cell
        comps = _comps(g, lambda i, j: g[i][j] != bg)
        blocks = []
        inblock = set()
        for cs in comps:
            if any(g[a][b] == body for a, b in cs) and len(cs) > 1:
                blocks.append(cs)
                inblock.update(cs)
        # legend: remaining non-bg cells; shape colour = most common
        rest = {}
        for i in range(H):
            for j in range(W):
                if g[i][j] != bg and (i, j) not in inblock:
                    rest[g[i][j]] = rest.get(g[i][j], 0) + 1
        if not rest or not blocks:
            return None
        shp = max(rest, key=lambda k: rest[k])
        bh = max(a for a, b in blocks[0]) - min(a for a, b in blocks[0]) + 1
        bw = max(b for a, b in blocks[0]) - min(b for a, b in blocks[0]) + 1
        legend = {}
        for i in range(H):
            for j in range(W):
                c = g[i][j]
                if c != bg and c != shp and (i, j) not in inblock:
                    pat = []
                    for a in range(bh):
                        row = []
                        for b in range(bw):
                            x, y = i + dr + a, j + dc + b
                            row.append(1 if 0 <= x < H and 0 <= y < W and g[x][y] == shp else 0)
                        pat.append(row)
                    legend[c] = pat
        r0 = min(a for cs in blocks for a, b in cs)
        r1 = max(a for cs in blocks for a, b in cs)
        c0 = min(b for cs in blocks for a, b in cs)
        c1 = max(b for cs in blocks for a, b in cs)
        out = [[bg] * (c1 - c0 + 1) for _ in range(r1 - r0 + 1)]
        for cs in blocks:
            cols = [g[a][b] for a, b in cs if g[a][b] != body]
            if not cols:
                continue
            col = cols[0]
            if col not in legend:
                return None
            pat = legend[col]
            br = min(a for a, b in cs)
            bc = min(b for a, b in cs)
            for a in range(bh):
                for b in range(bw):
                    if pat[a][b]:
                        x, y = br - r0 + a, bc - c0 + b
                        if 0 <= x < len(out) and 0 <= y < len(out[0]):
                            out[x][y] = col
        return out
    return fn


def fam(train):
    offs = [(1, 1), (1, 0), (0, 1), (1, -1), (-1, 1)]
    for k, (dr, dc) in enumerate(offs):
        fn = _make(dr, dc)
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
            yield ("legend_shape_blocks_%d_%d" % (dr, dc), 10 + k, fn)


FAMILIES = [fam]
