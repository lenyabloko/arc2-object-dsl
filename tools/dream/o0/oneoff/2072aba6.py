CARD = "2072aba6"
READING = "Upscale the grid by an integer factor, replacing each cell by a fixed block learned per colour (here every filled cell becomes a 2x2 checker of 1 and 2, empty cells stay empty)."

from collections import Counter


def _learn(train):
    kh = kw = None
    blocks = {}
    for p in train:
        a, b = p["input"], p["output"]
        H, W = len(a), len(a[0])
        OH, OW = len(b), len(b[0])
        if OH % H or OW % W:
            return None
        h, w = OH // H, OW // W
        if kh is None:
            kh, kw = h, w
        elif (kh, kw) != (h, w):
            return None
        for r in range(H):
            for c in range(W):
                blk = tuple(tuple(b[r * h + i][c * w + j] for j in range(w)) for i in range(h))
                v = a[r][c]
                if blocks.setdefault(v, blk) != blk:
                    return None
    return kh, kw, blocks


def fam(train):
    L = _learn(train)
    if L is None:
        return
    kh, kw, blocks = L
    cnt = Counter(v for p in train for row in p["input"] for v in row)
    bg = cnt.most_common(1)[0][0]
    fg = [c for c, _ in cnt.most_common() if c != bg]
    default_fg = blocks[fg[0]] if fg else blocks[bg]

    def fn(g):
        H, W = len(g), len(g[0])
        out = [[0] * (W * kw) for _ in range(H * kh)]
        for r in range(H):
            for c in range(W):
                blk = blocks.get(g[r][c], default_fg)
                for i in range(kh):
                    for j in range(kw):
                        out[r * kh + i][c * kw + j] = blk[i][j]
        return out

    if all(fn(p["input"]) == p["output"] for p in train):
        yield ("per_colour_block_upscale", 1, fn)


FAMILIES = [fam]
