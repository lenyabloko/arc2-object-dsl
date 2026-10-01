CARD = "9356391f"
READING = ("The colour list in the header row is drawn as concentric square rings around the single seed pixel "
           "(ring k gets the k-th listed colour), and any listed colour whose ring does not fit inside the grid "
           "is struck out in the header with the separator colour.")


def _parts(g):
    H, W = len(g), len(g[0])
    for s in range(1, H):
        if len(set(g[s])) == 1 and g[s][0] != 0:
            return s
    return None


def _make(strike):
    def fn(g):
        H, W = len(g), len(g[0])
        s = _parts(g)
        if s is None:
            return [r[:] for r in g]
        sc = g[s][0]
        cnt = {}
        for i in range(s + 1, H):
            for x in g[i]:
                cnt[x] = cnt.get(x, 0) + 1
        bg = max(cnt, key=lambda k: cnt[k])
        seeds = [(i, j) for i in range(s + 1, H) for j in range(W) if g[i][j] != bg]
        hdr = [x for r in g[:s] for x in r]
        last = max([i for i, x in enumerate(hdr) if x != bg], default=-1)
        seq = hdr[:last + 1]
        out = [r[:] for r in g]
        for (si, sj) in seeds:
            for k, col in enumerate(seq):
                for i in range(si - k, si + k + 1):
                    for j in range(sj - k, sj + k + 1):
                        if max(abs(i - si), abs(j - sj)) != k:
                            continue
                        if s < i < H and 0 <= j < W:
                            out[i][j] = col
                fits = si - k > s and si + k < H and sj - k >= 0 and sj + k < W
                if strike and not fits:
                    idx = k
                    out[idx // W][idx % W] = sc
        return out
    return fn


def fam(train):
    for name, strike in (("rings_strike_clipped", True), ("rings", False)):
        fn = _make(strike)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1 if strike else 0, fn)
        except Exception:
            pass


FAMILIES = [fam]
