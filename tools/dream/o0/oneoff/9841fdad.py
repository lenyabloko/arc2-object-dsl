CARD = "9841fdad"
READING = ("The frame splits into a source panel holding coloured bars and an empty target panel; "
           "each bar is copied into the same row of the target panel, keeping its margin to the "
           "nearer side wall, and bars with equal margins on both sides are stretched to keep "
           "both margins.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _mode(vals):
    cnt = {}
    for x in vals:
        cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _panels(g):
    H, W = len(g), len(g[0])
    f = g[0][0]
    sep = [j for j in range(W) if all(g[i][j] == f for i in range(H))]
    rows = [i for i in range(H) if not all(x == f for x in g[i])]
    pans = []
    j = 0
    while j < W:
        if j in sep:
            j += 1
            continue
        k = j
        while k + 1 < W and (k + 1) not in sep:
            k += 1
        pans.append((j, k))
        j = k + 1
    return pans, rows


def _core(g):
    pans, rows = _panels(g)
    if len(pans) != 2 or not rows:
        return None
    info = []
    for (a, b) in pans:
        vals = [g[i][j] for i in rows for j in range(a, b + 1)]
        bgc = _mode(vals)
        info.append((a, b, bgc, len(set(vals)) > 1))
    srcs = [x for x in info if x[3]]
    tgts = [x for x in info if not x[3]]
    if len(srcs) != 1 or len(tgts) != 1:
        return None
    s0, s1, sbg, _ = srcs[0]
    t0, t1, tbg, _ = tgts[0]
    out = [list(r) for r in g]
    for i in rows:
        j = s0
        while j <= s1:
            c = g[i][j]
            if c == sbg:
                j += 1
                continue
            e = j
            while e + 1 <= s1 and g[i][e + 1] == c:
                e += 1
            L = j - s0
            R = s1 - e
            w = e - j + 1
            if L == R:
                lo, hi = t0 + L, t1 - R
            elif L < R:
                lo, hi = t0 + L, t0 + L + w - 1
            else:
                lo, hi = t1 - R - w + 1, t1 - R
            for x in range(max(lo, t0), min(hi, t1) + 1):
                out[i][x] = c
            j = e + 1
    return out


def _solve(g):
    r = _core(g)
    if r is not None:
        return r
    r = _core(_T(g))
    if r is not None:
        return _T(r)
    return [list(x) for x in g]


def fam(train):
    try:
        if all(_solve(p["input"]) == p["output"] for p in train):
            yield ("panel_bar_copy_nearest_wall", 1.0, _solve)
    except Exception:
        pass


FAMILIES = [fam]
