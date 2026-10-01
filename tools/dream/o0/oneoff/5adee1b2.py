CARD = "5adee1b2"
READING = ("Two-colour legend pairs map an object colour to a frame colour; every object of a key colour "
           "gets its 1-cell-expanded bounding box filled with the mapped colour on background cells reachable "
           "from the box border (enclosed holes stay background).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _comps(g, bg, same_colour):
    H, W = len(g), len(g[0])
    seen = [[False] * W for _ in range(H)]
    out = []
    for i in range(H):
        for j in range(W):
            if g[i][j] == bg or seen[i][j]:
                continue
            stack, cells = [(i, j)], []
            seen[i][j] = True
            while stack:
                a, b = stack.pop()
                cells.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg and \
                                (not same_colour or g[x][y] == g[i][j]):
                            seen[x][y] = True
                            stack.append((x, y))
            out.append(cells)
    return out


def _frame(g):
    H, W = len(g), len(g[0])
    bg = _bg(g)
    comps = _comps(g, bg, False)
    legend, objs = [], []
    for cells in comps:
        cols = {g[a][b] for a, b in cells}
        (legend if len(cols) == 2 else objs).append(cells)
    objcols = {g[c[0][0]][c[0][1]] for c in objs}
    mp = {}
    for cells in legend:
        cols = {g[a][b] for a, b in cells}
        key = [c for c in cols if c in objcols]
        if len(key) == 1:
            k = key[0]
        else:  # fallback: colour of the leftmost cell
            a, b = min(cells, key=lambda t: (t[1], t[0]))
            k = g[a][b]
        v = (cols - {k}).pop()
        mp[k] = v
    if not mp:
        return None
    out = [list(r) for r in g]
    for cells in objs:
        c = g[cells[0][0]][cells[0][1]]
        if c not in mp:
            continue
        r0 = max(0, min(a for a, _ in cells) - 1)
        r1 = min(H - 1, max(a for a, _ in cells) + 1)
        c0 = max(0, min(b for _, b in cells) - 1)
        c1 = min(W - 1, max(b for _, b in cells) + 1)
        seen = set()
        stack = [(a, b) for a in range(r0, r1 + 1) for b in range(c0, c1 + 1)
                 if (a in (r0, r1) or b in (c0, c1)) and g[a][b] == bg]
        seen.update(stack)
        while stack:
            a, b = stack.pop()
            out[a][b] = mp[c]
            for x, y in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if r0 <= x <= r1 and c0 <= y <= c1 and (x, y) not in seen and g[x][y] == bg:
                    seen.add((x, y))
                    stack.append((x, y))
    return out


def fam(train):
    try:
        if all(_frame(p["input"]) == p["output"] for p in train):
            yield "legend_frame_bbox_fill", 1, _frame
    except Exception:
        pass


FAMILIES = [fam]
