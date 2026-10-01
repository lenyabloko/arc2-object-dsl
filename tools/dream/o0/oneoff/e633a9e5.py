CARD = "e633a9e5"
READING = ("The grid is enlarged by duplicating its first and last rows and its first and last "
           "columns, so edge cells become 2-wide and interior cells stay 1-wide.")


def _make(k):
    # duplicate the k outermost rows/columns on each side (k induced from shapes)
    def fn(g):
        H, W = len(g), len(g[0])
        rows = []
        for i in range(H):
            rows.append(i)
            if i < k or i >= H - k:
                rows.append(i)
        cols = []
        for j in range(W):
            cols.append(j)
            if j < k or j >= W - k:
                cols.append(j)
        return [[g[i][j] for j in cols] for i in rows]
    return fn


def fam(train):
    for k in (1, 2):
        fn = _make(k)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("dup_edges_%d" % k, 1 + k, fn)
        except Exception:
            pass


FAMILIES = [fam]
