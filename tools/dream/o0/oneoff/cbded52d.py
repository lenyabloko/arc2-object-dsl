CARD = "cbded52d"
READING = ("In the grid of separated blocks, whenever two blocks in the same block-row or block-column "
           "carry the same marker colour at the same in-block position, every block between them gets "
           "that marker at that position too.")


def _bands(n, sepset):
    bands = []
    cur = []
    for i in range(n):
        if i in sepset:
            if cur:
                bands.append(cur)
                cur = []
        else:
            cur.append(i)
    if cur:
        bands.append(cur)
    return bands


def _make(cascade):
    def fn(g):
        H, W = len(g), len(g[0])
        # separator colour: a colour filling entire rows and columns
        seprows = [i for i in range(H) if len(set(g[i])) == 1]
        sepcols = [j for j in range(W) if len(set(g[i][j] for i in range(H))) == 1]
        cand = set(g[i][0] for i in seprows) & set(g[0][j] for j in sepcols)
        if not cand:
            return None
        sc = cand.pop()
        rs = set(i for i in seprows if g[i][0] == sc)
        cs = set(j for j in sepcols if g[0][j] == sc)
        rb = _bands(H, rs)
        cb = _bands(W, cs)
        if len(set(len(b) for b in rb)) != 1 or len(set(len(b) for b in cb)) != 1:
            return None
        bh, bw = len(rb[0]), len(cb[0])
        cnt = {}
        for R in rb:
            for C in cb:
                for i in R:
                    for j in C:
                        cnt[g[i][j]] = cnt.get(g[i][j], 0) + 1
        base = max(cnt, key=lambda k: cnt[k])
        nR, nC = len(rb), len(cb)
        out = [row[:] for row in g]
        src = g
        while True:
            changed = False
            for a in range(bh):
                for b in range(bw):
                    # rows of blocks
                    for I in range(nR):
                        for J1 in range(nC):
                            v = src[rb[I][a]][cb[J1][b]]
                            if v == base:
                                continue
                            for J2 in range(J1 + 2, nC):
                                if src[rb[I][a]][cb[J2][b]] == v:
                                    for J in range(J1 + 1, J2):
                                        if out[rb[I][a]][cb[J][b]] != v:
                                            out[rb[I][a]][cb[J][b]] = v
                                            changed = True
                    for J in range(nC):
                        for I1 in range(nR):
                            v = src[rb[I1][a]][cb[J][b]]
                            if v == base:
                                continue
                            for I2 in range(I1 + 2, nR):
                                if src[rb[I2][a]][cb[J][b]] == v:
                                    for I in range(I1 + 1, I2):
                                        if out[rb[I][a]][cb[J][b]] != v:
                                            out[rb[I][a]][cb[J][b]] = v
                                            changed = True
            if not cascade or not changed:
                break
            src = [row[:] for row in out]
        return out
    return fn


def fam(train):
    for k, cascade in enumerate((False, True)):
        fn = _make(cascade)
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
            yield ("between_equal_markers_%s" % ("cascade" if cascade else "once"), 10 + k, fn)


FAMILIES = [fam]
