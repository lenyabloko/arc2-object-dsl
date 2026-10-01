CARD = "e7b06bea"
READING = ("The length L of the marker bar in the first column sets a period: the adjacent full-height "
           "colour stripes on the right are removed and replaced by a single column just left of them "
           "that cycles through the stripe colours in order, L rows per colour.")


def _fn(g):
    H, W = len(g), len(g[0])
    # full-height uniform non-zero columns forming the stripe block on the right
    full = [j for j in range(W) if g[0][j] != 0 and all(g[i][j] == g[0][j] for i in range(H))]
    if not full:
        return [list(r) for r in g]
    j1 = max(full)
    j0 = j1
    while j0 - 1 in full:
        j0 -= 1
    cols = [g[0][j] for j in range(j0, j1 + 1)]
    out = [list(r) for r in g]
    for i in range(H):
        for j in range(j0, j1 + 1):
            out[i][j] = 0
    # marker bar: the remaining non-zero vertical run starting at the top
    rest = [(i, j) for i in range(H) for j in range(W) if out[i][j] != 0]
    if not rest:
        return out
    mc = min(j for _, j in rest)
    L = 0
    while L < H and out[L][mc] != 0:
        L += 1
    L = max(L, 1)
    tc = j0 - 1
    if tc < 0:
        return out
    for i in range(H):
        out[i][tc] = cols[(i // L) % len(cols)]
    return out


def fam(train):
    try:
        if all(_fn(p["input"]) == p["output"] for p in train):
            yield ("stripes_to_cycled_column", 1.0, _fn)
    except Exception:
        pass


FAMILIES = [fam]
