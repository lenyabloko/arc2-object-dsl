CARD = "7d7772cc"
READING = ("A framed key line sits beside a uniform frame line; each loose cell in the open "
           "region moves to the line next to the frame if it matches the key colour at its "
           "position, otherwise to the far edge of the open region.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _flipv(g):
    return [row[:] for row in g[::-1]]


def _bg(cells):
    cnt = {}
    for v in cells:
        cnt[v] = cnt.get(v, 0) + 1
    return max(sorted(cnt), key=lambda k: cnt[k])


def _solve_rows(g, match_near):
    """Frame line is a full uniform row L; data region strictly above L (rows 0..L-1),
    key row L+1. Returns output or None if the layout does not parse."""
    H, W = len(g), len(g[0])
    for L in range(1, H - 1):
        row = g[L]
        fc = row[0]
        if any(v != fc for v in row):
            continue
        data = g[:L]
        dcells = [v for r in data for v in r]
        if fc in dcells:
            continue
        rest = [v for r in g[L + 1:] for v in r]
        if fc not in rest:
            continue
        bg = _bg(dcells)
        key = g[L + 1]
        movers = [(r, c, g[r][c]) for r in range(L) for c in range(W) if g[r][c] != bg]
        if not movers:
            continue
        out = [r[:] for r in g]
        for r in range(L):
            for c in range(W):
                out[r][c] = bg
        near, far = L - 1, 0
        for r, c, v in movers:
            m = (v == key[c])
            tgt = near if (m == match_near) else far
            out[tgt][c] = v
        return out
    return None


def _orient(g, k):
    # k in 0..3: identity, flip vertical, transpose, transpose+flip
    if k == 0:
        return g, lambda o: o
    if k == 1:
        return _flipv(g), lambda o: _flipv(o)
    if k == 2:
        return _T(g), lambda o: _T(o)
    return _flipv(_T(g)), lambda o: _T(_flipv(o))


def _make(match_near):
    def fn(g):
        g = [list(r) for r in g]
        for k in range(4):
            h, back = _orient(g, k)
            o = _solve_rows(h, match_near)
            if o is not None:
                return back(o)
        return None
    return fn


def fam(train):
    for name, cost, mn in (("key_match_near", 1, True), ("key_match_far", 2, False)):
        fn = _make(mn)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
