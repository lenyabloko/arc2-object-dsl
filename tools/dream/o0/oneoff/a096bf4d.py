CARD = "a096bf4d"
READING = ("In the lattice of identical tiles, whenever two tiles in the same tile-row or tile-column "
           "share the same odd-one-out cell (same position, same non-default colour), every tile "
           "between them receives that cell too.")


def _bg(g):
    # separator colour: most common colour on the grid's outer border
    H, W = len(g), len(g[0])
    cnt = {}
    for i in range(H):
        for j in range(W):
            if i in (0, H - 1) or j in (0, W - 1):
                cnt[g[i][j]] = cnt.get(g[i][j], 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _tiles(g, bg):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    boxes = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            st = [(i, j)]
            seen[i][j] = True
            r0 = r1 = i; c0 = c1 = j
            while st:
                a, b = st.pop()
                r0 = min(r0, a); r1 = max(r1, a); c0 = min(c0, b); c1 = max(c1, b)
                for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                        seen[x][y] = True
                        st.append((x, y))
            boxes.append((r0, c0, r1 - r0 + 1, c1 - c0 + 1))
    return boxes


def _make(axes):
    def fn(g):
        bg = _bg(g)
        out = [list(r) for r in g]
        boxes = _tiles(g, bg)
        if not boxes:
            return out
        h, w = boxes[0][2], boxes[0][3]
        if any((b[2], b[3]) != (h, w) for b in boxes):
            return out
        rows = sorted({b[0] for b in boxes}); cols = sorted({b[1] for b in boxes})
        grid = {(rows.index(b[0]), cols.index(b[1])): (b[0], b[1]) for b in boxes}
        R, C = len(rows), len(cols)
        mode = {}
        for di in range(h):
            for dj in range(w):
                cnt = {}
                for (r0, c0) in grid.values():
                    v = g[r0 + di][c0 + dj]
                    cnt[v] = cnt.get(v, 0) + 1
                mode[(di, dj)] = max(cnt, key=lambda k: cnt[k])
        lines = []
        if "row" in axes:
            for tr in range(R):
                lines.append([(tr, tc) for tc in range(C)])
        if "col" in axes:
            for tc in range(C):
                lines.append([(tr, tc) for tr in range(R)])
        for line in lines:
            line = [t for t in line if t in grid]
            for di in range(h):
                for dj in range(w):
                    m = mode[(di, dj)]
                    byv = {}
                    for k, t in enumerate(line):
                        r0, c0 = grid[t]
                        v = g[r0 + di][c0 + dj]
                        if v != m:
                            byv.setdefault(v, []).append(k)
                    for v, ks in byv.items():
                        if len(ks) < 2:
                            continue
                        for k in range(min(ks), max(ks) + 1):
                            r0, c0 = grid[line[k]]
                            out[r0 + di][c0 + dj] = v
        return out
    return fn


def fam(train):
    for name, axes in (("tile_anomaly_bridge_rows_cols", ("row", "col")),
                       ("tile_anomaly_bridge_rows", ("row",)),
                       ("tile_anomaly_bridge_cols", ("col",))):
        fn = _make(axes)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield (name, 1.0, fn)


FAMILIES = [fam]
