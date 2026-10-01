CARD = "32597951"
READING = "Inside the bounding box of the patch-colour region, every cell of the pattern colour is recoloured to the new colour."


def _diffmap(train):
    m = {}
    for p in train:
        a, b = p["input"], p["output"]
        if len(a) != len(b) or len(a[0]) != len(b[0]):
            return None
        for r in range(len(a)):
            for c in range(len(a[0])):
                if a[r][c] != b[r][c]:
                    if m.setdefault(a[r][c], b[r][c]) != b[r][c]:
                        return None
    return m


def _make(src, dst, patch):
    def fn(g):
        H, W = len(g), len(g[0])
        cells = [(r, c) for r in range(H) for c in range(W) if g[r][c] == patch]
        out = [row[:] for row in g]
        if not cells:
            return out
        r0, r1 = min(r for r, _ in cells), max(r for r, _ in cells)
        c0, c1 = min(c for _, c in cells), max(c for _, c in cells)
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if g[r][c] in src:
                    out[r][c] = dst[g[r][c]]
        return out
    return fn


def fam(train):
    m = _diffmap(train)
    if not m:
        return
    cols = set()
    for p in train:
        for row in p["input"]:
            cols |= set(row)
    k = 0
    for patch in sorted(cols - set(m) - set(m.values())):
        fn = _make(set(m), m, patch)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield ("bbox_recolour_%d" % patch, 1 + k, fn)
                k += 1
        except Exception:
            pass


FAMILIES = [fam]
