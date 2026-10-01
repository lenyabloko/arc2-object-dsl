CARD = "b7f8a4d8"
READING = ("In a lattice of framed tiles, tiles whose inner colour is unusual are joined to every other "
           "tile of the same inner colour in their tile-row or tile-column by painting that colour "
           "across the background gaps between them (frames and other tiles left untouched).")


def _counts(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return cnt


def _sep(g, default):
    # background = colour of complete uniform separator rows/columns, if any
    lines = [r for r in g] + [list(c) for c in zip(*g)]
    cnt = {}
    for ln in lines:
        if len(set(ln)) == 1:
            cnt[ln[0]] = cnt.get(ln[0], 0) + 1
    if not cnt:
        return default
    return max(cnt, key=lambda c: (cnt[c], c == default))


def _make(k):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _counts(g)
        order = sorted(cnt, key=lambda c: (-cnt[c], c))
        bg = _sep(g, order[0])
        odd = set(order[k:])
        out = [row[:] for row in g]
        for c in odd:
            for i in range(H):
                js = [j for j in range(W) if g[i][j] == c]
                if len(js) >= 2:
                    for j in range(js[0], js[-1] + 1):
                        if g[i][j] == bg:
                            out[i][j] = c
            for j in range(W):
                iis = [i for i in range(H) if g[i][j] == c]
                if len(iis) >= 2:
                    for i in range(iis[0], iis[-1] + 1):
                        if g[i][j] == bg:
                            out[i][j] = c
        return out
    return fn


def fam(train):
    for k in (2, 3, 4, 1):
        fn = _make(k)
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("join_rare_inner_rank%d" % k, 1.0 + 0.1 * k, fn)


FAMILIES = [fam]
