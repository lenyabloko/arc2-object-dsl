CARD = "fea12743"
READING = ("Among the equally sized panels, the one whose shape is the cell-wise union of two other "
           "panels is recoloured with one new colour and those two component panels with another.")


def _colors(g):
    return {x for r in g for x in r}


def _period(lines, bg):
    n = len(lines)
    for p in range(2, n):
        if (n - 1) % p:
            continue
        if all(all(x == bg for x in lines[k]) for k in range(0, n, p)):
            return p
    return None


def _panels(g, bg):
    H, W = len(g), len(g[0])
    pr = _period(g, bg)
    pc = _period([[g[r][c] for r in range(H)] for c in range(W)], bg)
    if pr is None or pc is None:
        return None
    pans = []
    for r0 in range(1, H, pr):
        for c0 in range(1, W, pc):
            cells = frozenset((a, b) for a in range(pr - 1) for b in range(pc - 1)
                              if g[r0 + a][c0 + b] != bg)
            pans.append((r0, c0, pr - 1, pc - 1, cells))
    return pans


def _find(pans):
    n = len(pans)
    for k in range(n):
        for i in range(n):
            for j in range(i + 1, n):
                if k in (i, j):
                    continue
                A, B, C = pans[i][4], pans[j][4], pans[k][4]
                if A and B and A != B and A != C and B != C and (A | B) == C:
                    return i, j, k
    return None


def _induce(train):
    res = None
    for p in train:
        i, o = p["input"], p["output"]
        pans = _panels(i, 0)
        if pans is None:
            return None
        t = _find(pans)
        if t is None:
            return None
        a, b, k = t

        def colof(pi):
            r0, c0, h, w, cells = pans[pi]
            cs = {o[r0 + x][c0 + y] for (x, y) in cells}
            return cs.pop() if len(cs) == 1 else None

        pc, pc2, wc = colof(a), colof(b), colof(k)
        if pc is None or pc != pc2 or wc is None:
            return None
        if res is None:
            res = (pc, wc)
        elif res != (pc, wc):
            return None
    return res


def _make(part_c, whole_c, bg):
    def fn(g):
        out = [row[:] for row in g]
        pans = _panels(g, bg)
        if not pans:
            return out
        t = _find(pans)
        if t is None:
            return out
        a, b, k = t
        for idx, col in ((a, part_c), (b, part_c), (k, whole_c)):
            r0, c0, h, w, cells = pans[idx]
            for (x, y) in cells:
                out[r0 + x][c0 + y] = col
        return out
    return fn


def fam(train):
    roles = _induce(train)
    if roles is None:
        return
    fn = _make(roles[0], roles[1], 0)
    try:
        if all(fn(p["input"]) == p["output"] for p in train):
            yield ("union_panel_recolor", 1, fn)
    except Exception:
        pass


FAMILIES = [fam]
