CARD = "bcb3040b"
READING = ("The two cells of the colour that occurs exactly twice are joined by a straight "
           "(row, column or diagonal) segment, and every cell strictly between them is recoloured "
           "by a fixed colour map learned from training (background to the marker colour, other "
           "colours to their learned counterparts).")


def _markers(g):
    cnt = {}
    pos = {}
    for i, r in enumerate(g):
        for j, x in enumerate(r):
            cnt[x] = cnt.get(x, 0) + 1
            pos.setdefault(x, []).append((i, j))
    two = [c for c in cnt if cnt[c] == 2]
    if len(two) != 1:
        return None
    c = two[0]
    (a, b), (e, f) = pos[c]
    dr, dc = e - a, f - b
    if not (dr == 0 or dc == 0 or abs(dr) == abs(dc)):
        return None
    return c, (a, b), (e, f)


def _path(p, q):
    (a, b), (e, f) = p, q
    n = max(abs(e - a), abs(f - b))
    sr = (e > a) - (e < a)
    sc = (f > b) - (f < b)
    return [(a + k * sr, b + k * sc) for k in range(1, n)]


def _learn(train):
    m = {}
    rel = {}  # colour -> "marker" placeholder
    for p in train:
        mk = _markers(p["input"])
        if mk is None:
            return None
        c, s, t = mk
        for (i, j) in _path(s, t):
            x = p["input"][i][j]
            y = p["output"][i][j]
            key = x
            val = ("M" if y == c else y)
            if key in m and m[key] != val:
                return None
            m[key] = val
    return m


def _make(m, mode):
    def fn(g):
        mk = _markers(g)
        out = [list(r) for r in g]
        if mk is None:
            return out
        c, s, t = mk
        for (i, j) in _path(s, t):
            x = g[i][j]
            if x in m:
                v = m[x]
                out[i][j] = c if v == "M" else v
            elif mode == 1:
                out[i][j] = c
        return out
    return fn


def fam(train):
    m = _learn(train)
    if m is None:
        return
    for mode in (0, 1):
        fn = _make(m, mode)
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
            yield ("segment_recolour_mode%d" % mode, 1 + mode, fn)


FAMILIES = [fam]
