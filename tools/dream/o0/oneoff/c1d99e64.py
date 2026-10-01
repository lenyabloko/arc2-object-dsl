CARD = "c1d99e64"
READING = ("Every row and every column consisting entirely of the empty colour is repainted in the "
           "line colour learned from training; all other cells are unchanged.")


def _learn(train):
    src = dst = None
    for p in train:
        g, o = p["input"], p["output"]
        H, W = len(g), len(g[0])
        for i in range(H):
            for j in range(W):
                if g[i][j] != o[i][j]:
                    if src is None:
                        src, dst = g[i][j], o[i][j]
                    elif (src, dst) != (g[i][j], o[i][j]):
                        return None
    if src is None:
        return None
    return src, dst


def _make(src, dst, rows, cols):
    def fn(g):
        H, W = len(g), len(g[0])
        out = [list(r) for r in g]
        if rows:
            for i in range(H):
                if all(x == src for x in g[i]):
                    out[i] = [dst] * W
        if cols:
            for j in range(W):
                if all(g[i][j] == src for i in range(H)):
                    for i in range(H):
                        out[i][j] = dst
        return out
    return fn


def fam(train):
    sd = _learn(train)
    if sd is None:
        return
    src, dst = sd
    for name, cost, rows, cols in (("rows_and_cols", 1, True, True),
                                   ("rows_only", 2, True, False),
                                   ("cols_only", 2, False, True)):
        fn = _make(src, dst, rows, cols)
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
            yield ("full_lines_%s" % name, cost, fn)


FAMILIES = [fam]
