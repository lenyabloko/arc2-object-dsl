CARD = "aab50785"
READING = ("Each pair of same-coloured 2x2 squares lying on the same two rows brackets a two-row strip; "
           "the strips between the brackets are cut out and stacked top to bottom.")


def _make(K):
    def fn(g):
        H, W = len(g), len(g[0])
        out = []
        r = 0
        while r < H - 1:
            starts = [c for c in range(W - 1)
                      if g[r][c] == K and g[r][c + 1] == K and g[r + 1][c] == K and g[r + 1][c + 1] == K]
            if starts:
                a, b = min(starts), max(starts)
                if b >= a + 2:
                    out.append(list(g[r][a + 2:b]))
                    out.append(list(g[r + 1][a + 2:b]))
                    r += 2
                    continue
            r += 1
        if not out or any(len(x) != len(out[0]) for x in out) or len(out[0]) == 0:
            raise ValueError("no strips")
        return out
    return fn


def fam(train):
    n = 0
    for K in range(1, 10):
        fn = _make(K)
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
            yield ("bracket_strips_K%d" % K, 1, fn)
            n += 1
            if n >= 2:
                return


FAMILIES = [fam]
