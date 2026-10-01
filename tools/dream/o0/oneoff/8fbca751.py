CARD = "8fbca751"
READING = ("The shape lives on a grid of k-by-k tiles anchored at its bounding box; every tile "
           "touching the shape has its empty cells filled with the new colour.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _fill_colour(train):
    cols = set()
    for p in train:
        g, o = p["input"], p["output"]
        for r in range(len(g)):
            for c in range(len(g[0])):
                if g[r][c] != o[r][c]:
                    cols.add(o[r][c])
    return cols.pop() if len(cols) == 1 else None


def _make(k, anchor, fc):
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        pts = [(r, c) for r in range(H) for c in range(W) if g[r][c] != bg]
        out = [row[:] for row in g]
        if not pts:
            return out
        if anchor == "bbox":
            R0 = min(r for r, _ in pts); C0 = min(c for _, c in pts)
        else:
            R0 = C0 = 0
        tiles = set(((r - R0) // k, (c - C0) // k) for r, c in pts)
        for (tr, tc) in tiles:
            for r in range(R0 + tr * k, R0 + tr * k + k):
                for c in range(C0 + tc * k, C0 + tc * k + k):
                    if 0 <= r < H and 0 <= c < W and out[r][c] == bg:
                        out[r][c] = fc
        return out
    return fn


def fam(train):
    if any(len(p["input"]) != len(p["output"]) or len(p["input"][0]) != len(p["output"][0])
           for p in train):
        return
    fc = _fill_colour(train)
    if fc is None:
        return
    n = 0
    for anchor in ("bbox", "origin"):
        for k in range(2, 8):
            fn = _make(k, anchor, fc)
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("tile_fill_%s_k%d" % (anchor, k), 1.0 + 0.1 * k + (0 if anchor == "bbox" else 1), fn)
                n += 1
                if n >= 3:
                    return


FAMILIES = [fam]
