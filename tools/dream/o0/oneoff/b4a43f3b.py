CARD = "b4a43f3b"
READING = ("Above the separator line is a pattern drawn at block scale; shrink it to its true tile, then "
           "build the output by placing that tile at every coloured cell of the mask below the separator "
           "(output = mask size times tile size).")


def _split(g):
    H, W = len(g), len(g[0])
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    cands = []
    for i in range(1, H - 1):
        row = g[i]
        if len(set(row)) == 1 and row[0] != 0:
            excl = cnt[row[0]] == W
            cands.append((not excl, abs(2 * i - (H - 1)), "r", i, row[0]))
    for j in range(1, W - 1):
        colv = [g[i][j] for i in range(H)]
        if len(set(colv)) == 1 and colv[0] != 0:
            excl = cnt[colv[0]] == H
            cands.append((not excl, abs(2 * j - (W - 1)), "c", j, colv[0]))
    if not cands:
        return None
    cands.sort()
    _, _, kind, k, c = cands[0]
    if kind == "r":
        return [r[:] for r in g[:k]], [r[:] for r in g[k + 1:]], c
    return [r[:k] for r in g], [r[k + 1:] for r in g], c


def _blocky(p, f):
    H, W = len(p), len(p[0])
    if H % f or W % f:
        return False
    for i in range(H):
        for j in range(W):
            if p[i][j] != p[i - i % f][j - j % f]:
                return False
    return True


def _tile(p, f):
    return [[p[i][j] for j in range(0, len(p[0]), f)] for i in range(0, len(p), f)]


def _render(tile, mask, bg):
    th, tw = len(tile), len(tile[0])
    out = [[bg] * (len(mask[0]) * tw) for _ in range(len(mask) * th)]
    for a in range(len(mask)):
        for b in range(len(mask[0])):
            if mask[a][b] != bg:
                for i in range(th):
                    for j in range(tw):
                        out[a * th + i][b * tw + j] = tile[i][j]
    return out


def _make(fixed_f, swap):
    def fn(g):
        s = _split(g)
        if s is None:
            return [r[:] for r in g]
        pat, mask, _ = s
        if swap:
            pat, mask = mask, pat
        if fixed_f:
            f = fixed_f
        else:
            f = 1
            for k in range(2, min(len(pat), len(pat[0])) + 1):
                if _blocky(pat, k):
                    f = k
        return _render(_tile(pat, f), mask, 0)
    return fn


def fam(train):
    cands = [("maxblock", None, False)]
    for f in (1, 2, 3, 4):
        cands.append(("fixed%d" % f, f, False))
    cands.append(("maxblock_swap", None, True))
    for i, (nm, f, sw) in enumerate(cands):
        fn = _make(f, sw)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("scaled_tile_mask_" + nm, 1 + i, fn)
        except Exception:
            pass


FAMILIES = [fam]
