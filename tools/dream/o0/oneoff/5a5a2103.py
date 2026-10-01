CARD = "5a5a2103"
READING = ("The separator lines split the grid into cells; the one non-key shape is stamped into every "
           "cell, recoloured with the key colour found in the first cell of that cell-row.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _lines(g):
    """Full uniform non-zero rows/cols -> (sep colour, row idx list, col idx list)."""
    H, W = len(g), len(g[0])
    rows = [i for i in range(H) if g[i][0] != 0 and all(x == g[i][0] for x in g[i])]
    cols = [j for j in range(W) if g[0][j] != 0 and all(g[i][j] == g[0][j] for i in range(H))]
    if not rows or not cols:
        return None
    s = g[rows[0]][0]
    if any(g[i][0] != s for i in rows) or any(g[0][j] != s for j in cols):
        return None
    return s, rows, cols


def _spans(idx, n):
    out, prev = [], -1
    for k in idx + [n]:
        if k - prev > 1:
            out.append((prev + 1, k))
        prev = k
    return out


def _solve(g):
    L = _lines(g)
    if L is None:
        return None
    s, rows, cols = L
    H, W = len(g), len(g[0])
    rs, cs = _spans(rows, H), _spans(cols, W)
    if len(rs) < 1 or len(cs) < 2:
        return None
    ch, cw = rs[0][1] - rs[0][0], cs[0][1] - cs[0][0]
    if any(b - a != ch for a, b in rs) or any(b - a != cw for a, b in cs):
        return None
    keys = []
    for (r0, r1) in rs:
        cl = {g[i][j] for i in range(r0, r1) for j in range(cs[0][0], cs[0][1])} - {0}
        if len(cl) != 1:
            return None
        keys.append(cl.pop())
    mask = set()
    for (r0, r1) in rs:
        for (c0, c1) in cs[1:]:
            for i in range(r0, r1):
                for j in range(c0, c1):
                    if g[i][j] != 0:
                        mask.add((i - r0, j - c0))
    if not mask:
        return None
    out = [list(r) for r in g]
    for k, (r0, r1) in enumerate(rs):
        for (c0, c1) in cs:
            for i in range(r0, r1):
                for j in range(c0, c1):
                    out[i][j] = keys[k] if (i - r0, j - c0) in mask else 0
    return out


def _rows(g):
    return _solve(g)


def _cols(g):
    r = _solve(_T(g))
    return None if r is None else _T(r)


def fam(train):
    for name, cost, fn in (("stamp_template_rowkeys", 1, _rows), ("stamp_template_colkeys", 2, _cols)):
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield name, cost, fn
        except Exception:
            pass


FAMILIES = [fam]
