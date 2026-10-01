CARD = "a406ac07"
READING = ("The key column and key row on the grid edge list colours; every cell whose key-column colour "
           "equals its key-row colour is painted that colour, giving one block per colour along the diagonal.")


def _make(kc_side, kr_side):
    def fn(g):
        H, W = len(g), len(g[0])
        kc = 0 if kc_side == 0 else W - 1
        kr = 0 if kr_side == 0 else H - 1
        out = [list(r) for r in g]
        for r in range(H):
            a = g[r][kc]
            if a == 0:
                continue
            for c in range(W):
                if g[kr][c] == a:
                    out[r][c] = a
        return out
    return fn


def fam(train):
    for kc_side in (1, 0):
        for kr_side in (1, 0):
            fn = _make(kc_side, kr_side)
            try:
                if all(fn(p["input"]) == p["output"] for p in train):
                    yield ("keycol%d_keyrow%d_match" % (kc_side, kr_side), 1, fn)
            except Exception:
                pass


FAMILIES = [fam]
