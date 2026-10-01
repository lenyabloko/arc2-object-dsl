CARD = "6d0160f0"
READING = ("The grid is cut by separator lines into blocks; the one block containing the marker colour is "
           "copied into the block whose index equals the marker's position inside that block, and every "
           "other block is cleared.")


def _layout(g):
    H, W = len(g), len(g[0])
    seprows = [i for i in range(H) if g[i][0] != 0 and all(x == g[i][0] for x in g[i])]
    sepcols = [j for j in range(W) if g[0][j] != 0 and all(g[i][j] == g[0][j] for i in range(H))]

    def ranges(n, seps):
        out, start = [], None
        for k in range(n + 1):
            if k == n or k in seps:
                if start is not None:
                    out.append((start, k))
                start = None
            elif start is None:
                start = k
        return out

    return ranges(H, set(seprows)), ranges(W, set(sepcols))


def _make(marker):
    def fn(g):
        rr, cc = _layout(g)
        if not rr or not cc:
            return None
        src = None
        for bi, (r0, r1) in enumerate(rr):
            for bj, (c0, c1) in enumerate(cc):
                for i in range(r0, r1):
                    for j in range(c0, c1):
                        if g[i][j] == marker:
                            if src is not None and src[:2] != (bi, bj):
                                return None
                            src = (bi, bj, i - r0, j - c0)
        if src is None:
            return None
        bi, bj, li, lj = src
        if li >= len(rr) or lj >= len(cc):
            return None
        out = [row[:] for row in g]
        for (r0, r1) in rr:
            for (c0, c1) in cc:
                for i in range(r0, r1):
                    for j in range(c0, c1):
                        out[i][j] = 0
        sr0, sc0 = rr[bi][0], cc[bj][0]
        tr0, tr1 = rr[li]
        tc0, tc1 = cc[lj]
        for i in range(tr1 - tr0):
            for j in range(tc1 - tc0):
                if sr0 + i < rr[bi][1] and sc0 + j < cc[bj][1]:
                    out[tr0 + i][tc0 + j] = g[sr0 + i][sc0 + j]
        return out
    return fn


def fam(train):
    for m in range(1, 10):
        fn = _make(m)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("marker_block_to_index_c%d" % m, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
