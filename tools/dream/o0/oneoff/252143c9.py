CARD = "252143c9"
READING = "Clear everything to the background colour, then from the centre cell draw a diagonal ray of the centre's colour toward the corner quadrant that holds most cells of that colour."


def _bg(g):
    cnt = {}
    for row in g:
        for v in row:
            cnt[v] = cnt.get(v, 0) + 1
    return max(cnt, key=lambda k: (cnt[k], -k))


def _make(score_mode):
    def fn(g):
        H, W = len(g), len(g[0])
        bg = _bg(g)
        cr, cc = H // 2, W // 2
        col = g[cr][cc]
        out = [[bg] * W for _ in range(H)]
        best = None
        for dr in (-1, 1):
            for dc in (-1, 1):
                n = 0
                for r in range(H):
                    for c in range(W):
                        if (r - cr) * dr > 0 and (c - cc) * dc > 0 and g[r][c] == col:
                            if score_mode == "ray":
                                if r - cr == (c - cc) * dr * dc:
                                    n += 1
                            else:
                                n += 1
                key = (n, -dr, dc)
                if best is None or key > best[0]:
                    best = (key, dr, dc)
        _, dr, dc = best
        r, c = cr, cc
        while 0 <= r < H and 0 <= c < W:
            out[r][c] = col
            r += dr
            c += dc
        return out
    return fn


def fam(train):
    for name, mode in (("diag_ray_to_quadrant", "quad"), ("diag_ray_to_diag", "ray")):
        fn = _make(mode)
        try:
            if all(fn(p["input"]) == p["output"] for p in train):
                yield (name, 1, fn)
        except Exception:
            pass


FAMILIES = [fam]
