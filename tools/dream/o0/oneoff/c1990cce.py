CARD = "c1990cce"
READING = ("The single marked cell of a one-row input becomes the apex of a square output in which two "
           "diagonal arms of that colour run down to the edges, and the region strictly below both arms "
           "is striped with new-colour diagonals parallel to one arm, spaced at a period learned from "
           "training and phased to that arm.")


def _new_colour(train):
    nc = None
    for p in train:
        ins = set(x for r in p["input"] for x in r)
        for r in p["output"]:
            for x in r:
                if x not in ins:
                    if nc is not None and nc != x:
                        return None
                    nc = x
    return nc


def _make(period, flip, nc):
    def fn(g):
        row = g[0]
        W = len(row)
        cnt = {}
        for x in row:
            cnt[x] = cnt.get(x, 0) + 1
        bg = max(cnt, key=lambda k: cnt[k])
        idx = [j for j, x in enumerate(row) if x != bg]
        if len(idx) != 1:
            return [list(r) for r in g]
        c0 = idx[0]
        mc = row[c0]
        H = W
        out = [[bg] * W for _ in range(H)]
        for r in range(H):
            for c in range(W):
                if c == c0 - r or c == c0 + r:
                    out[r][c] = mc
                    continue
                inside = (r + c > c0) and (r - c > -c0)
                if not inside:
                    continue
                if not flip:
                    k = (r - c) - (-c0)   # offset from the right arm line r - c = -c0
                else:
                    k = (r + c) - c0      # offset from the left arm line r + c = c0
                if k % period == 0:
                    out[r][c] = nc
        return out
    return fn


def fam(train):
    nc = _new_colour(train)
    if nc is None:
        return
    n = 0
    for period in range(2, 9):
        for flip in (0, 1):
            fn = _make(period, flip, nc)
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
                yield ("v_stripes_p%d_f%d" % (period, flip), period + flip, fn)
                n += 1
                if n >= 3:
                    return


FAMILIES = [fam]
