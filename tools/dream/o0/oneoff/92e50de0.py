CARD = "92e50de0"
READING = ("The grid is divided into equal cells by full separator lines; the one decorated cell's pattern is "
           "copied into every cell that lies an even number of cells away from it both vertically and horizontally.")


def _sep(g):
    H, W = len(g), len(g[0])
    for c in sorted({x for r in g for x in r}):
        rows = [i for i in range(H) if all(x == c for x in g[i])]
        cols = [j for j in range(W) if all(g[i][j] == c for i in range(H))]
        if rows and cols and len(rows) < H:
            return c, rows, cols
    return None


def _runs(n, seps):
    s = set(seps)
    out, cur = [], []
    for i in range(n):
        if i in s:
            if cur:
                out.append(cur)
            cur = []
        else:
            cur.append(i)
    if cur:
        out.append(cur)
    return out


def _bg(g, sc):
    cnt = {}
    for r in g:
        for x in r:
            if x != sc:
                cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k)) if cnt else 0


def _make(k):
    def fn(g):
        H, W = len(g), len(g[0])
        s = _sep(g)
        if s is None:
            return [r[:] for r in g]
        sc, rs, cs = s
        bg = _bg(g, sc)
        R = _runs(H, rs)
        C = _runs(W, cs)
        out = [r[:] for r in g]
        src = []
        for a, rr in enumerate(R):
            for b, cc in enumerate(C):
                if any(g[i][j] != bg for i in rr for j in cc):
                    src.append((a, b))
        for (a, b) in src:
            rr, cc = R[a], C[b]
            pat = [[g[i][j] for j in cc] for i in rr]
            for a2, r2 in enumerate(R):
                if (a2 - a) % k:
                    continue
                for b2, c2 in enumerate(C):
                    if (b2 - b) % k:
                        continue
                    for di in range(min(len(r2), len(rr))):
                        for dj in range(min(len(c2), len(cc))):
                            v = pat[di][dj]
                            if v != bg:
                                out[r2[di]][c2[dj]] = v
        return out
    return fn


def fam(train):
    for k in (2, 1, 3, 4):
        fn = _make(k)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("cell_copy_stride%d" % k, k, fn)
        except Exception:
            pass


FAMILIES = [fam]
