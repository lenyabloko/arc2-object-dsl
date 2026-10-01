CARD = "4522001f"
READING = ("The small L of the main colour around the marker cell points to a corner; the output, scaled up "
           "by the training size ratio, holds a run of equal squares of the main colour laid along the "
           "diagonal starting from that corner (square size and count induced from training).")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _sgn(v):
    return (v > 0) - (v < 0)


def _make(s, b, n):
    def fn(g):
        bg = _bg(g)
        H, W = len(g), len(g[0])
        pos = {}
        for i in range(H):
            for j in range(W):
                if g[i][j] != bg:
                    pos.setdefault(g[i][j], []).append((i, j))
        if len(pos) < 2:
            return None
        cols = sorted(pos, key=lambda c: len(pos[c]))
        marker, main = cols[0], cols[-1]
        mr = sum(a for a, _ in pos[marker]) / len(pos[marker])
        mc = sum(b_ for _, b_ in pos[marker]) / len(pos[marker])
        cr = sum(a for a, _ in pos[main]) / len(pos[main])
        cc = sum(b_ for _, b_ in pos[main]) / len(pos[main])
        dr, dc = _sgn(cr - mr), _sgn(cc - mc)
        if dr == 0 or dc == 0:
            return None
        OH, OW = H * s, W * s
        out = [[bg] * OW for _ in range(OH)]
        for k in range(n):
            if dr > 0:
                rs = range(OH - (k + 1) * b, OH - k * b)
            else:
                rs = range(k * b, (k + 1) * b)
            if dc > 0:
                cs = range(OW - (k + 1) * b, OW - k * b)
            else:
                cs = range(k * b, (k + 1) * b)
            for r in rs:
                for c in cs:
                    if 0 <= r < OH and 0 <= c < OW:
                        out[r][c] = main
        return out
    return fn


def fam(train):
    s = None
    for p in train:
        h, w = len(p["input"]), len(p["input"][0])
        oh, ow = len(p["output"]), len(p["output"][0])
        if oh % h or ow % w or oh // h != ow // w:
            return
        if s is None:
            s = oh // h
        elif s != oh // h:
            return
    found = 0
    for n in range(1, 5):
        for b in range(1, 3 * s + 1):
            fn = _make(s, b, n)
            try:
                ok = all(fn(p["input"]) == p["output"] for p in train)
            except Exception:
                ok = False
            if ok:
                yield ("diag_squares_s%d_b%d_n%d" % (s, b, n), 1.0 + 0.01 * (n + b), fn)
                found += 1
                if found >= 3:
                    return


FAMILIES = [fam]
