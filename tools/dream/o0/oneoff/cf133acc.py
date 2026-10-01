CARD = "cf133acc"
READING = ("Each one-cell gap in a horizontal line is filled with the line colour, and the gap's column "
           "becomes a vertical line where every stretch takes the colour of the gapped line just below it "
           "(the bottom stretch keeps the colour of the vertical stub at the edge).")


def _rot(g):
    return [list(r) for r in zip(*g[::-1])]


def _tr(g):
    return [list(r) for r in zip(*g)]


def _dihedral():
    # (forward, inverse) pairs
    def ident(g):
        return [list(r) for r in g]

    def r1(g):
        return _rot(g)

    def r2(g):
        return _rot(_rot(g))

    def r3(g):
        return _rot(_rot(_rot(g)))

    def t(g):
        return _tr(g)

    def fh(g):
        return [list(r[::-1]) for r in g]

    def fv(g):
        return [list(r) for r in g[::-1]]

    def at(g):
        return _rot(_rot(_tr(g)))

    return [("id", ident, ident), ("r90", r1, r3), ("r180", r2, r2), ("r270", r3, r1),
            ("tr", t, t), ("fh", fh, fh), ("fv", fv, fv), ("atr", at, at)]


def _core(g):
    H, W = len(g), len(g[0])
    out = [list(r) for r in g]
    gaps = {}
    for r in range(H):
        for c in range(1, W - 1):
            if g[r][c] == 0 and g[r][c - 1] != 0 and g[r][c + 1] != 0:
                gaps[(r, c)] = g[r][c - 1]
    cols = sorted(set(c for (_, c) in gaps))
    for c in cols:
        cur = g[H - 1][c]
        for r in range(H - 1, -1, -1):
            if (r, c) in gaps:
                cur = gaps[(r, c)]
            if out[r][c] == 0 and cur != 0:
                out[r][c] = cur
    return out


def fam(train):
    for name, f, inv in _dihedral():
        def fn(g, f=f, inv=inv):
            return inv(_core(f(g)))
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("gapcolumns_" + name, 1, fn)
                return
        except Exception:
            continue


FAMILIES = [fam]
