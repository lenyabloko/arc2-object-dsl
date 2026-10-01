CARD = "692cd3b6"
READING = ("Two hollow frames each have one gap; colour the gaps and fill the rectangle spanned by the "
           "two cells just outside the gaps, except the parts hidden behind a frame (the frame's band "
           "extended away from its gap).")


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
            st = [(i, j)]
            seen[i][j] = True
            cells = []
            while st:
                a, b = st.pop()
                cells.append((a, b))
                for da in (-1, 0, 1):
                    for db in (-1, 0, 1):
                        x, y = a + da, b + db
                        if 0 <= x < H and 0 <= y < W and not seen[x][y] and g[x][y] != bg:
                            seen[x][y] = True
                            st.append((x, y))
            out.append(cells)
    return out


def _frame(g, bg, cells):
    r0 = min(a for a, _ in cells); r1 = max(a for a, _ in cells)
    c0 = min(b for _, b in cells); c1 = max(b for _, b in cells)
    if r1 - r0 < 2 or c1 - c0 < 2:
        return None
    gaps = []
    for i in range(r0, r1 + 1):
        for j in range(c0, c1 + 1):
            if (i in (r0, r1) or j in (c0, c1)) and g[i][j] == bg:
                gaps.append((i, j))
    if len(gaps) != 1:
        return None
    gi, gj = gaps[0]
    corner = gi in (r0, r1) and gj in (c0, c1)
    if corner:
        return None
    if gi == r0:
        d = (-1, 0)
    elif gi == r1:
        d = (1, 0)
    elif gj == c0:
        d = (0, -1)
    else:
        d = (0, 1)
    return {"box": (r0, r1, c0, c1), "gap": (gi, gj), "d": d}


def _shadowed(f, i, j):
    r0, r1, c0, c1 = f["box"]
    dr, dc = f["d"]
    if dr == -1:   # gap on top: shadow below, within columns
        return c0 <= j <= c1 and i >= r0
    if dr == 1:
        return c0 <= j <= c1 and i <= r1
    if dc == -1:
        return r0 <= i <= r1 and j >= c0
    return r0 <= i <= r1 and j <= c1


def _make(fill):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        frames = []
        for cells in _comps(g, bg):
            f = _frame(g, bg, cells)
            if f is not None:
                frames.append(f)
        out = [row[:] for row in g]
        if len(frames) != 2:
            return out
        outs = []
        for f in frames:
            gi, gj = f["gap"]
            out[gi][gj] = fill
            outs.append((gi + f["d"][0], gj + f["d"][1]))
        ra, rb = sorted((outs[0][0], outs[1][0]))
        ca, cb = sorted((outs[0][1], outs[1][1]))
        for i in range(max(ra, 0), min(rb, H - 1) + 1):
            for j in range(max(ca, 0), min(cb, W - 1) + 1):
                if g[i][j] != bg:
                    continue
                if any(_shadowed(f, i, j) for f in frames):
                    continue
                out[i][j] = fill
        return out
    return fn


def _fill_colour(train):
    cols = set()
    for p in train:
        for ri, ro in zip(p["input"], p["output"]):
            for a, b in zip(ri, ro):
                if a != b:
                    cols.add(b)
    return cols


def fam(train):
    try:
        cols = _fill_colour(train)
    except Exception:
        return
    if len(cols) != 1:
        return
    fill = cols.pop()
    fn = _make(fill)
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return
        except Exception:
            return
    yield ("frame_gap_bridge_fill", 1, fn)


FAMILIES = [fam]
