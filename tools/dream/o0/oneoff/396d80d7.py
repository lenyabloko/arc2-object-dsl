CARD = "396d80d7"
READING = ("Every background cell that touches the main shape colour diagonally but no non-background cell "
           "orthogonally is painted with the shape's minority (inner) colour.")


def _count(g):
    c = {}
    for r in g:
        for x in r:
            c[x] = c.get(x, 0) + 1
    return c


def _make(require_no_orth):
    def fn(g):
        H, W = len(g), len(g[0])
        cnt = _count(g)
        order = sorted(cnt, key=lambda k: -cnt[k])
        if len(order) < 3:
            return [list(r) for r in g]
        bg = order[0]

        def area(c):
            pts = [(i, j) for i in range(H) for j in range(W) if g[i][j] == c]
            rs = [a for a, _ in pts]; cs = [b for _, b in pts]
            return (max(rs) - min(rs) + 1) * (max(cs) - min(cs) + 1)
        # outer (shape) colour = largest bounding box, ties by count
        rest = sorted(order[1:], key=lambda c: (-area(c), -cnt[c]))
        shape, fill = rest[0], rest[1]
        out = [list(r) for r in g]
        for i in range(H):
            for j in range(W):
                if g[i][j] != bg:
                    continue
                diag = any(0 <= i + a < H and 0 <= j + b < W and g[i + a][j + b] == shape
                           for a in (-1, 1) for b in (-1, 1))
                orth = any(0 <= i + a < H and 0 <= j + b < W and g[i + a][j + b] != bg
                           for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if diag and (not orth or not require_no_orth):
                    out[i][j] = fill
        return out
    return fn


def fam(train):
    for req in (True, False):
        fn = _make(req)
        try:
            ok = all(fn(p["input"]) == p["output"] for p in train)
        except Exception:
            ok = False
        if ok:
            yield ("diag_not_orth_fill" if req else "diag_fill", 1 + (not req), fn)
FAMILIES = [fam]
