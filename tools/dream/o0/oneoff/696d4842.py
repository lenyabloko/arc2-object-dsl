CARD = "696d4842"
READING = ("Each bent line pointing at a lone dot extends from that end up to the dot, and the same "
           "number of cells at its other end are recoloured with the dot's colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


D4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


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
                for da, db in D4:
                    x, y = a + da, b + db
                    if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] == col:
                        seen[x][y] = True
                        st.append((x, y))
            out.append((col, cells))
    return out


def _order(cells):
    s = set(cells)
    nb = {c: [(c[0] + a, c[1] + b) for a, b in D4 if (c[0] + a, c[1] + b) in s] for c in cells}
    ends = [c for c in cells if len(nb[c]) == 1]
    if len(ends) != 2 or any(len(v) > 2 for v in nb.values()):
        return None
    path = [min(ends)]
    prev = None
    while True:
        cur = path[-1]
        nxt = [x for x in nb[cur] if x != prev]
        if not nxt:
            break
        prev = cur
        path.append(nxt[0])
    if len(path) != len(cells):
        return None
    return path


def _make():
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        comps = _comps(g, bg)
        dots = {}
        for col, cells in comps:
            if len(cells) == 1:
                dots[cells[0]] = col
        out = [row[:] for row in g]
        for col, cells in comps:
            if len(cells) < 2:
                continue
            path = _order(cells)
            if path is None:
                continue
            for seq in (path, path[::-1]):
                end, before = seq[-1], seq[-2]
                dr, dc = end[0] - before[0], end[1] - before[1]
                r, c = end[0] + dr, end[1] + dc
                gap = []
                hit = None
                while 0 <= r < H and 0 <= c < W:
                    if g[r][c] != bg:
                        if (r, c) in dots and dots[(r, c)] != col:
                            hit = (r, c)
                        break
                    gap.append((r, c))
                    r += dr
                    c += dc
                if hit is None:
                    continue
                k = len(gap)
                for (a, b) in gap:
                    out[a][b] = col
                for (a, b) in seq[:k]:
                    out[a][b] = dots[hit]
                break
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
    yield ("snake_slides_to_dot", 1, fn)


FAMILIES = [fam]
