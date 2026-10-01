CARD = "12422b43"
READING = "The marker column's length L selects the top L rows (minus the marker) as a stamp, which is repeated cyclically downward below the last non-empty row to the bottom of the grid."


def _marker(g):
    H, W = len(g), len(g[0])
    # marker column: an edge column whose non-zero cells form one run of a single colour starting at row 0
    for c in (0, W - 1):
        v = g[0][c]
        if v == 0:
            continue
        L = 0
        while L < H and g[L][c] == v:
            L += 1
        if all(g[r][c] == 0 for r in range(L, H)):
            return c, L
    return None


def _make(cyclic):
    def fn(g):
        H, W = len(g), len(g[0])
        m = _marker(g)
        out = [row[:] for row in g]
        if m is None:
            return out
        mc, L = m
        stamp = [[(g[r][c] if c != mc else 0) for c in range(W)] for r in range(L)]
        last = max((r for r in range(H) if any(g[r][c] != 0 for c in range(W) if c != mc)), default=-1)
        k = 0
        for r in range(last + 1, H):
            if not cyclic and k >= L:
                break
            row = stamp[k % L]
            for c in range(W):
                if row[c] != 0:
                    out[r][c] = row[c]
            k += 1
        return out
    return fn


def fam(train):
    for name, cost, cyc in (("marker_stamp_repeat_down", 1, True),):
        fn = _make(cyc)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
