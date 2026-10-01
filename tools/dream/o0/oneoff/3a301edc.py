CARD = "3a301edc"
READING = ("The two-colour rectangle gets a surrounding frame in its inner colour whose thickness equals "
           "the inner block's size, shrunk if needed so the frame fits inside the grid.")


def _count(g):
    c = {}
    for r in g:
        for x in r:
            c[x] = c.get(x, 0) + 1
    return c


def _bbox(g, pred):
    pts = [(i, j) for i in range(len(g)) for j in range(len(g[0])) if pred(g[i][j])]
    if not pts:
        return None
    rs = [a for a, _ in pts]; cs = [b for _, b in pts]
    return min(rs), min(cs), max(rs), max(cs)


_MEAS = {
    "min": lambda h, w: min(h, w),
    "max": lambda h, w: max(h, w),
    "h": lambda h, w: h,
    "w": lambda h, w: w,
}


def _make(meas, cap):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _count(g)
        bg = max(cnt, key=lambda k: cnt[k])
        ob = _bbox(g, lambda v: v != bg)
        out = [list(r) for r in g]
        if ob is None:
            return out
        r0, c0, r1, c1 = ob
        outer = g[r0][c0]
        inner_cols = [c for c in cnt if c not in (bg, outer)]
        if not inner_cols:
            return out
        inner = inner_cols[0]
        ib = _bbox(g, lambda v: v == inner)
        t = _MEAS[meas](ib[2] - ib[0] + 1, ib[3] - ib[1] + 1)
        if cap:
            t = min(t, r0, c0, H - 1 - r1, W - 1 - c1)
        for i in range(r0 - t, r1 + t + 1):
            for j in range(c0 - t, c1 + t + 1):
                if 0 <= i < H and 0 <= j < W and not (r0 <= i <= r1 and c0 <= j <= c1):
                    out[i][j] = inner
        return out
    return fn


def fam(train):
    n = 0
    for cap in (True, False):
        for k, meas in enumerate(("min", "max", "h", "w")):
            fn = _make(meas, cap)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                n += 1
                yield ("frame_%s_cap%d" % (meas, cap), 1 + k + 4 * (not cap), fn)
                if n >= 3:
                    return
FAMILIES = [fam]
