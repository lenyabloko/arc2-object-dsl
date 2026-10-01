CARD = "aee291af"
READING = ("Among the framed square panels (solid border, interior marked with a second colour) "
           "scattered over a noisy background, all are identical except one; output that odd panel.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _panels(g, bg, F, M):
    H, W = len(g), len(g[0])
    cands = []
    for k in range(3, min(H, W) + 1):
        for r in range(H - k + 1):
            for c in range(W - k + 1):
                ok = True
                for t in range(k):
                    if (g[r][c + t] != F or g[r + k - 1][c + t] != F
                            or g[r + t][c] != F or g[r + t][c + k - 1] != F):
                        ok = False
                        break
                if not ok:
                    continue
                hasm = False
                for i in range(r + 1, r + k - 1):
                    for j in range(c + 1, c + k - 1):
                        v = g[i][j]
                        if v == M:
                            hasm = True
                        elif v != F:
                            ok = False
                            break
                    if not ok:
                        break
                if ok and hasm:
                    cands.append((r, c, k))
    # keep only maximal panels (drop ones contained in another)
    keep = []
    for (r, c, k) in cands:
        inside = False
        for (r2, c2, k2) in cands:
            if (r2, c2, k2) != (r, c, k) and r2 <= r and c2 <= c and r + k <= r2 + k2 and c + k <= c2 + k2:
                inside = True
                break
        if not inside:
            keep.append((r, c, k))
    return keep


def _make(F, M):
    def fn(g):
        bg = _bg(g)
        ps = _panels(g, bg, F, M)
        groups = {}
        for r, c, k in ps:
            key = tuple(tuple(g[i][c:c + k]) for i in range(r, r + k))
            groups.setdefault(key, []).append((r, c))
        singles = [key for key, v in groups.items() if len(v) == 1]
        multi = [key for key, v in groups.items() if len(v) >= 2]
        if len(singles) != 1 or not multi:
            raise ValueError("no unique odd panel")
        return [list(row) for row in singles[0]]
    return fn


def fam(train):
    # frame colour = output border colour, mark colour = other output colour (same over all pairs)
    F = M = None
    for p in train:
        o = p["output"]
        f = o[0][0]
        ms = set(v for row in o for v in row) - {f}
        if len(ms) != 1:
            return
        m = ms.pop()
        if F is None:
            F, M = f, m
        elif (F, M) != (f, m):
            return
    fn = _make(F, M)
    for p in train:
        try:
            if fn(p["input"]) != p["output"]:
                return
        except Exception:
            return
    yield ("odd_panel_F%d_M%d" % (F, M), 1, fn)


FAMILIES = [fam]
