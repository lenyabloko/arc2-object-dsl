CARD = "91413438"
READING = ("The output is a canvas of N-by-N tiles of the input, where N is the number of background "
           "cells, and the input is copied into the first M tiles in reading order, M being the "
           "number of coloured cells.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _counts(g):
    zs = sum(1 for r in g for x in r if x == 0)
    return {"n0": zs, "nfg": len(g) * len(g[0]) - zs}


def _make(side_key, copy_key):
    def fn(g):
        cn = _counts(g)
        N, M = cn[side_key], cn[copy_key]
        h, w = len(g), len(g[0])
        out = [[0] * (N * w) for _ in range(N * h)]
        for t in range(min(M, N * N)):
            tr, tc = divmod(t, N)
            for r in range(h):
                for c in range(w):
                    out[tr * h + r][tc * w + c] = g[r][c]
        return out
    return fn


def fam(train):
    n = 0
    for sk in ("n0", "nfg"):
        for ck in ("nfg", "n0"):
            fn = _make(sk, ck)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("tile_canvas_%s_%s" % (sk, ck), 1.0 + n, fn)
                n += 1


FAMILIES = [fam]
