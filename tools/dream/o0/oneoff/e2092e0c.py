CARD = "e2092e0c"
READING = ("The small pattern fenced off by a separator-coloured L in a corner is searched for elsewhere in "
           "the grid, and its copy is enclosed in a one-cell frame of the separator colour.")


def _flip(g, fv, fh):
    h = g[::-1] if fv else g
    return [r[::-1] for r in h] if fh else [r[:] for r in h]


def _key(g):
    """Top-left key: row k and column k (cells 0..k) are a uniform colour s; returns (k, s)."""
    H, W = len(g), len(g[0])
    for k in range(1, min(H, W) - 1):
        s = g[k][k]
        if s != 0 and all(g[k][j] == s for j in range(k + 1)) and all(g[i][k] == s for i in range(k + 1)):
            return k, s
    return None


def _solve(g, fv, fh, exact):
    G = _flip(g, fv, fh)
    H, W = len(G), len(G[0])
    ks = _key(G)
    if ks is None:
        return None
    k, s = ks
    pat = [row[:k] for row in G[:k]]
    best = None
    for r in range(H - k + 1):
        for c in range(W - k + 1):
            if r <= k and c <= k:
                continue
            if exact:
                sc = sum(1 for i in range(k) for j in range(k) if G[r + i][c + j] == pat[i][j])
            else:
                sc = sum(1 for i in range(k) for j in range(k)
                         if pat[i][j] != 0 and G[r + i][c + j] == pat[i][j])
            if best is None or sc > best[0]:
                best = (sc, r, c)
    if best is None:
        return None
    _, r, c = best
    out = [row[:] for row in G]
    for i in range(r - 1, r + k + 1):
        for j in range(c - 1, c + k + 1):
            if i in (r - 1, r + k) or j in (c - 1, c + k):
                if 0 <= i < H and 0 <= j < W:
                    out[i][j] = s
    return _flip(out, fv, fh)


def _make(fv, fh, exact):
    def fn(g):
        o = _solve(g, fv, fh, exact)
        return o if o is not None else [r[:] for r in g]
    return fn


def fam(train):
    cands = []
    for exact in (True, False):
        for fv in (0, 1):
            for fh in (0, 1):
                cands.append(("key_frame_v%d_h%d_exact%d" % (fv, fh, exact),
                              fv + fh + (0 if exact else 1), _make(fv, fh, exact)))
    cands.sort(key=lambda t: t[1])
    n = 0
    for name, cost, fn in cands:
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
            yield (name, cost, fn)
            n += 1
            if n >= 2:
                return


FAMILIES = [fam]
