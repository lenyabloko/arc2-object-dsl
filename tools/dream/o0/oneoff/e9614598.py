CARD = "e9614598"
READING = ("Stamp the pattern learned from training (a small plus of a new colour) centred on the "
           "midpoint between the two marker cells.")


def _pts(g):
    return [(i, j) for i, r in enumerate(g) for j, x in enumerate(r) if x != 0]


def _make(stamp):
    def fn(g):
        out = [list(r) for r in g]
        pts = _pts(g)
        if len(pts) != 2:
            return out
        (a, b), (c, d) = pts
        if (a + c) % 2 or (b + d) % 2:
            return out
        mi, mj = (a + c) // 2, (b + d) // 2
        H, W = len(g), len(g[0])
        for di, dj, v in stamp:
            i, j = mi + di, mj + dj
            if 0 <= i < H and 0 <= j < W:
                out[i][j] = v
        return out
    return fn


def fam(train):
    stamp = None
    for p in train:
        g, o = p["input"], p["output"]
        pts = _pts(g)
        if len(pts) != 2:
            return
        (a, b), (c, d) = pts
        if (a + c) % 2 or (b + d) % 2:
            return
        mi, mj = (a + c) // 2, (b + d) // 2
        diff = frozenset((i - mi, j - mj, o[i][j]) for i in range(len(g)) for j in range(len(g[0]))
                         if o[i][j] != g[i][j])
        if stamp is None:
            stamp = diff
        elif diff != stamp:
            return
    if stamp is None:
        return
    fn = _make(sorted(stamp))
    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("midpoint_stamp", 1.0, fn)


FAMILIES = [fam]
