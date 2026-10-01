CARD = "332202d5"
READING = ("A vertical line crossed by coloured horizontal lines: each background row takes the colour of "
           "its nearest horizontal line (rows equidistant to two different colours become the crossing "
           "colour), the horizontal lines become crossing-colour lines, and the vertical line swaps its "
           "line and crossing colours.")


def _T(g):
    return [list(r) for r in zip(*g)]


def _mc(xs):
    cnt = {}
    for x in xs:
        cnt[x] = cnt.get(x, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _solve(g):
    H, W = len(g), len(g[0])
    bg = _mc([x for r in g for x in r])
    vcols = [c for c in range(W) if all(g[r][c] != bg for r in range(H))]
    hrows = [r for r in range(H) if all(x != bg for x in g[r])]
    if not vcols or not hrows or len(hrows) == H:
        return None
    nonline = [r for r in range(H) if r not in hrows]
    V = _mc([g[r][c] for r in nonline for c in vcols])
    X = _mc([g[r][c] for r in hrows for c in vcols])
    if V == X:
        return None
    lcol = {}
    for r in hrows:
        others = [g[r][c] for c in range(W) if c not in vcols]
        if not others:
            return None
        lcol[r] = _mc(others)
    out = []
    for r in range(H):
        if r in lcol:
            row = [X] * W
            for c in vcols:
                row[c] = V
        else:
            dmin = min(abs(r - h) for h in hrows)
            cols = set(lcol[h] for h in hrows if abs(r - h) == dmin)
            if len(cols) == 1:
                C = cols.pop()
                row = [C] * W
                for c in vcols:
                    row[c] = X
            else:
                row = [X] * W
        out.append(row)
    return out


def _solve_any(g):
    o = _solve(g)
    if o is not None:
        return o
    o = _solve(_T(g))
    return None if o is None else _T(o)


def fam(train):
    if all(_solve_any(p["input"]) == p["output"] for p in train):
        yield ("nearest_line_fill", 2, _solve_any)


FAMILIES = [fam]
