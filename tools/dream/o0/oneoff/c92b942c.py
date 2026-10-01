CARD = "c92b942c"
READING = ("Tile the input 3x3; every row containing a coloured cell has its background filled with a "
           "line colour, and each coloured cell gets a second colour at its up-left and down-right "
           "diagonal neighbours.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _make(fy, fx, lc, dc, diags):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        HH, WW = H * fy, W * fx
        t = [[g[i % H][j % W] for j in range(WW)] for i in range(HH)]
        out = [row[:] for row in t]
        pts = [(i, j) for i in range(HH) for j in range(WW) if t[i][j] != bg]
        rows = set(i for i, j in pts)
        for i in rows:
            for j in range(WW):
                if out[i][j] == bg:
                    out[i][j] = lc
        for i, j in pts:
            for di, dj in diags:
                x, y = i + di, j + dj
                if 0 <= x < HH and 0 <= y < WW and t[x][y] == bg:
                    out[x][y] = dc
        return out
    return fn


def fam(train):
    p0 = train[0]
    H, W = len(p0["input"]), len(p0["input"][0])
    OH, OW = len(p0["output"]), len(p0["output"][0])
    if OH % H or OW % W:
        return
    fy, fx = OH // H, OW // W
    incol = set(x for p in train for r in p["input"] for x in r)
    new = sorted(set(x for p in train for r in p["output"] for x in r) - incol)
    diag_sets = [((-1, -1), (1, 1)), ((-1, 1), (1, -1)),
                 ((-1, -1), (1, 1), (-1, 1), (1, -1))]
    k = 0
    for lc in new:
        for dc in new:
            if lc == dc:
                continue
            for ds in diag_sets:
                fn = _make(fy, fx, lc, dc, ds)
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
                    k += 1
                    yield ("tile_rowline_diag_%d_%d" % (lc, dc), 10 + k, fn)


FAMILIES = [fam]
