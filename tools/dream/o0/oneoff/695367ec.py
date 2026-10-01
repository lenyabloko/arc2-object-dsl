CARD = "695367ec"
READING = ("A solid N x N square of colour c becomes a fixed-size grid ruled by lines of colour c "
           "every N+1 cells (after each block of N background cells).")


def _make(H, W, phase):
    def fn(g):
        n = len(g)
        c = g[0][0]
        p = n + 1
        out = [[0] * W for _ in range(H)]
        for i in range(H):
            for j in range(W):
                if (i - phase(n)) % p == 0 or (j - phase(n)) % p == 0:
                    out[i][j] = c
        return out
    return fn


def fam(train):
    sizes = set((len(p["output"]), len(p["output"][0])) for p in train)
    cands = []
    if len(sizes) == 1:
        H, W = sizes.pop()
        cands.append(("ruled_lines_after_blocks_fixed_size", 1, _make(H, W, lambda n: n)))
        cands.append(("ruled_lines_from_origin_fixed_size", 2, _make(H, W, lambda n: 0)))
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


FAMILIES = [fam]
