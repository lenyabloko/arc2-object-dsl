CARD = "846bdb03"
READING = ("The two-coloured loose shape is moved inside the frame formed by the two coloured bars "
           "with corner markers, mirrored left-right if needed so each colour sits next to the bar "
           "of the same colour, and the frame is cropped out.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _find_frame(g, bg):
    H, W = len(g), len(g[0])
    pos = {}
    for i in range(H):
        for j in range(W):
            if g[i][j] != bg:
                pos.setdefault(g[i][j], []).append((i, j))
    for col, ps in pos.items():
        if len(ps) != 4:
            continue
        rs = sorted(set(p[0] for p in ps))
        cs = sorted(set(p[1] for p in ps))
        if len(rs) != 2 or len(cs) != 2:
            continue
        r1, r2 = rs
        c1, c2 = cs
        if r2 - r1 < 2 or c2 - c1 < 2:
            continue
        # bars: either vertical bars in columns c1,c2 or horizontal bars in rows r1,r2
        lv = [g[r][c1] for r in range(r1 + 1, r2)]
        rv = [g[r][c2] for r in range(r1 + 1, r2)]
        if len(set(lv)) == 1 and len(set(rv)) == 1 and lv[0] != bg and rv[0] != bg:
            return (r1, r2, c1, c2, lv[0], rv[0])
    return None


def _flip(cells, w):
    return {(a, w - 1 - b): v for (a, b), v in cells.items()}


def _solve(g, allow_flip):
    bg = _bg(g)
    fr = _find_frame(g, bg)
    if fr is None:
        return None
    r1, r2, c1, c2, L, R = fr
    shape = {}
    for i in range(len(g)):
        for j in range(len(g[0])):
            if g[i][j] == bg:
                continue
            if r1 <= i <= r2 and j in (c1, c2):
                continue
            shape[(i, j)] = g[i][j]
    if not shape:
        return None
    a0 = min(p[0] for p in shape); b0 = min(p[1] for p in shape)
    a1 = max(p[0] for p in shape); b1 = max(p[1] for p in shape)
    h, w = a1 - a0 + 1, b1 - b0 + 1
    if h != r2 - r1 - 1 or w != c2 - c1 - 1:
        return None
    cells = {(a - a0, b - b0): v for (a, b), v in shape.items()}

    def score(cs):
        # mean column of left colour minus mean column of right colour (want negative)
        lc = [b for (a, b), v in cs.items() if v == L]
        rc = [b for (a, b), v in cs.items() if v == R]
        if not lc or not rc:
            return 0
        return sum(lc) / len(lc) - sum(rc) / len(rc)

    if allow_flip and score(cells) > 0:
        cells = _flip(cells, w)
    out = [row[c1:c2 + 1] for row in g[r1:r2 + 1]]
    out = [list(r) for r in out]
    for i in range(1, h + 1):
        for j in range(1, w + 1):
            out[i][j] = bg
    for (a, b), v in cells.items():
        out[a + 1][b + 1] = v
    return out


def _make(allow_flip):
    def fn(g):
        return _solve(g, allow_flip)
    return fn


def fam(train):
    for name, cost, fn in (("frame_insert_mirror_to_bars", 1, _make(True)),
                           ("frame_insert_plain", 2, _make(False))):
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


FAMILIES = [fam]
