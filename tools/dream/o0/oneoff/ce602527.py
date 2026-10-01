CARD = "ce602527"
READING = ("One large shape is cut off by the grid edge; output the small shape whose 2x-enlarged "
           "pattern matches the large shape's visible part.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _matches(mask, H, W, pat, k):
    """True if pat scaled by k can be placed so that, within the grid, it equals the mask."""
    big = set(mask)
    r0 = min(a for a, b in big); r1 = max(a for a, b in big)
    c0 = min(b for a, b in big); c1 = max(b for a, b in big)
    h, w = len(pat), len(pat[0])
    for oy in range(r1 - k * h + 1, r0 + 1):
        for ox in range(c1 - k * w + 1, c0 + 1):
            ok = True
            for i in range(max(0, oy), min(H, oy + k * h)):
                for j in range(max(0, ox), min(W, ox + k * w)):
                    want = pat[(i - oy) // k][(j - ox) // k]
                    if want != ((i, j) in big):
                        ok = False
                        break
                if not ok:
                    break
            if ok:
                return True
    return False


def _make(k):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        bycol = {}
        for i in range(H):
            for j in range(W):
                if g[i][j] != bg:
                    bycol.setdefault(g[i][j], []).append((i, j))
        if len(bycol) < 2:
            return None
        def touches(cs):
            return any(a in (0, H - 1) or b in (0, W - 1) for a, b in cs)
        bigs = [c for c in bycol if touches(bycol[c])]
        if len(bigs) != 1:
            bigs = [max(bycol, key=lambda c: len(bycol[c]))]
        bc = bigs[0]
        res = []
        for c, cs in bycol.items():
            if c == bc:
                continue
            r0 = min(a for a, b in cs); r1 = max(a for a, b in cs)
            c0 = min(b for a, b in cs); c1 = max(b for a, b in cs)
            S = set(cs)
            pat = [[(i, j) in S for j in range(c0, c1 + 1)] for i in range(r0, r1 + 1)]
            if _matches(bycol[bc], H, W, pat, k):
                res.append((c, pat))
        if len(res) != 1:
            return None
        c, pat = res[0]
        return [[c if x else bg for x in row] for row in pat]
    return fn


def fam(train):
    for idx, k in enumerate((2, 3, 4)):
        fn = _make(k)
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
            yield ("match_scaled_x%d" % k, 10 + idx, fn)


FAMILIES = [fam]
