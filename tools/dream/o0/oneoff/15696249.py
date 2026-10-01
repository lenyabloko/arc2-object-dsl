CARD = "15696249"
READING = ("Find the single-colour row (or column) of the input; the output is a k-times enlarged blank canvas with the input "
           "tiled k times along that row (column) in the block position matching its index.")


def _ratio(train):
    ks = set()
    for p in train:
        I, O = p["input"], p["output"]
        if len(O) % len(I) or len(O[0]) % len(I[0]):
            return None
        a, b = len(O) // len(I), len(O[0]) // len(I[0])
        if a != b:
            return None
        ks.add(a)
    return ks.pop() if len(ks) == 1 else None


def _make(k_mode, k_fixed, bg):
    def fn(g):
        h, w = len(g), len(g[0])
        if k_mode == 'fixed':
            kr = kc = k_fixed
        else:
            kr, kc = h, w
        out = [[bg] * (w * kc) for _ in range(h * kr)]
        urows = [i for i in range(h) if len(set(g[i])) == 1]
        ucols = [j for j in range(w) if len(set(g[r][j] for r in range(h))) == 1]
        if len(urows) == 1 and urows[0] < kr:
            bi = urows[0]
            for t in range(kc):
                for r in range(h):
                    for c in range(w):
                        out[bi * h + r][t * w + c] = g[r][c]
        elif len(ucols) == 1 and ucols[0] < kc:
            bj = ucols[0]
            for t in range(kr):
                for r in range(h):
                    for c in range(w):
                        out[t * h + r][bj * w + c] = g[r][c]
        return out
    return fn


def fam(train):
    k = _ratio(train)
    if k is None:
        return
    cands = [("tile_along_uniform_line_k=size", 1, _make('size', None, 0)),
             ("tile_along_uniform_line_k=%d" % k, 2, _make('fixed', k, 0))]
    n = 0
    for name, cost, fn in cands:
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, cost, fn)
                n += 1
        except Exception:
            pass


FAMILIES = [fam]
