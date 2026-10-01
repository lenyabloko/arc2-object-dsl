CARD = "10fcaaa3"
READING = "Tile the input k-by-k, then put a new colour on every empty diagonal neighbour of each coloured pixel (no wrap-around)."


def _infer(train):
    ks = set()
    for p in train:
        a, b = p["input"], p["output"]
        if len(b) % len(a) or len(b[0]) % len(a[0]):
            return None
        ky, kx = len(b) // len(a), len(b[0]) // len(a[0])
        ks.add((ky, kx))
    if len(ks) != 1:
        return None
    ky, kx = ks.pop()
    new = set()
    for p in train:
        ins = {v for row in p["input"] for v in row}
        outs = {v for row in p["output"] for v in row}
        new |= outs - ins
    if len(new) != 1:
        return None
    return ky, kx, new.pop()


def _make(ky, kx, mark, wrap):
    def fn(g):
        h, w = len(g), len(g[0])
        H, W = h * ky, w * kx
        t = [[g[r % h][c % w] for c in range(W)] for r in range(H)]
        out = [row[:] for row in t]
        for r in range(H):
            for c in range(W):
                if t[r][c] != 0 and t[r][c] != mark:
                    for dy in (-1, 1):
                        for dx in (-1, 1):
                            y, x = r + dy, c + dx
                            if wrap:
                                y %= H
                                x %= W
                            elif not (0 <= y < H and 0 <= x < W):
                                continue
                            if t[y][x] == 0:
                                out[y][x] = mark
        return out
    return fn


def fam(train):
    p = _infer(train)
    if p is None:
        return
    ky, kx, mark = p
    for name, cost, wrap in (("tile_diag_mark", 1, False), ("tile_diag_mark_wrap", 2, True)):
        fn = _make(ky, kx, mark, wrap)
        try:
            if all(fn(q["input"]) == q["output"] for q in train):
                yield (name, cost, fn)
        except Exception:
            pass


FAMILIES = [fam]
