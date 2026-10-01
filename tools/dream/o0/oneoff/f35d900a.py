CARD = "f35d900a"
READING = ("Each of the corner dots is ringed by a 3x3 border of the other dot colour, and along each side "
           "joining two aligned dots a dotted line of a new colour is drawn, starting next to each ring and "
           "alternating symmetrically toward the middle.")


def _bg(g):
    cnt = {}
    for r in g:
        for x in r:
            cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: cnt[k])


def _colours(g):
    s = set()
    for r in g:
        s.update(r)
    return s


def _learn_conn(train):
    k = None
    for p in train:
        new = _colours(p["output"]) - _colours(p["input"])
        if len(new) != 1:
            return None
        c = new.pop()
        if k is not None and k != c:
            return None
        k = c
    return k


def _make(K, rad):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        dots = [(i, j, g[i][j]) for i in range(H) for j in range(W) if g[i][j] != bg]
        cols = sorted(set(c for _, _, c in dots))
        out = [r[:] for r in g]
        # connectors between aligned dots
        for a in range(len(dots)):
            for b in range(a + 1, len(dots)):
                i1, j1, _ = dots[a]
                i2, j2, _ = dots[b]
                if i1 == i2:
                    lo, hi = sorted((j1, j2))
                    e0, e1 = lo + rad, hi - rad
                    for j in range(e0 + 1, e1):
                        if min(j - e0, e1 - j) % 2 == 1:
                            out[i1][j] = K
                elif j1 == j2:
                    lo, hi = sorted((i1, i2))
                    e0, e1 = lo + rad, hi - rad
                    for i in range(e0 + 1, e1):
                        if min(i - e0, e1 - i) % 2 == 1:
                            out[i][j1] = K
        for i, j, c in dots:
            others = [x for x in cols if x != c]
            rc = others[0] if len(others) == 1 else c
            for x in range(i - rad, i + rad + 1):
                for y in range(j - rad, j + rad + 1):
                    if 0 <= x < H and 0 <= y < W and (x, y) != (i, j):
                        out[x][y] = rc
        return out
    return fn


def fam(train):
    K = _learn_conn(train)
    if K is None:
        return
    for rad in (1, 2):
        fn = _make(K, rad)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("swap_rings_dotted_r%d" % rad, rad, fn)
        except Exception:
            pass


FAMILIES = [fam]
