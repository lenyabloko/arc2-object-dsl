CARD = "3f23242b"
READING = ("Every single marker cell is replaced by a fixed house-shaped stamp (roof, walls, centre "
           "post) whose floor row is extended across the whole grid as a line.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _markers(g, bg):
    return [(i, j) for i in range(len(g)) for j in range(len(g[0])) if g[i][j] != bg]


def _learn(train):
    """Learn (template dict offset->colour, line rows {dr: colour}, line cols {dc: colour})
    from a training pair containing exactly one marker."""
    for p in train:
        a, b = p["input"], p["output"]
        bg = _bg(a)
        ms = _markers(a, bg)
        if len(ms) != 1 or len(a) != len(b) or len(a[0]) != len(b[0]):
            continue
        r, c = ms[0]
        H, W = len(b), len(b[0])
        full_rows = [i for i in range(H) if all(x != bg for x in b[i])]
        full_cols = [j for j in range(W) if all(b[i][j] != bg for i in range(H))]
        cells = [(i, j) for i in range(H) for j in range(W)
                 if b[i][j] != bg and i not in full_rows and j not in full_cols]
        if not cells:
            continue
        r0 = min(i for i, _ in cells); r1 = max(i for i, _ in cells)
        c0 = min(j for _, j in cells); c1 = max(j for _, j in cells)
        # extend window to adjacent line rows / cols
        while r0 - 1 in full_rows:
            r0 -= 1
        while r1 + 1 in full_rows:
            r1 += 1
        while c0 - 1 in full_cols:
            c0 -= 1
        while c1 + 1 in full_cols:
            c1 += 1
        tmpl = {}
        for i in range(r0, r1 + 1):
            for j in range(c0, c1 + 1):
                tmpl[(i - r, j - c)] = b[i][j]
        lrows = {}
        for i in full_rows:
            outside = [b[i][j] for j in range(W) if not (c0 <= j <= c1)]
            if not outside:
                return None
            lrows[i - r] = max(set(outside), key=outside.count)
        lcols = {}
        for j in full_cols:
            outside = [b[i][j] for i in range(H) if not (r0 <= i <= r1)]
            if not outside:
                return None
            lcols[j - c] = max(set(outside), key=outside.count)
        return tmpl, lrows, lcols
    return None


def _make(model, write_bg):
    tmpl, lrows, lcols = model

    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        out = [row[:] for row in g]
        ms = _markers(g, bg)
        for r, c in ms:
            for dr, col in lrows.items():
                if 0 <= r + dr < H:
                    for j in range(W):
                        out[r + dr][j] = col
            for dc, col in lcols.items():
                if 0 <= c + dc < W:
                    for i in range(H):
                        out[i][c + dc] = col
        for r, c in ms:
            for (dr, dc), col in tmpl.items():
                if col == bg and not write_bg:
                    continue
                i, j = r + dr, c + dc
                if 0 <= i < H and 0 <= j < W:
                    out[i][j] = col
        return out
    return fn


def fam(train):
    model = _learn(train)
    if model is None:
        return
    for cost, wb in ((1, True), (2, False)):
        fn = _make(model, wb)
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
            yield ("stamp_with_lines_writebg%d" % wb, cost, fn)


FAMILIES = [fam]
